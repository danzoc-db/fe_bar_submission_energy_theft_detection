"""Grant a workspace user broad access to the energy-theft-detection demo.

Applies:
  - Databricks App: CAN_MANAGE on ``energy-theft-detection``
  - SQL warehouse (from app resources or --warehouse-id): CAN_MANAGE
  - Model serving / AI Gateway endpoints (by name): CAN_MANAGE (uses endpoint id for Permissions API)
  - Genie Space (from app resources or --genie-space-id): CAN_MANAGE
  - Unity Catalog: USE CATALOG + ALL PRIVILEGES ON SCHEMA (demo schema)

Requires an admin-capable principal in ``databricks auth`` / CLI profile.

Usage:
  python3 scripts/grant_user_demo_access.py \\
    --profile <your-profile> --catalog <your_catalog> --user user@example.com --apply

  # Preview only (no API writes):
  python3 scripts/grant_user_demo_access.py \\
    --profile <your-profile> --catalog <your_catalog> --user user@example.com
"""

from __future__ import annotations

import argparse
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppAccessControlRequest, AppPermissionLevel
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

APP_NAME = "energy-theft-detection"
DEFAULT_SCHEMA = "energy_theft_protection"
DEFAULT_SERVING_ENDPOINT_NAMES = [
    "energy-theft-bedrock-gateway",
    "energy-theft-gemini-gateway",
    "energy-theft-openai-gateway",
    "energy-theft-llama-gateway",
]


def _user_principal(user: str) -> str:
    u = user.strip()
    if not u:
        raise SystemExit("--user is required (Databricks login, usually email)")
    return u


def _grant_app(w: WorkspaceClient, user: str, apply: bool) -> None:
    req = AppAccessControlRequest(
        user_name=user,
        permission_level=AppPermissionLevel.CAN_MANAGE,
    )
    print(f"[app] {APP_NAME}: CAN_MANAGE for {user}")
    if apply:
        w.apps.update_permissions(APP_NAME, access_control_list=[req])
        print("      OK")


def _grant_warehouse(w: WorkspaceClient, user: str, warehouse_id: str, apply: bool) -> None:
    if not warehouse_id:
        print("[warehouse] SKIP — no warehouse id")
        return
    ac = AccessControlRequest(user_name=user, permission_level=PermissionLevel.CAN_MANAGE)
    print(f"[warehouse] {warehouse_id}: CAN_MANAGE for {user}")
    if apply:
        w.permissions.update("sql/warehouses", warehouse_id, access_control_list=[ac])
        print("           OK")


def _grant_serving(w: WorkspaceClient, user: str, names: list[str], apply: bool) -> None:
    ac = AccessControlRequest(user_name=user, permission_level=PermissionLevel.CAN_MANAGE)
    for name in names:
        try:
            ep = w.serving_endpoints.get(name)
            eid = ep.id or ""
            if not eid:
                print(f"[serving] {name}: SKIP — no endpoint id")
                continue
            print(f"[serving] {name} ({eid}): CAN_MANAGE for {user}")
            if apply:
                w.permissions.update("serving-endpoints", eid, access_control_list=[ac])
                print("          OK")
        except Exception as e:
            print(f"[serving] {name}: ERROR {e}")


def _grant_genie(w: WorkspaceClient, user: str, space_id: str, apply: bool) -> None:
    if not space_id:
        print("[genie] SKIP — no Genie space id on app")
        return
    print(f"[genie] space {space_id}: CAN_MANAGE (or CAN_RUN) for {user}")
    if apply:
        try:
            w.permissions.update(
                "genie",
                space_id,
                access_control_list=[
                    AccessControlRequest(user_name=user, permission_level=PermissionLevel.CAN_MANAGE)
                ],
            )
            print("        OK (CAN_MANAGE)")
        except Exception as e1:
            try:
                w.permissions.update(
                    "genie",
                    space_id,
                    access_control_list=[
                        AccessControlRequest(user_name=user, permission_level=PermissionLevel.CAN_RUN)
                    ],
                )
                print(f"        OK (CAN_RUN; CAN_MANAGE failed: {e1})")
            except Exception as e2:
                print(f"        ERROR: CAN_MANAGE: {e1}; CAN_RUN: {e2}")


