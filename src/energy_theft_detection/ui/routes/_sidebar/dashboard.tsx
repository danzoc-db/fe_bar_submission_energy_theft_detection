import { createFileRoute } from "@tanstack/react-router";
import { Suspense, useState, useRef, useEffect, lazy, useMemo, Component } from "react";
import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useGetDashboardKPIsSuspense,
  useGetDashboardRecoveryOpportunitySuspense,
  useGetModelPerformanceSuspense,
  useGetInvestigationKPIsSuspense,
  useSendGenieMessage,
  warmGenie,
  getDashboardKPIs,
  getDashboardKPIsKey,
  getDashboardRecoveryOpportunity,
  getDashboardRecoveryOpportunityKey,
  getModelPerformance,
  getModelPerformanceKey,
  getInvestigationKPIs,
  getInvestigationKPIsKey,
  getDailyBriefing,
  getDailyBriefingKey,
  listFlaggedAccounts,
  listFlaggedAccountsKey,
} from "@/lib/api";
import selector from "@/lib/selector";
import { useWorkspaceConfig, genieSpaceUrl, useJobUrl } from "@/lib/workspace-config";
import {
  Loader2,
  ShieldAlert,
  PoundSterling,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  Info,
  ExternalLink,
  Sparkles,
  Target,
  BrainCircuit,
  ShieldCheck,
  NotebookPen,
  Layers,
  Zap,
  GitBranch,
  MessageSquare,
  Unlock,
  Shield,
  Database,
  Ruler,
  Globe,
} from "lucide-react";
import {
  UnderTheHood,
  HoodSection,
  HoodBullet,
  FabricCallout,
} from "@/components/under-the-hood";


interface SectionBoundaryProps { section: string; children: ReactNode; }
interface SectionBoundaryState { error: Error | null; }
class SectionErrorBoundary extends Component<SectionBoundaryProps, SectionBoundaryState> {
  state: SectionBoundaryState = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) return (
      <Card className="border-destructive/30">
        <CardContent className="py-8 flex flex-col items-center justify-center text-center gap-2">
          <ShieldAlert className="h-6 w-6 text-destructive/60" />
          <p className="text-sm font-medium text-destructive">
            {this.props.section} could not be loaded
          </p>
          <p className="text-xs text-muted-foreground max-w-md">
            The data for this section is temporarily unavailable. Other sections continue to work independently.
          </p>
        </CardContent>
      </Card>
    );
    return this.props.children;
  }
}

const SUGGESTED_QUESTIONS = [
  "At the current monthly run rate, will we hit the £97M recovery target this year — show monthly recovered revenue vs the £8.1M/month pace needed?",
  "Which region is recovering the most revenue and which is underperforming — show monthly revenue recovered by region?",
  "Which postcode sectors have the highest concentration of HIGH risk accounts, and what is their average risk score?",
  "Compare the average recovery per confirmed theft case between gas and electricity — which fuel type yields more per case?",
];

function DashboardPending() {
  return (
    <div className="container mx-auto py-8 space-y-8 animate-pulse">
      <Skeleton className="h-8 w-72" />
      <div className="grid gap-4 md:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Skeleton className="h-80 rounded-xl" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    </div>
  );
}

