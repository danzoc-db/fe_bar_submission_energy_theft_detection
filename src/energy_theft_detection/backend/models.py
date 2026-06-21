"""Pydantic response models — persona-grouped.

No ORM (stateless app). All data comes from SQL Warehouse reads and is
mapped into these shapes before being returned to the frontend.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FuelType(str, Enum):
    ELECTRICITY = "electricity"
    GAS = "gas"


class InvestigationStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
    CONFIRMED_THEFT = "CONFIRMED_THEFT"


class CaseOutcome(str, Enum):
    THEFT_CONFIRMED = "THEFT_CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    PENDING = "PENDING"


# ---------------------------------------------------------------------------
# Susie's Dashboard Models
# ---------------------------------------------------------------------------

class DashboardKPIs(BaseModel):
    """KPI tile row on the executive dashboard — Susie's CFO story."""
    annual_theft_exposure_gbp: float = Field(description="~£323m, derived from RECCo x BG market share")
    exposure_vs_aop_pct: float = Field(description="Exposure / divisional AOP as %")
    revenue_recovered_ytd_gbp: float = Field(description="Live: sum of back-billed recoveries")
    recovery_rate_pct: float = Field(description="Recovered / pro-rata recoverable as %")
    detection_precision_pct: float = Field(description="Confirmed theft / total HIGH cases closed as %")
    recovery_target_gbp: float = Field(description="Annual recovery target (~£97m)")


class RiskHeatmapPoint(BaseModel):
    """Single postcode sector aggregation for the heatmap."""
    postcode_sector: str
    latitude: float
    longitude: float
    avg_composite_risk_score: float
    high_risk_count: int
    total_accounts: int


class TrendDataPoint(BaseModel):
    """Monthly trend of flagged accounts by risk tier."""
    month: str
    risk_tier: RiskTier
    count: int


class ScoreDistributionBin(BaseModel):
    """Single bin for the ML risk score histogram."""
    score_bin: float
    account_count: int


class FuelSplitItem(BaseModel):
    """Fuel type breakdown of anomaly flags."""
    fuel_type: FuelType
    count: int
    percentage: float


class RecoveryOpportunity(BaseModel):
    """£323M exposure broken down by ML confidence tier for the exec donut chart."""
    total_exposure_gbp: float = Field(description="Total annual theft exposure (~£323M)")
    recovered_ytd_gbp: float = Field(description="Revenue already recovered year-to-date")
    high_confidence_gbp: float = Field(description="Estimated annual loss from HIGH-tier accounts")
    high_confidence_accounts: int = Field(description="Number of HIGH-tier accounts")
    medium_confidence_gbp: float = Field(description="Estimated annual loss from MEDIUM-tier accounts")
    medium_confidence_accounts: int = Field(description="Number of MEDIUM-tier accounts")
    remaining_exposure_gbp: float = Field(description="Undetected/low-confidence remainder to £323M")


# ---------------------------------------------------------------------------
# Robbie's Investigation Models
# ---------------------------------------------------------------------------

class FlaggedAccountListItem(BaseModel):
    """Summary row in the flagged accounts table."""
    account_id: str
    postcode: str
    risk_tier: RiskTier
    composite_risk_score: float
    consumption_drop_pct: float
    comms_gap_count_30d: int
    fuel_type: FuelType
    investigation_status: InvestigationStatus


class MeterReadPoint(BaseModel):
    """Single half-hourly meter read for the time-series chart."""
    read_timestamp: datetime
    consumption_kwh: float
    read_quality: str


class AnomalySignals(BaseModel):
    """Five signal components for the radar chart."""
    isolation_forest_score: float
    lstm_deviation_score: float
    cohort_deviation_score: float
    comms_gap_normalised: float
    consumption_drop_normalised: float


class AccountDetail(BaseModel):
    """Full account view for the detail drawer."""
    account_id: str
    postcode: str
    region: str
    property_type: str
    council_tax_band: str
    fuel_type: FuelType
    risk_tier: RiskTier
    composite_risk_score: float
    consumption_drop_pct: float
    comms_gap_count_30d: int
    signals: AnomalySignals
    meter_reads: list[MeterReadPoint]
    cohort_avg_reads: list[MeterReadPoint]
    anomaly_onset: datetime | None = None


