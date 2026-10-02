#!/usr/bin/env python3
"""Provision the Lakebase operational-serving layer for Energy Theft Detection.

This is the operational-serving stage of the end-to-end journey:

    Lakeflow (ingest) -> Unity Catalog (govern) -> ML/GenAI (score)
        -> Lakebase (serve + transact) -> Genie (ask) -> App (surface)

Why Lakebase here
-----------------
The medallion pipeline + ML scoring produce the gold table ``anomaly_scores`` in
Delta. That is the right home for *analytics* and *ML*, but it is the wrong home
for the investigator app's hot path:

  * The flagged-account queue is read on every page load. Serving it from a SQL
    Warehouse pays a cold-start / query-planning tax (the repo already carries a
    "cold-path latency" optimization pass to work around exactly this).
  * Case state (status, assignment, outcome, recovered amount) is *transactional*.
    Investigators open, re-assign and close cases interactively. Row-level updates
    at interactive latency are an OLTP workload, not a Delta MERGE workload.

So this script stands up a Lakebase (managed Postgres) instance that:

  1. Hosts a **synced table** ``anomaly_scores_serving`` kept in sync from the
     Delta gold table (Delta -> Postgres), giving the app a sub-second,
     always-warm read path for the risk queue.
  2. Hosts a native-Postgres **OLTP case-management schema**
     (``revenue_protection.investigation_cases`` + an append-only
     ``case_events`` audit log, with a trigger that records every state
     transition) that the app writes to with millisecond, read-your-writes
     commits.

The script is idempotent: re-running it reuses an existing instance / synced
table and re-applies the OLTP DDL with ``IF NOT EXISTS`` guards. Every step
prints a result line so the run log is committable as execution evidence
(``docs/evidence/lakebase_provision_run.txt``).

Usage
-----
    uv run python3 scripts/provision_lakebase.py \
        --profile zoccali-fevm-aws \
        --catalog zoccali_fevm \
        --warehouse-id 85c1b174d196486d

Add ``--teardown`` to delete the synced table + instance (demo cleanup).

Grant the Databricks App service principal (required for the deployed app;
provisioning connects as the user, so the SP role has no table privileges
until this runs):

    uv run python3 scripts/provision_lakebase.py \
        --profile zoccali-fevm-aws \
        --skip-synced-table \
        --grant-principal energy-theft-detection

``--grant-principal`` accepts an app name, SP display name, or application id.
Combined with ``--skip-synced-table`` it is a grant-only fast path (no Delta
rebuild, no demo transaction).
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# Defaults (aws field-demo target; override on the CLI)
# --------------------------------------------------------------------------- #
DEFAULT_PROFILE = "zoccali-fevm-aws"
DEFAULT_CATALOG = "zoccali_fevm"
DEFAULT_SCHEMA = "energy_theft_protection"
DEFAULT_WAREHOUSE_ID = "85c1b174d196486d"
INSTANCE_NAME = "energy-theft-lakebase"
INSTANCE_CAPACITY = "CU_1"  # smallest Lakebase SKU; plenty for a demo queue
LOGICAL_DB = "databricks_postgres"  # default logical database on a Lakebase instance
PG_SCHEMA = "revenue_protection"
SERVING_SOURCE_TABLE = "anomaly_scores_serving_src"  # deduped Delta source for the sync
SERVING_SYNCED_TABLE = "anomaly_scores_serving"  # synced table (UC name) -> Postgres


def log(msg: str) -> None:
    """Timestamped, ASCII-only log line (committable as evidence)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def banner(title: str) -> None:
    print("\n" + "=" * 72, flush=True)
    print(title, flush=True)
    print("=" * 72, flush=True)


# --------------------------------------------------------------------------- #
# SQL Warehouse helpers (Delta side)
# --------------------------------------------------------------------------- #
def run_sql(w, warehouse_id: str, catalog: str, schema: str, statement: str):
    """Execute a statement on the SQL Warehouse and return result rows (list of dict)."""
    from databricks.sdk.service.sql import StatementState

    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        catalog=catalog,
        schema=schema,
        statement=statement,
        wait_timeout="50s",
    )
    # Poll until terminal if not already finished.
    while resp.status and resp.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)

    if resp.status and resp.status.state != StatementState.SUCCEEDED:
        err = resp.status.error.message if resp.status and resp.status.error else "unknown"
        raise RuntimeError(f"SQL failed ({resp.status.state}): {err}\n  statement: {statement[:200]}")

    rows = []
    if resp.result and resp.result.data_array:
        cols = [c.name for c in resp.manifest.schema.columns]
        for r in resp.result.data_array:
            rows.append(dict(zip(cols, r)))
    return rows


