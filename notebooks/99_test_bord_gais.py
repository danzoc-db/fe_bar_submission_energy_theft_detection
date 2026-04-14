# Databricks notebook source
# MAGIC %md
# MAGIC # Bord Gáis Energy — Validation Tests
# MAGIC
# MAGIC Run after Genie Code has generated and executed the BGE bronze ingest notebook.
# MAGIC Validates that Irish data landed correctly and coexists with UKI Gas data.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

errors = []

def check(name, condition, msg):
    if not condition:
        errors.append(f"FAIL: {name} — {msg}")
        print(f"  ✗ {name}: {msg}")
    else:
        print(f"  ✓ {name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Business unit presence

# COMMAND ----------

for table in ["property_reference", "meters", "smart_meter_reads", "_ground_truth_labels"]:
    bus = [r["business_unit"] for r in spark.sql(f"SELECT DISTINCT business_unit FROM {table}").collect()]
    check(f"{table}_has_uki_gas", "uki_gas" in bus, f"Missing uki_gas in {table}")
    check(f"{table}_has_bord_gais", "bord_gais" in bus, f"Missing bord_gais in {table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Row counts

# COMMAND ----------

bg_props = spark.sql("SELECT COUNT(*) AS c FROM property_reference WHERE business_unit = 'uki_gas'").collect()[0]["c"]
bge_props = spark.sql("SELECT COUNT(*) AS c FROM property_reference WHERE business_unit = 'bord_gais'").collect()[0]["c"]
check("bg_property_count", bg_props == 2000, f"Expected 2000, got {bg_props}")
check("bge_property_count", bge_props == 500, f"Expected 500, got {bge_props}")
print(f"  property_reference: BG={bg_props}, BGE={bge_props}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Irish Eircode format

# COMMAND ----------

bge_postcodes = spark.sql("""
    SELECT DISTINCT LEFT(postcode, 3) AS prefix
    FROM property_reference
    WHERE business_unit = 'bord_gais'
""").collect()
prefixes = [r["prefix"] for r in bge_postcodes]
irish_prefixes = {"D01", "D02", "D04", "D06", "D08", "D12", "D14", "D16", "D18", "D24",
                  "T12", "T23", "T45", "H91", "V94", "X91", "V92", "V93", "Y35",
                  "F94", "F26", "F28", "F91", "A91", "A92"}
has_irish = any(p in irish_prefixes for p in prefixes)
check("eircode_prefixes", has_irish, f"No Irish Eircode prefixes found. Got: {prefixes[:10]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Silver views include BGE data

# COMMAND ----------

silver_bus = [r["business_unit"] for r in spark.sql("SELECT DISTINCT business_unit FROM silver_smart_meter_reads").collect()]
check("silver_includes_bge", "bord_gais" in silver_bus, f"silver_smart_meter_reads missing bord_gais. Got: {silver_bus}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Gold tables include BGE data

# COMMAND ----------

gold_bus = [r["business_unit"] for r in spark.sql("SELECT DISTINCT business_unit FROM gold_daily_consumption").collect()]
check("gold_daily_includes_bge", "bord_gais" in gold_bus, f"gold_daily_consumption missing bord_gais. Got: {gold_bus}")

gold_feat_bus = [r["business_unit"] for r in spark.sql("SELECT DISTINCT business_unit FROM gold_account_features").collect()]
check("gold_features_includes_bge", "bord_gais" in gold_feat_bus, f"gold_account_features missing bord_gais. Got: {gold_feat_bus}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

if errors:
    print(f"\n{'='*60}")
    print(f"  {len(errors)} FAILURES:")
    for e in errors:
        print(f"    {e}")
    print(f"{'='*60}")
    raise AssertionError(f"{len(errors)} validation checks failed")
else:
    print(f"\n{'='*60}")
    print("  ALL CHECKS PASSED ✓")
    print(f"{'='*60}")
