"""Acceptance tests — Lakebase operational-serving layer.

These run offline (no Databricks connectivity). They verify:

  * Lakebase is OFF by default and the app degrades gracefully to the Delta
    path (the /case endpoint reports source="delta" and the close endpoint
    still succeeds).
  * The config surface for Lakebase has safe defaults.
  * LakebaseClient.available() is False when the feature is disabled, without
    attempting any network/credential call.
"""

from energy_theft_detection.backend.config import AppConfig
from energy_theft_detection.backend.lakebase_client import LakebaseClient


class TestLakebaseConfigDefaults:
    def test_disabled_by_default(self):
        cfg = AppConfig()
        assert cfg.lakebase_enabled is False

    def test_default_names(self):
        cfg = AppConfig()
        assert cfg.lakebase_instance_name == "energy-theft-lakebase"
        assert cfg.lakebase_database == "databricks_postgres"
        assert cfg.lakebase_schema == "revenue_protection"
        assert cfg.lakebase_serving_table == "anomaly_scores_serving"


class TestLakebaseClientOffline:
    def test_available_false_when_disabled(self):
        """available() short-circuits to False with no network call when disabled."""
        cfg = AppConfig()  # lakebase_enabled defaults False
        # Pass a sentinel workspace to prove no SDK call is made when disabled.
        client = LakebaseClient(cfg, workspace=object())  # type: ignore[arg-type]
        assert client.available() is False

    def test_read_methods_return_none_when_disabled(self):
        cfg = AppConfig()
        client = LakebaseClient(cfg, workspace=object())  # type: ignore[arg-type]
        assert client.fetch_queue() is None
        assert client.get_case("UKI-0000001") is None
        assert client.list_events("UKI-0000001") is None
        assert client.close_case(
            "UKI-0000001", outcome="FALSE_POSITIVE", status="CLOSED",
            recovered_gbp=None, notes=None,
        ) is None


class TestInvestigationCaseEndpoint:
    def test_case_endpoint_reports_delta_when_disabled(self, client):
        """With Lakebase off, /case degrades to source=delta with no data."""
        r = client.get("/api/investigation/UKI-0000001/case")
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "delta"
        assert data["lakebase_enabled"] is False
        assert data["case"] is None
        assert data["events"] == []


class TestCloseStillWorksWithoutLakebase:
    def test_close_falls_back_to_delta_path(self, client):
        """Close endpoint still returns 200 in offline mode (regression guard)."""
        r = client.post(
            "/api/investigation/UKI-0000001/close",
            json={"outcome": "confirmed_theft", "recovered_amount": 1234.0},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["outcome"] == "THEFT_CONFIRMED"
        assert data["recovered_amount"] == 1234.0
