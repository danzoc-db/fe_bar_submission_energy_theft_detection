#!/usr/bin/env python3
"""Generate Power BI Project (.pbip) directories from the shared external-lineage
module — single source of truth for the UC bootstrap, the backend endpoint,
and the .pbip artifacts.

For each PBIReport in scripts/setup/external_lineage_objects.POWER_BI_REPORTS:

    dashboards/powerbi/<slug>/
        <slug>.pbip                              # JSON entry
        <slug>.Report/
            definition.pbir                       # PBIR-Legacy version 1.0
            report.json                           # minimal report with 1 page + N card visuals
        <slug>.SemanticModel/
            definition.pbism                      # version 4.0 (TMDL)
            definition/
                database.tmdl
                model.tmdl                        # culture + annotations
                expressions.tmdl                  # parameterised Databricks connection
                cultures/en-US.tmdl               # required by TMDL
                tables/<upstream_table>.tmdl      # one per upstream UC table
        .gitignore

The TMDL tables reference exactly the columns that
scripts/setup/external_lineage_objects.py says are used (via
`columns_used_from(report.name, source_table)`), keeping the .pbip in lockstep
with the UC external_metadata registration and the app's lineage toggle.

Run:

    python scripts/generate_pbip.py              # writes dashboards/powerbi/
    python scripts/generate_pbip.py --only=pbi_revenue_protection_exec
    python scripts/generate_pbip.py --out=/tmp/pbip-test
    python scripts/generate_pbip.py --validate-only

The generator is **idempotent**: it deletes the per-report directory first
and re-emits from scratch, so re-running produces a clean tree (no stale
files from a previous run).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_MODULE_PATH = REPO_ROOT / "scripts" / "setup" / "external_lineage_objects.py"
DEFAULT_OUT_DIR = REPO_ROOT / "dashboards" / "powerbi"


# ---------------------------------------------------------------------------
# Shared module loader (matches the pattern in the backend)
# ---------------------------------------------------------------------------

def _load_shared():
    spec = importlib.util.spec_from_file_location(
        "_pbip_lineage_objects", str(SHARED_MODULE_PATH)
    )
    assert spec and spec.loader, "could not build importlib spec for shared module"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_pbip_lineage_objects"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    """`pbi_revenue_protection_exec` -> `revenue-protection-exec`."""
    return name.removeprefix("pbi_").replace("_", "-")


def _stable_guid(seed: str) -> str:
    """Reproducible UUID so re-runs produce identical diffs."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"energy-theft-pbip://{seed}"))


def _tmdl_quote(value: str) -> str:
    """Quote a string literal for TMDL. TMDL uses double quotes."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _tmdl_ident(name: str) -> str:
    """Quote an identifier with single quotes when it contains special chars."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    escaped = name.replace("'", "''")
    return f"'{escaped}'"


# ---------------------------------------------------------------------------
# JSON entry files
# ---------------------------------------------------------------------------

def write_pbip_entry(report_dir: Path, slug: str) -> Path:
    """Top-level <slug>.pbip — opens the report when double-clicked."""
    payload = {
        "version": "1.0",
        "artifacts": [
            {"report": {"path": f"{slug}.Report"}},
        ],
        "settings": {
            "enableAutoRecovery": True,
        },
    }
    p = report_dir / f"{slug}.pbip"
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p


def write_pbir(report_subdir: Path, slug: str) -> Path:
    """definition.pbir — PBIR-Legacy 1.0 referencing the sibling SemanticModel."""
    payload = {
        "version": "1.0",
        "datasetReference": {
            "byPath": {"path": f"../{slug}.SemanticModel"},
            "byConnection": None,
        },
    }
    p = report_subdir / "definition.pbir"
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p


def write_pbism(semantic_subdir: Path) -> Path:
    """definition.pbism — TMDL format (version 4.0)."""
    payload = {
        "version": "4.0",
        "settings": {},
    }
    p = semantic_subdir / "definition.pbism"
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# TMDL emission
# ---------------------------------------------------------------------------

