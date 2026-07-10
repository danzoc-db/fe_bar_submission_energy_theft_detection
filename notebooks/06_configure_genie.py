# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — Genie Space Configuration
# MAGIC
# MAGIC Creates or updates the **Revenue Protection Executive Intelligence** Genie Space
# MAGIC with the correct table identifiers, instructions, and sample questions.
# MAGIC
# MAGIC Run *after* `01d_metric_views.py` has created the metric views and the
# MAGIC underlying tables (`anomaly_scores`, `investigation_cases`, `property_reference`)
# MAGIC are populated.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
dbutils.widgets.text("genie_space_id", "")
dbutils.widgets.text("sql_warehouse_id", "")
dbutils.widgets.text("app_name", "energy-theft-detection")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id")
SQL_WAREHOUSE_ID = dbutils.widgets.get("sql_warehouse_id")
APP_NAME = dbutils.widgets.get("app_name")

print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA}")
print(f"Genie Space ID: {GENIE_SPACE_ID or '(will create new)'}")
print(f"SQL Warehouse ID: {SQL_WAREHOUSE_ID or '(auto-detect)'}")
print(f"App Name: {APP_NAME or '(not set)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Genie Space Configuration

# COMMAND ----------

DISPLAY_NAME = "Revenue Protection Executive Intelligence"

TABLE_IDENTIFIERS = [
    f"{CATALOG}.{SCHEMA}.anomaly_scores",
    f"{CATALOG}.{SCHEMA}.investigation_cases",
    f"{CATALOG}.{SCHEMA}.property_reference",
    f"{CATALOG}.{SCHEMA}.risk_exposure_metrics",
    f"{CATALOG}.{SCHEMA}.theft_detection_metrics",
]

DESCRIPTION = f"""Susie Chambers executive analytics space for CFO prep, board reporting, and portfolio health monitoring. Uses governed Unity Catalog Metric Views for consistent KPI definitions across {CATALOG}.{SCHEMA}."""

INSTRUCTIONS = f"""Prefer metric views (theft_detection_metrics, risk_exposure_metrics) for KPI questions. Fall back to investigation_cases, anomaly_scores, or property_reference only when a metric view lacks the needed dimension.

Default time grain is monthly unless the user specifies otherwise. Express monetary values in GBP with comma separators. Round percentages to one decimal place.

RUN RATE CONTEXT: ML model deployed October 2025; Oct–Dec 2025 was ramp-up. Annual recovery target £97M. For run rate or annualised pace use calendar year 2026 only (January onwards). Cumulative recovery from October 2025; run rate from January 2026.

Regional performance: use Region on theft_detection_metrics. Postcode hotspots: risk_exposure_metrics with Postcode Sector. OPEN HIGH triage: anomaly_scores WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN'."""

SAMPLE_QUESTIONS = [
    "What is our annualised run rate based on 2026 monthly recovery so far?",
    "Which postcode sectors have the most HIGH risk accounts and what is each sector's average composite risk score? Rank the top 10.",
    "For 2026 year-to-date, which region recovered the most revenue from confirmed theft and which the least? Show total GBP by region.",
    "For OPEN HIGH-risk triage: how many accounts, their average composite_risk_score, latest HIGH-tier precision_pct from model_performance_log, and YTD Avg Recovery Per Case from theft_detection_metrics — combine for indicative backlog upside at current model quality.",
    "Show me total revenue recovered and confirmed theft cases by month for the last 6 months.",
    "What is the current detection precision rate and how has it trended monthly?",
    "What percentage of our estate is flagged as HIGH risk, broken down by fuel type?",
    "What is the monthly revenue recovery trend since the ML model was deployed in October 2025?",
    "Are we on track to hit the £97M annual recovery target? Show cumulative recovery vs linear pace.",
]

EXAMPLE_QUESTION_SQLS = [
    {
        "question": "What is our annualised run rate based on 2026 monthly recovery so far?",
        "sql": f"""SELECT SUM(revenue_recovered_gbp) / NULLIF(GREATEST(MONTH(CURRENT_DATE()) - 1, 1), 0) * 12 AS annualised_run_rate
FROM {CATALOG}.{SCHEMA}.investigation_cases
WHERE outcome = 'THEFT_CONFIRMED' AND YEAR(closed_timestamp) = 2026 AND closed_timestamp IS NOT NULL""",
    },
    {
        "question": "Are we on track to hit the £97M annual recovery target?",
        "sql": f"""SELECT SUM(revenue_recovered_gbp) AS cumulative_recovery,
  SUM(CASE WHEN YEAR(closed_timestamp) = 2026 THEN revenue_recovered_gbp ELSE 0 END)
    / NULLIF(GREATEST(MONTH(CURRENT_DATE()) - 1, 1), 0) * 12 AS annualised_run_rate
FROM {CATALOG}.{SCHEMA}.investigation_cases
WHERE outcome = 'THEFT_CONFIRMED' AND closed_timestamp IS NOT NULL""",
    },
    {
        "question": "Which postcode sectors have the most HIGH risk accounts and what is each sector's average composite risk score? Rank the top 10.",
        "sql": f"""SELECT postcode_sector, COUNT(*) AS high_risk_accounts, AVG(composite_risk_score) AS avg_risk_score
FROM {CATALOG}.{SCHEMA}.anomaly_scores
WHERE risk_tier = 'HIGH'
GROUP BY postcode_sector
ORDER BY high_risk_accounts DESC
LIMIT 10""",
    },
    {
        "question": "For 2026 year-to-date, which region recovered the most revenue from confirmed theft and which the least? Show total GBP by region.",
        "sql": f"""SELECT region, SUM(revenue_recovered_gbp) AS total_recovered
FROM {CATALOG}.{SCHEMA}.investigation_cases
WHERE outcome = 'THEFT_CONFIRMED' AND YEAR(closed_timestamp) = 2026 AND closed_timestamp IS NOT NULL
GROUP BY region
ORDER BY total_recovered DESC""",
    },
    {
        "question": "Show me total revenue recovered and confirmed theft cases by month for the last 6 months.",
        "sql": f"""SELECT DATE_TRUNC('month', closed_timestamp) AS month,
  SUM(revenue_recovered_gbp) AS revenue_recovered,
  COUNT_IF(outcome = 'THEFT_CONFIRMED') AS confirmed_cases
FROM {CATALOG}.{SCHEMA}.investigation_cases
WHERE closed_timestamp >= ADD_MONTHS(DATE_TRUNC('month', CURRENT_DATE()), -6)
GROUP BY DATE_TRUNC('month', closed_timestamp)
ORDER BY month""",
    },
    {
        "question": "What is the current detection precision rate and how has it trended monthly?",
        "sql": f"""SELECT month, precision_pct
FROM {CATALOG}.{SCHEMA}.model_performance_log
WHERE risk_tier = 'HIGH'
ORDER BY month""",
    },
    {
        "question": "What percentage of our estate is flagged as HIGH risk, broken down by fuel type?",
        "sql": f"""SELECT fuel_type,
  COUNT(*) AS high_risk_accounts,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_of_high_risk
FROM {CATALOG}.{SCHEMA}.anomaly_scores
WHERE risk_tier = 'HIGH'
GROUP BY fuel_type
ORDER BY high_risk_accounts DESC""",
    },
    {
        "question": "For OPEN HIGH-risk triage: how many accounts, their average composite_risk_score, latest HIGH-tier precision_pct from model_performance_log, and YTD Avg Recovery Per Case from theft_detection_metrics",
        "sql": f"""SELECT
  (SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.anomaly_scores WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN') AS open_high_backlog,
  (SELECT AVG(composite_risk_score) FROM {CATALOG}.{SCHEMA}.anomaly_scores WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN') AS avg_composite_score,
  (SELECT precision_pct FROM {CATALOG}.{SCHEMA}.model_performance_log WHERE risk_tier = 'HIGH' ORDER BY month DESC LIMIT 1) AS latest_precision_pct""",
    },
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create or Update the Genie Space

# COMMAND ----------

import json as _json
import uuid

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
api = w.api_client

def _get_space_via_rest(space_id):
    """Fetch a Genie Space via REST API (works on all SDK versions)."""
    resp = api.do("GET", f"/api/2.0/genie/spaces/{space_id}")
    return _json.loads(resp.content) if hasattr(resp, "content") else resp

def _update_space_idempotent(space_id, display_name, description, table_ids, warehouse_id):
    """Update a Genie Space idempotently — skip title when unchanged to avoid ResourceAlreadyExists."""
    try:
        existing = _get_space_via_rest(space_id)
        needs_title = existing.get("title", "") != display_name
    except Exception:
        needs_title = True

    def _try_rest(include_title):
        body = {"description": description, "table_identifiers": table_ids}
        if include_title:
            body["title"] = display_name
        if warehouse_id:
            body["warehouse_id"] = warehouse_id
        api.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)

    try:
        _try_rest(needs_title)
        print(f"✓ Updated Genie Space via REST API: {space_id}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  Title '{display_name}' already exists — retrying without title")
            _try_rest(False)
            print(f"✓ Updated Genie Space via REST API (no title change): {space_id}")
        else:
            raise

def _data_sources():
    """Split tables vs metric views for serialized_space."""
    tables = [{"identifier": t} for t in TABLE_IDENTIFIERS if not t.endswith("_metrics")]
    metric_views = [{"identifier": t} for t in TABLE_IDENTIFIERS if t.endswith("_metrics")]
    ds = {"tables": tables}
    if metric_views:
        ds["metric_views"] = metric_views
    return ds


def _build_example_sql_entries():
    """Build example_question_sqls entries for serialized_space."""
    entries = []
    for ex in EXAMPLE_QUESTION_SQLS:
        entries.append({
            "id": str(uuid.uuid4()).replace("-", ""),
            "question": ex["question"],
            "sql": ex["sql"].strip(),
        })
    return entries


def _build_serialized_space():
    """Build the serialized_space JSON string with tables, instructions, and sample questions."""
    instruction_lines = [line + "\n" for line in INSTRUCTIONS.split("\n")]
    ss = {
        "version": 2,
        "data_sources": _data_sources(),
        "instructions": {
            "text_instructions": [
                {"id": str(uuid.uuid4()).replace("-", ""), "content": instruction_lines}
            ],
            "example_question_sqls": _build_example_sql_entries(),
        },
    }
    return _json.dumps(ss)

if GENIE_SPACE_ID:
    print(f"Updating existing Genie Space: {GENIE_SPACE_ID}")
    _update_space_idempotent(GENIE_SPACE_ID, DISPLAY_NAME, DESCRIPTION, TABLE_IDENTIFIERS, SQL_WAREHOUSE_ID)
else:
    print("Creating new Genie Space...")
    body = {
        "title": DISPLAY_NAME,
        "description": DESCRIPTION,
        "serialized_space": _build_serialized_space(),
    }
    if SQL_WAREHOUSE_ID:
        body["warehouse_id"] = SQL_WAREHOUSE_ID
    resp = api.do("POST", "/api/2.0/genie/spaces", body=body)
    result = _json.loads(resp.content) if hasattr(resp, "content") else resp
    GENIE_SPACE_ID = result.get("space_id", result.get("id", ""))
    print(f"✓ Created Genie Space: {GENIE_SPACE_ID}")
    print(f"  → Add this to databricks.yml: genie_space_id: \"{GENIE_SPACE_ID}\"")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Apply Instructions via `serialized_space`
# MAGIC
# MAGIC The SDK `description` field is metadata only — it does **not** populate the
# MAGIC "General Instructions" panel visible at `?sp=context.instructions` in the
# MAGIC Genie room UI. That panel is driven by `serialized_space.instructions`.
# MAGIC
# MAGIC We GET the current `serialized_space`, merge our instructions and sample
# MAGIC questions into it, then PATCH the space so both surfaces are consistent.

# COMMAND ----------

resp = api.do(
    "GET",
    f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}",
    query={"include_serialized_space": "true"},
)
current = _json.loads(resp.content) if hasattr(resp, "content") else resp

