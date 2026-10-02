# How this demo was built with AI

FE Bar rewards treating AI as a teammate. This is the working method for the
UKI Gas energy-theft demo - tools, prompts, and patterns, not a feature list.

## Tools

| Tool | Role |
|------|------|
| Cursor (Agent) | Implementation, deploy, evidence capture, ADRs/roadmap |
| Isaac / Claude Design | Interview PoC narrative, backlog, compete framing |
| Databricks CLI + Python SDK | Bundle deploy, Apps, SQL Warehouse, Lakebase, Genie |
| Databricks AI Dev Kit skills | Lakebase provisioned, Asset Bundles, APX apps, UC |
| pytest + ruff | Offline acceptance before any remote change |

## Patterns that actually landed

- **One journey, then serve it.** Medallion + ML stay the analytics system of
  record in Delta. Lakebase was added as the operational-serving stage
  (`scripts/provision_lakebase.py`) so the app queue and case close are OLTP,
  then reverse-synced to Delta for Genie.
- **Feature-flag the new layer.** `LAKEBASE_ENABLED` defaults off so other
  bundle targets stay Delta-only. The aws target patches it on at build time.
- **Do not invent credentials.** Short-lived OAuth via
  `generate_database_credential`. App SP Postgres grants are a script flag
  (`--grant-principal`), not a pasted password.
- **Evidence over screenshots.** Live SQL, Genie Q-to-SQL, Lakebase psycopg,
  and app deployment status are committed under `docs/evidence/`.
- **Trade-offs as ADRs.** `docs/architecture-decisions.md` is the
  customer-shareable compete pack; internal `go/` source tags stay out of it.

## Prompts that drove the Lakebase slice

Typical working prompt (paraphrased):

> Take over the Lakebase operational-serving layer. Script owns instance +
> synced table; bundle keeps the app database binding. Grant the app SP on
> Postgres. Deploy to zoccali-fevm-aws. Prove /case returns source=lakebase
> and confirmed-theft writes hit Postgres, not only Delta.

Follow-ups: add `--grant-principal`, capture six-stage evidence, put
`provision_lakebase` on the `end_to_end` job so the DAG is one connected
journey.

## What we did not do with AI

- No production customer data. Synthetic UKI accounts only.
- No deck PDF in this pass (gap tracked separately).
- No silent commit of generated `_version.py` or `.build/`.
