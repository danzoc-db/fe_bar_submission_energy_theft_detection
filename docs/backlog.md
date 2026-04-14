# Feature Backlog

Features deferred from the current sprint. Ordered by estimated demo impact.

---

## Current Implementation Status

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | Landing Page — hero, sourced metrics, architecture diagram, persona cards | **Done** | Dark hero, £323M/£163M/£6.2M/£97M with source tooltips, UKI Energy Group scale row, horizontal E2E architecture with tooltips, "Meet the Team" cards |
| 2 | Executive Dashboard (`/dashboard`) — Susie's View | **Done** | 5 KPI tiles (exposure, AOP%, YTD recovery, recovery rate, detection precision), Revenue Recovery Opportunity donut, Investigation Outcomes bar+line chart, Case Pipeline row, embedded Genie chat with UC Metric View highlighting |
| 3 | Investigation Workbench (`/investigation`) — Robbie's View | **Done** | 5 operational KPI tiles with click-to-filter, AI Daily Briefing (Bedrock), flagged accounts table with risk/status filtering, account detail drawer (composite score, signal breakdown, LLM case summary, 90-day consumption chart, field dispatch generator with PDF download) |
| 4 | AI Governance (`/governance`) | **Done** | AI Component Registry, PII Access Matrix (red/amber/green badges), UC Lineage DAG (interactive Plotly network graph), AI Gateway Audit log, column-level metadata |
| 5 | Presentation (`/presentation`) — 9-slide deck | **Done** | Title, Financial Challenge, Meet Susie, Meet Robbie, Architecture, Demo Walkthrough, Governance, Why Databricks, Next Steps — scrollable + slide view toggle |
| 6 | Why Databricks (`/why-databricks`) | **Done** | Speed, Genie, governance, cost — each with Fabric compete callout |
| 7 | Medallion Data Pipeline (Bronze/Silver/Gold) | **Done** | `01a_bronze_ingest`, `01b_silver_cleanse`, `01c_gold_aggregate`, `01d_metric_views` — 2K accounts, 2.88M reads, 11 regions |
| 8 | ML Models — Isolation Forest + LSTM Autoencoder | **Done** | Trained, registered in MLflow, batch scoring writes to `anomaly_scores` |
| 9 | UC Metric Views — `theft_detection_metrics`, `risk_exposure_metrics` | **Done** | YAML-based MEASURE() definitions, referenced by Genie and dashboard |
| 10 | Genie Space — Susie's Executive Intelligence | **Done** | Embedded via Conversation API, UC Metric View grounding, 4 suggested questions |
| 11 | LLM Case Summary + Daily Briefing — Bedrock via AI Gateway | **Done** | Structured JSON output, Bedrock badge, governance link, lazy-loaded with skeleton |
| 12 | Field Dispatch Document Generator | **Done** | LLM generates narrative + actions + evidence checklist + safety notes, in-app render + PDF download + schedule investigation |
| 13 | UC PII Tagging + Column Metadata | **Done** | 13 PII fields across 5 tables, Ofgem DAPF / ELEXON BSC basis |
| 14 | Under the Hood panels | **Done** | Data Engineering, Genie, MLflow, Bedrock, Metric Views, App Architecture — each with Fabric compete callout |

---

## Tier 2 (Next Sprint)

| # | Feature | Persona | Status | Notes |
|---|---------|---------|--------|-------|
| 1 | Robbie's Operational Genie Space | Robbie | Backlog | Geographic clustering, workload triage, field dispatch optimisation |
| 2 | Model Performance Trend Page | Susie | Partial | Monthly precision/recall shown in dashboard Investigation Outcomes chart — dedicated page deferred |
| 3 | ~~Field Dispatch Document Generator~~ | ~~Robbie~~ | **Done** | Moved to current sprint — implemented with LLM narrative, evidence checklist, PDF download |
| 4 | ETU Referral Builder | Robbie | Backlog | Structured output for RECCo ETU submission (R0233 compliance) |
| 5 | Regional Drill-Down from Heatmap | Susie | Backlog | Click region → filtered account table |

## Tier 3 (Future)

