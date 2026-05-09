# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — Agent Atlas (Multi-Agent Supervisor)
# MAGIC
# MAGIC Creates or updates the **Energy Theft Atlas Supervisor** — a Multi-Agent
# MAGIC Supervisor (MAS) that orchestrates sub-agents for board report generation.
# MAGIC
# MAGIC The MAS routes KPI data queries to the Genie Space and composes structured
# MAGIC board reports. It is deployed as a model serving endpoint and consumed by
# MAGIC the application's `/api/agent/atlas/board-report` endpoint.
# MAGIC
# MAGIC Run *after* `06_configure_genie.py` has created/updated the Genie Space.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
dbutils.widgets.text("genie_space_id", "")
dbutils.widgets.text("app_name", "energy-theft-detection")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id")
APP_NAME = dbutils.widgets.get("app_name")

assert GENIE_SPACE_ID, "genie_space_id is required — the MAS routes data queries to the Genie Space"

print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA}")
print(f"Genie Space ID: {GENIE_SPACE_ID}")
print(f"App Name: {APP_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## MAS Configuration

# COMMAND ----------

MAS_NAME = "Energy Theft Atlas Supervisor"

MAS_DESCRIPTION = (
    "Multi-agent supervisor for generating Revenue Protection board reports. "
    "Routes KPI and investigation data queries to the Genie Space for SQL "
    "analysis on Unity Catalog tables."
)

MAS_INSTRUCTIONS = """You generate board-ready Revenue Protection reports for UKI Gas energy theft detection.

Routing rules:
1. Any question about numbers, KPIs, accounts, cases, revenue recovered, risk scores, postcode sectors, model performance, investigation outcomes → kpi_data_agent
2. For board reports: gather all KPI data from kpi_data_agent, then compose the final structured report.

Always respond with structured JSON when asked for a board report. Include: executive_summary, revenue_protection_overview, regional_analysis, model_performance_summary, recommendations (array of action items), and kpi_highlights (array of label/value/trend/context objects).

Context: Annual theft exposure £323M, recovery target £97M/year, models are Isolation Forest + LSTM Autoencoder with composite scoring on Databricks."""

MAS_AGENTS = [
    {
        "name": "kpi_data_agent",
        "genie_space_id": GENIE_SPACE_ID,
        "description": (
            "Answers data questions about energy theft detection KPIs, "
            "investigation cases, anomaly scores, revenue recovered, risk tiers, "
            "postcode sectors, model performance, and cases closed using SQL on "
            "Unity Catalog tables."
        ),
    },
]

MAS_EXAMPLES = [
    {
        "question": "Generate a Revenue Protection board report for UKI Gas",
        "guideline": (
            "Query kpi_data_agent for: total HIGH-risk accounts, top postcode sectors, "
            "precision rate, cases closed this month, revenue recovered YTD. Compose into "
            "a JSON board report with executive_summary, revenue_protection_overview, "
            "regional_analysis, model_performance_summary, recommendations, kpi_highlights."
        ),
    },
    {
        "question": "How many HIGH risk accounts do we have and what is the recovery rate?",
        "guideline": "Route to kpi_data_agent for the SQL data answer.",
    },
    {
        "question": "Show all investigation cases closed today",
        "guideline": "Route to kpi_data_agent to query investigation_cases table.",
    },
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create or Update the MAS

# COMMAND ----------

import json as _json
import time

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
api = w.api_client


def _find_mas_by_name(name: str) -> dict | None:
    """Search for an existing MAS by listing all and matching by name."""
    try:
        resp = api.do("GET", "/api/2.0/multi-agent-supervisors")
        result = _json.loads(resp.content) if hasattr(resp, "content") else resp
        for mas in result.get("supervisors", result.get("items", [])):
            mas_name = mas.get("name", "").replace("_", " ")
            if mas_name.lower() == name.lower() or mas.get("name", "").lower() == name.replace(" ", "_").lower():
                return mas
    except Exception as e:
        print(f"  ⚠ Could not list MAS: {e}")
    return None


def _create_mas() -> dict:
    """Create a new MAS via the REST API."""
    body = {
        "name": MAS_NAME,
        "description": MAS_DESCRIPTION,
        "instructions": MAS_INSTRUCTIONS,
        "agents": MAS_AGENTS,
    }
    resp = api.do("POST", "/api/2.0/multi-agent-supervisors", body=body)
    result = _json.loads(resp.content) if hasattr(resp, "content") else resp
    return result


def _update_mas(tile_id: str) -> dict:
    """Update an existing MAS via the REST API."""
    body = {
        "description": MAS_DESCRIPTION,
        "instructions": MAS_INSTRUCTIONS,
        "agents": MAS_AGENTS,
    }
    resp = api.do("PATCH", f"/api/2.0/multi-agent-supervisors/{tile_id}", body=body)
    result = _json.loads(resp.content) if hasattr(resp, "content") else resp
    return result


existing = _find_mas_by_name(MAS_NAME)

if existing:
    tile_id = existing.get("tile_id", existing.get("id", ""))
    print(f"Found existing MAS: {tile_id}")
    result = _update_mas(tile_id)
    print(f"✓ Updated MAS: {MAS_NAME}")
    MAS_TILE_ID = tile_id
else:
    print("Creating new MAS...")
    result = _create_mas()
    MAS_TILE_ID = result.get("tile_id", result.get("id", ""))
    print(f"✓ Created MAS: {MAS_NAME} (tile_id={MAS_TILE_ID})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Add Examples

# COMMAND ----------

for ex in MAS_EXAMPLES:
    try:
        api.do(
            "POST",
            f"/api/2.0/multi-agent-supervisors/{MAS_TILE_ID}/examples",
            body=ex,
        )
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            pass
        else:
            print(f"  ⚠ Could not add example: {e}")

print(f"✓ {len(MAS_EXAMPLES)} examples configured")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Wait for Endpoint Provisioning

# COMMAND ----------

MAS_ENDPOINT_NAME = f"mas-{MAS_TILE_ID.split('-')[0] if MAS_TILE_ID else 'unknown'}-endpoint"

max_wait_seconds = 300
poll_interval = 15
elapsed = 0

print(f"Waiting for MAS endpoint to provision (max {max_wait_seconds}s)...")
print(f"  Expected endpoint name pattern: mas-<tile_id_prefix>-endpoint")

endpoint_ready = False
while elapsed < max_wait_seconds:
    try:
        resp = api.do("GET", f"/api/2.0/serving-endpoints")
        endpoints = _json.loads(resp.content) if hasattr(resp, "content") else resp
        for ep in endpoints.get("endpoints", []):
            if MAS_TILE_ID and MAS_TILE_ID[:8] in ep.get("name", ""):
                MAS_ENDPOINT_NAME = ep["name"]
                state = ep.get("state", {}).get("ready", "UNKNOWN")
                if state == "READY":
                    endpoint_ready = True
                    break
                else:
                    print(f"  [{elapsed}s] Endpoint {MAS_ENDPOINT_NAME}: {state}")
    except Exception as e:
        print(f"  [{elapsed}s] Poll error: {e}")

    if endpoint_ready:
        break
    time.sleep(poll_interval)
    elapsed += poll_interval

if endpoint_ready:
    print(f"\n✓ MAS endpoint READY: {MAS_ENDPOINT_NAME}")
else:
    print(f"\n⚠ MAS endpoint not ready after {max_wait_seconds}s — may still be provisioning")
    print(f"  Check manually: databricks serving-endpoints get {MAS_ENDPOINT_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Grant App Service Principal Access

# COMMAND ----------

def _grant_sp_endpoint_access(endpoint_name: str, app_name: str):
    """Grant CAN_QUERY on the MAS serving endpoint to the app's service principal."""
    if not app_name:
        print("⚠ app_name not set — skipping SP permission grant")
        return

    try:
        app_info = w.apps.get(app_name)
    except Exception as e:
        print(f"⚠ Could not look up app '{app_name}': {e}")
        return

    sp_id = getattr(app_info, "service_principal_id", None)
    if not sp_id:
        print(f"⚠ App '{app_name}' has no service_principal_id")
        return

    try:
        sp = w.service_principals.get(sp_id)
        sp_app_id = sp.application_id
        sp_display = sp.display_name or sp_app_id
    except Exception as e:
        print(f"⚠ Could not look up SP {sp_id}: {e}")
        return

    print(f"Granting CAN_QUERY on {endpoint_name} to SP: {sp_display}")

    try:
        resp = api.do("GET", f"/api/2.0/permissions/serving-endpoints/{endpoint_name}")
        acl = _json.loads(resp.content) if hasattr(resp, "content") else resp
        existing_sps = {
            e.get("service_principal_name", "").lower()
            for e in acl.get("access_control_list", [])
            if any(
                p.get("permission_level") in ("CAN_QUERY", "CAN_MANAGE")
                and not p.get("inherited")
                for p in e.get("all_permissions", [])
            )
        }
        if sp_display.lower() in existing_sps or sp_app_id.lower() in existing_sps:
            print(f"  ✓ SP already has access to {endpoint_name}")
            return
    except Exception:
        pass

    try:
        api.do(
            "PATCH",
            f"/api/2.0/permissions/serving-endpoints/{endpoint_name}",
            body={
                "access_control_list": [
                    {"service_principal_name": sp_display, "permission_level": "CAN_QUERY"}
                ]
            },
        )
        print(f"  ✓ Granted CAN_QUERY on {endpoint_name} → {sp_display}")
    except Exception as e:
        print(f"  ✗ Failed to grant: {e}")
        print(f"    Manual fix: databricks permissions update serving-endpoints {endpoint_name} ...")


_grant_sp_endpoint_access(MAS_ENDPOINT_NAME, APP_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify MAS Endpoint

# COMMAND ----------

import httpx

host = w.config.host
headers = w.config.authenticate()

print(f"Testing MAS endpoint: {MAS_ENDPOINT_NAME}")
print(f"  Host: {host}")

try:
    test_resp = httpx.post(
        f"{host}/serving-endpoints/{MAS_ENDPOINT_NAME}/invocations",
        json={"input": [{"role": "user", "content": "How many HIGH risk accounts do we have?"}]},
        headers=headers,
        timeout=60,
    )
    print(f"  Status: {test_resp.status_code}")
    if test_resp.status_code == 200:
        data = test_resp.json()
        output_items = data.get("output", [])
        text_parts = []
        for item in output_items:
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        text_parts.append(part.get("text", "")[:200])
        if text_parts:
            print(f"  ✓ MAS responded: {text_parts[0][:100]}...")
        else:
            print(f"  ✓ MAS responded (no text extracted): {str(data)[:200]}")
    else:
        print(f"  ⚠ MAS returned {test_resp.status_code}: {test_resp.text[:200]}")
except Exception as e:
    print(f"  ⚠ MAS test failed: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("Agent Atlas MAS Configuration Summary")
print("=" * 60)
print(f"  MAS Name:       {MAS_NAME}")
print(f"  Tile ID:        {MAS_TILE_ID}")
print(f"  Endpoint:       {MAS_ENDPOINT_NAME}")
print(f"  Genie Space:    {GENIE_SPACE_ID}")
print(f"  Agents:         {len(MAS_AGENTS)}")
print(f"  Examples:       {len(MAS_EXAMPLES)}")
print()
print(f"  → Set MAS_ENDPOINT={MAS_ENDPOINT_NAME} in app.yml or env vars")
print(f"  → Add to databricks.yml variables: mas_endpoint: \"{MAS_ENDPOINT_NAME}\"")
print("=" * 60)
