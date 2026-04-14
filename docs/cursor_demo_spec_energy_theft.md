# 🔍 Databricks Demo: AI-Driven Energy Theft Detection
### UKI Gas / UKI Energy — Demo Specification

---

## 1. The Business Problem: Energy Theft in the UK

Energy theft is the deliberate, criminal diversion of gas or electricity without
payment. It is physical, organised, and growing.

| Impact | Metric | Source |
|--------|--------|--------|
| Annual value stolen across Great Britain | **£1.4bn/year** | RECCo / Capgemini, Jan 2023; RECCo Feb 2026 |
| Added to every honest household's bill | **£50/year** | RECCo, Feb 2026 |
| Deaths from tampered supplies | **~36/year (every 10 days)** | Ofgem ETU Decision, R0233, June 2025 |
| UKI Gas estimated theft exposure | **£392m/year** | Derived: RECCo % × BG market share |
| ML-recoverable value (30% benchmark) | **£118m/year** | Industry benchmark |
| UKI Gas Home Energy divisional profit (2025) | **£163m** | UKI Energy Preliminary Results, Feb 2026 |

**The anchor stat:** £118m recoverable = **72% of UKI Gas's entire Home Energy
divisional operating profit.** Early, accurate detection of meter anomalies is one
of the most material levers available to protect that margin.

> Theft exposure is an estimate embedded in receivables and bad debt provisions —
> label as such in the UI. Directionally correct and appropriate for executive conversation.

**Primary theft methods:**

| Method | Description |
|--------|-------------|
| Meter bypass | Physical wires routed around the meter so consumption flows unrecorded |
| Meter manipulation | Tampering using magnets or drilling to slow/reverse readings |
| Smart meter data spoofing | Corrupting DCC data transmission to report lower consumption |
| Illegal reconnection | Reconnecting a supply disconnected by the supplier |

---

## 2. The Personas

These two personas are the lens through which every page of this application is
designed. Every KPI tile, every chart, and every agent action maps back to one of them.

---

### 🕵️ Robbie Henderson
**Senior Revenue Protection Analyst — Theft Detection**
*UKI Gas Home Energy Supply | Revenue Protection Team*

Robbie is a mid-career data analyst embedded in UKI Gas's Revenue Protection
team. His job is to take anomaly signals from the ML platform and turn them into
confirmed theft cases: reviewing flagged accounts, dispatching field engineers,
and closing cases. He is comfortable with data tools but is not a data scientist
— he relies on the platform to surface and score, while he focuses on
investigation and triage.

**A day in Robbie's life:**
1. Opens the **Investigation Workbench** to review overnight HIGH risk flags
2. Uses **Genie** to cluster accounts geographically and reduce truck-roll cost
3. Reviews the **90-day consumption chart** for the step-down signature of bypass
4. Reads the **LLM-generated Case Summary** to understand the key signals
5. Clicks **"Generate Field Dispatch"** — the agent builds the investigation doc
6. Field engineer reports outcome; Robbie closes the case and logs revenue recovered
7. For organised crime clusters, submits formal **ETU referral** via RECCo

**Robbie's KPIs:**

| KPI | Target |
|-----|--------|
| Theft Detection Precision Rate | **>60%** (confirmed theft / total HIGH cases closed) |
| Mean time from flag to field dispatch | **<3 working days** |
| Cases investigated per week | 25–30 per analyst |
| Revenue recovered per confirmed case | £2,400–£4,000 avg |
| False positive rate (HIGH tier) | **<40%** |
| ETU referrals submitted (YTD) | Regulatory compliance (REC R0233, June 2025) |

**What Robbie needs from the app:** The queue in front of him today. Which accounts
are most likely real theft, what does the evidence look like, and how fast can he
dispatch. The app collapses a 40-minute manual investigation per account into minutes.

---

### 📊 Susie Chambers
**Head of Revenue Protection & Financial Crime, UKI Gas Home Energy**
*UKI Energy plc | Director-level, reporting to Chief Customer Officer*