| # | Feature | Notes |
|---|---------|-------|
| 6 | Organised Crime Cluster Detection | Graph-based analysis of co-located anomalies |
| 7 | Real-Time Streaming Ingestion | Zerobus / Structured Streaming for near-real-time scoring |
| 8 | Historical Analysis (7-year view) | Deep archive for seasonal trend comparison |
| 9 | ~~Agent Orchestration (Supervisor)~~ | See Agent Proposals below — promoted to Tier 1 candidate |
| 10 | Streamlit Rebuild | Simpler deployment option if APX proves too complex to maintain |
| 11 | Mobile-Responsive Investigation View | Field engineers reviewing cases on tablets |
| 12 | A/B Model Comparison | Side-by-side scoring from two model versions |

---

---

## We Could Enhance the Energy Theft Protection Team with AI Agents

The current platform gives Susie governed dashboards and Robbie LLM-assisted investigation tools. But both still spend hours on manual, repetitive orchestration work that AI agents could eliminate. Built on **Databricks Agent Bricks** and the **Databricks Agentic Framework**, these agents would run as governed, auditable workflows inside Unity Catalog — the same governance perimeter that already protects the data and models.

---

### Meet the Agents

<table>
<tr>
<td width="50%" valign="top">

#### 🤖 Agent Atlas — Monthly Board Report Generator

**Built for Susie** · Supervisor Agent (Multi-Agent System)

Susie spends **2–3 days every month** assembling the Revenue Protection board pack for the CFO: pulling KPIs from dashboards, writing narratives around regional trends, comparing model performance month-on-month, and formatting it all into a slide deck. Agent Atlas does this in minutes.

**What Atlas does:**

- 📊 Queries UC Metric Views for all board KPIs — revenue recovered, detection precision, exposure vs AOP, regional breakdown
- 📈 Analyses month-on-month trends and flags significant movements (e.g. "West Midlands recovery up 23%, driven by 4 organised crime closures")
- 🌍 Gathers UK energy theft market intelligence, regulatory context, and industry benchmarking via Google Gemini
- ✍️ Generates executive narrative — plain English, CFO-ready, with sourced figures, market context, and caveats — via Amazon Bedrock
- 📄 Produces a structured board pack (Markdown → PDF/PPTX) with KPI summary, regional heatmap commentary, market intelligence, model performance trends, and recommended actions
- 🔒 All data access governed by Unity Catalog — same PII controls, same audit trail. Both LLM providers governed by the same AI Gateway.

**How it works on Databricks:**

```
┌──────────────────────────────────────────────────────────────┐
│              Agent Atlas — Supervisor Agent                    │
│               (Databricks Agent Bricks)                       │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────┐  │
│  │ KPI       │  │ Trend    │  │ Market    │  │ Narrative  │  │
│  │ Collector │  │ Analyser │  │ Intel     │  │ Writer     │  │
│  │           │  │          │  │           │  │            │  │
│  │ Genie API │  │ SQL +    │  │ Gemini    │  │ Bedrock    │  │
│  │ + Metric  │  │ Python   │  │ (Google)  │  │ (AWS)      │  │
│  │ Views     │  │ analysis │  │ via GW    │  │ via GW     │  │
│  └────┬──────┘  └────┬─────┘  └─────┬─────┘  └─────┬──────┘  │
│       └──────────────┼──────────────┼──────────────┘         │
│                      ▼              ▼                        │
│            ┌─────────────────────────────┐                   │
│            │     Report Assembler        │                   │
│            │     (Markdown/PPTX)         │                   │
│            └─────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
         ▼                    ▼
  Unity Catalog          AI Gateway
  (governed data)     (audited LLM calls —
                       Bedrock + Gemini)
```

**Databricks building blocks:** Agent Bricks Supervisor · Genie Conversation API (tool) · UC Metric Views (KPI source) · Bedrock via AI Gateway (narrative) · Gemini via AI Gateway (market intelligence) · MLflow Tracing (observability) · UC Functions (data retrieval tools) · Databricks Jobs (monthly schedule)

**Value:** Susie's 2–3 day monthly report assembly → 15-minute review-and-send. Every figure sourced, every LLM call audited, every data access governed. Two cloud providers (AWS Bedrock + Google Gemini), one governance layer. The CFO gets the same answer whether Susie asks Genie or Atlas writes the report.

> *"I used to spend the first week of every month building the board pack. Now I review what Atlas drafted over coffee and send it before lunch."*
> — Susie Chambers, Head of Fraud & Intelligence

</td>
<td width="50%" valign="top">

#### 🤖 Agent Sentinel — Investigation Triage & Dispatch Supervisor

