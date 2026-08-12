# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