if current.get("serialized_space"):
    ss = _json.loads(current["serialized_space"])
else:
    ss = {"version": 1, "data_sources": {"tables": []}}

ss["data_sources"] = _data_sources()

instruction_id = None
if ss.get("instructions", {}).get("text_instructions"):
    instruction_id = ss["instructions"]["text_instructions"][0].get("id")
if not instruction_id:
    instruction_id = str(uuid.uuid4()).replace("-", "")

ss["instructions"] = {
    "text_instructions": [
        {
            "id": instruction_id,
            "content": [line + "\n" for line in INSTRUCTIONS.split("\n")],
        }
    ],
    "example_question_sqls": _build_example_sql_entries(),
}

patch_body = {
    "description": DESCRIPTION,
    "warehouse_id": SQL_WAREHOUSE_ID or current.get("warehouse_id", ""),
    "serialized_space": _json.dumps(ss),
}
current_title = current.get("title", "")
if current_title != DISPLAY_NAME:
    patch_body["title"] = DISPLAY_NAME

try:
    api.do("PATCH", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}", body=patch_body)
except Exception as e:
    if "already exists" in str(e).lower():
        patch_body.pop("title", None)
        api.do("PATCH", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}", body=patch_body)
    else:
        raise

print(f"✓ serialized_space instructions applied ({len(INSTRUCTIONS)} chars, {len(EXAMPLE_QUESTION_SQLS)} example SQL)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Configuration

# COMMAND ----------

existing = _get_space_via_rest(GENIE_SPACE_ID)
print(f"Space: {existing.get('title', 'N/A')}")
print(f"Tables: {len(TABLE_IDENTIFIERS)}")

for i, q in enumerate(SAMPLE_QUESTIONS, 1):
    print(f"  {i}. {q}")

print(f"\n✓ Genie Space configured with {len(TABLE_IDENTIFIERS)} tables and {len(SAMPLE_QUESTIONS)} sample questions")
print(f"  Space ID: {GENIE_SPACE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Table Access

# COMMAND ----------

for table in TABLE_IDENTIFIERS:
    try:
        count = spark.sql(f"SELECT COUNT(*) AS n FROM {table}").collect()[0]["n"]
        print(f"  ✓ {table}: {count:,} rows")
    except Exception as e:
        print(f"  ✗ {table}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify App Service Principal Permissions
# MAGIC
# MAGIC The Genie Space executes SQL on behalf of the calling principal. When the
# MAGIC Databricks App calls Genie, it authenticates as its service principal — so
# MAGIC that SP needs `SELECT` on every table the Genie Space references.
# MAGIC
# MAGIC This cell verifies the grants are in place and applies them if missing.

# COMMAND ----------

def _ensure_sp_genie_access(catalog, schema, table_ids, app_name_param):
    """Verify + fix the app SP's UC grants for all Genie-referenced tables."""
    if not app_name_param:
        print("⚠ app_name not set — skipping SP permission verification")
        return

    try:
        app_info = w.apps.get(app_name_param)
    except Exception as e:
        print(f"⚠ Could not look up app '{app_name_param}': {e}")
        return

    sp_id = getattr(app_info, "service_principal_id", None)
    if not sp_id:
        print(f"⚠ App '{app_name_param}' has no service_principal_id")
        return

    try:
        sp = w.service_principals.get(sp_id)
        sp_app_id = sp.application_id
        sp_display = sp.display_name or sp_app_id
    except Exception as e:
        print(f"⚠ Could not look up SP {sp_id}: {e}")
        return

    print(f"Verifying UC access for SP: {sp_display} (application_id={sp_app_id})")

    grants = [
        f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{sp_app_id}`",
        f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{sp_app_id}`",
        f"GRANT SELECT ON SCHEMA `{catalog}`.`{schema}` TO `{sp_app_id}`",
    ]
    all_ok = True
    for stmt in grants:
        try:
            spark.sql(stmt)
            print(f"  ✓ {stmt}")
        except Exception as e:
            error_str = str(e)
            if "already" in error_str.lower():
                print(f"  ✓ {stmt} (already granted)")
            else:
                print(f"  ✗ {stmt} — {e}")
                all_ok = False

    if all_ok:
        print(f"✓ App SP has full read access to {catalog}.{schema}")
    else:
        print("⚠ Some grants failed — Genie may return PERMISSION_DENIED at runtime")

_ensure_sp_genie_access(CATALOG, SCHEMA, TABLE_IDENTIFIERS, APP_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Grant Demo User Access
# MAGIC
# MAGIC Ensures named demo users have:
# MAGIC 1. `CAN_RUN` on the Genie Space (otherwise the API returns 404)
# MAGIC 2. `CAN_USE` on the SQL Warehouse (otherwise Genie queries return 403)

# COMMAND ----------

# Keep empty by default for workspace portability.
# Add users only where those principals actually exist.
DEMO_USERS = []

def _ensure_demo_user_access(space_id, warehouse_id, users):
    """Grant CAN_RUN on the Genie Space and CAN_USE on the warehouse."""
    if not users:
        return
    import json as _j

    # --- Genie Space CAN_RUN ---
    if space_id:
        resp = api.do("GET", f"/api/2.0/permissions/genie/{space_id}")
        acl = _j.loads(resp.content) if hasattr(resp, "content") else resp
        existing = {
            e.get("user_name", "").lower()
            for e in acl.get("access_control_list", [])
            if any(
                p.get("permission_level") in ("CAN_RUN", "CAN_MANAGE", "CAN_EDIT")
                and not p.get("inherited")
                for p in e.get("all_permissions", [])
            )
        }
        to_grant = [u for u in users if u.lower() not in existing]
        if to_grant:
            api.do(
                "PATCH",
                f"/api/2.0/permissions/genie/{space_id}",
                body={
                    "access_control_list": [
                        {"user_name": u, "permission_level": "CAN_RUN"}
                        for u in to_grant
                    ]
                },
            )
            for u in to_grant:
                print(f"  ✓ Genie CAN_RUN → {u}")
        else:
            print(f"✓ All {len(users)} demo users already have Genie Space access")

    # --- SQL Warehouse CAN_USE ---
    if warehouse_id:
        resp = api.do("GET", f"/api/2.0/permissions/sql/warehouses/{warehouse_id}")
        wh_acl = _j.loads(resp.content) if hasattr(resp, "content") else resp
        wh_existing = {
            e.get("user_name", "").lower()
            for e in wh_acl.get("access_control_list", [])
            if any(
                p.get("permission_level") in ("CAN_USE", "CAN_MANAGE", "IS_OWNER", "CAN_MONITOR")
                and not p.get("inherited")
                for p in e.get("all_permissions", [])
            )
        }
        wh_to_grant = [u for u in users if u.lower() not in wh_existing]
        if wh_to_grant:
            api.do(
                "PATCH",
                f"/api/2.0/permissions/sql/warehouses/{warehouse_id}",
                body={
                    "access_control_list": [
                        {"user_name": u, "permission_level": "CAN_USE"}
                        for u in wh_to_grant
                    ]
                },
            )
            for u in wh_to_grant:
                print(f"  ✓ Warehouse CAN_USE → {u}")
        else:
            print(f"✓ All {len(users)} demo users already have SQL Warehouse access")

_ensure_demo_user_access(GENIE_SPACE_ID, SQL_WAREHOUSE_ID, DEMO_USERS)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Add Benchmark Questions
# MAGIC
# MAGIC Registers benchmark questions with reference SQL (ground truth) so Genie's
# MAGIC native evaluation framework can assess accuracy programmatically via
# MAGIC `w.genie.genie_create_eval_run()`.

# COMMAND ----------

BENCHMARK_QUESTIONS = [
    {
        "question": "Are we on track to hit the £97M annual recovery target?",
        "sql_answer": f"""SELECT SUM(revenue_recovered_gbp) AS cumulative_recovery, SUM(CASE WHEN YEAR(closed_timestamp) = 2026 THEN revenue_recovered_gbp ELSE 0 END) / NULLIF(GREATEST(MONTH(CURRENT_DATE()) - 1, 1), 0) * 12 AS annualised_run_rate FROM {CATALOG}.{SCHEMA}.investigation_cases WHERE outcome = 'THEFT_CONFIRMED' AND closed_timestamp IS NOT NULL""",
    },
    {
        "question": "What is our annualised run rate based on 2026 monthly recovery so far?",
        "sql_answer": f"""SELECT SUM(revenue_recovered_gbp) / NULLIF(GREATEST(MONTH(CURRENT_DATE()) - 1, 1), 0) * 12 AS annualised_run_rate FROM {CATALOG}.{SCHEMA}.investigation_cases WHERE outcome = 'THEFT_CONFIRMED' AND YEAR(closed_timestamp) = 2026 AND closed_timestamp IS NOT NULL""",
    },
    {
        "question": "How many HIGH risk accounts are there and what is their average composite risk score?",
        "sql_answer": f"""SELECT COUNT(*) AS high_risk_accounts, AVG(composite_risk_score) AS avg_composite_score FROM {CATALOG}.{SCHEMA}.anomaly_scores WHERE risk_tier = 'HIGH'""",
    },
    {
        "question": "What is the total number of high risk flagged accounts?",
        "sql_answer": f"""SELECT COUNT(*) AS high_risk_accounts FROM {CATALOG}.{SCHEMA}.anomaly_scores WHERE risk_tier = 'HIGH'""",
    },
    {
        "question": "Show me monthly revenue recovered by region",
        "sql_answer": f"""SELECT region, DATE_TRUNC('month', closed_timestamp) AS month, SUM(revenue_recovered_gbp) AS revenue_recovered FROM {CATALOG}.{SCHEMA}.investigation_cases WHERE outcome = 'THEFT_CONFIRMED' AND closed_timestamp IS NOT NULL GROUP BY region, DATE_TRUNC('month', closed_timestamp) ORDER BY month, region""",
    },
    {
        "question": "Which region is recovering the most revenue?",
        "sql_answer": f"""SELECT region, SUM(revenue_recovered_gbp) AS total_recovered FROM {CATALOG}.{SCHEMA}.investigation_cases WHERE outcome = 'THEFT_CONFIRMED' AND closed_timestamp IS NOT NULL GROUP BY region ORDER BY total_recovered DESC""",
    },
    {
        "question": "What is the current detection precision rate?",
        "sql_answer": f"""SELECT precision_pct FROM {CATALOG}.{SCHEMA}.model_performance_log WHERE risk_tier = 'HIGH' ORDER BY month DESC LIMIT 1""",
    },
    {
        "question": "How has our precision rate trended monthly?",
        "sql_answer": f"""SELECT month, precision_pct FROM {CATALOG}.{SCHEMA}.model_performance_log WHERE risk_tier = 'HIGH' ORDER BY month""",
    },
    {
        "question": "How many OPEN HIGH risk accounts are in triage and what is their average composite risk score?",
        "sql_answer": f"""SELECT COUNT(*) AS open_high_backlog, AVG(composite_risk_score) AS avg_composite_score FROM {CATALOG}.{SCHEMA}.anomaly_scores WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN'""",
    },
]

resp = api.do(
    "GET",
    f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}",
    query={"include_serialized_space": "true"},
)
space_data = _json.loads(resp.content) if hasattr(resp, "content") else resp

if space_data.get("serialized_space"):
    ss_bench = _json.loads(space_data["serialized_space"])
else:
    ss_bench = {}

existing_benchmarks = ss_bench.get("benchmark_questions", [])
existing_texts = {b.get("question", b.get("text", "")).strip().lower() for b in existing_benchmarks}

added = 0
for bq in BENCHMARK_QUESTIONS:
    if bq["question"].strip().lower() not in existing_texts:
        existing_benchmarks.append({
            "id": str(uuid.uuid4()).replace("-", ""),
            "question": bq["question"],
            "sql_answer": bq["sql_answer"].strip(),
        })
        added += 1

ss_bench["benchmark_questions"] = existing_benchmarks

bench_patch = {"serialized_space": _json.dumps(ss_bench)}
try:
    api.do("PATCH", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}", body=bench_patch)
    print(f"✓ Benchmark questions: {added} added, {len(existing_benchmarks)} total")
except Exception as e:
    print(f"⚠ Could not add benchmark questions via serialized_space: {e}")
    print("  Benchmarks can be added manually via the Genie Space UI Benchmarks tab")
