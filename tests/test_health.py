"""Tests for health check, readiness, and schema access probe.

Without a SQL Warehouse connection (default test config), readiness should
report not-ready with a clear error message, and health should include
schema_access fields.
"""

from unittest.mock import MagicMock, patch


class TestHealthEndpoint:
    """Health check endpoint returns schema access status."""

    def test_health_returns_200(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_reports_schema_access_field(self, client):
        data = client.get("/api/health").json()
        assert "schema_access_ok" in data
        assert isinstance(data["schema_access_ok"], bool)

    def test_health_reports_schema_access_error_field(self, client):
        data = client.get("/api/health").json()
        assert "schema_access_error" in data

    def test_health_schema_access_false_without_warehouse(self, client):
        """Without a warehouse, schema access should be False."""
        data = client.get("/api/health").json()
        assert data["schema_access_ok"] is False


class TestReadinessEndpoint:
    """Readiness endpoint surfaces permission issues."""

    def test_readiness_returns_200(self, client):
        r = client.get("/api/readiness")
        assert r.status_code == 200

    def test_readiness_fields(self, client):
        data = client.get("/api/readiness").json()
        assert "ready" in data
        assert "error" in data
        assert isinstance(data["ready"], bool)
        assert data["error"] is None or isinstance(data["error"], str)

    def test_readiness_not_ready_without_warehouse(self, client):
        """Without SQL Warehouse, readiness should report not ready."""
        data = client.get("/api/readiness").json()
        assert data["ready"] is False
        assert data["error"] is not None
        assert len(data["error"]) > 0

    def test_readiness_error_mentions_warehouse(self, client):
        """Error message should explain the SQL Warehouse is not connected."""
        data = client.get("/api/readiness").json()
        assert "SQL Warehouse" in data["error"] or "GRANT" in data["error"]


class TestCheckSchemaAccess:
    """Unit tests for _check_schema_access retry & error classification."""

    def _make_db(self, side_effect=None):
        db = MagicMock()
        db.resolve_catalog.return_value = "test_catalog"
        db._schema = "test_schema"
        db._client.config.client_id = "test-sp-id"
        if side_effect:
            db.execute.side_effect = side_effect
        return db

    def test_success_on_first_try(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db()
        db.execute.return_value = [{"1": 1}]
        ok, err = _check_schema_access(db, retries=1, backoff=0)
        assert ok is True
        assert err == ""

    def test_schema_permission_error_no_retry(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db(side_effect=RuntimeError("PERMISSION_DENIED: User does not have SELECT"))
        ok, err = _check_schema_access(db, retries=3, backoff=0)
        assert ok is False
        assert "Schema access denied" in err
        assert "GRANT" in err
        assert db.execute.call_count == 1

    def test_warehouse_permission_error_no_retry(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db(side_effect=RuntimeError("You do not have permission to use the SQL Warehouse"))
        ok, err = _check_schema_access(db, retries=3, backoff=0)
        assert ok is False
        assert "Warehouse access denied" in err
        assert "CAN_USE" in err
        assert db.execute.call_count == 1

    def test_transient_error_retries(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db(side_effect=RuntimeError("Statement timed out after 30s"))
        ok, err = _check_schema_access(db, retries=3, backoff=0)
        assert ok is False
        assert "transient" in err.lower()
        assert "timed out" in err.lower()
        assert db.execute.call_count == 3

    def test_transient_then_success(self):
        from energy_theft_detection.backend.router import _check_schema_access
        db = self._make_db()
        db.execute.side_effect = [RuntimeError("timeout"), [{"1": 1}]]
        ok, err = _check_schema_access(db, retries=3, backoff=0)
        assert ok is True
        assert err == ""
        assert db.execute.call_count == 2


class TestTryWarmCache:
    """_try_warm_cache only re-warms when cache is incomplete."""

    @patch("energy_theft_detection.backend.router._warm_cache")
    @patch("energy_theft_detection.backend.router._cache_get")
    def test_rewarms_when_cache_empty(self, mock_cache_get, mock_warm):
        from energy_theft_detection.backend.router import _try_warm_cache
        mock_cache_get.return_value = None
        db = MagicMock()
        _try_warm_cache(db)
        mock_warm.assert_called_once_with(db)

    @patch("energy_theft_detection.backend.router._warm_cache")
    @patch("energy_theft_detection.backend.router._cache_get")
    def test_skips_when_cache_full(self, mock_cache_get, mock_warm):
        from energy_theft_detection.backend.router import _try_warm_cache
        mock_cache_get.return_value = "some-data"
        db = MagicMock()
        _try_warm_cache(db)
        mock_warm.assert_not_called()
