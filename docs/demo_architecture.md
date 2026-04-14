# Demo Architecture

End-to-end architecture overview and demo walkthrough guide.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Databricks Platform                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Databricks App (APX)                       │    │
│  │                                                              │    │
│  │  ┌─────────────┐  ┌──────────────────────────────────────┐  │    │
│  │  │   FastAPI    │  │      React + TypeScript               │  │    │
│  │  │   Backend    │  │                                      │  │    │
│  │  │             ─┼──┼─▶ Executive Dashboard (Susie)        │  │    │
│  │  │  /api/dash   │  │   KPI tiles, heatmap, Genie panel    │  │    │
│  │  │  /api/inv    │  │                                      │  │    │
│  │  │  /api/gov    │  │─▶ Investigation Workbench (Robbie)   │  │    │
│  │  │  /api/genie  │  │   Accounts, detail drawer, LLM       │  │    │
│  │  │  /api/llm    │  │                                      │  │    │
│  │  │             ─┼──┼─▶ AI Governance                      │  │    │
│  │  │              │  │   PII matrix, lineage DAG, audit      │  │    │
│  │  │             ─┼──┼─▶ Why Databricks                     │  │    │
│  │  │              │  │─▶ Presentation                        │  │    │
│  │  └──────┬───────┘  └──────────────────────────────────────┘  │    │
│  └─────────┼────────────────────────────────────────────────────┘    │
│            │                                                         │
│  ┌─────────┼─────────────────────────────────────────────────────┐  │
│  │         │              Data & AI Layer                         │  │
│  │         │                                                     │  │
│  │  ┌──────┴──────┐  ┌────────────┐  ┌───────────────────────┐  │  │
│  │  │SQL Warehouse│  │AI Gateway  │  │Genie Conversation API│  │  │
│  │  │(read-only)  │  │(Bedrock)   │  │(Susie's NL queries)  │  │  │
│  │  └──────┬──────┘  └─────┬──────┘  └───────────┬───────────┘  │  │
│  │         │               │                      │              │  │
│  │  ┌──────┴───────────────┴──────────────────────┴───────────┐  │  │
│  │  │                   Unity Catalog                          │  │  │
│  │  │  dz_demos.energy_theft_protection                        │  │  │
│  │  │                                                          │  │  │
│  │  │  Delta Tables:              ML Models (MLflow):          │  │  │
│  │  │  ├─ smart_meter_reads       ├─ isolation_forest_v3       │  │  │
│  │  │  ├─ meters                  └─ lstm_consumption_v2       │  │  │
│  │  │  ├─ anomaly_scores                                      │  │  │
│  │  │  ├─ investigation_cases     Metric Views:                │  │  │
│  │  │  ├─ property_reference      ├─ theft_precision_rate      │  │  │
│  │  │  └─ model_performance_log   └─ revenue_recovery          │  │  │
│  │  │                                                          │  │  │
│  │  │  System Tables:                                          │  │  │
│  │  │  └─ system.serving.endpoint_usage (AI Gateway audit)     │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Demo Walkthrough (12 Minutes)

### Opening (1 min)
Start on the **Presentation** page. Walk through the first 3 slides:
- Business problem: £323m theft exposure vs £163m divisional profit
- Industry context: suppliers detecting only 40% of target, ETU reform
- What this demo shows: unified platform for data, ML, LLMs, and NL queries

### Act 1: Susie's World (4 min)
Switch to the **Executive Dashboard**:
1. KPI tiles — "here's what Susie sees when she opens her morning dashboard"
2. Risk heatmap — "hotspots in the estate, clickable to drill down"
3. Trend chart — "is detection improving month over month?"
4. Genie panel — ask: "What is our revenue recovered year-to-date?"
   → Genie queries UC Metric View, returns governed answer
   → "This is the same answer everyone gets — no conflicting spreadsheets"

### Act 2: Robbie's World (4 min)
Switch to **Investigation Workbench**:
1. Flagged accounts table — "Robbie opens this every morning"
2. Click a HIGH risk account → detail drawer opens
3. 90-day consumption chart — "see the step-down? That's the bypass signature"
4. LLM case summary — "Bedrock via AI Gateway, not a random API key"
   → "40-minute manual investigation, done in 10 seconds"
5. Signal radar — "which signals are driving this flag?"

### Act 3: Governance (2 min)
Switch to **AI Governance**:
1. PII access matrix — "every model, every PII field, regulatory justification"
2. UC lineage DAG — "column-level data flow from raw reads to LLM output"
3. AI Gateway audit — "every Bedrock call logged: who, when, tokens, guardrails"
4. "This is one platform. One audit trail. One perimeter."

### Closing (1 min)
Switch to **Why Databricks**:
- Quickly highlight Section 1 (fragmentation risk) and Section 4 (governance)
- "Every week of delay costs ~£6.2m in unrecovered revenue"

---

## Key Demo Talking Points

| When | Say |
|------|-----|
| Genie answers a question | "That answer came from a UC Metric View — governed definition, not hallucination" |
| LLM summary loads | "Bedrock via AI Gateway — audit trail, rate limits, guardrails, all in one place" |
| PII matrix shown | "Ofgem and ELEXON define these fields as PII — we show exactly which models touch them" |
| Heatmap loads | "100K accounts, pre-scored. In production, this would be 7.5 million" |
| Why Databricks | "This isn't a feature comparison — it's about how long it takes to get to first investigation" |
