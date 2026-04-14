"""TC-WP: Workspace portability tests.

Validates that the app can be configured for different workspaces
via environment variables (CATALOG, SCHEMA_NAME, etc.) without code changes,
and that the workspace-config endpoint exposes dynamic values to the frontend.
"""

import os
import pathlib
import shutil
import tempfile

import pytest


# ---------------------------------------------------------------------------
# TC-WP1: Catalog & schema are configurable
# ---------------------------------------------------------------------------


class TestCatalogConfiguration:
    """TC-WP1: Catalog is configurable via CATALOG env var."""

    def test_default_catalog_is_empty(self):
        """MUST: Default catalog is empty when no env var is set."""
        saved = os.environ.pop("CATALOG", None)
        try:
            from energy_theft_detection.backend.config import AppConfig

            config = AppConfig(sql_warehouse_id="", _env_file=None)
            assert config.catalog == ""
        finally:
            if saved is not None:
                os.environ["CATALOG"] = saved

    def test_catalog_reads_from_env(self):
        """MUST: Catalog reads from CATALOG env var for workspace portability."""
        os.environ["CATALOG"] = "azsu_centrica_demo"
        try:
            from energy_theft_detection.backend.config import AppConfig

            config = AppConfig(sql_warehouse_id="", _env_file=None)
            assert config.catalog == "azsu_centrica_demo"
        finally:
            os.environ.pop("CATALOG", None)

    def test_schema_reads_from_env(self):
        """MUST: Schema reads from SCHEMA_NAME env var."""
        os.environ["SCHEMA_NAME"] = "custom_schema"
        try:
            from energy_theft_detection.backend.config import AppConfig

            config = AppConfig(sql_warehouse_id="", _env_file=None)
            assert config.schema_name == "custom_schema"
        finally:
            os.environ.pop("SCHEMA_NAME", None)

    def test_schema_default_is_energy_theft_protection(self):
        """MUST: Schema defaults to energy_theft_protection."""
        os.environ.pop("SCHEMA_NAME", None)
        from energy_theft_detection.backend.config import AppConfig

        config = AppConfig(sql_warehouse_id="", _env_file=None)
        assert config.schema_name == "energy_theft_protection"


# ---------------------------------------------------------------------------
# TC-WP2: workspace_url derivation
# ---------------------------------------------------------------------------


class TestWorkspaceUrl:
    """TC-WP2: workspace_url property reads from DATABRICKS_HOST."""

    def test_workspace_url_from_env(self):
        """MUST: workspace_url reads from DATABRICKS_HOST env var."""
        os.environ["DATABRICKS_HOST"] = "https://my-workspace.cloud.databricks.com"
        try:
            from energy_theft_detection.backend.config import AppConfig

            config = AppConfig(sql_warehouse_id="", _env_file=None)
            assert config.workspace_url == "https://my-workspace.cloud.databricks.com"
        finally:
            os.environ.pop("DATABRICKS_HOST", None)

    def test_workspace_url_strips_trailing_slash(self):
        """MUST: workspace_url strips trailing slash."""
        os.environ["DATABRICKS_HOST"] = "https://example.com/"
        try:
            from energy_theft_detection.backend.config import AppConfig

            config = AppConfig(sql_warehouse_id="", _env_file=None)
            assert config.workspace_url == "https://example.com"
        finally:
            os.environ.pop("DATABRICKS_HOST", None)

    def test_workspace_url_empty_when_not_set(self):
        """MUST: workspace_url is empty string when DATABRICKS_HOST is not set."""
        os.environ.pop("DATABRICKS_HOST", None)
        from energy_theft_detection.backend.config import AppConfig

        config = AppConfig(sql_warehouse_id="", _env_file=None)
        assert config.workspace_url == ""


# ---------------------------------------------------------------------------
# TC-WP3: /api/workspace-config endpoint
# ---------------------------------------------------------------------------


class TestWorkspaceConfigEndpoint:
    """TC-WP3: Workspace config endpoint for frontend portability."""

    def test_workspace_config_returns_200(self, client):
        """MUST: /api/workspace-config responds."""
        r = client.get("/api/workspace-config")
        assert r.status_code == 200

    def test_workspace_config_has_required_fields(self, client):
        """MUST: Response contains all required fields."""
        data = client.get("/api/workspace-config").json()
        for field in ["workspace_url", "catalog", "schema_name", "genie_space_id"]:
            assert field in data, f"Missing field: {field}"

    def test_workspace_config_schema_default(self, client):
        """MUST: schema_name is populated with default."""
        data = client.get("/api/workspace-config").json()
        assert data["schema_name"] == "energy_theft_protection"


# ---------------------------------------------------------------------------
# TC-WP4: Health endpoint diagnostics
# ---------------------------------------------------------------------------


class TestHealthEndpointDiagnostics:
    """TC-WP4: Health endpoint exposes config + SQL diagnostic."""

    def test_health_includes_catalog(self, client):
        """MUST: /api/health reports configured catalog."""
        data = client.get("/api/health").json()
        assert "catalog" in data

    def test_health_includes_schema(self, client):
        """MUST: /api/health reports configured schema."""
        data = client.get("/api/health").json()
        assert "schema" in data
        assert isinstance(data["schema"], str)

    def test_health_includes_warehouse(self, client):
        """SHOULD: /api/health reports warehouse_id."""
        data = client.get("/api/health").json()
        assert "warehouse_id" in data

    def test_health_includes_sql_test(self, client):
        """MUST: /api/health reports sql_test result."""
        data = client.get("/api/health").json()
        assert "sql_test" in data
        assert "sql_error" in data

    def test_health_sql_test_null_without_connection(self, client):
        """MUST: sql_test is null when SQL is not configured."""
        data = client.get("/api/health").json()
        assert data["sql_test"] is None