Susie owns the Revenue Protection function as a P&L-accountable director. She
presents to the UKI Gas Home Energy CFO quarterly on theft exposure and
recovery, and to the Group Risk Committee annually. She manages Robbie's team,
field engineering capacity, and regulatory compliance obligations under Ofgem's
new Energy Theft Unit (ETU). She does not write SQL. She opens dashboards and
asks questions in plain English.

**Susie's KPIs:**

| KPI | Current | Target |
|-----|---------|--------|
| Revenue recovered YTD | Live (app) | **£118m/year** |
| Recovery rate vs recoverable | Live | **>30%** |
| Theft exposure as % of divisional AOP | ~240% (£392m vs £163m) | Reduce YoY |
| Theft Detection Precision Rate (portfolio) | Live | >60% |
| HIGH risk accounts as % of estate | Live | Monitor / reduce |
| ETU referrals submitted YTD | Live | Regulatory compliance |

**What Susie needs from the app:** Can she answer a CFO question in 30 seconds?
Is YTD recovery on track? Where are the geographic hotspots? Is the model getting
better? She uses Genie for on-demand answers without waiting two days for a report
from her team.

---

## 3. Application Overview

**Platform:** Databricks App (Streamlit)
**Data:** Delta tables in Unity Catalog — `dz_demos.energy_theft`
**ML:** MLflow-registered Isolation Forest + LSTM ensemble, batch-scored
**NL Interface:** Genie Conversation API
**Summarisation:** Databricks Model Serving LLM endpoint (Claude via AI Gateway)
**Governance:** Unity Catalog — single plane for data, models, LLMs, and Genie

| Page | Designed For | Description |
|------|-------------|-------------|
| 1. Executive Dashboard | **Susie** | KPI tiles, theft heatmap, trend chart, recovery tracker |
| 2. Theft Investigation Workbench | **Robbie** | Genie triage, flagged account list, LLM case summaries, field dispatch |
| 3. Historical Analysis & Prediction | **Both** | Trend analysis, risk forecast, model performance |
| 4. Agentic Use Cases | **Both** | Field dispatch agent + signpost for future agents |
| 5. AI Governance | **Susie / Demo** | UC lineage, model registry, AI Gateway audit, permissions |

---

## 4. Data Model & Simulated Dataset

All tables in Unity Catalog: **`dz_demos.energy_theft`**

### 4.1 Core Delta Tables

```sql
-- dz_demos.energy_theft.smart_meter_reads
CREATE TABLE smart_meter_reads (
  account_id        STRING,
  read_timestamp    TIMESTAMP,       -- Half-hourly interval
  fuel_type         STRING,          -- 'electricity' | 'gas'
  consumption_kwh   DOUBLE,
  read_quality      STRING,          -- 'actual' | 'estimated' | 'missing'
  comms_gap_flag    BOOLEAN,
  postcode          STRING,          -- Masked to sector e.g. 'NW1 5'
  property_type     STRING,          -- 'terraced' | 'semi' | 'flat' | 'detached'
  council_tax_band  STRING           -- A-H
);

-- dz_demos.energy_theft.anomaly_scores
CREATE TABLE anomaly_scores (
  account_id              STRING,
  score_timestamp         TIMESTAMP,
  fuel_type               STRING,
  isolation_forest_score  DOUBLE,    -- 0–1, higher = more anomalous
  lstm_deviation_score    DOUBLE,    -- Z-score vs own 90-day baseline
  cohort_deviation_score  DOUBLE,    -- Z-score vs similar property cohort
  comms_gap_count_30d     INT,
  consumption_drop_pct    DOUBLE,    -- % drop vs prior 30-day rolling avg
  composite_risk_score    DOUBLE,    -- Weighted ensemble — PRIMARY signal
  risk_tier               STRING,    -- 'HIGH' | 'MEDIUM' | 'LOW'
  postcode_sector         STRING,
  model_version           STRING,
  investigation_status    STRING     -- 'OPEN' | 'IN_PROGRESS' | 'CLOSED' | 'CONFIRMED_THEFT'
);

-- dz_demos.energy_theft.investigation_cases
CREATE TABLE investigation_cases (
  case_id               STRING,
  account_id            STRING,
  opened_timestamp      TIMESTAMP,
  investigator_id       STRING,
  llm_summary           STRING,
  field_dispatch_doc    STRING,
  outcome               STRING,      -- 'THEFT_CONFIRMED' | 'FALSE_POSITIVE' | 'PENDING'
  revenue_recovered_gbp DOUBLE,
  closed_timestamp      TIMESTAMP
);

-- dz_demos.energy_theft.property_reference
CREATE TABLE property_reference (
  account_id       STRING,
  postcode         STRING,
  region           STRING,
  property_type    STRING,
  council_tax_band STRING,
  floor_area_m2    DOUBLE,
  epc_rating       STRING
);
```

