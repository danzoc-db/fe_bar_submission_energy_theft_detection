"""Single source of truth for the four fake Power BI reports that we register
as Unity Catalog external metadata objects with column-level lineage.

Imported by:
- notebooks/09_configure_external_lineage.py — registers external_metadata +
  external_lineage relationships in UC via the GA REST APIs.
- src/energy_theft_detection/backend/router.py — exposes
  GET /api/governance/external-lineage, falling back to this static list when
  the live UC read fails.
- scripts/generate_pbip.py — emits .pbip Power BI Project directories whose
  TMDL semantic models reference exactly the columns mapped here.

The dataclasses are deliberately framework-agnostic (no pydantic, no SDK)
so this file is import-safe from notebook contexts that don't have FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PBIReport:
    """One fake Power BI report registered as a UC external_metadata object.

    Attributes:
        name: Unique UC external_metadata identifier (snake_case).
        display: Human-readable display name shown in Catalog Explorer.
        entity_type: "dashboard" or "report" — matches Power BI's distinction.
        url: Realistic-looking app.powerbi.com URL that opens in a new tab.
        description: Markdown-ish multi-line description for the lineage sheet.
        columns: Column names exposed by the Power BI semantic model. These
            become the right-hand side of every ColumnEdge for this report.
    """

    name: str
    display: str
    entity_type: str  # "dashboard" | "report"
    url: str
    description: str
    columns: list[str]


@dataclass(frozen=True)
class ColumnEdge:
    """One UPSTREAM column-level lineage edge from a UC table to a PBI report.

    Both `source_column` and `target_column` are *column names*, not FQNs.
    `source_table` is the short table name (e.g. "anomaly_scores") — the
    bootstrap notebook fully-qualifies it with the runtime catalog/schema.
    """

    source_table: str
    source_column: str
    target_pbi: str
    target_column: str


# Stable fake GUIDs so the URLs don't churn between runs. These do NOT resolve
# to real Power BI tenants — they exist purely to make the lineage UI look
# realistic when an SA clicks through.
_PBI_WORKSPACE_GUID = "f4c93a18-2b7e-4f5d-9a31-8c6e2d4f1b09"


def _pbi_url(report_guid: str, slug: str) -> str:
    return (
        f"https://app.powerbi.com/groups/{_PBI_WORKSPACE_GUID}/reports/"
        f"{report_guid}/ReportSection?ctid=demo&experience=power-bi&slug={slug}"
    )


POWER_BI_REPORTS: list[PBIReport] = [
    PBIReport(
        name="pbi_revenue_protection_exec",
        display="Revenue Protection Executive Dashboard",
        entity_type="dashboard",
        url=_pbi_url("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", "revenue-protection-exec"),
        description=(
            "Susie Chambers's monthly board pack — total recovery vs target, "
            "regional split, detection precision KPI, and risk tier mix. "
            "Refreshed nightly from the Databricks SQL Warehouse via DirectQuery."
        ),
        columns=[
            "account_id",
            "high_risk_score",
            "risk_band",
            "recovered_gbp",
            "case_outcome",
            "region",
            "closed_at",
        ],
    ),
    PBIReport(
        name="pbi_field_ops_heatmap",
        display="Field Operations Heat Map",
        entity_type="report",
        url=_pbi_url("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e", "field-operations-heatmap"),
        description=(
            "Operational view for revenue-protection field teams — postcode-sector "
            "risk intensity, top open HIGH cases by region, and dispatch backlog. "
            "Used by area managers for daily standup."
        ),
        columns=[
            "account_id",
            "sector",
            "risk_intensity",
            "region",
            "case_status",
            "opened_at",
        ],
    ),
    PBIReport(
        name="pbi_customer_insights",
        display="Customer Insights & Theft Patterns",
        entity_type="report",
        url=_pbi_url("c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f", "customer-insights"),
        description=(
            "Analyst-facing pattern explorer — daily consumption traces for flagged "
            "accounts, comms-gap clustering, and risk-score distributions. "
            "Used by the data science team to refine new model features."
        ),
        columns=[
            "account_id",
            "daily_consumption",
            "comms_gap",
            "score",
            "fuel_type",
        ],
    ),
    PBIReport(
        name="pbi_regulatory_compliance",
        display="Regulatory Compliance Report (TDIS R0173)",
        entity_type="report",
        url=_pbi_url("d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f80", "regulatory-compliance"),
        description=(
            "Ofgem TDIS R0173 monthly compliance return — confirmed theft outcomes, "
            "tier-level precision, and case closure latency. Exported as the "
            "evidence pack for the quarterly regulatory submission."
        ),
        columns=[
            "case_id",
            "case_outcome",
            "tier_precision",
            "tier_recall",
            "closed_at",
            "model_version",
        ],
    ),
]


COLUMN_EDGES: list[ColumnEdge] = [
    # ─── Revenue Protection Exec Dashboard ─────────────────────────────────
    ColumnEdge("anomaly_scores", "account_id", "pbi_revenue_protection_exec", "account_id"),
    ColumnEdge("anomaly_scores", "composite_risk_score", "pbi_revenue_protection_exec", "high_risk_score"),
    ColumnEdge("anomaly_scores", "risk_tier", "pbi_revenue_protection_exec", "risk_band"),
    ColumnEdge("investigation_cases", "revenue_recovered_gbp", "pbi_revenue_protection_exec", "recovered_gbp"),
    ColumnEdge("investigation_cases", "outcome", "pbi_revenue_protection_exec", "case_outcome"),
    ColumnEdge("investigation_cases", "region", "pbi_revenue_protection_exec", "region"),
    ColumnEdge("investigation_cases", "closed_timestamp", "pbi_revenue_protection_exec", "closed_at"),
    # ─── Field Operations Heat Map ────────────────────────────────────────
    ColumnEdge("anomaly_scores", "account_id", "pbi_field_ops_heatmap", "account_id"),
    ColumnEdge("anomaly_scores", "postcode_sector", "pbi_field_ops_heatmap", "sector"),
    ColumnEdge("anomaly_scores", "composite_risk_score", "pbi_field_ops_heatmap", "risk_intensity"),
    ColumnEdge("investigation_cases", "region", "pbi_field_ops_heatmap", "region"),
    ColumnEdge("investigation_cases", "opened_timestamp", "pbi_field_ops_heatmap", "opened_at"),
    # ─── Customer Insights & Theft Patterns ───────────────────────────────
    ColumnEdge("smart_meter_reads", "account_id", "pbi_customer_insights", "account_id"),
    ColumnEdge("smart_meter_reads", "consumption_kwh", "pbi_customer_insights", "daily_consumption"),
    ColumnEdge("smart_meter_reads", "comms_gap_flag", "pbi_customer_insights", "comms_gap"),
    ColumnEdge("smart_meter_reads", "fuel_type", "pbi_customer_insights", "fuel_type"),
    ColumnEdge("anomaly_scores", "composite_risk_score", "pbi_customer_insights", "score"),
    # ─── Regulatory Compliance Report (TDIS R0173) ────────────────────────
    ColumnEdge("investigation_cases", "case_id", "pbi_regulatory_compliance", "case_id"),
    ColumnEdge("investigation_cases", "outcome", "pbi_regulatory_compliance", "case_outcome"),
    ColumnEdge("investigation_cases", "closed_timestamp", "pbi_regulatory_compliance", "closed_at"),
    ColumnEdge("model_performance_log", "precision_pct", "pbi_regulatory_compliance", "tier_precision"),
    ColumnEdge("model_performance_log", "recall_pct", "pbi_regulatory_compliance", "tier_recall"),
    ColumnEdge("model_performance_log", "model_version", "pbi_regulatory_compliance", "model_version"),
]


# Source table schemas — only the columns referenced by ColumnEdge. Used by:
# 1. tests/test_external_lineage_setup.py (drift detection — column rename in
#    notebook 04_batch_scoring would break the lineage definitions).
# 2. scripts/generate_pbip.py (emitting correctly-typed TMDL columns).
#
# Types are TMDL/Tabular types: "string", "int64", "double", "dateTime",
# "boolean". Kept tight so drift detection actually catches mismatches.
SOURCE_TABLE_SCHEMAS: dict[str, dict[str, str]] = {
    "smart_meter_reads": {
        "account_id": "string",
        "read_timestamp": "dateTime",
        "fuel_type": "string",
        "consumption_kwh": "double",
        "read_quality": "string",
        "comms_gap_flag": "boolean",
        "postcode": "string",
        "property_type": "string",
        "council_tax_band": "string",
    },
    "anomaly_scores": {
        "account_id": "string",
        "score_timestamp": "dateTime",
        "fuel_type": "string",
        "isolation_forest_score": "double",
        "lstm_deviation_score": "double",
        "cohort_deviation_score": "double",
        "comms_gap_count_30d": "int64",
        "consumption_drop_pct": "double",
        "composite_risk_score": "double",
        "risk_tier": "string",
        "postcode_sector": "string",
        "model_version": "string",
        "investigation_status": "string",
    },
    "investigation_cases": {
        "case_id": "string",
        "account_id": "string",
        "opened_timestamp": "dateTime",
        "investigator_id": "string",
        "llm_summary": "string",
        "field_dispatch_doc": "string",
        "outcome": "string",
        "revenue_recovered_gbp": "double",
        "closed_timestamp": "dateTime",
        "region": "string",
    },
    "model_performance_log": {
        "month": "dateTime",
        "model_version": "string",
        "risk_tier": "string",
        "precision_pct": "double",
        "recall_pct": "double",
        "f1_score": "double",
        "cases_scored": "int64",
        "cases_confirmed": "int64",
    },
}


# Marker properties dictionary applied to every external_metadata + lineage
# relationship registered by the bootstrap notebook. Lets the backend filter
# `external_metadata.list()` to *only* our four objects, and lets a future
# teardown script sweep test artifacts without touching unrelated objects.
DEMO_PROPERTIES: dict[str, str] = {
    "created_by": "energy-theft-end-to-end",
    "demo": "uki-gas-energy-theft-detection",
}


def upstream_tables_for(pbi_name: str) -> list[str]:
    """Return the unique upstream UC table names that feed a given PBI report.

    Drives the .pbip generator (one TMDL table per upstream) and the backend
    response so the frontend can group edges per source.
    """
    return sorted({e.source_table for e in COLUMN_EDGES if e.target_pbi == pbi_name})


def columns_used_from(pbi_name: str, source_table: str) -> list[str]:
    """Return the columns of `source_table` that are mapped into `pbi_name`."""
    return sorted({
        e.source_column
        for e in COLUMN_EDGES
        if e.target_pbi == pbi_name and e.source_table == source_table
    })


__all__ = [
    "PBIReport",
    "ColumnEdge",
    "POWER_BI_REPORTS",
    "COLUMN_EDGES",
    "SOURCE_TABLE_SCHEMAS",
    "DEMO_PROPERTIES",
    "upstream_tables_for",
    "columns_used_from",
]