def emit_database_tmdl(report_name: str) -> str:
    """database.tmdl — database wrapper. Model definition lives in model.tmdl."""
    db_name = report_name.removeprefix("pbi_")
    return (
        f"database {_tmdl_ident(db_name)}\n"
        f"\tcompatibilityLevel: 1567\n"
    )


def emit_model_tmdl(report_name: str, upstream_tables: list[str]) -> str:
    """Top-level model.tmdl with table query order + culture."""
    order = json.dumps(upstream_tables)
    return (
        f"model Model\n"
        f"\tculture: en-US\n"
        f"\tdiscourageImplicitMeasures\n"
        f"\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        f"\tsourceQueryCulture: en-GB\n"
        f"\tdataAccessOptions\n"
        f"\t\tlegacyRedirects\n"
        f"\t\treturnErrorValuesAsNull\n"
        f"\n"
        f"annotation PBI_QueryOrder = {order}\n"
        f"annotation PBI_ETD_Report = {report_name}\n"
    )


def emit_culture_tmdl() -> str:
    return (
        "cultureInfo en-US\n"
        "\n"
        "linguisticMetadata = {\n"
        "  \"Version\": \"1.0.0\",\n"
        "  \"Language\": \"en-US\"\n"
        "}\n"
        "\tcontentType: json\n"
    )


def _param_expression(name: str, default: str) -> str:
    """One M parameter — `expression <name> = "<default>" meta [...]` block."""
    lt = _stable_guid(f"expression/{name}")
    list_json = json.dumps([default])  # `List={"foo"}` accepts JSON array literal
    return (
        f'expression {name} = "{default}" meta '
        f'[IsParameterQuery=true, List={list_json}, '
        f'DefaultValue="{default}", Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {lt}\n"
    )


def emit_expressions_tmdl(default_catalog: str, default_schema: str) -> str:
    """M parameters the user fills on first open in Power BI Desktop."""
    parts = [
        _param_expression("workspace_host", "https://your-workspace.cloud.databricks.com"),
        _param_expression("http_path", "/sql/1.0/warehouses/your-warehouse-id"),
        _param_expression("catalog_name", default_catalog),
        _param_expression("schema_name", default_schema),
    ]
    return "\n".join(parts) + "\n"


# TMDL data type mapping — keeps in sync with SOURCE_TABLE_SCHEMAS values
_TMDL_DATA_TYPES = {
    "string": "string",
    "int64": "int64",
    "double": "double",
    "dateTime": "dateTime",
    "boolean": "boolean",
}

_TMDL_SUMMARIZE_BY = {
    "string": "none",
    "int64": "sum",
    "double": "sum",
    "dateTime": "none",
    "boolean": "none",
}

_TMDL_FORMAT = {
    "double": "0.000",
    "int64": "0",
    "dateTime": "yyyy-mm-dd",
}