**Built for Robbie** · Supervisor Agent (Multi-Agent System)

Robbie's target is **25–30 cases per week**, but each case takes 30–40 minutes of manual triage: checking signals, reviewing the consumption chart, reading the LLM summary, generating the dispatch doc, and grouping nearby cases for efficient truck rolls. Agent Sentinel orchestrates the entire batch — triage, summarise, cluster, dispatch — so Robbie reviews and approves rather than assembles.

**What Sentinel does:**

- 🔍 Pulls overnight HIGH-risk flags and ranks them by composite score, recency, and geographic density
- 🗺️ Clusters flagged accounts by postcode sector to minimise field engineer truck-roll cost — "5 accounts in NW3, 3 in NW6, schedule as 2 routes"
- 📝 Generates batch case summaries — one LLM call per cluster, not per account, reducing token cost and improving context
- 🚚 Produces grouped field dispatch packs with route-optimised visit order, evidence checklists, and safety notes per property type
- ⚠️ Flags potential organised crime patterns — 3+ HIGH accounts within 0.5 miles triggers an ETU alert with pre-filled referral data
- 🔒 Every action logged — UC lineage from score → triage → dispatch → field outcome

**How it works on Databricks:**

```
┌─────────────────────────────────────────────┐
│      Agent Sentinel — Supervisor Agent       │
│         (Databricks Agent Bricks)            │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Triage   │  │ Cluster  │  │ Dispatch  │  │
│  │ Agent    │  │ Agent    │  │ Agent     │  │
│  │          │  │          │  │           │  │
│  │ SQL +    │  │ Geospatial│ │ Bedrock   │  │
│  │ anomaly_ │  │ grouping │  │ via AI    │  │
│  │ scores   │  │ + routing│  │ Gateway   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       └──────────────┼──────────────┘        │
│                      ▼                       │
│            ┌─────────────────┐               │
│            │  ETU Alert      │               │
│            │  Monitor        │               │
│            │  (crime cluster)│               │
│            └─────────────────┘               │
└──────────────────────────────────────────────┘
         ▼                    ▼
  Unity Catalog          AI Gateway
  (governed data)     (audited LLM calls)
```

**Databricks building blocks:** Agent Bricks Supervisor · UC Functions (SQL tools for anomaly_scores, investigation_cases, property_reference) · H3 geospatial indexing (postcode clustering) · Bedrock via AI Gateway (batch summaries + dispatch generation) · MLflow Tracing (full orchestration observability) · Databricks Jobs (hourly/daily trigger) · Delta table write-back (investigation_cases status updates)

**Value:** Robbie processes a full day's triage queue in 20 minutes instead of 4 hours. Geographic clustering alone reduces field engineer travel cost by an estimated 30–40%. The ETU alert monitor catches organised crime patterns that manual review misses.

> *"Sentinel had my morning queue triaged, clustered, and dispatch-ready before I'd finished my first coffee. I just review, approve, and the field team is rolling."*
> — Robbie Henderson, Senior Revenue Protection Analyst

</td>
</tr>
</table>

---

### Why Agent Bricks on Databricks?

| Capability | How Agents Use It |
|-----------|------------------|
| **Unity Catalog governance** | Every tool call — SQL query, LLM prompt, data write — governed by the same UC permissions, PII tags, and audit trail as the rest of the platform |
| **AI Gateway + guardrails** | All Bedrock calls routed through AI Gateway with PII blocking, prompt injection filters, and rate limiting. Every call logged to inference tables |
| **MLflow Tracing** | Full observability: trace every agent step, measure latency, token usage, and quality. Debug failures without guesswork |
| **Genie as a tool** | Agents can call Genie Conversation API as a tool — natural language queries grounded in UC Metric Views, no hallucinated KPIs |
| **UC Functions as tools** | Register SQL functions in Unity Catalog and expose them as agent tools — governed, versioned, reusable |
| **Databricks Jobs** | Schedule agents on cron (Atlas: monthly, Sentinel: daily) or trigger via API. Serverless — scale to zero between runs |
| **One platform** | No stitching Azure AI Foundry + Logic Apps + Power Automate + Purview. Agents, data, models, LLMs, governance — one security perimeter |

---

*Both agents would be registered in Unity Catalog, traced in MLflow, and auditable end-to-end. The same governance that protects the data today protects the autonomous agents tomorrow.*
