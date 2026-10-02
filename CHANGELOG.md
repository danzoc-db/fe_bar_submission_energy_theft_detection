# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added - Lakebase operational-serving layer

- **Lakebase (managed Postgres) operational-serving stage**, completing the
  end-to-end journey: Lakeflow -> Unity Catalog -> ML/GenAI -> **Lakebase** ->
  Genie -> App.
  - `scripts/provision_lakebase.py` and `notebooks/10_provision_lakebase.py` -
    idempotent provisioning of the instance, a **synced table**
    (`anomaly_scores_serving`, Delta -> Postgres) for the low-latency risk queue,
    and a native-Postgres **OLTP schema** (`revenue_protection.investigation_cases`
    + append-only `case_events` audit log with a state-transition trigger).
  - `backend/lakebase_client.py` - psycopg client using short-lived OAuth
    credentials; reads the serving queue and commits case open/assign/close with
    read-your-writes latency.
  - Investigation close path now commits to Lakebase (with the Delta MERGE kept
    as the analytics / Genie reverse-sync path); new
    `GET /api/investigation/{account_id}/case` surfaces the live case + audit trail.
  - DABs resources for the `zoccali-fevm-aws` target: `database_instances`,
    `synced_database_tables`, and a `database` app-resource binding.
  - Feature-flagged via `LAKEBASE_ENABLED` (default off): the app falls back to
    the Delta-only path unchanged when disabled.
  - `tests/test_lakebase.py` - offline acceptance tests for config defaults,
    graceful fallback, and the new endpoint.

---

## [1.0.0] - 2026-08-12

### Added

- **Executive Dashboard** - KPI tiles, risk heatmap, trend charts, fuel split, Genie NL panel
- **Investigation Workbench** - Flagged accounts table, detail drawer, signal breakdown, LLM case summaries
- **AI Governance** - PII matrix, component registry, Unity Catalog lineage DAG, AI Gateway audit trail
- **Board Report** - Agent Atlas multi-agent supervisor integration with trace visualization
- **Presentation Mode** - 9-slide overview for demo delivery
- **Why Databricks** - Compete messaging page with AI Gateway expansion

### Data Pipeline

- Medallion architecture (Bronze/Silver/Gold) via Spark Declarative Pipelines
- Isolation Forest + LSTM ensemble for anomaly detection
- Metric Views for Genie natural-language queries
- External lineage to 4 Power BI reports

### Infrastructure

- Databricks Asset Bundles (DABs) deployment
- Multi-workspace support (AWS, Azure)
- AI Gateway endpoints (Bedrock, OpenAI/FMAPI, Gemini, Llama)
- Genie Space configuration notebook

### Governance

- Repository hardened for external customer sharing
- CODEOWNERS, AGENTS.md, ACCESS_TOKEN_HANDLING.md
- DB license for databricks-solutions compatibility
- SECURITY.md with vulnerability reporting policy
- Workspace portability (no hardcoded IDs or credentials)

### Documentation

- Full PRD and architecture docs
- Workspace setup guide
- External lineage configuration guide
- Demo video link
