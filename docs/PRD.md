# AI-Driven Energy Theft Detection for UKI Gas
## Product Requirements Document

**Version:** 1.0
**Date:** 17 March 2026
**Catalog:** `<your_catalog>.energy_theft_protection`
**Framework:** Databricks APX (FastAPI + React)
**Workspace Profile:** `<your-profile>`

---

## 1. Executive Summary

### The Business Problem

Energy theft is the deliberate diversion of gas or electricity without payment. It is
physical, organised, and growing. In the UK, metering equipment interference incidents
increased 370% between 2017 and 2021. Someone is killed from meter tampering
approximately once every ten days.

| Metric | Value | Source |
|--------|-------|--------|
| Annual value stolen across Great Britain | **£830m–£1.4bn/year** | RECCo / Capgemini Theft Estimation, Jan 2023; RECCo press release |
| Added to every honest household's bill | **£29–48/year** | Ofgem TDIS Authority Decision, May 2025 |
| Deaths from tampered supplies | **~1 every 10 days (~36/year)** | Ofgem, BBC investigations |
| UKI Gas estimated theft exposure | **~£323m/year** | Derived: £1.4bn × BG 23.1% market share (Ofgem, Jan 2025) |
| ML-recoverable value (30% benchmark) | **~£97m/year** | Industry benchmark; Enel achieved 70–300% improvement per inspection |
| UKI Gas Home Energy divisional profit (2025) | **£163m** | UKI Energy Preliminary Results, Feb 2026 |
| BG theft exposure as % of divisional AOP | **~198%** | £323m exposure vs £163m AOP |
| UK suppliers' theft detection rate vs target | **~40%** | 16,581 confirmed vs 41,000 target (Ofgem, 2022/23) |

**The anchor stat:** UKI Gas's estimated theft exposure (~£323m) exceeds its entire
Home Energy divisional operating profit (£163m) by nearly 2x. Even a conservative
ML-assisted recovery programme recovering 30% of that exposure would yield ~£97m —
equivalent to 59% of the division's profit. Early, accurate detection of meter anomalies
is one of the most material levers available to protect that margin.

> All theft exposure figures are estimates derived from public sources. The derivation
> uses BG's 23.1% domestic market share (Ofgem retail market indicators, Jan 2025)
> applied to RECCo's upper-range theft estimate. Label as estimates in the UI.

### Industry Context

UK energy suppliers are significantly underperforming their Ofgem theft detection
targets, identifying only ~40% of expected cases. The regulatory environment is
tightening: Ofgem approved the Energy Theft Unit (ETU) under REC R0233 in June 2025,
and reformed the Theft Detection Incentive Scheme (TDIS) in May 2025 to pay suppliers
for desktop investigations and site visits regardless of confirmation outcome.

Internationally, Enel deploys ML theft detection across 20 million smart meters using
500+ features from seven source systems, achieving 70% improvement in recovery per
inspection in Italy and over 300% in Spain. The technical approach is proven at scale.

### Demo Objectives

1. Show how Databricks unifies data, ML, LLMs, and NL queries under one governed
   platform — not stitched together from separate services
2. Demonstrate persona-driven AI: Susie (executive) uses Genie for governed NL queries;
   Robbie (analyst) uses Bedrock LLM for investigation summaries
3. Make AI governance visible: PII field tagging, column-level lineage, and a unified
   audit trail across all AI components — aligned to Ofgem/ELEXON requirements
4. Raise urgency: every week of delay costs ~£6.2m in unrecovered revenue

---

## 2. Personas

Every page, KPI tile, chart, and AI interaction maps back to one of these two personas.
The app navigation follows Susie's world first, then Robbie's world, then governance.

### Susie Chambers
**Head of Revenue Protection & Financial Crime, UKI Gas Home Energy**
*UKI Energy plc | Director-level, reporting to Chief Customer Officer*

Susie owns the Revenue Protection function as a P&L-accountable director. She presents
to the UKI Gas Home Energy CFO quarterly on theft exposure and recovery, and to the
Group Risk Committee annually. She manages Robbie's team, field engineering capacity,
and regulatory compliance obligations under the ETU. She does not write SQL. She opens
dashboards and asks questions in plain English.

