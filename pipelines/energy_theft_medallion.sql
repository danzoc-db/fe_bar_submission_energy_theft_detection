-- =============================================================================
-- Energy Theft Detection — Spark Declarative Pipeline (Medallion)
--
-- Bronze: Auto Loader from UC Volume raw parquet
-- Silver: Cleansed reads + ML model features (with data quality expectations)
-- Gold:   Business aggregates for dashboards & Genie (with expectations)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- BRONZE — Streaming tables from raw Volume parquet
-- ---------------------------------------------------------------------------

CREATE OR REFRESH MATERIALIZED VIEW property_reference
CLUSTER BY (region)
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM read_files(
  '/Volumes/${catalog}/${schema}/raw_data/property_reference/',
  format => 'parquet'
);

CREATE OR REFRESH MATERIALIZED VIEW meters
CLUSTER BY (fuel_type)
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM read_files(
  '/Volumes/${catalog}/${schema}/raw_data/meters/',
  format => 'parquet'
);

CREATE OR REFRESH MATERIALIZED VIEW smart_meter_reads (
  CONSTRAINT non_null_consumption EXPECT (consumption_kwh IS NOT NULL) ON VIOLATION DROP ROW
)
CLUSTER BY (account_id, fuel_type)
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM read_files(
  '/Volumes/${catalog}/${schema}/raw_data/smart_meter_reads/',
  format => 'parquet'
);

CREATE OR REFRESH MATERIALIZED VIEW _ground_truth_labels
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM read_files(
  '/Volumes/${catalog}/${schema}/raw_data/ground_truth/',
  format => 'parquet'
);


-- ---------------------------------------------------------------------------
-- SILVER — Cleansed data + ML model features
--
-- Data quality expectations:
--   DROP ROW  — invalid postcodes, future timestamps, unknown fuel types
--               are excluded from downstream tables.
--   ALLOW     — negative consumption, unknown regions, and feature-range
--               warnings are logged but records still flow through.
-- ---------------------------------------------------------------------------

CREATE OR REFRESH MATERIALIZED VIEW silver_smart_meter_reads (
  CONSTRAINT positive_consumption     EXPECT (consumption_kwh > 0),
  CONSTRAINT valid_read_timestamp     EXPECT (read_timestamp IS NOT NULL AND read_timestamp <= current_timestamp()) ON VIOLATION DROP ROW,
  CONSTRAINT valid_fuel_type          EXPECT (fuel_type IN ('electricity', 'gas')) ON VIOLATION DROP ROW
)
CLUSTER BY (account_id, fuel_type)
AS
SELECT smr.*
FROM smart_meter_reads smr
INNER JOIN (
    SELECT DISTINCT account_id
    FROM meters
    WHERE meter_type = 'smart'
) sm ON smr.account_id = sm.account_id;

CREATE OR REFRESH MATERIALIZED VIEW silver_property_reference (
  CONSTRAINT valid_uk_postcode EXPECT (postcode RLIKE '^[A-Z]{1,2}[0-9][0-9A-Z]?\\s?[0-9][A-Z]{2}$') ON VIOLATION DROP ROW,
  CONSTRAINT known_region      EXPECT (region IN ('London', 'South East', 'South West', 'East of England', 'West Midlands', 'East Midlands', 'North West', 'North East', 'Yorkshire and the Humber', 'Wales', 'Scotland'))
)
CLUSTER BY (region)
AS
SELECT *
FROM property_reference
WHERE postcode IS NOT NULL
  AND LENGTH(TRIM(postcode)) > 0
  AND region IS NOT NULL
  AND property_type IS NOT NULL;

