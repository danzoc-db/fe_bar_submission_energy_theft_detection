# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — Schema Setup
# MAGIC
# MAGIC Creates the Unity Catalog schema and grants the app service principal
# MAGIC access to UC objects.  ML output tables (`anomaly_scores`,
# MAGIC `investigation_cases`, `model_performance_log`) are **not** truncated
# MAGIC here — downstream notebooks use `overwrite` mode, making the pipeline
# MAGIC idempotent and safe to cancel/re-run without data loss.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
dbutils.widgets.text("app_name", "energy-theft-detection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
APP_NAME = dbutils.widgets.get("app_name")

print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA} COMMENT 'British Gas Energy Theft Detection — ML-powered anomaly detection.'")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"\nSchema {CATALOG}.{SCHEMA} ready.")
print("ML output tables are written with overwrite mode — no truncation needed.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Grant App Service Principal Access to UC Objects
# MAGIC
# MAGIC The Databricks App's service principal needs `USE CATALOG`, `USE SCHEMA`, and
# MAGIC `SELECT` on the schema so the Genie Space can execute queries on behalf of
# MAGIC the app.  Without this, Genie returns `PERMISSION_DENIED` /
# MAGIC `TABLES_MISSING_EXCEPTION`.

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def _grant_app_sp_access(catalog: str, schema: str, app_name: str) -> None:
    """Look up the app service principal and grant it UC read access."""
    if not app_name:
        print("⚠ app_name not set — skipping SP permission grants")
        return

    try:
        app_info = w.apps.get(app_name)
    except Exception as e:
        print(f"⚠ Could not look up app '{app_name}': {e}")
        print("  (App may not be deployed yet — permissions will be granted on next run)")
        return

    sp_id = getattr(app_info, "service_principal_id", None)
    if not sp_id:
        print(f"⚠ App '{app_name}' has no service_principal_id — skipping grants")
        return

    try:
        sp = w.service_principals.get(sp_id)
        sp_app_id = sp.application_id
        sp_display = sp.display_name or sp_app_id
    except Exception as e:
        print(f"⚠ Could not look up service principal {sp_id}: {e}")
        return

    print(f"Granting UC access to app SP: {sp_display} (application_id={sp_app_id})")

    grants = [
        f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{sp_app_id}`",
        f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{sp_app_id}`",
        f"GRANT SELECT ON SCHEMA `{catalog}`.`{schema}` TO `{sp_app_id}`",
    ]
    for stmt in grants:
        try:
            spark.sql(stmt)
            print(f"  ✓ {stmt}")
        except Exception as e:
            error_str = str(e)
            if "already" in error_str.lower() or "ALREADY_EXISTS" in error_str:
                print(f"  ✓ {stmt} (already granted)")
            else:
                print(f"  ⚠ {stmt} — {e}")

_grant_app_sp_access(CATALOG, SCHEMA, APP_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Grant Named-User Access to UC Objects
# MAGIC
# MAGIC These grants persist independently of the app deployment, ensuring
# MAGIC stakeholders retain data access even if the app is torn down.

# COMMAND ----------

_NAMED_USERS = [
    "john.southcombe@databricks.com",
]

def _grant_named_user_access(catalog: str, schema: str, users: list[str]) -> None:
    """Grant USE CATALOG, USE SCHEMA, and SELECT to individual users."""
    for user in users:
        grants = [
            f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{user}`",
            f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{user}`",
            f"GRANT SELECT ON SCHEMA `{catalog}`.`{schema}` TO `{user}`",
        ]
        for stmt in grants:
            try:
                spark.sql(stmt)
                print(f"  ✓ {stmt}")
            except Exception as e:
                error_str = str(e)
                if "already" in error_str.lower() or "ALREADY_EXISTS" in error_str:
                    print(f"  ✓ {stmt} (already granted)")
                else:
                    print(f"  ⚠ {stmt} — {e}")

_grant_named_user_access(CATALOG, SCHEMA, _NAMED_USERS)
