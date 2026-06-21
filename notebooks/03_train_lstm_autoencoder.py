# Databricks notebook source
# MAGIC %md
# MAGIC # LSTM Autoencoder — 90-Day Consumption Anomaly Detection
# MAGIC
# MAGIC Trains an LSTM autoencoder on 90-day daily consumption sequences and registers it in MLflow under Unity Catalog.
# MAGIC The reconstruction-error z-score is the **lstm_deviation_score** used in anomaly ranking.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Config

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.lstm_consumption_v2"

import mlflow
import json
import io
from datetime import datetime
mlflow.set_registry_uri("databricks-uc")

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Data Preparation

# COMMAND ----------

from datetime import timedelta
import numpy as np
import pandas as pd

SEQ_LEN = 90

# Read pre-aggregated daily consumption from gold layer
daily_df = spark.sql("""
  SELECT account_id, read_date, daily_kwh
  FROM gold_daily_consumption
  WHERE fuel_type = 'electricity'
""")

max_date = spark.sql("SELECT MAX(read_date) AS d FROM gold_daily_consumption WHERE fuel_type = 'electricity'").collect()[0]["d"]
date_range = [max_date - timedelta(days=i) for i in range(SEQ_LEN - 1, -1, -1)]

# Collect to pandas for matrix construction
daily_pd = daily_df.toPandas()

# Pivot: rows = accounts, columns = days
pivot = daily_pd.pivot_table(index="account_id", columns="read_date", values="daily_kwh")

# Align to our 90-day window (reindex to full date range)
matrix = pivot.reindex(columns=date_range)

# Forward-fill then fill remaining NaN with 0
matrix = matrix.ffill(axis=1).bfill(axis=1).fillna(0.0)

# Per-account: zero-mean, unit-variance (avoid div-by-zero)
means = matrix.mean(axis=1)
stds = matrix.std(axis=1)
stds = stds.replace(0, 1.0)  # avoid division by zero
matrix_norm = matrix.sub(means, axis=0).div(stds, axis=0)

# Build tensor: (n_accounts, seq_len, 1) for LSTM
X = np.float32(matrix_norm.values[:, :, np.newaxis])
account_ids = matrix_norm.index.tolist()

n_accounts = X.shape[0]
print(f"Prepared {n_accounts} accounts × {SEQ_LEN} days")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Model Definition

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
        # Encoder: LSTM -> last hidden -> latent
        _, (h_n, _) = self.encoder(x)
        latent = self.encoder_proj(h_n.squeeze(0))
        # Decoder: repeat latent across seq_len -> LSTM -> reconstruct
        latent_seq = latent.unsqueeze(1).repeat(1, self.seq_len, 1)
        out, _ = self.decoder(latent_seq)
        reconstructed = self.decoder_proj(out)
        return reconstructed

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Training

# COMMAND ----------

from torch.utils.data import TensorDataset, DataLoader

HIDDEN_DIM = 32
LATENT_DIM = 16
EPOCHS = 50
LR = 1e-3
BATCH_SIZE = 64

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = LSTMAutoencoder(input_dim=1, hidden_dim=HIDDEN_DIM, latent_dim=LATENT_DIM, seq_len=SEQ_LEN).to(device)

dataset = TensorDataset(torch.from_numpy(X))
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

optimizer = torch.optim.Adam(model.parameters(), lr=LR)
criterion = nn.MSELoss()

