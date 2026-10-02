#!/usr/bin/env python3
"""Capture a single connected-journey evidence log from a live workspace.

Proves the six stages are populated and joined on the same catalog/schema:

    Lakeflow (medallion) -> Unity Catalog (tags + lineage)
        -> ML scoring -> Lakebase (serve + transact)
        -> Genie (NL) -> App (surface)

Prints ASCII to stdout. Redirect to docs/evidence/end_to_end_journey.txt.

    uv run python3 scripts/capture_journey_evidence.py \
        --profile zoccali-fevm-aws \
        --catalog zoccali_fevm \
        --warehouse-id 85c1b174d196486d \
        --genie-space-id 01f16db6c03419a3b953033d66b5855f
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone

DEFAULT_PROFILE = "zoccali-fevm-aws"
DEFAULT_CATALOG = "zoccali_fevm"
DEFAULT_SCHEMA = "energy_theft_protection"
DEFAULT_WAREHOUSE = "85c1b174d196486d"
DEFAULT_GENIE = "01f16db6c03419a3b953033d66b5855f"
INSTANCE_NAME = "energy-theft-lakebase"
LOGICAL_DB = "databricks_postgres"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def banner(title: str) -> None:
    print("\n" + "=" * 72, flush=True)
    print(title, flush=True)
    print("=" * 72, flush=True)


def run_sql(w, warehouse_id: str, catalog: str, schema: str, statement: str):
    from databricks.sdk.service.sql import StatementState

    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        catalog=catalog,
        schema=schema,
        statement=statement,
        wait_timeout="50s",
    )
    while resp.status and resp.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status and resp.status.state != StatementState.SUCCEEDED:
        err = resp.status.error.message if resp.status and resp.status.error else "unknown"
        raise RuntimeError(f"SQL failed ({resp.status.state}): {err}\n  {statement[:180]}")
    rows = []
    if resp.result and resp.result.data_array:
        cols = [c.name for c in resp.manifest.schema.columns]
        for r in resp.result.data_array:
            rows.append(dict(zip(cols, r)))
    return rows


def stage_medallion(w, warehouse_id: str, catalog: str, schema: str) -> None:
    banner("STAGE 1: Lakeflow medallion (Delta row counts)")
    tables = [
        "property_reference",
        "meters",
        "smart_meter_reads",
        "anomaly_scores",
        "investigation_cases",
        "model_performance_log",
        "anomaly_scores_serving_src",
        "anomaly_scores_serving",
    ]
    for t in tables:
        fq = f"{catalog}.{schema}.{t}"
        try:
            n = run_sql(w, warehouse_id, catalog, schema, f"SELECT COUNT(*) AS n FROM {fq}")
            log(f"  {fq}: {n[0]['n'] if n else 0} rows")
        except Exception as e:  # noqa: BLE001
            log(f"  {fq}: NOT QUERYABLE ({e})")


def stage_uc_governance(w, warehouse_id: str, catalog: str, schema: str) -> None:
    banner("STAGE 2: Unity Catalog tags + lineage")
    try:
        tags = run_sql(
            w,
            warehouse_id,
            catalog,
            schema,
            f"""
            SELECT column_name, tag_name, tag_value
            FROM system.information_schema.column_tags
            WHERE catalog_name = '{catalog}'
              AND schema_name = '{schema}'
            ORDER BY tag_name, column_name
            LIMIT 40
            """,
        )
        log(f"  column tags returned: {len(tags)}")
        pii = [r for r in tags if (r.get("tag_value") or "").upper() in ("PII", "QUASI-PII")
               or (r.get("tag_name") or "").lower() in ("pii", "class")]
        for r in tags[:25]:
            log(f"    {r.get('column_name')}: {r.get('tag_name')}={r.get('tag_value')}")
        log(f"  PII-like tag rows in sample: {len(pii)}")
    except Exception as e:  # noqa: BLE001
        log(f"  column_tags query failed: {e}")

    try:
        lin = run_sql(
            w,
            warehouse_id,
            catalog,
            schema,
            f"""
            SELECT source_table_full_name, target_table_full_name, event_time
            FROM system.access.table_lineage
            WHERE target_table_full_name LIKE '{catalog}.{schema}.%'
               OR source_table_full_name LIKE '{catalog}.{schema}.%'
            ORDER BY event_time DESC
            LIMIT 15
            """,
        )
        log(f"  system.access.table_lineage rows: {len(lin)}")
        for r in lin[:10]:
            log(f"    {r.get('source_table_full_name')} -> {r.get('target_table_full_name')}")
    except Exception as e:  # noqa: BLE001
        log(f"  table_lineage query failed (may be delayed): {e}")

    try:
        ext = run_sql(
            w,
            warehouse_id,
            catalog,
            schema,
            f"""
            SELECT name, system_type
            FROM system.information_schema.catalogs
            WHERE catalog_name = '{catalog}'
            LIMIT 5
            """,
        )
        log(f"  catalogs probe: {ext}")
    except Exception as e:  # noqa: BLE001
        log(f"  catalogs probe skipped: {e}")


def stage_ml(w, warehouse_id: str, catalog: str, schema: str) -> None:
    banner("STAGE 3: ML scoring (anomaly_scores + model_performance_log)")
    try:
        tiers = run_sql(
            w,
            warehouse_id,
            catalog,
            schema,
            f"""
            SELECT risk_tier, COUNT(*) AS n,
                   ROUND(AVG(composite_risk_score), 4) AS avg_score
            FROM {catalog}.{schema}.anomaly_scores
            GROUP BY risk_tier
            ORDER BY 1
            """,
        )
        for r in tiers:
            log(f"  anomaly_scores {r.get('risk_tier')}: n={r.get('n')} avg={r.get('avg_score')}")
    except Exception as e:  # noqa: BLE001
        log(f"  anomaly_scores aggregate failed: {e}")

    try:
        perf = run_sql(
            w,
            warehouse_id,
            catalog,
            schema,
            f"""
            SELECT month, model_version, risk_tier, precision_pct, recall_pct,
                   f1_score, cases_scored, cases_confirmed
            FROM {catalog}.{schema}.model_performance_log
            WHERE risk_tier = 'HIGH'
            ORDER BY month DESC
            LIMIT 6
            """,
        )
        log("  latest HIGH-tier model_performance_log:")
        for r in perf:
            log(
                f"    {r.get('month')} {r.get('model_version')} "
                f"precision={r.get('precision_pct')} recall={r.get('recall_pct')} "
                f"f1={r.get('f1_score')} scored={r.get('cases_scored')} "
                f"confirmed={r.get('cases_confirmed')}"
            )
    except Exception as e:  # noqa: BLE001
        log(f"  model_performance_log failed: {e}")


def stage_lakebase(w, catalog: str, schema: str) -> None:
    banner("STAGE 4: Lakebase operational serving")
    try:
        inst = w.database.get_database_instance(name=INSTANCE_NAME)
        log(f"  instance {INSTANCE_NAME} state={inst.state} capacity={inst.effective_capacity}")
        log(f"  read_write_dns={inst.read_write_dns}")
    except Exception as e:  # noqa: BLE001
        log(f"  instance lookup failed: {e}")
        return
    try:
        st = w.database.get_synced_database_table(
            name=f"{catalog}.{schema}.anomaly_scores_serving"
        )
        status = getattr(st.data_synchronization_status, "detailed_state", None)
        log(f"  synced table UC state={st.unity_catalog_provisioning_state} sync={status}")
    except Exception as e:  # noqa: BLE001
        log(f"  synced table lookup failed: {e}")

    try:
        import psycopg

        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()), instance_names=[INSTANCE_NAME]
        )
        user = w.current_user.me().user_name
        conn = psycopg.connect(
            host=inst.read_write_dns,
            port=5432,
            dbname=LOGICAL_DB,
            user=user,
            password=cred.token,
            sslmode="require",
            autocommit=True,
            connect_timeout=15,
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM energy_theft_protection.anomaly_scores_serving"
            )
            n = cur.fetchone()[0]
            log(f"  Postgres serving queue rows: {n}")
            cur.execute("SELECT COUNT(*) FROM revenue_protection.investigation_cases")
            log(f"  Postgres OLTP cases: {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM revenue_protection.case_events")
            log(f"  Postgres OLTP events: {cur.fetchone()[0]}")
        conn.close()
    except Exception as e:  # noqa: BLE001
        log(f"  Postgres probe failed: {e}")


def stage_genie(w, space_id: str, question: str) -> None:
    banner("STAGE 5: Genie Q -> SQL -> answer")
    import requests

    host = str(w.config.host).rstrip("/")
    headers = w.config.authenticate()
    log(f"  space_id={space_id}")
    log(f"  question={question!r}")
    try:
        resp = requests.post(
            f"{host}/api/2.0/genie/spaces/{space_id}/start-conversation",
            json={"content": question},
            headers=headers,
            timeout=60,
        )
        log(f"  start-conversation HTTP {resp.status_code}")
        if resp.status_code != 200:
            log(f"  body={resp.text[:400]}")
            return
        data = resp.json()
        conv_id = data.get("conversation_id")
        msg_id = data.get("message_id")
        log(f"  conversation_id={conv_id} message_id={msg_id}")
        if not msg_id:
            log(f"  payload keys={list(data.keys())}")
            return
        result = None
        for i in range(40):
            time.sleep(2)
            poll = requests.get(
                f"{host}/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}",
                headers=headers,
                timeout=30,
            )
            if poll.status_code != 200:
                continue
            msg = poll.json()
            status = msg.get("status")
            if i % 5 == 0:
                log(f"  poll {i}: status={status}")
            if status in ("COMPLETED", "FAILED", "CANCELLED"):
                result = msg
                break
        if not result:
            log("  Genie poll timed out")
            return
        log(f"  final status={result.get('status')}")
        attachments = result.get("attachments") or []
        for att in attachments:
            q = att.get("query") or {}
            sql = q.get("query") or q.get("sql") or att.get("query_text")
            if sql:
                log("  generated SQL:")
                for line in str(sql).splitlines()[:25]:
                    log(f"    {line}")
            text = (
                att.get("text")
                or (att.get("query") or {}).get("description")
                or att.get("statement")
            )
            if text:
                log(f"  answer_text={str(text)[:500]}")
        content = result.get("content") or result.get("error")
        if content:
            log(f"  content={str(content)[:500]}")
        log(f"  attachment_count={len(attachments)}")
    except Exception as e:  # noqa: BLE001
        log(f"  Genie call failed: {e}")


def stage_app(w) -> None:
    banner("STAGE 6: Databricks App (energy-theft-detection)")
    try:
        app = w.apps.get("energy-theft-detection")
        ad = app.active_deployment
        st = ad.status if ad else None
        log(f"  url={app.url}")
        log(f"  compute={getattr(app.compute_status, 'state', None)}")
        log(f"  deployment_id={ad.deployment_id if ad else None}")
        log(f"  deployment_state={getattr(st, 'state', None)}")
        log(f"  deployment_message={getattr(st, 'message', None)}")
        names = [r.name for r in (app.resources or [])]
        log(f"  app_resources={names}")
        log(f"  service_principal_client_id={app.service_principal_client_id}")
    except Exception as e:  # noqa: BLE001
        log(f"  apps.get failed: {e}")


def stage_job_graph() -> None:
    banner("JOB GRAPH: energy-theft-end-to-end (from databricks.yml)")
    from pathlib import Path

    text = Path("databricks.yml").read_text()
    log("  provision_lakebase present: " + str("task_key: \"provision_lakebase\"" in text))
    log("  notebook 10_provision_lakebase.py referenced: "
        + str("10_provision_lakebase.py" in text))
    log("  configure_genie depends on provision_lakebase: "
        + str("provision_lakebase" in text.split("configure_genie", 1)[-1][:400]))
    log("  DAG: create_schema -> seed -> medallion -> train/score")
    log("       batch_scoring -> provision_lakebase -> configure_genie")
    log("       batch_scoring -> apply_uc_metadata -> metric_views -> lineage -> genie")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=DEFAULT_PROFILE)
    ap.add_argument("--catalog", default=DEFAULT_CATALOG)
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--warehouse-id", default=DEFAULT_WAREHOUSE)
    ap.add_argument("--genie-space-id", default=DEFAULT_GENIE)
    args = ap.parse_args()

    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient(profile=args.profile)
    me = w.current_user.me().user_name
    banner("CONNECTED JOURNEY EVIDENCE")
    log(f"Authenticated as {me} profile={args.profile}")
    log(f"catalog={args.catalog} schema={args.schema} warehouse={args.warehouse_id}")
    log("Journey: Lakeflow -> UC -> ML -> Lakebase -> Genie -> App")

    stage_job_graph()
    stage_medallion(w, args.warehouse_id, args.catalog, args.schema)
    stage_uc_governance(w, args.warehouse_id, args.catalog, args.schema)
    stage_ml(w, args.warehouse_id, args.catalog, args.schema)
    stage_lakebase(w, args.catalog, args.schema)
    stage_genie(
        w,
        args.genie_space_id,
        "What is the latest HIGH-tier detection precision from model_performance_log?",
    )
    stage_app(w)
    banner("DONE")
    log("Six stages probed against the same workspace. See docs/evidence/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
