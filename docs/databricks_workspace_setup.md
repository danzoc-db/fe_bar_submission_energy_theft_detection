# Databricks Workspace Setup

Configuration required in the `azure-field-demos` workspace before the app can run.

---

## 1. Unity Catalog

### Catalog and Schema

```sql
CREATE CATALOG IF NOT EXISTS dz_demos;
CREATE SCHEMA IF NOT EXISTS dz_demos.energy_theft_protection;
```

### Delta Tables

Six tables as defined in `docs/PRD.md` Section 4.1:
- `smart_meter_reads` — half-hourly consumption
- `meters` — meter registry
- `anomaly_scores` — ML-scored risk
- `investigation_cases` — case lifecycle
- `property_reference` — static property metadata
- `model_performance_log` — monthly model metrics

### Metric Views

Two UC Metric Views as defined in `docs/PRD.md` Section 7:
- `metric_theft_precision_rate` — confirmed theft / total HIGH cases closed
- `metric_revenue_recovery` — revenue recovered by month and region

---

## 2. SQL Warehouse

| Setting | Value |
|---------|-------|
| Name | `energy-theft-demo-warehouse` (or shared existing) |
| Type | Serverless |
| Size | Small (auto-scaling) |
| Catalog default | `dz_demos` |
| Schema default | `energy_theft_protection` |

Store the warehouse ID in `.env` as `SQL_WAREHOUSE_ID`.

---

## 3. AI Gateway (Bedrock LLM)

### Endpoint Configuration

| Setting | Value |
|---------|-------|
| Name | `energy-theft-bedrock-gateway` |
| Served model | External: AWS Bedrock (Claude or similar) |
| Rate limits | Per-user, logged |
| Guardrails | PII detection, prompt injection filter |

The AI Gateway provides:
- Unified audit log in `system.serving.endpoint_usage`
- Rate limiting per user/app
- Input/output guardrails
- Token usage tracking

---

## 4. MLflow Model Registry

### Registered Models

| Model Name | Version | Type |
|------------|---------|------|
| `dz_demos.energy_theft_protection.isolation_forest_theft` | v3 | sklearn IsolationForest |
| `dz_demos.energy_theft_protection.lstm_consumption` | v2 | keras LSTM Autoencoder |

Models are registered with MLflow experiment tracking showing training runs,
hyperparameters, and model cards. For the demo, models are simulated — scores are
pre-computed in `anomaly_scores`.

---

## 5. Genie Space

### Revenue Protection Executive Intelligence (Susie's Space)

| Setting | Value |
|---------|-------|
| Name | Revenue Protection Executive Intelligence |
| Tables | `anomaly_scores`, `investigation_cases`, `property_reference`, metric views |
| Persona | Executive (Susie Chambers) |
| Instructions | See PRD Section 6.1 |

---

## 6. App Registration

| Setting | Value |
|---------|-------|
| App name | `energy-theft-detection` |
| Source | DABs deployment |
| Auth | Databricks OAuth (user identity passthrough) |
| Resources | SQL Warehouse, AI Gateway endpoint, Genie Space |

---

## 7. Environment Variables (`.env`)

```bash
DATABRICKS_CONFIG_PROFILE=azure-field-demos
SQL_WAREHOUSE_ID=<warehouse-id>
AI_GATEWAY_ENDPOINT=energy-theft-bedrock-gateway
GENIE_SPACE_ID=<genie-space-id>
```
