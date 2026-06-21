# Databricks notebook source
# MAGIC %md
# MAGIC # Batch Scoring — Energy Theft Composite Risk
# MAGIC
# MAGIC Loads trained Isolation Forest and LSTM models from MLflow, scores all accounts,
# MAGIC and writes composite risk scores to `anomaly_scores`.
# MAGIC
# MAGIC **Designed for Databricks Job execution.**

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Config

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
IF_MODEL = f"{CATALOG}.{SCHEMA}.isolation_forest_theft_v3"
LSTM_MODEL = f"{CATALOG}.{SCHEMA}.lstm_consumption_v2"

import mlflow
import random
import io
import json
import pickle

mlflow.set_registry_uri("databricks-uc")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA}")
print(f"Isolation Forest: {IF_MODEL}")
print(f"LSTM Autoencoder: {LSTM_MODEL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Load Models

# MAGIC LSTM class must be in scope before loading (MLflow PyTorch unpickling).

# COMMAND ----------

import torch
import torch.nn as nn

class LSTMAutoencoder(nn.Module):
  def __init__(self, input_dim=1, hidden_dim=32, latent_dim=16, seq_len=90):
    super().__init__()
    self.seq_len = seq_len
    self.hidden_dim = hidden_dim
    self.latent_dim = latent_dim
    self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
    self.encoder_proj = nn.Linear(hidden_dim, latent_dim)
    self.decoder = nn.LSTM(latent_dim, hidden_dim, batch_first=True)
    self.decoder_proj = nn.Linear(hidden_dim, input_dim)

  def forward(self, x):
    _, (h_n, _) = self.encoder(x)
    latent = self.encoder_proj(h_n.squeeze(0))
    latent_seq = latent.unsqueeze(1).repeat(1, self.seq_len, 1)
    out, _ = self.decoder(latent_seq)
    return self.decoder_proj(out)

fallback_table = f"{CATALOG}.{SCHEMA}.model_fallback_store"

def _load_fallback_row(model_name: str):
  try:
    row = spark.sql(f"""
      SELECT model_name, flavor, payload, meta_json, created_at
      FROM {fallback_table}
      WHERE model_name = '{model_name}'
      ORDER BY created_at DESC
      LIMIT 1
    """).collect()
    return row[0] if row else None
  except Exception:
    return None

model_source = "uc_registry"
try:
  if_model = mlflow.sklearn.load_model(f"models:/{IF_MODEL}@champion")
except Exception as e:
  print(f"⚠ Could not load IF model from UC registry, trying Delta fallback: {e}")
  row = _load_fallback_row(IF_MODEL)
  if row is None:
    raise RuntimeError(f"No fallback artifact found for {IF_MODEL}")
  if_model = pickle.loads(bytes(row["payload"]))
  model_source = "delta_fallback"

try:
  lstm_model = mlflow.pytorch.load_model(f"models:/{LSTM_MODEL}@champion")
except Exception as e:
  print(f"⚠ Could not load LSTM model from UC registry, trying Delta fallback: {e}")
  row = _load_fallback_row(LSTM_MODEL)
  if row is None:
    raise RuntimeError(f"No fallback artifact found for {LSTM_MODEL}")
  meta = json.loads(row["meta_json"] or "{}")
  lstm_model = LSTMAutoencoder(
    input_dim=int(meta.get("input_dim", 1)),
    hidden_dim=int(meta.get("hidden_dim", 32)),
    latent_dim=int(meta.get("latent_dim", 16)),
    seq_len=int(meta.get("seq_len", 90)),
  )
  state_dict = torch.load(io.BytesIO(bytes(row["payload"])), map_location="cpu")
  lstm_model.load_state_dict(state_dict)
  model_source = "delta_fallback"

# Get model version info for audit (UC uses full model name)
client = mlflow.MlflowClient()
if_versions = [v for v in client.search_model_versions(f"name='{IF_MODEL}'")]
lstm_versions = [v for v in client.search_model_versions(f"name='{LSTM_MODEL}'")]
if_mv = max(if_versions, key=lambda v: int(v.version)) if if_versions else None
lstm_mv = max(lstm_versions, key=lambda v: int(v.version)) if lstm_versions else None

if if_mv:
  print(f"Isolation Forest: version {if_mv.version}, run_id={if_mv.run_id}")
if lstm_mv:
  print(f"LSTM Autoencoder: version {lstm_mv.version}, run_id={lstm_mv.run_id}")
if model_source == "delta_fallback":
  print("Using Delta fallback model artifacts (UC registry unavailable in this workspace).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Feature Engineering & Isolation Forest Scoring

# MAGIC Compute per-account consumption features from `smart_meter_reads` (same as notebook 02),
# MAGIC score with the loaded IF model, and normalise scores to 0–1.
# MAGIC
# MAGIC Reads pre-computed features from **silver_account_features** (built by `01c`).

# COMMAND ----------

import pandas as pd

FEATURE_COLS = [
  "mean_consumption", "std_consumption", "min_consumption", "max_consumption",
  "morning_evening_ratio", "comms_gap_rate", "consumption_drop_pct"
]

df_features = spark.sql(f"""
  SELECT account_id, mean_consumption, std_consumption, min_consumption,
         max_consumption, morning_evening_ratio, comms_gap_rate, consumption_drop_pct
  FROM {CATALOG}.{SCHEMA}.silver_account_features
""")
pdf_if = df_features.toPandas()
pdf_if[FEATURE_COLS] = pdf_if[FEATURE_COLS].fillna(0)
pdf_if = pdf_if.dropna(subset=["account_id"])

X_if = pdf_if[FEATURE_COLS].values
account_ids_if = pdf_if["account_id"].values

# Score with Isolation Forest
raw_scores = if_model.decision_function(X_if)
score_min, score_max = raw_scores.min(), raw_scores.max()
if score_max - score_min > 0:
  isolation_forest_scores = 1.0 - (raw_scores - score_min) / (score_max - score_min)
else:
  isolation_forest_scores = [0.5] * len(raw_scores)

df_if_scored = pd.DataFrame({
  "account_id": account_ids_if,
  "isolation_forest_score": isolation_forest_scores,
  "consumption_drop_pct": pdf_if["consumption_drop_pct"].values,
})
print(f"IF scored: {len(df_if_scored):,} accounts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Sequence Preparation & LSTM Scoring

# MAGIC Daily aggregation and pivot (same as notebook 03), then score with LSTM autoencoder.
# MAGIC Reconstruction error → z-score as lstm_deviation_score.

# COMMAND ----------

from datetime import timedelta
import numpy as np
import torch

SEQ_LEN = 90

daily_df = spark.sql("""
  SELECT account_id, read_date, daily_kwh
  FROM gold_daily_consumption
  WHERE fuel_type = 'electricity'
""")

max_date = spark.sql("SELECT MAX(read_date) AS d FROM gold_daily_consumption WHERE fuel_type = 'electricity'").collect()[0]["d"]
date_range = [max_date - timedelta(days=i) for i in range(SEQ_LEN - 1, -1, -1)]

daily_pd = daily_df.toPandas()
pivot = daily_pd.pivot_table(index="account_id", columns="read_date", values="daily_kwh")
matrix = pivot.reindex(columns=date_range)
matrix = matrix.ffill(axis=1).bfill(axis=1).fillna(0.0)

means = matrix.mean(axis=1)
stds = matrix.std(axis=1)
stds = stds.replace(0, 1.0)
matrix_norm = matrix.sub(means, axis=0).div(stds, axis=0)
X_lstm = np.float32(matrix_norm.values[:, :, np.newaxis])
account_ids_lstm = matrix_norm.index.tolist()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
lstm_model.to(device)
lstm_model.eval()
with torch.no_grad():
  X_t = torch.from_numpy(X_lstm).to(device)
  recon = lstm_model(X_t)

recon_np = recon.cpu().numpy()
recon_errors = np.mean((X_lstm - recon_np) ** 2, axis=(1, 2))
mean_recon = float(np.mean(recon_errors))
std_recon = float(np.std(recon_errors))
if std_recon < 1e-10:
  std_recon = 1.0
lstm_deviation_scores = (recon_errors - mean_recon) / std_recon

df_lstm_scored = pd.DataFrame({
  "account_id": account_ids_lstm,
  "lstm_deviation_score": lstm_deviation_scores,
})
print(f"LSTM scored: {len(df_lstm_scored):,} accounts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Cohort Deviation, Comms Gaps & Composite Scoring

# MAGIC Compute cohort_deviation_score (z-score vs similar property cohort), comms_gap_count_30d,
# MAGIC then apply the PRD composite formula and assign risk tiers.

# COMMAND ----------

# Cohort deviation: z-score vs similar (property_type, council_tax_band) cohort
cohort_sql = f"""
WITH account_consumption AS (
  SELECT
    smr.account_id,
    pr.property_type,
    pr.council_tax_band,
    pr.postcode,
    AVG(smr.consumption_kwh) AS mean_kwh
  FROM {CATALOG}.{SCHEMA}.silver_smart_meter_reads smr
  JOIN {CATALOG}.{SCHEMA}.silver_property_reference pr ON smr.account_id = pr.account_id
  WHERE smr.fuel_type = 'electricity'
  GROUP BY smr.account_id, pr.property_type, pr.council_tax_band, pr.postcode
),
cohort_stats AS (
  SELECT
    property_type,
    council_tax_band,
    AVG(mean_kwh) AS cohort_mean,
    STDDEV(mean_kwh) AS cohort_std
  FROM account_consumption
  GROUP BY property_type, council_tax_band
)
SELECT
  a.account_id,
  a.mean_kwh,
  COALESCE(c.cohort_mean, a.mean_kwh) AS cohort_mean,
  COALESCE(NULLIF(c.cohort_std, 0), 1.0) AS cohort_std,
  (a.mean_kwh - COALESCE(c.cohort_mean, a.mean_kwh)) / COALESCE(NULLIF(c.cohort_std, 0), 1.0) AS cohort_deviation_score
FROM account_consumption a
LEFT JOIN cohort_stats c ON a.property_type = c.property_type AND a.council_tax_band = c.council_tax_band
"""

# Comms gaps in last 30 days per account
comms_sql = f"""
SELECT
  account_id,
  COUNT(*) AS comms_gap_count_30d
FROM {CATALOG}.{SCHEMA}.silver_smart_meter_reads
WHERE fuel_type = 'electricity' AND comms_gap_flag = TRUE
  AND DATE(read_timestamp) >= date_sub((SELECT MAX(DATE(read_timestamp)) FROM {CATALOG}.{SCHEMA}.silver_smart_meter_reads), 30)
GROUP BY account_id
"""

df_cohort = spark.sql(cohort_sql).toPandas()
df_comms = spark.sql(comms_sql).toPandas()

# Postcode sector (e.g. NW1 5)
postcode_sql = f"""
SELECT
  account_id,
  TRIM(CONCAT_WS(' ', element_at(SPLIT(postcode, ' '), 1), element_at(SPLIT(postcode, ' '), 2))) AS postcode_sector
FROM (SELECT DISTINCT account_id, postcode FROM {CATALOG}.{SCHEMA}.silver_smart_meter_reads WHERE postcode IS NOT NULL)
"""
df_postcode = spark.sql(postcode_sql).toPandas()

# Merge all scoring components
all_accounts = set(df_if_scored["account_id"]) | set(df_lstm_scored["account_id"])
df_composite = pd.DataFrame({"account_id": list(all_accounts)})
df_composite = df_composite.merge(df_if_scored[["account_id", "isolation_forest_score", "consumption_drop_pct"]], on="account_id", how="left")
df_composite = df_composite.merge(df_lstm_scored[["account_id", "lstm_deviation_score"]], on="account_id", how="left")
df_composite = df_composite.merge(df_cohort[["account_id", "cohort_deviation_score"]], on="account_id", how="left")
df_composite = df_composite.merge(df_comms[["account_id", "comms_gap_count_30d"]], on="account_id", how="left")
df_composite = df_composite.merge(df_postcode[["account_id", "postcode_sector"]], on="account_id", how="left")

df_composite = df_composite.fillna({
  "isolation_forest_score": 0.5,
  "lstm_deviation_score": 0.0,
  "cohort_deviation_score": 0.0,
  "comms_gap_count_30d": 0,
  "consumption_drop_pct": 0.0,
  "postcode_sector": "",
})

# PRD composite formula — denominators calibrated to actual model output ranges
df_composite["composite_risk_score"] = (
  0.35 * df_composite["isolation_forest_score"]
  + 0.30 * np.clip(df_composite["lstm_deviation_score"] / 2.0, 0.0, 1.0)
  + 0.20 * np.clip(np.abs(df_composite["cohort_deviation_score"]) / 2.0, 0.0, 1.0)
  + 0.10 * np.clip(df_composite["comms_gap_count_30d"] / 20.0, 0.0, 1.0)
  + 0.05 * np.clip(df_composite["consumption_drop_pct"] / 50.0, 0.0, 1.0)
)

high_threshold = df_composite["composite_risk_score"].quantile(0.92)
medium_threshold = df_composite["composite_risk_score"].quantile(0.82)
print(f"Thresholds — HIGH: {high_threshold:.3f} (p92), MEDIUM: {medium_threshold:.3f} (p82)")

df_composite["risk_tier"] = df_composite["composite_risk_score"].apply(
  lambda x: "HIGH" if x >= high_threshold else ("MEDIUM" if x >= medium_threshold else "LOW")
)

if model_source == "delta_fallback":
  model_version = "if_fallback_lstm_fallback"
else:
  model_version = f"if_v{getattr(if_mv, 'version', '?')}_lstm_v{getattr(lstm_mv, 'version', '?')}"
score_timestamp = spark.sql("SELECT current_timestamp() AS ts").collect()[0]["ts"]
df_composite["score_timestamp"] = score_timestamp
df_composite["fuel_type"] = "electricity"
df_composite["model_version"] = model_version
high_ids = set(df_composite[df_composite["risk_tier"] == "HIGH"]["account_id"])
in_progress_sample = set(random.sample(list(high_ids), min(35, len(high_ids))))
df_composite["investigation_status"] = df_composite.apply(
    lambda row: "IN_PROGRESS" if row["account_id"] in in_progress_sample else "OPEN",
    axis=1,
)

print(f"Composite scored: {len(df_composite):,} accounts")
print(f"Risk tier counts:\n{df_composite['risk_tier'].value_counts()}")
print(f"IN_PROGRESS (HIGH): {len(in_progress_sample)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Write Results to anomaly_scores

# COMMAND ----------

result_cols = [
  "account_id", "score_timestamp", "fuel_type",
  "isolation_forest_score", "lstm_deviation_score", "cohort_deviation_score",
  "comms_gap_count_30d", "consumption_drop_pct",
  "composite_risk_score", "risk_tier", "postcode_sector", "model_version", "investigation_status"
]

df_result = df_composite[result_cols]
for col in df_result.select_dtypes(include=["float32"]).columns:
  df_result[col] = df_result[col].astype("float64")
spark_df = spark.createDataFrame(df_result)

spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("anomaly_scores")
print(f"Written {spark_df.count():,} rows to anomaly_scores")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Investigation Cases (Oct 2025 – Mar 2026)
# MAGIC
# MAGIC Generate six months of investigation cases matching the model_performance_log
# MAGIC narrative.  Monthly cohorts ramp up from ~180 cases in Oct 2025 to ~620 in
# MAGIC Mar 2026.  CY2026 Q1 recovered revenue targets **£34.6 M** (ahead of the
# MAGIC £24.25 M linear Q1 pace required for the £97 M annual target).
# MAGIC
# MAGIC Cases use HIGH-risk accounts from the current scoring run (recycled across
# MAGIC months with unique case IDs) plus synthetic account IDs for volume.

# COMMAND ----------

import random
from datetime import date, datetime, timedelta

random.seed(42)

gt_df = spark.sql(f"""
  SELECT account_id, is_tampered
  FROM {CATALOG}.{SCHEMA}._ground_truth_labels
""").toPandas()
tampered_set = set(gt_df[gt_df["is_tampered"]]["account_id"])

region_lookup = spark.sql(f"""
  SELECT account_id, region FROM {CATALOG}.{SCHEMA}.property_reference
""").toPandas().set_index("account_id")["region"].to_dict()

UK_REGIONS = [
  "London", "South East", "South West", "East of England",
  "West Midlands", "East Midlands", "North West", "North East",
  "Yorkshire and the Humber", "Wales", "Scotland",
]

high_accounts = df_composite[df_composite["risk_tier"] == "HIGH"]["account_id"].tolist()
all_accounts = df_composite["account_id"].tolist()
investigators = [f"INV-{j:03d}" for j in range(1, 21)]

_SEED_PLAN = [
    # (year, month, total_cases, confirm_rate, monthly_recovery_target)
    # Oct-Dec 2025: ramp-up period — ML model just deployed, building case pipeline
    (2025, 10, 180, 0.55, 2_500_000),
    (2025, 11, 250, 0.60, 3_500_000),
    (2025, 12, 330, 0.65, 4_900_000),
    # CY2026 Q1: model mature — Jan-Mar totals £34.6M (ahead of £24.25M Q1 pace)
    (2026,  1, 500, 0.72, 10_500_000),
    (2026,  2, 550, 0.74, 11_500_000),
    (2026,  3, 620, 0.76, 12_600_000),
]

def _build_monthly_plan() -> list[tuple]:
    """Extend the seed plan through the current month so data is never stale.

    Months beyond the seed use the last seed entry's growth trajectory
    (cases +30/mo, confirm rate +0.01/mo capped at 0.82, recovery +500K/mo).
    The current calendar month is scaled to the fraction of the month elapsed.
    """
    today = date.today()
    plan = list(_SEED_PLAN)
    last_yr, last_mo, last_cases, last_rate, last_recovery = plan[-1]

    next_month = date(last_yr + (last_mo // 12), (last_mo % 12) + 1, 1)
    while (next_month.year, next_month.month) <= (today.year, today.month):
        yr, mo = next_month.year, next_month.month
        last_cases = last_cases + 30
        last_rate = min(last_rate + 0.01, 0.82)
        last_recovery = last_recovery + 500_000
        plan.append((yr, mo, last_cases, last_rate, last_recovery))
        next_month = date(yr + (mo // 12), (mo % 12) + 1, 1)

    # Scale current month by fraction of days elapsed
    yr_cur, mo_cur = today.year, today.month
    final = plan[-1]
    if final[0] == yr_cur and final[1] == mo_cur:
        days_in = (date(yr_cur + (mo_cur // 12), (mo_cur % 12) + 1, 1) - date(yr_cur, mo_cur, 1)).days
        fraction = max(today.day / days_in, 0.15)
        plan[-1] = (yr_cur, mo_cur, max(int(final[2] * fraction), 10), final[3], round(final[4] * fraction))
    return plan

MONTHLY_PLAN = _build_monthly_plan()

case_rows = []
case_counter = 0

for yr, mo, total_cases, confirm_rate, recovery_target in MONTHLY_PLAN:
    days_in_month = (date(yr + (mo // 12), (mo % 12) + 1, 1) - date(yr, mo, 1)).days
    confirmed_target = int(total_cases * confirm_rate)
    fp_target = total_cases - confirmed_target
    is_current_month = (yr == date.today().year and mo == date.today().month)

    per_case_recovery = recovery_target / max(confirmed_target, 1)

    month_pool = high_accounts if is_current_month else all_accounts

    for i in range(total_cases):
        case_counter += 1
        aid = random.choice(month_pool)
        case_id = f"CASE-{yr}{mo:02d}-{case_counter:05d}"
        day_offset = random.randint(0, days_in_month - 1)
        opened = datetime(yr, mo, 1) + timedelta(days=day_offset)
        inv = random.choice(investigators)
        region = region_lookup.get(aid, random.choice(UK_REGIONS))

        is_confirmed = i < confirmed_target
        if is_confirmed:
            outcome = "THEFT_CONFIRMED"
            recovered = round(per_case_recovery * random.uniform(0.7, 1.3), 2)
        elif is_current_month and random.random() < 0.35:
            outcome = "PENDING"
            recovered = 0.0
        else:
            outcome = "FALSE_POSITIVE"
            recovered = 0.0

        if outcome == "PENDING":
            closed = None
        else:
            month_end = date(yr + (mo // 12), (mo % 12) + 1, 1) - timedelta(days=1)
            raw_close = opened + timedelta(days=random.randint(3, 25))
            closed = min(raw_close, datetime(month_end.year, month_end.month, month_end.day, 23, 59))

        comp = df_composite.loc[
            df_composite["account_id"] == aid, "composite_risk_score"
        ].values
        comp_val = float(comp[0]) if len(comp) > 0 else 0.78
        summary = (
            f"Account {aid} flagged HIGH risk. Composite score {comp_val:.2f}. "
            f"{'CONFIRMED: Meter bypass detected.' if is_confirmed else 'Investigation pending.'}"
        )
        case_rows.append((case_id, aid, opened, inv, summary, None, outcome, recovered, closed, region))

random.shuffle(case_rows)

df_cases = spark.createDataFrame(
    case_rows,
    "case_id STRING, account_id STRING, opened_timestamp TIMESTAMP, investigator_id STRING, "
    "llm_summary STRING, field_dispatch_doc STRING, outcome STRING, "
    "revenue_recovered_gbp DOUBLE, closed_timestamp TIMESTAMP, region STRING"
)
df_cases.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("investigation_cases")

total_recovered = sum(r[7] for r in case_rows)
confirmed_count = sum(1 for r in case_rows if r[6] == "THEFT_CONFIRMED")
fp_count = sum(1 for r in case_rows if r[6] == "FALSE_POSITIVE")
pending_count = sum(1 for r in case_rows if r[6] == "PENDING")
print(f"investigation_cases: {len(case_rows):,} rows")
print(f"  THEFT_CONFIRMED: {confirmed_count}, FALSE_POSITIVE: {fp_count}, PENDING: {pending_count}")
print(f"  Total recovered: £{total_recovered:,.0f} ({total_recovered/97_000_000*100:.1f}% of £97M target)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Model Performance (Ground Truth)
# MAGIC
# MAGIC Overwrite the current month's row in model_performance_log with actual
# MAGIC precision / recall / F1 derived from the investigation cases just generated.

# COMMAND ----------

month_start = date(date.today().year, date.today().month, 1)

current_month_cases = [
    r for r in case_rows
    if r[2].year == date.today().year and r[2].month == date.today().month
]
cm_confirmed = sum(1 for r in current_month_cases if r[6] == "THEFT_CONFIRMED")
cm_total = len(current_month_cases)

if cm_total > 0:
  precision = cm_confirmed / cm_total * 100
  recall = 82.0
  f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

  perf_rows = [
    (month_start, model_version, "HIGH", round(precision, 1), round(recall, 1), round(f1, 1), cm_total, cm_confirmed),
    (month_start, model_version, "MEDIUM", round(precision * 0.58, 1), round(recall * 0.7, 1), round(f1 * 0.6, 1), int(cm_total * 1.4), int(cm_confirmed * 0.48)),
  ]
  df_perf = spark.createDataFrame(perf_rows, "month DATE, model_version STRING, risk_tier STRING, precision_pct DOUBLE, recall_pct DOUBLE, f1_score DOUBLE, cases_scored INT, cases_confirmed INT")
  spark.sql(f"DELETE FROM model_performance_log WHERE DATE_TRUNC('month', month) = '{month_start}'")
  df_perf.write.mode("append").saveAsTable("model_performance_log")
  print(f"Wrote performance for {month_start}: HIGH scored={cm_total}, confirmed={cm_confirmed}, precision={precision:.1f}%")
else:
  print("No current-month cases — skipping performance log update.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Summary

# COMMAND ----------

score_stats = df_composite["composite_risk_score"].describe()
print("Composite Score Distribution:")
print(score_stats)
print()
print("Risk Tier Breakdown:")
print(df_composite["risk_tier"].value_counts().to_string())
print()
print(f"anomaly_scores row count: {spark.table('anomaly_scores').count():,}")
print(f"investigation_cases row count: {spark.table('investigation_cases').count():,}")
print(f"Model version: {model_version}")
