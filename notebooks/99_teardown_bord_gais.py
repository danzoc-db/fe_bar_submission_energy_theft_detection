# Databricks notebook source
# MAGIC %md
# MAGIC # Bord Gáis Energy — Teardown
# MAGIC
# MAGIC Removes all Bord Gáis Energy data from the schema, leaving British Gas intact.
# MAGIC Run after the demo to clean up.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Removing bord_gais data from {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delete BGE rows from bronze tables

# COMMAND ----------

tables = ["smart_meter_reads", "meters", "property_reference", "_ground_truth_labels"]

for table in tables:
    before = spark.sql(f"SELECT COUNT(*) AS c FROM {table} WHERE business_unit = 'bord_gais'").collect()[0]["c"]
    if before > 0:
        spark.sql(f"DELETE FROM {table} WHERE business_unit = 'bord_gais'")
        print(f"  ✓ {table}: deleted {before:,} bord_gais rows")
    else:
        print(f"  – {table}: no bord_gais rows found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rebuild gold tables (BGE data removed via silver views)

# COMMAND ----------

print("Rebuilding gold_daily_consumption...")
spark.sql("""
CREATE OR REPLACE TABLE gold_daily_consumption AS
SELECT
    account_id,
    DATE(read_timestamp) AS read_date,
    fuel_type,
    SUM(consumption_kwh) AS daily_kwh,
    business_unit
FROM silver_smart_meter_reads
GROUP BY account_id, DATE(read_timestamp), fuel_type, business_unit
""")
print(f"  gold_daily_consumption: {spark.table('gold_daily_consumption').count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

for table in tables + ["gold_daily_consumption", "gold_account_features"]:
    bus = spark.sql(f"SELECT DISTINCT business_unit FROM {table}").collect()
    units = [r["business_unit"] for r in bus]
    bge_count = spark.sql(f"SELECT COUNT(*) AS c FROM {table} WHERE business_unit = 'bord_gais'").collect()[0]["c"]
    total = spark.sql(f"SELECT COUNT(*) AS c FROM {table}").collect()[0]["c"]
    print(f"  {table}: {total:,} rows, units={units}, bord_gais={bge_count}")

print("\nTeardown complete. Only british_gas data remains.")