def build_serving_source(w, warehouse_id: str, catalog: str, schema: str) -> int:
    """Create a deduped Delta table to act as the clean sync source.

    anomaly_scores can carry multiple rows per account (one per fuel type, and
    historically one per scoring batch). A synced table needs a stable, unique
    primary key, so we materialise the latest score per (account_id, fuel_type)
    with a deterministic ``serving_key`` and only the HIGH/MEDIUM queue the app
    actually serves. Change Data Feed is enabled so the sync can run TRIGGERED
    (snapshot) refreshes efficiently after each scoring batch.
    """
    fqtn = f"{catalog}.{schema}.{SERVING_SOURCE_TABLE}"
    ctas = f"""
        CREATE OR REPLACE TABLE {fqtn}
        TBLPROPERTIES (delta.enableChangeDataFeed = true) AS
        WITH ranked AS (
          SELECT
            *,
            ROW_NUMBER() OVER (
              PARTITION BY account_id, fuel_type
              ORDER BY score_timestamp DESC
            ) AS rn
          FROM {catalog}.{schema}.anomaly_scores
          WHERE risk_tier IN ('HIGH', 'MEDIUM')
        )
        SELECT
          concat(account_id, '|', fuel_type)        AS serving_key,
          account_id,
          fuel_type,
          composite_risk_score,
          risk_tier,
          isolation_forest_score,
          lstm_deviation_score,
          cohort_deviation_score,
          comms_gap_count_30d,
          consumption_drop_pct,
          postcode_sector,
          model_version,
          investigation_status,
          score_timestamp
        FROM ranked
        WHERE rn = 1
    """
    run_sql(w, warehouse_id, catalog, schema, ctas)
    rows = run_sql(w, warehouse_id, catalog, schema, f"SELECT COUNT(*) AS n FROM {fqtn}")
    n = int(rows[0]["n"]) if rows else 0
    log(f"Serving source table {fqtn} built: {n} rows (HIGH/MEDIUM queue, deduped)")
    return n


# --------------------------------------------------------------------------- #
# Lakebase instance + synced table
# --------------------------------------------------------------------------- #
def ensure_instance(w):
    from databricks.sdk.service.database import DatabaseInstance

    try:
        inst = w.database.get_database_instance(name=INSTANCE_NAME)
        log(f"Lakebase instance '{INSTANCE_NAME}' already exists (state={inst.state}, "
            f"capacity={inst.effective_capacity})")
        return inst
    except Exception:
        log(f"Creating Lakebase instance '{INSTANCE_NAME}' (capacity={INSTANCE_CAPACITY}) ...")

    waiter = w.database.create_database_instance(
        DatabaseInstance(name=INSTANCE_NAME, capacity=INSTANCE_CAPACITY)
    )
    inst = waiter.result(timeout=__import__("datetime").timedelta(minutes=15))
    log(f"Lakebase instance '{INSTANCE_NAME}' is {inst.state}; "
        f"read-write DNS = {inst.read_write_dns}")
    return inst


