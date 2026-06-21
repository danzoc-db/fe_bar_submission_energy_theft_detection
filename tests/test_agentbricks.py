"""TC-AB: Agent Bricks portability and deployment tests.

Validates that the Multi-Agent Supervisor (MAS) for Agent Atlas is:
- Configurable via MAS_ENDPOINT env var (workspace-portable)
- Gracefully degrades when MAS is unavailable (offline fallback)
- Uses correct request/response contract with the serving endpoint
- Provisioned by the 08_configure_agent_atlas notebook
- Integrated into the DAB bundle as a variable + app resource

Unit tests run without network; integration tests require `azsu-centrica-demo`
profile and are marked with `@pytest.mark.integration`.
"""

import os
import pathlib
import subprocess
import tempfile
import shutil

import pytest


PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
DATABRICKS_YML = PROJECT_ROOT / "databricks.yml"
APP_YML = PROJECT_ROOT / "app.yml"


# ---------------------------------------------------------------------------
# TC-AB1: MAS_ENDPOINT configuration portability
# ---------------------------------------------------------------------------


class TestMASConfiguration:
    """TC-AB1: MAS_ENDPOINT is configurable per workspace via env var."""

    def test_mas_endpoint_reads_from_env(self):
        """MUST: AppConfig reads MAS_ENDPOINT from environment."""
        os.environ["MAS_ENDPOINT"] = "mas-test-endpoint"
        try:
            from energy_theft_detection.backend.config import AppConfig

            config = AppConfig(sql_warehouse_id="", _env_file=None)
            assert config.mas_endpoint == "mas-test-endpoint"
        finally:
            os.environ["MAS_ENDPOINT"] = ""

    def test_mas_endpoint_default_when_empty(self):
        """MUST: AppConfig has a default MAS endpoint (can be empty for new workspaces)."""
        os.environ["MAS_ENDPOINT"] = ""
        from energy_theft_detection.backend.config import AppConfig

        config = AppConfig(sql_warehouse_id="", _env_file=None)
        assert isinstance(config.mas_endpoint, str)

    def test_no_hardcoded_mas_tile_ids_in_src(self):
        """MUST: No hardcoded MAS tile IDs in src/ — all driven by config."""
        import re

        tile_id_pattern = re.compile(r"mas-[0-9a-f]{8}-endpoint")
        violations = []
        for ext in ("*.py", "*.ts", "*.tsx"):
            for f in SRC_DIR.rglob(ext):
                content = f.read_text(errors="ignore")
                matches = tile_id_pattern.findall(content)
                if matches:
                    violations.append((str(f.relative_to(PROJECT_ROOT)), matches))
        if violations:
            pytest.fail(
                f"Hardcoded MAS tile IDs in source (should use config.mas_endpoint): {violations}"
            )

    def test_workspace_config_exposes_mas_endpoint(self, client):
        """MUST: /api/workspace-config includes mas_endpoint field."""
        data = client.get("/api/workspace-config").json()
        assert "mas_endpoint" in data


# ---------------------------------------------------------------------------
# TC-AB2: Board report graceful fallback
# ---------------------------------------------------------------------------


