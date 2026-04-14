# British Gas Energy Theft Detection

AI-driven anomaly detection demo built on Databricks — APX (FastAPI + React).

See `docs/PRD.md` for the full product requirements document.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [bun](https://bun.sh/) (JavaScript runtime, used by APX for frontend)
- Python 3.11+
- Node.js 18+ (bun handles this)

## Local Development

```bash
# 1. Install Python dependencies
uv sync

# 2. Install frontend dependencies
bun install

# 3. Start the dev server (backend + frontend with hot reload)
bun run dev          # or: uv run apx dev start
```

The app starts at **http://localhost:9003**. Without a `SQL_WAREHOUSE_ID` configured, all endpoints return default values — this is the **offline mode** local experience, no Databricks connectivity required.

### Convenience Scripts

| Command | What it does |
|---------|-------------|
| `bun run dev` | Start dev server (FastAPI + Vite HMR) on port 9003 |
| `bun run test` | Run the full pytest suite |
| `bun run check` | TypeScript + Python type checking |
| `bun run build` | Production build into `.build/` |

### Environment Variables

The app uses a two-layer env config:

1. **`.env`** — safe defaults, committed to git. Works out of the box in offline mode.
2. **`.env.local`** — your workspace-specific overrides, **gitignored**. Values here take precedence.

To connect to a real Databricks workspace:

```bash
cp .env.local.example .env.local
# Edit .env.local with your workspace credentials
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABRICKS_CONFIG_PROFILE` | No | Databricks CLI profile name (default: `DEFAULT`) |
| `SQL_WAREHOUSE_ID` | No | SQL Warehouse ID for live data |
| `AI_GATEWAY_ENDPOINT` | No | AI Gateway endpoint name for Bedrock LLM |
| `GEMINI_GATEWAY_ENDPOINT` | No | AI Gateway endpoint for Gemini LLM |
| `MAS_ENDPOINT` | No | Agent Bricks Multi-Agent Supervisor endpoint |
| `GENIE_SPACE_ID` | No | Genie Space ID for executive NL queries |
| `CATALOG` | No | Unity Catalog catalog name |
| `SCHEMA_NAME` | No | UC schema (default: `energy_theft_protection`) |

### Running Tests

```bash
bun run test         # or: uv run pytest tests/ -v
```

All tests pass with no external dependencies — they run against the FastAPI test client in offline mode.

### Type Checking

```bash
bun run check        # or: uv run apx dev check
```

TypeScript compilation must succeed. Python type errors from `notebooks/` are expected (PySpark types only available on Databricks runtime).

## Remote Deployment (Databricks Apps)

### Prerequisites

1. Databricks CLI configured with a workspace profile (e.g., `azure-field-demos`)
2. A SQL Warehouse created in the target workspace
3. Unity Catalog schema `dz_demos.energy_theft_protection` created

### Deploy

```bash
# Set your SQL warehouse ID
export SQL_WAREHOUSE_ID=<your-warehouse-id>

# Build and deploy
uv run apx build
databricks bundle deploy -t dev --var sql_warehouse_id=$SQL_WAREHOUSE_ID

# Open the deployed app
databricks bundle run energy-theft-detection-app -t dev
```

### Data Setup (on Databricks cluster)

1. Run `sql/01_create_tables.sql` to create the Unity Catalog tables
2. Run `notebooks/01_generate_synthetic_data.py` as a notebook on a cluster to populate 100K synthetic accounts

## Architecture

- **Backend:** FastAPI (Python) — stateless, reads from Delta tables via SQL Warehouse Statement Execution API
- **Frontend:** React + TypeScript + Vite + shadcn/ui + TanStack Router/Query
- **Data:** Unity Catalog (`dz_demos.energy_theft_protection`)
- **ML:** Isolation Forest + LSTM ensemble (pre-computed scores in Delta)
- **NL:** Genie Conversation API (executive queries over Metric Views)
- **LLM:** Bedrock via AI Gateway (investigation case summaries)
- **Deploy:** Databricks Apps via DABs (Databricks Asset Bundles)

## Personas

- **Susie Chambers** (Head of Revenue Protection) — Executive Dashboard, Genie NL queries
- **Robbie Henderson** (Senior Analyst) — Investigation Workbench, LLM case summaries

## Pages

| Page | Persona | Description |
|------|---------|-------------|
| Executive Dashboard | Susie | KPI tiles, risk heatmap, trend chart, fuel split, Genie panel |
| Investigation Workbench | Robbie | Flagged accounts table, detail drawer, signal breakdown, LLM summary |
| AI Governance | Both | PII matrix, component registry, UC lineage DAG, AI Gateway audit |
| Why Databricks | Demo | Advisory compete page (5 sections + architecture summary) |
| Presentation | Demo | 9-slide overview for show-me-don't-tell-me delivery |

## Documentation

All documentation lives in `docs/`:

- `PRD.md` — Full product requirements
- `tech_stack.md` — Architecture decisions
- `development_methodology.md` — Plan/Agent TDD process
- `demo_architecture.md` — End-to-end walkthrough
- `databricks_workspace_setup.md` — Workspace configuration guide
- `backlog.md` — Deferred features
- `issues_and_fixes.md` — Known issues and resolutions