**Primary AI technology:** Genie Space — natural language queries over UC Metric Views.
Susie needs answers she can cite to the CFO. Genie + UC Metric Views prevent
hallucination and ensure consistent KPI definitions.

**Susie's KPIs:**

| KPI | Current | Target |
|-----|---------|--------|
| Revenue recovered YTD | Live (app) | ~£97m/year (30% of exposure) |
| Recovery rate vs recoverable | Live | >30% |
| Theft exposure as % of divisional AOP | ~198% | Reduce YoY |
| Theft Detection Precision Rate (portfolio) | Live | >60% (demo-assumed target) |
| HIGH risk accounts as % of estate | Live | Monitor / reduce |
| ETU referrals submitted YTD | Live | Regulatory compliance |

**What Susie needs:** Can she answer a CFO question in 30 seconds? Is YTD recovery on
track? Where are the geographic hotspots? Is the model improving?

### Robbie Henderson
**Senior Revenue Protection Analyst — Theft Detection**
*UKI Gas Home Energy Supply | Revenue Protection Team*

Robbie is a mid-career data analyst embedded in UKI Gas's Revenue Protection team.
His job is to take anomaly signals from the ML platform and turn them into confirmed
theft cases: reviewing flagged accounts, dispatching field engineers, and closing cases.
He is comfortable with data tools but is not a data scientist — he relies on the
platform to surface and score, while he focuses on investigation and triage.

**Primary AI technology:** Bedrock LLM (via AI Gateway) — structured investigation
summaries, signal narratives, and field dispatch documents. The LLM collapses a
40-minute manual investigation per account into minutes.

**A day in Robbie's life:**
1. Opens the Investigation Workbench to review overnight HIGH risk flags
2. Reviews the 90-day consumption chart for the step-down signature of bypass
3. Reads the LLM-generated Case Summary to understand the key signals
4. Clicks "Generate Field Dispatch" — the LLM builds the investigation document
5. Field engineer reports outcome; Robbie closes the case and logs revenue recovered
6. For organised crime clusters, submits formal ETU referral via RECCo

**Robbie's KPIs:**

| KPI | Target |
|-----|--------|
| Theft Detection Precision Rate | >60% (confirmed theft / total HIGH cases closed) |
| Mean time from flag to field dispatch | <3 working days |
| Cases investigated per week | 25–30 per analyst |
| Revenue recovered per confirmed case | £2,400–£4,000 avg (industry estimate) |
| False positive rate (HIGH tier) | <40% |
| ETU referrals submitted (YTD) | Regulatory compliance (REC R0233) |

> The 60% precision target and £2,400–£4,000 recovery per case are industry estimates
> used for demo purposes. Public benchmarks are not available; operational data from
> UKRPA or RECCo would be needed for validation.

---

## 3. Application Overview