### 4.2 Simulated Dataset

Generate **100,000 account records**:
- **95% normal** — seasonal sine wave + Gaussian noise, morning/evening peaks
- **3% tampered** — sudden step-down of 30–70% at a random point, flat curve,
  simulated comms gaps
- **2% edge cases** — legitimate drops (vacant, solar install) near the HIGH/MEDIUM
  boundary to test precision

Label all screens: **"Simulated Data — Demo Environment"**

---

## 5. Page 1: Executive Dashboard
*Susie's view. KPI-driven. No account detail.*

**KPI Tile Row:**
- Total accounts monitored: 7,500,000 (demo shows 100k)
- HIGH risk accounts flagged this week
- Estimated monthly theft exposure: £{composite_risk_score × avg_case_value}
- Revenue recovered YTD ← **Susie's primary number**
- Cases confirmed as theft (YTD)

**Risk Heatmap** — UK postcode sector choropleth coloured by average
`composite_risk_score`. Plotly Mapbox. Drillable to sector level.

**Theft Signal Trend** — 12-month rolling line chart of flagged accounts by
risk tier (HIGH / MEDIUM). Shows whether detection is improving over time.

**Dual Fuel Split** — Pie chart: electricity vs gas anomaly flags this month
(expect ~73% electricity / ~27% gas, consistent with RECCo volume split).

---

## 6. Page 2: Theft Investigation Workbench
*Robbie's view. This is where the real work happens.*

### 6.1 Genie Natural Language Query Panel

Embed the Genie Conversation API. The Genie space is trained on `anomaly_scores`,
`smart_meter_reads`, and `property_reference` in `dz_demos.energy_theft`.

**Pre-loaded example prompts (show these in the demo):**

---

**Genie Question 1 — Robbie's Morning Triage**
> *"Show me electricity accounts with a composite risk score above 0.75 in North
> West London postcode sectors NW1–NW10 this week, ranked by risk score, with
> their property type and council tax band."*

Why it lands: geographic clustering reduces truck-roll cost. Genie generates SQL
directly against live Delta tables — no pre-built semantic model required.

---

**Genie Question 2 — Susie's CFO Prep (UC Metric View — Anti-Hallucination)**
> *"What is the current Theft Detection Precision Rate, and how has it trended
> over the last 6 months?"*

This question **must** use the Unity Catalog Metric View below to prevent Genie
computing the formula differently each time. This is a live demonstration of
**anti-hallucination via UC governance** — a core differentiator vs Fabric /
Power BI Copilot, which requires a pre-built semantic model and breaks silently
on schema change.

```sql
-- dz_demos.energy_theft.metric_theft_precision_rate
CREATE METRIC VIEW metric_theft_precision_rate
COMMENT 'Theft Detection Precision Rate: confirmed theft / total HIGH risk cases closed.
         Primary KPI for model performance. Refreshed daily.'
AS
SELECT
  DATE_TRUNC('month', closed_timestamp)                     AS month,
  COUNT_IF(outcome = 'THEFT_CONFIRMED')                     AS confirmed_theft_cases,
  COUNT_IF(outcome IN ('THEFT_CONFIRMED','FALSE_POSITIVE')) AS total_closed_cases,
  ROUND(
    COUNT_IF(outcome = 'THEFT_CONFIRMED') * 100.0
    / NULLIF(COUNT_IF(outcome IN ('THEFT_CONFIRMED','FALSE_POSITIVE')), 0), 2
  )                                                         AS theft_detection_precision_pct
FROM dz_demos.energy_theft.investigation_cases
WHERE risk_tier = 'HIGH'
GROUP BY 1
ORDER BY 1;
```