def ensure_synced_table(w, catalog: str, schema: str):
    from databricks.sdk.service.database import (
        SyncedDatabaseTable,
        SyncedTableSchedulingPolicy,
        SyncedTableSpec,
    )

    name = f"{catalog}.{schema}.{SERVING_SYNCED_TABLE}"
    source = f"{catalog}.{schema}.{SERVING_SOURCE_TABLE}"
    try:
        st = w.database.get_synced_database_table(name=name)
        log(f"Synced table '{name}' already exists "
            f"(state={st.unity_catalog_provisioning_state})")
        return st
    except Exception:
        log(f"Creating synced table '{name}' from '{source}' (Delta -> Postgres) ...")

    spec = SyncedTableSpec(
        source_table_full_name=source,
        primary_key_columns=["serving_key"],
        # Triggered snapshot after each scoring batch (CDF enabled on the source
        # so we can switch to CONTINUOUS later without a reload).
        scheduling_policy=SyncedTableSchedulingPolicy.SNAPSHOT,
        create_database_objects_if_missing=True,
    )
    st = w.database.create_synced_database_table(
        SyncedDatabaseTable(
            name=name,
            database_instance_name=INSTANCE_NAME,
            logical_database_name=LOGICAL_DB,
            spec=spec,
        )
    )
    log(f"Synced table '{name}' created; UC provisioning state = "
        f"{st.unity_catalog_provisioning_state}")
    wait_for_sync(w, name)
    return st


def wait_for_sync(w, name: str, timeout_s: int = 600) -> None:
    """Poll until the synced table's initial snapshot is ONLINE (or fails)."""
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        st = w.database.get_synced_database_table(name=name)
        status = st.data_synchronization_status
        state = getattr(status, "detailed_state", None)
        state_name = state.value if state is not None else "UNKNOWN"
        if state_name != last:
            log(f"  sync state: {state_name}")
            last = state_name
        if state_name.startswith("SYNCED_TABLE_ONLINE"):
            log("  initial snapshot complete; synced table is ONLINE")
            return
        if "FAILED" in state_name:
            log(f"  sync FAILED: {state_name}")
            return
        time.sleep(10)
    log(f"  sync not ONLINE within {timeout_s}s (continuing; check later)")


# --------------------------------------------------------------------------- #
# Postgres (OLTP) side
# --------------------------------------------------------------------------- #
def pg_connect(w, host: str, user: str):
    """Open a psycopg connection to Lakebase using a short-lived OAuth credential."""
    import psycopg

    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()), instance_names=[INSTANCE_NAME]
    )
    conn = psycopg.connect(
        host=host,
        port=5432,
        dbname=LOGICAL_DB,
        user=user,
        password=cred.token,
        sslmode="require",
        autocommit=True,
    )
    log(f"Connected to Lakebase Postgres at {host}:5432/{LOGICAL_DB} as {user}")
    return conn


OLTP_DDL = f"""
CREATE SCHEMA IF NOT EXISTS {PG_SCHEMA};

-- Transactional case state. Written by the investigator app at interactive
-- latency. This is the operational-serving system of record for case lifecycle.
CREATE TABLE IF NOT EXISTS {PG_SCHEMA}.investigation_cases (
    case_id                TEXT PRIMARY KEY DEFAULT ('CASE-' || to_char(now(), 'YYYYMMDDHH24MISSMS') || '-' || substr(md5(random()::text), 1, 6)),
    account_id             TEXT NOT NULL,
    fuel_type              TEXT,
    status                 TEXT NOT NULL DEFAULT 'OPEN'
                             CHECK (status IN ('OPEN','IN_PROGRESS','CLOSED','CONFIRMED_THEFT')),
    priority               TEXT DEFAULT 'MEDIUM' CHECK (priority IN ('LOW','MEDIUM','HIGH')),
    assigned_to            TEXT,
    outcome                TEXT CHECK (outcome IN ('THEFT_CONFIRMED','FALSE_POSITIVE','INCONCLUSIVE','PENDING')),
    revenue_recovered_gbp  NUMERIC(12,2),
    notes                  TEXT,
    opened_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at              TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_cases_account ON {PG_SCHEMA}.investigation_cases (account_id);
CREATE INDEX IF NOT EXISTS idx_cases_status  ON {PG_SCHEMA}.investigation_cases (status);

-- Append-only audit log of every state transition. Feeds the governance page
-- and the reverse-sync back into Delta for analytics / Genie.
CREATE TABLE IF NOT EXISTS {PG_SCHEMA}.case_events (
    event_id    BIGSERIAL PRIMARY KEY,
    case_id     TEXT NOT NULL,
    account_id  TEXT,
    event_type  TEXT NOT NULL,
    actor       TEXT,
    from_status TEXT,
    to_status   TEXT,
    detail      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_case ON {PG_SCHEMA}.case_events (case_id);

-- Trigger: on any case insert/update, stamp updated_at and append an audit
-- event. This is the kind of row-level, transactional logic that belongs in
-- Postgres, not in a Delta MERGE.
CREATE OR REPLACE FUNCTION {PG_SCHEMA}.log_case_event() RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO {PG_SCHEMA}.case_events (case_id, account_id, event_type, actor, from_status, to_status, detail)
        VALUES (NEW.case_id, NEW.account_id, 'CASE_OPENED', NEW.assigned_to, NULL, NEW.status,
                jsonb_build_object('priority', NEW.priority));
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        NEW.updated_at := now();
        IF (NEW.status IS DISTINCT FROM OLD.status) THEN
            INSERT INTO {PG_SCHEMA}.case_events (case_id, account_id, event_type, actor, from_status, to_status, detail)
            VALUES (NEW.case_id, NEW.account_id, 'STATUS_CHANGE', NEW.assigned_to, OLD.status, NEW.status,
                    jsonb_build_object('outcome', NEW.outcome, 'recovered_gbp', NEW.revenue_recovered_gbp));
        END IF;
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_log_case_event ON {PG_SCHEMA}.investigation_cases;
CREATE TRIGGER trg_log_case_event
    BEFORE INSERT OR UPDATE ON {PG_SCHEMA}.investigation_cases
    FOR EACH ROW EXECUTE FUNCTION {PG_SCHEMA}.log_case_event();
"""


