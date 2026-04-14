# Databricks notebook source
# MAGIC %md
# MAGIC # Isolation Forest — Energy Theft Anomaly Model
# MAGIC
# MAGIC Trains an Isolation Forest model on smart meter consumption features and registers it in MLflow under Unity Catalog.
# MAGIC
# MAGIC **Output:**
# MAGIC - Model: `dz_demos.energy_theft_protection.isolation_forest_theft_v3`
# MAGIC - Scored accounts with isolation_forest_score (0–1, higher = more anomalous)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Config

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.isolation_forest_theft_v3"

import mlflow

mlflow.set_registry_uri("databricks-uc")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA}")
print(f"Model: {MODEL_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Feature Engineering
# MAGIC
# MAGIC Reads pre-computed features from the **silver_account_features** table
# MAGIC (built by `01c_gold_aggregate.py`). No raw reads processing needed.

# COMMAND ----------

df_features = spark.sql(f"""
  SELECT account_id, mean_consumption, std_consumption, min_consumption,
         max_consumption, morning_evening_ratio, comms_gap_rate, consumption_drop_pct
  FROM {CATALOG}.{SCHEMA}.silver_account_features
""")

# Fill remaining nulls and convert to Pandas for sklearn
import pandas as pd

FEATURE_COLS = [
  "mean_consumption", "std_consumption", "min_consumption", "max_consumption",
  "morning_evening_ratio", "comms_gap_rate", "consumption_drop_pct"
]

pdf = df_features.toPandas()
pdf[FEATURE_COLS] = pdf[FEATURE_COLS].fillna(0)
pdf = pdf.dropna(subset=["account_id"])

X = pdf[FEATURE_COLS].values
account_ids = pdf["account_id"].values

print(f"Accounts: {len(pdf):,}")
print(f"Features: {FEATURE_COLS}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Train Isolation Forest

# MAGIC - `contamination=0.05`: expect ~5% anomalies
# MAGIC - `n_estimators=200`: balance of speed and stability
# MAGIC - Scores normalised 0–1 (higher = more anomalous)

# COMMAND ----------

from sklearn.ensemble import IsolationForest

model = IsolationForest(
  contamination=0.05,
  n_estimators=200,
  random_state=42,
)

model.fit(X)

# decision_function: more negative = more anomalous; invert and min-max to 0–1
raw_scores = model.decision_function(X)
score_min, score_max = raw_scores.min(), raw_scores.max()
if score_max - score_min > 0:
  isolation_forest_scores = 1.0 - (raw_scores - score_min) / (score_max - score_min)
else:
  isolation_forest_scores = [0.5] * len(raw_scores)

print(f"Score range: [{isolation_forest_scores.min():.4f}, {isolation_forest_scores.max():.4f}]")
print(f"Mean score: {sum(isolation_forest_scores) / len(isolation_forest_scores):.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. MLflow Logging (Unity Catalog)

# COMMAND ----------

with mlflow.start_run(run_name="isolation_forest_theft_v3"):
  mlflow.log_params({
    "n_estimators": 200,
    "contamination": 0.05,
    "n_features": len(FEATURE_COLS),
    "n_accounts": len(pdf),
  })

  mlflow.log_metrics({
    "mean_score": float(sum(isolation_forest_scores) / len(isolation_forest_scores)),
    "std_score": float(pd.Series(isolation_forest_scores).std()),
    "pct_high_risk": float((pd.Series(isolation_forest_scores) >= 0.7).mean() * 100),
  })

  mlflow.sklearn.log_model(
    model, "model",
    registered_model_name=MODEL_NAME,
    input_example=pdf[FEATURE_COLS].head(5),
  )

  # --- Diagnostic Artifacts ---
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from sklearn.preprocessing import StandardScaler

  scores_series = pd.Series(isolation_forest_scores)
  p82 = float(scores_series.quantile(0.82))
  p92 = float(scores_series.quantile(0.92))

  # 1. Anomaly Score Distribution
  fig, ax = plt.subplots(figsize=(10, 5))
  ax.hist(isolation_forest_scores, bins=80, color="#4A90D9", edgecolor="white", alpha=0.85)
  ax.axvline(p82, color="#F5A623", ls="--", lw=2, label=f"p82 MEDIUM threshold ({p82:.3f})")
  ax.axvline(p92, color="#D0021B", ls="--", lw=2, label=f"p92 HIGH threshold ({p92:.3f})")
  ax.set_xlabel("Isolation Forest Score (0\u20131, higher = more anomalous)")
  ax.set_ylabel("Account Count")
  ax.set_title("Anomaly Score Distribution \u2014 Isolation Forest")
  ax.legend()
  fig.tight_layout()
  mlflow.log_figure(fig, "diagnostics/score_distribution.png")
  plt.close(fig)

  # 2. Feature Importance (averaged from each tree's feature_importances_)
  import numpy as _np
  importances = _np.mean(
      [tree.feature_importances_ for tree in model.estimators_], axis=0
  )
  fig, ax = plt.subplots(figsize=(8, 5))
  idx = importances.argsort()
  ax.barh([FEATURE_COLS[i] for i in idx], importances[idx], color="#7B68EE")
  ax.set_xlabel("Importance (mean split contribution)")
  ax.set_title("Feature Importance \u2014 Isolation Forest")
  fig.tight_layout()
  mlflow.log_figure(fig, "diagnostics/feature_importance.png")
  plt.close(fig)

  # 3. Top Anomaly Feature Profiles (z-scored heatmap)
  features_z = pd.DataFrame(
      StandardScaler().fit_transform(pdf[FEATURE_COLS]),
      columns=FEATURE_COLS, index=pdf.index,
  )
  top20_idx = scores_series.nlargest(20).index
  top20_z = features_z.iloc[top20_idx]

  fig, ax = plt.subplots(figsize=(10, 7))
  im = ax.imshow(top20_z.values, aspect="auto", cmap="RdYlBu_r")
  ax.set_xticks(range(len(FEATURE_COLS)))
  ax.set_xticklabels(FEATURE_COLS, rotation=45, ha="right", fontsize=9)
  ax.set_ylabel("Top 20 Anomalous Accounts")
  ax.set_title("Feature Z-Scores \u2014 Top 20 Anomalous Accounts")
  fig.colorbar(im, ax=ax, label="Z-score (red = high deviation)")
  fig.tight_layout()
  mlflow.log_figure(fig, "diagnostics/top_anomaly_profiles.png")
  plt.close(fig)

  print("Logged 3 diagnostic artifacts to MLflow")

  run_id = mlflow.active_run().info.run_id
  print(f"Run ID: {run_id}")
  print(f"Model registered: {MODEL_NAME}")

client = mlflow.MlflowClient()
latest = max(client.search_model_versions(f"name='{MODEL_NAME}'"), key=lambda v: int(v.version))
client.set_registered_model_alias(MODEL_NAME, "champion", latest.version)
print(f"Set @champion alias to version {latest.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Score Output

# MAGIC Write account_id + isolation_forest_score to a temp view and display a sample.

# COMMAND ----------

scored_pdf = pd.DataFrame({
  "account_id": account_ids,
  "isolation_forest_score": isolation_forest_scores,
})
scored_pdf = scored_pdf.sort_values("isolation_forest_score", ascending=False).reset_index(drop=True)

df_scored = spark.createDataFrame(scored_pdf)
df_scored.createOrReplaceTempView("isolation_forest_scored_accounts")

# COMMAND ----------

display(df_scored.limit(100))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Summary

# MAGIC Model registration info and score distribution.

# COMMAND ----------

import json

summary = {
  "model_name": MODEL_NAME,
  "run_id": run_id,
  "catalog": CATALOG,
  "schema": SCHEMA,
  "n_accounts_scored": len(scored_pdf),
  "score_stats": {
    "mean": float(scored_pdf["isolation_forest_score"].mean()),
    "std": float(scored_pdf["isolation_forest_score"].std()),
    "min": float(scored_pdf["isolation_forest_score"].min()),
    "max": float(scored_pdf["isolation_forest_score"].max()),
    "pct_high_risk_0.7": float((scored_pdf["isolation_forest_score"] >= 0.7).mean() * 100),
    "pct_high_risk_0.9": float((scored_pdf["isolation_forest_score"] >= 0.9).mean() * 100),
  },
}

print(json.dumps(summary, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC **Temp table** `isolation_forest_scored_accounts` is available for downstream pipelines.
# MAGIC Model `dz_demos.energy_theft_protection.isolation_forest_theft_v3` is ready for batch scoring or Model Serving.