**Target: >60%.** Below 60%, too many false positive field visits erode
investigator trust and inflate opex.

---

**Genie Question 3 — Emerging Threat Signal**
> *"Which postcode sectors have seen average composite risk scores increase by
> more than 20% in the last 14 days?"*

Why it lands: early detection of organised theft rings operating across multiple
adjacent properties — the pattern that drives ETU referrals.

---

### 6.2 Flagged Account List

Sortable table: `account_id`, `postcode`, `risk_tier`, `composite_risk_score`,
`consumption_drop_pct`, `comms_gap_count_30d`, `fuel_type`, `investigation_status`

Click any row → Account Detail Drawer.

### 6.3 Account Detail Drawer

1. **Consumption time series** — 90-day half-hourly reads, anomaly onset date
   marked, cohort average overlaid. The step-down signature is visually obvious.
2. **Signal breakdown** — radar chart of the five anomaly signals
3. **LLM Case Summary** — auto-generated via Model Serving endpoint:

```
Prompt:
"You are an energy theft investigation assistant for UKI Gas.
Given the following account anomaly data, generate a structured investigation
summary: risk assessment, key signals, recommended action, and priority.

Account: {account_id} | Postcode: {postcode} | Fuel: {fuel_type}
Composite risk score: {composite_risk_score}
Consumption drop (30d): {consumption_drop_pct}%
Comms gaps (30d): {comms_gap_count_30d}
Cohort deviation: {cohort_deviation_score}
Property: {property_type}, Council tax band: {council_tax_band}

Respond as JSON:
{risk_level, key_signals[], recommended_action, priority, estimated_loss_per_month_gbp}"
```

4. **"Generate Field Dispatch" button** — triggers the Field Engineer Agent (Section 8)

---

## 7. Page 3: Historical Analysis & Prediction
*Both personas. Robbie uses it operationally; Susie uses it for trend narratives.*

- **Monthly theft detection volume** — 24-month bar chart, split by fuel type
- **Seasonal pattern** — theft rates by month overlaid with Ofgem price cap
  change dates (theft spikes correlate with price increases — powerful visual)
- **30-day risk forecast** — MEDIUM-tier accounts whose LSTM trajectory suggests
  elevation to HIGH within 30 days
- **Model Performance** — Precision/Recall trend (6-month rolling from UC
  Metric View), confusion matrix for last 30 days of closed cases

---

## 8. Page 4: Agentic Use Cases

### ✅ PRIMARY AGENT: Field Engineer Dispatch Document Generator
*(Build this for the demo)*

**Trigger:** Robbie clicks "Generate Field Dispatch" on a HIGH risk account.

**Agent workflow:**
```
Step 1 — Retrieve account context
  → Query anomaly_scores, smart_meter_reads, investigation_cases
  → Retrieve property_reference (postcode, property type, EPC)

Step 2 — Retrieve local area intelligence
  → Query anomaly_scores for other HIGH risk accounts within 0.5 miles
  → Retrieve prior confirmed theft cases in same postcode sector

Step 3 — Call LLM to generate structured field document
  → Output: structured JSON → rendered as formatted document

Step 4 — Write document reference to investigation_cases.field_dispatch_doc
  → Update investigation_status to 'IN_PROGRESS'
```

