# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Cleanse — DEPRECATED
# MAGIC
# MAGIC Silver-layer views have been migrated to the **Spark Declarative Pipeline**
# MAGIC (`energy_theft_medallion`).  The SDP creates these as materialized views:
# MAGIC
# MAGIC | Materialized View | Description |
# MAGIC |-------------------|-------------|
# MAGIC | `silver_smart_meter_reads` | Smart-meter reads, missing quality filtered |
# MAGIC | `silver_property_reference` | Validated postcodes, non-null fields |
# MAGIC | `silver_account_features` | ML feature vectors (moved from gold) |
# MAGIC
# MAGIC This notebook is retained for reference only.  It is no longer called by
# MAGIC the `energy-theft-data-generation` job.

# COMMAND ----------

print("This notebook has been superseded by the energy_theft_medallion SDP pipeline.")
print("See pipelines/energy_theft_medallion.sql for the silver layer definitions.")
