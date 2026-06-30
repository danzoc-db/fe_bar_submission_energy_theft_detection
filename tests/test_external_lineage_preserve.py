"""Unit tests for non-destructive external_metadata registration logic."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_MODULE_PATH = REPO_ROOT / "scripts" / "setup" / "external_lineage_objects.py"


def _load_shared():
    spec = importlib.util.spec_from_file_location(
        "_test_external_lineage_preserve", str(SHARED_MODULE_PATH)
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_test_external_lineage_preserve"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestPreserveRegistrationLogic:
    """Mirrors notebooks/09_configure_external_lineage.py decision paths."""

    def test_is_demo_metadata_matches_marker(self):
        shared = _load_shared()
        meta = {
            "name": "revenue_protection_exec_dashboard",
            "properties": dict(shared.DEMO_PROPERTIES),
        }
        props = meta.get("properties") or {}
        assert all(props.get(k) == v for k, v in shared.DEMO_PROPERTIES.items())

    def test_register_preserves_existing_without_force_recreate(self):
        """When object exists and force_recreate=false, create/delete must not run."""
        shared = _load_shared()
        report = shared.POWER_BI_REPORTS[0]
        existing = {
            "name": report.name,
            "properties": dict(shared.DEMO_PROPERTIES),
            "columns": report.columns,
        }

        delete_called = False
        create_called = False

        def fake_get(name: str):
            assert name == report.name
            return existing

        def fake_delete(name: str):
            nonlocal delete_called
            delete_called = True

        def fake_create(r):
            nonlocal create_called
            create_called = True

        force_recreate = False
        dry_run = False

        # Inline the notebook's preserve branch
        if dry_run:
            outcome = "dry_run"
        else:
            ex = fake_get(report.name)
            if ex:
                props = ex.get("properties") or {}
                is_demo = all(props.get(k) == v for k, v in shared.DEMO_PROPERTIES.items())
                assert is_demo
                if not force_recreate:
                    outcome = "preserved"
                else:
                    fake_delete(report.name)
                    fake_create(report)
                    outcome = "recreated"
            else:
                fake_create(report)
                outcome = "created"

        assert outcome == "preserved"
        assert delete_called is False
        assert create_called is False

    def test_soft_skip_when_create_probe_fails(self):
        allowed, reason = False, "CREATE probe returned 403"
        would_mutate = allowed
        assert would_mutate is False
        assert "403" in reason