# ---------------------------------------------------------------------------
# TC-WP5: Graceful SQL degradation (endpoints return 200 without SQL)
# ---------------------------------------------------------------------------


class TestGracefulSQLDegradation:
    """TC-WP5: API endpoints return default data when SQL is unavailable."""

    def test_kpis_returns_200_without_sql(self, client):
        """MUST: KPIs returns 200 with default data when SQL is unavailable."""
        r = client.get("/api/dashboard/kpis")
        assert r.status_code == 200
        data = r.json()
        assert data["annual_theft_exposure_gbp"] > 0

    def test_heatmap_returns_empty_without_sql(self, client):
        """MUST: Heatmap returns 200 with empty list when SQL is unavailable."""
        r = client.get("/api/dashboard/heatmap")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_score_distribution_returns_empty_without_sql(self, client):
        """MUST: Score distribution returns 200 when SQL is unavailable."""
        r = client.get("/api/dashboard/score-distribution")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_model_performance_returns_empty_without_sql(self, client):
        """MUST: Model performance returns 200 when SQL is unavailable."""
        r = client.get("/api/governance/model-performance")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_investigation_kpis_returns_200_without_sql(self, client):
        """MUST: Investigation KPIs returns 200 with default data."""
        r = client.get("/api/investigation/kpis")
        assert r.status_code == 200
        data = r.json()
        assert "open_high_cases" in data


# ---------------------------------------------------------------------------
# TC-WP6: No hardcoded workspace references in source
# ---------------------------------------------------------------------------


class TestNoHardcodedWorkspaceRefs:
    """TC-WP6: Source code contains no hardcoded workspace URLs or catalog names."""

    @pytest.fixture
    def src_dir(self):
        return pathlib.Path(__file__).parent.parent / "src"

    def test_no_hardcoded_workspace_urls(self, src_dir):
        """MUST: No hardcoded Databricks workspace URLs in src/."""
        import re

        pattern = re.compile(r"adb-\d+\.\d+\.azuredatabricks\.net")
        violations = []
        for f in src_dir.rglob("*.py"):
            content = f.read_text(errors="ignore")
            if pattern.search(content):
                violations.append(str(f))
        for f in src_dir.rglob("*.tsx"):
            content = f.read_text(errors="ignore")
            if pattern.search(content):
                violations.append(str(f))
        assert violations == [], f"Hardcoded workspace URLs found in: {violations}"

    def test_no_hardcoded_dz_demos_catalog(self, src_dir):
        """MUST: No hardcoded 'dz_demos' catalog in src/ (should use config)."""
        violations = []
        for ext in ("*.py", "*.tsx", "*.ts"):
            for f in src_dir.rglob(ext):
                if f.name in ("api.ts",):
                    continue
                content = f.read_text(errors="ignore")
                if "dz_demos" in content:
                    violations.append(str(f))
        assert violations == [], f"Hardcoded 'dz_demos' found in: {violations}"


# ---------------------------------------------------------------------------
# TC-WP7: patch_app_yml.py build script
# ---------------------------------------------------------------------------


class TestPatchAppYml:
    """TC-WP7: Build script correctly patches CATALOG in app.yml."""

    @pytest.fixture
    def temp_build_dir(self):
        """Create a temp .build/ dir with a sample app.yml."""
        tmpdir = tempfile.mkdtemp()
        build_dir = pathlib.Path(tmpdir) / ".build"
        build_dir.mkdir()
        app_yml = build_dir / "app.yml"
        app_yml.write_text(
            'command: ["uvicorn", "app:app"]\n'
            "env:\n"
            '  - name: "CATALOG"\n'
            '    value: ""  # CATALOG\n'
            '  - name: "SCHEMA_NAME"\n'
            '    value: "energy_theft_protection"\n'
        )
        yield tmpdir, build_dir, app_yml
        shutil.rmtree(tmpdir)

    def test_patch_substitutes_catalog(self, temp_build_dir):
        """MUST: Script replaces empty CATALOG with target value."""
        tmpdir, build_dir, app_yml = temp_build_dir
        import subprocess

        script = pathlib.Path(__file__).parent.parent / "scripts" / "patch_app_yml.py"
        result = subprocess.run(
            ["python3", str(script), "my_test_catalog"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        content = app_yml.read_text()
        assert 'value: "my_test_catalog"' in content

    def test_patch_preserves_other_values(self, temp_build_dir):
        """MUST: Script does not modify other env vars."""
        tmpdir, build_dir, app_yml = temp_build_dir
        import subprocess

        script = pathlib.Path(__file__).parent.parent / "scripts" / "patch_app_yml.py"
        subprocess.run(
            ["python3", str(script), "patched_catalog"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        content = app_yml.read_text()
        assert 'value: "energy_theft_protection"' in content
        assert "uvicorn" in content
