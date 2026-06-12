"""API routes — persona-grouped.

Susie's routes:  /api/dashboard/*
Robbie's routes: /api/investigation/*
Governance:      /api/governance/*
Genie:           /api/genie/*
LLM:             /api/llm/*

Each route queries the SQL Warehouse first, with graceful defaults when
SQL_WAREHOUSE_ID is not configured.
"""

from __future__ import annotations

import time as _time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .._metadata import api_prefix
from .logger import logger
from .models import (
    AgentStep,
    AIComponentRegistryItem,
    AIGatewayAuditEntry,
    AccountDetail,
    AuditSummary,
    AnomalySignals,
    BoardReport,
    BoardReportKPI,
    ColumnMetadata,
    DailyBriefing,
    DashboardKPIs,
    DispatchReport,
    ExternalLineageEdge,
    ExternalLineageNode,
    ExternalLineageResponse,
    FlaggedAccountListItem,
    FuelSplitItem,
    FuelType,
    GenieConversation,
    GenieMessage,
    InvestigationKPIs,
    InvestigationStatus,
    LLMCaseSummary,
    MeterReadPoint,
    ModelPerformancePoint,
    PIIFieldAccess,
    RecoveryOpportunity,
    RiskHeatmapPoint,
    RiskTier,
    ScoreDistributionBin,
    TrendDataPoint,
)
from .config import AppConfig
from .sql_client import SQLClient

api = APIRouter(prefix=api_prefix)


def _sql(request: Request) -> SQLClient | None:
    return getattr(request.app.state, "sql_client", None)


def _workspace_host(db: SQLClient) -> str:
    """Clean workspace host URL from the SDK config (strips query params like ?o=)."""
    raw = str(db._client.config.host or "")
    return raw.split("?")[0].rstrip("/")


def _config(request: Request) -> AppConfig | None:
    return getattr(request.app.state, "config", None)


_MODEL_KEY_ENDPOINTS = {
    "bedrock": "ai_gateway_endpoint",
    "openai": "openai_gateway_endpoint",
    "llama": "llama_gateway_endpoint",
}


def _resolve_ai_endpoint(request: Request, config: AppConfig | None) -> str:
    """Read X-Model-Key header and return the matching AI Gateway endpoint name."""
    model_key = request.headers.get("x-model-key", "bedrock")
    attr = _MODEL_KEY_ENDPOINTS.get(model_key, "ai_gateway_endpoint")
    return getattr(config, attr, "energy-theft-bedrock-gateway") if config else ""


# ---------------------------------------------------------------------------
# In-memory TTL cache for SQL-heavy endpoints
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 5400  # seconds — 1.5 hours for demo stability

