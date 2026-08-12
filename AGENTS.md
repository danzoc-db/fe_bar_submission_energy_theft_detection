# Agent Rules for UKI Gas Energy Theft Detection

<!--
SYNC NOTE: This file is the cross-tool mirror of `.cursorrules`.
Both files MUST stay in sync. If you change one, change the other in the same PR.
Loaded automatically by:
  - Claude Code        (AGENTS.md)
  - OpenAI Codex CLI   (AGENTS.md)
  - Cursor             (.cursorrules; recent versions also read AGENTS.md)
Content below is identical to `.cursorrules`.
-->

## Mission

This repository is the **UKI Gas Energy Theft Detection** demo: an AI-driven anomaly
detection application for UK energy retailers, built on Databricks APX (FastAPI + React).
It showcases ML scoring, investigator workflows, Genie natural-language queries, and
AI governance in a single deployable application.

The demo targets **external customer sharing** - all code, docs, and config must be
free of internal/customer-specific data and deployable to any Databricks workspace.

## Golden Rules

* Don't put emojis in SQL, Python, or general code files
* **NEVER GIVE UP!** Always investigate thoroughly before concluding something is missing or broken
  * Always search with CLI/API, check multiple sources, verify before concluding
  * If something worked before and "disappeared", it's likely still there - just hidden
* Do not hallucinate - verify against the actual code before making claims
* **ALWAYS ask before committing** - never `git commit` or `git push` without explicit user approval
* **ALWAYS try programmatic approaches before suggesting manual/UI steps** - check the SDK, REST API, CLI, and config files BEFORE concluding something needs manual action

## Repo-Specific Rules

* **Workspace portability** - all scripts, notebooks, and tests must work with any
  `--profile` and `--catalog`. No hard-coded workspace IDs, catalog names, or user emails.
* **Keep databricks.yml variables clean** - workspace-specific values go in target
  overrides, not the root `variables:` block.
* **Secrets in Secret Scopes only** - never commit tokens, API keys, or credentials.
  Use Databricks Secret Scopes (`energy-theft-fmapi`, `energy-theft-bedrock`, etc.).
* **Run the test suite before opening a PR:** `bun run test` or `uv run pytest tests/ -v`
* **Lint before opening a PR:** `ruff check . && ruff format .`
* **TypeScript must compile:** `bun run check`
* **Don't over-document** - keep docs neat and consolidated. Internal dev docs go in
  `docs/internal/` (gitignored).

## Architecture Notes

* **Backend:** FastAPI (`src/energy_theft_detection/backend/`)
* **Frontend:** React + TanStack Router (`src/energy_theft_detection/ui/`)
* **Notebooks:** Medallion pipeline, ML training, Genie config (`notebooks/`)
* **Pipelines:** Declarative SQL pipelines (`pipelines/`)
* **Deployment:** Databricks Asset Bundles (`databricks.yml`)

## Branch, Commit & Secrets Conventions

* Branch from an up-to-date `main`; never commit directly to `main`.
* Branch naming: `feat/<work>` for new work, `fix/<fix>` for fixes. All lowercase.
* Squash-merge only; write a meaningful PR title/description.
* **Never commit secrets** (tokens, API keys, passwords). Use a gitignored `.env.local`.
  See [`ACCESS_TOKEN_HANDLING.md`](ACCESS_TOKEN_HANDLING.md) for the full policy.
* If you're "vibe coding", read [`AI_CODING_GOTCHAS.md`](AI_CODING_GOTCHAS.md) first.

## Databricks AI Dev Kit

* For Databricks-specific development patterns and best practices, refer to the
  **Databricks AI Dev Kit**: https://github.com/databricks-solutions/ai-dev-kit
* It provides markdown skills and MCP tools for SDP pipelines, Unity Catalog, Jobs,
  AI/BI Dashboards, Genie Spaces, MLflow, Model Serving, Databricks Apps, and more.
* Install into a project via:
  `bash <(curl -sL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/install.sh)`
