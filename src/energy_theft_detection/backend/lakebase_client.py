"""Lakebase (managed Postgres) client for the operational-serving layer.

This is the transactional / low-latency read path that complements the
analytical ``SQLClient`` (SQL Warehouse over Delta):

  * **Read** the flagged-account queue from the synced table
    ``public.anomaly_scores_serving`` (kept in sync from the Delta gold table),
    giving the investigator app a sub-second, always-warm read path.
  * **Write** case lifecycle state (open / assign / close) to
    ``revenue_protection.investigation_cases`` with millisecond,
    read-your-writes commits, and an append-only ``case_events`` audit log.

Auth model
----------
The client never stores a long-lived password. It calls
``WorkspaceClient.database.generate_database_credential`` to mint a short-lived
OAuth token (used as the Postgres password) and refreshes it before expiry.
Locally this uses the CLI profile; in a deployed Databricks App it uses the
app's service principal (the app must be granted access to the instance via a
``database`` app resource in ``databricks.yml``).

Everything is best-effort: if ``psycopg`` is unavailable, the instance can't be
reached, or Lakebase is disabled by config, every method returns ``None`` /
empty so callers transparently fall back to the Delta path. The app therefore
runs unchanged in offline mode.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any

from databricks.sdk import WorkspaceClient

from .config import AppConfig
from .logger import logger

# Credential lifetime is ~1h; refresh with headroom.
_CRED_TTL_SECONDS = 45 * 60


class LakebaseClient:
    """Thin, self-healing psycopg wrapper around a Lakebase instance."""

    def __init__(self, config: AppConfig, workspace: WorkspaceClient | None = None):
        self._config = config
        self._schema = config.lakebase_schema
        self._serving_table = config.lakebase_serving_table
        self._serving_schema = config.lakebase_serving_schema
        self._instance = config.lakebase_instance_name
        self._database = config.lakebase_database

        self._client = workspace or (
            WorkspaceClient()
            if os.environ.get("DATABRICKS_HOST")
            else WorkspaceClient(profile=config.databricks_config_profile)
        )

        self._lock = threading.Lock()
        self._cred_token: str | None = None
        self._cred_minted_at: float = 0.0
        self._host: str | None = None
        self._user: str | None = None
        self._available: bool | None = None  # lazy health check result

    # --------------------------------------------------------------------- #
    # Connection management
    # --------------------------------------------------------------------- #
    def _resolve_host_user(self) -> None:
        if self._host and self._user:
            return
        inst = self._client.database.get_database_instance(name=self._instance)
        self._host = inst.read_write_dns
        self._user = self._client.current_user.me().user_name

    def _token(self) -> str:
        """Return a valid OAuth credential, refreshing if near expiry."""
        now = time.time()
        cached = self._cred_token
        if cached and (now - self._cred_minted_at) < _CRED_TTL_SECONDS:
            return cached
        cred = self._client.database.generate_database_credential(
            request_id=str(uuid.uuid4()), instance_names=[self._instance]
        )
        token = cred.token or ""
        self._cred_token = token
        self._cred_minted_at = now
        return token

    def _connect(self):
        import psycopg  # imported lazily so the app runs without psycopg installed

        self._resolve_host_user()
        return psycopg.connect(
            host=self._host,
            port=5432,
            dbname=self._database,
            user=self._user,
            password=self._token(),
            sslmode="require",
            autocommit=True,
            connect_timeout=10,
        )

    def available(self) -> bool:
        """Lazy, cached health check. False => callers fall back to Delta."""
        if not self._config.lakebase_enabled:
            return False
        if self._available is not None:
            return self._available
        with self._lock:
            if self._available is not None:
                return self._available
            try:
                with self._connect() as conn, conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                self._available = True
                logger.info(f"Lakebase available: {self._instance} ({self._host})")
            except Exception as e:  # noqa: BLE001 - best-effort health check
                self._available = False
                logger.warning(f"Lakebase unavailable, falling back to Delta: {e}")
        return self._available

    def _rows(self, sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return []
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    # --------------------------------------------------------------------- #
    # Read path: flagged-account serving queue (synced from Delta)
    # --------------------------------------------------------------------- #
    def fetch_queue(self, limit: int = 100, risk_tier: str | None = None) -> list[dict[str, Any]] | None:
        if not self.available():
            return None
        try:
            where = ""
            params: tuple = ()
            if risk_tier:
                where = "WHERE risk_tier = %s"
                params = (risk_tier,)
            sql = f"""
                SELECT serving_key, account_id, fuel_type, composite_risk_score,
                       risk_tier, comms_gap_count_30d, consumption_drop_pct,
                       postcode_sector, model_version, investigation_status, score_timestamp
                FROM {self._serving_schema}.{self._serving_table}
                {where}
                ORDER BY composite_risk_score DESC
                LIMIT %s
            """
            return self._rows(sql, params + (limit,))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Lakebase fetch_queue failed: {e}")
            return None

    # --------------------------------------------------------------------- #
    # Write path: case lifecycle (OLTP)
    # --------------------------------------------------------------------- #
    def get_case(self, account_id: str) -> dict[str, Any] | None:
        if not self.available():
            return None
        try:
            rows = self._rows(
                f"""SELECT case_id, account_id, status, outcome, assigned_to,
                           revenue_recovered_gbp, opened_at, updated_at, closed_at
                    FROM {self._schema}.investigation_cases
                    WHERE account_id = %s
                    ORDER BY opened_at DESC LIMIT 1""",
                (account_id,),
            )
            return rows[0] if rows else None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Lakebase get_case failed: {e}")
            return None

    def close_case(
        self,
        account_id: str,
        *,
        outcome: str,
        status: str,
        recovered_gbp: float | None,
        notes: str | None,
        actor: str = "robbie.henderson",
    ) -> dict[str, Any] | None:
        """Close (or open-then-close) a case transactionally. Returns the row.

        This replaces the async Delta MERGE for the interactive close action:
        a single autocommit round-trip, read-your-writes, with the trigger
        appending a ``case_events`` audit record. Returns ``None`` when Lakebase
        is unavailable so the caller keeps the Delta path.
        """
        if not self.available():
            return None
        try:
            with self._connect() as conn, conn.cursor() as cur:
                # Update the most recent open case for this account, if any.
                cur.execute(
                    f"""UPDATE {self._schema}.investigation_cases
                        SET status=%s, outcome=%s, revenue_recovered_gbp=%s,
                            notes=%s, assigned_to=COALESCE(assigned_to, %s), closed_at=now()
                        WHERE case_id = (
                            SELECT case_id FROM {self._schema}.investigation_cases
                            WHERE account_id=%s AND status NOT IN ('CLOSED','CONFIRMED_THEFT')
                            ORDER BY opened_at DESC LIMIT 1
                        )
                        RETURNING case_id, status, outcome, revenue_recovered_gbp""",
                    (status, outcome, recovered_gbp, notes, actor, account_id),
                )
                row = cur.fetchone()
                if row is None:
                    # No open case: insert an already-closed one (keeps the audit trail honest).
                    cur.execute(
                        f"""INSERT INTO {self._schema}.investigation_cases
                            (account_id, status, outcome, revenue_recovered_gbp, notes, assigned_to, closed_at)
                            VALUES (%s, %s, %s, %s, %s, %s, now())
                            RETURNING case_id, status, outcome, revenue_recovered_gbp""",
                        (account_id, status, outcome, recovered_gbp, notes, actor),
                    )
                    row = cur.fetchone()
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Lakebase close_case failed: {e}")
            return None

    def list_events(self, account_id: str, limit: int = 20) -> list[dict[str, Any]] | None:
        if not self.available():
            return None
        try:
            return self._rows(
                f"""SELECT event_type, from_status, to_status, actor, created_at
                    FROM {self._schema}.case_events
                    WHERE account_id = %s
                    ORDER BY event_id DESC LIMIT %s""",
                (account_id, limit),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Lakebase list_events failed: {e}")
            return None
