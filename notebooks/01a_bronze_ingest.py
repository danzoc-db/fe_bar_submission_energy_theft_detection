# Databricks notebook source
# MAGIC %md
# MAGIC # Seed Raw Data — UKI Gas Synthetic Data to Volume
# MAGIC
# MAGIC Generates realistic smart meter data for UKI Gas and writes raw **parquet
# MAGIC files** to a UC Volume.  The Spark Declarative Pipeline (`energy_theft_medallion`)
# MAGIC ingests from this volume via Auto Loader into bronze streaming tables.
# MAGIC
# MAGIC **Output (raw parquet in Volume):**
# MAGIC
# MAGIC | Path | Rows | Description |
# MAGIC |------|------|-------------|
# MAGIC | `raw_data/property_reference/` | 2,000 | Customer premises data |
# MAGIC | `raw_data/meters/` | 4,000 | Meter asset register (2 per account) |
# MAGIC | `raw_data/smart_meter_reads/` | ~2,880,000 | Half-hourly consumption |
# MAGIC | `raw_data/ground_truth/` | 2,000 | Known tampered/normal for evaluation |
# MAGIC
# MAGIC All files include `business_unit` column for multi-entity support.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
BUSINESS_UNIT = "uki_gas"
NUM_ACCOUNTS = 2_000
TAMPERED_PCT = 0.03
EDGE_CASE_PCT = 0.02
DAYS_OF_READS = 90
SAMPLE_FACTOR = 6  # every 6th half-hour = 8 reads per day per fuel
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")
dbutils.fs.rm(VOLUME_PATH, recurse=True)
print(f"Volume: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Property Reference

# COMMAND ----------

import random
from datetime import date, datetime, timedelta

random.seed(42)

POSTCODE_COORDS = {
    "E1": (51.515, -0.056), "EC1": (51.523, -0.110), "N1": (51.540, -0.100),
    "NW1": (51.534, -0.145), "SE1": (51.500, -0.085), "SW1": (51.498, -0.142),
    "W1": (51.514, -0.150), "WC1": (51.521, -0.118),
    "BN1": (50.842, -0.131), "GU1": (51.236, -0.574), "ME1": (51.393, 0.539),
    "OX1": (51.752, -1.258), "RG1": (51.454, -0.973), "SL1": (51.510, -0.595),
    "BA1": (51.381, -2.360), "BS1": (51.454, -2.588), "EX1": (50.724, -3.534),
    "GL1": (51.864, -2.244), "PL1": (50.371, -4.142),
    "CB1": (52.205, 0.121), "CM1": (51.736, 0.470), "CO1": (51.889, 0.901),
    "IP1": (52.056, 1.155), "NR1": (52.629, 1.298),
    "B1": (52.480, -1.898), "CV1": (52.408, -1.510), "DY1": (52.509, -2.087),
    "WS1": (52.585, -1.976), "WV1": (52.585, -2.133),
    "DE1": (52.922, -1.476), "LE1": (52.634, -1.131), "LN1": (53.234, -0.540),
    "NG1": (52.953, -1.150), "NN1": (52.240, -0.891),
    "L1": (53.405, -2.978), "M1": (53.480, -2.237), "OL1": (53.541, -2.097),
    "PR1": (53.763, -2.707), "WA1": (53.390, -2.597),
    "DH1": (54.776, -1.576), "DL1": (54.524, -1.556), "NE1": (54.970, -1.614),
    "SR1": (54.906, -1.381), "TS1": (54.574, -1.235),
    "BD1": (53.795, -1.752), "DN1": (53.523, -1.133), "HD1": (53.645, -1.785),
    "HU1": (53.745, -0.337), "LS1": (53.800, -1.548), "S1": (53.381, -1.470),
    "CF1": (51.481, -3.179), "LD1": (52.248, -3.381), "LL1": (53.280, -3.828),
    "NP1": (51.588, -2.999), "SA1": (51.621, -3.943),
    "AB1": (57.150, -2.094), "DD1": (56.462, -2.970), "EH1": (55.949, -3.191),
    "FK1": (56.117, -3.936), "G1": (55.860, -4.251), "KY1": (56.112, -3.161),
}
FALLBACK_COORDS = (51.507, -0.128)

UK_REGIONS = [
    "London", "South East", "South West", "East of England",
    "West Midlands", "East Midlands", "North West", "North East",
    "Yorkshire and the Humber", "Wales", "Scotland",
]
REGION_WEIGHTS = [0.18, 0.14, 0.09, 0.10, 0.10, 0.08, 0.12, 0.05, 0.08, 0.03, 0.03]
PROPERTY_TYPES = ["terraced", "semi-detached", "detached", "flat", "bungalow"]
PROPERTY_WEIGHTS = [0.28, 0.26, 0.18, 0.22, 0.06]
CTB = ["A", "B", "C", "D", "E", "F", "G", "H"]
CTB_WEIGHTS = [0.10, 0.15, 0.22, 0.20, 0.15, 0.10, 0.05, 0.03]
EPC_RATINGS = ["A", "B", "C", "D", "E", "F", "G"]
EPC_WEIGHTS = [0.02, 0.10, 0.25, 0.35, 0.18, 0.08, 0.02]

POSTCODE_PREFIXES = {
    "London": ["E1", "EC1", "N1", "NW1", "SE1", "SW1", "W1", "WC1"],
    "South East": ["BN1", "GU1", "ME1", "OX1", "RG1", "SL1"],
    "South West": ["BA1", "BS1", "EX1", "GL1", "PL1"],
    "East of England": ["CB1", "CM1", "CO1", "IP1", "NR1"],
    "West Midlands": ["B1", "CV1", "DY1", "WS1", "WV1"],
    "East Midlands": ["DE1", "LE1", "LN1", "NG1", "NN1"],
    "North West": ["L1", "M1", "OL1", "PR1", "WA1"],
    "North East": ["DH1", "DL1", "NE1", "SR1", "TS1"],
    "Yorkshire and the Humber": ["BD1", "DN1", "HD1", "HU1", "LS1", "S1"],
    "Wales": ["CF1", "LD1", "LL1", "NP1", "SA1"],
    "Scotland": ["AB1", "DD1", "EH1", "FK1", "G1", "KY1"],
}

property_rows = []
for i in range(NUM_ACCOUNTS):
    region = random.choices(UK_REGIONS, weights=REGION_WEIGHTS, k=1)[0]
    prefix = random.choice(POSTCODE_PREFIXES[region])
    postcode = f"{prefix} {random.randint(1, 9)}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}"
    prop_type = random.choices(PROPERTY_TYPES, weights=PROPERTY_WEIGHTS, k=1)[0]
    ctb = random.choices(CTB, weights=CTB_WEIGHTS, k=1)[0]
    epc = random.choices(EPC_RATINGS, weights=EPC_WEIGHTS, k=1)[0]
    floor_area = max(25.0, round(random.gauss(85, 25), 1))
    lat, lon = POSTCODE_COORDS.get(prefix, FALLBACK_COORDS)
    lat += random.uniform(-0.01, 0.01)
    lon += random.uniform(-0.01, 0.01)
    property_rows.append((f"UKI-{i:07d}", postcode, region, prop_type, ctb, floor_area, epc, round(lat, 6), round(lon, 6), BUSINESS_UNIT))

df_properties = spark.createDataFrame(
    property_rows,
    "account_id STRING, postcode STRING, region STRING, property_type STRING, council_tax_band STRING, floor_area_m2 DOUBLE, epc_rating STRING, latitude DOUBLE, longitude DOUBLE, business_unit STRING"
)
df_properties.write.mode("overwrite").parquet(f"{VOLUME_PATH}/property_reference")
print(f"property_reference: {df_properties.count():,} rows → {VOLUME_PATH}/property_reference")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Meters (2 per account)

# COMMAND ----------

meter_rows = []
for i in range(NUM_ACCOUNTS):
    aid = f"UKI-{i:07d}"
    for j, fuel in enumerate(["electricity", "gas"]):
        meter_rows.append((
            f"MTR-{i:07d}-{j}",
            aid,
            str(1000000000000 + i * 2 + j),
            f"E6S{random.randint(10000000, 99999999)}",
            fuel,
            random.choices(["smart", "traditional", "prepayment"], weights=[0.70, 0.20, 0.10], k=1)[0],
            date(2020, 1, 1) + timedelta(days=random.randint(0, 1800)),
            datetime(2026, 3, 17, 0, 0, 0),
            BUSINESS_UNIT,
        ))

df_meters = spark.createDataFrame(
    meter_rows,
    "meter_id STRING, account_id STRING, mpan STRING, meter_serial_number STRING, fuel_type STRING, meter_type STRING, install_date DATE, last_read_timestamp TIMESTAMP, business_unit STRING"
)
df_meters.write.mode("overwrite").parquet(f"{VOLUME_PATH}/meters")
print(f"meters: {df_meters.count():,} rows → {VOLUME_PATH}/meters")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Smart Meter Reads
# MAGIC
# MAGIC 2K accounts x 90 days x 8 reads/day x 2 fuels = ~2.88M rows
# MAGIC
# MAGIC **Tamper signatures (extreme so real IF/LSTM models flag HIGH):**
# MAGIC - Type A: Sudden step-down (55-95% drop, onset day 10-40)
# MAGIC - Type B: Gradual linear decline over 14-28 days (50-90% final drop)
# MAGIC - Type C: Intermittent (zero/near-zero on ~50% of random days)
# MAGIC - All tampered: elevated comms gap rate (15-30%)

# COMMAND ----------

import numpy as np

np.random.seed(42)

num_tampered = int(NUM_ACCOUNTS * TAMPERED_PCT)
num_edge = int(NUM_ACCOUNTS * EDGE_CASE_PCT)

tampered_ids = set(f"UKI-{i:07d}" for i in random.sample(range(NUM_ACCOUNTS), num_tampered))
edge_ids = set(f"UKI-{i:07d}" for i in random.sample(range(NUM_ACCOUNTS), num_edge)) - tampered_ids

tamper_types = {}
recent_tamper_ids = set()
tampered_list = list(tampered_ids)
random.shuffle(tampered_list)
num_recent = max(10, len(tampered_list) // 5)
for i, aid in enumerate(tampered_list):
    if i < num_recent:
        tamper_types[aid] = random.choice(["A", "B"])
        recent_tamper_ids.add(aid)
    else:
        tamper_types[aid] = random.choice(["A", "B", "C"])

prop_lookup = {r[0]: (r[1], r[2], r[3], r[4]) for r in property_rows}

start_date = datetime(2025, 12, 18, 0, 0, 0)  # 90 days before 2026-03-17
BATCH_SIZE = 500

print(f"Generating reads for {NUM_ACCOUNTS:,} accounts ({DAYS_OF_READS} days, sample every {SAMPLE_FACTOR}th half-hour)...")
print(f"Tampered: {num_tampered} (types A/B/C), Edge: {num_edge}")

for batch_start in range(0, NUM_ACCOUNTS, BATCH_SIZE):
    batch_end = min(batch_start + BATCH_SIZE, NUM_ACCOUNTS)
    batch_reads = []

    for i in range(batch_start, batch_end):
        aid = f"UKI-{i:07d}"
        postcode, region, prop_type, ctb = prop_lookup[aid]
        is_tampered = aid in tampered_ids
        is_edge = aid in edge_ids
        tamper_type = tamper_types.get(aid, None)

        base_elec = np.random.uniform(0.3, 1.2)
        base_gas = np.random.uniform(0.2, 0.8)
        acct_gap_rate = np.random.uniform(0.15, 0.30) if is_tampered else 0.005

        is_recent_tamper = aid in recent_tamper_ids
        if is_tampered and tamper_type == "A":
            tamper_day = np.random.randint(DAYS_OF_READS - 10, DAYS_OF_READS - 3) if is_recent_tamper else np.random.randint(10, 41)
        else:
            tamper_day = 999
        tamper_drop = np.random.uniform(0.55, 0.95) if is_tampered and tamper_type == "A" else 0
        if is_tampered and tamper_type == "B":
            tamper_b_start = np.random.randint(DAYS_OF_READS - 14, DAYS_OF_READS - 7) if is_recent_tamper else np.random.randint(10, 50)
        else:
            tamper_b_start = 999
        tamper_b_days = np.random.randint(5, 10) if (is_tampered and tamper_type == "B" and is_recent_tamper) else (np.random.randint(14, 29) if is_tampered and tamper_type == "B" else 0)
        tamper_b_drop = np.random.uniform(0.50, 0.90) if is_tampered and tamper_type == "B" else 0
        tamper_c_zero_days = set(np.random.choice(range(DAYS_OF_READS), size=int(DAYS_OF_READS * np.random.uniform(0.45, 0.60)), replace=False)) if is_tampered and tamper_type == "C" else set()

        edge_day = np.random.randint(10, 25) if is_edge else 999
        edge_drop = np.random.uniform(0.15, 0.30) if is_edge else 0

        for day in range(DAYS_OF_READS):
            ts_base = start_date + timedelta(days=day)
            doy = ts_base.timetuple().tm_yday

            for hh in range(0, 48, SAMPLE_FACTOR):
                ts = ts_base + timedelta(minutes=hh * 30)
                hour = ts.hour + ts.minute / 60.0
                daily = 1.4 if (7 <= hour <= 9 or 17 <= hour <= 21) else (0.4 if hour <= 5 else 0.8)

                for fuel, base in [("electricity", base_elec), ("gas", base_gas)]:
                    if fuel == "gas":
                        seasonal = 0.6 + 0.9 * (1 + np.cos(2 * np.pi * (doy - 15) / 365)) / 2
                    else:
                        seasonal = 1.0 + 0.1 * np.cos(2 * np.pi * (doy - 200) / 365)

                    kwh = base * seasonal * daily + np.random.normal(0, 0.08 * base)

                    if is_tampered:
                        if tamper_type == "A" and day >= tamper_day:
                            kwh *= (1 - tamper_drop)
                        elif tamper_type == "B":
                            if day >= tamper_b_start + tamper_b_days:
                                kwh *= (1 - tamper_b_drop)
                            elif day >= tamper_b_start:
                                frac = (day - tamper_b_start) / tamper_b_days
                                kwh *= (1 - tamper_b_drop * frac)
                        elif tamper_type == "C" and day in tamper_c_zero_days:
                            kwh *= np.random.uniform(0, 0.05)
                    elif is_edge and day >= edge_day:
                        kwh *= (1 - edge_drop)

                    kwh = max(0.01, kwh)
                    is_gap = np.random.random() < acct_gap_rate
                    quality = "missing" if is_gap else ("estimated" if np.random.random() < 0.02 else "actual")
                    kwh_val = None if np.random.random() < 0.03 else round(float(kwh), 4)
                    batch_reads.append((aid, ts, fuel, kwh_val, quality, bool(is_gap), postcode, prop_type, ctb, BUSINESS_UNIT))

    df_batch = spark.createDataFrame(
        batch_reads,
        "account_id STRING, read_timestamp TIMESTAMP, fuel_type STRING, consumption_kwh DOUBLE, read_quality STRING, comms_gap_flag BOOLEAN, postcode STRING, property_type STRING, council_tax_band STRING, business_unit STRING"
    )
    df_batch.write.mode("append").parquet(f"{VOLUME_PATH}/smart_meter_reads")

    if (batch_start // BATCH_SIZE) % 4 == 0:
        print(f"  Batch {batch_start}-{batch_end}: {len(batch_reads):,} rows written")

read_count = spark.read.parquet(f"{VOLUME_PATH}/smart_meter_reads").count()
print(f"smart_meter_reads: {read_count:,} rows → {VOLUME_PATH}/smart_meter_reads")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Ground Truth Labels

# COMMAND ----------

gt_rows = []
for i in range(NUM_ACCOUNTS):
    aid = f"UKI-{i:07d}"
    if aid in tampered_ids:
        gt_rows.append((aid, True, tamper_types[aid], BUSINESS_UNIT))
    elif aid in edge_ids:
        gt_rows.append((aid, False, "edge", BUSINESS_UNIT))
    else:
        gt_rows.append((aid, False, "normal", BUSINESS_UNIT))

df_gt = spark.createDataFrame(
    gt_rows,
    "account_id STRING, is_tampered BOOLEAN, label_type STRING, business_unit STRING"
)
df_gt.write.mode("overwrite").parquet(f"{VOLUME_PATH}/ground_truth")
print(f"_ground_truth_labels: {df_gt.count():,} rows → {VOLUME_PATH}/ground_truth  (tampered={sum(1 for r in gt_rows if r[1])})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Data Quality Test Records
# MAGIC
# MAGIC Inject deliberate error records so SDP pipeline expectations fire visibly
# MAGIC in the Pipeline UI "Data quality" tab.
# MAGIC
# MAGIC | Layer | Expectation | Action | Source |
# MAGIC |-------|------------|--------|--------|
# MAGIC | Bronze | `non_null_consumption` | **DROP** | ~3% of reads have null `consumption_kwh` |
# MAGIC | Silver | `valid_read_timestamp` | **DROP** | Future-dated reads below |
# MAGIC | Silver | `valid_fuel_type` | **DROP** | Invalid fuel types below |
# MAGIC | Silver | `valid_uk_postcode` | **DROP** | Invalid postcodes in error properties |
# MAGIC | Silver | `positive_consumption` | ALLOW | Negative consumption below |
# MAGIC | Silver | `known_region` | ALLOW | Unknown regions in error properties |
# MAGIC | Gold | `has_business_unit` | ALLOW | Null business_unit below |

# COMMAND ----------

from datetime import datetime, timedelta

now = datetime.now()
base_ts = datetime(2026, 2, 15, 10, 0, 0)

error_reads = [
    # Negative consumption (4 records) — triggers: positive_consumption
    ("UKI-0001990", base_ts,                          "electricity", -0.50, "actual", False, "E1 4PA", "flat",           "C", BUSINESS_UNIT),
    ("UKI-0001991", base_ts + timedelta(hours=1),     "gas",         -1.20, "actual", False, "M1 3AB", "terraced",      "B", BUSINESS_UNIT),
    ("UKI-0001992", base_ts + timedelta(hours=2),     "electricity", -0.80, "actual", False, "LS1 5DL","semi-detached", "D", BUSINESS_UNIT),
    ("UKI-0001993", base_ts + timedelta(hours=3),     "gas",         -2.30, "actual", False, "BS1 2HR","detached",      "E", BUSINESS_UNIT),
    # Future-dated reads (4 records) — triggers: valid_read_timestamp
    ("UKI-0001994", now + timedelta(days=30),         "electricity",  0.85, "actual", False, "N1 7GU", "flat",           "C", BUSINESS_UNIT),
    ("UKI-0001995", now + timedelta(days=60),         "gas",          0.42, "actual", False, "SE1 1JA","terraced",      "B", BUSINESS_UNIT),
    ("UKI-0001996", now + timedelta(days=90),         "electricity",  1.10, "actual", False, "W1 2PF", "detached",      "F", BUSINESS_UNIT),
    ("UKI-0001997", now + timedelta(days=180),        "gas",          0.65, "actual", False, "CB1 3JS","semi-detached", "D", BUSINESS_UNIT),
    # Invalid fuel type (2 records) — triggers: valid_fuel_type
    ("UKI-0001990", base_ts + timedelta(hours=4),     "solar",        0.90, "actual", False, "E1 4PA", "flat",           "C", BUSINESS_UNIT),
    ("UKI-0001991", base_ts + timedelta(hours=5),     "hydrogen",     0.55, "actual", False, "M1 3AB", "terraced",      "B", BUSINESS_UNIT),
    # Null business unit (2 records) — triggers: has_business_unit in gold
    ("UKI-0001992", base_ts + timedelta(hours=6),     "electricity",  0.70, "actual", False, "LS1 5DL","semi-detached", "D", None),
    ("UKI-0001993", base_ts + timedelta(hours=7),     "gas",          0.45, "actual", False, "BS1 2HR","detached",      "E", None),
]

df_error_reads = spark.createDataFrame(
    error_reads,
    "account_id STRING, read_timestamp TIMESTAMP, fuel_type STRING, consumption_kwh DOUBLE, read_quality STRING, comms_gap_flag BOOLEAN, postcode STRING, property_type STRING, council_tax_band STRING, business_unit STRING"
)
df_error_reads.write.mode("append").parquet(f"{VOLUME_PATH}/smart_meter_reads")
print(f"Appended {len(error_reads)} error records to smart_meter_reads")

error_properties = [
    # Invalid postcode format (3 records) — triggers: valid_uk_postcode
    ("UKI-ERR-0001", "INVALID",  "London",    "flat",      "C", 65.0, "D", 51.51, -0.08, BUSINESS_UNIT),
    ("UKI-ERR-0002", "123",      "Scotland",  "terraced",  "B", 80.0, "C", 55.95, -3.19, BUSINESS_UNIT),
    ("UKI-ERR-0003", "XX 00Z",   "Wales",     "detached",  "E", 95.0, "E", 51.48, -3.18, BUSINESS_UNIT),
    # Unknown region (3 records) — triggers: known_region
    ("UKI-ERR-0004", "SW1 1AA",  "Atlantis",  "flat",      "D", 70.0, "C", 51.50, -0.14, BUSINESS_UNIT),
    ("UKI-ERR-0005", "NE1 2BN",  "Narnia",    "terraced",  "B", 85.0, "D", 54.97, -1.61, BUSINESS_UNIT),
    ("UKI-ERR-0006", "GU1 3EH",  "Channel Islands", "semi-detached", "C", 78.0, "C", 49.45, -2.54, BUSINESS_UNIT),
]

df_error_props = spark.createDataFrame(
    error_properties,
    "account_id STRING, postcode STRING, region STRING, property_type STRING, council_tax_band STRING, floor_area_m2 DOUBLE, epc_rating STRING, latitude DOUBLE, longitude DOUBLE, business_unit STRING"
)
df_error_props.write.mode("append").parquet(f"{VOLUME_PATH}/property_reference")
print(f"Appended {len(error_properties)} error records to property_reference")
print(f"Total error records: {len(error_reads) + len(error_properties)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

for name in ["property_reference", "meters", "smart_meter_reads", "ground_truth"]:
    count = spark.read.parquet(f"{VOLUME_PATH}/{name}").count()
    print(f"  {name}: {count:,} rows")

print(f"\nRaw data seeded to Volume for business_unit='{BUSINESS_UNIT}'.")
print("Next: SDP pipeline (energy_theft_medallion) ingests from this Volume.")
