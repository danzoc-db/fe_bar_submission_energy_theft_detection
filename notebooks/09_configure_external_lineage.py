# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — External Lineage (Power BI → UC)
# MAGIC
# MAGIC Registers four fake Power BI reports as Unity Catalog **external_metadata**
# MAGIC objects and creates column-level **external_lineage** relationships from
# MAGIC `anomaly_scores`, `investigation_cases`, `smart_meter_reads`, and
# MAGIC `model_performance_log` to the right report columns.
# MAGIC
# MAGIC Reads the definitions from the shared module
# MAGIC [`scripts/setup/external_lineage_objects.py`](../scripts/setup/external_lineage_objects.py)
# MAGIC — same module the backend `/api/governance/external-lineage` endpoint and
# MAGIC the `.pbip` generator import, so UC, the app, and the Power BI artifacts
# MAGIC never drift apart.
# MAGIC
# MAGIC ## Behaviour
# MAGIC - **Non-destructive by default.** Existing `external_metadata` objects are
# MAGIC   left in place when `CREATE EXTERNAL METADATA` is missing or when objects
# MAGIC   already exist. The monthly e2e job must never wipe UC lineage because a
# MAGIC   permission probe failed mid-run.
# MAGIC - **Optional recreate.** Set widget `force_recreate=true` to DELETE→CREATE
# MAGIC   our demo objects (only when the pre-flight probe passes).
# MAGIC - **Soft-skip on missing privilege.** If `CREATE EXTERNAL METADATA` is
# MAGIC   not held on the metastore, the notebook prints a clear remediation
# MAGIC   message and exits 0 — so it doesn't break the e2e job in workspaces
# MAGIC   where the SP can't register external objects.
# MAGIC - **SDK first, REST fallback.** Uses `WorkspaceClient.external_metadata`
# MAGIC   and `WorkspaceClient.external_lineage` when available (SDK ≥ 0.50);
# MAGIC   falls back to raw REST against `/api/2.0/lineage-tracking/*` for older
# MAGIC   installed SDKs, matching the pattern used in `08_configure_agent_atlas.py`.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
dbutils.widgets.dropdown("dry_run", "false", ["true", "false"])
dbutils.widgets.dropdown("force_recreate", "false", ["true", "false"])

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
DRY_RUN = dbutils.widgets.get("dry_run") == "true"
FORCE_RECREATE = dbutils.widgets.get("force_recreate") == "true"

