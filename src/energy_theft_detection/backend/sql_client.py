"""Stateless SQL Warehouse client using Databricks SDK Statement Execution API.

All data access flows through this module. No ORM, no connection pool — each
query executes a statement against the SQL Warehouse and returns rows as dicts.
"""

import os
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

from .config import AppConfig
from .logger import logger


class SQLClient:
    def __init__(self, config: AppConfig):
        self._config = config
        if os.environ.get("DATABRICKS_HOST"):
            self._client = WorkspaceClient()
        else:
            self._client = WorkspaceClient(profile=config.databricks_config_profile)
        self._warehouse_id = config.sql_warehouse_id
        self._schema = config.schema_name
        self._configured_catalog = config.catalog

        self._catalog = self._resolve_catalog(config.catalog)
        logger.info(f"SQLClient catalog resolved to: {self._catalog}")

    def _resolve_catalog(self, configured_catalog: str) -> str:
        """Verify the configured catalog exists; auto-detect from warehouse if not."""
        if configured_catalog:
            try:
                resp = self._client.statement_execution.execute_statement(
                    warehouse_id=self._warehouse_id,
                    statement=f"USE CATALOG `{configured_catalog}`",
                    wait_timeout="10s",
                )
                use_failed = resp.status and resp.status.state == StatementState.FAILED
                if not use_failed:
                    return configured_catalog
            except Exception as e:
                logger.warning(f"USE CATALOG failed for '{configured_catalog}': {e}")
            logger.warning(
                f"Configured catalog '{configured_catalog}' is not accessible, "
                "auto-detecting from warehouse"
            )

        try:
            resp = self._client.statement_execution.execute_statement(
                warehouse_id=self._warehouse_id,
                statement="SELECT current_catalog() AS cat",
                wait_timeout="10s",
            )
            if resp.manifest and resp.result and resp.result.data_array:
                cols = [c.name for c in resp.manifest.schema.columns]
                row = dict(zip(cols, resp.result.data_array[0]))
                detected = row.get("cat", "")
                if detected:
                    logger.info(f"Auto-detected catalog: {detected}")
                    return detected
        except Exception as e:
            logger.warning(f"Catalog auto-detection failed: {e}")

        return configured_catalog

    def resolve_catalog(self) -> str:
        """Return the resolved catalog name."""
        return self._catalog

    def _execute_raw(self, sql: str):
        """Run a statement and return the raw SDK response object."""
        logger.info(f"Executing SQL: {sql[:120]}...")
        response = self._client.statement_execution.execute_statement(
            warehouse_id=self._warehouse_id,
            catalog=self._catalog,
            schema=self._schema,
            statement=sql,
            wait_timeout="30s",
        )
        if response.status and response.status.state == StatementState.FAILED:
            error_msg = response.status.error.message if response.status.error else "Unknown error"
            raise RuntimeError(f"SQL execution failed: {error_msg}")
        return response

    def execute(self, sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL statement and return results as a list of dicts."""
        response = self._execute_raw(sql)

        if not response.manifest or not response.result:
            return []

        columns = [col.name for col in response.manifest.schema.columns]  # type: ignore[union-attr]
        rows: list[dict[str, Any]] = []

        if response.result.data_array:
            for row_data in response.result.data_array:
                rows.append(dict(zip(columns, row_data)))

        return rows

    def get_columns(self, table: str) -> list[str]:
        """Return column names for a table using manifest metadata."""
        response = self._execute_raw(f"SELECT * FROM {table} LIMIT 0")
        if not response.manifest or not response.manifest.schema or not response.manifest.schema.columns:
            return []
        return [col.name for col in response.manifest.schema.columns]

    @property
    def fqn(self) -> str:
        """Fully-qualified schema name for table references."""
        return f"{self._catalog}.{self._schema}"