**Platform:** Databricks App (APX — FastAPI + React + TypeScript)
**Data:** Delta tables in Unity Catalog — `<your_catalog>.energy_theft_protection`
**ML:** MLflow-registered Isolation Forest + LSTM ensemble, batch-scored (simulated)
**NL Interface:** Genie Conversation API (Susie's executive space)
**Summarisation:** Bedrock LLM via AI Gateway (Robbie's investigation summaries)
**Governance:** Unity Catalog — single plane for data, models, LLMs, Genie, and PII

**The Hero Message:** *"£1.4 billion is stolen from UK energy suppliers every year.
40% goes undetected. How might UKI Gas turn £323M of loss exposure into
recovered revenue, faster, with Data & AI?"*

The headline builds from defensible public data (£1.4bn RECCo, 40% Ofgem) to the
BG-specific question (£323M derived estimate), so the audience arrives at the
derived figure through context rather than cold assertion.

All energy theft figures cover **both electricity and gas** across the full BG estate.
The £323M figure is an estimate derived from RECCo industry theft data applied to
BG market share — embedded in receivables and bad debt provisions. This is clearly
labelled in the UI with source tooltips on every financial metric.

| Page | Route | Designed For | Description |
|------|-------|-------------|-------------|
| Landing Page | `/` | **All** | Dark hero with exam question headline, "Meet Susie" / "Meet Robbie" persona cards with goals + quotes, sourced impact metrics |
| Executive Dashboard | `/dashboard` | **Susie** | KPI tiles with tooltips, risk heatmap, trend chart, Genie chat |
| Investigation Workbench | `/investigation` | **Robbie** | Flagged account table, detail drawer, LLM case summaries |
| AI Governance | `/governance` | **Demo audience** | PII access matrix (high-contrast badges), UC lineage DAG, AI Gateway audit |
| Why Databricks | `/why-databricks` | **Demo audience** | Advisory platform context (6 sections) |
| Presentation | `/presentation` | **Demo audience** | 9-slide deck — exam question, financial challenge, Meet Susie/Robbie, architecture, demo walkthrough, governance, Why Databricks, next steps |

---

## 4. Data Model

All tables in Unity Catalog: **`<your_catalog>.energy_theft_protection`**

### 4.1 Core Delta Tables

```sql
CREATE TABLE smart_meter_reads (
  account_id        STRING,
  read_timestamp    TIMESTAMP,        -- Half-hourly interval
  fuel_type         STRING,           -- 'electricity' | 'gas'
  consumption_kwh   DOUBLE,
  read_quality      STRING,           -- 'actual' | 'estimated' | 'missing'
  comms_gap_flag    BOOLEAN,
  postcode          STRING,           -- Masked to sector e.g. 'NW1 5'
  property_type     STRING,           -- 'terraced' | 'semi' | 'flat' | 'detached'
  council_tax_band  STRING            -- A–H
);

CREATE TABLE meters (
  meter_id          STRING,
  account_id        STRING,
  mpan              STRING,           -- Meter Point Administration Number (PII)
  meter_serial_number STRING,         -- Physical device identifier (PII)
  fuel_type         STRING,           -- 'electricity' | 'gas'
  meter_type        STRING,           -- 'smart' | 'traditional' | 'prepayment'
  install_date      DATE,
  last_read_timestamp TIMESTAMP
);

CREATE TABLE anomaly_scores (
  account_id              STRING,
  score_timestamp         TIMESTAMP,
  fuel_type               STRING,
  isolation_forest_score  DOUBLE,     -- 0–1, higher = more anomalous
  lstm_deviation_score    DOUBLE,     -- Z-score vs own 90-day baseline
  cohort_deviation_score  DOUBLE,     -- Z-score vs similar property cohort
  comms_gap_count_30d     INT,
  consumption_drop_pct    DOUBLE,     -- % drop vs prior 30-day rolling avg
  composite_risk_score    DOUBLE,     -- Weighted ensemble — PRIMARY signal
  risk_tier               STRING,     -- 'HIGH' | 'MEDIUM' | 'LOW'
  postcode_sector         STRING,
  model_version           STRING,
  investigation_status    STRING      -- 'OPEN' | 'IN_PROGRESS' | 'CLOSED' | 'CONFIRMED_THEFT'
);

CREATE TABLE investigation_cases (
  case_id               STRING,
  account_id            STRING,
  opened_timestamp      TIMESTAMP,
  investigator_id       STRING,
  llm_summary           STRING,       -- Bedrock-generated (PII-derived)
  field_dispatch_doc    STRING,
  outcome               STRING,       -- 'THEFT_CONFIRMED' | 'FALSE_POSITIVE' | 'PENDING'
  revenue_recovered_gbp DOUBLE,
  closed_timestamp      TIMESTAMP
);

CREATE TABLE property_reference (
  account_id       STRING,
  postcode         STRING,
  region           STRING,
  property_type    STRING,
  council_tax_band STRING,
  floor_area_m2    DOUBLE,
  epc_rating       STRING
);

CREATE TABLE model_performance_log (
  month             DATE,
  model_version     STRING,
  risk_tier         STRING,
  precision_pct     DOUBLE,
  recall_pct        DOUBLE,
  f1_score          DOUBLE,
  cases_scored      INT,
  cases_confirmed   INT
);
```

### 4.2 PII Field Classification

Under the UK Data Access and Privacy Framework (DAPF), Ofgem GDPR guidance, and
ELEXON BSC data protection rules, the following field-level PII classifications apply.
The AI Governance tab displays which ML models and LLM prompts access which PII
fields, with visible PII badges.

**Regulatory basis:**
- **Ofgem DAPF:** Half-hourly consumption data linked to MPAN is personal data
  requiring opt-in consent for domestic customers
- **ELEXON BSC:** MPANs, addresses, and consumption data linked to domestic premises
  are personal data (BSC data protection guidance, effective March 2025)
- **ICO guidance:** Postcode + consumption pattern can re-identify individuals even
  without name/address
- **RECCo / GDPR Art. 6(1)(f):** Theft investigation data handled under legitimate
  interest but still classified as personal data

| Table | Field | PII Tag | Regulatory Basis |
|-------|-------|---------|-----------------|
| `smart_meter_reads` | `account_id` | PII | ELEXON BSC — links to domestic customer |
| `smart_meter_reads` | `consumption_kwh` | PII (when linked) | Ofgem DAPF — half-hourly data is personal when linked to MPAN/premises |
| `smart_meter_reads` | `postcode` | PII | ICO — identifies premises; masked to sector level |
| `meters` | `mpan` | PII | ELEXON BSC — directly identifies premises |
| `meters` | `meter_serial_number` | PII | Ofgem — identifies physical device at premises |
| `property_reference` | `account_id` | PII | Links to domestic customer |
| `property_reference` | `postcode` | PII | Identifies premises |
| `property_reference` | `property_type` + `council_tax_band` | Quasi-PII | ICO — combined with postcode can re-identify household |
| `property_reference` | `epc_rating` | Quasi-PII | Linked to specific property via EPC register |
| `anomaly_scores` | `account_id` | PII | Links scored risk to domestic customer |
| `anomaly_scores` | `postcode_sector` | PII | Identifies area of premises |
| `investigation_cases` | `account_id` | PII | Links investigation to customer |
| `investigation_cases` | `investigator_id` | PII (staff) | Identifies UKI Gas employee |
| `investigation_cases` | `llm_summary` | PII (derived) | LLM output may contain account-linked PII from prompt context |

**Non-PII fields:** `composite_risk_score`, `risk_tier`, `fuel_type`, `model_version`,
all fields in `model_performance_log` (aggregated metrics only).

### 4.3 Simulated Dataset

Generate **100,000 account records** with **200,000 meters** (~2 per account):
- **95% normal** — seasonal sine wave + Gaussian noise, morning/evening peaks
- **3% tampered** — sudden step-down of 30–70% at a random point, flat curve,
  simulated comms gaps
- **2% edge cases** — legitimate drops (vacant, solar install) near the HIGH/MEDIUM
  boundary to test precision

Label all screens: **"Simulated Data — Demo Environment"**

---

## 5. ML Model Specifications

### 5.1 Technical Approach

The demo uses two complementary models, consistent with industry practice:

| Model | Technique | Purpose | Key Features |
|-------|-----------|---------|-------------|
| `isolation_forest_theft_v3` | Isolation Forest | Point-in-time anomaly detection | 30-day consumption stats, comms gap count, cohort deviation, property features |
| `lstm_consumption_v2` | LSTM Autoencoder | Temporal sequence anomaly | 90-day half-hourly consumption sequence, reconstruction error as deviation score |

**Industry validation:**
- Hybrid Isolation Forest + XGBoost achieves F1 0.77 on real utility data
  (Energies journal, 2025)
- LSTM-Autoencoder + CNN architectures achieve 95–97% accuracy on SGCC dataset
  (Nature Scientific Reports, 2025)
- Enel production deployment uses 500+ features across 20M meters

### 5.2 Composite Risk Score

```
composite_risk_score = (
    0.35 × isolation_forest_score +
    0.30 × lstm_deviation_score +
    0.20 × cohort_deviation_score +
    0.10 × normalised_comms_gap_count +
    0.05 × normalised_consumption_drop_pct
)
```

| Risk Tier | Composite Score Range | Expected % of Estate |
|-----------|----------------------|---------------------|
| HIGH | >= 0.75 | ~3% |
| MEDIUM | 0.50–0.74 | ~7% |
| LOW | < 0.50 | ~90% |

### 5.3 PII Fields Accessed by Models

| Model | PII Fields Accessed |
|-------|-------------------|
| `isolation_forest_theft_v3` | account_id, consumption_kwh, postcode, property_type, council_tax_band |
| `lstm_consumption_v2` | account_id, consumption_kwh, mpan |
| Bedrock LLM (case summary) | account_id, postcode, consumption_kwh, composite_risk_score, cohort_deviation_score, property_type, council_tax_band |
| Genie Space (Susie) | All fields in queried tables (governed by UC permissions) |

For the demo, models are simulated (pre-computed scores in `anomaly_scores`). MLflow
experiments show training runs and model cards.

---

## 6. Genie Space Design

### 6.1 Susie's Space: "Revenue Protection Executive Intelligence" (Tier 1)

**Purpose:** Executive-level questions for CFO prep, board reporting, and portfolio
health monitoring. Susie asks in plain English and expects answers she can cite.

**Tables:**
- `<your_catalog>.energy_theft_protection.anomaly_scores`
- `<your_catalog>.energy_theft_protection.investigation_cases`
- `<your_catalog>.energy_theft_protection.property_reference`
- `<your_catalog>.energy_theft_protection.metric_theft_precision_rate` (metric view)
- `<your_catalog>.energy_theft_protection.metric_revenue_recovery` (metric view)

**Sample Questions:**

1. "What is our revenue recovered year-to-date, and are we on track to hit the
   £97 million annual target?"
2. "What is the current Theft Detection Precision Rate, and how has it trended
   over the last 6 months?" — *must use UC Metric View*
3. "Which regions have the highest theft exposure this quarter, and how does that
   compare to last quarter?"
4. "What percentage of our estate is flagged as HIGH risk, and is that proportion
   growing or shrinking?"
5. "How many cases has the team closed this month, and what is the confirmed
   theft rate?"
6. "Show me a breakdown of theft exposure by fuel type — are we seeing more
   electricity or gas anomalies?"

**Genie instructions:**
- Always use metric views for KPI questions (theft precision rate, revenue recovery)
- Default time grain is monthly unless user specifies otherwise
- Express monetary values in GBP with comma separators
- When asked about "target" or "on track", compare against the £97m annual /
  £8.1m monthly benchmark

### 6.2 Robbie's Space: "Theft Investigation Triage" (Backlog)

Operational triage — geographic clustering, workload management, field dispatch
optimisation. Deferred to Tier 3.

---

## 7. UC Metric Views

### 7.1 Theft Detection Precision Rate

```sql
CREATE OR REPLACE VIEW <your_catalog>.energy_theft_protection.metric_theft_precision_rate
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Theft Detection Precision Rate: confirmed theft / total HIGH risk cases
            closed. Primary KPI for model performance. Refreshed daily."
  source: <your_catalog>.energy_theft_protection.investigation_cases
  filter: risk_tier = 'HIGH'
  dimensions:
    - name: Month
      expr: DATE_TRUNC('MONTH', closed_timestamp)
      comment: "Month case was closed"
  measures:
    - name: Confirmed Theft Cases
      expr: COUNT_IF(outcome = 'THEFT_CONFIRMED')
    - name: Total Closed Cases
      expr: COUNT_IF(outcome IN ('THEFT_CONFIRMED', 'FALSE_POSITIVE'))
    - name: Theft Detection Precision Pct
      expr: >
        ROUND(
          COUNT_IF(outcome = 'THEFT_CONFIRMED') * 100.0
          / NULLIF(COUNT_IF(outcome IN ('THEFT_CONFIRMED', 'FALSE_POSITIVE')), 0),
          2
        )
      comment: "Target: >60%. Below 60%, too many false positive field visits erode
                investigator trust and inflate opex."
$$
```

### 7.2 Revenue Recovery

```sql
CREATE OR REPLACE VIEW <your_catalog>.energy_theft_protection.metric_revenue_recovery
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Revenue recovered from confirmed theft cases. Primary financial KPI."
  source: <your_catalog>.energy_theft_protection.investigation_cases
  filter: outcome = 'THEFT_CONFIRMED'
  dimensions:
    - name: Month
      expr: DATE_TRUNC('MONTH', closed_timestamp)
    - name: Region
      expr: region
      comment: "Geographic region for board reporting"
  measures:
    - name: Revenue Recovered GBP
      expr: SUM(revenue_recovered_gbp)
    - name: Cases Confirmed
      expr: COUNT(1)
    - name: Avg Recovery Per Case
      expr: ROUND(SUM(revenue_recovered_gbp) / NULLIF(COUNT(1), 0), 2)
$$
```

---

## 8. Feature Specifications

### 8.1 Executive Dashboard (`/dashboard`) — Susie's View

**KPI Tile Row:**
- Total accounts monitored (demo: 100K; production: 7.5M)
- HIGH risk accounts flagged this week
- Estimated monthly theft exposure
- Revenue recovered YTD
- Cases confirmed as theft (YTD)

**Risk Heatmap:** UK postcode sector choropleth coloured by average
`composite_risk_score`. Plotly Mapbox. Drillable to sector level.

**Theft Signal Trend:** 12-month rolling line chart of flagged accounts by risk tier
(HIGH / MEDIUM). Shows whether detection is improving over time.

**Dual Fuel Split:** Pie chart: electricity vs gas anomaly flags this month.

**Embedded Genie Panel:** Genie Conversation API for Susie's executive questions.
Pre-loaded example prompts visible.

### 8.2 Investigation Workbench (`/investigation`) — Robbie's View

**Flagged Account Table:** Sortable by `account_id`, `postcode`, `risk_tier`,
`composite_risk_score`, `consumption_drop_pct`, `comms_gap_count_30d`, `fuel_type`,
`investigation_status`. Filterable by risk tier, fuel type, postcode sector.

**Account Detail Drawer** (click any row):
1. **Consumption time series** — 90-day half-hourly reads, anomaly onset date marked,
   cohort average overlaid. The step-down signature is visually obvious.
2. **Signal breakdown** — radar chart of five anomaly signals
3. **LLM Case Summary** — Bedrock-generated via AI Gateway:

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
{risk_level, key_signals[], recommended_action, priority,
 estimated_loss_per_month_gbp}"
```

### 8.3 AI Governance (`/governance`) — Demo Differentiator

**AI Component Registry:**

| Component | Type | Model | PII Fields Accessed |
|-----------|------|-------|-------------------|
| Theft Risk Scorer | ML Model | isolation_forest_theft_v3 | account_id, consumption_kwh, postcode, property_type, council_tax_band |
| Sequence Anomaly | ML Model | lstm_consumption_v2 | account_id, consumption_kwh, mpan |
| Case Summariser | LLM | Bedrock (AI Gateway) | account_id, postcode, consumption_kwh, risk_score, property details |
| Executive Intelligence | Genie | Revenue Protection Space | All fields in queried tables (UC-governed) |

**PII Access Matrix:** Visual matrix mapping each AI component to PII fields accessed,
with red (PII), amber (Quasi-PII), green (Non-PII) badges and Ofgem/ELEXON regulatory
justification per access pattern.

**UC Lineage DAG:** Interactive Plotly network graph showing column-level data flow
from raw smart meter reads through ML scoring to investigation cases to LLM outputs,
with PII badges on each node.

**AI Gateway Audit Panel:** Last 100 LLM calls: timestamp, caller, token count,
latency, guardrail triggered (PII detection, prompt injection filter). Read from
`system.serving.endpoint_usage`.

### 8.4 Why Databricks (`/why-databricks`) — Advisory Platform Context

Six sections, each framed as: problem → architecture requirement → how this demo
solves it → risk with alternative approaches. See plan for full detail.

### 8.5 Presentation (`/presentation`) — Show-Me-Don't-Tell-Me

Nine-slide in-app deck with scrollable + slide view toggle. Content structure:

1. **Title** — Hero: "£1.4bn stolen. 40% undetected. How might BG turn £323M into recovered revenue?"
2. **The Financial Challenge** — £323M, £163M, £6.2M/wk, £97M — all sourced with tooltips
3. **Meet Susie** — Emoji, role, 4 goals, quote, CTA to dashboard
4. **Meet Robbie** — Emoji, role, 4 goals, quote, CTA to workbench
5. **Architecture** — Ingest → Store → Score → Govern → Serve pipeline
6. **Live Demo Walkthrough** — 6 steps with links to each page
7. **AI Governance** — PII matrix, component registry, lineage, audit
8. **Why Databricks** — Speed, Genie, governance, cost
9. **Next Steps** — 4-phase roadmap

### 8.6 Design Patterns

**Source-annotated metrics:** Every financial figure has a tooltip citing its source
(RECCo, UKI Energy Results, Ofgem, or "Derived"). The £323M tooltip includes the
caveat that it is "an estimate embedded in receivables and bad debt provisions —
directionally correct for executive conversation."

**Persona cards:** Each persona is introduced with an emoji avatar, role title,
4 goal bullet points, an italic quote in a dark card, and a CTA button to their
primary page.

**PII badge contrast:** PII tags use `bg-red-100 text-red-800` (light mode) and
`dark:bg-red-950 dark:text-red-300` (dark mode) for clear readability. The
`--destructive-foreground` CSS variable is set to white for proper badge rendering.

---

## 9. Acceptance Test Cases

To be designed in Plan Mode during Phase 2. Test categories:

| Category | Priority | Est. Cases |
|----------|----------|-----------|
| Dashboard KPI tiles | MUST | 5 |
| Dashboard heatmap data | MUST | 3 |
| Dashboard trend chart | MUST | 3 |
| Genie Conversation API proxy | MUST | 4 |
| Flagged accounts list + pagination | MUST | 5 |
| Account detail drawer | MUST | 4 |
| LLM case summary generation | SHOULD | 3 |
| AI Governance component registry | MUST | 3 |
| PII access matrix | MUST | 4 |
| UC lineage DAG | SHOULD | 3 |
| AI Gateway audit panel | SHOULD | 3 |
| Error handling (404, 422, 500) | MUST | 4 |

---

## 10. Sources

| Claim | Source | Verified |
|-------|--------|----------|
| £830m–£1.4bn/year stolen | RECCo / Capgemini Theft Estimation, Jan 2023; RECCo press release | Yes |
| £29–48/year per household | Ofgem TDIS Authority Decision, May 2025 | Yes |
| ~1 death every 10 days | Ofgem; BBC; The Times investigation | Yes |
| ETU approved (R0233) | Ofgem R0233, June 2025 | Yes |
| UKI Gas 7.5M customers | UKI Energy 2025 Preliminary Results, Feb 2026 | Yes |
| BG Home Energy AOP: £163m | UKI Energy 2025 Preliminary Results, Feb 2026 | Yes |
| BG market share: 23.1% | Ofgem retail market indicators, Jan 2025 | Yes |
| 370% increase in metering interference | Ofgem TDIS Authority Decision, May 2025 | Yes |
| UK suppliers at 40% of theft target | 16,581 confirmed vs 41,000 target (Ofgem 2022/23) | Yes |
| Enel: 70–300% improvement with ML | BestPractice.AI / AWS case study | Yes |
| Hybrid IF+XGBoost F1 0.77 | Energies journal, MDPI, 2025 | Yes |
| 30% ML recovery rate | Industry benchmark (estimate) | Estimate |
| ~£323m BG exposure | Derived: RECCo upper range × BG market share | Derived |
| £2,400–£4,000/case recovery | Industry estimate (UKRPA) | Estimate |
| 60% precision target | Demo-assumed target | Assumed |

---

*All financial figures for UKI Gas theft exposure are estimates derived from public
sources. Demo data is clearly labelled as simulated throughout the application.*
