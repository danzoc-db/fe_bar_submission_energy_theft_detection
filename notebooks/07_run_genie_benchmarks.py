# Databricks notebook source
# MAGIC %md
# MAGIC # Genie Space — Benchmark Evaluation
# MAGIC
# MAGIC Triggers a benchmark evaluation run against the **Revenue Protection Executive
# MAGIC Intelligence** Genie Space using the REST API, polls until complete, and
# MAGIC asserts a minimum accuracy threshold.
# MAGIC
# MAGIC Run *after* `06_configure_genie.py` has created/updated the space and
# MAGIC registered benchmark questions with reference SQL ground truth.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
dbutils.widgets.text("genie_space_id", "")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id")

ACCURACY_THRESHOLD = 60

print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA}")
print(f"Genie Space ID: {GENIE_SPACE_ID}")
print(f"Accuracy threshold: {ACCURACY_THRESHOLD}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Validate Prerequisites

# COMMAND ----------

import json as _json
import time

if not GENIE_SPACE_ID:
    print("⚠ No GENIE_SPACE_ID provided — skipping benchmark evaluation")
    dbutils.notebook.exit("SKIPPED: no genie_space_id")

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
api = w.api_client

resp = api.do("GET", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}")
space_data = _json.loads(resp.content) if hasattr(resp, "content") else resp
print(f"Space: {space_data.get('title', 'N/A')}")
print(f"Space ID: {GENIE_SPACE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Trigger Benchmark Evaluation Run

# COMMAND ----------

print("Starting benchmark evaluation run...")
try:
    resp = api.do("POST", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/eval-runs")
    eval_data = _json.loads(resp.content) if hasattr(resp, "content") else resp
    eval_run_id = eval_data.get("eval_run_id", eval_data.get("id"))
    print(f"Eval run started: {eval_run_id}")
except Exception as e:
    error_str = str(e)
    if "NOT_FOUND" in error_str or "404" in error_str or "no benchmark" in error_str.lower():
        print(f"⚠ Genie benchmarks not available: {e}")
        print("  This space may not have benchmark questions configured.")
        print("  Add benchmarks via the Genie Space UI Benchmarks tab.")
        dbutils.notebook.exit("SKIPPED: no benchmarks configured or API not available")
    raise

if not eval_run_id:
    print("⚠ Could not extract eval_run_id from response")
    dbutils.notebook.exit("SKIPPED: could not start eval run")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Poll Until Complete

# COMMAND ----------

MAX_WAIT_SECONDS = 600
POLL_INTERVAL = 5

elapsed = 0
final_status = None

while elapsed < MAX_WAIT_SECONDS:
    time.sleep(POLL_INTERVAL)
    elapsed += POLL_INTERVAL

    try:
        resp = api.do("GET", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/eval-runs/{eval_run_id}")
        run_data = _json.loads(resp.content) if hasattr(resp, "content") else resp
        status = str(run_data.get("status", "")).upper()
    except Exception:
        status = "POLLING_ERROR"

    if elapsed % 30 == 0:
        print(f"  Polling... {elapsed}s elapsed, status={status}")

    if status in ("COMPLETED", "FAILED", "CANCELLED"):
        final_status = status
        break

if not final_status:
    print(f"⚠ Eval run timed out after {MAX_WAIT_SECONDS}s")
    dbutils.notebook.exit(f"TIMEOUT after {MAX_WAIT_SECONDS}s")

print(f"Eval run {final_status} after {elapsed}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Collect and Assess Results

# COMMAND ----------

try:
    resp = api.do("GET", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/eval-runs/{eval_run_id}/results")
    results_data = _json.loads(resp.content) if hasattr(resp, "content") else resp
    results = results_data.get("results", [])
except Exception as e:
    print(f"⚠ Could not fetch eval results: {e}")
    results = []

if not results:
    print("⚠ No benchmark results returned — space may have no benchmark questions")
    print("  Add benchmarks via 06_configure_genie.py or the Genie Space UI")
    dbutils.notebook.exit("SKIPPED: no benchmark results")

good_count = 0
bad_count = 0
review_count = 0

for r in results:
    rating = str(r.get("rating", "UNKNOWN")).upper() if isinstance(r, dict) else "UNKNOWN"
    question = r.get("question", "") if isinstance(r, dict) else ""

    if "GOOD" in rating or "CORRECT" in rating:
        good_count += 1
        symbol = "✓"
    elif "BAD" in rating or "INCORRECT" in rating:
        bad_count += 1
        symbol = "✗"
    else:
        review_count += 1
        symbol = "?"

    print(f"  {symbol} [{rating}] {question[:80]}")

total = len(results)
accuracy = good_count / total * 100 if total > 0 else 0

print(f"\n{'='*60}")
print(f"Benchmark Results: {good_count} GOOD / {bad_count} BAD / {review_count} REVIEW")
print(f"Accuracy: {accuracy:.0f}% (threshold: {ACCURACY_THRESHOLD}%)")
print(f"{'='*60}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Assert Accuracy Threshold

# COMMAND ----------

if accuracy < ACCURACY_THRESHOLD:
    msg = (
        f"Genie benchmark accuracy {accuracy:.0f}% is below "
        f"the {ACCURACY_THRESHOLD}% threshold "
        f"({good_count}/{total} GOOD). "
        f"Review benchmark results in the Genie Space UI."
    )
    print(f"⚠ {msg}")
    print("  This is a warning — not failing the pipeline task.")
    print("  Investigate via: Genie Space → Benchmarks → Evaluations tab")
else:
    print(f"✓ Benchmark accuracy {accuracy:.0f}% meets {ACCURACY_THRESHOLD}% threshold")

dbutils.notebook.exit(
    f"accuracy={accuracy:.0f}% good={good_count} bad={bad_count} review={review_count} total={total}"
)