def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (_time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_get_ttl(key: str, ttl_seconds: int) -> Any | None:
    """Cache lookup with a per-key TTL override (default cache uses _CACHE_TTL)."""
    entry = _cache.get(key)
    if entry and (_time.monotonic() - entry[0]) < ttl_seconds:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (_time.monotonic(), value)


_CLOSE_AFFECTED_KEYS = [
    "dashboard_kpis",
    "investigation_kpis",
    "dashboard_recovery_opportunity",
]


def _optimistic_cache_update(
    outcome: str,
    recovered: float | None,
) -> None:
    """Optimistically patch cached KPIs with the known close delta so the
    next frontend read is instant — no SQL round-trip required.

    The background thread will eventually re-warm the cache with real data,
    but the user sees the change immediately.
    """
    from .models import InvestigationKPIs, DashboardKPIs

    is_theft = outcome == "THEFT_CONFIRMED"
    rec_amt = recovered or 0.0

    inv = _cache_get("investigation_kpis")
    if isinstance(inv, InvestigationKPIs):
        updated = inv.model_copy(update={
            "open_high_cases": max(inv.open_high_cases - 1, 0),
            "closed_this_month": inv.closed_this_month + 1,
            "confirmed_theft_this_month": inv.confirmed_theft_this_month + (1 if is_theft else 0),
            "revenue_recovered_this_month_gbp": inv.revenue_recovered_this_month_gbp + rec_amt,
            "precision_rate_pct": round(
                (inv.confirmed_theft_this_month + (1 if is_theft else 0))
                * 100.0
                / max(inv.closed_this_month + 1, 1),
                1,
            ),
        })
        _cache_set("investigation_kpis", updated)

    dash = _cache_get("dashboard_kpis")
    if isinstance(dash, DashboardKPIs):
        new_ytd = dash.revenue_recovered_ytd_gbp + rec_amt
        updated_dash = dash.model_copy(update={
            "revenue_recovered_ytd_gbp": new_ytd,
            "recovery_rate_pct": round(
                new_ytd * 100.0 / max(dash.recovery_target_gbp, 1), 1
            ),
        })
        _cache_set("dashboard_kpis", updated_dash)

    stale_keys = [k for k in _cache if k.startswith("flagged_accounts:")]
    for k in stale_keys:
        _cache.pop(k, None)


def _invalidate_and_rewarm(db: "SQLClient") -> None:
    """Full cache invalidation + SQL re-warm. Runs in background thread
    after the SQL writes complete so the cache converges to truth."""
    import threading

    for key in _CLOSE_AFFECTED_KEYS:
        _cache.pop(key, None)
    stale_keys = [k for k in _cache if k.startswith("flagged_accounts:")]
    for k in stale_keys:
        _cache.pop(k, None)

    def _rewarm():
        try:
            _warm_cache(db)
        except Exception as e:
            logger.warning(f"Background re-warm after close failed: {e}")

    threading.Thread(target=_rewarm, daemon=True).start()


# ---------------------------------------------------------------------------
# Schema access probe — retries on transient failures (cold warehouse, etc.)
# ---------------------------------------------------------------------------

_schema_access_ok: bool = False
_schema_access_error: str = ""
_schema_access_last_check: float = 0.0
_SCHEMA_RECHECK_COOLDOWN = 30.0  # seconds between re-checks on failure


def _check_schema_access(db: "SQLClient", *, retries: int = 3, backoff: float = 10.0) -> tuple[bool, str]:
    """Probe SELECT access on anomaly_scores, retrying on transient errors.

    Returns (True, "") on success, or (False, diagnostic_message) on failure.
    Updates module-level state so /health and /readiness can report it.
    """
    global _schema_access_ok, _schema_access_error, _schema_access_last_check
    import time as _t

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            db.execute("SELECT 1 FROM anomaly_scores LIMIT 1")
            _schema_access_ok = True
            _schema_access_error = ""
            _schema_access_last_check = _t.monotonic()
            return True, ""
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            is_permission = any(kw in err_str for kw in ("permission", "denied", "grant", "privilege", "access"))
            if is_permission:
                break
            if attempt < retries:
                logger.warning(f"Schema probe attempt {attempt}/{retries} failed (transient): {e}")
                _t.sleep(backoff * attempt)

    catalog = db.resolve_catalog()
    schema = db._schema
    sp_id = ""
    try:
        sp_id = str(db._client.config.client_id or "")
    except Exception:
        pass

    err_type = type(last_err).__name__ if last_err else "Unknown"
    err_msg = str(last_err) if last_err else "No details"

    is_permission = any(kw in err_msg.lower() for kw in ("permission", "denied", "grant", "privilege", "access"))

    is_warehouse = "permission to use the sql warehouse" in err_msg.lower()

    if is_warehouse:
        hint = (
            f"Warehouse access denied — the app's service principal does not have "
            f"CAN_USE on the SQL Warehouse.\n"
            f"  Fix: run  python3 scripts/verify_app_permissions.py --profile <profile> --fix\n"
            f"  Or grant CAN_USE on the warehouse to SP {sp_id} in the workspace UI."
        )
    elif is_permission:
        principal = f"`{sp_id}`" if sp_id else "<app_service_principal_client_id>"
        hint = (
            f"Schema access denied — the app's service principal cannot query "
            f"{catalog}.{schema}.\n"
            f"  Fix: run  python3 scripts/verify_app_permissions.py --profile <profile> --fix\n"
            f"  Or: GRANT USE SCHEMA, SELECT ON SCHEMA {catalog}.{schema} TO {principal}"
        )
    else:
        hint = (
            f"Schema probe failed after {retries} attempts — likely a transient issue "
            f"(cold warehouse, timeout, network).\n"
            f"  Error: {err_type}: {err_msg}\n"
            f"  The app will automatically retry on the next readiness check."
        )

    _schema_access_ok = False
    _schema_access_error = hint
    _schema_access_last_check = _t.monotonic()
    return False, hint


def _try_warm_cache(db: "SQLClient") -> None:
    """Re-warm the cache if it's mostly empty (self-heal after cold start)."""
    critical_keys = ["dashboard_kpis", "investigation_kpis", "model_performance"]
    populated = sum(1 for k in critical_keys if _cache_get(k) is not None)
    if populated < len(critical_keys):
        logger.info("Cache incomplete — re-warming after successful readiness check")
        _warm_cache(db)


def _maybe_self_heal(db: "SQLClient") -> bool:
    """If schema_access was previously failed, re-probe and warm cache on success.

    Called from data endpoints when they get SQL errors so the next request succeeds.
    Returns True if self-heal succeeded (caller should retry its query).
    """
    if _schema_access_ok:
        return False
    elapsed = _time.monotonic() - _schema_access_last_check
    if elapsed < _SCHEMA_RECHECK_COOLDOWN:
        return False
    ok, _ = _check_schema_access(db, retries=1, backoff=0)
    if ok:
        _try_warm_cache(db)
        return True
    return False


def _warm_cache(db: "SQLClient") -> None:
    """Pre-execute all dashboard SQL queries at startup so the first user
    request is always served from the in-memory cache."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .sql_client import SQLClient

    queries: dict[str, str] = {
        "dashboard_kpis": """
            SELECT
              ROUND(COALESCE(SUM(revenue_recovered_gbp), 0), 0) AS recovered,
              COUNT_IF(outcome = 'THEFT_CONFIRMED') AS confirmed,
              COUNT_IF(outcome IS NOT NULL) AS closed
            FROM investigation_cases
            WHERE closed_timestamp >= DATE_TRUNC('year', CURRENT_DATE())
        """,
        "dashboard_heatmap": """
            SELECT
              a.postcode_sector,
              ROUND(AVG(a.composite_risk_score), 4) AS avg_score,
              COUNT(CASE WHEN a.risk_tier='HIGH' THEN 1 END) AS high_count,
              COUNT(*) AS total,
              ROUND(AVG(p.latitude), 4) AS latitude,
              ROUND(AVG(p.longitude), 4) AS longitude
            FROM anomaly_scores a
            JOIN property_reference p ON a.account_id = p.account_id
            GROUP BY a.postcode_sector
            HAVING COUNT(CASE WHEN a.risk_tier='HIGH' THEN 1 END) > 0
            ORDER BY avg_score DESC
            LIMIT 50
        """,
        "dashboard_score_distribution": """
            SELECT
              FLOOR(composite_risk_score / 10) * 10 AS score_bin,
              COUNT(*) AS account_count
            FROM anomaly_scores
            GROUP BY score_bin
            ORDER BY score_bin
        """,
        "dashboard_recovery_opportunity_tiers": """
            SELECT risk_tier, COUNT(*) AS accounts FROM anomaly_scores GROUP BY risk_tier
        """,
        "dashboard_recovery_opportunity_recovered": """
            SELECT ROUND(COALESCE(SUM(revenue_recovered_gbp), 0), 0) AS recovered
            FROM investigation_cases
            WHERE closed_timestamp >= DATE_TRUNC('year', CURRENT_DATE())
        """,
        "investigation_kpis_anomaly": """
            SELECT
              COUNT_IF(risk_tier = 'HIGH' AND investigation_status = 'OPEN') AS open_high,
              COUNT_IF(risk_tier = 'MEDIUM' AND investigation_status = 'OPEN') AS open_medium,
              COUNT_IF(investigation_status = 'IN_PROGRESS') AS in_progress
            FROM anomaly_scores
        """,
        "investigation_kpis_cases": """
            SELECT
              COUNT_IF(closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE())) AS closed_mo,
              COUNT_IF(outcome = 'THEFT_CONFIRMED' AND closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE())) AS confirmed_mo,
              COUNT_IF(outcome = 'THEFT_CONFIRMED') AS confirmed_all,
              COUNT_IF(outcome IS NOT NULL) AS closed_all,
              ROUND(COALESCE(AVG(DATEDIFF(COALESCE(closed_timestamp, CURRENT_TIMESTAMP()), opened_timestamp)), 0), 1) AS avg_days,
              ROUND(COALESCE(SUM(CASE WHEN closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE()) THEN revenue_recovered_gbp ELSE 0 END), 0), 0) AS recovered_mo
            FROM investigation_cases
        """,
        "investigation_kpis_top_sector": """
            SELECT postcode_sector, COUNT(*) AS cnt
            FROM anomaly_scores
            WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN'
            GROUP BY postcode_sector
            ORDER BY cnt DESC
            LIMIT 1
        """,
        "model_performance": """
            SELECT
              DATE_FORMAT(month, 'yyyy-MM') AS month_str,
              model_version, risk_tier,
              precision_pct, recall_pct, f1_score,
              cases_scored, cases_confirmed
            FROM model_performance_log
            ORDER BY month, risk_tier
        """,
        "dashboard_trend": """
            SELECT
              DATE_FORMAT(month, 'yyyy-MM') AS month_str,
              risk_tier,
              cases_scored AS count
            FROM model_performance_log
            ORDER BY month, risk_tier
        """,
        "dashboard_fuel_split": """
            SELECT fuel_type, COUNT(*) AS cnt
            FROM anomaly_scores
            WHERE risk_tier IN ('HIGH', 'MEDIUM')
            GROUP BY fuel_type
        """,
    }

    results: dict[str, Any] = {}

    def _run(key: str, sql: str):
        try:
            return key, db.execute(sql)
        except Exception as e:
            logger.warning(f"Cache warm query failed for {key}: {e}")
            return key, None

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_run, k, v): k for k, v in queries.items()}
        for f in as_completed(futures):
            key, rows = f.result()
            results[key] = rows

    _build_warm_cache(results)


def _build_warm_cache(results: dict[str, Any]) -> None:
    """Transform raw SQL results into cached response objects."""
    from datetime import date
    from .models import (
        DashboardKPIs, RiskHeatmapPoint, ScoreDistributionBin,
        RecoveryOpportunity, InvestigationKPIs,
        TrendDataPoint, FuelSplitItem,
        ModelPerformancePoint, RiskTier, FuelType,
    )

    rows = results.get("dashboard_kpis")
    if rows:
        try:
            r = rows[0]
            recovered_ytd = float(r.get("recovered", 0) or 0)
            confirmed = int(r.get("confirmed", 0) or 0)
            closed = int(r.get("closed", 0) or 0)
            precision_pct = round(confirmed * 100.0 / closed, 1) if closed > 0 else 0.0
            months = max(1, (date.today().month))
            pro_rata = ANNUAL_THEFT_EXPOSURE * (months / 12.0)
            recovery_rate = round(recovered_ytd * 100.0 / pro_rata, 1) if pro_rata > 0 else 0.0
            if recovered_ytd > 0:
                _cache_set("dashboard_kpis", DashboardKPIs(
                    annual_theft_exposure_gbp=ANNUAL_THEFT_EXPOSURE,
                    exposure_vs_aop_pct=round(ANNUAL_THEFT_EXPOSURE / DIVISIONAL_AOP * 100, 0),
                    revenue_recovered_ytd_gbp=recovered_ytd,
                    recovery_rate_pct=recovery_rate,
                    detection_precision_pct=precision_pct,
                    recovery_target_gbp=RECOVERY_TARGET,
                ))
        except Exception as e:
            logger.warning(f"Cache warm build failed for dashboard_kpis: {e}")

    rows = results.get("dashboard_heatmap")
    if rows:
        try:
            _cache_set("dashboard_heatmap", [
                RiskHeatmapPoint(
                    postcode_sector=r["postcode_sector"],
                    latitude=float(r["latitude"]) if r.get("latitude") else 51.5,
                    longitude=float(r["longitude"]) if r.get("longitude") else -0.1,
                    avg_composite_risk_score=float(r["avg_score"]),
                    high_risk_count=int(r["high_count"]),
                    total_accounts=int(r["total"]),
                )
                for r in rows
            ])
        except Exception as e:
            logger.warning(f"Cache warm build failed for dashboard_heatmap: {e}")

    rows = results.get("dashboard_score_distribution")
    if rows:
        try:
            _cache_set("dashboard_score_distribution", [
                ScoreDistributionBin(
                    score_bin=float(r["score_bin"]),
                    account_count=int(r["account_count"]),
                )
                for r in rows
            ])
        except Exception as e:
            logger.warning(f"Cache warm build failed for dashboard_score_distribution: {e}")

    tier_rows = results.get("dashboard_recovery_opportunity_tiers")
    rec_rows = results.get("dashboard_recovery_opportunity_recovered")
    if tier_rows:
        try:
            high_accounts = medium_accounts = total_scored = 0
            for r in tier_rows:
                accts = int(r.get("accounts", 0) or 0)
                tier = r["risk_tier"]
                total_scored += accts
                if tier == "HIGH":
                    high_accounts = accts
                elif tier == "MEDIUM":
                    medium_accounts = accts
            recovered_ytd = float(rec_rows[0].get("recovered", 0) or 0) if rec_rows else 0.0
            if total_scored > 0:
                high_pct = high_accounts / total_scored
                medium_pct = medium_accounts / total_scored
                high_gbp = min(round(high_pct * HIGH_CONCENTRATION * ANNUAL_THEFT_EXPOSURE, 0), ANNUAL_THEFT_EXPOSURE * 0.40)
                medium_gbp = min(round(medium_pct * MEDIUM_CONCENTRATION * ANNUAL_THEFT_EXPOSURE, 0), ANNUAL_THEFT_EXPOSURE * 0.30)
                remaining = max(0.0, ANNUAL_THEFT_EXPOSURE - recovered_ytd - high_gbp - medium_gbp)
                _cache_set("dashboard_recovery_opportunity", RecoveryOpportunity(
                    total_exposure_gbp=ANNUAL_THEFT_EXPOSURE,
                    recovered_ytd_gbp=recovered_ytd,
                    high_confidence_gbp=high_gbp,
                    high_confidence_accounts=high_accounts,
                    medium_confidence_gbp=medium_gbp,
                    medium_confidence_accounts=medium_accounts,
                    remaining_exposure_gbp=remaining,
                ))
        except Exception as e:
            logger.warning(f"Cache warm build failed for dashboard_recovery_opportunity: {e}")

    anomaly_rows = results.get("investigation_kpis_anomaly")
    case_rows_inv = results.get("investigation_kpis_cases")
    sector_rows = results.get("investigation_kpis_top_sector")
    if anomaly_rows and case_rows_inv:
        try:
            ar = anomaly_rows[0] if anomaly_rows else {}
            cr = case_rows_inv[0] if case_rows_inv else {}
            closed_all = int(cr.get("closed_all", 0) or 0)
            confirmed_all = int(cr.get("confirmed_all", 0) or 0)
            precision = round(confirmed_all * 100.0 / closed_all, 1) if closed_all > 0 else 0.0
            top_sector = sector_rows[0]["postcode_sector"] if sector_rows else "N/A"
            top_count = int(sector_rows[0]["cnt"]) if sector_rows else 0
            _cache_set("investigation_kpis", InvestigationKPIs(
                open_high_cases=int(ar.get("open_high", 0) or 0),
                open_medium_cases=int(ar.get("open_medium", 0) or 0),
                in_progress_cases=int(ar.get("in_progress", 0) or 0),
                closed_this_month=int(cr.get("closed_mo", 0) or 0),
                confirmed_theft_this_month=int(cr.get("confirmed_mo", 0) or 0),
                precision_rate_pct=precision,
                avg_days_to_close=float(cr.get("avg_days", 0) or 0),
                revenue_recovered_this_month_gbp=float(cr.get("recovered_mo", 0) or 0),
                top_postcode_sector=top_sector,
                top_sector_count=top_count,
            ))
        except Exception as e:
            logger.warning(f"Cache warm build failed for investigation_kpis: {e}")

    rows = results.get("model_performance")
    if rows:
        try:
            built = [
                ModelPerformancePoint(
                    month=r["month_str"],
                    model_version=r["model_version"],
                    risk_tier=RiskTier(r["risk_tier"]),
                    precision_pct=float(r["precision_pct"]),
                    recall_pct=float(r["recall_pct"]),
                    f1_score=float(r["f1_score"]),
                    cases_scored=int(r["cases_scored"]),
                    cases_confirmed=int(r["cases_confirmed"]),
                )
                for r in rows
            ]
            _cache_set("model_performance", built)
        except Exception as e:
            logger.warning(f"Cache warm build failed for model_performance: {e}")

    rows = results.get("dashboard_trend")
    if rows:
        try:
            _cache_set("dashboard_trend", [
                TrendDataPoint(
                    month=r["month_str"],
                    risk_tier=RiskTier(r["risk_tier"]),
                    count=int(r["count"]),
                )
                for r in rows
            ])
        except Exception as e:
            logger.warning(f"Cache warm build failed for dashboard_trend: {e}")

    rows = results.get("dashboard_fuel_split")
    if rows:
        try:
            total = sum(int(r["cnt"]) for r in rows) or 1
            _cache_set("dashboard_fuel_split", [
                FuelSplitItem(
                    fuel_type=FuelType(r["fuel_type"]),
                    count=int(r["cnt"]),
                    percentage=round(int(r["cnt"]) / total * 100, 1),
                )
                for r in rows
            ])
        except Exception as e:
            logger.warning(f"Cache warm build failed for dashboard_fuel_split: {e}")


# ---------------------------------------------------------------------------
# Susie's Executive Dashboard
# ---------------------------------------------------------------------------

ANNUAL_THEFT_EXPOSURE = 323_000_000.0
DIVISIONAL_AOP = 163_000_000.0
RECOVERY_TARGET = 97_000_000.0


@api.get(
    "/dashboard/kpis",
    response_model=DashboardKPIs,
    operation_id="getDashboardKPIs",
)
async def get_dashboard_kpis(request: Request):
    """KPI tiles: exposure, AOP ratio, recovered YTD, recovery rate, precision."""
    cached = _cache_get("dashboard_kpis")
    if cached is not None:
        return cached

    from datetime import date

    months_elapsed = max(date.today().month, 1)
    pro_rata_recoverable = ANNUAL_THEFT_EXPOSURE * (months_elapsed / 12.0)

    recovered_ytd = 0.0
    precision_pct = 0.0
    from_sql = False

    db = _sql(request)
    if db:
        for _attempt in range(2):
            try:
                rows = db.execute("""
                    SELECT
                      ROUND(COALESCE(SUM(revenue_recovered_gbp), 0), 0) AS recovered,
                      COUNT_IF(outcome = 'THEFT_CONFIRMED') AS confirmed,
                      COUNT_IF(outcome IS NOT NULL) AS closed
                    FROM investigation_cases
                    WHERE closed_timestamp >= DATE_TRUNC('year', CURRENT_DATE())
                """)
                if rows:
                    r = rows[0]
                    recovered_ytd = float(r.get("recovered", 0) or 0)
                    confirmed = int(r.get("confirmed", 0) or 0)
                    closed = int(r.get("closed", 0) or 0)
                    precision_pct = round(confirmed * 100.0 / closed, 1) if closed > 0 else 0.0
                    from_sql = recovered_ytd > 0
                break
            except Exception as e:
                logger.warning(f"Dashboard KPIs query failed (using defaults): {e}")
                if _attempt == 0 and _maybe_self_heal(db):
                    cached = _cache_get("dashboard_kpis")
                    if cached is not None:
                        return cached
                    continue
                break

    if recovered_ytd == 0:
        recovered_ytd = 34_600_000.0  # CY2026 Q1 recovery (ahead of £24.25M linear Q1 pace)
        precision_pct = 72.0
    recovery_rate = round(recovered_ytd * 100.0 / pro_rata_recoverable, 1) if pro_rata_recoverable > 0 else 0.0

    result = DashboardKPIs(
        annual_theft_exposure_gbp=ANNUAL_THEFT_EXPOSURE,
        exposure_vs_aop_pct=round(ANNUAL_THEFT_EXPOSURE / DIVISIONAL_AOP * 100, 0),
        revenue_recovered_ytd_gbp=recovered_ytd,
        recovery_rate_pct=recovery_rate,
        detection_precision_pct=precision_pct,
        recovery_target_gbp=RECOVERY_TARGET,
    )
    if from_sql:
        _cache_set("dashboard_kpis", result)
    return result


@api.get(
    "/dashboard/heatmap",
    response_model=list[RiskHeatmapPoint],
    operation_id="getDashboardHeatmap",
)
async def get_dashboard_heatmap(request: Request):
    """Postcode sector risk aggregation for the UK heatmap."""
    cached = _cache_get("dashboard_heatmap")
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        try:
            rows = db.execute("""
                SELECT
                  a.postcode_sector,
                  ROUND(AVG(a.composite_risk_score), 4) AS avg_score,
                  COUNT(CASE WHEN a.risk_tier='HIGH' THEN 1 END) AS high_count,
                  COUNT(*) AS total,
                  ROUND(AVG(p.latitude), 4) AS latitude,
                  ROUND(AVG(p.longitude), 4) AS longitude
                FROM anomaly_scores a
                JOIN property_reference p ON a.account_id = p.account_id
                GROUP BY a.postcode_sector
                HAVING COUNT(CASE WHEN a.risk_tier='HIGH' THEN 1 END) > 0
                ORDER BY avg_score DESC
                LIMIT 50
            """)
            result = [
                RiskHeatmapPoint(
                    postcode_sector=r["postcode_sector"],
                    latitude=float(r["latitude"]) if r.get("latitude") else 51.5,
                    longitude=float(r["longitude"]) if r.get("longitude") else -0.1,
                    avg_composite_risk_score=float(r["avg_score"]),
                    high_risk_count=int(r["high_count"]),
                    total_accounts=int(r["total"]),
                )
                for r in rows
            ]
            _cache_set("dashboard_heatmap", result)
            return result
        except Exception as e:
            logger.warning(f"Dashboard heatmap query failed: {e}")
    return []


@api.get(
    "/dashboard/trend",
    response_model=list[TrendDataPoint],
    operation_id="getDashboardTrend",
)
async def get_dashboard_trend(request: Request):
    """12-month rolling flagged accounts by risk tier from model performance log."""
    cached = _cache_get("dashboard_trend")
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        try:
            rows = db.execute("""
                SELECT
                  DATE_FORMAT(month, 'yyyy-MM') AS month_str,
                  risk_tier,
                  cases_scored AS count
                FROM model_performance_log
                ORDER BY month, risk_tier
            """)
            result = [
                TrendDataPoint(
                    month=r["month_str"],
                    risk_tier=RiskTier(r["risk_tier"]),
                    count=int(r["count"]),
                )
                for r in rows
            ]
            _cache_set("dashboard_trend", result)
            return result
        except Exception as e:
            logger.warning(f"Dashboard trend query failed: {e}")
    return []


@api.get(
    "/dashboard/fuel-split",
    response_model=list[FuelSplitItem],
    operation_id="getDashboardFuelSplit",
)
async def get_dashboard_fuel_split(request: Request):
    """Current anomaly flag count by fuel type (HIGH + MEDIUM)."""
    cached = _cache_get("dashboard_fuel_split")
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        try:
            rows = db.execute("""
                SELECT
                  fuel_type,
                  COUNT(*) AS cnt
                FROM anomaly_scores
                WHERE risk_tier IN ('HIGH', 'MEDIUM')
                GROUP BY fuel_type
            """)
            total = sum(int(r["cnt"]) for r in rows) or 1
            result = [
                FuelSplitItem(
                    fuel_type=FuelType(r["fuel_type"]),
                    count=int(r["cnt"]),
                    percentage=round(int(r["cnt"]) / total * 100, 1),
                )
                for r in rows
            ]
            _cache_set("dashboard_fuel_split", result)
            return result
        except Exception as e:
            logger.warning(f"Dashboard fuel split query failed: {e}")
    return [
        FuelSplitItem(fuel_type=FuelType.ELECTRICITY, count=180, percentage=60.0),
        FuelSplitItem(fuel_type=FuelType.GAS, count=122, percentage=40.0),
    ]


@api.get(
    "/dashboard/score-distribution",
    response_model=list[ScoreDistributionBin],
    operation_id="getDashboardScoreDistribution",
)
async def get_dashboard_score_distribution(request: Request):
    """Binned composite risk score histogram for the executive dashboard."""
    cached = _cache_get("dashboard_score_distribution")
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        try:
            rows = db.execute("""
                SELECT
                  FLOOR(composite_risk_score * 20) / 20 AS score_bin,
                  COUNT(*) AS account_count
                FROM anomaly_scores
                GROUP BY 1
                ORDER BY 1
            """)
            result = [
                ScoreDistributionBin(
                    score_bin=float(r["score_bin"]),
                    account_count=int(r["account_count"]),
                )
                for r in rows
            ]
            _cache_set("dashboard_score_distribution", result)
            return result
        except Exception as e:
            logger.warning(f"Dashboard score distribution query failed: {e}")
    return []


BG_DOMESTIC_CUSTOMERS = 7_500_000.0
HIGH_CONCENTRATION = 20.0
MEDIUM_CONCENTRATION = 5.0


@api.get(
    "/dashboard/recovery-opportunity",
    response_model=RecoveryOpportunity,
    operation_id="getDashboardRecoveryOpportunity",
)
async def get_dashboard_recovery_opportunity(request: Request):
    """Revenue recovery opportunity by ML confidence tier for the exec donut chart.

    Projects the ML risk-tier distribution from the scored base to the full
    BG domestic customer population. HIGH-risk accounts represent
    disproportionately more theft per account (Pareto concentration), so
    their share of the £323M exposure is amplified by a concentration factor.
    """
    cached = _cache_get("dashboard_recovery_opportunity")
    if cached is not None:
        return cached

    recovered_ytd = 0.0
    high_accounts = 0
    medium_accounts = 0
    total_scored = 0
    from_sql = False

    db = _sql(request)
    if db:
        try:
            tier_rows = db.execute("""
                SELECT
                  risk_tier,
                  COUNT(*) AS accounts
                FROM anomaly_scores
                GROUP BY risk_tier
            """)
            for r in tier_rows:
                accts = int(r.get("accounts", 0) or 0)
                tier = r["risk_tier"]
                total_scored += accts
                if tier == "HIGH":
                    high_accounts = accts
                elif tier == "MEDIUM":
                    medium_accounts = accts

            rec_rows = db.execute("""
                SELECT ROUND(COALESCE(SUM(revenue_recovered_gbp), 0), 0) AS recovered
                FROM investigation_cases
                WHERE closed_timestamp >= DATE_TRUNC('year', CURRENT_DATE())
            """)
            if rec_rows:
                recovered_ytd = float(rec_rows[0].get("recovered", 0) or 0)

            from_sql = total_scored > 0
        except Exception as e:
            logger.warning(f"Recovery opportunity query failed (using defaults): {e}")

    if from_sql and total_scored > 0:
        high_pct = high_accounts / total_scored
        medium_pct = medium_accounts / total_scored
        high_gbp = round(high_pct * HIGH_CONCENTRATION * ANNUAL_THEFT_EXPOSURE, 0)
        medium_gbp = round(medium_pct * MEDIUM_CONCENTRATION * ANNUAL_THEFT_EXPOSURE, 0)
        high_gbp = min(high_gbp, ANNUAL_THEFT_EXPOSURE * 0.40)
        medium_gbp = min(medium_gbp, ANNUAL_THEFT_EXPOSURE * 0.30)
    else:
        high_gbp = 58_000_000.0
        high_accounts = 185
        medium_gbp = 32_000_000.0
        medium_accounts = 420
        recovered_ytd = 34_600_000.0

    remaining = max(0.0, ANNUAL_THEFT_EXPOSURE - recovered_ytd - high_gbp - medium_gbp)

    result = RecoveryOpportunity(
        total_exposure_gbp=ANNUAL_THEFT_EXPOSURE,
        recovered_ytd_gbp=recovered_ytd,
        high_confidence_gbp=high_gbp,
        high_confidence_accounts=high_accounts,
        medium_confidence_gbp=medium_gbp,
        medium_confidence_accounts=medium_accounts,
        remaining_exposure_gbp=remaining,
    )
    if from_sql:
        _cache_set("dashboard_recovery_opportunity", result)
    return result


# ---------------------------------------------------------------------------
# Robbie's Investigation Workbench
# ---------------------------------------------------------------------------

@api.get(
    "/investigation/kpis",
    response_model=InvestigationKPIs,
    operation_id="getInvestigationKPIs",
)
async def get_investigation_kpis(request: Request):
    """Operational KPI tiles for Robbie's daily triage."""
    cached = _cache_get("investigation_kpis")
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        for _attempt in range(2):
            try:
                rows = db.execute("""
                    SELECT
                      COUNT_IF(risk_tier = 'HIGH' AND investigation_status = 'OPEN') AS open_high,
                      COUNT_IF(risk_tier = 'MEDIUM' AND investigation_status = 'OPEN') AS open_medium,
                      COUNT_IF(investigation_status = 'IN_PROGRESS') AS in_progress
                    FROM anomaly_scores
                """)
                r = rows[0] if rows else {}
                open_high = int(r.get("open_high", 0) or 0)
                open_medium = int(r.get("open_medium", 0) or 0)
                in_progress = int(r.get("in_progress", 0) or 0)

                case_rows = db.execute("""
                    SELECT
                      COUNT_IF(closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE())) AS closed_mo,
                      COUNT_IF(outcome = 'THEFT_CONFIRMED' AND closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE())) AS confirmed_mo,
                      COUNT_IF(outcome = 'THEFT_CONFIRMED') AS confirmed_all,
                      COUNT_IF(outcome IS NOT NULL) AS closed_all,
                      ROUND(COALESCE(AVG(DATEDIFF(COALESCE(closed_timestamp, CURRENT_TIMESTAMP()), opened_timestamp)), 0), 1) AS avg_days,
                      ROUND(COALESCE(SUM(CASE WHEN closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE()) THEN revenue_recovered_gbp ELSE 0 END), 0), 0) AS recovered_mo
                    FROM investigation_cases
                """)
                cr = case_rows[0] if case_rows else {}
                closed_mo = int(cr.get("closed_mo", 0) or 0)
                confirmed_mo = int(cr.get("confirmed_mo", 0) or 0)
                confirmed_all = int(cr.get("confirmed_all", 0) or 0)
                closed_all = int(cr.get("closed_all", 0) or 0)
                avg_days = float(cr.get("avg_days", 0) or 0)
                recovered_mo = float(cr.get("recovered_mo", 0) or 0)
                precision = round(confirmed_all * 100.0 / closed_all, 1) if closed_all > 0 else 0.0

                sector_rows = db.execute("""
                    SELECT postcode_sector, COUNT(*) AS cnt
                    FROM anomaly_scores
                    WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN'
                    GROUP BY postcode_sector
                    ORDER BY cnt DESC
                    LIMIT 1
                """)
                top_sector = sector_rows[0]["postcode_sector"] if sector_rows else "N/A"
                top_count = int(sector_rows[0]["cnt"]) if sector_rows else 0

                result = InvestigationKPIs(
                    open_high_cases=open_high,
                    open_medium_cases=open_medium,
                    in_progress_cases=in_progress,
                    closed_this_month=closed_mo,
                    confirmed_theft_this_month=confirmed_mo,
                    precision_rate_pct=precision,
                    avg_days_to_close=avg_days,
                    revenue_recovered_this_month_gbp=recovered_mo,
                    top_postcode_sector=top_sector,
                    top_sector_count=top_count,
                )
                _cache_set("investigation_kpis", result)
                return result
            except Exception as e:
                logger.warning(f"Investigation KPIs query failed (using defaults): {e}")
                if _attempt == 0 and _maybe_self_heal(db):
                    cached = _cache_get("investigation_kpis")
                    if cached is not None:
                        return cached
                    continue
                break

    return InvestigationKPIs(
        open_high_cases=168,
        open_medium_cases=312,
        in_progress_cases=35,
        closed_this_month=87,
        confirmed_theft_this_month=64,
        precision_rate_pct=72.0,
        avg_days_to_close=6.2,
        revenue_recovered_this_month_gbp=8_500_000.0,
        top_postcode_sector="NW1 5",
        top_sector_count=12,
    )


