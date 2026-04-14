"""Verify and fix permissions for the energy-theft-detection Databricks App.

Run after `databricks bundle deploy` to ensure the app's service principal
has CAN_USE on the SQL warehouse and USE SCHEMA + SELECT on the data schema.

Usage:
    python3 scripts/verify_app_permissions.py [--profile PROFILE] [--fix]

Without --fix, the script only reports missing permissions.
With --fix, it grants any missing permissions automatically.
"""

import argparse
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import ObjectPermissions


APP_NAME = "energy-theft-detection"
DEFAULT_CATALOG = "dz_demos"
DEFAULT_SCHEMA = "energy_theft_protection"


def get_app_info(w: WorkspaceClient) -> tuple[str, str]:
    """Return (service_principal_client_id, warehouse_id) for the app."""
    app = w.apps.get(APP_NAME)
    sp_id = app.service_principal_client_id or ""
    wh_id = ""
    for r in app.resources or []:
        if r.sql_warehouse:
            wh_id = r.sql_warehouse.id or ""
            break
    return sp_id, wh_id


def check_warehouse_permission(w: WorkspaceClient, sp_id: str, wh_id: str) -> bool:
    """Check if the SP has CAN_USE on the warehouse."""
    perms: ObjectPermissions = w.permissions.get("sql/warehouses", wh_id)
    for acl in perms.access_control_list or []:
        if acl.service_principal_name == sp_id:
            for p in acl.all_permissions or []:
                if p.permission_level and p.permission_level.value in ("CAN_USE", "CAN_MANAGE", "IS_OWNER"):
                    return True
    return False


def fix_warehouse_permission(w: WorkspaceClient, sp_id: str, wh_id: str) -> None:
    from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
    w.permissions.update(
        "sql/warehouses",
        wh_id,
        access_control_list=[
            AccessControlRequest(
                service_principal_name=sp_id,
                permission_level=PermissionLevel.CAN_USE,
            )
        ],
    )


def check_schema_grants(w: WorkspaceClient, sp_id: str, catalog: str, schema_fqn: str) -> dict[str, bool]:
    """Check USE CATALOG, USE SCHEMA, SELECT grants for the SP."""
    results: dict[str, bool] = {
        "USE CATALOG": False,
        "USE SCHEMA": False,
        "SELECT": False,
    }
    try:
        resp = w.statement_execution.execute_statement(
            statement=f"SHOW GRANTS ON CATALOG {catalog}",
            warehouse_id=check_schema_grants._wh_id,
            wait_timeout="30s",
        )
        for row in (resp.result.data_array or []) if resp.result else []:
            row_str = str(row).upper()
            if sp_id in str(row) and ("USE_CATALOG" in row_str or "USE CATALOG" in row_str):
                results["USE CATALOG"] = True
    except Exception as e:
        print(f"  Warning: could not check catalog grants: {e}")

    try:
        resp = w.statement_execution.execute_statement(
            statement=f"SHOW GRANTS ON SCHEMA {schema_fqn}",
            warehouse_id=check_schema_grants._wh_id,
            wait_timeout="30s",
        )
        for row in (resp.result.data_array or []) if resp.result else []:
            row_str = str(row).upper()
            if sp_id in str(row):
                if "USE_SCHEMA" in row_str or "USE SCHEMA" in row_str:
                    results["USE SCHEMA"] = True
                if "SELECT" in row_str:
                    results["SELECT"] = True
    except Exception as e:
        print(f"  Warning: could not check schema grants: {e}")

    return results


def fix_schema_grants(w: WorkspaceClient, sp_id: str, missing: list[str], catalog: str, schema_fqn: str) -> None:
    stmts: list[str] = []
    if "USE CATALOG" in missing:
        stmts.append(f"GRANT USE CATALOG ON CATALOG {catalog} TO `{sp_id}`")
    schema_privs = [g for g in missing if g in ("USE SCHEMA", "SELECT")]
    if schema_privs:
        privs = ", ".join(schema_privs)
        stmts.append(f"GRANT {privs} ON SCHEMA {schema_fqn} TO `{sp_id}`")
    for stmt in stmts:
        try:
            w.statement_execution.execute_statement(
                statement=stmt,
                warehouse_id=check_schema_grants._wh_id,
                wait_timeout="30s",
            )
            print(f"  ✅ {stmt}")
        except Exception as e:
            print(f"  ❌ Failed: {stmt}\n     {e}")


def main():
    parser = argparse.ArgumentParser(description="Verify app permissions")
    parser.add_argument("--profile", default=None, help="Databricks CLI profile")
    parser.add_argument("--fix", action="store_true", help="Auto-fix missing permissions")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, help=f"UC catalog (default: {DEFAULT_CATALOG})")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help=f"UC schema (default: {DEFAULT_SCHEMA})")
    args = parser.parse_args()

    catalog = args.catalog
    schema_fqn = f"{catalog}.{args.schema}"

    kwargs = {"profile": args.profile} if args.profile else {}
    w = WorkspaceClient(**kwargs)
    print(f"Workspace: {w.config.host}")

    try:
        sp_id, wh_id = get_app_info(w)
    except Exception as e:
        print(f"⚠ App '{APP_NAME}' not found (first deploy?) — skipping permission check.")
        print(f"  Re-run after the app is created: python3 scripts/verify_app_permissions.py --fix")
        sys.exit(0)
    if not sp_id:
        print(f"❌ Could not find service principal for app '{APP_NAME}'")
        sys.exit(1)
    print(f"App SP:    {sp_id}")
    print(f"Warehouse: {wh_id}")
    check_schema_grants._wh_id = wh_id

    all_ok = True

    # 1. Warehouse CAN_USE
    print("\n[1/2] SQL Warehouse CAN_USE")
    if check_warehouse_permission(w, sp_id, wh_id):
        print("  ✅ CAN_USE granted")
    else:
        all_ok = False
        print("  ❌ CAN_USE missing")
        if args.fix:
            fix_warehouse_permission(w, sp_id, wh_id)
            print("  ✅ Fixed — CAN_USE granted")

    # 2. Schema grants
    print(f"\n[2/2] Unity Catalog grants on {schema_fqn}")
    grants = check_schema_grants(w, sp_id, catalog, schema_fqn)
    missing = [g for g, ok in grants.items() if not ok]
    for grant, ok in grants.items():
        print(f"  {'✅' if ok else '❌'} {grant}")
    if missing:
        all_ok = False
        if args.fix:
            fix_schema_grants(w, sp_id, missing, catalog, schema_fqn)

    if all_ok:
        print("\n✅ All permissions verified — app is ready.")
    elif not args.fix:
        print(f"\n❌ Missing permissions detected. Re-run with --fix to auto-repair.")
        sys.exit(1)
    else:
        print("\n✅ Permissions fixed. Restart the app to pick up changes.")


if __name__ == "__main__":
    main()
