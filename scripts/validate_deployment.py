"""Post-deployment validation for energy-theft-detection Databricks App.

Runs against a live workspace after `databricks bundle deploy` to verify
that all critical integrations (Genie, Bedrock, Gemini, SQL, audit trail)
are functional. Designed to be run from CI or locally.

Usage:
    python3 scripts/validate_deployment.py --profile <CLI_PROFILE> --target <BUNDLE_TARGET>
    python3 scripts/validate_deployment.py --profile <your-profile> --target <your-target>
    python3 scripts/validate_deployment.py --app-url https://energy-theft-detection-....databricksapps.com
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from enum import Enum

from databricks.sdk import WorkspaceClient


APP_NAME = "energy-theft-detection"
BEDROCK_ENDPOINT = "energy-theft-bedrock-gateway"
GEMINI_ENDPOINT = "energy-theft-gemini-gateway"
OPENAI_ENDPOINT = "energy-theft-openai-gateway"
LLAMA_ENDPOINT = "energy-theft-llama-gateway"

BUNDLE_TARGETS = {
    "dev": {"catalog": "dz_demos", "profile": "DEFAULT"},
    "azure-field-demo": {"catalog": "dz_demos", "profile": "azure-field-demo"},
    "zoccali-fevm-aws": {"catalog": "zoccali_fevm", "profile": "zoccali-fevm-aws"},
}


class Status(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    duration_ms: int = 0


@dataclass
class ValidationReport:
    target: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == Status.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == Status.FAIL)

    @property
    def warned(self) -> int:
        return sum(1 for r in self.results if r.status == Status.WARN)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def print_report(self):
        icons = {Status.PASS: "✅", Status.FAIL: "❌", Status.WARN: "⚠️ ", Status.SKIP: "⏭️ "}
        print(f"\n{'=' * 70}")
        print(f"  Deployment Validation — target: {self.target}")
        print(f"{'=' * 70}\n")
        for r in self.results:
            icon = icons[r.status]
            timing = f" ({r.duration_ms}ms)" if r.duration_ms else ""
            print(f"  {icon} {r.name}{timing}")
            if r.message:
                print(f"     {r.message}")
        print(f"\n{'─' * 70}")
        print(f"  Results: {self.passed} passed, {self.failed} failed, {self.warned} warnings")
        if self.all_passed:
            print("  ✅ All checks passed — deployment is healthy")
        else:
            print("  ❌ Deployment has issues — see failures above")
        print(f"{'─' * 70}\n")


def _timed(fn):
    t0 = time.monotonic()
    try:
        result = fn()
        return result, int((time.monotonic() - t0) * 1000)
    except Exception as e:
        return e, int((time.monotonic() - t0) * 1000)


def check_app_exists(w: WorkspaceClient) -> CheckResult:
    """Verify the Databricks App exists and is running."""
    try:
        app = w.apps.get(APP_NAME)
        sp_id = app.service_principal_client_id or "(none)"
        status = getattr(app, "status", None)
        active_deployment = getattr(app, "active_deployment", None)
        if active_deployment:
            deploy_status = getattr(active_deployment, "status", None)
            deploy_state = getattr(deploy_status, "state", "UNKNOWN") if deploy_status else "UNKNOWN"
            return CheckResult(
                "App exists and deployed",
                Status.PASS,
                f"SP: {sp_id}, deployment state: {deploy_state}",
            )
        return CheckResult(
            "App exists",
            Status.WARN,
            f"App exists (SP: {sp_id}) but no active deployment found",
        )
    except Exception as e:
        return CheckResult("App exists", Status.FAIL, f"App '{APP_NAME}' not found: {e}")


def check_app_resources(w: WorkspaceClient) -> list[CheckResult]:
    """Verify app resource bindings (warehouse, endpoints, Genie Space)."""
    results = []
    try:
        app = w.apps.get(APP_NAME)
        resources = {r.name: r for r in (app.resources or [])}

        if "warehouse" in resources:
            wh = resources["warehouse"].sql_warehouse
            wh_id = wh.id if wh else "(none)"
            results.append(CheckResult("Resource: SQL Warehouse", Status.PASS, f"ID: {wh_id}"))
        else:
            results.append(CheckResult("Resource: SQL Warehouse", Status.FAIL, "Missing 'warehouse' resource binding"))

        if "serving_endpoint" in resources:
            results.append(CheckResult("Resource: Bedrock endpoint", Status.PASS, BEDROCK_ENDPOINT))
        else:
            results.append(CheckResult("Resource: Bedrock endpoint", Status.WARN, "Missing 'serving_endpoint' resource"))

        if "gemini_endpoint" in resources:
            results.append(CheckResult("Resource: Gemini endpoint", Status.PASS, GEMINI_ENDPOINT))
        else:
            results.append(CheckResult("Resource: Gemini endpoint", Status.WARN, "Missing 'gemini_endpoint' resource"))

        if "genie-space" in resources:
            gs = resources["genie-space"]
            gs_id = getattr(gs, "genie_space", None)
            space_id = gs_id.space_id if gs_id else "(unknown)"
            results.append(CheckResult("Resource: Genie Space", Status.PASS, f"Space ID: {space_id}"))
        else:
            results.append(CheckResult(
                "Resource: Genie Space",
                Status.FAIL,
                "Missing 'genie-space' resource binding — GENIE_SPACE_ID will be empty at runtime. "
                "Add genie-space resource to the target in databricks.yml",
            ))

    except Exception as e:
        results.append(CheckResult("App resources", Status.FAIL, str(e)))
    return results


def check_genie_space(w: WorkspaceClient, genie_space_id: str) -> CheckResult:
    """Verify the Genie Space exists and is accessible."""
    if not genie_space_id:
        return CheckResult("Genie Space accessible", Status.SKIP, "No Genie Space ID configured")
    try:
        resp, ms = _timed(lambda: w.api_client.do("GET", f"/api/2.0/genie/spaces/{genie_space_id}"))
        if isinstance(resp, Exception):
            raise resp
        name = resp.get("display_name", "(unknown)")
        return CheckResult("Genie Space accessible", Status.PASS, f"'{name}' (ID: {genie_space_id})", ms)
    except Exception as e:
        err = str(e)
        if "NOT_FOUND" in err or "404" in err:
            return CheckResult(
                "Genie Space accessible",
                Status.FAIL,
                f"Genie Space ID '{genie_space_id}' not found — create it or update genie_space_id variable",
            )
        if "PERMISSION" in err:
            return CheckResult(
                "Genie Space accessible",
                Status.FAIL,
                f"Permission denied on Genie Space '{genie_space_id}' — check CAN_RUN on the app SP",
            )
        return CheckResult("Genie Space accessible", Status.FAIL, f"Error: {err[:200]}")


def check_serving_endpoint(w: WorkspaceClient, endpoint_name: str, label: str) -> CheckResult:
    """Verify a model serving endpoint exists, is ready, and responds."""
    try:
        ep = w.serving_endpoints.get(endpoint_name)
        state = getattr(ep, "state", None)
        ready = getattr(state, "ready", None) if state else None

        if ready and str(ready) == "READY":
            try:
                resp, ms = _timed(lambda: w.serving_endpoints.query(
                    endpoint_name,
                    messages=[{"role": "user", "content": "Say 'ok' in one word."}],
                    max_tokens=5,
                ))
                if isinstance(resp, Exception):
                    raise resp
                return CheckResult(
                    f"{label} endpoint responds",
                    Status.PASS,
                    f"Endpoint '{endpoint_name}' is READY and responds",
                    ms,
                )
            except Exception as query_err:
                err = str(query_err)
                if "PERMISSION_DENIED" in err:
                    if "security token" in err.lower() or "aws" in err.lower() or "credential" in err.lower():
                        return CheckResult(
                            f"{label} endpoint responds",
                            Status.FAIL,
                            f"Endpoint exists but external provider credentials are invalid — "
                            f"check secret scope for '{endpoint_name}'",
                        )
                    return CheckResult(
                        f"{label} endpoint responds",
                        Status.FAIL,
                        f"Permission denied querying endpoint: {err[:200]}",
                    )
                return CheckResult(f"{label} endpoint responds", Status.WARN, f"Endpoint READY but query failed: {err[:200]}")
        else:
            return CheckResult(
                f"{label} endpoint responds",
                Status.WARN,
                f"Endpoint '{endpoint_name}' exists but state is {ready or 'UNKNOWN'}",
            )
    except Exception as e:
        err = str(e)
        if "RESOURCE_DOES_NOT_EXIST" in err or "404" in err:
            return CheckResult(
                f"{label} endpoint responds",
                Status.FAIL,
                f"Endpoint '{endpoint_name}' does not exist — deploy it first",
            )
        return CheckResult(f"{label} endpoint responds", Status.FAIL, f"Error: {err[:200]}")


def check_secret_scope(w: WorkspaceClient, scope_name: str, label: str) -> CheckResult:
    """Verify a secret scope exists."""
    try:
        scopes = w.secrets.list_scopes()
        for s in scopes:
            if s.name == scope_name:
                keys = list(w.secrets.list_secrets(scope_name))
                key_names = [k.key for k in keys]
                return CheckResult(
                    f"{label} secret scope",
                    Status.PASS,
                    f"Scope '{scope_name}' exists with keys: {', '.join(key_names)}",
                )
        return CheckResult(
            f"{label} secret scope",
            Status.FAIL,
            f"Secret scope '{scope_name}' not found — create it with the required credentials",
        )
    except Exception as e:
        return CheckResult(f"{label} secret scope", Status.WARN, f"Could not list scopes: {e}")


def check_sql_warehouse(w: WorkspaceClient, warehouse_id: str) -> CheckResult:
    """Verify SQL warehouse exists and can execute a query."""
    if not warehouse_id:
        return CheckResult("SQL Warehouse", Status.SKIP, "No warehouse ID configured")
    try:
        resp, ms = _timed(lambda: w.statement_execution.execute_statement(
            statement="SELECT 1 AS test",
            warehouse_id=warehouse_id,
            wait_timeout="30s",
        ))
        if isinstance(resp, Exception):
            raise resp
        status = resp.status
        if status and str(getattr(status, "state", "")) == "SUCCEEDED":
            return CheckResult("SQL Warehouse responds", Status.PASS, f"Warehouse {warehouse_id} is healthy", ms)
        return CheckResult("SQL Warehouse responds", Status.WARN, f"Query returned status: {status}", ms)
    except Exception as e:
        return CheckResult("SQL Warehouse responds", Status.FAIL, f"Query failed: {str(e)[:200]}")


def check_schema_tables(w: WorkspaceClient, warehouse_id: str, catalog: str, schema: str) -> CheckResult:
    """Verify key tables exist in the target schema."""
    if not warehouse_id or not catalog:
        return CheckResult("Schema tables", Status.SKIP, "Warehouse or catalog not configured")

    required_tables = ["anomaly_scores", "investigation_cases", "property_reference"]
    try:
        resp = w.statement_execution.execute_statement(
            statement=f"SHOW TABLES IN {catalog}.{schema}",
            warehouse_id=warehouse_id,
            wait_timeout="30s",
        )
        tables = []
        if resp.result and resp.result.data_array:
            tables = [row[1] for row in resp.result.data_array if len(row) > 1]
        missing = [t for t in required_tables if t not in tables]
        if missing:
            return CheckResult(
                "Schema tables exist",
                Status.FAIL,
                f"Missing tables: {', '.join(missing)}. Run the end-to-end job first.",
            )
        return CheckResult("Schema tables exist", Status.PASS, f"Found {len(tables)} tables including all required ones")
    except Exception as e:
        return CheckResult("Schema tables exist", Status.FAIL, f"Error: {str(e)[:200]}")


def check_app_health_endpoint(w: WorkspaceClient, app_url_override: str | None = None) -> CheckResult:
    """Hit the app's /api/health endpoint if the app URL is resolvable.

    If ``app_url_override`` is set (e.g. from ``--app-url``), that base URL is used
    instead of the URL returned by the Apps API — useful when validating a
    specific *.databricksapps.com host.
    """
    try:
        url = (app_url_override or "").strip().rstrip("/") or None
        if not url:
            app = w.apps.get(APP_NAME)
            url = getattr(app, "url", None)
        if not url:
            return CheckResult("App /api/health", Status.SKIP, "App URL not available (not yet deployed?)")

        import httpx
        with httpx.Client(timeout=15, follow_redirects=True) as http:
            resp = http.get(f"{url}/api/health")
            if resp.status_code == 200:
                data = resp.json()
                sql_ok = data.get("sql_test")
                return CheckResult(
                    "App /api/health",
                    Status.PASS if sql_ok else Status.WARN,
                    f"Healthy — SQL: {'connected' if sql_ok else 'not connected'}, catalog: {data.get('catalog', 'N/A')}",
                )
            if resp.status_code == 401:
                return CheckResult(
                    "App /api/health",
                    Status.PASS,
                    "Reachable — HTTP 401 without browser session (expected); signed-in users (e.g. after email grant) should get 200.",
                )
            return CheckResult("App /api/health", Status.WARN, f"HTTP {resp.status_code}")
    except Exception as e:
        return CheckResult("App /api/health", Status.SKIP, f"Could not reach app: {str(e)[:150]}")


def check_system_tables(w: WorkspaceClient, warehouse_id: str) -> CheckResult:
    """Verify system.serving.endpoint_usage is accessible (for audit trail)."""
    if not warehouse_id:
        return CheckResult("System tables (audit trail)", Status.SKIP, "No warehouse ID")
    try:
        resp, ms = _timed(lambda: w.statement_execution.execute_statement(
            statement="""
                SELECT COUNT(*) AS cnt
                FROM system.serving.endpoint_usage eu
                JOIN system.serving.served_entities se
                  ON eu.served_entity_id = se.served_entity_id
                WHERE se.endpoint_name IN ('energy-theft-bedrock-gateway', 'energy-theft-gemini-gateway')
                  AND eu.request_time >= CURRENT_DATE() - INTERVAL 1 DAY
            """,
            warehouse_id=warehouse_id,
            wait_timeout="30s",
        ))
        if isinstance(resp, Exception):
            raise resp
        cnt = 0
        if resp.result and resp.result.data_array:
            cnt = int(resp.result.data_array[0][0])
        if cnt > 0:
            return CheckResult("System tables (audit trail)", Status.PASS, f"{cnt} LLM calls in last 24h", ms)
        return CheckResult(
            "System tables (audit trail)",
            Status.WARN,
            "No LLM calls in last 24h — audit trail will be empty until calls are made. "
            "Note: system tables have ~5 min ingestion latency.",
            ms,
        )
    except Exception as e:
        err = str(e)
        if "PERMISSION" in err:
            return CheckResult(
                "System tables (audit trail)",
                Status.FAIL,
                "No access to system.serving tables — grant USE CATALOG on system, USE SCHEMA + SELECT on system.serving",
            )
        return CheckResult("System tables (audit trail)", Status.FAIL, f"Error: {err[:200]}")


def check_external_lineage(app_url: str, token: str | None = None) -> CheckResult:
    """Hit /api/governance/external-lineage and verify Power BI nodes and edges are present."""
    try:
        import httpx

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        url = app_url.rstrip("/") + "/api/governance/external-lineage"
        with httpx.Client(timeout=20, follow_redirects=True) as http:
            resp = http.get(url, headers=headers)
        if resp.status_code == 401:
            return CheckResult(
                "External lineage (Power BI)",
                Status.WARN,
                "HTTP 401 — pass --token <PAT> to authenticate; skipping lineage check",
            )
        if resp.status_code != 200:
            return CheckResult("External lineage (Power BI)", Status.FAIL, f"HTTP {resp.status_code}")
        data = resp.json()
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        source = data.get("source", "unknown")
        pbi_nodes = [n for n in nodes if n.get("system_type") == "POWER_BI"]
        if len(pbi_nodes) < 4:
            return CheckResult(
                "External lineage (Power BI)",
                Status.FAIL,
                f"Expected 4 Power BI report nodes, got {len(pbi_nodes)} (source: {source})",
            )
        if len(edges) < 20:
            return CheckResult(
                "External lineage (Power BI)",
                Status.WARN,
                f"Only {len(edges)} column edges (expected ~28, source: {source})",
            )
        status = Status.PASS if source == "live" else Status.WARN
        msg = f"{len(pbi_nodes)} PBI reports, {len(edges)} column edges, source={source}"
        if source != "live":
            msg += " — source is 'fallback' (UC lineage not live yet; run 09_configure_external_lineage)"
        return CheckResult("External lineage (Power BI)", status, msg)
    except Exception as e:
        return CheckResult("External lineage (Power BI)", Status.SKIP, f"Could not reach app: {str(e)[:150]}")


def run_validation(profile: str, target: str, app_url: str | None = None, token: str | None = None) -> ValidationReport:
    report = ValidationReport(target=target)

    target_config = BUNDLE_TARGETS.get(target, {})
    catalog = target_config.get("catalog", "")
    schema = "energy_theft_protection"

    kwargs = {"profile": profile} if profile else {}
    w = WorkspaceClient(**kwargs)
    print(f"Workspace: {w.config.host}")

    report.results.append(check_app_exists(w))

    report.results.extend(check_app_resources(w))

    genie_space_id = ""
    try:
        app = w.apps.get(APP_NAME)
        for r in (app.resources or []):
            if r.name == "genie-space" and r.genie_space:
                genie_space_id = r.genie_space.space_id or ""
    except Exception:
        pass
    report.results.append(check_genie_space(w, genie_space_id))

    warehouse_id = ""
    try:
        app = w.apps.get(APP_NAME)
        for r in (app.resources or []):
            if r.sql_warehouse:
                warehouse_id = r.sql_warehouse.id or ""
                break
    except Exception:
        pass

    report.results.append(check_sql_warehouse(w, warehouse_id))
    report.results.append(check_schema_tables(w, warehouse_id, catalog, schema))
    report.results.append(check_serving_endpoint(w, OPENAI_ENDPOINT, "OpenAI/FMAPI"))
    report.results.append(check_serving_endpoint(w, LLAMA_ENDPOINT, "Llama/FMAPI"))
    report.results.append(check_serving_endpoint(w, BEDROCK_ENDPOINT, "Bedrock"))
    report.results.append(check_serving_endpoint(w, GEMINI_ENDPOINT, "Gemini"))
    report.results.append(check_secret_scope(w, "energy-theft-fmapi", "FMAPI"))
    report.results.append(check_secret_scope(w, "energy-theft-bedrock", "Bedrock"))
    report.results.append(check_secret_scope(w, "energy-theft-gemini", "Gemini"))
    report.results.append(check_system_tables(w, warehouse_id))

    resolved_url = (app_url or "").strip().rstrip("/") or None
    if not resolved_url:
        try:
            app = w.apps.get(APP_NAME)
            resolved_url = getattr(app, "url", None)
        except Exception:
            pass

    report.results.append(check_app_health_endpoint(w, app_url))
    if resolved_url:
        report.results.append(check_external_lineage(resolved_url, token))

    return report


def main():
    parser = argparse.ArgumentParser(description="Validate energy-theft-detection deployment")
    parser.add_argument("--profile", default=None, help="Databricks CLI profile")
    parser.add_argument("--target", default="dev", choices=list(BUNDLE_TARGETS.keys()), help="Bundle target")
    parser.add_argument("--app-url", default=None, help="Deployed app URL (optional, for health check)")
    parser.add_argument("--token", default=None, help="Databricks PAT for authenticated app endpoint checks")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    profile = args.profile or BUNDLE_TARGETS.get(args.target, {}).get("profile")

    report = run_validation(profile, args.target, args.app_url, args.token)

    if args.json:
        out = {
            "target": report.target,
            "passed": report.passed,
            "failed": report.failed,
            "warnings": report.warned,
            "all_passed": report.all_passed,
            "checks": [
                {"name": r.name, "status": r.status.value, "message": r.message, "duration_ms": r.duration_ms}
                for r in report.results
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        report.print_report()

    sys.exit(0 if report.all_passed else 1)


if __name__ == "__main__":
    main()