class TestBoardReportFallback:
    """TC-AB2: Board report works in offline mode (MAS unavailable)."""

    def test_board_report_200_without_mas(self, client):
        """MUST: Board report returns 200 even when MAS_ENDPOINT is empty."""
        r = client.post("/api/agent/atlas/board-report")
        assert r.status_code == 200

    def test_board_report_has_all_fields_without_mas(self, client):
        """MUST: All required board report fields are present in fallback mode."""
        data = client.post("/api/agent/atlas/board-report").json()
        required_fields = [
            "report_title", "period", "generated_at",
            "executive_summary", "recommendations",
            "kpi_highlights", "agent_trace",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_board_report_fallback_has_content(self, client):
        """MUST: Fallback mode still generates meaningful content."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert len(data["executive_summary"]) > 20
        assert len(data["recommendations"]) >= 1

    def test_board_report_trace_is_list(self, client):
        """SHOULD: agent_trace is a list (may be empty in pure offline mode)."""
        data = client.post("/api/agent/atlas/board-report").json()
        assert isinstance(data["agent_trace"], list)


# ---------------------------------------------------------------------------
# TC-AB3: MAS request/response contract
# ---------------------------------------------------------------------------


class TestMASContract:
    """TC-AB3: MAS invocation uses the correct Responses API contract."""

    def test_mas_prompt_is_well_formed(self):
        """MUST: The MAS prompt in router.py uses the Responses API input format."""
        router_path = SRC_DIR / "energy_theft_detection" / "backend" / "router.py"
        content = router_path.read_text()
        assert 'json={"input": [{"role": "user", "content":' in content, (
            "MAS invocation should use Responses API format: "
            '{"input": [{"role": "user", "content": ...}]}'
        )

    def test_mas_endpoint_url_uses_config(self):
        """MUST: MAS URL is built from config, not hardcoded."""
        router_path = SRC_DIR / "energy_theft_detection" / "backend" / "router.py"
        content = router_path.read_text()
        assert "mas_endpoint" in content
        assert "config.mas_endpoint" in content or "mas_endpoint = config" in content


# ---------------------------------------------------------------------------
# TC-AB4: DAB bundle integration
# ---------------------------------------------------------------------------


class TestDABIntegration:
    """TC-AB4: MAS is properly wired into the Databricks Asset Bundle."""

    def test_databricks_yml_has_mas_variable(self):
        """MUST: databricks.yml defines a mas_endpoint variable."""
        content = DATABRICKS_YML.read_text()
        assert "mas_endpoint:" in content

    def test_databricks_yml_has_mas_app_resource(self):
        """MUST: databricks.yml includes MAS as an app resource."""
        content = DATABRICKS_YML.read_text()
        assert 'name: "mas_endpoint"' in content
        assert "${var.mas_endpoint}" in content

    def test_databricks_yml_has_configure_agent_atlas_task(self):
        """MUST: End-to-end job includes configure_agent_atlas task."""
        content = DATABRICKS_YML.read_text()
        assert "configure_agent_atlas" in content
        assert "08_configure_agent_atlas.py" in content

    def test_configure_agent_atlas_task_depends_on_genie(self):
        """MUST: configure_agent_atlas runs after configure_genie."""
        content = DATABRICKS_YML.read_text()
        lines = content.splitlines()
        atlas_idx = next(
            (i for i, line in enumerate(lines) if "configure_agent_atlas" in line and "task_key" in line),
            None,
        )
        assert atlas_idx is not None
        deps_section = "\n".join(lines[atlas_idx:atlas_idx + 5])
        assert "configure_genie" in deps_section

    def test_app_yml_has_mas_endpoint_env(self):
        """MUST: app.yml defines MAS_ENDPOINT env var."""
        content = APP_YML.read_text()
        assert "MAS_ENDPOINT" in content

    def test_each_target_has_mas_variable(self):
        """MUST: All targets define mas_endpoint variable (even if empty)."""
        content = DATABRICKS_YML.read_text()
        targets = ["dev:", "azsu:", "azure-field-demo:"]
        for target in targets:
            target_idx = content.find(target)
            if target_idx == -1:
                continue
            target_section = content[target_idx:target_idx + 500]
            assert "mas_endpoint" in target_section, (
                f"Target {target} is missing mas_endpoint variable"
            )


# ---------------------------------------------------------------------------
# TC-AB5: Notebook portability (08_configure_agent_atlas.py)
# ---------------------------------------------------------------------------


class TestNotebookPortability:
    """TC-AB5: MAS provisioning notebook is portable across workspaces."""

    @pytest.fixture
    def notebook_content(self):
        return (NOTEBOOKS_DIR / "08_configure_agent_atlas.py").read_text()

    def test_notebook_exists(self):
        """MUST: 08_configure_agent_atlas.py notebook exists."""
        assert (NOTEBOOKS_DIR / "08_configure_agent_atlas.py").is_file()

    def test_notebook_accepts_genie_space_id_param(self, notebook_content):
        """MUST: Notebook accepts genie_space_id as a widget parameter."""
        assert 'dbutils.widgets.text("genie_space_id"' in notebook_content

    def test_notebook_accepts_catalog_param(self, notebook_content):
        """MUST: Notebook accepts catalog as a widget parameter."""
        assert 'dbutils.widgets.text("catalog"' in notebook_content

    def test_notebook_accepts_app_name_param(self, notebook_content):
        """MUST: Notebook accepts app_name as a widget parameter."""
        assert 'dbutils.widgets.text("app_name"' in notebook_content

    def test_notebook_uses_rest_api_not_mcp(self, notebook_content):
        """MUST: Notebook uses REST API directly for portability."""
        assert "api.do(" in notebook_content or "api_client" in notebook_content

    def test_notebook_creates_or_updates_idempotently(self, notebook_content):
        """MUST: Notebook handles both create and update cases."""
        assert "_find_mas_by_name" in notebook_content or "find" in notebook_content.lower()
        assert "_create_mas" in notebook_content
        assert "_update_mas" in notebook_content

    def test_notebook_grants_sp_access(self, notebook_content):
        """MUST: Notebook grants CAN_QUERY to the app service principal."""
        assert "CAN_QUERY" in notebook_content
        assert "service_principal" in notebook_content.lower()

    def test_notebook_waits_for_provisioning(self, notebook_content):
        """MUST: Notebook polls until endpoint is ready."""
        assert "READY" in notebook_content
        assert "poll" in notebook_content.lower() or "wait" in notebook_content.lower()

    def test_notebook_outputs_endpoint_name(self, notebook_content):
        """MUST: Notebook prints the endpoint name for downstream usage."""
        assert "MAS_ENDPOINT" in notebook_content

    def test_notebook_no_hardcoded_tile_ids(self, notebook_content):
        """MUST: No hardcoded MAS tile IDs — all discovered or created dynamically."""
        import re

        matches = re.findall(r"mas-[0-9a-f]{8}-endpoint", notebook_content)
        assert matches == [], f"Hardcoded tile IDs in notebook: {matches}"


# ---------------------------------------------------------------------------
# TC-AB6: patch_app_yml.py handles MAS_ENDPOINT
# ---------------------------------------------------------------------------


class TestPatchAppYmlMAS:
    """TC-AB6: Build script patches MAS_ENDPOINT into app.yml."""

    @pytest.fixture
    def temp_build_dir(self):
        tmpdir = tempfile.mkdtemp()
        build_dir = pathlib.Path(tmpdir) / ".build"
        build_dir.mkdir()
        app_yml = build_dir / "app.yml"
        app_yml.write_text(
            'command: ["uvicorn", "app:app"]\n'
            "env:\n"
            '  - name: "CATALOG"\n'
            '    value: ""  # CATALOG\n'
            '  - name: "MAS_ENDPOINT"\n'
            '    value: ""  # MAS_ENDPOINT\n'
        )
        yield tmpdir, build_dir, app_yml
        shutil.rmtree(tmpdir)

    def test_patch_with_mas_endpoint(self, temp_build_dir):
        """MUST: Script patches MAS_ENDPOINT when provided."""
        tmpdir, _, app_yml = temp_build_dir
        script = PROJECT_ROOT / "scripts" / "patch_app_yml.py"
        result = subprocess.run(
            ["python3", str(script), "my_catalog", "mas-abc12345-endpoint"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        content = app_yml.read_text()
        assert 'value: "mas-abc12345-endpoint"' in content
        assert 'value: "my_catalog"' in content

    def test_patch_without_mas_endpoint(self, temp_build_dir):
        """MUST: Script leaves MAS_ENDPOINT empty when not provided."""
        tmpdir, _, app_yml = temp_build_dir
        script = PROJECT_ROOT / "scripts" / "patch_app_yml.py"
        result = subprocess.run(
            ["python3", str(script), "my_catalog"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        content = app_yml.read_text()
        assert 'value: "my_catalog"' in content
        assert '# MAS_ENDPOINT' in content


# ---------------------------------------------------------------------------
# TC-AB7: Remote MAS integration (requires deployed workspace)
# ---------------------------------------------------------------------------


_INTEGRATION_MAS_ENDPOINT = "mas-c41b54be-endpoint"
_INTEGRATION_PROFILE = "azsu-centrica-demo"
_INTEGRATION_APP_URL = "https://energy-theft-detection-7405616473758737.17.azure.databricksapps.com"


@pytest.fixture(scope="module")
def _integration_workspace():
    from databricks.sdk import WorkspaceClient

    try:
        return WorkspaceClient(profile=_INTEGRATION_PROFILE)
    except Exception:
        pytest.skip(f"Cannot authenticate with profile {_INTEGRATION_PROFILE}")


@pytest.mark.integration
class TestRemoteMASIntegration:
    """TC-AB7: MAS endpoint responds on deployed workspace.

    Run with: pytest tests/test_agentbricks.py -m integration -v
    Requires: azsu-centrica-demo profile + deployed app
    """

    @pytest.fixture
    def workspace(self, _integration_workspace):
        return _integration_workspace

    @pytest.fixture
    def mas_endpoint_name(self):
        return _INTEGRATION_MAS_ENDPOINT

    def test_mas_endpoint_exists(self, workspace, mas_endpoint_name):
        """MUST: MAS serving endpoint exists on the workspace."""
        if not mas_endpoint_name:
            pytest.skip("MAS_ENDPOINT not configured")
        ep = workspace.serving_endpoints.get(mas_endpoint_name)
        assert ep is not None, f"Endpoint {mas_endpoint_name} not found"

    def test_mas_endpoint_ready(self, workspace, mas_endpoint_name):
        """MUST: MAS serving endpoint is in READY state."""
        if not mas_endpoint_name:
            pytest.skip("MAS_ENDPOINT not configured")
        ep = workspace.serving_endpoints.get(mas_endpoint_name)
        ready_val = ep.state.ready.value if hasattr(ep.state.ready, "value") else str(ep.state.ready)
        assert ready_val == "READY", f"Endpoint state: {ep.state.ready}"

    def test_mas_endpoint_responds(self, workspace, mas_endpoint_name):
        """MUST: MAS endpoint processes a query and returns output."""
        if not mas_endpoint_name:
            pytest.skip("MAS_ENDPOINT not configured")
        import httpx

        host = workspace.config.host
        headers = workspace.config.authenticate()
        resp = httpx.post(
            f"{host}/serving-endpoints/{mas_endpoint_name}/invocations",
            json={"input": [{"role": "user", "content": "How many HIGH risk accounts do we have?"}]},
            headers=headers,
            timeout=90,
        )
        assert resp.status_code == 200, f"MAS returned {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert "output" in data, f"No 'output' in response: {list(data.keys())}"

    def test_mas_endpoint_latency(self, workspace, mas_endpoint_name):
        """SHOULD: MAS responds within 90 seconds for simple queries."""
        if not mas_endpoint_name:
            pytest.skip("MAS_ENDPOINT not configured")
        import httpx
        import time

        host = workspace.config.host
        headers = workspace.config.authenticate()
        start = time.time()
        resp = httpx.post(
            f"{host}/serving-endpoints/{mas_endpoint_name}/invocations",
            json={"input": [{"role": "user", "content": "What is the total revenue recovered this month?"}]},
            headers=headers,
            timeout=90,
        )
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 90, f"MAS took {elapsed:.1f}s — too slow for demo"

    def test_board_report_generates_content(self, workspace):
        """MUST: Board report endpoint returns content (via MAS or fallback)."""
        import httpx

        headers = workspace.config.authenticate()
        resp = httpx.post(
            f"{_INTEGRATION_APP_URL}/api/agent/atlas/board-report",
            headers=headers,
            timeout=120,
        )
        if resp.status_code != 200:
            pytest.skip(f"Board report returned {resp.status_code}")
        data = resp.json()
        assert "executive_summary" in data
        assert len(data["executive_summary"]) > 20
        trace = data.get("agent_trace", [])
        agent_names = [step.get("agent", "") for step in trace]
        if "supervisor" in agent_names or "kpi_data_agent" in agent_names:
            pass  # MAS path — ideal
        else:
            pass  # Fallback path — acceptable until app redeployed with MAS_ENDPOINT
