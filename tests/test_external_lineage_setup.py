"""Drift tests for scripts/setup/external_lineage_objects.py.

These guard against the most common way the external-lineage feature can
break silently:

  * A column is renamed in `notebooks/04_batch_scoring.py` or in the silver
    layer, but the shared lineage module still references the old name.
    Result: `notebooks/09_configure_external_lineage.py` would fail at runtime
    with a confusing "source column not found" error from the GA API.

  * A new PBI report is added but its name is reused or its column list
    contradicts the COLUMN_EDGES targets — Catalog Explorer would render
    edges into nothing.

  * The `.pbip` generator would emit TMDL referencing dead columns.

Run as a normal pytest suite — no Databricks connection needed; we only
inspect the shared module against its own SOURCE_TABLE_SCHEMAS fixture.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_MODULE_PATH = REPO_ROOT / "scripts" / "setup" / "external_lineage_objects.py"


@pytest.fixture(scope="module")
def lineage():
    """Load the shared module directly from disk (no package install needed)."""
    spec = importlib.util.spec_from_file_location(
        "_test_external_lineage_objects", str(SHARED_MODULE_PATH)
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_test_external_lineage_objects"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestReports:
    """Reports are well-formed."""

    def test_has_four_reports(self, lineage):
        assert len(lineage.POWER_BI_REPORTS) == 4

    def test_report_names_unique(self, lineage):
        names = [r.name for r in lineage.POWER_BI_REPORTS]
        assert len(names) == len(set(names)), "duplicate PBI report name"

    def test_report_names_snake_case(self, lineage):
        for r in lineage.POWER_BI_REPORTS:
            assert r.name.islower(), f"{r.name} should be lowercase"
            assert " " not in r.name, f"{r.name} should be snake_case"

    def test_report_entity_types_known(self, lineage):
        allowed = {"dashboard", "report"}
        for r in lineage.POWER_BI_REPORTS:
            assert r.entity_type in allowed, (
                f"{r.name}.entity_type={r.entity_type!r} not in {allowed}"
            )

    def test_report_urls_look_like_powerbi(self, lineage):
        for r in lineage.POWER_BI_REPORTS:
            assert r.url.startswith("https://app.powerbi.com/"), (
                f"{r.name} URL doesn't look like a Power BI report URL"
            )

    def test_report_has_at_least_three_columns(self, lineage):
        for r in lineage.POWER_BI_REPORTS:
            assert len(r.columns) >= 3, (
                f"{r.name} has only {len(r.columns)} columns — make it look richer"
            )


class TestColumnEdges:
    """Column edges reference real UC tables / columns."""

    def test_at_least_fifteen_edges(self, lineage):
        assert len(lineage.COLUMN_EDGES) >= 15

    def test_every_source_table_known(self, lineage):
        known = set(lineage.SOURCE_TABLE_SCHEMAS)
        for e in lineage.COLUMN_EDGES:
            assert e.source_table in known, (
                f"unknown source_table {e.source_table!r} (add it to "
                f"SOURCE_TABLE_SCHEMAS or fix the typo)"
            )

    def test_every_source_column_in_schema(self, lineage):
        """The drift test that actually saves us. Catches typos and renames."""
        for e in lineage.COLUMN_EDGES:
            schema = lineage.SOURCE_TABLE_SCHEMAS[e.source_table]
            assert e.source_column in schema, (
                f"ColumnEdge references missing column "
                f"{e.source_table}.{e.source_column} — either the column was "
                f"renamed in 04_batch_scoring.py / silver layer, or the typo "
                f"is in scripts/setup/external_lineage_objects.py."
            )

    def test_every_target_pbi_known(self, lineage):
        names = {r.name for r in lineage.POWER_BI_REPORTS}
        for e in lineage.COLUMN_EDGES:
            assert e.target_pbi in names, (
                f"ColumnEdge targets unknown PBI report {e.target_pbi!r}"
            )

    def test_every_target_column_declared_on_report(self, lineage):
        cols_by_name = {r.name: set(r.columns) for r in lineage.POWER_BI_REPORTS}
        for e in lineage.COLUMN_EDGES:
            assert e.target_column in cols_by_name[e.target_pbi], (
                f"ColumnEdge maps to {e.target_pbi}.{e.target_column} but "
                f"that column isn't declared on the report — Catalog Explorer "
                f"will render an edge into nothing."
            )

    def test_every_report_has_at_least_one_edge(self, lineage):
        sources = {e.target_pbi for e in lineage.COLUMN_EDGES}
        for r in lineage.POWER_BI_REPORTS:
            assert r.name in sources, (
                f"{r.name} has no column edges — would show up in Catalog "
                f"Explorer with no upstream lineage."
            )


class TestHelpers:
    def test_upstream_tables_for_returns_unique_sorted(self, lineage):
        for r in lineage.POWER_BI_REPORTS:
            tables = lineage.upstream_tables_for(r.name)
            assert tables == sorted(set(tables))
            assert all(isinstance(t, str) for t in tables)

    def test_columns_used_from_returns_unique_sorted(self, lineage):
        for r in lineage.POWER_BI_REPORTS:
            for tbl in lineage.upstream_tables_for(r.name):
                cols = lineage.columns_used_from(r.name, tbl)
                assert cols == sorted(set(cols))
                assert all(isinstance(c, str) for c in cols)


class TestDemoMarker:
    def test_demo_marker_set(self, lineage):
        assert lineage.DEMO_PROPERTIES.get("created_by") == "energy-theft-end-to-end"