def _grant_uc_schema(w: WorkspaceClient, user: str, warehouse_id: str, catalog: str, schema: str, apply: bool) -> None:
    if not warehouse_id:
        print("[uc] SKIP — no warehouse for SQL execution")
        return
    schema_fqn = f"{catalog}.{schema}"
    principal = user.replace("`", "")
    stmts = [
        f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{principal}`",
        f"GRANT ALL PRIVILEGES ON SCHEMA {schema_fqn} TO `{principal}`",
    ]
    for stmt in stmts:
        print(f"[uc] {stmt}")
        if apply:
            try:
                w.statement_execution.execute_statement(
                    statement=stmt,
                    warehouse_id=warehouse_id,
                    wait_timeout="50s",
                )
                print("     OK")
            except Exception as e:
                print(f"     ERROR: {e}")
                if "ALL PRIVILEGES" in stmt.upper():
                    fb = (
                        f"GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE, CREATE FUNCTION, "
                        f"CREATE MODEL, EXECUTE ON SCHEMA {schema_fqn} TO `{principal}`"
                    )
                    print(f"[uc] fallback: {fb}")
                    w.statement_execution.execute_statement(
                        statement=fb,
                        warehouse_id=warehouse_id,
                        wait_timeout="50s",
                    )
                    print("     OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant demo app + data access to a user")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name for the demo")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="Unity Catalog schema (default: energy_theft_protection)")
    parser.add_argument("--user", required=True, help="Databricks user name (email)")
    parser.add_argument("--warehouse-id", default="", help="SQL warehouse ID fallback if not bound on the app")
    parser.add_argument("--genie-space-id", default="", help="Genie space ID fallback if not bound on the app")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform grants (omit for dry run — no auth required)",
    )
    args = parser.parse_args()
    user = _user_principal(args.user)

    catalog = args.catalog
    schema = args.schema
    warehouse_id_fb = args.warehouse_id
    genie_space_id_fb = args.genie_space_id
    serving_names = list(DEFAULT_SERVING_ENDPOINT_NAMES)

    if not args.apply:
        print("Dry run (no API calls). Profile:", args.profile)
        print("Catalog:", catalog)
        print("User:", user)
        print("\nPlanned grants:")
        print(f"  - App {APP_NAME}: CAN_MANAGE")
        wh_label = warehouse_id_fb or "(from app resources)"
        print(f"  - Warehouse {wh_label}: CAN_MANAGE")
        for n in serving_names:
            print(f"  - Serving endpoint {n}: CAN_MANAGE")
        genie_label = genie_space_id_fb or "(from app resources)"
        print(f"  - Genie space {genie_label}: CAN_MANAGE")
        print(f"  - UC catalog `{catalog}`: USE CATALOG")
        print(f"  - UC schema `{catalog}.{schema}`: ALL PRIVILEGES (or schema privilege fallback)")
        print(
            f"\nRun with auth:\n  databricks auth login --host <your-workspace-host>\n"
            f"  python3 scripts/grant_user_demo_access.py --profile {args.profile} "
            f"--catalog {catalog} --user {user} --apply"
        )
        sys.exit(0)

    w = WorkspaceClient(profile=args.profile)
    print(f"Workspace: {w.config.host}\nUser: {user}\n")

    warehouse_id = warehouse_id_fb
    genie_space_id = genie_space_id_fb
    try:
        app = w.apps.get(APP_NAME)
        for r in app.resources or []:
            if r.sql_warehouse and r.sql_warehouse.id:
                warehouse_id = r.sql_warehouse.id or warehouse_id
            if r.genie_space and r.genie_space.space_id:
                genie_space_id = r.genie_space.space_id or genie_space_id
    except Exception as e:
        print(f"WARN: could not load app '{APP_NAME}': {e}")
        print("      Using --warehouse-id / --genie-space-id fallbacks where provided.")

    _grant_app(w, user, True)
    _grant_warehouse(w, user, warehouse_id, True)
    _grant_serving(w, user, serving_names, True)
    _grant_genie(w, user, genie_space_id, True)
    _grant_uc_schema(w, user, warehouse_id, catalog, schema, True)
    print("\nDone.")


if __name__ == "__main__":
    main()