export const Route = createFileRoute("/_sidebar/dashboard")({
  loader: ({ context: { queryClient } }) => {
    queryClient.ensureQueryData({ queryKey: getDailyBriefingKey(), queryFn: getDailyBriefing });
    queryClient.ensureQueryData({ queryKey: listFlaggedAccountsKey(), queryFn: () => listFlaggedAccounts() });

    return Promise.all([
      queryClient.ensureQueryData({ queryKey: getDashboardKPIsKey(), queryFn: getDashboardKPIs }),
      queryClient.ensureQueryData({ queryKey: getDashboardRecoveryOpportunityKey(), queryFn: getDashboardRecoveryOpportunity }),
      queryClient.ensureQueryData({ queryKey: getModelPerformanceKey(), queryFn: getModelPerformance }),
      queryClient.ensureQueryData({ queryKey: getInvestigationKPIsKey(), queryFn: getInvestigationKPIs }),
    ]);
  },
  pendingComponent: DashboardPending,
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <TooltipProvider delayDuration={200}>
      <div className="container mx-auto py-8 space-y-8">


        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Executive Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Susie Chambers — Head of Fraud & Intelligence
            </p>
            <p className="text-xs text-accent/70 font-medium tracking-wide mt-1.5 italic">
              Energise a fairer future, faster with energy theft detection on Databricks
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge variant="outline" className="text-muted-foreground border-border text-xs">
              Live ML Inference
            </Badge>
            <PipelineLink />
          </div>
        </div>

        {/* KPI Row */}
        <div>
          <div className="flex items-center gap-1.5 mb-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Revenue Protection KPIs
            </h2>
            <DataEngineeringHood />
          </div>
          <SectionErrorBoundary section="KPIRow">
          <Suspense fallback={<KPISkeleton />}>
            <KPIRow />
          </Suspense>
          </SectionErrorBoundary>
        </div>

        {/* Charts — business outcomes */}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
            Detection & Investigation Performance
          </h2>
          <div className="grid gap-6 md:grid-cols-2 items-stretch">
            <SectionErrorBoundary section="RecoveryOpportunity">
            <Suspense fallback={<ChartSkeleton title="Revenue Recovery Opportunity" />}>
              <div className="animate-scale-in h-full" style={{ animationDelay: "400ms" }}>
                <RecoveryOpportunityCard />
              </div>
            </Suspense>
            </SectionErrorBoundary>
            <SectionErrorBoundary section="InvestigationOutcomes">
            <Suspense fallback={<ChartSkeleton title="Investigation Outcomes" />}>
              <div className="animate-scale-in h-full" style={{ animationDelay: "500ms" }}>
                <InvestigationOutcomesCard />
              </div>
            </Suspense>
            </SectionErrorBoundary>
          </div>

          {/* Case Pipeline — operational snapshot */}
          <div className="mt-6">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
              Case Pipeline — This Month
            </h2>
            <SectionErrorBoundary section="CasePipeline">
            <Suspense fallback={<KPISkeleton />}>
              <div className="animate-fade-slide-up" style={{ animationDelay: "600ms" }}>
                <CasePipelineCard />
              </div>
            </Suspense>
            </SectionErrorBoundary>
          </div>
        </div>

        {/* Genie — inline, large, captivating */}
        <div>
          <div className="flex items-center gap-1.5 mb-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Talk to your Data with Genie
            </h2>
            <GenieHood />
          </div>
          <div className="animate-scale-in" style={{ animationDelay: "800ms" }}>
            <GenieInline />
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// Pipeline Link — latest SDP run in Databricks
// ---------------------------------------------------------------------------

function PipelineLink() {
  const { data: job, isLoading } = useJobUrl();

  if (isLoading || !job?.job_url) return null;

  return (
    <a
      href={job.job_url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-[11px] text-accent hover:text-accent/80 transition-colors font-medium"
    >
      <Layers className="h-3 w-3" />
      View End-to-End Pipeline in Databricks
      <ExternalLink className="h-2.5 w-2.5" />
    </a>
  );
}

// ---------------------------------------------------------------------------
// KPI Tiles
// ---------------------------------------------------------------------------

interface KPIMeta {
  key: string;
  label: string;
  group: "exposure" | "recovered" | "effectiveness";
  icon: React.ElementType;
  keylineColor: string;
  tooltip: React.ReactNode | ((kpis: Record<string, number>) => React.ReactNode);
  format: (v: number) => string;
  subtitle: string | ((kpis: Record<string, number>) => string);
  target?: string;
  hasProgressBar?: boolean;
}

const KPI_GROUPS: { id: KPIMeta["group"]; label: string }[] = [
  { id: "exposure", label: "Exposure" },
  { id: "recovered", label: "Recovered" },
  { id: "effectiveness", label: "Detection Effectiveness" },
];

const KPI_META: KPIMeta[] = [
  {
    key: "annual_theft_exposure_gbp",
    label: "Annual Theft Exposure",
    group: "exposure",
    icon: ShieldAlert,
    keylineColor: "bg-bg-red",
    tooltip: (kpis) => {
      const recovered = kpis.revenue_recovered_ytd_gbp;
      const recStr = recovered >= 1_000_000 ? `£${(recovered / 1_000_000).toFixed(1)}M` : `£${Math.round(recovered / 1_000)}K`;
      const net = kpis.annual_theft_exposure_gbp - recovered;
      const netStr = `£${Math.round(net / 1_000_000)}M`;
      return `Derived from RECCo's £1.4bn UK theft estimate × UKI Gas's 23.1% domestic market share (Ofgem retail market indicators, Jan 2025). Label as estimate — directionally correct for executive conversation.\n\n↓ ${recStr} recovered YTD → ${netStr} net remaining exposure.`;
    },
    format: (n) => `£${Math.round(n / 1_000_000)}M`,
    subtitle: (kpis) => {
      const recovered = kpis.revenue_recovered_ytd_gbp;
      const recStr = recovered >= 1_000_000 ? `£${(recovered / 1_000_000).toFixed(1)}M` : `£${Math.round(recovered / 1_000)}K`;
      return `↓ ${recStr} recovered\n~£6.2M/wk unrecovered`;
    },
  },
  {
    key: "exposure_vs_aop_pct",
    label: "Exposure vs Divisional AOP",
    group: "exposure",
    icon: TrendingDown,
    keylineColor: "bg-bg-orange",
    tooltip:
      "UKI Gas Home Energy divisional operating profit was £163m (UKI Energy Preliminary Results, Feb 2026). Theft exposure (~£323m) is nearly 2x the entire division's profit.",
    format: (n) => `${Math.round(n)}%`,
    subtitle: "£323m exposure\nvs £163m operating profit",
  },
  {
    key: "revenue_recovered_ytd_gbp",
    label: "Revenue Recovered YTD",
    group: "recovered",
    icon: TrendingUp,
    keylineColor: "bg-bg-lime",
    tooltip:
      "Revenue recovered year-to-date from confirmed theft cases via back-billing. Annual target is 30% of estimated £323m exposure (~£97m). 36% of target after Q1 = 11pts ahead of linear 25% pace. Source: investigation_cases table.",
    format: (n) =>
      n >= 1_000_000 ? `£${(n / 1_000_000).toFixed(1)}M` : `£${Math.round(n / 1_000)}K`,
    subtitle: (kpis) => {
      const pct = kpis.recovery_target_gbp > 0
        ? ((kpis.revenue_recovered_ytd_gbp / kpis.recovery_target_gbp) * 100).toFixed(0)
        : "0";
      return `${pct}% of £97m target\n11pts ahead of Q1 pace`;
    },
    hasProgressBar: true,
  },
  {
    key: "recovery_rate_pct",
    label: "Recovery Rate",
    group: "effectiveness",
    icon: PoundSterling,
    keylineColor: "bg-bg-cyan",
    tooltip: (
      <>
        Recovered revenue as a percentage of pro-rata recoverable theft for the year to date. Industry benchmark for ML-assisted programmes is 30% (
        <a href="https://www.bestpractice.ai/ai-case-study-best-practice/enel_improved_the_average_energy_recovered_per_non-technical_loss_inspection_by_70%25_in_italy_and_more_than_300%25_in_spain_using_machine_learning" target="_blank" rel="noopener noreferrer" className="underline text-accent hover:text-accent/80">
          Enel achieved 70% and 300% improvement per inspection in Italy and Spain, respectively
        </a>).
      </>
    ),
    format: (n) => `${n.toFixed(1)}%`,
    subtitle: "above 30% benchmark\nML investment is paying off",
    target: ">30%",
  },
  {
    key: "detection_precision_pct",
    label: "Detection Precision",
    group: "effectiveness",
    icon: CheckCircle,
    keylineColor: "bg-bg-cyan",
    tooltip:
      "Theft Detection Precision Rate: confirmed theft cases / total HIGH-risk cases closed. Below 60%, false-positive field visits erode investigator trust and inflate opex. Source: UC Metric View.",
    format: (n) => `${n.toFixed(1)}%`,
    subtitle: "confirmed theft / HIGH cases closed",
    target: ">60%",
  },
];

function KPIRow() {
  const { data: kpis } = useGetDashboardKPIsSuspense(selector());
  const kpiRecord = kpis as unknown as Record<string, number>;

  const groupLabels = Object.fromEntries(KPI_GROUPS.map((g) => [g.id, g.label]));
  let lastGroup = "";

  return (
    <div className="grid gap-4 md:grid-cols-5">
      {KPI_META.map((meta, idx) => {
        const showLabel = meta.group !== lastGroup;
        lastGroup = meta.group;
        return (
          <div
            key={meta.key}
            className="space-y-1.5 animate-fade-slide-up"
            style={{ animationDelay: `${idx * 80}ms` }}
          >
            <p className={`text-[10px] font-medium uppercase tracking-wider ${showLabel ? "text-muted-foreground/60" : "text-transparent"}`}>
              {groupLabels[meta.group]}
            </p>
            <KPITile meta={meta} value={kpiRecord[meta.key]} allKpis={kpiRecord} />
          </div>
        );
      })}
    </div>
  );
}

function KPITile({
  meta,
  value,
  allKpis,
}: {
  meta: KPIMeta;
  value: number;
  allKpis: Record<string, number>;
}) {
  const Icon = meta.icon;
  const subtitle =
    typeof meta.subtitle === "function" ? meta.subtitle(allKpis) : meta.subtitle;
  const tooltipText =
    typeof meta.tooltip === "function" ? meta.tooltip(allKpis) : meta.tooltip;
  const progressPct = meta.hasProgressBar && allKpis.recovery_target_gbp > 0
    ? Math.min(100, (allKpis.revenue_recovered_ytd_gbp / allKpis.recovery_target_gbp) * 100)
    : 0;

  return (
    <div className="relative flex rounded-lg border bg-card overflow-hidden transition-shadow hover:shadow-md">
      <div className={`w-1 shrink-0 ${meta.keylineColor}`} />
      <div className="flex-1 p-4 space-y-2">
        <div className="flex items-center justify-between">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <div className="flex items-center gap-1.5">
            {meta.target && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5 font-normal text-muted-foreground">
                <Target className="h-2.5 w-2.5 mr-0.5" />
                {meta.target}
              </Badge>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <button className="text-muted-foreground/40 hover:text-muted-foreground transition-colors">
                  <Info className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[300px] text-xs leading-relaxed whitespace-pre-line">
                {tooltipText}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
        <p className="text-3xl font-bold tracking-tight text-foreground animate-count-up">
          {meta.format(value)}
        </p>
        {meta.hasProgressBar && (
          <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-bg-cyan transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        )}
        <div>
          <p className="text-xs font-semibold text-foreground">{meta.label}</p>
          <p className="text-[11px] text-muted-foreground leading-snug whitespace-pre-line">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Case Pipeline — operational snapshot for Susie
// ---------------------------------------------------------------------------

function CasePipelineCard() {
  const { data: kpis } = useGetInvestigationKPIsSuspense(selector());
  const confirmationRate = kpis.closed_this_month > 0
    ? Math.round((kpis.confirmed_theft_this_month / kpis.closed_this_month) * 1000) / 10
    : 0;

  const metrics = [
    { label: "Open HIGH Accounts", value: kpis.open_high_cases.toLocaleString(), color: "border-red-500", icon: ShieldAlert, tooltip: "Unique accounts currently scored HIGH by the ML model and awaiting investigation. This is a live snapshot from anomaly_scores — it refreshes every scoring run." },
    { label: "Accounts In Triage", value: kpis.in_progress_cases.toLocaleString(), color: "border-amber-500", icon: Loader2, tooltip: "HIGH-risk accounts currently assigned to an investigator for active field triage." },
    { label: "Cases Closed", value: kpis.closed_this_month.toLocaleString(), color: "border-blue-500", icon: CheckCircle, tooltip: "Investigation cases resolved this calendar month (confirmed + false positive). An account may have multiple cases over time as it is re-scored and re-investigated." },
    { label: "Confirmation Rate", value: `${confirmationRate}%`, color: "border-green-500", icon: TrendingUp, tooltip: "Confirmed theft / total cases closed this month. Higher = fewer wasted field visits. Target >60%." },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-4">
      {metrics.map((m, i) => {
        const Icon = m.icon;
        return (
          <Card key={m.label} className={`border-l-4 ${m.color} animate-fade-slide-up`} style={{ animationDelay: `${i * 60}ms` }}>
            <CardContent className="py-4 px-5 flex items-center gap-4">
              <Icon className="h-5 w-5 text-muted-foreground shrink-0" />
              <div className="flex-1">
                <p className="text-2xl font-bold tracking-tight">{m.value}</p>
                <p className="text-xs text-muted-foreground">{m.label}</p>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="text-muted-foreground/30 hover:text-muted-foreground transition-colors shrink-0">
                    <Info className="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[220px] text-xs">
                  {m.tooltip}
                </TooltipContent>
              </Tooltip>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Plotly (lazy)
// ---------------------------------------------------------------------------

const Plot = lazy(() => import("react-plotly.js"));

// ---------------------------------------------------------------------------
// Revenue Recovery Opportunity — donut chart by ML confidence tier
// ---------------------------------------------------------------------------

function fmtGbp(n: number): string {
  if (n >= 1_000_000_000) return `£${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `£${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `£${Math.round(n / 1_000)}K`;
  return `£${Math.round(n)}`;
}

function RecoveryOpportunityCard() {
  const { data: opp } = useGetDashboardRecoveryOpportunitySuspense(selector());

  const BG_TARGET = 97_000_000;

  const segments = useMemo(() => [
    { label: "Recovered YTD", value: opp.recovered_ytd_gbp, color: "#22c55e", detail: "Already clawed back" },
    { label: "HIGH Risk (ML)", value: opp.high_confidence_gbp, color: "#FF3621", detail: `${opp.high_confidence_accounts.toLocaleString()} accounts` },
    { label: "MEDIUM Risk (ML)", value: opp.medium_confidence_gbp, color: "#f59e0b", detail: `${opp.medium_confidence_accounts.toLocaleString()} accounts` },
    { label: "Remaining Exposure", value: opp.remaining_exposure_gbp, color: "#d1d5db", detail: "Undetected / low confidence" },
  ], [opp]);

  const total = opp.total_exposure_gbp;
  const bgPct = Math.min(100, (opp.recovered_ytd_gbp / BG_TARGET) * 100);
  const annualisedRunRate = opp.recovered_ytd_gbp * (12 / Math.max(new Date().getMonth(), 1));

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">Revenue Recovery Opportunity</CardTitle>
          <Tooltip>
            <TooltipTrigger asChild>
              <button className="text-muted-foreground/40 hover:text-muted-foreground transition-colors">
                <Info className="h-3.5 w-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-[300px] text-xs leading-relaxed">
              Of the £323M annual theft exposure (RECCo estimate × BG 23.1% market share), this shows what ML intelligence identifies as recoverable at HIGH and MEDIUM confidence, what has already been recovered, and the remaining gap. The BG target (£97M) is a conservative 30% ML-assisted recovery rate applied to the full exposure.
            </TooltipContent>
          </Tooltip>
        </div>
      </CardHeader>
      <CardContent className="h-[480px] p-0 pr-2 flex flex-col">
        <div className="flex-1 min-h-0">
          <Suspense fallback={<div className="h-full flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>}>
            <Plot
              data={[
                {
                  type: "pie" as const,
                  values: segments.map((s) => s.value),
                  labels: segments.map((s) => s.label),
                  marker: { colors: segments.map((s) => s.color) },
                  hole: 0.55,
                  textinfo: "none" as const,
                  hovertemplate: segments.map(
                    (s) => `<b>${s.label}</b><br>${fmtGbp(s.value)} (${((s.value / total) * 100).toFixed(1)}%)<br>${s.detail}<extra></extra>`
                  ),
                  sort: false,
                  direction: "clockwise" as const,
                  domain: { x: [0, 1], y: [0.05, 1] },
                },
              ]}
              layout={{
                margin: { l: 10, r: 10, t: 10, b: 50 },
                showlegend: true,
                legend: {
                  orientation: "h" as const,
                  y: -0.02,
                  x: 0.5,
                  xanchor: "center" as const,
                  font: { size: 10, color: "#6b7280" },
                },
                annotations: [
                  {
                    text: `<b>${fmtGbp(total)}</b><br><span style="font-size:10px;color:#6b7280">Total Exposure</span>`,
                    showarrow: false,
                    font: { size: 18, color: "#1f2937" },
                    x: 0.5,
                    y: 0.53,
                    xanchor: "center" as const,
                    yanchor: "middle" as const,
                  },
                ],
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                hoverlabel: { bgcolor: "#1f2937", font: { color: "#fff", size: 12 }, bordercolor: "transparent" },
              }}
              config={{ displayModeBar: false, responsive: true }}
              useResizeHandler
              style={{ width: "100%", height: "100%" }}
            />
          </Suspense>
        </div>
        <p className="text-[9px] text-muted-foreground/60 text-center italic px-4 -mt-1">Risk segments identified by Isolation Forest + LSTM anomaly detection models</p>
        {/* Target progress bars */}
        <div className="px-4 pb-4 space-y-3 shrink-0 border-t pt-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Recovery vs Targets</p>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="h-3.5 w-3.5 text-emerald-600" />
                <span className="text-xs font-bold text-foreground">BG Target — £97M</span>
              </div>
              <span className="text-sm font-bold text-emerald-600">{bgPct.toFixed(0)}%</span>
            </div>
            <div className="h-3 w-full rounded-full bg-muted overflow-hidden relative">
              <div className="absolute left-[25%] top-0 h-full w-0.5 bg-foreground/25 z-10" title="Q1 linear pace (25%)" />
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-700"
                style={{ width: `${bgPct}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>{fmtGbp(opp.recovered_ytd_gbp)} of £97M</span>
              <span className="font-medium">Run rate: {fmtGbp(annualisedRunRate)}/yr</span>
            </div>
          </div>
          <div className="rounded border border-dashed border-muted-foreground/20 bg-muted/30 px-3 py-2">
            <p className="text-[10px] text-muted-foreground">
              <span className="font-semibold text-foreground">Group context:</span>{" "}
              £97M UKI Gas recovery target = 12% of UKI Energy Group adj. operating profit (£814M, FY2025)
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Investigation Outcomes — cases flagged vs confirmed theft (business view)
// ---------------------------------------------------------------------------

function InvestigationOutcomesCard() {
  const { data: points } = useGetModelPerformanceSuspense(selector());

  const ML_DEPLOY_LABEL = "Oct 2025";

  const { months, flagged, confirmed, confirmRate, mlDeployIdx } = useMemo(() => {
    const high = [...points]
      .filter((p) => p.risk_tier === "HIGH")
      .sort((a, b) => a.month.localeCompare(b.month))
      .slice(-12);
    const fmt = (m: string) => {
      const [y, mo] = m.split("-");
      return new Date(+y, +mo - 1).toLocaleString("en-GB", { month: "short", year: "numeric" });
    };
    const fmtMonths = high.map((p) => fmt(p.month));
    return {
      months: fmtMonths,
      flagged: high.map((p) => p.cases_scored),
      confirmed: high.map((p) => p.cases_confirmed),
      confirmRate: high.map((p) =>
        p.cases_scored > 0 ? Math.round((p.cases_confirmed / p.cases_scored) * 100 * 10) / 10 : 0,
      ),
      mlDeployIdx: fmtMonths.indexOf(ML_DEPLOY_LABEL),
    };
  }, [points]);

  if (points.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-sm font-semibold">Investigation Outcomes</CardTitle></CardHeader>
        <CardContent className="h-[480px] flex items-center justify-center text-muted-foreground text-sm">
          No investigation data available
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">Investigation Outcomes — HIGH Risk Flags</CardTitle>
          <div className="flex gap-3 text-xs">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: "#FF3621" }} /> Confirmed theft</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-gray-300" /> Flagged cases</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: "#002F87" }} /> Hit rate %</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="h-[480px] p-0 pr-2">
        <Suspense fallback={<div className="h-full flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>}>
          <Plot
            data={[
              {
                type: "bar" as const,
                name: "Flagged cases",
                x: months,
                y: flagged,
                marker: { color: "#e5e7eb" },
                hovertemplate: "<b>%{x}</b><br>Flagged: %{y:,}<extra></extra>",
              },
              {
                type: "bar" as const,
                name: "Confirmed theft",
                x: months,
                y: confirmed,
                marker: { color: "#FF3621" },
                hovertemplate: "<b>%{x}</b><br>Confirmed: %{y:,}<extra></extra>",
              },
              {
                type: "scatter" as const,
                mode: "lines+markers" as const,
                name: "Hit rate",
                x: months,
                y: confirmRate,
                yaxis: "y2",
                line: { color: "#002F87", width: 2.5, shape: "spline" as const },
                marker: { size: 5, color: "#002F87" },
                hovertemplate: "<b>%{x}</b><br>Hit rate: %{y:.1f}%<extra></extra>",
              },
            ]}
            layout={{
              margin: { l: 45, r: 45, t: 20, b: 50 },
              barmode: "overlay" as const,
              xaxis: {
                type: "category" as const,
                title: { text: "Month", font: { size: 11, color: "#6b7280" } },
                tickfont: { size: 10, color: "#6b7280" },
                gridcolor: "#f3f4f6",
                tickangle: -45,
              },
              yaxis: {
                title: { text: "Cases", font: { size: 11, color: "#6b7280" } },
                tickfont: { size: 10, color: "#6b7280" },
                gridcolor: "#f3f4f6",
                zeroline: false,
              },
              yaxis2: {
                title: { text: "Hit rate (%)", font: { size: 11, color: "#002F87" } },
                tickfont: { size: 10, color: "#002F87" },
                overlaying: "y" as const,
                side: "right" as const,
                range: [0, 100],
                zeroline: false,
                showgrid: false,
              },
              showlegend: false,
              shapes: mlDeployIdx >= 0 ? [
                {
                  type: "line" as const,
                  x0: ML_DEPLOY_LABEL, x1: ML_DEPLOY_LABEL,
                  y0: 0, y1: 1, yref: "paper" as const,
                  line: { color: "#002F87", width: 2, dash: "dash" as const },
                },
              ] : [],
              annotations: mlDeployIdx >= 0 ? [
                {
                  x: ML_DEPLOY_LABEL,
                  y: 1,
                  yref: "paper" as const,
                  text: "ML Model<br>Deployed",
                  showarrow: true,
                  arrowhead: 0,
                  ax: 40,
                  ay: -25,
                  font: { size: 9, color: "#002F87", family: "inherit" },
                  bordercolor: "#002F87",
                  borderwidth: 1,
                  borderpad: 3,
                  bgcolor: "rgba(255,255,255,0.9)",
                },
              ] : [],
              paper_bgcolor: "transparent",
              plot_bgcolor: "transparent",
              hoverlabel: { bgcolor: "#1f2937", font: { color: "#fff", size: 12 }, bordercolor: "transparent" },
              hovermode: "x unified" as const,
            }}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </Suspense>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// UK Risk Map — scattermapbox choropleth
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Markdown bold renderer for Genie responses
// ---------------------------------------------------------------------------

function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n{2,}/g, '</p><p class="mt-2">')
    .replace(/\n/g, "<br/>");
}

// ---------------------------------------------------------------------------
// SQL Metric View highlighter
// ---------------------------------------------------------------------------

function metricViewVariants(catalog: string, schema: string) {
  const views = ["theft_detection_metrics", "risk_exposure_metrics"];
  return views.flatMap((v) => [
    `\`${catalog}\`.\`${schema}\`.\`${v}\``,
    `${catalog}.${schema}.${v}`,
    `\`${v}\``,
    v,
  ]);
}

function HighlightMetricView({ sql, catalog, schema }: { sql: string; catalog: string; schema: string }) {
  const pattern = metricViewVariants(catalog, schema)
    .map((v) => v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|");
  const regex = new RegExp(`(${pattern})`, "gi");
  const parts = sql.split(regex);

  return (
    <>
      {parts.map((part, i) => {
        const isMatch = regex.test(part);
        regex.lastIndex = 0;
        if (isMatch) {
          return (
            <Tooltip key={i}>
              <TooltipTrigger asChild>
                <span className="font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1 py-0.5 rounded cursor-help border border-emerald-500/20">
                  {part}
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs text-xs">
                <div className="flex items-center gap-1.5 mb-1">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                  <span className="font-semibold">Certified UC Metric View</span>
                </div>
                <p>
                  This table is a <strong>Unity Catalog Metric View</strong> —
                  a governed, business-defined set of KPI calculations using{" "}
                  <code className="text-[11px] font-semibold bg-white/15 text-emerald-300 px-1 py-0.5 rounded font-mono">MEASURE()</code>.
                  Genie queries it but cannot alter the definitions.
                </p>
              </TooltipContent>
            </Tooltip>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Genie — inline, large, captivating
// ---------------------------------------------------------------------------

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  columns?: string[];
  data?: Record<string, unknown>[];
}

const GENIE_FEATURES = [
  {
    icon: BrainCircuit,
    title: "Knows the language of your business",
    desc: "Reads table schemas, column descriptions, and metric view definitions in Unity Catalog",
    iconBg: "bg-[#002F87]/10",
    iconColor: "text-[#002F87]",
  },
  {
    icon: NotebookPen,
    title: "Curate, Audit & Improve the Genie Space",
    desc: "Space-level instructions and curated examples guide accurate, consistent answers",
    iconBg: "bg-accent/10",
    iconColor: "text-accent",
  },
  {
    icon: ShieldCheck,
    title: "Centralised Access & Security in Mind",
    desc: "Permissions to both the Genie Space, and the underlying data, required.\nAll UC controls enforced.",
    iconBg: "bg-emerald-500/10",
    iconColor: "text-emerald-600",
  },
];

function GenieInline() {
  const { data: wsConfig } = useWorkspaceConfig();
  const genieUrl = wsConfig ? genieSpaceUrl(wsConfig) : "#";
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [convId, setConvId] = useState("new");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sendMutation = useSendGenieMessage();
  const warmedRef = useRef(false);

  const hasConversation = messages.length > 0;

  useEffect(() => {
    if (warmedRef.current) return;
    warmedRef.current = true;
    warmGenie().then((resp) => {
      const cid = resp.data.conversation_id;
      if (cid) setConvId(cid);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend(text?: string) {
    const q = text || input.trim();
    if (!q) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);

    sendMutation.mutate(
      { params: { conversation_id: convId, message: q } },
      {
        onSuccess: (resp) => {
          const msg = resp.data;
          if (msg.conversation_id) setConvId(msg.conversation_id);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: msg.content,
              sql: msg.sql ?? undefined,
              columns: msg.columns ?? undefined,
              data: (msg.data as Record<string, unknown>[]) ?? undefined,
            },
          ]);
        },
        onError: () => {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "Something went wrong. Please try again." },
          ]);
        },
      }
    );
  }

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="bg-[#002F87] text-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-white/10 flex items-center justify-center">
              <Sparkles className="h-4.5 w-4.5 text-[#0093F5]" />
            </div>
            <div>
              <h3 className="font-semibold text-base">Ask Genie</h3>
              <p className="text-white/60 text-xs">
                Natural language queries powered by Databricks AI
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={genieUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] text-white/50 hover:text-white/80 transition-colors"
            >
              View in Databricks <ExternalLink className="h-2.5 w-2.5" />
            </a>
            <Badge variant="outline" className="border-white/20 text-white/70 text-[10px] font-normal">
              DATABRICKS GENIE
            </Badge>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-col">
        {/* Messages or empty state */}
        <div className={`overflow-auto px-6 py-4 ${hasConversation ? "min-h-[200px] max-h-[480px]" : "min-h-[280px]"}`}>
          {!hasConversation ? (
            <div className="flex flex-col items-center justify-center h-full py-4 space-y-5">
              <div className="text-center space-y-1">
                <p className="text-sm font-semibold text-foreground">Genie knows your business with Unity Catalog</p>
                <p className="text-xs text-muted-foreground">Ask any question, Genie creates SQL trusted by your business thanks to UC Business Semantics</p>
              </div>
              <div className="grid grid-cols-3 gap-6 max-w-3xl mx-auto">
                {GENIE_FEATURES.map((feat) => (
                  <div key={feat.title} className="flex flex-col items-center text-center space-y-2.5">
                    <div className={`h-14 w-14 rounded-2xl ${feat.iconBg} flex items-center justify-center`}>
                      <feat.icon className={`h-6 w-6 ${feat.iconColor}`} />
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-foreground leading-snug">{feat.title}</p>
                      <p className="text-[11px] text-muted-foreground leading-relaxed whitespace-pre-line">{feat.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Conversation */
            <div className="space-y-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="h-7 w-7 rounded-lg bg-accent/10 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="h-3.5 w-3.5 text-accent" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                      msg.role === "user"
                        ? "bg-accent text-white rounded-tr-sm"
                        : "bg-muted/60 rounded-tl-sm"
                    }`}
                  >
                    <div className="leading-relaxed [&>p]:mt-2 first:[&>p]:mt-0" dangerouslySetInnerHTML={{ __html: `<p>${renderMarkdown(msg.content)}</p>` }} />
                    {msg.data && msg.columns && msg.data.length > 0 && (
                      <div className="mt-3 overflow-x-auto rounded-lg border bg-background/90 shadow-sm">
                        <table className="text-[11px] w-full">
                          <thead>
                            <tr className="border-b bg-muted/50">
                              {msg.columns.map((col) => (
                                <th key={col} className="px-3 py-2 text-left font-semibold text-muted-foreground whitespace-nowrap">{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {msg.data.map((row, ri) => (
                              <tr key={ri} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                                {msg.columns!.map((col) => (
                                  <td key={col} className="px-3 py-1.5 font-mono whitespace-nowrap">{String(row[col] ?? "")}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {msg.sql && (
                      <details className="mt-2">
                        <summary className="text-xs cursor-pointer opacity-60 hover:opacity-100 transition-opacity">
                          View Genie SQL
                        </summary>
                        <pre className="text-xs mt-1.5 p-2.5 bg-background/80 rounded font-mono whitespace-pre-wrap break-words">
                          <HighlightMetricView sql={msg.sql} catalog={wsConfig?.catalog ?? ""} schema={wsConfig?.schema_name ?? ""} />
                        </pre>
                        {/MEASURE\s*\(/i.test(msg.sql) && (
                          <div className="mt-2 flex items-center gap-1.5">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400">
                                  <ShieldCheck className="h-3.5 w-3.5" />
                                  <span className="font-medium">Certified UC Metric View</span>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side="bottom" className="max-w-xs text-xs">
                                <p>
                                  These metrics use <strong>MEASURE()</strong> functions from Unity Catalog Metric Views —
                                  pre-defined, governed calculations materialised by the business.
                                  Genie did not generate these formulas; they are trusted, certified definitions
                                  enforced by Unity Catalog.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                            <MetricViewHood />
                          </div>
                        )}
                      </details>
                    )}
                  </div>
                </div>
              ))}
              {sendMutation.isPending && (
                <div className="flex gap-3">
                  <div className="h-7 w-7 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                    <Sparkles className="h-3.5 w-3.5 text-accent" />
                  </div>
                  <div className="bg-muted rounded-xl rounded-tl-sm px-4 py-3 flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Genie is thinking...
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input area — always visible */}
        <div className="border-t px-6 py-3 space-y-2.5 shrink-0">
          {/* Question pills: 2x2 grid when empty, horizontal scroll when chatting */}
          {!hasConversation ? (
            <div className="grid grid-cols-2 gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  disabled={sendMutation.isPending}
                  className="text-[11px] leading-tight px-3 py-2 rounded-full border-2 border-accent/40 text-accent hover:border-accent hover:bg-accent/10 transition-all cursor-pointer text-left disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {q}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  disabled={sendMutation.isPending}
                  className="text-[11px] leading-tight px-3 py-1.5 rounded-full border border-accent/30 text-accent hover:border-accent hover:bg-accent/10 transition-all cursor-pointer whitespace-nowrap shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about any metric, trend, or pattern..."
              className="flex-1 text-sm px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-accent/50"
              disabled={sendMutation.isPending}
            />
            <Button
              type="submit"
              size="sm"
              disabled={!input.trim() || sendMutation.isPending}
              className="shrink-0 gap-1.5 px-4"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Ask
            </Button>
          </form>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Under the Hood — Data Engineering
// ---------------------------------------------------------------------------

function DataEngineeringHood() {
  return (
    <UnderTheHood title="Data Engineering — Serverless Pipelines">
      <HoodSection title="How it's built" icon={Layers}>
        <HoodBullet icon={Zap} bold="Serverless & auto-scaling">
          No clusters. Compute spins up, processes 10K–10M accounts, scales to zero. Pay per second.
        </HoodBullet>
        <HoodBullet icon={GitBranch} bold="Declarative pipelines + data quality">
          SDP: define the what, Databricks handles orchestration & retries. 11 data quality expectations baked into silver/gold layers — Fabric Data Factory has no equivalent inline quality framework.
        </HoodBullet>
        <HoodBullet icon={Database} bold="Medallion + UC lineage">
          Bronze → Silver → Gold, governed by UC with full column-level lineage from source to dashboard.
        </HoodBullet>
      </HoodSection>

      <FabricCallout category="Cost">
        <p>
          <strong>Fabric shares Capacity Units</strong> across all workloads — one spike throttles everything. No scale-to-zero; you pay for reserved capacity idle or not.
        </p>
        <p>
          <strong>Duplicated Security & Access Control overhead</strong> — UC policies are not replicated, so people-time is spent ensuring alignment of security and access controls for compliance. Another permission model to maintain.
        </p>
      </FabricCallout>
    </UnderTheHood>
  );
}

// ---------------------------------------------------------------------------
// Under the Hood — Genie
// ---------------------------------------------------------------------------

function GenieHood() {
  return (
    <UnderTheHood title="Genie Space & UC Semantics">
      <HoodSection title="How it's built" icon={Layers}>
        <HoodBullet icon={MessageSquare} bold="NL → SQL → trusted answer">
          Conversation API turns natural language into SQL on a Serverless Warehouse. All via REST, embedded in the app.
        </HoodBullet>
        <HoodBullet icon={Ruler} bold="Governed metrics">
          <code className="text-[11px] bg-muted px-0.5 rounded font-mono">MEASURE()</code> defines certified KPIs in UC. Genie uses them — never invents formulas.
        </HoodBullet>
        <HoodBullet icon={Unlock} bold="User-identity throughout">
          OBO auth means UC access controls are enforced per-user. No shared service principal.
        </HoodBullet>
      </HoodSection>

      <FabricCallout category="Cost">
        <p>
          <strong>Power BI Pro/Premium + Copilot</strong> each require per-user or per-capacity licensing. With Genie, we don't charge you a licence to talk to your data — like everything on Databricks, you only pay for what you use.
        </p>
        <p>
          Genie queries Delta tables directly under UC — same governance, same user identity, same lineage. No need to mirror into Fabric, no UC policies to recreate, no propagation lag. KPIs are governed at the source.
        </p>
      </FabricCallout>
    </UnderTheHood>
  );
}

// ---------------------------------------------------------------------------
// Under the Hood — UC Metric Views vs Power BI Semantic Models
// ---------------------------------------------------------------------------

function MetricViewHood() {
  return (
    <UnderTheHood title="UC Metric Views — Governed Metrics">
      <HoodSection title="How it's built" icon={Layers}>
        <HoodBullet icon={Globe} bold="One definition, use it anywhere">
          Define a KPI once in SQL. Use it in Apps, Genie, Power BI, Agents — the engine computes it at any granularity on read.
        </HoodBullet>
        <HoodBullet icon={Shield} bold="Business owns the formula">
          Version-controlled & permissioned in UC. Analysts approve — no engineer needed. LLMs can't hallucinate formulas.
        </HoodBullet>
        <HoodBullet icon={Zap} bold="Virtual, no ETL">
          No materialisation, no refresh schedule. Compute on read — one object replaces 20+ separate views at different granularities.
        </HoodBullet>
      </HoodSection>

      <FabricCallout category="Governance">
        <p>
          <strong>DAX semantic model required</strong> — proprietary language, specialist skill set, 20+ measures manually maintained at different granularities, locked inside the Power BI semantic model. Copilot generates unverified formulas outside the governance perimeter. Purview can't see inside DAX models.
        </p>
        <p>
          Databricks: one Metric View <em>is</em> the semantic layer — SQL, governed by UC, queryable in Apps, Genie, Power BI, and Agents. Zero DAX.
        </p>
      </FabricCallout>
    </UnderTheHood>
  );
}

// ---------------------------------------------------------------------------
// Skeletons
// ---------------------------------------------------------------------------

function KPISkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex rounded-lg border bg-card overflow-hidden">
          <div className="w-1 bg-muted shrink-0" />
          <div className="flex-1 p-4 space-y-3">
            <div className="flex justify-between">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-3.5 w-3.5" />
            </div>
            <Skeleton className="h-9 w-20" />
            <div className="space-y-1">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-2.5 w-36" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ChartSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <Skeleton className="h-full w-full" />
      </CardContent>
    </Card>
  );
}
