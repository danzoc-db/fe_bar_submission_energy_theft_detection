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
   ┌───────┴────────┐  ┌──────────────────┐  ┌─────────────────────┐
   │ SQL Warehouse  │  │ Lakebase          │  │    AI Gateway       │
   │ Statement Exec │  │ (managed Postgres)│  │  (Bedrock LLM proxy)│
   │   API (read)   │  │  read + write     │  └─────────────────────┘
   └───────┬────────┘  └────────┬─────────┘
           │                    │
           │        synced table (Delta -> Postgres)
           │        + reverse sync (closed cases -> Delta)
           │                    │
   ┌───────┴────────────────────┴─────────────────────────┐
   │             Unity Catalog                            │
   │  <your_catalog>.energy_theft_protection                    │
   │  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
   │  │Delta Tables│ │Metric Views  │ │MLflow Models  │  │
   │  │(6 tables)  │ │(2 KPI views) │ │(2 registered) │  │
   │  └────────────┘ └──────────────┘ └───────────────┘  │
   │  ┌──────────────────┐ ┌───────────────────────────┐  │
   │  │Genie Space       │ │system.serving audit logs  │  │
   │  │(Susie's exec NL) │ │(AI Gateway audit trail)   │  │
   │  └──────────────────┘ └───────────────────────────┘  │
   └──────────────────────────────────────────────────────┘

   Lakebase (managed Postgres, operational serving):
     public.anomaly_scores_serving     <- synced from Delta gold (read path)
     revenue_protection.investigation_cases + case_events (OLTP write path)
```

**Key decision: Lakebase for operational serving.** The analytical path (medallion
pipeline, ML scoring, Genie) lives in Delta via SQL Warehouse. The *operational*
path lives in Lakebase (managed Postgres):

- A **synced table** `anomaly_scores_serving` is kept in sync from the Delta gold
  table (Delta -> Postgres) so the investigator app serves the flagged-account
  queue at OLTP latency without a SQL Warehouse cold-start on every page load.
- A native-Postgres **OLTP schema** `revenue_protection` holds the transactional
  case state (`investigation_cases` + an append-only `case_events` audit log with
  a trigger that records every state transition). The app writes case open /
  assign / close actions here with millisecond, read-your-writes commits.

The Delta MERGE still runs as the analytics / Genie reverse-sync path, so closed
cases remain queryable in natural language. The layer is **feature-flagged**
(`LAKEBASE_ENABLED`): when off, every call falls back to the Delta path and the
app behaves exactly as the earlier stateless build. See
`scripts/provision_lakebase.py` and `notebooks/10_provision_lakebase.py`.

**Trade-offs considered:**

| Option | Why not |
|--------|---------|
| Delta-only (previous design) | Interactive case writes become async Delta MERGEs (seconds, eventual consistency); the queue read pays a warehouse cold-start. Fine for a static demo, wrong for a live revenue-protection workflow. |
| External RDS/Aurora Postgres | Another system to run, secure and network to the app; credentials to rotate; no UC lineage. Lakebase gives managed Postgres *inside* the platform with short-lived OAuth credentials and a first-class synced table from Delta. |
| Continuous (CDC) sync | Needs Change Data Feed and a running pipeline per table. The queue only changes after a scoring batch, so a `SNAPSHOT` (triggered) refresh is cheaper and sufficient; CDF is enabled on the source so we can switch to continuous later. |

---

## Application Stack

### Backend: Python + FastAPI

| Component | Package | Purpose |
|-----------|---------|---------|
| Web Framework | `fastapi` | REST API with OpenAPI schema generation |
| ASGI Server | `uvicorn` | Production-grade async server |
| Validation | `pydantic` / `pydantic-settings` | Request/response models, typed config |
| Databricks SDK | `databricks-sdk` | SQL Warehouse statement execution, Genie API, AI Gateway, Lakebase credentials |
| HTTP | `httpx` | Async HTTP client for Databricks API calls |
| Postgres driver | `psycopg` (v3) | Lakebase connections for the operational-serving path |

**Data access, two paths:** analytical reads/writes use the Databricks SDK
Statement Execution API against SQL Warehouse (Delta), mapped to Pydantic models.
The operational-serving path uses `psycopg` against Lakebase (Postgres) with
short-lived OAuth credentials minted via
`WorkspaceClient.database.generate_database_credential` (no stored passwords).
We deliberately keep raw SQL over an ORM: the queries are few and explicit, and
the same style spans both the SQL Warehouse and Postgres clients.

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
| Profile | `<your-profile>` | Workspace authentication |

---

## Data Access Pattern

All data access is read-only via SQL Warehouse Statement Execution API:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="<your-profile>")

result = w.statement_execution.execute_statement(
    warehouse_id=WAREHOUSE_ID,
    catalog="<your_catalog>",
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
