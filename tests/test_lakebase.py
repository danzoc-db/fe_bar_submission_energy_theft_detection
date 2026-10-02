"""Acceptance tests — Lakebase operational-serving layer.

These run offline (no Databricks connectivity). They verify:

  * Lakebase is OFF by default and the app degrades gracefully to the Delta
    path (the /case endpoint reports source="delta" and the close endpoint
    still succeeds).
  * The config surface for Lakebase has safe defaults.
  * LakebaseClient.available() is False when the feature is disabled, without
    attempting any network/credential call.
"""

import importlib.util
from pathlib import Path

from energy_theft_detection.backend.config import AppConfig
from energy_theft_detection.backend.lakebase_client import LakebaseClient


def _provision_mod():
    path = Path(__file__).resolve().parents[1] / "scripts" / "provision_lakebase.py"
    spec = importlib.util.spec_from_file_location("provision_lakebase", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


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


class TestGrantPrincipalSql:
    def test_grants_quote_uuid_role_and_uc_serving_schema(self):
        mod = _provision_mod()
        role = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        stmts = mod.grant_sql_statements(role, "energy_theft_protection")
        joined = "\n".join(stmts)
        assert f'TO "{role}"' in joined
        assert "GRANT USAGE ON SCHEMA \"energy_theft_protection\"" in joined
        assert "GRANT SELECT ON \"energy_theft_protection\".anomaly_scores_serving" in joined
        assert "GRANT USAGE ON SCHEMA revenue_protection" in joined
        assert "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA revenue_protection" in joined
        assert "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA revenue_protection" in joined

    def test_cli_exposes_grant_principal(self):
        text = Path("scripts/provision_lakebase.py").read_text()
        assert "--grant-principal" in text

    def test_end_to_end_job_includes_lakebase_before_genie(self):
        yml = Path("databricks.yml").read_text()
        assert 'task_key: "provision_lakebase"' in yml
        assert "10_provision_lakebase.py" in yml
        genie_block = yml.split("task_key: \"configure_genie\"", 1)[1][:500]
        assert "provision_lakebase" in genie_block