print(f"Catalog:  {CATALOG}")
print(f"Schema:   {SCHEMA}")
print(f"Dry run:  {DRY_RUN}")
print(f"Force recreate: {FORCE_RECREATE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load shared definitions from `scripts/setup/external_lineage_objects.py`

# COMMAND ----------

import os
import sys
import uuid


def _find_scripts_setup_dir() -> str | None:
    """Locate scripts/setup relative to this notebook's deployed location.

    Asset Bundles upload the repo to a single workspace folder, so once we
    know the notebook path we can walk up one directory to find sibling
    scripts/setup/. Falls back to /Workspace path conventions.
    """
    try:
        ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()  # type: ignore[name-defined]
        nb_path = ctx.notebookPath().get()  # e.g. "/Workspace/Users/.../files/notebooks/09_..."
        nb_dir = os.path.dirname(nb_path)
        # /notebooks/.. → bundle root
        candidate = os.path.join(nb_dir, "..", "scripts", "setup")
        candidate_fs = "/Workspace" + os.path.normpath(candidate) if not candidate.startswith("/Workspace") else os.path.normpath(candidate)
        if os.path.isdir(candidate_fs):
            return candidate_fs
        if os.path.isdir(os.path.normpath(candidate)):
            return os.path.normpath(candidate)
    except Exception as e:
        print(f"  ⚠ Notebook context lookup failed: {e}")
    # Last-resort: project root if running locally
    here = os.path.dirname(os.path.realpath("__file__"))
    candidate = os.path.normpath(os.path.join(here, "..", "scripts", "setup"))
    return candidate if os.path.isdir(candidate) else None


_scripts_setup = _find_scripts_setup_dir()
if _scripts_setup:
    sys.path.insert(0, _scripts_setup)
    print(f"✓ scripts/setup resolved to: {_scripts_setup}")
else:
    raise RuntimeError(
        "Could not locate scripts/setup/ — expected sibling of notebooks/. "
        "Asset Bundle deploy should put both under the same files/ root."
    )

from external_lineage_objects import (  # noqa: E402
    COLUMN_EDGES,
    DEMO_PROPERTIES,
    POWER_BI_REPORTS,
    PBIReport,
    ColumnEdge,
)

print(f"✓ Loaded {len(POWER_BI_REPORTS)} Power BI reports, {len(COLUMN_EDGES)} column edges")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Privilege pre-flight
# MAGIC
# MAGIC `CREATE EXTERNAL METADATA` on the metastore is required. Without it the
# MAGIC notebook soft-skips so the e2e job still passes — the backend endpoint
# MAGIC will fall back to the static dataclass list and the lineage toggle in
# MAGIC the app still works (just without writes to Catalog Explorer).

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()


def _has_create_external_metadata() -> tuple[bool, str]:
    """Return (allowed, reason). True if we can write external_metadata."""
    try:
        # Definitive probe: attempt create+delete of a temporary object.
        # This validates CREATE EXTERNAL METADATA for the *runtime identity*.
        host = w.config.host
        headers = w.config.authenticate()
        import httpx

        probe_name = f"perm_probe_{uuid.uuid4().hex[:8]}"
        body = {
            "name": probe_name,
            "system_type": "POWER_BI",
            "entity_type": "report",
            "url": "https://example.com/probe",
            "description": "temporary permission probe",
            "columns": ["probe_col"],
            "properties": dict(DEMO_PROPERTIES),
        }
        create_resp = httpx.post(
            f"{host}/api/2.0/lineage-tracking/external-metadata",
            headers={**headers, "Content-Type": "application/json"},
            json=body,
            timeout=20,
        )
        if create_resp.status_code not in (200, 201):
            return False, f"CREATE probe returned {create_resp.status_code}: {create_resp.text[:200]}"

        # Cleanup probe object.
        _ = httpx.delete(
            f"{host}/api/2.0/lineage-tracking/external-metadata/{probe_name}",
            headers=headers,
            timeout=20,
        )
        return True, "CREATE/DELETE probe succeeded"
    except Exception as e:
        return False, f"pre-flight exception: {e}"


_allowed, _reason = _has_create_external_metadata()
print(f"Pre-flight: allowed={_allowed} ({_reason})")

if not _allowed:
    print("=" * 70)
    print("SOFT SKIP — CREATE EXTERNAL METADATA on the metastore is not held.")
    print(f"Reason: {_reason}")
    print()
    print("No UC external_metadata or external_lineage objects were modified.")
    print("Any objects registered in a previous successful run are preserved.")
    print()
    print("Remediation:")
    print("  1. Ask a metastore admin to grant your principal:")
    print("       GRANT CREATE EXTERNAL METADATA ON METASTORE TO `<sp-or-user>`;")
    print("  2. Re-run this notebook (optionally with force_recreate=true).")
    print()
    print("Until then the app's External Lineage toggle still works — the")
    print("backend will return live UC data when readable, else source=\"fallback\".")
    print("=" * 70)
    dbutils.notebook.exit(f"soft-skip: missing CREATE EXTERNAL METADATA grant ({_reason})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## SDK / REST helper layer
# MAGIC
# MAGIC Prefer the SDK; transparently fall back to REST against the GA
# MAGIC `/api/2.0/lineage-tracking/external-metadata` and
# MAGIC `/api/2.0/lineage-tracking/external-lineage` endpoints for older SDK
# MAGIC versions. Same defensive pattern used by `08_configure_agent_atlas.py`.

# COMMAND ----------

import json as _json

import httpx

_USE_SDK_METADATA = hasattr(w, "external_metadata")
_USE_SDK_LINEAGE = hasattr(w, "external_lineage")

print(f"SDK external_metadata: {_USE_SDK_METADATA}")
print(f"SDK external_lineage:  {_USE_SDK_LINEAGE}")

_host = w.config.host.rstrip("/")


def _rest_headers() -> dict:
    return {**w.config.authenticate(), "Content-Type": "application/json"}


def _get_external_metadata(name: str) -> dict | None:
    """Return external_metadata payload if present, else None."""
    if _USE_SDK_METADATA:
        try:
            obj = w.external_metadata.get_external_metadata(name=name)
            return {
                "name": getattr(obj, "name", name),
                "properties": dict(getattr(obj, "properties", None) or {}),
                "columns": list(getattr(obj, "columns", None) or []),
            }
        except Exception as e:
            if "NOT_FOUND" in str(e).upper() or "404" in str(e):
                return None
            raise
    resp = httpx.get(
        f"{_host}/api/2.0/lineage-tracking/external-metadata/{name}",
        headers=_rest_headers(),
        timeout=30,
    )
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise RuntimeError(f"GET failed {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def _is_demo_metadata(meta: dict) -> bool:
    props = meta.get("properties") or {}
    return all(props.get(k) == v for k, v in DEMO_PROPERTIES.items())


def _register_external_metadata(report: PBIReport) -> str:
    """Create-or-preserve one external_metadata object. Never deletes unless forced.

    Returns one of: created | preserved | recreated | skipped_foreign | dry_run
    """
    if DRY_RUN:
        existing = _get_external_metadata(report.name)
        if existing and _is_demo_metadata(existing) and not FORCE_RECREATE:
            return "dry_run_preserve"
        if FORCE_RECREATE and existing:
            return "dry_run_recreate"
        return "dry_run_create"

    existing = _get_external_metadata(report.name)
    if existing:
        if not _is_demo_metadata(existing):
            print(f"     ⚠ skipped — {report.name} exists but is not owned by this demo")
            return "skipped_foreign"
        if not FORCE_RECREATE:
            print(f"     ✓ preserved existing ({len(existing.get('columns') or report.columns)} columns)")
            return "preserved"
        _delete_external_metadata(report.name)

    try:
        _create_external_metadata(report)
    except Exception as e:
        msg = str(e)
        if "ALREADY_EXISTS" in msg.upper() or "409" in msg or "exists" in msg.lower():
            print("     ✓ already exists (preserved)")
            return "preserved"
        raise
    return "recreated" if existing else "created"


def _delete_external_metadata(name: str) -> None:
    """Best-effort delete; ignore 404."""
    if _USE_SDK_METADATA:
        try:
            w.external_metadata.delete_external_metadata(name=name)
            return
        except Exception as e:
            if "NOT_FOUND" not in str(e).upper() and "404" not in str(e):
                raise
            return
    resp = httpx.delete(
        f"{_host}/api/2.0/lineage-tracking/external-metadata/{name}",
        headers=_rest_headers(),
        timeout=30,
    )
    if resp.status_code not in (200, 204, 404):
        raise RuntimeError(f"DELETE failed {resp.status_code}: {resp.text[:200]}")


def _create_external_metadata(report: PBIReport) -> None:
    body = {
        "name": report.name,
        "system_type": "POWER_BI",
        "entity_type": report.entity_type,
        "url": report.url,
        "description": report.description,
        "columns": report.columns,
        "properties": dict(DEMO_PROPERTIES),
    }
    if _USE_SDK_METADATA:
        from databricks.sdk.service import catalog as _cat
        obj = _cat.ExternalMetadata(
            name=report.name,
            system_type=_cat.SystemType.POWER_BI,
            entity_type=report.entity_type,
            url=report.url,
            description=report.description,
            columns=report.columns,
            properties=dict(DEMO_PROPERTIES),
        )
        w.external_metadata.create_external_metadata(external_metadata=obj)
        return
    resp = httpx.post(
        f"{_host}/api/2.0/lineage-tracking/external-metadata",
        headers=_rest_headers(),
        json=body,
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"CREATE failed {resp.status_code}: {resp.text[:200]}")


def _list_existing_lineage(target_pbi: str) -> list[dict]:
    """List existing relationships whose target is this external_metadata."""
    if _USE_SDK_LINEAGE:
        from databricks.sdk.service import catalog as _cat
        obj_info = _cat.ExternalLineageObject(
            external_metadata=_cat.ExternalLineageExternalMetadata(name=target_pbi)
        )
        try:
            return [
                {"id": getattr(r, "external_lineage_info", None) and getattr(r.external_lineage_info, "id", None)}  # noqa: E501
                for r in w.external_lineage.list_external_lineage_relationships(
                    object_info=obj_info,
                    lineage_direction=_cat.LineageDirection.UPSTREAM,
                )
            ]
        except Exception as e:
            print(f"    (list lineage failed for {target_pbi}: {e})")
            return []
    return []  # REST path not strictly needed; create_or_replace below handles duplicates  # noqa: E501


def _delete_lineage_id(rel_id: str) -> None:
    if not rel_id:
        return
    if _USE_SDK_LINEAGE:
        try:
            # SDK has delete_external_lineage_relationship — signature varies.
            w.external_lineage.delete_external_lineage_relationship(id=rel_id)  # type: ignore[call-arg]
            return
        except Exception as e:
            print(f"    (SDK lineage delete failed for {rel_id}: {e})")
    resp = httpx.delete(
        f"{_host}/api/2.0/lineage-tracking/external-lineage/{rel_id}",
        headers=_rest_headers(),
        timeout=30,
    )
    if resp.status_code not in (200, 204, 404):
        print(f"    (REST lineage delete returned {resp.status_code})")


def _create_lineage(edge: ColumnEdge, catalog: str, schema: str) -> None:
    """Create one UPSTREAM column-level relationship: UC table → PBI report."""
    src_fqn = f"{catalog}.{schema}.{edge.source_table}"
    if _USE_SDK_LINEAGE:
        from databricks.sdk.service import catalog as _cat
        rel = _cat.CreateRequestExternalLineage(
            source=_cat.ExternalLineageObject(
                table=_cat.ExternalLineageTable(name=src_fqn),
            ),
            target=_cat.ExternalLineageObject(
                external_metadata=_cat.ExternalLineageExternalMetadata(name=edge.target_pbi),
            ),
            columns=[
                _cat.ColumnRelationship(source=edge.source_column, target=edge.target_column),
            ],
            properties=dict(DEMO_PROPERTIES),
        )
        w.external_lineage.create_external_lineage_relationship(external_lineage_relationship=rel)
        return
    body = {
        "source": {"table": {"name": src_fqn}},
        "target": {"external_metadata": {"name": edge.target_pbi}},
        "columns": [
            {"source": edge.source_column, "target": edge.target_column},
        ],
        "properties": dict(DEMO_PROPERTIES),
    }
    resp = httpx.post(
        f"{_host}/api/2.0/lineage-tracking/external-lineage",
        headers=_rest_headers(),
        json=body,
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"CREATE lineage failed {resp.status_code}: {resp.text[:200]}")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Register external_metadata (create-or-preserve)

# COMMAND ----------

print(f"\nRegistering {len(POWER_BI_REPORTS)} Power BI reports as UC external_metadata\n")
print(f"Mode: {'force recreate (DELETE→CREATE)' if FORCE_RECREATE else 'preserve existing (no deletes)'}\n")

metadata_stats: dict[str, int] = {}
metadata_failures = 0
for report in POWER_BI_REPORTS:
    print(f"  → {report.name}  ({report.display})")
    try:
        outcome = _register_external_metadata(report)
        metadata_stats[outcome] = metadata_stats.get(outcome, 0) + 1
        if outcome.startswith("dry_run"):
            print(f"     [dry-run] {outcome}")
    except Exception as e:
        metadata_failures += 1
        print(f"     ✗ FAILED (existing object preserved): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register column-level external_lineage relationships
# MAGIC
# MAGIC Each `ColumnEdge` becomes one UPSTREAM relationship: a UC table is the
# MAGIC upstream source, the Power BI external_metadata object is the downstream
# MAGIC target. Catalog Explorer renders these as outbound arrows from the table.

# COMMAND ----------

print(f"\nCreating {len(COLUMN_EDGES)} column-level lineage relationships\n")

# Group existing-by-target for idempotent re-create where possible.
created = 0
failed = 0
for edge in COLUMN_EDGES:
    src = f"{CATALOG}.{SCHEMA}.{edge.source_table}.{edge.source_column}"
    tgt = f"{edge.target_pbi}.{edge.target_column}"
    print(f"  → {src} → {tgt}")
    if DRY_RUN:
        print("     [dry-run] would CREATE lineage")
        continue
    try:
        _create_lineage(edge, CATALOG, SCHEMA)
        created += 1
        print("     ✓ created")
    except Exception as e:
        # Likely "ALREADY_EXISTS" on re-run — SDK returns it as a 409-ish error.
        msg = str(e)
        if "ALREADY_EXISTS" in msg.upper() or "409" in msg or "exists" in msg.lower():
            print("     ✓ already exists (idempotent)")
            created += 1
        else:
            failed += 1
            print(f"     ✗ FAILED: {msg[:200]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 70)
print("External Lineage configuration summary")
print("=" * 70)
print(f"  Reports attempted:         {len(POWER_BI_REPORTS)}")
print(f"  Report outcomes:           {metadata_stats or '(none — dry run only)'}")
print(f"  Report registration fails: {metadata_failures}")
print(f"  Lineage edges attempted:   {len(COLUMN_EDGES)}")
print(f"  Lineage edges created/ok:  {created}")
print(f"  Lineage edges failed:      {failed}")
if metadata_failures or failed:
    print()
    print("  ⚠ Some writes failed — existing UC objects were not deleted.")
    print("    The end-to-end job can continue; the app falls back to static")
    print("    lineage definitions when live UC reads are unavailable.")
print()
print("  Verify in Catalog Explorer:")
for r in POWER_BI_REPORTS:
    print(f"    • {r.display}  ({r.name})")
print()
print("  Backend endpoint:  GET /api/governance/external-lineage")
print("  Frontend toggle:   UC Lineage tab → 'External Lineage' switch")
print("=" * 70)