def apply_oltp_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(OLTP_DDL)
    log(f"OLTP schema '{PG_SCHEMA}' applied (investigation_cases, case_events, trigger)")


def demo_transaction(conn) -> None:
    """Run a real open -> assign -> close transaction and show the audit trail.

    This proves the OLTP path end to end and gives committable evidence that
    the trigger fires and read-your-writes works.
    """
    acct = f"DEMO-ACCT-{uuid.uuid4().hex[:8].upper()}"
    with conn.cursor() as cur:
        # OPEN
        cur.execute(
            f"""INSERT INTO {PG_SCHEMA}.investigation_cases
                (account_id, fuel_type, priority, assigned_to, status)
                VALUES (%s, 'gas', 'HIGH', 'robbie.henderson', 'IN_PROGRESS')
                RETURNING case_id, status, opened_at""",
            (acct,),
        )
        case_id, status, opened_at = cur.fetchone()
        log(f"  OPEN  case {case_id} for {acct}: status={status} opened_at={opened_at}")

        # CLOSE as confirmed theft
        cur.execute(
            f"""UPDATE {PG_SCHEMA}.investigation_cases
                SET status='CONFIRMED_THEFT', outcome='THEFT_CONFIRMED',
                    revenue_recovered_gbp=4820.00, closed_at=now(),
                    notes='Bypass detected at field visit'
                WHERE case_id=%s
                RETURNING status, outcome, revenue_recovered_gbp, updated_at""",
            (case_id,),
        )
        status, outcome, recovered, updated_at = cur.fetchone()
        log(f"  CLOSE case {case_id}: status={status} outcome={outcome} "
            f"recovered=GBP{recovered} updated_at={updated_at}")

        # Show the audit trail the trigger produced
        cur.execute(
            f"""SELECT event_type, from_status, to_status, created_at
                FROM {PG_SCHEMA}.case_events
                WHERE case_id=%s ORDER BY event_id""",
            (case_id,),
        )
        for ev in cur.fetchall():
            log(f"    audit: {ev[0]:14s} {str(ev[1]):16s} -> {str(ev[2]):16s} @ {ev[3]}")


def grant_sql_statements(role_name: str, serving_schema: str) -> list[str]:
    """Postgres GRANTs the deployed app SP needs on serving + OLTP schemas.

    Role names are application ids (UUIDs with hyphens) so they must be quoted
    as identifiers. ``serving_schema`` mirrors the UC schema name, not public.
    """
    r = role_name.replace('"', '""')
    s = serving_schema.replace('"', '""')
    return [
        f'GRANT USAGE ON SCHEMA "{s}" TO "{r}"',
        f'GRANT SELECT ON "{s}".{SERVING_SYNCED_TABLE} TO "{r}"',
        f'GRANT USAGE ON SCHEMA {PG_SCHEMA} TO "{r}"',
        f'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {PG_SCHEMA} TO "{r}"',
        f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {PG_SCHEMA} TO "{r}"',
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {PG_SCHEMA} '
        f'GRANT SELECT, INSERT, UPDATE ON TABLES TO "{r}"',
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {PG_SCHEMA} '
        f'GRANT USAGE, SELECT ON SEQUENCES TO "{r}"',
    ]


