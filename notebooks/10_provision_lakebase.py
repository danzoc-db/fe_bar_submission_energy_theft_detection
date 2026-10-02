# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — Lakebase Operational-Serving Layer
# MAGIC
# MAGIC Stands up the **Lakebase** (managed Postgres) operational-serving stage of
# MAGIC the end-to-end journey:
# MAGIC
# MAGIC ```
# MAGIC Lakeflow -> Unity Catalog -> ML/GenAI -> [ Lakebase ] -> Genie -> App
# MAGIC ```
# MAGIC
# MAGIC **Why Lakebase here.** The medallion pipeline + ML scoring land the gold
# MAGIC table `anomaly_scores` in Delta. Delta is right for analytics/ML, but wrong
# MAGIC for the investigator app's hot path:
# MAGIC
# MAGIC - The flagged-account queue is read on every page load — serving it from a
# MAGIC   SQL Warehouse pays a cold-start / planning tax.
# MAGIC - Case state (status, assignment, outcome, recovered amount) is
# MAGIC   *transactional*. Interactive row-level updates are an OLTP workload, not a
# MAGIC   Delta MERGE workload.
# MAGIC
# MAGIC This notebook provisions a Lakebase instance that:
# MAGIC
# MAGIC 1. hosts a **synced table** `anomaly_scores_serving` kept in sync from Delta
# MAGIC    (Delta -> Postgres) for sub-second, always-warm reads of the risk queue;
# MAGIC 2. hosts a native-Postgres **OLTP case-management schema**
# MAGIC    (`revenue_protection.investigation_cases` + an append-only
# MAGIC    `case_events` audit log, with a trigger recording every state change)
# MAGIC    that the app writes to with millisecond, read-your-writes commits.
# MAGIC
# MAGIC Idempotent and safe to re-run. The heavy lifting lives in
# MAGIC `scripts/provision_lakebase.py`; this notebook is a thin on-cluster wrapper
# MAGIC so the step is reproducible from the Workflows job alongside notebooks
# MAGIC `00`–`09`.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]>=3.2.0" "databricks-sdk>=0.85.0"
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "zoccali_fevm")
dbutils.widgets.text("schema", "energy_theft_protection")
dbutils.widgets.text("warehouse_id", "")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
WAREHOUSE_ID = dbutils.widgets.get("warehouse_id")
print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA}")
print(f"Warehouse: {WAREHOUSE_ID or '(must be set)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Make the provisioning module importable
# MAGIC
# MAGIC The repo root is added to `sys.path` so we can reuse the exact same logic
# MAGIC that runs locally (one source of truth for the Delta source table, the
# MAGIC instance, the synced table and the OLTP schema).

# COMMAND ----------

import os
import sys

# When run from the bundle, the repo is checked out next to notebooks/.
repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "provision_lakebase", os.path.join(repo_root, "scripts", "provision_lakebase.py")
)
prov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prov)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run provisioning
# MAGIC
# MAGIC On a Databricks cluster the default `WorkspaceClient()` authenticates with
# MAGIC the notebook principal, so no profile is needed. We call the staged
# MAGIC functions directly and print results so the cell output is committable as
# MAGIC execution evidence.

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
me = w.current_user.me().user_name
print(f"Authenticated as {me}")

# Stage 1: deduped Delta serving source (HIGH/MEDIUM queue)
prov.build_serving_source(w, WAREHOUSE_ID, CATALOG, SCHEMA)

# Stage 2: Lakebase instance
inst = prov.ensure_instance(w)

# Stage 3: synced table (Delta -> Postgres)
prov.ensure_synced_table(w, CATALOG, SCHEMA)

# Stage 4: OLTP case-management schema (native Postgres)
conn = prov.pg_connect(w, inst.read_write_dns, me)
prov.apply_oltp_schema(conn)

# Stage 5 + 6: demo transaction + verification
prov.demo_transaction(conn)
prov.verify(conn)
conn.close()

print("Lakebase operational-serving layer provisioned and verified.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC
# MAGIC - Enable the app's Lakebase path by deploying the `zoccali-fevm-aws` target
# MAGIC   (it sets `LAKEBASE_ENABLED=true` and binds the `database` app resource).
# MAGIC - The synced table refreshes on a `SNAPSHOT` schedule; trigger a refresh
# MAGIC   after each scoring batch (`04_batch_scoring.py`) so the serving queue
# MAGIC   reflects the latest model output.
