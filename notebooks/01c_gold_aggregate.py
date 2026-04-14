# Databricks notebook source
# MAGIC %md
# MAGIC # Model Performance Log — Historical Narrative Data
# MAGIC
# MAGIC Generates the synthetic 24-month model performance log that drives the
# MAGIC Investigation Outcomes chart on the executive dashboard.
# MAGIC
# MAGIC **Note**: Bronze/silver/gold table creation has moved to the Spark Declarative
# MAGIC Pipeline (`energy_theft_medallion`).  This notebook only creates the
# MAGIC `model_performance_log` table which is synthetic narrative data, not a
# MAGIC transformation of meter reads.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Building model_performance_log in {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model Performance Log (Historical)
# MAGIC
# MAGIC 24 months (April 2024 – March 2026).
# MAGIC - Pre-Oct 2025 (`manual_v1`): very low volume manual investigations
# MAGIC - Oct 2025+ (`if_v1_lstm_v1`): ML model deployed — dramatic step change
# MAGIC
# MAGIC **Narrative**: Pre-ML the team manually flagged a handful of accounts per
# MAGIC month with a ~15-22% hit rate.  After ML deployment the model flags
# MAGIC hundreds of HIGH-risk accounts per month with precision climbing from
# MAGIC ~55% to ~74% by March 2026.

# COMMAND ----------

import random
from datetime import date

random.seed(42)

ML_DEPLOY_OFFSET = 18  # month offset 18 = October 2025

perf_rows = []
for month_offset in range(25):
    m_month = ((4 + month_offset - 1) % 12) + 1
    m_year = 2024 + (4 + month_offset - 1) // 12
    m = date(m_year, m_month, 1)

    is_ml = month_offset >= ML_DEPLOY_OFFSET
    version = "if_v1_lstm_v1" if is_ml else "manual_v1"
    ml_months_elapsed = month_offset - ML_DEPLOY_OFFSET if is_ml else 0

    for tier in ["HIGH", "MEDIUM"]:
        if is_ml:
            if tier == "HIGH":
                base_scored = 180 + ml_months_elapsed * 76
                scored = random.randint(int(base_scored * 0.92), int(base_scored * 1.08))
                base_precision = 55.0 + ml_months_elapsed * 4.2
                precision = round(base_precision + random.uniform(-1.0, 1.0), 1)
            else:
                base_scored = 300 + ml_months_elapsed * 60
                scored = random.randint(int(base_scored * 0.90), int(base_scored * 1.10))
                precision = round(35.0 + ml_months_elapsed * 2.0 + random.uniform(-2, 2), 1)
        else:
            if tier == "HIGH":
                scored = random.randint(8, 25)
                precision = round(15.0 + random.uniform(-3, 7), 1)
            else:
                scored = random.randint(15, 50)
                precision = round(8.0 + random.uniform(-2, 4), 1)

        precision = max(5.0, min(95.0, precision))
        confirmed = max(0, int(scored * precision / 100))
        recall = round(random.uniform(35, 65) + (20 if is_ml else 0), 1)
        recall = min(95.0, recall)
        f1 = round(2 * precision * recall / (precision + recall + 0.01), 1)
        perf_rows.append((m, version, tier, precision, recall, f1, scored, confirmed))

df_perf = spark.createDataFrame(
    perf_rows,
    "month DATE, model_version STRING, risk_tier STRING, precision_pct DOUBLE, recall_pct DOUBLE, f1_score DOUBLE, cases_scored INT, cases_confirmed INT"
)
df_perf.write.mode("overwrite").saveAsTable("model_performance_log")
print(f"model_performance_log: {df_perf.count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

count = spark.table("model_performance_log").count()
print(f"  model_performance_log: {count:,} rows")
print("\nNext: ML training pipeline reads from silver_account_features and gold_daily_consumption (SDP).")