def resolve_sp(w, principal: str) -> tuple[str, str]:
    """Resolve app name / display name / id to (application_id, display_name)."""
    principal = principal.strip()
    if not principal:
        raise RuntimeError("--grant-principal requires an app name, SP display name, or application id")

    try:
        app = w.apps.get(principal)
        sp_id = app.service_principal_client_id or ""
        if sp_id:
            try:
                sp = w.service_principals.get(sp_id)
                app_id = sp.application_id or sp_id
                display = sp.display_name or principal
                log(f"Resolved app '{principal}' -> SP {display} (application_id={app_id})")
                return app_id, display
            except Exception as e:  # noqa: BLE001
                log(f"SP lookup by client id {sp_id} failed ({e}); using client id as role")
                return sp_id, principal
    except Exception:
        pass

    for sp in w.service_principals.list():
        app_id = sp.application_id or ""
        sp_id = sp.id or ""
        display = sp.display_name or ""
        if principal in {app_id, sp_id, display}:
            log(f"Resolved principal '{principal}' -> SP {display} (application_id={app_id or sp_id})")
            return app_id or sp_id, display or principal

    raise RuntimeError(
        f"Could not resolve principal '{principal}' to a service principal "
        "(tried apps.get and service_principals.list)"
    )


def ensure_pg_role(conn, application_id: str) -> str:
    """Return the Postgres role for the SP, creating it via databricks_create_role if needed."""
    with conn.cursor() as cur:
        cur.execute("SELECT rolname FROM pg_roles WHERE rolname = %s", (application_id,))
        row = cur.fetchone()
        if row:
            log(f"Postgres role already exists: {row[0]}")
            return row[0]
        try:
            cur.execute(
                "SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')",
                (application_id,),
            )
            created = cur.fetchone()
            log(f"databricks_create_role({application_id!r}, 'SERVICE_PRINCIPAL') -> {created}")
        except Exception as e:  # noqa: BLE001
            log(f"databricks_create_role skipped or failed: {e}")
        cur.execute("SELECT rolname FROM pg_roles WHERE rolname = %s", (application_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "SELECT rolname FROM pg_roles WHERE rolname ILIKE %s ORDER BY rolname",
            (f"%{application_id}%",),
        )
        matches = [r[0] for r in cur.fetchall()]
        if len(matches) == 1:
            log(f"Matched Postgres role by ILIKE: {matches[0]}")
            return matches[0]
        if matches:
            log(f"Multiple pg_roles matched {application_id}: {matches}")
        raise RuntimeError(
            f"Postgres role for '{application_id}' not found. Connect with psql and \\du "
            "to inspect roles, then re-run with --grant-principal <rolname>."
        )


def grant_principal(w, conn, principal: str, serving_schema: str) -> str:
    """Create (if needed) and GRANT serving + OLTP privileges to the app SP role."""
    application_id, display = resolve_sp(w, principal)
    role = ensure_pg_role(conn, application_id)
    stmts = grant_sql_statements(role, serving_schema)
    with conn.cursor() as cur:
        for stmt in stmts:
            cur.execute(stmt)
            log(f"  {stmt}")
    log(f"Granted serving+OLTP privileges to Postgres role '{role}' ({display})")
    return role


def verify(conn, serving_schema: str) -> None:
    """Print row counts for the synced table + OLTP tables as evidence.

    The synced table lands in a Postgres schema that mirrors the UC schema name
    (e.g. ``energy_theft_protection``), not ``public``.
    """
    serving_fqtn = f"{serving_schema}.{SERVING_SYNCED_TABLE}"
    with conn.cursor() as cur:
        # Synced table (read path). Tolerate a still-provisioning sync so the
        # OLTP evidence below always lands.
        try:
            cur.execute(f"SELECT COUNT(*) FROM {serving_fqtn}")
            synced = cur.fetchone()[0]
            log(f"  synced queue rows ({serving_fqtn}): {synced}")
            cur.execute(
                f"SELECT risk_tier, COUNT(*) FROM {serving_fqtn} "
                "GROUP BY risk_tier ORDER BY 1"
            )
            for tier, n in cur.fetchall():
                log(f"    {tier}: {n}")
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log(f"  synced table not queryable yet (sync may be in progress): {e}")

        # OLTP tables (write path) — always available.
        cur.execute(f"SELECT COUNT(*) FROM {PG_SCHEMA}.investigation_cases")
        cases = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {PG_SCHEMA}.case_events")
        events = cur.fetchone()[0]
        log(f"  OLTP cases: {cases}, audit events: {events}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=DEFAULT_PROFILE)
    ap.add_argument("--catalog", default=DEFAULT_CATALOG)
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--warehouse-id", default=DEFAULT_WAREHOUSE_ID)
    ap.add_argument("--skip-synced-table", action="store_true",
                    help="Only (re)apply the OLTP schema; skip instance/synced-table provisioning")
    ap.add_argument(
        "--grant-principal",
        metavar="SP",
        default=None,
        help="App name, SP display name, or application id to GRANT serving+OLTP privileges",
    )
    ap.add_argument("--teardown", action="store_true", help="Delete synced table + instance and exit")
    args = ap.parse_args()

    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient(profile=args.profile)
    me = w.current_user.me()
    user = me.user_name
    log(f"Authenticated as {user} on profile '{args.profile}'")

    if args.teardown:
        banner("TEARDOWN")
        name = f"{args.catalog}.{args.schema}.{SERVING_SYNCED_TABLE}"
        try:
            w.database.delete_synced_database_table(name=name)
            log(f"Deleted synced table {name}")
        except Exception as e:
            log(f"Synced table delete skipped: {e}")
        try:
            w.database.delete_database_instance(name=INSTANCE_NAME, purge=True)
            log(f"Deleted instance {INSTANCE_NAME}")
        except Exception as e:
            log(f"Instance delete skipped: {e}")
        return 0

    # Grant-only fast path: --grant-principal + --skip-synced-table skips the
    # Delta rebuild and demo transaction (infra is already live).
    if args.grant_principal and args.skip_synced_table:
        banner("GRANT Postgres privileges to app service principal")
        inst = w.database.get_database_instance(name=INSTANCE_NAME)
        host = inst.read_write_dns
        conn = pg_connect(w, host, user)
        grant_principal(w, conn, args.grant_principal, args.schema)
        conn.close()
        banner("DONE")
        log(f"Granted '{args.grant_principal}' on {INSTANCE_NAME}/{LOGICAL_DB}")
        return 0

    banner("STAGE 1: Delta serving source (dedup HIGH/MEDIUM queue)")
    build_serving_source(w, args.warehouse_id, args.catalog, args.schema)

    inst = None
    if not args.skip_synced_table:
        banner("STAGE 2: Lakebase instance")
        inst = ensure_instance(w)

        banner("STAGE 3: Synced table (Delta -> Postgres)")
        ensure_synced_table(w, args.catalog, args.schema)
    else:
        inst = w.database.get_database_instance(name=INSTANCE_NAME)

    banner("STAGE 4: OLTP case-management schema (native Postgres)")
    host = inst.read_write_dns
    conn = pg_connect(w, host, user)
    apply_oltp_schema(conn)

    banner("STAGE 5: Demo transaction (open -> close -> audit trail)")
    demo_transaction(conn)

    banner("STAGE 6: Verification")
    verify(conn, args.schema)

    if args.grant_principal:
        banner("STAGE 7: GRANT Postgres privileges to app service principal")
        grant_principal(w, conn, args.grant_principal, args.schema)

    conn.close()
    banner("DONE")
    log("Lakebase operational-serving layer provisioned and verified.")
    log(f"  instance        : {INSTANCE_NAME} ({host})")
    log(f"  synced table    : {args.catalog}.{args.schema}.{SERVING_SYNCED_TABLE}")
    log(f"  oltp schema     : {LOGICAL_DB}.{PG_SCHEMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
