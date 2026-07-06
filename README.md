# UKI Gas Energy Theft Detection

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

---

## Deployment: zoccali-fevm-aws (AWS FEVM — catalog dev target)

Private development workspace used for dbdemos catalog iteration.
Once stable, the demo will migrate to E2 Demo West with area lead approval.

**Workspace:** `fevm-zoccali-fevm-aws.cloud.databricks.com`  
**Catalog / Schema:** `zoccali_fevm.energy_theft_protection`  
**SQL Warehouse:** `85c1b174d196486d` (5X-Large serverless)  
**Genie Space:** `01f16db6c03419a3b953033d66b5855f`  
**App URL:** https://energy-theft-detection-7474643973020026.aws.databricksapps.com  
**dbdemos Catalog ID:** *(TBD — update after submission)*  
**Maintainer:** Daniel Zoccali (`daniel.zoccali@databricks.com`)

### Deploy commands

```bash
# 1. Build frontend + patch app.yml + verify permissions
BUN_CONFIG_NO_VERIFY=1 uv run apx build

# 2. Deploy bundle (endpoints, job, pipeline, app)
uv run databricks bundle deploy -t zoccali-fevm-aws

# 3. Deploy app source code
databricks apps deploy energy-theft-detection --profile zoccali-fevm-aws \
  --source-code-path "/Workspace/Users/daniel.zoccali@databricks.com/.bundle/energy-theft-detection/zoccali-fevm-aws/files/.build"
```

### Variables

| Variable | Value |
|----------|-------|
| `catalog` | `zoccali_fevm` |
| `sql_warehouse_id` | `85c1b174d196486d` |
| `genie_space_id` | `01f16db6c03419a3b953033d66b5855f` |
| `mas_endpoint` | *(empty — set after running 08_configure_agent_atlas.py)* |
| `fmapi_secret_scope` | `energy-theft-fmapi` |

### Post-deploy validation

```bash
# Full deployment health check (includes FMAPI endpoints + external lineage)
python3 scripts/validate_deployment.py \
  --profile zoccali-fevm-aws \
  --target zoccali-fevm-aws \
  --app-url https://energy-theft-detection-7474643973020026.aws.databricksapps.com \
  --token <YOUR_PAT>
```

### Smoke test checklist

1. `GET /api/health` — SQL connected, catalog `zoccali_fevm`
2. `/dashboard` — KPI tiles load, Genie panel responds
3. `/investigation` — case list loads, LLM summary calls `energy-theft-openai-gateway`
4. `/governance` — audit trail populated, external lineage shows 4 Power BI reports
5. `/board-report` — Agent Atlas trace (MAS or graceful fallback)
6. `/presentation` — "Build an App Like This" page loads
7. `/why-databricks` — compete messaging renders (if enabled)

### Cross-workspace reconciliation

After redeploying, compare the new app against the baseline to verify Power BI lineage parity:

```bash
# Snapshot the current (before) state
python3 scripts/reconcile_workspaces.py \
  --snapshot https://energy-theft-detection-7474643973020026.aws.databricksapps.com \
  --token <YOUR_PAT> \
  --out /tmp/before.json

# After redeploying, compare
python3 scripts/reconcile_workspaces.py \
  --compare /tmp/before.json \
  --after https://energy-theft-detection-7474643973020026.aws.databricksapps.com \
  --token <YOUR_PAT>
```

A clean reconciliation shows 0 differences and `source=live` for external lineage.

## Architecture

- **Backend:** FastAPI (Python) — stateless, reads from Delta tables via SQL Warehouse Statement Execution API
- **Frontend:** React + TypeScript + Vite + shadcn/ui + TanStack Router/Query
- **Data:** Unity Catalog (`dz_demos.energy_theft_protection`)
- **ML:** Isolation Forest + LSTM ensemble (pre-computed scores in Delta)
- **NL:** Genie Conversation API (executive queries over Metric Views)
- **LLM:** FMAPI (openai-gateway → `databricks-claude-sonnet-4`) via AI Gateway (investigation case summaries); Bedrock gateway also deployed but not the default
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
