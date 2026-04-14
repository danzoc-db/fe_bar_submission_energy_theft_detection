# Energy Theft Detection Demo — Tech Stack

**Version:** 1.0
**Date:** 17 March 2026

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                  Databricks App (APX)                             │
│  ┌──────────────────┐     ┌────────────────────────────────────┐ │
│  │  FastAPI Backend  │────▶│  React + TypeScript Frontend       │ │
│  │  (Python 3.11+)  │◀────│  (Vite + TanStack + shadcn/ui)    │ │
│  └───────┬──────────┘     └────────────────────────────────────┘ │
│          │                                                        │
└──────────┼────────────────────────────────────────────────────────┘
           │
   ┌───────┴────────┐         ┌───────────────────────┐
   │ SQL Warehouse  │         │    AI Gateway          │
   │ Statement Exec │         │  (Bedrock LLM proxy)   │
   │   API (read)   │         └───────────────────────┘
   └───────┬────────┘
           │
   ┌───────┴─────────────────────────────────────────────┐
   │             Unity Catalog                            │
   │  dz_demos.energy_theft_protection                    │
   │  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
   │  │Delta Tables│ │Metric Views  │ │MLflow Models  │  │
   │  │(6 tables)  │ │(2 KPI views) │ │(2 registered) │  │
   │  └────────────┘ └──────────────┘ └───────────────┘  │
   │  ┌──────────────────┐ ┌───────────────────────────┐  │
   │  │Genie Space       │ │system.serving audit logs  │  │
   │  │(Susie's exec NL) │ │(AI Gateway audit trail)   │  │
   │  └──────────────────┘ └───────────────────────────┘  │
   └──────────────────────────────────────────────────────┘
```

**Key decision: Stateless architecture (no Lakebase).** This demo reads from Delta
tables via SQL Warehouse. There is no OLTP write-back layer. All data is pre-computed
and batch-loaded. This keeps the demo simple, deployable, and focused on the AI/ML
governance story rather than transactional complexity.

---

## Application Stack

### Backend: Python + FastAPI

| Component | Package | Purpose |
|-----------|---------|---------|
| Web Framework | `fastapi` | REST API with OpenAPI schema generation |
| ASGI Server | `uvicorn` | Production-grade async server |
| Validation | `pydantic` / `pydantic-settings` | Request/response models, typed config |
| Databricks SDK | `databricks-sdk` | SQL Warehouse statement execution, Genie API, AI Gateway |
| HTTP | `httpx` | Async HTTP client for Databricks API calls |

**Why no ORM:** No Lakebase/PostgreSQL. All queries use the Databricks SDK
Statement Execution API against SQL Warehouse. Responses are mapped to Pydantic
models in the API layer.

### Frontend: React + TypeScript + Vite

| Component | Package | Purpose |
|-----------|---------|---------|
| UI Library | `react` / `react-dom` | Component framework |
| Bundler | `vite` | Fast dev server + production builds |
| Router | `@tanstack/react-router` | File-based routing with type safety |
| Data Fetching | `@tanstack/react-query` | Server state with suspense support |
| Styling | `tailwindcss` (v4) | Utility-first CSS |
| Components | shadcn/ui | Accessible component library |
| Charts | Plotly.js / react-plotly.js | Heatmaps, time series, radar charts |
| Maps | Plotly Mapbox | UK postcode choropleth |
| Icons | `lucide-react` | Consistent icon set |
| Animations | `motion` | Transitions and micro-interactions |

### Build & Development: apx Toolkit

| Command | Description |
|---------|-------------|
| `uv run apx dev start` | Start backend + frontend + OpenAPI watcher |
| `uv run apx build` | Production build |
| `uv run apx components add <name>` | Add shadcn/ui component |

### Deployment: Databricks Apps + DABs

| Component | Tool | Purpose |
|-----------|------|---------|
| Bundle Config | `databricks.yml` | App definition, deployment targets |
| App Entrypoint | `app.yml` | Uvicorn command for production |
| Deployment | `databricks bundle deploy` | Push to Databricks Apps |
| Profile | `azure-field-demos` | Workspace authentication |

---

## Data Access Pattern

All data access is read-only via SQL Warehouse Statement Execution API:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="azure-field-demos")

result = w.statement_execution.execute_statement(
    warehouse_id=WAREHOUSE_ID,
    catalog="dz_demos",
    schema="energy_theft_protection",
    statement="SELECT * FROM anomaly_scores WHERE risk_tier = 'HIGH' LIMIT 100"
)
```

Responses are parsed into Pydantic response models in the FastAPI route handlers.

---

## AI Components

| Component | Service | Access Method |
|-----------|---------|--------------|
| Genie (Susie's NL queries) | Genie Conversation API | Databricks SDK |
| Bedrock LLM (Robbie's summaries) | AI Gateway | Model Serving endpoint |
| ML Models (risk scoring) | Pre-computed in Delta | SQL read only |
| AI Audit Trail | `system.serving.endpoint_usage` | SQL read only |

---

## Branding

| Element | Value |
|---------|-------|
| Primary colour | UKI Gas blue `#0A84C8` |
| Secondary | UKI Energy corporate white/grey |
| Font | System default (Inter or similar sans-serif) |
| Banner | "Simulated Data — Demo Environment" on every page |

---

## References

- [Databricks Apps Cookbook](https://apps-cookbook.dev/)
- [APX Toolkit](https://github.com/databricks-solutions/apx)
- [Databricks Apps Examples](https://github.com/databricks-solutions/databricks-apps-examples)
- [Databricks SDK — Statement Execution](https://docs.databricks.com/en/dev-tools/sdk-python.html)
- [Genie Conversation API](https://docs.databricks.com/en/genie/genie-conversation-api.html)
