"""Tests for scripts/verify_app_permissions.py.

Unit-tests the permission checking logic without hitting a real workspace.
"""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from scripts.verify_app_permissions import (
    check_warehouse_permission,
    check_schema_grants,
)


# ---------------------------------------------------------------------------
# Warehouse permission checks
# ---------------------------------------------------------------------------


class TestCheckWarehousePermission:
    """Verify CAN_USE detection on the SQL Warehouse ACL."""

    def _make_acl(self, sp_name: str, level: str):
        acl = MagicMock()
        acl.service_principal_name = sp_name
        perm = MagicMock()
        perm.permission_level.value = level
        acl.all_permissions = [perm]
        return acl

    def test_returns_true_when_sp_has_can_use(self):
        w = MagicMock()
        w.permissions.get.return_value.access_control_list = [
            self._make_acl("sp-123", "CAN_USE"),
        ]
        assert check_warehouse_permission(w, "sp-123", "wh-abc") is True

    def test_returns_true_when_sp_has_can_manage(self):
        w = MagicMock()
        w.permissions.get.return_value.access_control_list = [
            self._make_acl("sp-123", "CAN_MANAGE"),
        ]
        assert check_warehouse_permission(w, "sp-123", "wh-abc") is True

    def test_returns_false_when_sp_missing(self):
        w = MagicMock()
        w.permissions.get.return_value.access_control_list = [
            self._make_acl("other-sp", "CAN_USE"),
        ]
        assert check_warehouse_permission(w, "sp-123", "wh-abc") is False

    def test_returns_false_when_acl_empty(self):
        w = MagicMock()
        w.permissions.get.return_value.access_control_list = []
        assert check_warehouse_permission(w, "sp-123", "wh-abc") is False


# ---------------------------------------------------------------------------
# Schema grant checks
# ---------------------------------------------------------------------------


class TestCheckSchemaGrants:
    """Verify UC grant detection from SHOW GRANTS output."""

    CATALOG = "dz_demos"
    SCHEMA_FQN = "dz_demos.energy_theft_protection"

    def _mock_ws(self, catalog_rows, schema_rows):
        """Create a mock WorkspaceClient that returns the given SHOW GRANTS rows."""
        w = MagicMock()

        def execute_side_effect(statement="", **kwargs):
            resp = MagicMock()
            if "CATALOG" in statement:
                resp.result.data_array = catalog_rows
            else:
                resp.result.data_array = schema_rows
            return resp

        w.statement_execution.execute_statement.side_effect = execute_side_effect
        check_schema_grants._wh_id = "wh-test"
        return w

    def test_all_grants_present(self):
        w = self._mock_ws(
            catalog_rows=[["sp-123", "USE CATALOG", "CATALOG", "dz_demos"]],
            schema_rows=[
                ["sp-123", "USE SCHEMA", "SCHEMA", "dz_demos.energy_theft_protection"],
                ["sp-123", "SELECT", "SCHEMA", "dz_demos.energy_theft_protection"],
            ],
        )
        result = check_schema_grants(w, "sp-123", self.CATALOG, self.SCHEMA_FQN)
        assert result == {"USE CATALOG": True, "USE SCHEMA": True, "SELECT": True}

    def test_missing_use_catalog(self):
        w = self._mock_ws(
            catalog_rows=[],
            schema_rows=[
                ["sp-123", "USE SCHEMA", "SCHEMA", "dz_demos.energy_theft_protection"],
                ["sp-123", "SELECT", "SCHEMA", "dz_demos.energy_theft_protection"],
            ],
        )
        result = check_schema_grants(w, "sp-123", self.CATALOG, self.SCHEMA_FQN)
        assert result["USE CATALOG"] is False
        assert result["USE SCHEMA"] is True
        assert result["SELECT"] is True

    def test_missing_select(self):
        w = self._mock_ws(
            catalog_rows=[["sp-123", "USE CATALOG", "CATALOG", "dz_demos"]],
            schema_rows=[
                ["sp-123", "USE SCHEMA", "SCHEMA", "dz_demos.energy_theft_protection"],
            ],
        )
        result = check_schema_grants(w, "sp-123", self.CATALOG, self.SCHEMA_FQN)
        assert result["SELECT"] is False

    def test_wrong_sp_ignored(self):
        w = self._mock_ws(
            catalog_rows=[["other-sp", "USE CATALOG", "CATALOG", "dz_demos"]],
            schema_rows=[
                ["other-sp", "USE SCHEMA", "SCHEMA", "dz_demos.energy_theft_protection"],
                ["other-sp", "SELECT", "SCHEMA", "dz_demos.energy_theft_protection"],
            ],
        )
        result = check_schema_grants(w, "sp-123", self.CATALOG, self.SCHEMA_FQN)
        assert all(v is False for v in result.values())

    def test_handles_underscore_format(self):
        """SHOW GRANTS may return USE_CATALOG (underscore) instead of USE CATALOG (space)."""
        w = self._mock_ws(
            catalog_rows=[["sp-123", "USE_CATALOG", "CATALOG", "dz_demos"]],
            schema_rows=[
                ["sp-123", "USE_SCHEMA", "SCHEMA", "dz_demos.energy_theft_protection"],
                ["sp-123", "SELECT", "SCHEMA", "dz_demos.energy_theft_protection"],
            ],
        )
        result = check_schema_grants(w, "sp-123", self.CATALOG, self.SCHEMA_FQN)
        assert result == {"USE CATALOG": True, "USE SCHEMA": True, "SELECT": True}


# ---------------------------------------------------------------------------
# Error message classification in _check_schema_access
# ---------------------------------------------------------------------------


class TestErrorClassification:
    """_check_schema_access produces actionable error messages."""

    def _make_db(self, side_effect):
        db = MagicMock()
        db.resolve_catalog.return_value = "cat"
        db._schema = "sch"
        db._client.config.client_id = "sp-id"
        db.execute.side_effect = side_effect
        return db

    def test_warehouse_error_mentions_can_use_and_script(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db(RuntimeError("You do not have permission to use the SQL Warehouse. Please contact your administrator."))
        ok, err = _check_schema_access(db, retries=1, backoff=0)
        assert ok is False
        assert "Warehouse access denied" in err
        assert "CAN_USE" in err
        assert "verify_app_permissions" in err

    def test_schema_error_mentions_grant_and_script(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db(RuntimeError("PERMISSION_DENIED: Insufficient privileges"))
        ok, err = _check_schema_access(db, retries=1, backoff=0)
        assert ok is False
        assert "Schema access denied" in err
        assert "GRANT" in err
        assert "verify_app_permissions" in err

    def test_transient_error_mentions_auto_retry(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db(RuntimeError("Connection timed out"))
        ok, err = _check_schema_access(db, retries=1, backoff=0)
        assert ok is False
        assert "transient" in err.lower()
        assert "auto" in err.lower()