def emit_table_tmdl(
    report_name: str,
    table: str,
    columns: list[str],
    schema: dict[str, str],
    measures: list[tuple[str, str, str]],
) -> str:
    """One table.tmdl per upstream UC table.

    `measures` is a list of (measure_name, dax_expression, format_string).
    """
    table_lineage = _stable_guid(f"{report_name}/{table}")
    lines: list[str] = [
        f"table {_tmdl_ident(table)}",
        f"\tlineageTag: {table_lineage}",
        "",
    ]
    for col in columns:
        dt = schema.get(col, "string")
        tmdl_dt = _TMDL_DATA_TYPES.get(dt, "string")
        col_lineage = _stable_guid(f"{report_name}/{table}/{col}")
        lines.append(f"\tcolumn {_tmdl_ident(col)}")
        lines.append(f"\t\tdataType: {tmdl_dt}")
        lines.append(f"\t\tsourceColumn: {col}")
        if dt in _TMDL_FORMAT:
            lines.append(f"\t\tformatString: {_TMDL_FORMAT[dt]}")
        lines.append(f"\t\tsummarizeBy: {_TMDL_SUMMARIZE_BY.get(dt, 'none')}")
        lines.append(f"\t\tlineageTag: {col_lineage}")
        lines.append("")

    for m_name, dax, fmt in measures:
        m_lineage = _stable_guid(f"{report_name}/{table}/measure/{m_name}")
        lines.append(f"\tmeasure {_tmdl_ident(m_name)} = {dax}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tlineageTag: {m_lineage}")
        lines.append("")

    # Partition — DirectQuery via the Databricks Power BI connector,
    # parameterised against the M expressions in expressions.tmdl.
    partition_lineage = _stable_guid(f"{report_name}/{table}/partition")
    m_expr = (
        "let\n"
        "\t\t\t\tSource = Databricks.Catalogs(workspace_host, http_path, null),\n"
        "\t\t\t\tcatalog = Source{[Name=catalog_name]}[Data],\n"
        "\t\t\t\tschema = catalog{[Name=schema_name]}[Data],\n"
        f'\t\t\t\ttbl = schema{{[Name="{table}"]}}[Data]\n'
        "\t\t\tin\n"
        "\t\t\t\ttbl"
    )
    lines.append(f"\tpartition {_tmdl_ident(table)} = m")
    lines.append("\t\tmode: directQuery")
    lines.append("\t\tsource =")
    lines.append(f"\t\t\t{m_expr}")
    lines.append("")
    lines.append("\tannotation PBI_ResultType = Table")
    lines.append("")
    lines.append(f"\tannotation PBI_TableLineageTag = {partition_lineage}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-report measure definitions — illustrative, demonstrate DAX patterns
# ---------------------------------------------------------------------------

# (table -> list of (measure_name, dax, formatString))
_REPORT_MEASURES: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "pbi_revenue_protection_exec": {
        "anomaly_scores": [
            ("HighRiskAccounts", "COUNTROWS(FILTER(anomaly_scores, anomaly_scores[risk_tier] = \"HIGH\"))", "#,0"),
            ("AverageRiskScore", "AVERAGE(anomaly_scores[composite_risk_score])", "0.000"),
        ],
        "investigation_cases": [
            ("RecoveredGBP", "SUM(investigation_cases[revenue_recovered_gbp])", "£#,0"),
            ("ConfirmedTheftCount", "CALCULATE(COUNTROWS(investigation_cases), investigation_cases[outcome] = \"THEFT_CONFIRMED\")", "#,0"),
            ("DetectionPrecisionPct", "DIVIDE([ConfirmedTheftCount], COUNTROWS(investigation_cases))", "0.0%"),
        ],
    },
    "pbi_field_ops_heatmap": {
        "anomaly_scores": [
            ("HighRiskHotspots", "COUNTROWS(FILTER(anomaly_scores, anomaly_scores[composite_risk_score] >= 0.75))", "#,0"),
            ("AverageRiskIntensity", "AVERAGE(anomaly_scores[composite_risk_score])", "0.000"),
        ],
        "investigation_cases": [
            ("OpenCasesByRegion", "CALCULATE(COUNTROWS(investigation_cases), ISBLANK(investigation_cases[closed_timestamp]))", "#,0"),
        ],
    },
    "pbi_customer_insights": {
        "smart_meter_reads": [
            ("DailyConsumptionKWh", "SUM(smart_meter_reads[consumption_kwh])", "0.0"),
            ("CommsGapAccounts", "CALCULATE(DISTINCTCOUNT(smart_meter_reads[account_id]), smart_meter_reads[comms_gap_flag] = TRUE())", "#,0"),
        ],
        "anomaly_scores": [
            ("AverageRiskScoreInsight", "AVERAGE(anomaly_scores[composite_risk_score])", "0.000"),
        ],
    },
    "pbi_regulatory_compliance": {
        "investigation_cases": [
            ("ConfirmedTheftYTD", "CALCULATE(COUNTROWS(investigation_cases), investigation_cases[outcome] = \"THEFT_CONFIRMED\")", "#,0"),
            ("AverageDaysToClose", "AVERAGEX(FILTER(investigation_cases, NOT ISBLANK(investigation_cases[closed_timestamp])), DATEDIFF(investigation_cases[opened_timestamp], investigation_cases[closed_timestamp], DAY))", "0.0"),
        ],
        "model_performance_log": [
            ("LatestPrecisionPct", "MAXX(TOPN(1, model_performance_log, model_performance_log[month], DESC), model_performance_log[precision_pct])", "0.0%"),
            ("LatestRecallPct", "MAXX(TOPN(1, model_performance_log, model_performance_log[month], DESC), model_performance_log[recall_pct])", "0.0%"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Report.json (PBIR-Legacy) — minimal page with N Card visuals per measure
# ---------------------------------------------------------------------------

def _card_visual(x: int, y: int, w: int, h: int, table: str, measure: str, label: str) -> dict:
    """Build one Card visualContainer config (singleVisual = card)."""
    visual_id = _stable_guid(f"visual/{table}/{measure}").replace("-", "")[:32]
    config = {
        "name": visual_id,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0}}],
        "singleVisual": {
            "visualType": "card",
            "projections": {
                "Values": [
                    {"queryRef": f"{measure}", "active": True}
                ]
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "t", "Entity": table, "Type": 0}],
                "Select": [
                    {
                        "Measure": {
                            "Expression": {"SourceRef": {"Source": "t"}},
                            "Property": measure,
                        },
                        "Name": f"{table}.{measure}",
                        "NativeReferenceName": label,
                    }
                ],
            },
            "objects": {
                "labels": [
                    {"properties": {"fontSize": {"expr": {"Literal": {"Value": "12D"}}}}}
                ]
            },
        },
    }
    return {
        "x": x, "y": y, "z": 0, "width": w, "height": h,
        "config": json.dumps(config),
        "filters": "[]",
    }