class InvestigationKPIs(BaseModel):
    """Operational KPI tiles for Robbie's investigation workbench."""
    open_high_cases: int = Field(description="HIGH-risk accounts awaiting investigation")
    open_medium_cases: int = Field(description="MEDIUM-risk accounts awaiting investigation")
    in_progress_cases: int = Field(description="Cases currently under investigation")
    closed_this_month: int = Field(description="Cases closed in the current calendar month")
    confirmed_theft_this_month: int = Field(description="Confirmed theft cases this month")
    precision_rate_pct: float = Field(description="Confirmed theft / total closed HIGH, all-time")
    avg_days_to_close: float = Field(description="Average days from open to close for closed cases")
    revenue_recovered_this_month_gbp: float = Field(description="Revenue recovered from cases closed this month")
    top_postcode_sector: str = Field(description="Postcode sector with most open HIGH cases")
    top_sector_count: int = Field(description="Number of HIGH cases in top sector")


class DailyBriefing(BaseModel):
    """AI-generated daily focus briefing for Robbie."""
    briefing: str
    actions: list[str] = []
    generated_at: str
    new_high_flags_24h: int = 0
    oldest_open_days: int = 0
    cluster_alert: str = ""


class LLMCaseSummary(BaseModel):
    """Bedrock-generated investigation summary."""
    account_id: str
    risk_level: str
    key_signals: list[str]
    recommended_action: str
    priority: str
    estimated_loss_per_month_gbp: Optional[float] = None
    raw_text: str


class DispatchReport(BaseModel):
    """Field investigation dispatch briefing for a flagged account."""
    case_reference: str
    generated_at: str
    priority: str
    account_id: str
    postcode: str
    region: str
    property_type: str
    council_tax_band: str
    fuel_type: str
    composite_risk_score: float
    consumption_drop_pct: float
    comms_gap_count_30d: int
    nearby_high_risk_count: int
    prior_theft_in_sector: bool
    narrative: str
    recommended_actions: list[str]
    evidence_checklist: list[str]
    safety_notes: list[str]
    estimated_monthly_loss_gbp: float


# ---------------------------------------------------------------------------
# Governance Models
# ---------------------------------------------------------------------------

class PIIFieldAccess(BaseModel):
    """One cell in the PII access matrix."""
    table_name: str
    field_name: str
    pii_tag: str
    regulatory_basis: str


class ColumnMetadata(BaseModel):
    """Column-level metadata from Unity Catalog INFORMATION_SCHEMA."""
    table_name: str
    column_name: str
    comment: str | None = None
    pii_tag: str | None = None
    regulatory_basis: str | None = None


class AIComponentRegistryItem(BaseModel):
    """Row in the AI component registry."""
    component_name: str
    component_type: str
    model_name: str
    pii_fields_accessed: list[str]
    last_run: str | None = None
    records_scored: int | None = None
    databricks_url: str | None = None


class AIGatewayAuditEntry(BaseModel):
    """Single AI Gateway audit log row."""
    request_timestamp: datetime
    endpoint_name: str
    request_user: str
    input_token_count: int
    output_token_count: int
    total_token_count: int
    cost_usd: float
    latency_ms: float
    status_code: int = 200
    guardrail_triggered: bool = False


class AuditSummary(BaseModel):
    """Aggregate stats for the audit panel header."""
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    error_count: int


class EndpointBudgetStatus(BaseModel):
    """Per-endpoint budget consumption and governance status."""
    endpoint_name: str
    display_name: str
    monthly_token_budget: int
    monthly_usd_budget: float
    used_tokens_mtd: int
    used_cost_usd_mtd: float
    token_budget_pct: float
    usd_budget_pct: float
    rate_limit_endpoint_calls_per_min: int
    rate_limit_user_calls_per_min: int
    blocked_request_count_mtd: int = 0


