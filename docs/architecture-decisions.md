# Architecture Decision Records

Short records of the key platform choices behind this build: context, decision,
and why not the main alternative. They back the trade-off summary in
[`docs/tech_stack.md`](tech_stack.md) and the in-app narrative on
[`/why-databricks`](../src/energy_theft_detection/ui/routes/_sidebar/why-databricks.tsx).

**Positioning.** Competitive statements below are for a technical buyer evaluating
Databricks against Microsoft Fabric / Azure. They are not a feature checklist.
Verify current product behaviour on [docs.databricks.com](https://docs.databricks.com)
and the vendor's public documentation before quoting externally. Sources cited here
are public docs only.

---

## ADR-1: Lakebase for operational serving (not external Postgres)

**Context.** ML scoring lands risk scores in Delta - right for analytics, wrong
for the investigator hot path. The flagged-account queue is read on every page
load, and case state (status, assignment, outcome, recovered amount) is
transactional.

**Decision.** Serve the queue and hold case state in Lakebase (managed Postgres):
a synced table from Delta for low-latency reads, and a native OLTP schema for
read-your-writes case commits.

**Why not external RDS/Aurora.** An external database is another system to run,
secure, network to the app, and rotate credentials for, with no Unity Catalog
lineage. Lakebase gives managed Postgres inside the platform, short-lived OAuth
credentials (no stored passwords), and a first-class synced table from Delta.

Covered in more detail in [`docs/tech_stack.md`](tech_stack.md).

**Public sources:**
[Lakebase (managed Postgres)](https://docs.databricks.com/aws/en/oltp/),
[synced tables](https://docs.databricks.com/aws/en/oltp/instances/sync-data/).

---

## ADR-2: Genie for natural language (not Power BI Copilot / Fabric)

**Context.** Susie needs executive natural-language access to governed KPIs
("Are we on track for the GBP 97m recovery target?") in seconds, not days.

**Decision.** Genie queries Delta tables directly under Unity Catalog, using the
same identity, governance and lineage as the rest of the platform.

**Why not Power BI Copilot / Fabric (positioning).** Copilot is licensed per user
or per capacity and typically sits on a pre-built DAX semantic model that can
break silently when the schema changes. Embedding conversational NL into a custom
app via REST has been preview in Fabric. Genie needs no extra per-user licence to
talk to the data, and no mirroring into OneLake/Fabric, so there are no UC
policies to recreate and no propagation lag.

In-app walkthrough: `/why-databricks` section "Executive Decision Speed".

**Public sources:**
[Genie](https://docs.databricks.com/aws/en/genie/),
[Genie Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api.html).

---

## ADR-3: Unity Catalog Metric Views (not a DAX semantic layer)

**Context.** KPIs (recovery rate, detection precision, exposure vs AOP) must be
defined once and consumed by the app, Genie, agents and BI consistently.

**Decision.** Define each KPI once in SQL as a UC Metric View.

**Why not Power BI DAX semantic models (positioning).** A DAX layer typically
means many measures maintained at different granularities, in a proprietary
language, living outside the governance perimeter where they can drift silently.
One governed, version-controlled, permissioned Metric View replaces that semantic
layer and is queryable everywhere, including by LLMs without a second KPI
definition.

**Public sources:**
[Metric views](https://docs.databricks.com/aws/en/metric-views/).

---

## ADR-4: Unity Catalog unified governance (not split Azure governance)

**Context.** Energy-theft work touches PII. Ofgem / ELEXON compliance needs a
coherent, column-level audit trail from raw data through model input to
investigation output.

**Decision.** Govern data, models, LLMs, Genie and lineage in one catalog, with
PII badges and automated classification.

**Why not Purview + Azure ML + AI Foundry (positioning).** Splitting governance
across services (data in one, models in another, LLM audit in a third) forces
manual stitching to assemble an audit trail, and each seam is a gap an auditor
can challenge. Item-level lineage (which table was used) is not enough;
column-level lineage (which PII fields the model consumed) is required.

In-app walkthrough: `/why-databricks` section "Regulatory Audit Trail".

**Public sources:**
[Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/),
[lineage](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage).

---

## ADR-5: Databricks serverless compute (not Fabric Capacity Units)

**Context.** Demand is spiky: daily batch scoring, intermittent executive
dashboards, concentrated investigation hours. Idle reserved capacity erodes the
ROI of the detection programme.

**Decision.** Run every component on serverless compute that auto-scales per
workload with transparent per-query pricing and scale-to-zero.

**Why not Fabric Capacity Units (positioning).** Fabric shares one CU pool across
ETL, BI, AI and Copilot; one workload spike can throttle, then freeze, the
others. There is no scale-to-zero, so reserved capacity bills whether idle or
not.

In-app walkthrough: `/why-databricks` section "Cost Governance".

**Public sources:**
[Serverless compute](https://docs.databricks.com/aws/en/compute/serverless/).

---

## ADR-6: Databricks Apps (not Azure App Service + Power BI Embedded + AI Foundry)

**Context.** The solution is a full application: FastAPI backend, React frontend,
Genie, Model Serving, LLM gateway.

**Decision.** Ship it on Databricks Apps, next to the data, inside the governance
perimeter.

**Why not the Azure stack (positioning).** Assembling the equivalent typically
means standing up and securing several services (App Service + Power BI Embedded
+ AI Foundry, plus Fabric SQL and a separate governance plane), each with its
own identity and billing model.

In-app walkthrough: `/why-databricks` section "Speed to Investigation".

**Public sources:**
[Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/).

---

## ADR-7: Synced-table SNAPSHOT refresh (not CONTINUOUS, yet)

**Context.** The serving queue only changes after a scoring batch.

**Decision.** Refresh the Lakebase synced table on a SNAPSHOT (triggered)
schedule after each batch. Change Data Feed is enabled on the source so a later
switch to CONTINUOUS needs no reload.

**Why not CONTINUOUS now.** Continuous CDC runs a pipeline per table; that
compute is unjustified while scores update only once per batch. Phase 3 of
[`docs/ROADMAP.md`](ROADMAP.md) flips this on when near-real-time scoring
arrives.

**Public sources:**
[Synced tables](https://docs.databricks.com/aws/en/oltp/instances/sync-data/),
[Change Data Feed](https://docs.databricks.com/aws/en/delta/delta-change-data-feed).

---

## ADR-8: Dual-write close path - Lakebase (OLTP) plus Delta (analytics)

**Context.** Closing a case must be instant for the analyst and queryable for
the executive and Genie.

**Decision.** The app commits case state to Lakebase for read-your-writes
latency, while the Delta MERGE remains the analytics / Genie reverse-sync path.

**Why not Delta-only.** Interactive case writes as async Delta MERGEs mean
seconds of latency and eventual consistency, and the queue read pays a warehouse
cold-start. Transactional state belongs in Postgres; analytics and NL stay on
Delta.

See [`docs/tech_stack.md`](tech_stack.md) and
[`docs/ROADMAP.md`](ROADMAP.md) Phase 1.