def emit_report_json(report) -> str:
    """Minimal PBIR-Legacy report.json with one page + Card visuals for each measure."""
    visuals: list[dict] = []
    x, y = 16, 16
    card_w, card_h = 240, 120
    gap = 16
    cards_per_row = 4
    idx = 0

    measures = _REPORT_MEASURES.get(report.name, {})
    for table, measure_list in measures.items():
        for m_name, _dax, _fmt in measure_list:
            row, col = divmod(idx, cards_per_row)
            vx = x + col * (card_w + gap)
            vy = y + row * (card_h + gap)
            visuals.append(_card_visual(vx, vy, card_w, card_h, table, m_name, m_name))
            idx += 1

    page_id = _stable_guid(f"{report.name}/page1").replace("-", "")[:32]
    payload = {
        "config": json.dumps({
            "version": "5.55",
            "themeCollection": {"baseTheme": {"name": "CY24SU06"}},
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
            "settings": {"useStylableVisualContainerHeader": True},
        }),
        "layoutOptimization": 0,
        "resourcePackages": [],
        "sections": [
            {
                "name": page_id,
                "displayName": report.display,
                "displayOption": 1,
                "config": json.dumps({"visibility": 0}),
                "filters": "[]",
                "height": 720,
                "width": 1280,
                "ordinal": 0,
                "visualContainers": visuals,
            }
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Per-report generation
# ---------------------------------------------------------------------------

def generate_report(
    out_dir: Path,
    report,
    shared,
    catalog_default: str = "demo_catalog",
    schema_default: str = "energy_theft_protection",
) -> dict:
    slug = _slug(report.name)
    pbip_root = out_dir / slug
    if pbip_root.exists():
        shutil.rmtree(pbip_root)
    pbip_root.mkdir(parents=True)

    # ── Top-level entry ────────────────────────────────────────────────────
    write_pbip_entry(pbip_root, slug)

    # ── Report folder ──────────────────────────────────────────────────────
    report_subdir = pbip_root / f"{slug}.Report"
    (report_subdir / "StaticResources").mkdir(parents=True)
    write_pbir(report_subdir, slug)
    (report_subdir / "report.json").write_text(
        emit_report_json(report), encoding="utf-8"
    )

    # ── SemanticModel folder ───────────────────────────────────────────────
    sem_subdir = pbip_root / f"{slug}.SemanticModel"
    sem_subdir.mkdir(parents=True)
    write_pbism(sem_subdir)
    sem_def = sem_subdir / "definition"
    (sem_def / "tables").mkdir(parents=True)
    (sem_def / "cultures").mkdir(parents=True)

    upstreams = shared.upstream_tables_for(report.name)
    (sem_def / "database.tmdl").write_text(
        emit_database_tmdl(report.name), encoding="utf-8"
    )
    (sem_def / "model.tmdl").write_text(
        emit_model_tmdl(report.name, upstreams), encoding="utf-8"
    )
    (sem_def / "expressions.tmdl").write_text(
        emit_expressions_tmdl(catalog_default, schema_default), encoding="utf-8"
    )
    (sem_def / "cultures" / "en-US.tmdl").write_text(
        emit_culture_tmdl(), encoding="utf-8"
    )

    measures_for_report = _REPORT_MEASURES.get(report.name, {})
    table_files: list[str] = []
    for table in upstreams:
        cols = shared.columns_used_from(report.name, table)
        schema = shared.SOURCE_TABLE_SCHEMAS[table]
        measures = measures_for_report.get(table, [])
        tmdl = emit_table_tmdl(report.name, table, cols, schema, measures)
        (sem_def / "tables" / f"{table}.tmdl").write_text(tmdl, encoding="utf-8")
        table_files.append(table)

    # .gitignore — exclude the per-user/runtime caches Power BI writes
    (pbip_root / ".gitignore").write_text(
        "**/.pbi/localSettings.json\n"
        "**/.pbi/cache.abf\n"
        "**/.pbi/editorSettings.json\n",
        encoding="utf-8",
    )

    return {
        "slug": slug,
        "report": report.name,
        "display": report.display,
        "out_dir": str(pbip_root),
        "upstream_tables": upstreams,
        "table_files": table_files,
        "measures": sum(len(v) for v in measures_for_report.values()),
    }


# ---------------------------------------------------------------------------
# Static validation
# ---------------------------------------------------------------------------

def _walk_json(path: Path) -> Iterable[Path]:
    yield from path.rglob("*.pbip")
    yield from path.rglob("*.pbir")
    yield from path.rglob("*.pbism")
    yield from path.rglob("*.json")


def validate_pbip_dir(pbip_root: Path, shared) -> list[str]:
    """Return a list of problem strings. Empty list = OK."""
    issues: list[str] = []
    slug = pbip_root.name

    # Required files
    must_exist = [
        pbip_root / f"{slug}.pbip",
        pbip_root / f"{slug}.Report" / "definition.pbir",
        pbip_root / f"{slug}.Report" / "report.json",
        pbip_root / f"{slug}.SemanticModel" / "definition.pbism",
        pbip_root / f"{slug}.SemanticModel" / "definition" / "database.tmdl",
        pbip_root / f"{slug}.SemanticModel" / "definition" / "model.tmdl",
        pbip_root / f"{slug}.SemanticModel" / "definition" / "expressions.tmdl",
        pbip_root / f"{slug}.SemanticModel" / "definition" / "cultures" / "en-US.tmdl",
    ]
    for p in must_exist:
        if not p.is_file():
            issues.append(f"missing: {p.relative_to(pbip_root)}")

    # JSON parse-ability
    for p in _walk_json(pbip_root):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"invalid JSON in {p.relative_to(pbip_root)}: {e}")

    # .pbip → .Report → .SemanticModel references
    try:
        entry = json.loads((pbip_root / f"{slug}.pbip").read_text(encoding="utf-8"))
        assert entry["artifacts"][0]["report"]["path"] == f"{slug}.Report"
    except Exception as e:
        issues.append(f"{slug}.pbip artifact mismatch: {e}")

    try:
        pbir = json.loads((pbip_root / f"{slug}.Report" / "definition.pbir").read_text(encoding="utf-8"))
        assert pbir["datasetReference"]["byPath"]["path"] == f"../{slug}.SemanticModel"
    except Exception as e:
        issues.append(f"definition.pbir reference mismatch: {e}")

    # TMDL columns match the shared module for the matching report
    report_name = "pbi_" + slug.replace("-", "_")
    report = next((r for r in shared.POWER_BI_REPORTS if r.name == report_name), None)
    if report is None:
        issues.append(f"could not match slug {slug!r} back to a PBIReport")
        return issues

    upstreams = shared.upstream_tables_for(report.name)
    tables_dir = pbip_root / f"{slug}.SemanticModel" / "definition" / "tables"
    tmdl_files = {p.stem for p in tables_dir.glob("*.tmdl")}
    if tmdl_files != set(upstreams):
        issues.append(
            f"TMDL tables {sorted(tmdl_files)} != upstream tables {sorted(upstreams)}"
        )

    for table in upstreams:
        tmdl = (tables_dir / f"{table}.tmdl").read_text(encoding="utf-8")
        expected_cols = shared.columns_used_from(report.name, table)
        for col in expected_cols:
            # `column foo` or `column 'foo bar'` — match the column declaration line.
            if not re.search(rf"^\tcolumn (?:{re.escape(col)}|'{re.escape(col)}')\b", tmdl, re.MULTILINE):
                issues.append(
                    f"{table}.tmdl missing column {col!r} (expected per shared module)"
                )
        if f'[Name="{table}"]' not in tmdl:
            issues.append(f"{table}.tmdl partition doesn't reference [Name=\"{table}\"]")

    # Report.json parses + has at least one page
    try:
        rep = json.loads((pbip_root / f"{slug}.Report" / "report.json").read_text(encoding="utf-8"))
        assert rep["sections"], "no pages in report.json"
        # Each visualContainer.config must itself parse as JSON
        for s in rep["sections"]:
            for v in s.get("visualContainers", []):
                json.loads(v["config"])
    except Exception as e:
        issues.append(f"report.json structural issue: {e}")

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory (default: dashboards/powerbi)")
    parser.add_argument("--only", help="Generate just one report by name (e.g. pbi_revenue_protection_exec)")
    parser.add_argument("--catalog", default="demo_catalog", help="Default UC catalog baked into the M parameter")
    parser.add_argument("--schema", default="energy_theft_protection", help="Default UC schema baked into the M parameter")
    parser.add_argument("--validate-only", action="store_true", help="Skip generation; just validate existing .pbip dirs")
    args = parser.parse_args()

    shared = _load_shared()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = [r for r in shared.POWER_BI_REPORTS if (not args.only or r.name == args.only)]
    if not reports:
        print(f"No reports match --only={args.only!r}")
        return 1

    if args.validate_only:
        all_ok = True
        for r in reports:
            slug = _slug(r.name)
            issues = validate_pbip_dir(out_dir / slug, shared)
            if issues:
                all_ok = False
                print(f"✗ {slug}:")
                for i in issues:
                    print(f"    - {i}")
            else:
                print(f"✓ {slug}  (no issues)")
        return 0 if all_ok else 1

    summary: list[dict] = []
    for r in reports:
        info = generate_report(out_dir, r, shared, args.catalog, args.schema)
        summary.append(info)
        issues = validate_pbip_dir(Path(info["out_dir"]), shared)
        info["issues"] = issues
        status = "✓" if not issues else "✗"
        print(f"{status} {info['slug']:30s}  tables={len(info['upstream_tables']):2d}  measures={info['measures']:2d}  → {info['out_dir']}")
        for i in issues:
            print(f"    ! {i}")

    print()
    print(f"Wrote {len(summary)} .pbip directories under {out_dir}")
    bad = sum(1 for s in summary if s["issues"])
    if bad:
        print(f"  {bad} report(s) have validation issues — see above")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
