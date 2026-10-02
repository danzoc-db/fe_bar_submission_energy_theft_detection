# Roadmap - Energy Theft Revenue Protection

**Outcome:** take UKI Gas from a reactive, ~40% detection rate toward the Ofgem
regulatory target by making every stage of the journey - ingest, govern, score,
serve, ask, act - faster and more automated, then layering governed AI agents on
top so Susie and Robbie spend their time deciding, not assembling.

The journey shipped today is the foundation. Each phase adds measurable
revenue-protection capability on the same governed platform.

---

## Phase 1 - Platform foundation (DELIVERED)

End-to-end governed journey, live and verifiable:

Lakeflow medallion -> Unity Catalog (PII tagging + column-level lineage) ->
Isolation Forest + LSTM scoring -> **Lakebase operational serving** (synced risk
queue + transactional case management) -> Genie natural language -> Databricks
App for Susie (executive) and Robbie (analyst).

- The Lakebase layer gives the investigator app a sub-second, always-warm read of
  the flagged-account queue and read-your-writes case commits, with an
  append-only audit trail (see [`docs/evidence/`](evidence/)).
- Susie already has the Executive Dashboard, Genie, and a board-report seed
  (`/board-report` plus `notebooks/08_configure_agent_atlas.py`).
- Robbie already has the Investigation Workbench, LLM case summaries, and field
  dispatch generation.

## Phase 2 - Agentic revenue protection (next)

Both personas still spend hours on manual orchestration. Governed agents on
Databricks Agent Bricks, running inside the same Unity Catalog perimeter, remove
it.

- **Agent Atlas (for Susie)** - a multi-agent supervisor that turns the 2-3 day
  monthly board-pack assembly into a 15-minute review-and-send. Sub-agents: KPI
  Collector (Genie + UC Metric Views), Trend Analyser (SQL/Python), Market Intel
  (Gemini via AI Gateway), Narrative Writer (Bedrock via AI Gateway), producing a
  governed Markdown/PPTX board pack. Every figure sourced, every LLM call audited,
  two cloud LLM providers under one governance layer. The board-report page and
  `notebooks/08_configure_agent_atlas.py` are the seed.
- **Agent Sentinel (for Robbie)** - a triage / cluster / dispatch supervisor. It
  ranks overnight HIGH-risk flags, clusters them by postcode sector to cut
  field-engineer truck-roll cost, generates route-optimised dispatch packs, and
  raises an ETU alert when 3+ HIGH accounts cluster within 0.5 miles (an
  organised-crime signal).
- **ETU Referral Builder** - structured output for the RECCo ETU submission
  (Ofgem R0233 compliance), pre-filled from the case record.

## Phase 3 - Real-time and graph (platform expansion)

- **Near-real-time scoring** via Zerobus / Structured Streaming, replacing the
  overnight batch so high-risk behaviour is flagged within minutes.
- **Organised Crime Cluster Detection** - graph analysis of co-located anomalies
  to surface coordinated theft rather than isolated accounts.
- **Continuous serving sync** - switch the Lakebase synced table from SNAPSHOT to
  CONTINUOUS (Change Data Feed is already enabled on the source) for sub-minute
  queue freshness, no reload required.
- **7-year historical archive** for seasonal trend comparison.

## Phase 4 - Scale and field operations

- **Model A/B comparison + monitoring** page: side-by-side scoring from two model
  versions, with precision/recall drift alerts.
- **Mobile-responsive investigation view** for field engineers reviewing cases on
  tablets.
- **Regional drill-down** from the executive heatmap to a filtered case list.
- **Robbie's operational Genie space** - geographic clustering, workload triage,
  and field-dispatch optimisation in natural language.

---

## Buyer KPIs

| Phase | Capability | Buyer KPI | Direction |
|-------|------------|-----------|-----------|
| 2 Atlas | Board pack | Analyst-days per month | 2-3 days of assembly to a 15-minute review-and-send |
| 2 Sentinel | Investigation throughput | Cases per analyst per week | Hold 25-30 while cutting triage from hours to minutes |
| 2 Sentinel | Field cost | Truck-roll cost per confirmed case | Geographic clustering; estimated 30-40% less travel |
| 3 | Detection latency | Time from anomalous behaviour to a HIGH flag | Overnight batch to near-real-time |
| 3 | Organised crime | Confirmed cluster closures | 3+ HIGH accounts within 0.5 miles become an ETU alert |

---

See [`docs/architecture-decisions.md`](architecture-decisions.md) for the platform
choices behind this roadmap, and [`docs/tech_stack.md`](tech_stack.md) for the
current architecture and trade-offs.