**Document output:**
```markdown
# UKI Gas — Field Investigation Dispatch
**Case Reference:** {case_id} | **Priority:** HIGH | **Date:** {today}

## Risk Summary
- Composite Risk Score: {score} / 1.0
- Consumption drop: {pct}% over 30 days
- Communications gaps: {count} in 30 days

## Local Intelligence
- {n} other HIGH risk accounts within 0.5 miles
- Prior confirmed theft in postcode sector: {yes/no}

## Recommended Actions
1. {action_1}
2. {action_2}
3. {action_3}

## Evidence Required
- Photograph meter serial number
- Record voltage at meter terminals
- Document any visible signs of bypass or damage
```

### Signpost Cards (Coming Soon)

- **Organised Crime Ring Detector** — graph analysis across flagged accounts to
  identify clusters of connected properties, same landlord, or adjacent tenancies
- **Ofgem ETU Referral Packager** — auto-assembles the evidence package required
  by the Energy Theft Unit (REC R0233, June 2025) in standardised format
- **Customer Communications Drafter** — tactful outreach for elevated-but-unconfirmed
  accounts requesting a voluntary meter inspection

---

## 9. Page 5: AI Governance
*The demo's differentiator page. The Databricks vs Fabric argument made visible.*

### 9.1 AI Component Registry

| Component | Type | Model | UC Location | Tables Accessed |
|-----------|------|-------|-------------|-----------------|
| Theft Risk Scorer | ML Model | isolation_forest_theft_v3 | dz_demos.energy_theft.models | smart_meter_reads, property_reference |
| Sequence Anomaly | ML Model | lstm_consumption_v2 | dz_demos.energy_theft.models | smart_meter_reads |
| Case Summariser | LLM | Claude (AI Gateway) | — | anomaly_scores, investigation_cases |
| Field Dispatch Writer | LLM Agent | Claude (AI Gateway) | — | anomaly_scores, property_reference |
| Theft Investigator | Genie | genie_theft_space_v1 | dz_demos.energy_theft.genie | anomaly_scores, metric_theft_precision_rate |

Every component — ML models, external LLMs, and Genie — governed under a single
Unity Catalog instance. Replicating this in Fabric means crossing Azure ML,
Microsoft Purview, AI Foundry, and Power BI workspaces — each with their own
governance layer and authentication model.

### 9.2 Unity Catalog Lineage (render as interactive DAG)

```
[DCC Smart Meter Feed]
        ↓
[bronze.raw_smart_meter_reads]
        ↓
[silver.cleaned_meter_reads] ← [property_reference]
        ↓
[gold.30day_rolling_features]
        ↓
[isolation_forest_theft_v3] → [anomaly_scores]
[lstm_consumption_v2]       → [anomaly_scores]
                                      ↓
                           [investigation_cases]
                                      ↓
                      [Case Summariser — Claude via AI Gateway]
                      [Field Dispatch Agent — Claude via AI Gateway]
                      [Genie: genie_theft_space_v1]
```

### 9.3 AI Gateway Audit Panel

Show last 100 LLM calls: timestamp, caller, token count, latency,
guardrail triggered (PII detection, prompt injection filter).

**Demo talking point:** Under Ofgem licence conditions, UKI Gas must evidence
its theft investigation processes. The AI Gateway audit log, UC lineage, and model
cards provide that audit trail natively — in one place.

---

## 10. Why Databricks — Not Microsoft Fabric

Present as a dismissible panel or on request from Susie / exec audience.

| Capability | Databricks | Microsoft Fabric |
|-----------|-----------|-----------------|
| ML model serving | Native (MLflow + Model Serving) | Exit to Azure ML — separate service, auth, and cost centre |
| NL query over live data | Genie queries Delta tables directly, adapts to schema changes | Power BI Copilot requires a pre-built semantic model — breaks silently on schema change |
| LLM governance | AI Gateway + Unity Catalog — one audit log | Azure AI Foundry + Microsoft Purview — separate governance layers |
| Data governance | Unity Catalog — single plane for data, models, LLMs, Genie | OneLake + Purview + Azure ML + Power BI workspaces — four auth integrations |
| Streaming at scale | 360m events/day (half-hourly × 7.5m accounts) native on Delta Live Tables | Eventhouse handles event visualisation; scoring and serving in different engines |
| Investigator UI | Databricks App + Genie + LLM in one security perimeter | Power BI Embedded + Azure App Service + Azure ML — three integrations |