@api.get(
    "/investigation/daily-briefing",
    response_model=DailyBriefing,
    operation_id="getDailyBriefing",
)
async def get_daily_briefing(request: Request):
    """AI-generated daily focus summary for Robbie via Bedrock."""
    cached = _cache_get("daily_briefing")
    if cached is not None:
        return cached

    from datetime import datetime, timezone
    import httpx

    db = _sql(request)
    config = _config(request)

    new_flags_24h = 0
    oldest_open_days = 0
    cluster_alert = ""
    open_high = 0
    in_progress = 0
    top_sectors: list[dict] = []

    if db:
        try:
            ctx = db.execute("""
                SELECT
                  COUNT_IF(risk_tier = 'HIGH' AND investigation_status = 'OPEN') AS open_high,
                  COUNT_IF(investigation_status = 'IN_PROGRESS') AS in_progress,
                  COUNT_IF(risk_tier = 'HIGH' AND score_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY) AS new_24h
                FROM anomaly_scores
            """)
            if ctx:
                r = ctx[0]
                open_high = int(r.get("open_high", 0) or 0)
                in_progress = int(r.get("in_progress", 0) or 0)
                new_flags_24h = int(r.get("new_24h", 0) or 0)

            oldest = db.execute("""
                SELECT DATEDIFF(CURRENT_DATE(), MIN(DATE(score_timestamp))) AS days
                FROM anomaly_scores
                WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN'
            """)
            if oldest and oldest[0].get("days"):
                oldest_open_days = int(oldest[0]["days"])

            top_sectors = db.execute("""
                SELECT postcode_sector, COUNT(*) AS cnt
                FROM anomaly_scores
                WHERE risk_tier = 'HIGH' AND investigation_status = 'OPEN'
                GROUP BY postcode_sector
                HAVING COUNT(*) >= 3
                ORDER BY cnt DESC
                LIMIT 3
            """) or []

            if top_sectors:
                parts = [f"{s['postcode_sector']} ({s['cnt']} cases)" for s in top_sectors]
                cluster_alert = f"Potential cluster activity: {', '.join(parts)}"
        except Exception as e:
            logger.error(f"daily_briefing SQL failed: {type(e).__name__}: {e}")

    ai_endpoint = _resolve_ai_endpoint(request, config)
    briefing_text = ""
    actions: list[str] = []

    if ai_endpoint and db:
        try:
            import json as _json
            host = _workspace_host(db)
            headers = db._client.config.authenticate()
            sector_str = "; ".join(f"{s['postcode_sector']}: {s['cnt']} HIGH cases" for s in top_sectors) if top_sectors else "no geographic clusters detected"

            prompt = f"""You are Robbie Henderson's AI assistant at UKI Gas Revenue Protection. Produce a morning briefing as a JSON object with two fields:

1. "summary": A 1-2 sentence overview of today's workload using the actual numbers below.
2. "actions": An array of 3-5 short, specific action items Robbie should complete today. Each action should be one sentence, start with a verb, and reference actual numbers or postcode sectors.

Data:
- {open_high} open HIGH-risk cases awaiting investigation
- {in_progress} cases currently in progress
- {new_flags_24h} new HIGH flags in the last 24 hours
- Oldest unactioned HIGH case: {oldest_open_days} days old
- Geographic clusters: {sector_str}

Priorities: Triage newest HIGH flags first, chase any case open > 5 days, investigate geographic clusters for organised theft rings.

Respond ONLY with the JSON object. No markdown, no code fences, no extra text."""

            with httpx.Client(timeout=30) as http:
                resp = http.post(
                    f"{host}/serving-endpoints/{ai_endpoint}/invocations",
                    json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 400},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        raw = choices[0].get("message", {}).get("content", "")
                        try:
                            parsed = _json.loads(raw)
                            briefing_text = parsed.get("summary", "")
                            actions = parsed.get("actions", [])
                        except (_json.JSONDecodeError, TypeError):
                            briefing_text = raw
        except Exception as e:
            logger.error(f"Daily briefing AI call failed: {e}")

    if not briefing_text:
        briefing_text = (
            f"You have {open_high} open HIGH-risk cases and {new_flags_24h} new overnight flags. "
            f"{'Your oldest unactioned case is ' + str(oldest_open_days) + ' days old. ' if oldest_open_days > 3 else ''}"
            f"Focus on the highest composite scores and any postcode clusters."
        )
    if not actions:
        actions = [
            f"Triage {new_flags_24h} new overnight HIGH flags" if new_flags_24h > 0 else "Review top-scoring open HIGH cases",
            f"Close or escalate cases open longer than 5 days (oldest: {oldest_open_days} days)" if oldest_open_days > 3 else "Keep case age under 5 days",
        ]
        if top_sectors:
            actions.append(f"Investigate cluster activity in {', '.join(s['postcode_sector'] for s in top_sectors)}")
        actions.append("Update investigation notes on all in-progress cases")

    result = DailyBriefing(
        briefing=briefing_text,
        actions=actions,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        new_high_flags_24h=new_flags_24h,
        oldest_open_days=oldest_open_days,
        cluster_alert=cluster_alert,
    )
    _cache_set("daily_briefing", result)
    return result


