import { getModelHeaders } from "./demo-settings";
import { ApiError, type LLMCaseSummary, type RiskTier } from "./api";

/** Merge demo model selector headers into fetch options. */
export function withModelHeaders(options?: RequestInit): RequestInit {
  return {
    ...options,
    headers: { ...options?.headers, ...getModelHeaders() },
  };
}

/** Flagged-account row fields available before account detail loads. */
export interface AccountRowPreview {
  account_id: string;
  risk_tier: RiskTier;
  composite_risk_score: number;
  consumption_drop_pct: number;
  comms_gap_count_30d: number;
}

/** Case summary with optional skip_sql context from the flagged-accounts table. */
export async function getCaseSummaryWithPreview(
  accountId: string,
  preview?: AccountRowPreview,
  options?: RequestInit,
): Promise<{ data: LLMCaseSummary }> {
  const searchParams = new URLSearchParams();
  if (preview) {
    searchParams.set("skip_sql", "true");
    searchParams.set("risk_level", preview.risk_tier);
    searchParams.set("consumption_drop_pct", String(preview.consumption_drop_pct));
    searchParams.set("composite_risk_score", String(preview.composite_risk_score));
    searchParams.set("comms_gap_count_30d", String(preview.comms_gap_count_30d));
  }
  const qs = searchParams.toString();
  const url = qs
    ? `/api/llm/case-summary/${accountId}?${qs}`
    : `/api/llm/case-summary/${accountId}`;
  const res = await fetch(url, { ...withModelHeaders(options), method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try {
      parsed = JSON.parse(body);
    } catch {
      parsed = body;
    }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
}

export function getCaseSummaryWithPreviewKey(
  accountId: string,
  preview?: AccountRowPreview,
) {
  return ["/api/llm/case-summary/{account_id}", { account_id: accountId, preview }] as const;
}