CREATE OR REFRESH MATERIALIZED VIEW silver_account_features (
  CONSTRAINT positive_mean_consumption   EXPECT (mean_consumption > 0),
  CONSTRAINT valid_comms_gap_rate        EXPECT (comms_gap_rate BETWEEN 0 AND 1),
  CONSTRAINT reasonable_consumption_drop EXPECT (consumption_drop_pct BETWEEN -100 AND 100)
)
CLUSTER BY (account_id)
AS
WITH reads AS (
    SELECT
        account_id,
        consumption_kwh,
        HOUR(read_timestamp) AS hour,
        comms_gap_flag,
        read_timestamp,
        business_unit
    FROM silver_smart_meter_reads
    WHERE fuel_type = 'electricity'
),
max_day AS (
    SELECT MAX(DATE(read_timestamp)) AS d FROM reads
),
agg AS (
    SELECT
        account_id,
        AVG(consumption_kwh) AS mean_consumption,
        STDDEV(consumption_kwh) AS std_consumption,
        MIN(consumption_kwh) AS min_consumption,
        MAX(consumption_kwh) AS max_consumption,
        AVG(CASE WHEN hour BETWEEN 7 AND 9 THEN consumption_kwh END) AS morning_avg,
        AVG(CASE WHEN hour BETWEEN 17 AND 21 THEN consumption_kwh END) AS evening_avg,
        AVG(CAST(comms_gap_flag AS INT)) AS comms_gap_rate,
        FIRST(business_unit) AS business_unit
    FROM reads
    GROUP BY account_id
),
daily AS (
    SELECT
        account_id,
        DATE(read_timestamp) AS day,
        AVG(consumption_kwh) AS daily_avg
    FROM reads
    GROUP BY account_id, DATE(read_timestamp)
),
last_7 AS (
    SELECT d.account_id, AVG(d.daily_avg) AS recent_avg
    FROM daily d
    CROSS JOIN max_day m
    WHERE d.day >= date_sub(m.d, 7)
    GROUP BY d.account_id
),
prior_7 AS (
    SELECT d.account_id, AVG(d.daily_avg) AS prior_avg
    FROM daily d
    CROSS JOIN max_day m
    WHERE d.day >= date_sub(m.d, 14) AND d.day < date_sub(m.d, 7)
    GROUP BY d.account_id
),
drop_pct AS (
    SELECT
        a.account_id,
        CASE
            WHEN p.prior_avg IS NULL OR p.prior_avg = 0 THEN 0
            ELSE (p.prior_avg - COALESCE(l.recent_avg, 0)) / p.prior_avg * 100
        END AS consumption_drop_pct
    FROM agg a
    LEFT JOIN last_7 l ON a.account_id = l.account_id
    LEFT JOIN prior_7 p ON a.account_id = p.account_id
)
SELECT
    a.account_id,
    a.mean_consumption,
    COALESCE(a.std_consumption, 0) AS std_consumption,
    a.min_consumption,
    a.max_consumption,
    CASE
        WHEN a.evening_avg IS NULL OR a.evening_avg = 0 THEN 1.0
        ELSE COALESCE(a.morning_avg, 0) / a.evening_avg
    END AS morning_evening_ratio,
    COALESCE(a.comms_gap_rate, 0) AS comms_gap_rate,
    COALESCE(d.consumption_drop_pct, 0) AS consumption_drop_pct,
    a.business_unit
FROM agg a
LEFT JOIN drop_pct d ON a.account_id = d.account_id
WHERE a.mean_consumption IS NOT NULL;


-- ---------------------------------------------------------------------------
-- GOLD — Business aggregates for dashboards, Genie, and KPIs
-- ---------------------------------------------------------------------------

CREATE OR REFRESH MATERIALIZED VIEW gold_daily_consumption (
  CONSTRAINT positive_daily_kwh EXPECT (daily_kwh > 0),
  CONSTRAINT valid_read_date    EXPECT (read_date <= current_date()),
  CONSTRAINT has_business_unit  EXPECT (business_unit IS NOT NULL)
)
CLUSTER BY (account_id, read_date)
AS
SELECT
    account_id,
    DATE(read_timestamp) AS read_date,
    fuel_type,
    SUM(consumption_kwh) AS daily_kwh,
    business_unit
FROM silver_smart_meter_reads
GROUP BY account_id, DATE(read_timestamp), fuel_type, business_unit;

CREATE OR REFRESH MATERIALIZED VIEW gold_postcode_cohort_daily (
  CONSTRAINT has_postcode EXPECT (postcode IS NOT NULL),
  CONSTRAINT valid_read_date EXPECT (read_date <= current_date())
)
CLUSTER BY (postcode, fuel_type, read_date)
AS
SELECT
    pr.postcode,
    g.fuel_type,
    g.read_date,
    AVG(g.daily_kwh) AS cohort_avg_kwh,
    COUNT(DISTINCT g.account_id) AS account_count
FROM gold_daily_consumption g
JOIN property_reference pr ON g.account_id = pr.account_id
GROUP BY pr.postcode, g.fuel_type, g.read_date;