@api.get(
    "/investigation/accounts",
    response_model=list[FlaggedAccountListItem],
    operation_id="listFlaggedAccounts",
)
async def list_flagged_accounts(
    request: Request,
    risk_tier: RiskTier | None = None,
    fuel_type: FuelType | None = None,
    investigation_status: InvestigationStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Paginated flagged accounts table, filterable by risk tier, fuel type, and investigation status."""
    cache_key = f"flagged_accounts:{risk_tier}:{fuel_type}:{investigation_status}:{limit}:{offset}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        try:
            conditions: list[str] = []
            if risk_tier:
                conditions.append(f"risk_tier = '{risk_tier.value}'")
            else:
                conditions.append("risk_tier IN ('HIGH', 'MEDIUM')")
            if fuel_type:
                conditions.append(f"fuel_type = '{fuel_type.value}'")
            if investigation_status:
                conditions.append(f"investigation_status = '{investigation_status.value}'")
            where = " AND ".join(conditions)

            rows = db.execute(f"""
                SELECT
                  a.account_id, pr.postcode, a.risk_tier,
                  a.composite_risk_score, a.consumption_drop_pct,
                  a.comms_gap_count_30d, a.fuel_type, a.investigation_status
                FROM anomaly_scores a
                LEFT JOIN property_reference pr ON a.account_id = pr.account_id
                WHERE {where}
                ORDER BY a.composite_risk_score DESC
                LIMIT {limit} OFFSET {offset}
            """)
            result = []
            for r in rows:
                try:
                    result.append(FlaggedAccountListItem(
                        account_id=r["account_id"],
                        postcode=r["postcode"] or "N/A",
                        risk_tier=RiskTier(r["risk_tier"]),
                        composite_risk_score=float(r["composite_risk_score"] or 0),
                        consumption_drop_pct=min(100.0, max(0.0, float(r["consumption_drop_pct"] or 0))),
                        comms_gap_count_30d=int(float(r["comms_gap_count_30d"] or 0)),
                        fuel_type=FuelType(r["fuel_type"]),
                        investigation_status=InvestigationStatus(r["investigation_status"]),
                    ))
                except (ValueError, TypeError, KeyError) as row_err:
                    logger.warning(f"Skipping row {r.get('account_id', '?')}: {row_err}")
            _cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"list_flagged_accounts failed: {type(e).__name__}: {e}")
            return []
    return []


@api.get(
    "/investigation/accounts/{account_id}",
    response_model=AccountDetail,
    operation_id="getAccountDetail",
)
async def get_account_detail(request: Request, account_id: str):
    """Full account detail with anomaly signals.

    Optimised: the main account query now includes score_timestamp, and
    the meter-reads + cohort-reads queries run in parallel via ThreadPool
    to cut latency from 4 sequential round-trips to 1 + 1 parallel pair.
    """
    cache_key = f"account_detail:{account_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        rows = db.execute(f"""
            SELECT
              a.account_id, pr.postcode, pr.region, pr.property_type,
              pr.council_tax_band, a.fuel_type, a.risk_tier,
              a.composite_risk_score, a.consumption_drop_pct,
              a.comms_gap_count_30d,
              a.isolation_forest_score, a.lstm_deviation_score,
              a.cohort_deviation_score, a.score_timestamp
            FROM anomaly_scores a
            JOIN property_reference pr ON a.account_id = pr.account_id
            WHERE a.account_id = '{account_id}'
            LIMIT 1
        """)
        if rows:
            r = rows[0]
            iso = float(r["isolation_forest_score"])
            lstm = float(r["lstm_deviation_score"])
            cohort = float(r["cohort_deviation_score"])
            gaps = int(float(r["comms_gap_count_30d"]))
            drop = min(100.0, max(0.0, float(r["consumption_drop_pct"])))
            fuel = r["fuel_type"]
            postcode_sector = r["postcode"]
            anomaly_onset = r.get("score_timestamp")

            from concurrent.futures import ThreadPoolExecutor

            meter_sql = f"""
                SELECT DATE(read_timestamp) AS day,
                       AVG(consumption_kwh) AS avg_kwh,
                       MAX(read_quality) AS read_quality
                FROM smart_meter_reads
                WHERE account_id = '{account_id}'
                  AND read_timestamp >= CURRENT_DATE() - INTERVAL 90 DAY
                GROUP BY DATE(read_timestamp)
                ORDER BY day
            """
            cohort_sql = f"""
                SELECT DATE(read_timestamp) AS day,
                       AVG(consumption_kwh) AS avg_kwh
                FROM smart_meter_reads
                WHERE postcode = '{postcode_sector}'
                  AND fuel_type = '{fuel}'
                  AND account_id != '{account_id}'
                  AND read_timestamp >= CURRENT_DATE() - INTERVAL 90 DAY
                GROUP BY DATE(read_timestamp)
                ORDER BY day
            """

            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_meter = pool.submit(db.execute, meter_sql)
                fut_cohort = pool.submit(db.execute, cohort_sql)
                meter_rows = fut_meter.result(timeout=30) or []
                cohort_rows = fut_cohort.result(timeout=30) or []

            meter_reads = [
                MeterReadPoint(
                    read_timestamp=mr["day"],
                    consumption_kwh=float(mr["avg_kwh"]),
                    read_quality=mr["read_quality"] or "actual",
                )
                for mr in meter_rows
            ]

            cohort_avg_reads = [
                MeterReadPoint(
                    read_timestamp=cr["day"],
                    consumption_kwh=float(cr["avg_kwh"]),
                    read_quality="actual",
                )
                for cr in cohort_rows
            ]

            detail_result = AccountDetail(
                account_id=r["account_id"],
                postcode=r["postcode"],
                region=r["region"],
                property_type=r["property_type"],
                council_tax_band=r["council_tax_band"],
                fuel_type=FuelType(fuel),
                risk_tier=RiskTier(r["risk_tier"]),
                composite_risk_score=float(r["composite_risk_score"]),
                consumption_drop_pct=drop,
                comms_gap_count_30d=gaps,
                signals=AnomalySignals(
                    isolation_forest_score=iso,
                    lstm_deviation_score=min(1.0, max(0.0, lstm / 4.0)),
                    cohort_deviation_score=min(1.0, abs(cohort) / 3.5),
                    comms_gap_normalised=min(1.0, gaps / 20.0),
                    consumption_drop_normalised=min(1.0, max(0.0, drop / 70.0)),
                ),
                meter_reads=meter_reads,
                cohort_avg_reads=cohort_avg_reads,
                anomaly_onset=anomaly_onset,
            )
            _cache_set(cache_key, detail_result)
            return detail_result
    return AccountDetail(
        account_id=account_id,
        postcode="NW1 5",
        region="London",
        property_type="terraced",
        council_tax_band="D",
        fuel_type=FuelType.ELECTRICITY,
        risk_tier=RiskTier.HIGH,
        composite_risk_score=0.87,
        consumption_drop_pct=62.3,
        comms_gap_count_30d=8,
        signals=AnomalySignals(
            isolation_forest_score=0.92,
            lstm_deviation_score=0.85,
            cohort_deviation_score=0.78,
            comms_gap_normalised=0.67,
            consumption_drop_normalised=0.89,
        ),
        meter_reads=[],
        cohort_avg_reads=[],
    )


# ---------------------------------------------------------------------------
# Shared financial estimate
# ---------------------------------------------------------------------------

_MONTHLY_LOSS_MULTIPLIER = 2.30


def _est_monthly_loss(drop_pct: float, score: float) -> float:
    """Single formula used by both the case summary and the dispatch report.

    Uses the stronger of (a) the absolute consumption drop or (b) the
    composite risk score scaled to 0-100, multiplied by a per-unit
    £/kWh-equivalent cost factor to produce a realistic ~£200/month for
    a typical HIGH-risk account.
    """
    signal = max(abs(drop_pct), score * 100)
    return round(signal * _MONTHLY_LOSS_MULTIPLIER, 2) if signal > 0 else 0.0


# ---------------------------------------------------------------------------
# LLM Case Summary (Bedrock via AI Gateway)
# ---------------------------------------------------------------------------

@api.get(
    "/llm/case-summary/{account_id}",
    response_model=LLMCaseSummary,
    operation_id="getCaseSummary",
)
async def get_case_summary(request: Request, account_id: str):
    """Generate LLM case summary for a flagged account via AI Gateway.

    Optimised: both anomaly_scores and investigation_cases are queried in
    parallel via ThreadPool to halve the latency.
    """
    cache_key = f"case_summary:{account_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = _sql(request)

    risk_level = "HIGH"
    signals: list[str] = []
    drop_pct = 0.0
    score = 0.0
    gaps = 0

    if db:
        from concurrent.futures import ThreadPoolExecutor

        anomaly_sql = f"""
            SELECT composite_risk_score, consumption_drop_pct,
                   comms_gap_count_30d, risk_tier,
                   isolation_forest_score, lstm_deviation_score
            FROM anomaly_scores
            WHERE account_id = '{account_id}'
            LIMIT 1
        """
        case_sql = f"""
            SELECT llm_summary FROM investigation_cases
            WHERE account_id = '{account_id}'
            LIMIT 1
        """

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_anomaly = pool.submit(db.execute, anomaly_sql)
            fut_case = pool.submit(db.execute, case_sql)
            rows = fut_anomaly.result(timeout=30)
            case_rows = fut_case.result(timeout=30)

        if rows:
            r = rows[0]
            risk_level = r["risk_tier"]
            drop_pct = min(100.0, max(0.0, float(r["consumption_drop_pct"])))
            score = float(r["composite_risk_score"])
            gaps = int(float(r["comms_gap_count_30d"]))
            signals = [
                f"{drop_pct:.1f}% consumption drop over 30 days",
                f"{gaps} communication gaps in 30 days",
                f"Isolation Forest score: {float(r['isolation_forest_score']):.2f}",
                f"LSTM deviation: {float(r['lstm_deviation_score']):.2f}",
            ]

        if case_rows and case_rows[0].get("llm_summary"):
            raw = case_rows[0]["llm_summary"]
            cs_result = LLMCaseSummary(
                account_id=account_id,
                risk_level=risk_level,
                key_signals=signals or ["Data from anomaly scoring model"],
                recommended_action="Dispatch field engineer for meter inspection" if risk_level == "HIGH" else "Monitor and re-score in next batch",
                priority="URGENT" if risk_level == "HIGH" else "STANDARD",
                estimated_loss_per_month_gbp=_est_monthly_loss(drop_pct, score),
                raw_text=raw,
            )
            _cache_set(cache_key, cs_result)
            return cs_result

    fallback = LLMCaseSummary(
        account_id=account_id,
        risk_level=risk_level,
        key_signals=signals or [
            "62% consumption drop over 30 days",
            "8 communication gaps in 30 days",
            "Cohort deviation 2.3 sigma above mean",
        ],
        recommended_action="Dispatch field engineer for meter inspection",
        priority="URGENT" if risk_level == "HIGH" else "STANDARD",
        estimated_loss_per_month_gbp=_est_monthly_loss(drop_pct, score) or 200.0,
        raw_text=f"Account {account_id} analysis pending full LLM integration.",
    )
    _cache_set(cache_key, fallback)
    return fallback


# ---------------------------------------------------------------------------
# Field Investigation Dispatch (Bedrock via AI Gateway)
# ---------------------------------------------------------------------------

@api.post(
    "/investigation/{account_id}/dispatch",
    response_model=DispatchReport,
    operation_id="generateDispatchReport",
)
async def generate_dispatch_report(request: Request, account_id: str):
    """Generate a field investigation dispatch briefing for a flagged account.

    Gathers account data + local intelligence, calls Bedrock via AI Gateway
    for the narrative, and returns a structured dispatch document.
    """
    from datetime import datetime, timezone
    import json
    import httpx

    db = _sql(request)
    config = _config(request)

    # --- 1. Gather account data ---
    acct: dict[str, Any] = {}
    if db:
        rows = db.execute(f"""
            SELECT a.account_id, pr.postcode, pr.region, pr.property_type,
                   pr.council_tax_band, a.fuel_type, a.risk_tier,
                   a.composite_risk_score, a.consumption_drop_pct,
                   a.comms_gap_count_30d, a.isolation_forest_score,
                   a.lstm_deviation_score, a.cohort_deviation_score,
                   a.postcode_sector
            FROM anomaly_scores a
            JOIN property_reference pr ON a.account_id = pr.account_id
            WHERE a.account_id = '{account_id}'
            LIMIT 1
        """)
        if rows:
            acct = rows[0]

    if not acct:
        acct = {
            "account_id": account_id, "postcode": "NW1 5", "region": "London",
            "property_type": "terraced", "council_tax_band": "D",
            "fuel_type": "electricity", "risk_tier": "HIGH",
            "composite_risk_score": "0.87", "consumption_drop_pct": "62.3",
            "comms_gap_count_30d": "8", "isolation_forest_score": "0.92",
            "lstm_deviation_score": "3.4", "cohort_deviation_score": "2.8",
            "postcode_sector": "NW1 5",
        }

    sector = acct.get("postcode_sector") or acct.get("postcode", "")
    fuel = str(acct.get("fuel_type", "electricity"))
    drop_pct = min(100.0, max(0.0, float(acct.get("consumption_drop_pct", 0))))
    gaps = int(float(acct.get("comms_gap_count_30d", 0)))
    score = float(acct.get("composite_risk_score", 0))

    est_monthly_loss = _est_monthly_loss(drop_pct, score)

    # --- 2. Local intelligence queries ---
    nearby_count = 0
    prior_theft = False
    if db and sector:
        nearby_rows = db.execute(f"""
            SELECT COUNT(*) AS cnt FROM anomaly_scores
            WHERE postcode_sector = '{sector}'
              AND risk_tier = 'HIGH'
              AND account_id != '{account_id}'
        """)
        if nearby_rows:
            nearby_count = int(nearby_rows[0]["cnt"])

        theft_rows = db.execute(f"""
            SELECT COUNT(*) AS cnt FROM investigation_cases ic
            JOIN anomaly_scores a ON ic.account_id = a.account_id
            WHERE a.postcode_sector = '{sector}'
              AND ic.outcome = 'THEFT_CONFIRMED'
        """)
        if theft_rows:
            prior_theft = int(theft_rows[0]["cnt"]) > 0

    # --- 3. Call LLM via AI Gateway for narrative ---
    narrative = ""
    ai_endpoint = _resolve_ai_endpoint(request, config)

    iso_score = float(acct.get("isolation_forest_score", 0))
    lstm_dev = float(acct.get("lstm_deviation_score", 0))
    cohort_dev = float(acct.get("cohort_deviation_score", 0))

    likelihood = "very high" if score >= 0.85 else "high" if score >= 0.7 else "moderate"

    if ai_endpoint and db:
        try:
            host = _workspace_host(db)
            headers = db._client.config.authenticate()
            prompt = f"""You are a senior revenue protection analyst at UKI Gas writing a dispatch briefing for a field engineer. The engineer needs to arrive fully prepared — they have not seen this account before.

Write a briefing that covers ALL of the following, using the exact numbers provided:

1. WHAT WE NOTICED: The specific anomalies detected and when they occurred.
2. KEY METRICS: Quote the exact scores so the engineer understands severity.
3. LIKELIHOOD: Based on the composite score of {score:.2f}/1.0, the likelihood of theft is {likelihood}.
4. WHAT TO EXPECT ON SITE: Based on the fuel type and signals, what the engineer is likely to find.
5. WHAT TO FOCUS ON: The most important things to check given this specific pattern.

Account data:
- Account: {account_id} | Postcode: {acct.get('postcode')} | Region: {acct.get('region')}
- Property: {acct.get('property_type')}, Council Tax Band {acct.get('council_tax_band')} | Fuel: {fuel}
- Composite risk score: {score:.2f} / 1.0 (likelihood: {likelihood})
- Consumption drop: {drop_pct:.1f}% over the last 30 days
- Smart meter communication gaps: {gaps} in the last 30 days
- Isolation Forest anomaly score: {iso_score:.2f} (0-1 scale, higher = more unusual)
- LSTM deviation from own baseline: {lstm_dev:.2f} standard deviations
- Deviation from peer group (similar properties): {cohort_dev:.2f} standard deviations
- Nearby HIGH-risk accounts in same postcode sector: {nearby_count}
- Prior confirmed theft in this sector: {'Yes — heightened area of concern' if prior_theft else 'No prior confirmed cases'}
- Estimated monthly loss: £{est_monthly_loss:.0f}

Write 5-7 sentences in plain English. Include the actual numbers. Do not use headers, bullet points, or markdown formatting."""

            with httpx.Client(timeout=60) as http:
                resp = http.post(
                    f"{host}/serving-endpoints/{ai_endpoint}/invocations",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                    },
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        narrative = choices[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"AI Gateway dispatch call failed: {e}")

    if not narrative:
        method = "meter bypass (wiring routed around the meter)" if fuel == "electricity" else "meter manipulation (magnets, drilled casing, or reversed connection)"
        peer_note = f"This account's usage is {cohort_dev:.1f} standard deviations below similar {acct.get('property_type', '')} properties in the {acct.get('postcode', '')} area (Band {acct.get('council_tax_band', '')})." if cohort_dev > 1.5 else ""
        area_note = f"There are {nearby_count} other HIGH-risk accounts in the same postcode sector and prior confirmed theft in this area — treat this as a heightened-risk sector." if nearby_count > 0 and prior_theft else (f"There are {nearby_count} other HIGH-risk accounts in the same postcode sector, which may indicate organised activity." if nearby_count > 0 else "No other high-risk accounts in the immediate area.")
        narrative = (
            f"Account {account_id} at {acct.get('postcode')} ({acct.get('property_type')}, Band {acct.get('council_tax_band')}) "
            f"has been flagged with a composite risk score of {score:.2f}/1.0, indicating a {likelihood} likelihood of energy theft. "
            f"Over the last 30 days, {fuel} consumption has dropped by {drop_pct:.1f}% against its rolling average, "
            f"and the smart meter has failed to report data on {gaps} occasions — "
            f"the coincidence of a sharp usage step-down with communication gaps is a classic signature of {method}. "
            f"The Isolation Forest model scored this account at {iso_score:.2f} (top {'5' if iso_score > 0.9 else '15'}% most anomalous), "
            f"and the LSTM model detected a {lstm_dev:.1f} standard deviation shift from the account's own 90-day baseline. "
            f"{peer_note} "
            f"{area_note} "
            f"The engineer should focus on physical inspection of the {fuel} meter installation, "
            f"comparing the physical meter reading against the last reported smart reading, "
            f"and documenting any signs of tampering. Estimated monthly loss: £{est_monthly_loss:.0f}."
        )

    # --- 4. Build fuel-specific actions and checklist ---
    if fuel == "gas":
        actions = [
            "Inspect gas meter for signs of manipulation (magnets, drilled casing, reversed connection)",
            "Compare physical meter reading with last reported smart reading",
            "Check for additional piping or rubber tubing bypassing the meter",
            "Inspect meter index and verify it advances when gas appliances are running",
        ]
        checklist = [
            "Photograph meter serial number and installation",
            "Record meter index reading",
            "Check for smell of gas near the meter",
            "Document any visible damage, drilled holes, or seal breaches",
            "Note condition of DCC communication module",
        ]
        safety = [
            "Follow Gas Safety (Installation and Use) Regulations 1998",
            "If gas leak detected: evacuate, do not operate switches, call National Gas Emergency on 0800 111 999",
            "Do not reconnect if evidence of tampering — isolate and escalate",
        ]
    else:
        actions = [
            "Inspect meter installation for bypass wiring routed around the meter",
            "Compare physical meter reading with last reported smart reading",
            "Record voltage at meter terminals (expect ~240V if supply is legitimate)",
            "Check DCC communication module for physical tampering or signal jamming",
        ]
        checklist = [
            "Photograph meter serial number and installation",
            "Record meter index reading and voltage at terminals",
            "Document any visible signs of bypass wiring, damaged seals, or cable re-routing",
            "Note condition of DCC communication module and any shielding",
            "Photograph supply cable routing from cut-out to meter",
        ]
        safety = [
            "Isolate supply before inspecting if bypass is suspected — risk of electrocution",
            "Do not reconnect if evidence of tampering — escalate to safety team",
            "If occupant is aggressive: withdraw and request police attendance under Rights of Entry Act 1954",
        ]

    now = datetime.now(timezone.utc)
    case_ref = f"BG-INV-{now.strftime('%Y')}-{abs(hash(account_id)) % 100000:05d}"

    return DispatchReport(
        case_reference=case_ref,
        generated_at=now.strftime("%d %b %Y, %H:%M UTC"),
        priority=str(acct.get("risk_tier", "HIGH")),
        account_id=account_id,
        postcode=str(acct.get("postcode", "")),
        region=str(acct.get("region", "")),
        property_type=str(acct.get("property_type", "")),
        council_tax_band=str(acct.get("council_tax_band", "")),
        fuel_type=fuel,
        composite_risk_score=score,
        consumption_drop_pct=drop_pct,
        comms_gap_count_30d=gaps,
        nearby_high_risk_count=nearby_count,
        prior_theft_in_sector=prior_theft,
        narrative=narrative,
        recommended_actions=actions,
        evidence_checklist=checklist,
        safety_notes=safety,
        estimated_monthly_loss_gbp=est_monthly_loss,
    )


# ---------------------------------------------------------------------------
# Investigation Close-Out
# ---------------------------------------------------------------------------


from typing import Literal


class InvestigationCloseRequest(BaseModel):
    outcome: Literal["confirmed_theft", "no_theft", "inconclusive"]
    recovered_amount: float | None = None
    notes: str | None = None


class InvestigationCloseResponse(BaseModel):
    success: bool
    account_id: str
    outcome: str
    recovered_amount: float | None = None
    message: str | None = None


_OUTCOME_MAP = {
    "confirmed_theft": "THEFT_CONFIRMED",
    "no_theft": "FALSE_POSITIVE",
    "inconclusive": "INCONCLUSIVE",
}


@api.post(
    "/investigation/{account_id}/close",
    response_model=InvestigationCloseResponse,
    operation_id="closeInvestigation",
)
async def close_investigation(request: Request, account_id: str, body: InvestigationCloseRequest):
    """Close an investigation case — writes outcome and recovered amount back to Lakehouse."""
    db_outcome = _OUTCOME_MAP[body.outcome]
    recovered = body.recovered_amount if body.outcome == "confirmed_theft" else None

    db = _sql(request)
    if not db:
        logger.warning(f"Close investigation (demo mode) for {account_id}: {body.outcome}")
        _cache.clear()
        return InvestigationCloseResponse(
            success=True,
            account_id=account_id,
            outcome=db_outcome,
            recovered_amount=recovered,
            message="Recorded (demo mode — SQL Warehouse unavailable)",
        )

    recovered_sql = str(recovered) if recovered is not None else "NULL"
    notes_safe = (body.notes or "").replace("'", "''")

    new_status = "CONFIRMED_THEFT" if db_outcome == "THEFT_CONFIRMED" else "CLOSED"

    merge_sql = f"""
        MERGE INTO investigation_cases AS t
        USING (SELECT '{account_id}' AS account_id) AS s
        ON t.account_id = s.account_id
          AND (t.outcome IS NULL OR t.outcome = 'PENDING')
        WHEN MATCHED THEN UPDATE SET
          outcome = '{db_outcome}',
          closed_timestamp = current_timestamp(),
          revenue_recovered_gbp = {recovered_sql}
        WHEN NOT MATCHED THEN INSERT (
          case_id, account_id, opened_timestamp, outcome,
          closed_timestamp, revenue_recovered_gbp
        ) VALUES (
          concat('CASE-', unix_timestamp()),
          '{account_id}',
          current_timestamp(),
          '{db_outcome}',
          current_timestamp(),
          {recovered_sql}
        )
    """
    update_sql = f"""
        UPDATE anomaly_scores
        SET investigation_status = '{new_status}'
        WHERE account_id = '{account_id}'
    """

    _optimistic_cache_update(db_outcome, recovered)

    import threading

    def _write_and_rewarm():
        from concurrent.futures import ThreadPoolExecutor
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_merge = pool.submit(db.execute, merge_sql)
                fut_update = pool.submit(db.execute, update_sql)
                try:
                    fut_merge.result(timeout=25)
                except Exception as e:
                    logger.error(f"Close investigation MERGE failed for {account_id}: {e}")
                try:
                    fut_update.result(timeout=25)
                except Exception as e:
                    logger.warning(f"Close investigation anomaly_scores update failed for {account_id}: {e}")
        finally:
            _invalidate_and_rewarm(db)

    threading.Thread(target=_write_and_rewarm, daemon=True).start()

    return InvestigationCloseResponse(
        success=True,
        account_id=account_id,
        outcome=db_outcome,
        recovered_amount=recovered,
        message="Investigation closed and written to Lakebase",
    )


# ---------------------------------------------------------------------------
# Genie Conversation API (Susie's NL Queries)
# ---------------------------------------------------------------------------

def _genie_headers(request: Request) -> tuple[str, dict[str, str], dict[str, str] | None] | None:
    """Return (host, primary_headers, fallback_headers) for Genie API calls.

    Always uses SP auth for portability — avoids dependency on user token
    passthrough (``user_api_scopes``) which isn't enabled on all workspaces.
    The app SP already has CAN_RUN on the Genie Space and SELECT on the
    underlying tables, so SP auth is sufficient and more reliable for
    always-on demo environments.
    """
    db = _sql(request)
    if not db:
        return None
    host = _workspace_host(db)
    headers = db._client.config.authenticate()
    return host, headers, None


@api.post(
    "/genie/conversation",
    response_model=GenieConversation,
    operation_id="startGenieConversation",
)
async def start_genie_conversation(request: Request):
    """Start a new Genie conversation."""
    return GenieConversation(
        conversation_id="new",
        messages=[],
    )


@api.post(
    "/genie/warm",
    response_model=GenieMessage,
    operation_id="warmGenie",
)
async def warm_genie(request: Request):
    """Pre-warm a Genie conversation so the first real question is fast.

    Starts a conversation with a lightweight question, returns the
    conversation_id the frontend should reuse for subsequent messages.
    """
    import asyncio
    import httpx

    config = _config(request)
    genie_space_id = (config.genie_space_id if config else "").strip()
    if not genie_space_id:
        return GenieMessage(role="assistant", content="", conversation_id=None)

    auth = _genie_headers(request)
    if not auth:
        return GenieMessage(role="assistant", content="", conversation_id=None)

    host, headers, fallback_headers = auth
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{host}/api/2.0/genie/spaces/{genie_space_id}/start-conversation",
                json={"content": "How many accounts are in the system?"},
                headers=headers,
            )
            if resp.status_code == 403 and fallback_headers:
                headers = fallback_headers
                resp = await http.post(
                    f"{host}/api/2.0/genie/spaces/{genie_space_id}/start-conversation",
                    json={"content": "How many accounts are in the system?"},
                    headers=headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                conv_id = data.get("conversation_id")
                msg_id = data.get("message_id")
                if conv_id and msg_id:
                    for _ in range(20):
                        await asyncio.sleep(0.5)
                        poll = await http.get(
                            f"{host}/api/2.0/genie/spaces/{genie_space_id}/conversations/{conv_id}/messages/{msg_id}",
                            headers=headers,
                        )
                        if poll.status_code == 200:
                            status = poll.json().get("status")
                            if status in ("COMPLETED", "FAILED", "CANCELLED"):
                                break
                return GenieMessage(role="assistant", content="", conversation_id=conv_id)
    except Exception as e:
        logger.warning(f"Genie warm-up failed (non-critical): {e}")
    return GenieMessage(role="assistant", content="", conversation_id=None)


async def _fetch_query_results(
    http: "httpx.AsyncClient",
    host: str,
    headers: dict[str, str],
    genie_space_id: str,
    conv_id: str,
    msg_id: str,
    attachment: dict,
) -> tuple[list[str] | None, list[dict[str, object]] | None]:
    """Fetch query result rows from the Genie query result API."""
    query_obj = attachment.get("query", {})
    statement_id = query_obj.get("statement_id")
    if not statement_id:
        return None, None
    try:
        resp = await http.get(
            f"{host}/api/2.0/genie/spaces/{genie_space_id}"
            f"/conversations/{conv_id}/messages/{msg_id}"
            f"/query-result/{statement_id}",
            headers=headers,
        )
        if resp.status_code != 200:
            return None, None
        result = resp.json()
        columns = [c.get("name", "") for c in result.get("statement_response", {}).get("manifest", {}).get("schema", {}).get("columns", [])]
        data_array = result.get("statement_response", {}).get("result", {}).get("data_array", [])
        if not columns or not data_array:
            return columns or None, None
        rows = [dict(zip(columns, row)) for row in data_array[:50]]
        return columns, rows
    except Exception as e:
        logger.warning(f"Genie query result fetch failed: {e}")
        return None, None


@api.post(
    "/genie/conversation/{conversation_id}/message",
    response_model=GenieMessage,
    operation_id="sendGenieMessage",
)
async def send_genie_message(
    request: Request,
    conversation_id: str,
    message: str = "",
):
    """Send a message to Genie via the REST API and poll for the response."""
    import asyncio
    import httpx

    config = _config(request)
    genie_space_id = (config.genie_space_id if config else "").strip()

    logger.info(f"Genie request — space_id={genie_space_id!r}, conv={conversation_id}")

    if not genie_space_id:
        return GenieMessage(
            role="assistant",
            content="Genie Space not configured. Set GENIE_SPACE_ID to enable.",
        )

    auth = _genie_headers(request)
    if not auth:
        return GenieMessage(
            role="assistant",
            content="SQL client not available. Cannot reach Genie API.",
        )

    host, headers, fallback_headers = auth

    try:
        is_new = conversation_id in ("new", "placeholder", "")

        async with httpx.AsyncClient(timeout=120) as http:
            if is_new:
                url = f"{host}/api/2.0/genie/spaces/{genie_space_id}/start-conversation"
            else:
                url = f"{host}/api/2.0/genie/spaces/{genie_space_id}/conversations/{conversation_id}/messages"

            payload = {"content": message}
            resp = await http.post(url, json=payload, headers=headers)

            if resp.status_code == 403 and fallback_headers:
                logger.warning(
                    f"Genie OBO auth returned 403, retrying with SP auth. "
                    f"Space: {genie_space_id}, Response: {resp.text[:300]}"
                )
                headers = fallback_headers
                resp = await http.post(url, json=payload, headers=headers)

            for _attempt in range(3):
                if resp.status_code != 429:
                    break
                backoff = 2 ** _attempt
                logger.warning(
                    f"Genie 429 rate-limited, retry {_attempt + 1}/3 "
                    f"after {backoff}s"
                )
                await asyncio.sleep(backoff)
                resp = await http.post(url, json=payload, headers=headers)

            if resp.status_code != 200:
                logger.error(f"Genie start failed: {resp.status_code} {resp.text[:500]}")
                return GenieMessage(
                    role="assistant",
                    content=f"Genie returned an error (HTTP {resp.status_code}). Try again.",
                )

            data = resp.json()
            real_conv_id = data.get("conversation_id", conversation_id)
            msg_id = data.get("message_id")

            if not msg_id:
                raw_content = data.get("content", "Genie did not return a message.")
                return GenieMessage(
                    role="assistant",
                    content=str(raw_content) if not isinstance(raw_content, str) else raw_content,
                    conversation_id=real_conv_id,
                )

            result_data = None
            poll_delay = 0.3
            for _ in range(60):
                await asyncio.sleep(poll_delay)
                poll_delay = min(poll_delay * 1.15, 1.5)
                poll = await http.get(
                    f"{host}/api/2.0/genie/spaces/{genie_space_id}/conversations/{real_conv_id}/messages/{msg_id}",
                    headers=headers,
                )
                if poll.status_code != 200:
                    continue
                msg_data = poll.json()
                status = msg_data.get("status")
                if status in ("COMPLETED", "EXECUTING_QUERY"):
                    result_data = msg_data
                    if status == "COMPLETED":
                        break
                elif status in ("FAILED", "CANCELLED"):
                    raw_error = msg_data.get("error", "Genie was unable to answer. Try rephrasing.")
                    return GenieMessage(
                        role="assistant",
                        content=str(raw_error) if not isinstance(raw_error, str) else raw_error,
                        conversation_id=real_conv_id,
                    )

            if not result_data:
                return GenieMessage(
                    role="assistant",
                    content="Genie timed out. Try a simpler question.",
                    conversation_id=real_conv_id,
                )

            text_parts: list[str] = []
            sql_text: str | None = None
            result_columns: list[str] | None = None
            result_rows: list[dict[str, object]] | None = None

            for att in result_data.get("attachments", []):
                if "text" in att and att["text"].get("content"):
                    text_parts.append(att["text"]["content"])
                if "query" in att:
                    query_obj = att["query"]
                    if query_obj.get("query"):
                        sql_text = query_obj["query"]
                    if query_obj.get("description"):
                        text_parts.insert(0, query_obj["description"])
                    result_columns, result_rows = await _fetch_query_results(
                        http, host, headers, genie_space_id,
                        real_conv_id, msg_id, att,
                    )

            response_text = "\n\n".join(text_parts) if text_parts else "Query completed."

        return GenieMessage(
            role="assistant",
            content=response_text,
            sql=sql_text,
            conversation_id=real_conv_id,
            columns=result_columns,
            data=result_rows,
        )

    except Exception as e:
        logger.error(f"Genie API error: {e}")
        return GenieMessage(
            role="assistant",
            content=f"Error querying Genie: {str(e)[:200]}",
        )


# ---------------------------------------------------------------------------
# Agent Atlas — Multi-Agent Board Report Supervisor
# ---------------------------------------------------------------------------

ATLAS_GENIE_QUESTIONS = [
    "At the current monthly run rate based on 2026 closures only, are we on track for the £97M annual recovery target? Show monthly revenue recovered vs an £8.1M per month reference pace.",
    "Rank the top 10 postcode sectors by count of HIGH risk accounts and show each sector's average composite_risk_score.",
    "For 2026 year-to-date, which region recovered the most GBP from confirmed theft cases and which the least? Show total revenue recovered by region.",
    "How many accounts have risk_tier HIGH and investigation_status OPEN, what is their average composite_risk_score, what is the latest precision_pct for risk_tier HIGH from model_performance_log, and what is YTD Avg Recovery Per Case from theft_detection_metrics?",
]


async def _atlas_query_genie(
    host: str,
    headers: dict[str, str],
    fallback_headers: dict[str, str] | None,
    genie_space_id: str,
    question: str,
) -> AgentStep:
    """Send one question to Genie and return an AgentStep with the answer."""
    import asyncio
    import httpx

    t0 = _time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=120) as http:
            url = f"{host}/api/2.0/genie/spaces/{genie_space_id}/start-conversation"
            payload = {"content": question}
            resp = await http.post(url, json=payload, headers=headers)

            if resp.status_code == 403 and fallback_headers:
                headers = fallback_headers
                resp = await http.post(url, json=payload, headers=headers)

            for attempt in range(3):
                if resp.status_code != 429:
                    break
                backoff = 2 ** attempt
                logger.warning(
                    f"Genie 429 rate-limited, retry {attempt + 1}/3 "
                    f"after {backoff}s"
                )
                await asyncio.sleep(backoff)
                resp = await http.post(url, json=payload, headers=headers)

            if resp.status_code != 200:
                return AgentStep(
                    agent="genie", question=question,
                    answer=f"Genie error (HTTP {resp.status_code})",
                    duration_ms=int((_time.monotonic() - t0) * 1000),
                )

            data = resp.json()
            conv_id = data.get("conversation_id")
            msg_id = data.get("message_id")
            if not (conv_id and msg_id):
                return AgentStep(
                    agent="genie", question=question,
                    answer="No conversation started",
                    duration_ms=int((_time.monotonic() - t0) * 1000),
                )

            poll_delay = 0.3
            result_data = None
            for _ in range(60):
                await asyncio.sleep(poll_delay)
                poll_delay = min(poll_delay * 1.15, 1.5)
                poll = await http.get(
                    f"{host}/api/2.0/genie/spaces/{genie_space_id}/conversations/{conv_id}/messages/{msg_id}",
                    headers=headers,
                )
                if poll.status_code != 200:
                    continue
                msg_data = poll.json()
                status = msg_data.get("status")
                if status == "COMPLETED":
                    result_data = msg_data
                    break
                elif status in ("FAILED", "CANCELLED"):
                    raw_error = msg_data.get("error", "Genie failed")
                    return AgentStep(
                        agent="genie", question=question,
                        answer=str(raw_error) if not isinstance(raw_error, str) else raw_error,
                        duration_ms=int((_time.monotonic() - t0) * 1000),
                    )

            if not result_data:
                return AgentStep(
                    agent="genie", question=question,
                    answer="Genie timed out",
                    duration_ms=int((_time.monotonic() - t0) * 1000),
                )

            text_parts: list[str] = []
            sql_text: str | None = None
            result_rows: list[dict[str, object]] | None = None
            for att in result_data.get("attachments", []):
                if "text" in att and att["text"].get("content"):
                    text_parts.append(att["text"]["content"])
                if "query" in att:
                    q = att["query"]
                    if q.get("query"):
                        sql_text = q["query"]
                    if q.get("description"):
                        text_parts.insert(0, q["description"])
                    _, rows = await _fetch_query_results(
                        http, host, headers, genie_space_id,
                        conv_id, msg_id, att,
                    )
                    result_rows = rows

            return AgentStep(
                agent="genie",
                question=question,
                answer="\n".join(text_parts) if text_parts else "No answer",
                data=result_rows,
                sql=sql_text,
                duration_ms=int((_time.monotonic() - t0) * 1000),
            )
    except Exception as e:
        logger.error(f"Atlas Genie step failed: {e}")
        return AgentStep(
            agent="genie", question=question,
            answer=f"Error: {str(e)[:200]}",
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )


async def _atlas_market_intelligence(
    host: str,
    headers: dict[str, str],
    gemini_endpoint: str,
    kpi_data: dict[str, str],
) -> AgentStep:
    """Call Gemini via AI Gateway for UK energy theft market & regulatory context."""
    import httpx

    t0 = _time.monotonic()
    kpi_summary = "\n".join(f"- {k}: {v}" for k, v in kpi_data.items()) if kpi_data else "No internal KPIs available yet."

    prompt = f"""You are composing an analyst-style market and regulatory intelligence briefing \
for a UKI Gas Revenue Protection board report. Your task is to SYNTHESISE the verified \
source material below into flowing prose — do NOT invent statistics or cite sources not listed here.

=== VERIFIED SOURCE MATERIAL ===

[RECCo / Capgemini Theft Estimation, Jan 2023]
- Annual energy theft across Great Britain: up to £1.4 billion/year (1,069 GWh gas + 2,837 GWh electricity).
- Cost passed to consumers: approximately £50/year per household.

[Ofgem, 2022/23]
- UK suppliers confirmed 16,581 energy thefts against an Ofgem target of 41,000 — approximately 40% of target.
- Metering equipment interference incidents increased 370% between 2017 and 2021.

[Ofgem TDIS Reform R0173, May 2025]
- Reformed Theft Detection Incentive Scheme now pays suppliers for Desktop Investigations and Site Visits \
regardless of whether they result in a confirmed theft — removing the disincentive to investigate marginal cases.

[Ofgem ETU R0233, June 2025]
- Energy Theft Unit (ETU) established under the Retail Energy Code, partnering with City of London Police.
- Companion R0234 introduced an Energy Theft Referral Assessment Service.

[DESNZ Smart Meters Quarterly Update, Q1 2025]
- 39 million smart meters installed in GB; 35 million operating in full smart mode (67% of all electricity meters).
- Regional variation: North East at 75%, London lagging at 60%.

[Enel / C3.ai — International Benchmark]
- Enel deployed ML-based theft detection across 20 million smart meters using 500+ features from 7 source systems.
- Results: 70% improvement in average energy recovered per inspection in Italy; over 300% improvement in Spain.
- Replaced rule-based identification with ML probability scoring prioritised by magnitude and likelihood.

[Zheng et al., IEEE Trans. Industrial Informatics, 2018 — 687 citations]
- "Wide and Deep Convolutional Neural Networks for Electricity-Theft Detection to Secure Smart Grids."
- Seminal academic paper demonstrating CNN-based detection of non-technical losses from smart meter consumption data.

[IEEE Surveys, 2024-25]
- Ensemble methods (Random Forest, LightGBM, ANN stacking) achieving ROC-AUC of 0.88 on real smart meter datasets.
- Non-technical losses represent up to 40% of transmission and distribution losses globally.

[UKRPA — UK Revenue Protection Association]
- Industry trade body (est. 1999); Strategic Plan 2025-26 published; annual conference.

=== INTERNAL PERFORMANCE DATA ===
{kpi_summary}

=== INSTRUCTIONS ===
Write a JSON object with one field, "market_intelligence", containing a 6-8 sentence analyst \
research note covering these five themes in order:

1. PROBLEM SCALE — Quantify the GB theft problem using the RECCo/Capgemini estimate and the \
Ofgem detection shortfall. Note the cost to honest consumers.
2. REGULATORY TAILWINDS — Summarise the 2025 reforms (TDIS R0173, ETU R0233) as creating a \
step-change in enforcement and supplier incentives.
3. INTERNATIONAL BENCHMARK — Cite Enel's ML deployment as proof that the approach works at scale, \
with specific recovery improvement figures.
4. ACADEMIC ML VALIDATION — Reference the depth of peer-reviewed research (Zheng et al. 2018, \
recent IEEE ensemble studies) to validate the ML techniques UKI Gas is adopting.
5. SMART METER OPPORTUNITY — Connect the 39M installed smart meters to the detection opportunity, \
noting regional variation and forward-looking implications for UKI Gas's analytics capability.

Where the internal performance data is available, weave in a comparison to the industry benchmarks.

Tone: CFO-facing analyst research note. Cite sources parenthetically (e.g. "RECCo/Capgemini, 2023"). \
Flowing prose only — no bullet points, no headers. Every claim must trace to a source listed above.

Respond ONLY with the JSON object. No markdown, no code fences."""

    try:
        async with httpx.AsyncClient(timeout=45) as http:
            resp = await http.post(
                f"{host}/serving-endpoints/{gemini_endpoint}/invocations",
                json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 800},
                headers=headers,
            )
            if resp.status_code == 200:
                import json as _json
                data = resp.json()
                usage = data.get("usage", {})
                tokens = usage.get("total_tokens", 0)
                choices = data.get("choices", [])
                if choices:
                    raw = choices[0].get("message", {}).get("content", "")
                    try:
                        parsed = _json.loads(raw)
                        answer = parsed.get("market_intelligence", raw)
                    except (_json.JSONDecodeError, TypeError):
                        answer = raw
                    return AgentStep(
                        agent="gemini",
                        question="Provide UK energy theft market & regulatory intelligence for the board report",
                        answer=answer,
                        duration_ms=int((_time.monotonic() - t0) * 1000),
                    )
            return AgentStep(
                agent="gemini",
                question="Provide UK energy theft market & regulatory intelligence for the board report",
                answer=f"Gemini returned HTTP {resp.status_code}",
                duration_ms=int((_time.monotonic() - t0) * 1000),
            )
    except Exception as e:
        logger.error(f"Atlas Gemini market intelligence failed: {e}")
        return AgentStep(
            agent="gemini",
            question="Provide UK energy theft market & regulatory intelligence for the board report",
            answer=f"Error: {str(e)[:200]}",
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )


_MARKET_INTELLIGENCE_FALLBACK = (
    "Energy theft across Great Britain is estimated at up to £1.4 billion per year — "
    "equivalent to 1,069 GWh of gas and 2,837 GWh of electricity — adding approximately "
    "£50 annually to every consumer's bill (RECCo/Capgemini, 2023). UK suppliers confirmed "
    "just 16,581 energy thefts in 2022/23 against an Ofgem target of 41,000, a shortfall "
    "that underscores the scale of the detection gap. The regulatory environment is shifting "
    "decisively: Ofgem's reformed Theft Detection Incentive Scheme (R0173, May 2025) now "
    "compensates suppliers for desktop investigations and site visits regardless of "
    "confirmation outcome, while the new Energy Theft Unit established under REC R0233 "
    "(June 2025) partners with City of London Police to pursue organised theft. "
    "Internationally, Enel's deployment of ML-based detection across 20 million smart meters "
    "— using 500+ features from seven source systems — delivered a 70% improvement in energy "
    "recovered per inspection in Italy and over 300% in Spain (Enel/C3.ai), demonstrating "
    "that the approach scales. The academic evidence is equally compelling: Zheng et al. "
    "(IEEE Trans. Industrial Informatics, 2018, 687 citations) established CNN-based "
    "detection of non-technical losses, and recent IEEE surveys (2024–25) report ensemble "
    "methods achieving ROC-AUC of 0.88 on real smart meter data. With 39 million smart "
    "meters now installed across GB and 35 million operating in full smart mode "
    "(DESNZ, Q1 2025), UKI Gas has an unprecedented data foundation for ML-driven "
    "revenue protection — particularly in high-penetration regions like the North East (75%) "
    "where detection models can operate at maximum efficacy."
)


@api.post(
    "/agent/atlas/board-report",
    response_model=BoardReport,
    operation_id="generateBoardReport",
)
async def generate_board_report(request: Request):
    """Agent Atlas: call the Agent Bricks Multi-Agent Supervisor endpoint.

    The MAS orchestrates sub-agents (Genie for data, Gemini for market intel,
    Bedrock for narrative) and returns a consolidated board report.  Falls back
    to direct orchestration if the MAS endpoint is unavailable.
    """
    import asyncio
    import json as _json
    from datetime import datetime, timezone

    config = _config(request)
    db = _sql(request)
    mas_endpoint = config.mas_endpoint if config else ""

    now = datetime.now(timezone.utc)
    generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
    period = now.strftime("%B %Y")
    trace: list[AgentStep] = []

    # ------------------------------------------------------------------
    # Primary path: call the Agent Bricks MAS endpoint
    # ------------------------------------------------------------------
    if mas_endpoint and db:
        t0 = _time.monotonic()
        try:
            import httpx

            host = _workspace_host(db)
            headers = db._client.config.authenticate()

            mas_prompt = (
                "Generate a Revenue Protection board report for UKI Gas. "
                "First collect KPI data (total HIGH-risk accounts, top postcode sectors, "
                "precision rate, cases closed this month, revenue recovered). "
                "Then gather market and regulatory intelligence about UK energy theft. "
                "Finally compose a board-ready report as a JSON object with these fields: "
                '"executive_summary" (2-3 sentences for the CFO, lead with £ impact), '
                '"revenue_protection_overview" (3-4 sentences on detection pipeline and recovery), '
                '"regional_analysis" (2-3 sentences on geographic patterns), '
                '"market_intelligence" (the full market context from Gemini), '
                '"model_performance_summary" (2-3 sentences on ML models), '
                '"recommendations" (array of 4-6 action items starting with verbs), '
                '"kpi_highlights" (array of objects with "label", "value", "trend", "context"). '
                "Additional context: Annual theft exposure £323M, recovery target £97M/year, "
                "models are Isolation Forest + LSTM Autoencoder with composite scoring on Databricks. "
                "Respond ONLY with the JSON object."
            )

            supervisor_step = AgentStep(
                agent="supervisor",
                question="Route to sub-agents: kpi_collector → market_intelligence → narrative_writer",
                answer="Dispatching to Agent Bricks MAS...",
                duration_ms=0,
            )

            async with httpx.AsyncClient(timeout=120) as http:
                resp = await http.post(
                    f"{host}/serving-endpoints/{mas_endpoint}/invocations",
                    json={"input": [{"role": "user", "content": mas_prompt}]},
                    headers=headers,
                )

            supervisor_step.duration_ms = int((_time.monotonic() - t0) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                output_items = data.get("output", [])

                sub_agents_called: list[str] = []
                all_text_parts: list[str] = []
                for item in output_items:
                    if item.get("type") == "function_call":
                        sub_agents_called.append(item.get("name", ""))
                        try:
                            fn_args = _json.loads(item.get("arguments", "{}"))
                        except (_json.JSONDecodeError, TypeError):
                            fn_args = {}
                        fn_step = AgentStep(
                            agent=item.get("name", "unknown"),
                            question=fn_args.get(
                                "genie_query", str(fn_args)[:200] if fn_args else item.get("name", "")
                            ),
                            answer="(routed by supervisor)",
                            duration_ms=0,
                        )
                        trace.append(fn_step)
                    elif item.get("type") == "message":
                        content_parts = item.get("content", [])
                        for part in content_parts:
                            if part.get("type") == "output_text":
                                text = part.get("text", "").strip()
                                if text and not text.startswith("<name>"):
                                    all_text_parts.append(text)
                                    agent_name = item.get("id", "")
                                    for called in sub_agents_called:
                                        if called in str(agent_name):
                                            existing = [s for s in trace if s.agent == called and s.answer == "(routed by supervisor)"]
                                            if existing:
                                                existing[-1].answer = text[:300]

                raw_content = "\n\n".join(all_text_parts)
                final_text = all_text_parts[-1] if all_text_parts else ""

                agents_str = " → ".join(dict.fromkeys(sub_agents_called)) if sub_agents_called else "direct"
                supervisor_step.answer = (
                    f"MAS completed — routed through {agents_str}"
                )
                trace.insert(0, supervisor_step)

                report_data: dict = {}
                for candidate in [final_text, raw_content]:
                    try:
                        cleaned = candidate.strip()
                        if cleaned.startswith("```"):
                            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
                        report_data = _json.loads(cleaned)
                        if report_data:
                            break
                    except (_json.JSONDecodeError, TypeError, ValueError):
                        continue

                market_text = report_data.get("market_intelligence", "")
                if not market_text:
                    market_text = _MARKET_INTELLIGENCE_FALLBACK

                exec_summary = report_data.get("executive_summary", "")
                if not exec_summary:
                    exec_summary = final_text[:500] if final_text else raw_content[:500]
                if not exec_summary:
                    exec_summary = f"Agent Atlas MAS routed through {agents_str} but returned no parseable content."

                return BoardReport(
                    report_title=f"Revenue Protection Board Report — {period}",
                    period=period,
                    generated_at=generated_at,
                    executive_summary=exec_summary,
                    revenue_protection_overview=report_data.get("revenue_protection_overview", ""),
                    regional_analysis=report_data.get("regional_analysis", ""),
                    market_intelligence=market_text,
                    model_performance_summary=report_data.get("model_performance_summary", ""),
                    recommendations=report_data.get("recommendations", []),
                    kpi_highlights=[
                        BoardReportKPI(
                            label=str(kpi.get("label", "")),
                            value=str(kpi.get("value", "")),
                            trend=str(kpi.get("trend", "")),
                            context=str(kpi.get("context", "")),
                        )
                        for kpi in report_data.get("kpi_highlights", [])
                        if isinstance(kpi, dict)
                    ],
                    agent_trace=trace,
                    genie_questions_asked=len([s for s in sub_agents_called if s == "kpi_collector"]),
                    bedrock_tokens_used=0,
                    gemini_tokens_used=0,
                )

            else:
                supervisor_step.answer = f"MAS returned HTTP {resp.status_code} — falling back to direct orchestration"
                trace.append(supervisor_step)
                logger.warning(f"MAS endpoint returned {resp.status_code}, falling back")

        except Exception as e:
            logger.error(f"MAS endpoint call failed: {type(e).__name__}: {e}")
            trace.append(AgentStep(
                agent="supervisor",
                question="Route to sub-agents",
                answer=f"MAS unavailable ({str(e)[:120]}) — falling back to direct orchestration",
                duration_ms=int((_time.monotonic() - t0) * 1000),
            ))

    # ------------------------------------------------------------------
    # Fallback: direct orchestration (Genie + Gemini + Bedrock)
    # ------------------------------------------------------------------
    genie_space_id = (config.genie_space_id if config else "").strip()
    ai_endpoint = _resolve_ai_endpoint(request, config)
    gemini_endpoint = config.gemini_gateway_endpoint if config else ""

    genie_tasks: list = []
    if genie_space_id and db:
        auth = _genie_headers(request)
        if auth:
            host, headers, fallback = auth
            genie_tasks = [
                _atlas_query_genie(host, headers, fallback, genie_space_id, q)
                for q in ATLAS_GENIE_QUESTIONS
            ]
    if genie_tasks:
        trace.extend(list(await asyncio.gather(*genie_tasks)))

    kpi_data: dict[str, str] = {}
    if db:
        try:
            kpi_rows = db.execute("""
                SELECT
                    COUNT(CASE WHEN risk_tier = 'HIGH' THEN 1 END) AS high_risk_count,
                    COUNT(CASE WHEN risk_tier = 'MEDIUM' THEN 1 END) AS medium_risk_count,
                    ROUND(AVG(composite_risk_score), 2) AS avg_composite_score,
                    COUNT(*) AS total_flagged
                FROM anomaly_scores
                WHERE risk_tier IN ('HIGH', 'MEDIUM')
            """) or []
            if kpi_rows:
                r = kpi_rows[0]
                kpi_data["high_risk_accounts"] = str(r.get("high_risk_count", "N/A"))
                kpi_data["medium_risk_accounts"] = str(r.get("medium_risk_count", "N/A"))
                kpi_data["avg_composite_score"] = str(r.get("avg_composite_score", "N/A"))
                kpi_data["total_flagged"] = str(r.get("total_flagged", "N/A"))
        except Exception as e:
            logger.error(f"Atlas SQL KPI query failed: {e}")

    if db:
        try:
            case_rows = db.execute("""
                SELECT
                    COUNT(CASE WHEN closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE()) THEN 1 END) AS closed_this_month,
                    COUNT(CASE WHEN outcome = 'THEFT_CONFIRMED' AND closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE()) THEN 1 END) AS confirmed_this_month,
                    ROUND(SUM(CASE WHEN outcome = 'THEFT_CONFIRMED' AND closed_timestamp >= DATE_TRUNC('month', CURRENT_DATE()) THEN revenue_recovered_gbp ELSE 0 END), 0) AS recovered_this_month
                FROM investigation_cases
            """) or []
            if case_rows:
                r = case_rows[0]
                kpi_data["closed_this_month"] = str(r.get("closed_this_month", "N/A"))
                kpi_data["confirmed_theft_this_month"] = str(r.get("confirmed_this_month", "N/A"))
                kpi_data["recovered_this_month_gbp"] = str(r.get("recovered_this_month", "N/A"))
        except Exception as e:
            logger.error(f"Atlas case SQL failed: {e}")

    market_intel_text = ""
    if gemini_endpoint and db:
        try:
            mi_host = _workspace_host(db)
            mi_headers = db._client.config.authenticate()
            gemini_step = await _atlas_market_intelligence(
                mi_host, mi_headers, gemini_endpoint, kpi_data,
            )
            is_gemini_error = gemini_step.answer.startswith("Error:") or gemini_step.answer.startswith("Gemini returned")
            if not is_gemini_error:
                market_intel_text = gemini_step.answer
            else:
                logger.warning(f"Gemini call failed ({gemini_step.answer}), using fallback market intelligence")
                gemini_step.answer = _MARKET_INTELLIGENCE_FALLBACK
            trace.append(gemini_step)
        except Exception as e:
            logger.error(f"Atlas Gemini step failed: {e}")

    if not market_intel_text:
        market_intel_text = _MARKET_INTELLIGENCE_FALLBACK

    genie_context = "\n\n".join(
        f"Question: {s.question}\nAnswer: {s.answer}"
        + (f"\nData: {_json.dumps(s.data[:5])}" if s.data else "")
        for s in trace if s.agent == "genie"
    )
    sql_context = "\n".join(f"- {k}: {v}" for k, v in kpi_data.items())

    report = BoardReport(
        report_title=f"Revenue Protection Board Report — {period}",
        period=period,
        generated_at=generated_at,
        executive_summary="",
        revenue_protection_overview="",
        regional_analysis="",
        market_intelligence=market_intel_text,
        model_performance_summary="",
        recommendations=[],
        kpi_highlights=[],
        agent_trace=trace,
        genie_questions_asked=len([s for s in trace if s.agent == "genie"]),
        bedrock_tokens_used=0,
        gemini_tokens_used=0,
    )

    if ai_endpoint and db:
        t0 = _time.monotonic()
        try:
            import httpx
            host = _workspace_host(db)
            headers = db._client.config.authenticate()

            prompt = f"""You are Agent Atlas, an AI assistant that generates monthly Revenue Protection board reports for Susie Thornton, Head of Revenue Protection at UKI Gas.