**The one-liner:** Databricks is not one of many services in the stack. It *is* the stack.

---

## 11. Technical Build Checklist for Cursor

### Prerequisites
- [ ] Databricks workspace with Unity Catalog enabled
- [ ] `dz_demos` catalog and `energy_theft` schema created
- [ ] Genie space created and pointed at `anomaly_scores` + metric views
- [ ] AI Gateway configured with Claude endpoint
- [ ] MLflow experiment created for theft scoring models

### Phase 1 — Data Layer
- [ ] Generate simulated dataset (100k accounts, 90-day history)
- [ ] Create all Delta tables per Section 4.1 schema
- [ ] Run Isolation Forest + LSTM scoring, write to `anomaly_scores`
- [ ] Create `metric_theft_precision_rate` UC Metric View (Section 6.2)
- [ ] Register models in MLflow Model Registry

### Phase 2 — Application Shell
- [ ] Scaffold Databricks App (Streamlit)
- [ ] Implement navigation: 5 pages as per Section 3
- [ ] Connect to Unity Catalog via databricks-sdk Python client

### Phase 3 — Executive Dashboard (Page 1)
- [ ] KPI tiles from `anomaly_scores` aggregate queries
- [ ] UK postcode choropleth heatmap (Plotly Mapbox)
- [ ] Trend chart and dual fuel split chart

### Phase 4 — Investigation Workbench (Page 2)
- [ ] Embed Genie Conversation API
- [ ] Implement flagged account table with sorting/filtering
- [ ] Account detail drawer with consumption chart + LLM summary
- [ ] Model serving endpoint call for case summary generation
- [ ] "Generate Field Dispatch" button triggering agent workflow

### Phase 5 — Historical Analysis (Page 3)
- [ ] Trend charts and seasonal pattern overlay
- [ ] Forward-looking risk prediction table
- [ ] Model performance dashboard with UC Metric View integration

### Phase 6 — AI Governance (Page 5)
- [ ] AI component registry table
- [ ] UC lineage DAG rendering (Plotly network graph)
- [ ] AI Gateway audit log panel from system.serving.endpoint_usage

### Phase 7 — Agentic Page (Page 4)
- [ ] Field dispatch agent implementation (LangChain on Databricks)
- [ ] Agent card UI with launch/status
- [ ] Document output render and write-back to investigation_cases

### Phase 8 — Demo Polish
- [ ] "Simulated Data — Demo Environment" banners on all data pages
- [ ] UKI Energy / UKI Gas branding (colours: #0A84C8 blue, white)
- [ ] Executive narrative tooltips on KPI tiles (hover = source citation)
- [ ] Compete rationale panel (Section 10)

---

## 12. Sources

| Claim | Source |
|-------|--------|
| £1.4bn/year stolen | RECCo / Capgemini Theft Estimation, Jan 2023; RECCo press release Feb 2026 |
| £50/year per household | RECCo, February 2026 |
| ~36 deaths/year | Ofgem ETU Decision, REC Change R0233, June 2025 |
| ETU approved | Ofgem R0233, June 2025 |
| UKI Gas 7.5m customers | UKI Energy 2025 Preliminary Results, Feb 2026 |
| UKI Gas Home Energy AOP: £163m | UKI Energy 2025 Preliminary Results, Feb 2026 |
| UK trade receivables: £1,443m | UKI Energy Financial Statements 2025 |
| 30% ML recovery rate | Industry benchmark, AI-augmented detection programmes |
| £392m exposure / £118m recoverable | Derived: RECCo % × BG market share |

---

*All financial figures for UKI Gas theft exposure are estimates derived from public sources.*
*Demo data must be clearly labelled as simulated throughout the application.*
*Catalog: `dz_demos.energy_theft` — update all SQL references accordingly.*