train_losses = []
for epoch in range(EPOCHS):
    model.train()
    epoch_loss = 0.0
    for (batch,) in loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        recon = model(batch)
        loss = criterion(recon, batch)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    avg_loss = epoch_loss / len(loader)
    train_losses.append(avg_loss)
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch+1}/{EPOCHS} — loss: {avg_loss:.6f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Scoring — Reconstruction Error → lstm_deviation_score

# COMMAND ----------

model.eval()
with torch.no_grad():
    X_t = torch.from_numpy(X).to(device)
    recon = model(X_t)

recon_np = recon.cpu().numpy()
recon_errors = np.mean((X - recon_np) ** 2, axis=(1, 2))

# Z-score reconstruction errors across all accounts
mean_recon = float(np.mean(recon_errors))
std_recon = float(np.std(recon_errors))
if std_recon < 1e-10:
    std_recon = 1.0
lstm_deviation_scores = (recon_errors - mean_recon) / std_recon

lstm_df = pd.DataFrame({"account_id": account_ids, "lstm_deviation_score": lstm_deviation_scores})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. MLflow Logging & Model Registration

# COMMAND ----------

import mlflow.pytorch

ANOMALOUS_THRESHOLD = 2.0
pct_anomalous = float(np.mean(np.abs(lstm_deviation_scores) > ANOMALOUS_THRESHOLD) * 100)

with mlflow.start_run(run_name="lstm_consumption_v2"):
    for i, loss in enumerate(train_losses):
        mlflow.log_metric("train_loss", loss, step=i)
    mlflow.log_params({
        "hidden_dim": HIDDEN_DIM,
        "latent_dim": LATENT_DIM,
        "epochs": EPOCHS,
        "lr": LR,
        "seq_len": SEQ_LEN,
        "n_accounts": n_accounts,
    })
    mlflow.log_metrics({
        "mean_recon_error": mean_recon,
        "std_recon_error": std_recon,
        "pct_anomalous": pct_anomalous,
    })
    from mlflow.models import infer_signature
    sample_input = X[:5].astype(np.float32)
    with torch.no_grad():
        sample_output = model(torch.from_numpy(sample_input).to(device)).cpu().numpy()
    sig = infer_signature(sample_input, sample_output)
    registry_ok = True
    try:
        mlflow.pytorch.log_model(model, "model", registered_model_name=MODEL_NAME, signature=sig)
    except Exception as e:
        registry_ok = False
        print(f"⚠ UC model registry upload failed, falling back to Delta model store: {e}")

    # --- Diagnostic Artifacts ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1. Training Loss Curve
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(1, EPOCHS + 1), train_losses, color="#4A90D9", lw=2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title("LSTM Autoencoder Training Loss")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    mlflow.log_figure(fig, "diagnostics/training_loss_curve.png")
    plt.close(fig)

    # 2. Reconstruction Error Distribution
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(recon_errors, bins=80, color="#50C878", edgecolor="white", alpha=0.85)
    threshold_mse = mean_recon + ANOMALOUS_THRESHOLD * std_recon
    ax.axvline(threshold_mse, color="#D0021B", ls="--", lw=2,
               label=f"Anomaly threshold (z={ANOMALOUS_THRESHOLD})")
    ax.set_xlabel("Reconstruction MSE")
    ax.set_ylabel("Account Count")
    ax.set_title("Reconstruction Error Distribution \u2014 LSTM Autoencoder")
    ax.legend()
    fig.tight_layout()
    mlflow.log_figure(fig, "diagnostics/reconstruction_error_dist.png")
    plt.close(fig)

    # 3. Top 5 Anomaly Reconstructions (Original vs Reconstructed)
    top5_idx = np.argsort(recon_errors)[-5:][::-1]
    fig, axes = plt.subplots(5, 1, figsize=(12, 14), sharex=True)
    for plot_i, (ax, acct_idx) in enumerate(zip(axes, top5_idx)):
        original = X[acct_idx, :, 0]
        reconstructed = recon_np[acct_idx, :, 0]
        ax.plot(original, label="Original", color="#4A90D9", lw=1.5)
        ax.plot(reconstructed, label="Reconstructed", color="#D0021B", lw=1.5, ls="--")
        ax.fill_between(range(SEQ_LEN), original, reconstructed, alpha=0.15, color="#D0021B")
        ax.set_ylabel("Norm. kWh")
        acct_name = account_ids[acct_idx] if acct_idx < len(account_ids) else f"#{acct_idx}"
        ax.set_title(f"{acct_name} \u2014 MSE: {recon_errors[acct_idx]:.4f}", fontsize=10)
        if plot_i == 0:
            ax.legend(loc="upper right")
    axes[-1].set_xlabel("Day (0\u201389)")
    fig.suptitle("Top 5 Anomalous Accounts \u2014 Original vs Reconstructed Consumption",
                 y=1.01, fontsize=12)
    fig.tight_layout()
    mlflow.log_figure(fig, "diagnostics/top_anomaly_reconstructions.png")
    plt.close(fig)

    print("Logged 3 diagnostic artifacts to MLflow")

if registry_ok:
    print(f"Registered model: {MODEL_NAME}")
    client = mlflow.MlflowClient()
    latest = max(client.search_model_versions(f"name='{MODEL_NAME}'"), key=lambda v: int(v.version))
    client.set_registered_model_alias(MODEL_NAME, "champion", latest.version)
    print(f"Set @champion alias to version {latest.version}")
else:
    fallback_table = f"{CATALOG}.{SCHEMA}.model_fallback_store"
    spark.sql(f"""
      CREATE TABLE IF NOT EXISTS {fallback_table} (
        model_name STRING,
        flavor STRING,
        payload BINARY,
        meta_json STRING,
        created_at TIMESTAMP
      )
    """)
    spark.sql(f"DELETE FROM {fallback_table} WHERE model_name = '{MODEL_NAME}'")
    buf = io.BytesIO()
    torch.save(model.state_dict(), buf)
    payload = bytearray(buf.getvalue())
    meta_json = json.dumps(
        {
            "framework": "pytorch",
            "class": "LSTMAutoencoder",
            "input_dim": 1,
            "hidden_dim": HIDDEN_DIM,
            "latent_dim": LATENT_DIM,
            "seq_len": SEQ_LEN,
        }
    )
    spark.createDataFrame(
        [(MODEL_NAME, "pytorch_state_dict", payload, meta_json, datetime.utcnow())],
        "model_name string, flavor string, payload binary, meta_json string, created_at timestamp",
    ).write.mode("append").saveAsTable(fallback_table)
    print(f"Saved fallback model artifact to {fallback_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Summary — Score Distribution & Top Deviators

# COMMAND ----------

display(spark.createDataFrame(lstm_df.describe()))

# COMMAND ----------

top_deviators = lstm_df.nlargest(20, "lstm_deviation_score")
display(spark.createDataFrame(top_deviators))