Using the data below, produce a board report as a JSON object with these fields:

1. "executive_summary": 2-3 sentences for the CFO. Lead with £ impact.
2. "revenue_protection_overview": 3-4 sentences on the current detection pipeline, case volumes, and recovery.
3. "regional_analysis": 2-3 sentences on geographic patterns and postcode clusters.
4. "model_performance_summary": 2-3 sentences on ML model accuracy, precision, and scoring coverage.
5. "recommendations": Array of 4-6 specific action items for the board, each starting with a verb.
6. "kpi_highlights": Array of objects with "label", "value", "trend" (up/down/flat), "context" (one sentence).

Data from Genie queries:
{genie_context if genie_context else "No Genie data available — use SQL KPIs below."}

SQL KPIs:
{sql_context if sql_context else "No SQL KPIs available."}

Market intelligence (from Gemini — cite where relevant):
{market_intel_text}

Additional context:
- Annual theft exposure: £323M (RECCo estimate × UKI Gas market share)
- Recovery target: £97M/year
- Models: Isolation Forest (tabular anomaly), LSTM Autoencoder (temporal patterns), composite scoring
- The platform runs on Databricks with Unity Catalog governance

Respond ONLY with the JSON object. No markdown, no code fences."""

            async with httpx.AsyncClient(timeout=60) as http:
                resp = await http.post(
                    f"{host}/serving-endpoints/{ai_endpoint}/invocations",
                    json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 1200},
                    headers=headers,
                )
            bedrock_tokens = 0
            bedrock_status = resp.status_code
            if resp.status_code != 200:
                logger.warning(f"Bedrock endpoint returned HTTP {resp.status_code}: {resp.text[:200]}")
            bedrock_raw = ""
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                bedrock_tokens = usage.get("total_tokens", 0)
                choices = data.get("choices", [])
                if choices:
                    bedrock_raw = choices[0].get("message", {}).get("content", "")
                    try:
                        parsed = _json.loads(bedrock_raw)
                        report.executive_summary = parsed.get("executive_summary", "")
                        report.revenue_protection_overview = parsed.get("revenue_protection_overview", "")
                        report.regional_analysis = parsed.get("regional_analysis", "")
                        report.model_performance_summary = parsed.get("model_performance_summary", "")
                        report.recommendations = parsed.get("recommendations", [])
                        report.kpi_highlights = [
                            BoardReportKPI(
                                label=str(kpi.get("label", "")),
                                value=str(kpi.get("value", "")),
                                trend=str(kpi.get("trend", "")),
                                context=str(kpi.get("context", "")),
                            )
                            for kpi in parsed.get("kpi_highlights", [])
                            if isinstance(kpi, dict)
                        ]
                    except (_json.JSONDecodeError, TypeError, ValueError) as parse_err:
                        logger.warning(f"Bedrock JSON parse failed: {parse_err}")
                        report.executive_summary = bedrock_raw

            bedrock_answer = report.executive_summary
            if not bedrock_answer:
                if bedrock_status != 200:
                    bedrock_answer = f"Bedrock HTTP {bedrock_status}: {resp.text[:150]}"
                elif bedrock_raw:
                    bedrock_answer = bedrock_raw[:200]
                else:
                    bedrock_answer = f"HTTP {bedrock_status}, no choices in response"
            elif len(bedrock_answer) > 200:
                bedrock_answer = bedrock_answer[:200] + "..."
            bedrock_step = AgentStep(
                agent="bedrock",
                question="Compose executive board report from collected data",
                answer=bedrock_answer,
                duration_ms=int((_time.monotonic() - t0) * 1000),
            )
            report.agent_trace.append(bedrock_step)
            report.bedrock_tokens_used = bedrock_tokens

            gemini_steps = [s for s in report.agent_trace if s.agent == "gemini"]
            if gemini_steps:
                report.gemini_tokens_used = sum(
                    len(s.answer.split()) * 2 for s in gemini_steps
                )

        except Exception as e:
            logger.error(f"Atlas Bedrock call failed: {type(e).__name__}: {e}")
            report.agent_trace.append(AgentStep(
                agent="bedrock",
                question="Compose executive board report from collected data",
                answer=f"Bedrock unavailable: {type(e).__name__}: {str(e)[:150]}",
                duration_ms=int((_time.monotonic() - t0) * 1000),
            ))

    if not report.executive_summary:
        high = kpi_data.get("high_risk_accounts", "N/A")
        medium = kpi_data.get("medium_risk_accounts", "N/A")
        closed = kpi_data.get("closed_this_month", "N/A")
        confirmed = kpi_data.get("confirmed_theft_this_month", "N/A")
        recovered = kpi_data.get("recovered_this_month_gbp", "N/A")

        report.executive_summary = (
            f"Revenue Protection currently tracks {high} HIGH-risk and {medium} MEDIUM-risk "
            f"accounts against a £323M annual theft exposure (RECCo estimate × UKI Gas market share). "
            f"{closed} cases closed this month with {confirmed} confirmed thefts."
        )
        if recovered and recovered != "N/A":
            try:
                rec_f = float(recovered)
                report.executive_summary += f" £{rec_f:,.0f} recovered this month."
            except (ValueError, TypeError):
                pass

        report.revenue_protection_overview = (
            f"The ML detection pipeline (Isolation Forest + LSTM Autoencoder) has scored "
            f"{kpi_data.get('total_flagged', 'N/A')} accounts with an average composite risk score "
            f"of {kpi_data.get('avg_composite_score', 'N/A')}. {high} accounts are classified HIGH risk "
            f"and {medium} as MEDIUM risk, feeding into the investigation case pipeline."
        )

        genie_answers = [s for s in trace if s.agent == "genie" and s.answer and s.answer != "No answer"]
        if genie_answers:
            report.regional_analysis = " ".join(
                s.answer[:200] for s in genie_answers
                if "postcode" in s.question.lower() or "region" in s.question.lower()
            )[:500] or "Regional analysis available via Genie — ask about postcode sectors or regional breakdown."

        report.model_performance_summary = (
            "Composite scoring combines Isolation Forest (35% weight), LSTM Autoencoder (30%), "
            "cohort deviation (20%), comms gap frequency (10%), and consumption drop (5%). "
            "Risk tiers assigned at p92 (HIGH) and p82 (MEDIUM) quantile thresholds."
        )

        report.recommendations = [
            "Prioritise top postcode sectors for geographic cluster investigations",
            "Accelerate triage of cases open longer than 5 days",
            "Review model precision monthly and retrain quarterly",
            "Expand smart meter comms gap monitoring to gas meters",
        ]

        report.kpi_highlights = []
        if high != "N/A":
            report.kpi_highlights.append(BoardReportKPI(label="HIGH Risk Accounts", value=str(high), trend="up", context="Accounts flagged by ML composite scoring"))
        if recovered and recovered != "N/A":
            try:
                report.kpi_highlights.append(BoardReportKPI(label="Recovered (Month)", value=f"£{float(recovered):,.0f}", trend="up", context="Revenue recovered from confirmed theft cases"))
            except (ValueError, TypeError):
                pass
        if kpi_data.get("avg_composite_score", "N/A") != "N/A":
            report.kpi_highlights.append(BoardReportKPI(label="Avg Risk Score", value=str(kpi_data["avg_composite_score"]), trend="flat", context="Mean composite score across flagged accounts"))

    return report


# ---------------------------------------------------------------------------
# AI Governance
# ---------------------------------------------------------------------------

_PII_MATRIX_DEFAULTS = [
    PIIFieldAccess(table_name="smart_meter_reads", field_name="account_id", pii_tag="PII", regulatory_basis="ELEXON BSC — links to domestic customer"),
    PIIFieldAccess(table_name="smart_meter_reads", field_name="consumption_kwh", pii_tag="PII", regulatory_basis="Ofgem DAPF — half-hourly data is personal when linked to MPAN/premises"),
    PIIFieldAccess(table_name="smart_meter_reads", field_name="postcode", pii_tag="PII", regulatory_basis="ICO — identifies premises"),
    PIIFieldAccess(table_name="meters", field_name="mpan", pii_tag="PII", regulatory_basis="ELEXON BSC — directly identifies premises"),
    PIIFieldAccess(table_name="meters", field_name="meter_serial_number", pii_tag="PII", regulatory_basis="Ofgem — identifies physical device at premises"),
    PIIFieldAccess(table_name="property_reference", field_name="account_id", pii_tag="PII", regulatory_basis="Links to domestic customer"),
    PIIFieldAccess(table_name="property_reference", field_name="postcode", pii_tag="PII", regulatory_basis="Identifies premises"),
    PIIFieldAccess(table_name="anomaly_scores", field_name="account_id", pii_tag="PII", regulatory_basis="Links scored risk to domestic customer"),
    PIIFieldAccess(table_name="anomaly_scores", field_name="postcode_sector", pii_tag="PII", regulatory_basis="Identifies area of premises"),
    PIIFieldAccess(table_name="investigation_cases", field_name="account_id", pii_tag="PII", regulatory_basis="Links investigation to customer"),
    PIIFieldAccess(table_name="investigation_cases", field_name="investigator_id", pii_tag="PII (staff)", regulatory_basis="Identifies UKI Gas employee"),
    PIIFieldAccess(table_name="investigation_cases", field_name="llm_summary", pii_tag="PII (derived)", regulatory_basis="LLM output may contain account-linked PII from prompt context"),
]


@api.get(
    "/governance/pii-matrix",
    response_model=list[PIIFieldAccess],
    operation_id="getPIIMatrix",
)
async def get_pii_matrix(request: Request):
    """PII field classification matrix — reads tags from UC INFORMATION_SCHEMA."""
    cached = _cache_get("pii_matrix")
    if cached is not None:
        return cached

    db = _sql(request)
    cfg = _config(request)
    if db and cfg:
        try:
            schema = cfg.schema_name
            rows = db.execute(f"""
                SELECT
                    ct.table_name,
                    ct.column_name AS field_name,
                    MAX(CASE WHEN ct.tag_name = 'pii_classification' THEN ct.tag_value END) AS pii_tag,
                    MAX(CASE WHEN ct.tag_name = 'regulatory_basis' THEN ct.tag_value END) AS regulatory_basis
                FROM information_schema.column_tags ct
                WHERE ct.schema_name = '{schema}'
                  AND ct.tag_name IN ('pii_classification', 'regulatory_basis')
                GROUP BY ct.table_name, ct.column_name
                ORDER BY ct.table_name, ct.column_name
            """)
            if rows:
                result = [
                    PIIFieldAccess(
                        table_name=r["table_name"],
                        field_name=r["field_name"],
                        pii_tag=r.get("pii_tag") or "PII",
                        regulatory_basis=r.get("regulatory_basis") or "",
                    )
                    for r in rows
                ]
                _cache_set("pii_matrix", result)
                return result
        except Exception as e:
            logger.warning(f"INFORMATION_SCHEMA.column_tags query failed (using defaults): {e}")

    return _PII_MATRIX_DEFAULTS


_COLUMN_METADATA_DEFAULTS = [
    ColumnMetadata(table_name="property_reference", column_name="account_id", comment="Unique customer account identifier — links to MPAN and premises", pii_tag="PII", regulatory_basis="ELEXON BSC — links to domestic customer"),
    ColumnMetadata(table_name="property_reference", column_name="postcode", comment="Full UK postcode of customer premises", pii_tag="PII", regulatory_basis="ICO — identifies premises; masked to sector level downstream"),
    ColumnMetadata(table_name="property_reference", column_name="region", comment="UK geographic region (e.g. London, South East)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="property_reference", column_name="property_type", comment="Type of dwelling (terraced, semi-detached, flat, etc.)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="property_reference", column_name="council_tax_band", comment="Council tax valuation band A–H", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="property_reference", column_name="floor_area_m2", comment="Approximate floor area in square metres", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="property_reference", column_name="epc_rating", comment="Energy Performance Certificate rating A–G", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="property_reference", column_name="latitude", comment="Approximate latitude of premises", pii_tag="Quasi-PII", regulatory_basis="ICO — combined with longitude can identify premises"),
    ColumnMetadata(table_name="property_reference", column_name="longitude", comment="Approximate longitude of premises", pii_tag="Quasi-PII", regulatory_basis="ICO — combined with latitude can identify premises"),
    ColumnMetadata(table_name="meters", column_name="meter_id", comment="Internal meter identifier", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="meters", column_name="account_id", comment="Links meter to customer account", pii_tag="PII", regulatory_basis="ELEXON BSC — links to domestic customer"),
    ColumnMetadata(table_name="meters", column_name="mpan", comment="Meter Point Administration Number — directly identifies premises", pii_tag="PII", regulatory_basis="ELEXON BSC — directly identifies premises"),
    ColumnMetadata(table_name="meters", column_name="meter_serial_number", comment="Physical meter device serial number", pii_tag="PII", regulatory_basis="Ofgem — identifies physical device at premises"),
    ColumnMetadata(table_name="meters", column_name="fuel_type", comment="Gas or electricity", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="meters", column_name="meter_type", comment="Smart meter generation (SMETS1, SMETS2)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="meters", column_name="install_date", comment="Date the meter was installed", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="meters", column_name="last_read_timestamp", comment="Timestamp of the most recent meter read", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="smart_meter_reads", column_name="account_id", comment="Links consumption data to customer account", pii_tag="PII", regulatory_basis="ELEXON BSC — links to domestic customer"),
    ColumnMetadata(table_name="smart_meter_reads", column_name="read_timestamp", comment="Half-hourly read timestamp", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="smart_meter_reads", column_name="fuel_type", comment="Gas or electricity", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="smart_meter_reads", column_name="consumption_kwh", comment="Half-hourly energy consumption in kWh — personal data when linked", pii_tag="PII", regulatory_basis="Ofgem DAPF — half-hourly data is personal when linked to MPAN/premises"),
    ColumnMetadata(table_name="smart_meter_reads", column_name="read_quality", comment="Read quality flag: actual, estimated, or missing", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="smart_meter_reads", column_name="comms_gap_flag", comment="True if the DCC communication link was interrupted", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="smart_meter_reads", column_name="postcode", comment="Customer postcode (denormalised for feature engineering)", pii_tag="PII", regulatory_basis="ICO — identifies premises"),
    ColumnMetadata(table_name="smart_meter_reads", column_name="property_type", comment="Property type (denormalised for cohort features)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="smart_meter_reads", column_name="council_tax_band", comment="Council tax band (denormalised for cohort features)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="account_id", comment="Links ML risk score to customer account", pii_tag="PII", regulatory_basis="Links scored risk to domestic customer"),
    ColumnMetadata(table_name="anomaly_scores", column_name="score_timestamp", comment="Timestamp when the ML scoring batch ran", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="fuel_type", comment="Fuel type scored (electricity or gas)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="isolation_forest_score", comment="Isolation Forest anomaly score (0–1, higher = more anomalous)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="lstm_deviation_score", comment="LSTM autoencoder deviation score — temporal anomaly signal", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="cohort_deviation_score", comment="Cohort deviation — how far this account deviates from similar properties", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="comms_gap_count_30d", comment="Count of DCC communication gaps in the last 30 days", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="consumption_drop_pct", comment="Percentage drop in consumption vs prior 30-day rolling average", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="composite_risk_score", comment="Weighted ensemble risk score (0–1) from all ML signals", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="risk_tier", comment="Risk classification: HIGH (≥0.75), MEDIUM (≥0.50), LOW (<0.50)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="postcode_sector", comment="Postcode sector (e.g. E1 4) — identifies geographic area", pii_tag="PII", regulatory_basis="Identifies area of premises"),
    ColumnMetadata(table_name="anomaly_scores", column_name="model_version", comment="Combined model version string (e.g. if_v3_lstm_v3)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="anomaly_scores", column_name="investigation_status", comment="Current investigation status: OPEN, IN_PROGRESS, CLOSED", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="investigation_cases", column_name="case_id", comment="Unique investigation case reference", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="investigation_cases", column_name="account_id", comment="Links investigation to customer account", pii_tag="PII", regulatory_basis="Links investigation to customer"),
    ColumnMetadata(table_name="investigation_cases", column_name="opened_timestamp", comment="Timestamp when the investigation was opened", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="investigation_cases", column_name="investigator_id", comment="Assigned investigator employee ID", pii_tag="PII (staff)", regulatory_basis="Identifies UKI Gas employee"),
    ColumnMetadata(table_name="investigation_cases", column_name="llm_summary", comment="LLM-generated case summary — may contain account-linked PII from prompt", pii_tag="PII (derived)", regulatory_basis="LLM output may contain account-linked PII from prompt context"),
    ColumnMetadata(table_name="investigation_cases", column_name="field_dispatch_doc", comment="LLM-generated field dispatch document", pii_tag="PII (derived)", regulatory_basis="LLM output may reference account details"),
    ColumnMetadata(table_name="investigation_cases", column_name="outcome", comment="Investigation outcome: THEFT_CONFIRMED, FALSE_POSITIVE, or PENDING", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="investigation_cases", column_name="revenue_recovered_gbp", comment="Revenue recovered through back-billing (GBP)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="investigation_cases", column_name="closed_timestamp", comment="Timestamp when the investigation was closed (null if pending)", pii_tag=None, regulatory_basis=None),
    ColumnMetadata(table_name="investigation_cases", column_name="region", comment="Geographic region of the investigated account", pii_tag=None, regulatory_basis=None),
]

_DATA_TABLES = list({m.table_name for m in _COLUMN_METADATA_DEFAULTS})


@api.get(
    "/governance/column-metadata",
    response_model=list[ColumnMetadata],
    operation_id="getColumnMetadata",
)
async def get_column_metadata(request: Request):
    """All column metadata (comments + PII tags) from UC.

    Tries DESCRIBE TABLE + information_schema.column_tags first.
    Falls back to embedded metadata that mirrors what notebook 05 applies.
    """
    cached = _cache_get("column_metadata")
    if cached is not None:
        return cached

    db = _sql(request)
    if not db:
        return _COLUMN_METADATA_DEFAULTS

    result: list[ColumnMetadata] = []
    from_uc = False
    try:
        for table in _DATA_TABLES:
            try:
                desc_rows = db.execute(f"DESCRIBE TABLE {table}")
                for r in desc_rows:
                    col_name = r.get("col_name", "")
                    if not col_name or col_name.startswith("#"):
                        continue
                    result.append(ColumnMetadata(
                        table_name=table,
                        column_name=col_name,
                        comment=r.get("comment") or None,
                        pii_tag=None,
                        regulatory_basis=None,
                    ))
                from_uc = True
            except Exception:
                try:
                    cols = db.get_columns(table)
                    for col_name in cols:
                        result.append(ColumnMetadata(
                            table_name=table,
                            column_name=col_name,
                            comment=None,
                            pii_tag=None,
                            regulatory_basis=None,
                        ))
                    from_uc = True
                except Exception as e:
                    logger.warning(f"Cannot get columns for {table}: {e}")

        if from_uc and result:
            tag_lookup: dict[str, dict[str, str]] = {}
            try:
                cfg = _config(request)
                schema = cfg.schema_name if cfg else "energy_theft_protection"
                tag_rows = db.execute(f"""
                    SELECT table_name, column_name, tag_name, tag_value
                    FROM information_schema.column_tags
                    WHERE schema_name = '{schema}'
                      AND tag_name IN ('pii_classification', 'regulatory_basis')
                """)
                for t in (tag_rows or []):
                    key = f"{t['table_name']}.{t['column_name']}"
                    tag_lookup.setdefault(key, {})[t["tag_name"]] = t["tag_value"]
            except Exception as e:
                logger.warning(f"column_tags query failed (using defaults): {e}")
                for m in _COLUMN_METADATA_DEFAULTS:
                    if m.pii_tag:
                        key = f"{m.table_name}.{m.column_name}"
                        tag_lookup.setdefault(key, {})["pii_classification"] = m.pii_tag
                        if m.regulatory_basis:
                            tag_lookup[key]["regulatory_basis"] = m.regulatory_basis

            for item in result:
                key = f"{item.table_name}.{item.column_name}"
                tags = tag_lookup.get(key, {})
                item.pii_tag = tags.get("pii_classification")
                item.regulatory_basis = tags.get("regulatory_basis")

            _cache_set("column_metadata", result)
            return result
    except Exception as e:
        logger.warning(f"Column metadata query failed: {e}")

    _cache_set("column_metadata", _COLUMN_METADATA_DEFAULTS)
    return _COLUMN_METADATA_DEFAULTS


@api.get(
    "/governance/components",
    response_model=list[AIComponentRegistryItem],
    operation_id="getAIComponents",
)
async def get_ai_components(request: Request):
    """AI component registry showing models, LLMs, and their PII access."""
    cached = _cache_get("ai_components")
    if cached is not None:
        return cached

    last_run_str: str | None = None
    records_scored: int | None = None
    db = _sql(request)
    if db:
        try:
            rows = db.execute("""
                SELECT MAX(score_timestamp) AS last_run, COUNT(*) AS total
                FROM anomaly_scores
            """)
            if rows and rows[0].get("last_run"):
                from datetime import datetime as _dt
                raw = rows[0]["last_run"]
                if isinstance(raw, str):
                    last_run_str = raw[:16].replace("T", " ")
                else:
                    last_run_str = raw.strftime("%Y-%m-%d %H:%M")
                records_scored = int(rows[0]["total"] or 0)
        except Exception as e:
            logger.error(f"Component batch run query failed: {e}")

    config = _config(request)
    db = _sql(request)
    ws = config.workspace_url if config else ""
    cat = db.resolve_catalog() if db else (config.catalog if config else "")
    sch = config.schema_name if config else ""
    genie_id = config.genie_space_id if config else ""
    result = [
        AIComponentRegistryItem(
            component_name="Theft Risk Scorer",
            component_type="ML Model",
            model_name="isolation_forest_theft_v3",
            pii_fields_accessed=["account_id", "consumption_kwh", "postcode", "property_type", "council_tax_band"],
            last_run=last_run_str,
            records_scored=records_scored,
            databricks_url=f"{ws}/explore/data/models/{cat}/{sch}/isolation_forest_theft_v3",
        ),
        AIComponentRegistryItem(
            component_name="Sequence Anomaly Detector",
            component_type="ML Model",
            model_name="lstm_consumption_v2",
            pii_fields_accessed=["account_id", "consumption_kwh", "mpan"],
            last_run=last_run_str,
            records_scored=records_scored,
            databricks_url=f"{ws}/explore/data/models/{cat}/{sch}/lstm_consumption_v2",
        ),
        AIComponentRegistryItem(
            component_name="Case Summariser",
            component_type="LLM (Bedrock via AI Gateway)",
            model_name="anthropic.claude-3-sonnet",
            pii_fields_accessed=["account_id", "postcode", "consumption_kwh", "composite_risk_score", "property_type", "council_tax_band"],
            databricks_url=f"{ws}/ml/endpoints/{config.ai_gateway_endpoint if config else 'energy-theft-bedrock-gateway'}",
        ),
        AIComponentRegistryItem(
            component_name="Market Intelligence",
            component_type="LLM (Gemini via AI Gateway)",
            model_name="gemini-2.0-flash",
            pii_fields_accessed=["None — uses aggregated KPIs only"],
            databricks_url=f"{ws}/ml/endpoints/{config.gemini_gateway_endpoint if config else 'energy-theft-gemini-gateway'}",
        ),
        AIComponentRegistryItem(
            component_name="Executive Intelligence",
            component_type="Genie Space",
            model_name="Revenue Protection Executive Intelligence",
            pii_fields_accessed=["All fields in queried tables (UC-governed)"],
            databricks_url=f"{ws}/genie/rooms/{genie_id}",
        ),
    ]
    if last_run_str is not None:
        _cache_set("ai_components", result)
    return result


# ---------------------------------------------------------------------------
# External Lineage — fake Power BI reports downstream of UC tables
# ---------------------------------------------------------------------------

# Cached for 10 minutes (rarely changes — Catalog Explorer additions are
# weekly at most). Mirrors the in-memory pattern used by column metadata.
_EXTERNAL_LINEAGE_TTL = 10 * 60


_LINEAGE_DEFS_CACHE: Any | None = None


def _load_shared_lineage_defs():
    """Import the shared external-lineage definitions.

    Canonical source: scripts/setup/external_lineage_objects.py. Hatch
    force-includes that same file into the wheel at
    energy_theft_detection/_external_lineage_objects.py so the deployed
    backend can `from energy_theft_detection import _external_lineage_objects`
    without depending on the source tree at runtime.

    For editable installs (local dev / pytest) the wheel copy isn't present,
    so we transparently fall back to loading the canonical file from disk via
    importlib.util — keeps a single source of truth in both modes.
    """
    global _LINEAGE_DEFS_CACHE
    if _LINEAGE_DEFS_CACHE is not None:
        return _LINEAGE_DEFS_CACHE
    try:
        from .. import _external_lineage_objects as _shared  # type: ignore[attr-defined]
        _LINEAGE_DEFS_CACHE = _shared
        return _shared
    except ImportError:
        pass
    try:
        import importlib.util as _ilu
        import sys as _sys
        from pathlib import Path as _Path
        here = _Path(__file__).resolve()
        candidates = [
            here.parents[3] / "scripts" / "setup" / "external_lineage_objects.py",
            here.parents[2] / "scripts" / "setup" / "external_lineage_objects.py",
        ]
        for cand in candidates:
            if cand.is_file():
                mod_name = "energy_theft_detection_lineage_defs"
                spec = _ilu.spec_from_file_location(mod_name, str(cand))
                if spec and spec.loader:
                    mod = _ilu.module_from_spec(spec)
                    # Register in sys.modules BEFORE exec — required so that
                    # @dataclass introspection in the file can look up the
                    # owning module by __module__.
                    _sys.modules[mod_name] = mod
                    spec.loader.exec_module(mod)
                    _LINEAGE_DEFS_CACHE = mod
                    return mod
        raise FileNotFoundError(
            "external_lineage_objects.py not found in wheel or scripts/setup/."
        )
    except Exception as exc:
        logger.error(f"Failed to load external lineage definitions: {exc}")
        raise


def _fallback_external_lineage() -> ExternalLineageResponse:
    """Build response from the static shared module — used when the live UC
    read fails or returns nothing for the demo namespace."""
    shared = _load_shared_lineage_defs()
    nodes = [
        ExternalLineageNode(
            name=r.name,
            display=r.display,
            system_type="POWER_BI",
            entity_type=r.entity_type,
            url=r.url,
            description=r.description,
            columns=list(r.columns),
        )
        for r in shared.POWER_BI_REPORTS
    ]
    edges = [
        ExternalLineageEdge(
            source_table=e.source_table,
            source_column=e.source_column,
            target_external=e.target_pbi,
            target_column=e.target_column,
        )
        for e in shared.COLUMN_EDGES
    ]
    return ExternalLineageResponse(nodes=nodes, edges=edges, source="fallback")


def _live_external_lineage(db: SQLClient) -> ExternalLineageResponse | None:
    """Read external_metadata + external_lineage from UC via the SDK.

    Returns None if the live read can't be completed (privileges, SDK
    version, network) — callers should fall back to the static defaults.
    Filters to objects tagged with our DEMO_PROPERTIES marker so we don't
    surface unrelated metastore-wide objects.
    """
    shared = _load_shared_lineage_defs()
    ws = db._client
    if not hasattr(ws, "external_metadata"):
        return None

    try:
        marker_key = "created_by"
        marker_val = shared.DEMO_PROPERTIES.get(marker_key, "")
        demo_names = {r.name for r in shared.POWER_BI_REPORTS}

        em_records = []
        for em in ws.external_metadata.list_external_metadata():
            props = getattr(em, "properties", {}) or {}
            name = getattr(em, "name", "")
            if (props.get(marker_key) == marker_val) or (name in demo_names):
                em_records.append(em)

        if not em_records:
            return None

        nodes: list[ExternalLineageNode] = []
        for em in em_records:
            sys_type = getattr(em, "system_type", "POWER_BI")
            sys_type_val = sys_type.value if hasattr(sys_type, "value") else str(sys_type)
            nodes.append(
                ExternalLineageNode(
                    name=em.name,
                    display=(getattr(em, "description", "") or em.name).split("\n")[0][:80],
                    system_type=sys_type_val,
                    entity_type=getattr(em, "entity_type", "report"),
                    url=getattr(em, "url", "") or "",
                    description=getattr(em, "description", "") or "",
                    columns=list(getattr(em, "columns", []) or []),
                )
            )

        # Enrich displays from the static module so the UI matches the bootstrap
        # without depending on the description first-line trick.
        static_displays = {r.name: r.display for r in shared.POWER_BI_REPORTS}
        for n in nodes:
            if n.name in static_displays:
                n.display = static_displays[n.name]

        # Lineage edges — query per target external object, UPSTREAM direction.
        from databricks.sdk.service import catalog as _cat
        edges: list[ExternalLineageEdge] = []
        for em in em_records:
            obj_info = _cat.ExternalLineageObject(
                external_metadata=_cat.ExternalLineageExternalMetadata(name=em.name)
            )
            try:
                for info in ws.external_lineage.list_external_lineage_relationships(
                    object_info=obj_info,
                    lineage_direction=_cat.LineageDirection.UPSTREAM,
                ):
                    rel = getattr(info, "external_lineage_info", None)
                    if not rel:
                        continue
                    src = getattr(rel, "source", None)
                    src_tbl = getattr(src, "table", None) if src else None
                    src_fqn = getattr(src_tbl, "name", "") if src_tbl else ""
                    # FQN -> short table name (catalog.schema.table)
                    src_short = src_fqn.split(".")[-1] if src_fqn else ""
                    col_rels = getattr(rel, "columns", []) or []
                    for cr in col_rels:
                        edges.append(
                            ExternalLineageEdge(
                                source_table=src_short,
                                source_column=getattr(cr, "source", "") or "",
                                target_external=em.name,
                                target_column=getattr(cr, "target", "") or "",
                            )
                        )
            except Exception as e:
                logger.warning(f"list_external_lineage_relationships failed for {em.name}: {e}")

        if not edges:
            # Nodes exist but no edges yet — looks empty in the UI. Treat as
            # incomplete and fall back to defaults so the demo still demos.
            return None

        return ExternalLineageResponse(nodes=nodes, edges=edges, source="live")

    except Exception as e:
        logger.warning(f"Live external-lineage read failed: {e}")
        return None


@api.get(
    "/governance/external-lineage",
    response_model=ExternalLineageResponse,
    operation_id="getExternalLineage",
)
async def get_external_lineage(request: Request):
    """External Power BI lineage — Catalog Explorer's external_metadata API.

    Returns the four fake Power BI reports we register as UC external objects
    via `notebooks/09_configure_external_lineage.py`, with column-level
    upstream relationships back to `anomaly_scores`, `investigation_cases`,
    `smart_meter_reads`, and `model_performance_log`.

    Live UC read first; falls back transparently to the static shared module
    (with `source="fallback"` on the response) when the metastore is not
    reachable or hasn't been bootstrapped yet.
    """
    cached = _cache_get_ttl("external_lineage", _EXTERNAL_LINEAGE_TTL)
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        live = _live_external_lineage(db)
        if live is not None:
            _cache_set("external_lineage", live)
            return live

    fb = _fallback_external_lineage()
    _cache_set("external_lineage", fb)
    return fb


_GATEWAY_ENDPOINTS = (
    "energy-theft-bedrock-gateway",
    "energy-theft-gemini-gateway",
    "energy-theft-openai-gateway",
    "energy-theft-llama-gateway",
)
_GATEWAY_IN_CLAUSE = ", ".join(f"'{e}'" for e in _GATEWAY_ENDPOINTS)

_COST_PER_TOKEN: dict[str, tuple[float, float]] = {
    "energy-theft-bedrock-gateway": (0.25 / 1e6, 1.25 / 1e6),      # Claude 3.5 Haiku
    "energy-theft-gemini-gateway": (0.075 / 1e6, 0.30 / 1e6),      # Gemini 2.0 Flash
    "energy-theft-openai-gateway": (0.15 / 1e6, 0.60 / 1e6),       # GPT-4o Mini via FMAPI
    "energy-theft-llama-gateway": (0.07 / 1e6, 0.07 / 1e6),        # Llama 3.1 70B via FMAPI (DBRX pricing)
}
_DEFAULT_COST = (0.25 / 1e6, 1.25 / 1e6)

def _row_cost(endpoint_name: str, input_tokens: int, output_tokens: int) -> float:
    inp_rate, out_rate = _COST_PER_TOKEN.get(endpoint_name, _DEFAULT_COST)
    return round(input_tokens * inp_rate + output_tokens * out_rate, 6)


@api.get(
    "/governance/audit",
    response_model=list[AIGatewayAuditEntry],
    operation_id="getAIGatewayAudit",
)
async def get_ai_gateway_audit(request: Request, limit: int = 100):
    """AI Gateway audit log — last N LLM calls from system.serving.endpoint_usage."""
    db = _sql(request)
    if db:
        try:
            rows = db.execute(f"""
                SELECT
                  eu.request_time,
                  se.endpoint_name,
                  eu.requester,
                  eu.input_token_count,
                  eu.output_token_count,
                  (eu.input_token_count + eu.output_token_count) AS total_token_count,
                  eu.status_code
                FROM system.serving.endpoint_usage eu
                JOIN system.serving.served_entities se
                  ON eu.served_entity_id = se.served_entity_id
                WHERE se.endpoint_name IN ({_GATEWAY_IN_CLAUSE})
                ORDER BY eu.request_time DESC
                LIMIT {limit}
            """)
            if rows:
                return [
                    AIGatewayAuditEntry(
                        request_timestamp=r["request_time"],
                        endpoint_name=r["endpoint_name"],
                        request_user=r["requester"] or "unknown",
                        input_token_count=int(r["input_token_count"] or 0),
                        output_token_count=int(r["output_token_count"] or 0),
                        total_token_count=int(r["total_token_count"] or 0),
                        cost_usd=_row_cost(
                            r["endpoint_name"],
                            int(r["input_token_count"] or 0),
                            int(r["output_token_count"] or 0),
                        ),
                        latency_ms=0.0,
                        status_code=int(r["status_code"] or 200),
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Audit query failed: {e}")
    return []


@api.get(
    "/governance/audit/summary",
    response_model=AuditSummary,
    operation_id="getAuditSummary",
)
async def get_audit_summary(request: Request):
    """Aggregate audit stats for the header card."""
    db = _sql(request)
    if db:
        try:
            rows = db.execute(f"""
                SELECT
                  se.endpoint_name,
                  COUNT(*) AS calls,
                  COALESCE(SUM(eu.input_token_count), 0) AS total_input,
                  COALESCE(SUM(eu.output_token_count), 0) AS total_output,
                  COUNT_IF(eu.status_code >= 400) AS errors
                FROM system.serving.endpoint_usage eu
                JOIN system.serving.served_entities se
                  ON eu.served_entity_id = se.served_entity_id
                WHERE se.endpoint_name IN ({_GATEWAY_IN_CLAUSE})
                GROUP BY se.endpoint_name
            """)
            if rows:
                total_calls = 0
                total_input = 0
                total_output = 0
                total_cost = 0.0
                total_errors = 0
                for r in rows:
                    ep = r["endpoint_name"]
                    inp = int(r["total_input"] or 0)
                    out = int(r["total_output"] or 0)
                    total_calls += int(r["calls"] or 0)
                    total_input += inp
                    total_output += out
                    total_errors += int(r["errors"] or 0)
                    total_cost += _row_cost(ep, inp, out)
                return AuditSummary(
                    total_calls=total_calls,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    total_cost_usd=round(total_cost, 4),
                    avg_latency_ms=0.0,
                    error_count=total_errors,
                )
        except Exception as e:
            logger.error(f"Audit summary query failed: {e}")
    return AuditSummary(
        total_calls=0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_cost_usd=0.0,
        avg_latency_ms=0.0,
        error_count=0,
    )


@api.get(
    "/governance/model-performance",
    response_model=list[ModelPerformancePoint],
    operation_id="getModelPerformance",
)
async def get_model_performance(request: Request):
    """Monthly model precision/recall/F1 from model_performance_log."""
    cached = _cache_get("model_performance")
    if cached is not None:
        return cached

    db = _sql(request)
    if db:
        for _attempt in range(2):
            try:
                rows = db.execute("""
                    SELECT
                      DATE_FORMAT(month, 'yyyy-MM') AS month_str,
                      model_version, risk_tier,
                      precision_pct, recall_pct, f1_score,
                      cases_scored, cases_confirmed
                    FROM model_performance_log
                    ORDER BY month, risk_tier
                """)
                result = [
                    ModelPerformancePoint(
                        month=r["month_str"],
                        model_version=r["model_version"],
                        risk_tier=RiskTier(r["risk_tier"]),
                        precision_pct=float(r["precision_pct"]),
                        recall_pct=float(r["recall_pct"]),
                        f1_score=float(r["f1_score"]),
                        cases_scored=int(r["cases_scored"]),
                        cases_confirmed=int(r["cases_confirmed"]),
                    )
                    for r in rows
                ]
                _cache_set("model_performance", result)
                return result
            except Exception as e:
                logger.warning(f"Model performance query failed: {e}")
                if _attempt == 0 and _maybe_self_heal(db):
                    cached = _cache_get("model_performance")
                    if cached is not None:
                        return cached
                    continue
                break
    return []


# ---------------------------------------------------------------------------
# Workspace Config (portable — no hardcoded URLs)
# ---------------------------------------------------------------------------


class WorkspaceConfigOut(BaseModel):
    workspace_url: str
    catalog: str
    schema_name: str
    genie_space_id: str
    mas_endpoint: str


@api.get(
    "/workspace-config",
    response_model=WorkspaceConfigOut,
    operation_id="getWorkspaceConfig",
)
async def get_workspace_config(request: Request):
    """Return workspace-specific config so the frontend never hardcodes URLs."""
    config = _config(request)
    db = _sql(request)
    catalog = db.resolve_catalog() if db else (config.catalog if config else "")
    return WorkspaceConfigOut(
        workspace_url=config.workspace_url if config else "",
        catalog=catalog,
        schema_name=config.schema_name if config else "",
        genie_space_id=config.genie_space_id if config else "",
        mas_endpoint=config.mas_endpoint if config else "",
    )


# ---------------------------------------------------------------------------
# Job URL — end-to-end pipeline job (portable across workspaces)
# ---------------------------------------------------------------------------


class JobUrlOut(BaseModel):
    job_url: str
    job_id: str


@api.get(
    "/pipeline-url",
    response_model=JobUrlOut,
    operation_id="getPipelineUrl",
)
async def get_pipeline_url(request: Request):
    """Return the URL of the energy-theft-end-to-end job (all runs page)."""
    db = _sql(request)
    if not db:
        raise HTTPException(503, "SQL client not configured")

    ws = db._client
    host = _workspace_host(db)

    job_name = "energy-theft-end-to-end"
    job_id = ""

    try:
        for j in ws.jobs.list(name=job_name):
            job_id = str(j.job_id or "")
            break
    except Exception:
        pass

    if job_id:
        url = f"{host}/jobs/{job_id}"
    else:
        url = f"{host}/jobs"

    return JobUrlOut(job_url=url, job_id=job_id)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@api.get("/health", operation_id="healthCheck")
async def health_check(request: Request):
    """Basic health check with SQL diagnostic."""
    db = _sql(request)
    config = _config(request)
    sql_test = None
    sql_error = None
    if db:
        try:
            rows = db.execute("SELECT 1 AS ok")
            sql_test = "ok" if rows else "empty"
        except Exception as e:
            sql_error = str(e)
    return {
        "status": "ok",
        "app": "energy-theft-detection",
        "sql_connected": db is not None,
        "sql_test": sql_test,
        "sql_error": sql_error,
        "catalog": db.resolve_catalog() if db else (config.catalog if config else None),
        "schema": config.schema_name if config else None,
        "warehouse_id": config.sql_warehouse_id if config else None,
        "schema_access_ok": _schema_access_ok,
        "schema_access_error": _schema_access_error or None,
    }



class ReadinessOut(BaseModel):
    ready: bool
    error: str | None = None


@api.get("/readiness", response_model=ReadinessOut, operation_id="getReadiness")
async def get_readiness(request: Request):
    """Check whether the app can serve data.

    If a previous check failed, automatically re-runs the probe (with a
    cooldown) so transient startup failures self-heal without a restart.
    """
    db = _sql(request)
    if not db:
        return ReadinessOut(
            ready=False,
            error="SQL Warehouse not connected — SQL_WAREHOUSE_ID is not configured.",
        )
    if not _schema_access_ok:
        elapsed = _time.monotonic() - _schema_access_last_check
        if elapsed >= _SCHEMA_RECHECK_COOLDOWN:
            ok, err = _check_schema_access(db, retries=1, backoff=0)
            if ok:
                _try_warm_cache(db)
                return ReadinessOut(ready=True)
            return ReadinessOut(ready=False, error=err)
        return ReadinessOut(ready=False, error=_schema_access_error or "Schema access check has not run yet.")
    return ReadinessOut(ready=True)


# ---------------------------------------------------------------------------
# APX Standard: Current User
# ---------------------------------------------------------------------------

class CurrentUserOut(BaseModel):
    user_name: str
    display_name: str


@api.get("/current-user", response_model=CurrentUserOut, operation_id="currentUser")
async def current_user(request: Request):
    """Return the current user. APX sidebar footer uses this."""
    forwarded_user = request.headers.get("X-Forwarded-Preferred-Username", "")
    display_name = forwarded_user.split("@")[0].replace(".", " ").title() if forwarded_user else "Demo User"
    return CurrentUserOut(
        user_name=forwarded_user or "demo@ukigas.co.uk",
        display_name=display_name or "Demo User",
    )