class BudgetAnomalyAlert(BaseModel):
    """Daily token-spike alert for governance and cost control."""
    active: bool
    latest_day: str | None = None
    latest_tokens: int = 0
    trailing_avg_tokens: float = 0.0
    spike_ratio: float = 0.0
    message: str = ""


class FinOpsSummary(BaseModel):
    """Unified AI Gateway FinOps/governance summary for the UI."""
    total_cost_usd_mtd: float
    total_tokens_mtd: int
    total_blocked_requests_mtd: int
    cost_per_investigation_usd: float
    investigations_mtd: int
    endpoint_budgets: list[EndpointBudgetStatus]
    anomaly_alert: BudgetAnomalyAlert


class ModelPerformancePoint(BaseModel):
    """Monthly model performance metric."""
    month: str
    model_version: str
    risk_tier: RiskTier
    precision_pct: float
    recall_pct: float
    f1_score: float
    cases_scored: int
    cases_confirmed: int


# ---------------------------------------------------------------------------
# External Lineage — fake Power BI reports downstream of UC tables
# ---------------------------------------------------------------------------

class ExternalLineageNode(BaseModel):
    """One Power BI report registered as a UC external_metadata object."""
    name: str = Field(description="Unique snake_case identifier — matches the UC external_metadata name.")
    display: str
    system_type: str = "POWER_BI"
    entity_type: str = Field(description='"dashboard" or "report".')
    url: str
    description: str
    columns: list[str]


class ExternalLineageEdge(BaseModel):
    """One UPSTREAM column-level edge from a UC table to a PBI report column."""
    source_table: str = Field(description="Short UC table name — matches LineageDAG node IDs in the frontend.")
    source_column: str
    target_external: str = Field(description="External metadata name (matches ExternalLineageNode.name).")
    target_column: str


class ExternalLineageResponse(BaseModel):
    """GET /api/governance/external-lineage payload."""
    nodes: list[ExternalLineageNode]
    edges: list[ExternalLineageEdge]
    source: Literal["live", "fallback"] = Field(
        description='"live" when read from Unity Catalog via external_metadata API; "fallback" when served from the static shared module.'
    )


# ---------------------------------------------------------------------------
# Genie Models
# ---------------------------------------------------------------------------

class GenieMessage(BaseModel):
    """A message in a Genie conversation."""
    role: str  # 'user' | 'assistant'
    content: str
    sql: Optional[str] = None
    data: Optional[list[dict[str, object]]] = None
    conversation_id: Optional[str] = None
    columns: Optional[list[str]] = None

    @field_validator("content", mode="before")
    @classmethod
    def _coerce_content_to_str(cls, v: object) -> str:
        """Genie API may return error dicts instead of strings for content.
        Coerce to string so Pydantic never rejects the value."""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return v.get("error", None) or str(v)
        return str(v)


class GenieConversation(BaseModel):
    """Genie conversation state."""
    conversation_id: str
    messages: list[GenieMessage]


# ---------------------------------------------------------------------------
# Agent Atlas — Board Report Models
# ---------------------------------------------------------------------------

class AgentStep(BaseModel):
    """One step in the multi-agent orchestration trace."""
    agent: str  # "supervisor" | "genie" | "gemini" | "bedrock"
    question: str
    answer: str
    data: Optional[list[dict[str, object]]] = None
    sql: Optional[str] = None
    duration_ms: int = 0


class BoardReportKPI(BaseModel):
    """Single KPI highlight in the board report."""
    label: str
    value: str
    trend: str = ""
    context: str = ""


class BoardReport(BaseModel):
    """Agent Atlas board report — assembled by Agent Bricks MAS (Genie + Gemini + Bedrock)."""
    report_title: str
    period: str
    generated_at: str
    executive_summary: str
    revenue_protection_overview: str
    regional_analysis: str
    market_intelligence: str = ""
    model_performance_summary: str
    recommendations: list[str]
    kpi_highlights: list[BoardReportKPI] = []
    agent_trace: list[AgentStep] = []
    genie_questions_asked: int = 0
    bedrock_tokens_used: int = 0
    gemini_tokens_used: int = 0
