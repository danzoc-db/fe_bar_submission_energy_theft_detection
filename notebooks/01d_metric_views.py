# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — UC Metric Views
# MAGIC
# MAGIC Creates **governed metric views** attached to the Genie Space so Susie can ask
# MAGIC natural language questions grounded in certified, business-owned formulas.
# MAGIC
# MAGIC | Metric View | Source | Purpose |
# MAGIC |-------------|--------|---------|
# MAGIC | `theft_detection_metrics` | `investigation_cases` | Revenue recovery, precision rate, case outcomes |
# MAGIC | `risk_exposure_metrics` | `anomaly_scores` | Estate risk profile, HIGH-risk %, postcode hotspots |
# MAGIC
# MAGIC Both views are **materialised** on a 6-hour schedule for fast retrieval.
# MAGIC
# MAGIC Run *after* `04_batch_scoring.py` has populated `anomaly_scores` and
# MAGIC `investigation_cases`.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Creating metric views in {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Theft Detection Metrics
# MAGIC
# MAGIC All investigation KPIs in a single metric view — revenue recovery, confirmed
# MAGIC theft count, precision rate, and average recovery per case. No filter applied
# MAGIC so Genie can slice freely by month and region.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.theft_detection_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Governed theft detection KPIs for Genie and executive dashboards"
  source: {CATALOG}.{SCHEMA}.investigation_cases
  dimensions:
    - name: Month
      expr: "DATE_TRUNC('MONTH', closed_timestamp)"
      comment: "Month of case closure"
    - name: Region
      expr: region
      comment: "Geographic region"
  measures:
    - name: Revenue Recovered
      expr: SUM(revenue_recovered_gbp)
      comment: "Total revenue recovered from back-billing confirmed theft cases"
    - name: Confirmed Theft Cases
      expr: COUNT_IF(outcome = 'THEFT_CONFIRMED')
      comment: "Cases confirmed as energy theft after field investigation"
    - name: Total Closed Cases
      expr: "COUNT_IF(outcome IN ('THEFT_CONFIRMED', 'FALSE_POSITIVE'))"
      comment: "Total cases closed (confirmed plus false positive)"
    - name: Detection Precision Rate
      expr: "COUNT_IF(outcome = 'THEFT_CONFIRMED') * 100.0 / NULLIF(COUNT_IF(outcome IN ('THEFT_CONFIRMED', 'FALSE_POSITIVE')), 0)"
      comment: "Confirmed theft divided by total closed. Target above 60%"
    - name: Avg Recovery Per Case
      expr: "ROUND(SUM(revenue_recovered_gbp) / NULLIF(COUNT_IF(outcome = 'THEFT_CONFIRMED'), 0), 2)"
      comment: "Average revenue recovered per confirmed theft case"
  materialization:
    schedule: every 6 hours
    mode: relaxed
    materialized_views:
      - name: baseline
        type: unaggregated
      - name: monthly_kpis
        type: aggregated
        dimensions:
          - Month
        measures:
          - Revenue Recovered
          - Confirmed Theft Cases
          - Total Closed Cases
          - Detection Precision Rate
          - Avg Recovery Per Case
      - name: monthly_regional_kpis
        type: aggregated
        dimensions:
          - Month
          - Region
        measures:
          - Revenue Recovered
          - Confirmed Theft Cases
          - Total Closed Cases
          - Detection Precision Rate
          - Avg Recovery Per Case
$$
""")

print("✓ theft_detection_metrics created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Risk Exposure Metrics
# MAGIC
# MAGIC Estate-wide risk profile from `anomaly_scores`. Answers questions about the
# MAGIC percentage of accounts flagged HIGH, postcode sector hotspots, and fuel-type
# MAGIC breakdowns.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.risk_exposure_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Risk exposure metrics for Genie queries"
  source: {CATALOG}.{SCHEMA}.anomaly_scores
  dimensions:
    - name: Postcode Sector
      expr: postcode_sector
      comment: "UK postcode sector"
    - name: Fuel Type
      expr: fuel_type
      comment: "electricity or gas"
    - name: Risk Tier
      expr: risk_tier
      comment: "HIGH MEDIUM LOW"
  measures:
    - name: HIGH Risk Accounts
      expr: COUNT_IF(risk_tier = 'HIGH')
      comment: "Accounts above HIGH threshold"
    - name: Total Accounts Monitored
      expr: COUNT(DISTINCT account_id)
      comment: "Unique accounts under scoring"
    - name: HIGH Risk Percentage
      expr: "COUNT_IF(risk_tier = 'HIGH') * 100.0 / NULLIF(COUNT(DISTINCT account_id), 0)"
      comment: "Percentage of estate flagged HIGH"
    - name: Average Risk Score
      expr: AVG(composite_risk_score)
      comment: "Mean composite risk score"
  materialization:
    schedule: every 6 hours
    mode: relaxed
    materialized_views:
      - name: baseline
        type: unaggregated
      - name: risk_by_sector
        type: aggregated
        dimensions:
          - Postcode Sector
        measures:
          - HIGH Risk Accounts
          - Total Accounts Monitored
          - HIGH Risk Percentage
          - Average Risk Score
      - name: risk_by_fuel_tier
        type: aggregated
        dimensions:
          - Fuel Type
          - Risk Tier
        measures:
          - HIGH Risk Accounts
          - Total Accounts Monitored
          - Average Risk Score
$$
""")

print("✓ risk_exposure_metrics created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verify Metric Views

# COMMAND ----------

for mv in ["theft_detection_metrics", "risk_exposure_metrics"]:
    info = spark.sql(f"DESCRIBE EXTENDED {CATALOG}.{SCHEMA}.{mv}").collect()
    print(f"\n{'='*60}")
    print(f"  {mv}")
    print(f"{'='*60}")
    for row in info:
        if row["col_name"] and row["col_name"].strip():
            print(f"  {row['col_name']:30s} {row['data_type'] or ''}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Smoke Tests

# COMMAND ----------

print("── Theft Detection KPIs ──")
display(spark.sql(f"""
    SELECT
        `Month`,
        `Region`,
        MEASURE(`Revenue Recovered`) AS revenue_recovered_gbp,
        MEASURE(`Confirmed Theft Cases`) AS confirmed,
        MEASURE(`Total Closed Cases`) AS closed,
        MEASURE(`Detection Precision Rate`) AS precision_rate,
        MEASURE(`Avg Recovery Per Case`) AS avg_recovery
    FROM {CATALOG}.{SCHEMA}.theft_detection_metrics
    GROUP BY ALL
    ORDER BY ALL
"""))

# COMMAND ----------

print("── Risk Exposure ──")
display(spark.sql(f"""
    SELECT
        `Fuel Type`,
        `Risk Tier`,
        MEASURE(`HIGH Risk Accounts`) AS high_risk,
        MEASURE(`Total Accounts Monitored`) AS total_monitored,
        MEASURE(`HIGH Risk Percentage`) AS high_risk_pct,
        MEASURE(`Average Risk Score`) AS avg_score
    FROM {CATALOG}.{SCHEMA}.risk_exposure_metrics
    GROUP BY ALL
    ORDER BY ALL
"""))
