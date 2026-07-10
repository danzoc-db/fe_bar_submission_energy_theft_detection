import { createFileRoute, Link } from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import type { MeterReadPoint } from "@/lib/api";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useListFlaggedAccountsSuspense,
  useGetAccountDetailSuspense,
  getAccountDetail,
  getAccountDetailKey,
  useGenerateDispatchReport,
  useGetInvestigationKPIsSuspense,
  useGetDailyBriefingSuspense,
  getInvestigationKPIs,
  getInvestigationKPIsKey,
  getDailyBriefing,
  getDailyBriefingKey,
  listFlaggedAccounts,
  listFlaggedAccountsKey,
  getAIComponents,
  getAIComponentsKey,
  getPIIMatrix,
  getPIIMatrixKey,
  getColumnMetadata,
  getColumnMetadataKey,
  getDashboardKPIs,
  getDashboardKPIsKey,
  useCloseInvestigation,
} from "@/lib/api";
import type { DispatchReport, RiskTier } from "@/lib/api";
import { InvestigationStatus } from "@/lib/api";
import selector from "@/lib/selector";
import {
  getCaseSummaryWithPreview,
  getCaseSummaryWithPreviewKey,
  withModelHeaders,
  type AccountRowPreview,
} from "@/lib/api-fetch";
import {
  Info,
  ShieldCheck,
  FileText,
  Download,
  CheckCircle,
  Loader2,
  AlertTriangle,
  Siren,
  Clock,
  Target,
  PoundSterling,
  MapPin,
  Users,
  Sparkles,
  Filter,
  Layers,
  BookOpen,
  Zap,
  Shield,
  Cpu,
  Code,
  LayoutDashboard,
  CalendarCheck,
} from "lucide-react";
import { ModelBadge } from "@/components/model-badge";
import { BedrockLogo, AWS_ORANGE } from "@/components/bedrock-badge";
import { useDemoSettings } from "@/lib/demo-settings";
import {
  UnderTheHood,
  HoodSection,
  HoodBullet,
  FabricCallout,
} from "@/components/under-the-hood";


const SIGNAL_META: Record<string, { label: string; tooltip: string; model: string }> = {
  isolation_forest: {
    label: "Unusual Pattern Detection",
    tooltip: "Isolation Forest model — detects accounts with consumption patterns that differ significantly from the norm. Scored 0-1, higher = more anomalous. Registered in MLflow Model Registry.",
    model: "Isolation Forest v3",
  },
  lstm_deviation: {
    label: "Consumption Trend Anomaly",
    tooltip: "LSTM neural network — compares each account's recent consumption against its own 90-day baseline. A high deviation means the account's usage has changed significantly. Registered in MLflow Model Registry.",
    model: "LSTM Consumption v2",
  },
  cohort_deviation: {
    label: "Peer Group Comparison",
    tooltip: "Cohort deviation model — compares this account's consumption to similar properties (same postcode sector, property type, council tax band). High scores mean this account is an outlier vs its peers.",
    model: "Cohort Deviation Scorer",
  },
  comms_gap: {
    label: "Smart Meter Communication Gaps",
    tooltip: "Counts periods where the smart meter failed to report data in the last 30 days. Frequent gaps can indicate deliberate tampering with the meter's communication module (e.g. jamming DCC signals).",
    model: "Rule-based (DCC comms log)",
  },
  consumption_drop: {
    label: "Sudden Usage Drop",
    tooltip: "Measures the percentage drop in consumption vs the prior 30-day rolling average. A sharp drop is a classic signature of meter bypass — consumption still flows, but the meter stops recording it.",
    model: "Rule-based (meter reads)",
  },
};

function InvestigationPending() {
  return (
    <div className="container mx-auto py-8 space-y-6 animate-pulse">
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-96 rounded-xl" />
    </div>
  );
}

export const Route = createFileRoute("/_sidebar/investigation")({
  loader: ({ context: { queryClient } }) => {
    queryClient.ensureQueryData({ queryKey: getAIComponentsKey(), queryFn: getAIComponents });
    queryClient.ensureQueryData({ queryKey: getPIIMatrixKey(), queryFn: getPIIMatrix });
    queryClient.ensureQueryData({ queryKey: getColumnMetadataKey(), queryFn: getColumnMetadata });
    queryClient.ensureQueryData({ queryKey: getDashboardKPIsKey(), queryFn: getDashboardKPIs });

    queryClient.ensureQueryData({ queryKey: getDailyBriefingKey(), queryFn: getDailyBriefing });
    queryClient.ensureQueryData({ queryKey: listFlaggedAccountsKey(), queryFn: () => listFlaggedAccounts() });

    return queryClient.ensureQueryData({ queryKey: getInvestigationKPIsKey(), queryFn: getInvestigationKPIs });
  },
  pendingComponent: InvestigationPending,
  component: InvestigationPage,
});

type StatusFilter = (typeof InvestigationStatus)[keyof typeof InvestigationStatus];

const STATUS_LABELS: Record<StatusFilter, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In Progress",
  CLOSED: "Closed",
  CONFIRMED_THEFT: "Confirmed Theft",
};

const STATUS_BADGE_STYLES: Record<StatusFilter, string> = {
  OPEN: "border-sky-500 text-sky-600 hover:bg-sky-50 dark:hover:bg-sky-950/30",
  IN_PROGRESS: "border-blue-500 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30",
  CLOSED: "border-gray-400 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-950/30",
  CONFIRMED_THEFT: "border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30",
};

function InvestigationPage() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [selectedPreview, setSelectedPreview] = useState<AccountRowPreview | undefined>();
  const [riskFilter, setRiskFilter] = useState<RiskTier | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter | null>(null);

  const handleSelectAccount = (id: string, preview?: AccountRowPreview) => {
    setSelectedAccount(id);
    setSelectedPreview(preview);
  };

  return (
    <TooltipProvider delayDuration={200}>
      <div className="container mx-auto py-8 space-y-6">


        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Investigation Workbench
            </h1>
            <p className="text-muted-foreground">
              🕵️ Robbie Henderson — Senior Revenue Protection Analyst
            </p>
          </div>
          <Badge variant="outline" className="text-accent border-accent/50">
            Live ML Inference
          </Badge>
        </div>

        {/* Operational KPIs */}
        <div id="investigation-kpis">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
            Today's Operations
          </h2>
          <Suspense fallback={<KPISkeleton />}>
            <InvestigationKPIRow
              onRiskFilterChange={setRiskFilter}
              onStatusFilterChange={setStatusFilter}
              activeRiskFilter={riskFilter}
              activeStatusFilter={statusFilter}
            />
          </Suspense>
        </div>

        {/* AI Daily Briefing */}
        <Suspense fallback={<BriefingSkeleton />}>
          <DailyBriefingCard />
        </Suspense>

        {/* Flagged Accounts */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CardTitle>Flagged Accounts</CardTitle>
                {(riskFilter || statusFilter) && (
                  <div className="flex items-center gap-1.5">
                    {riskFilter && (
                      <Badge variant="outline" className="gap-1 text-xs">
                        <Filter className="h-3 w-3" />
                        {riskFilter} risk
                        <button
                          onClick={() => setRiskFilter(null)}
                          className="ml-1 hover:text-destructive"
                        >
                          ×
                        </button>
                      </Badge>
                    )}
                    {statusFilter && (
                      <Badge variant="outline" className="gap-1 text-xs">
                        <Filter className="h-3 w-3" />
                        {STATUS_LABELS[statusFilter]}
                        <button
                          onClick={() => setStatusFilter(null)}
                          className="ml-1 hover:text-destructive"
                        >
                          ×
                        </button>
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-4">
                <div className="flex gap-1.5">
                  {(["HIGH", "MEDIUM", "LOW"] as RiskTier[]).map((tier) => (
                    <Badge
                      key={tier}
                      variant={tier === "HIGH" ? "destructive" : "outline"}
                      className={`cursor-pointer transition-all ${
                        riskFilter === tier
                          ? "ring-2 ring-offset-1 ring-accent"
                          : riskFilter && riskFilter !== tier
                            ? "opacity-40"
                            : ""
                      } ${
                        tier === "MEDIUM"
                          ? "border-amber-500 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                          : tier === "LOW"
                            ? "border-emerald-500 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                            : "hover:bg-red-50 dark:hover:bg-red-950/30"
                      }`}
                      onClick={() => setRiskFilter(riskFilter === tier ? null : tier)}
                    >
                      {tier}
                    </Badge>
                  ))}
                </div>
                <div className="h-5 w-px bg-border" />
                <div className="flex gap-1.5">
                  {(Object.keys(InvestigationStatus) as StatusFilter[]).map((status) => (
                    <Badge
                      key={status}
                      variant="outline"
                      className={`cursor-pointer transition-all text-xs ${
                        statusFilter === status
                          ? "ring-2 ring-offset-1 ring-accent"
                          : statusFilter && statusFilter !== status
                            ? "opacity-40"
                            : ""
                      } ${STATUS_BADGE_STYLES[status]}`}
                      onClick={() => setStatusFilter(statusFilter === status ? null : status)}
                    >
                      {STATUS_LABELS[status]}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<AccountTableSkeleton />}>
              <AccountTable
                onSelectAccount={handleSelectAccount}
                riskFilter={riskFilter}
                statusFilter={statusFilter}
              />
            </Suspense>
          </CardContent>
        </Card>

        {/* View Architecture — links back to hero page */}
        <div className="flex justify-center">
          <Button
            variant="outline"
            className="gap-2 border-accent/40 text-accent hover:bg-accent/10"
            asChild
          >
            <Link to="/" hash="architecture">
              <LayoutDashboard className="h-4 w-4" />
              Show me the Architecture
            </Link>
          </Button>
        </div>

        {/* Detail Drawer */}
        <Sheet
          open={selectedAccount !== null}
          onOpenChange={(open) => {
            if (!open) {
              setSelectedAccount(null);
              setSelectedPreview(undefined);
            }
          }}
        >
          <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto">
            {selectedAccount && (
              <Suspense
                fallback={
                  <div className="space-y-4 p-4">
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-40 w-full" />
                    <Skeleton className="h-40 w-full" />
                  </div>
                }
              >
                <AccountDetailDrawer
                  accountId={selectedAccount}
                  accountPreview={selectedPreview}
                />
              </Suspense>
            )}
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// Operational KPI Tiles
// ---------------------------------------------------------------------------

interface KPITileProps {
  label: string;
  value: string;
  icon: React.ElementType;
  color: string;
  iconColor: string;
  tooltip: string;
  onClick?: () => void;
  active?: boolean;
  subtitle?: string;
  highlight?: boolean;
  highlightDelta?: string;
}

function KPITile({ label, value, icon: Icon, color, iconColor, tooltip, onClick, active, subtitle, highlight, highlightDelta }: KPITileProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Card
          className={`relative overflow-hidden transition-all ${
            onClick ? "cursor-pointer hover:shadow-md hover:scale-[1.02]" : ""
          } ${active ? "ring-2 ring-accent ring-offset-1" : ""} ${
            highlight ? "ring-2 ring-green-500 ring-offset-1 animate-pulse" : ""
          }`}
          onClick={onClick}
        >
          <div className={`absolute left-0 top-0 bottom-0 w-1 ${highlight ? "bg-green-500" : color}`} />
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {label}
                </p>
                <p className="text-2xl font-bold tracking-tight">{value}</p>
                {highlightDelta && (
                  <p className="text-xs font-semibold text-green-600 animate-bounce">
                    +{highlightDelta} just recovered
                  </p>
                )}
                {!highlightDelta && subtitle && (
                  <p className="text-xs text-muted-foreground">{subtitle}</p>
                )}
              </div>
              <Icon className={`h-5 w-5 ${highlight ? "text-green-500" : iconColor}`} />
            </div>
          </CardContent>
        </Card>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-[280px] text-xs">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

function InvestigationKPIRow({
  onRiskFilterChange,
  onStatusFilterChange,
  activeRiskFilter,
  activeStatusFilter,
}: {
  onRiskFilterChange: (tier: RiskTier | null) => void;
  onStatusFilterChange: (status: StatusFilter | null) => void;
  activeRiskFilter: RiskTier | null;
  activeStatusFilter: StatusFilter | null;
}) {
  const { data: kpis } = useGetInvestigationKPIsSuspense(selector());
  const [recoveredHighlight, setRecoveredHighlight] = useState<number | null>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const amount = (e as CustomEvent<number>).detail;
      setRecoveredHighlight(amount);
      if (highlightTimer.current) clearTimeout(highlightTimer.current);
      highlightTimer.current = setTimeout(() => setRecoveredHighlight(null), 8000);
    };
    window.addEventListener("investigation-closed-theft", handler);
    return () => {
      window.removeEventListener("investigation-closed-theft", handler);
      if (highlightTimer.current) clearTimeout(highlightTimer.current);
    };
  }, []);

  const isOpenHighActive = activeRiskFilter === "HIGH" && activeStatusFilter === "OPEN";
  const isInProgressActive = activeStatusFilter === "IN_PROGRESS" && !activeRiskFilter;

  const handleOpenHighClick = () => {
    if (isOpenHighActive) {
      onRiskFilterChange(null);
      onStatusFilterChange(null);
    } else {
      onRiskFilterChange("HIGH");
      onStatusFilterChange("OPEN");
    }
  };

  const handleInProgressClick = () => {
    if (isInProgressActive) {
      onRiskFilterChange(null);
      onStatusFilterChange(null);
    } else {
      onRiskFilterChange(null);
      onStatusFilterChange("IN_PROGRESS");
    }
  };

  const formatCompactGbp = (value: number) => {
    if (value >= 1_000_000_000) return `£${(value / 1_000_000_000).toFixed(1)}B`;
    if (value >= 1_000_000) return `£${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `£${(value / 1_000).toFixed(1)}K`;
    return `£${Math.round(value).toLocaleString("en-GB")}`;
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      <KPITile
        label="Open Cases Awaiting Triage"
        value={String(kpis.open_high_cases)}
        icon={Siren}
        color="bg-red-500"
        iconColor="text-red-500"
        tooltip="HIGH-risk accounts flagged by ML models awaiting investigation. Click to filter the table to open HIGH cases, ordered by risk score."
        onClick={handleOpenHighClick}
        active={isOpenHighActive}
        subtitle="HIGH risk · ordered by score"
      />
      <KPITile
        label="In Progress"
        value={String(kpis.in_progress_cases)}
        icon={Users}
        color="bg-blue-500"
        iconColor="text-blue-500"
        tooltip="Cases currently under active investigation by the team. Click to filter the table to in-progress cases, ordered by risk score."
        onClick={handleInProgressClick}
        active={isInProgressActive}
        subtitle={`${kpis.open_medium_cases} MEDIUM queued`}
      />
      <KPITile
        label="Detection Precision"
        value={`${kpis.precision_rate_pct}%`}
        icon={Target}
        color="bg-emerald-500"
        iconColor="text-emerald-500"
        tooltip="Confirmed theft / total closed HIGH cases (all time). Target: >60%. Source: investigation_cases table."
        subtitle="Target >60%"
      />
      <KPITile
        label="Avg Days to Close"
        value={kpis.avg_days_to_close.toFixed(1)}
        icon={Clock}
        color="bg-amber-500"
        iconColor="text-amber-500"
        tooltip="Average calendar days from case opened to closed. Target: <3 working days from flag to field dispatch."
        subtitle="Target <5 days"
      />
      <KPITile
        label="Recovered This Month"
        value={formatCompactGbp(kpis.revenue_recovered_this_month_gbp)}
        icon={PoundSterling}
        color="bg-emerald-500"
        iconColor="text-emerald-500"
        tooltip={`Revenue recovered from confirmed theft back-billing this calendar month. ${kpis.confirmed_theft_this_month} confirmed cases, ${kpis.closed_this_month} total closed.`}
        subtitle={`${kpis.confirmed_theft_this_month} confirmed this month`}
        highlight={recoveredHighlight !== null}
        highlightDelta={recoveredHighlight !== null ? `£${recoveredHighlight.toLocaleString("en-GB")}` : undefined}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI Daily Briefing
// ---------------------------------------------------------------------------

function DailyBriefingCard() {
  const { data: briefing } = useGetDailyBriefingSuspense(selector());

  return (
    <Card className="border-accent/20 bg-accent/[0.02]">
      <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" />
            <div>
              <CardTitle className="text-base">Good Morning, Robbie</CardTitle>
              <p className="text-xs text-muted-foreground">
                AI Briefing · {briefing.generated_at}
              </p>
            </div>
            <BedrockHood />
          </div>
          <ModelBadge />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm font-semibold leading-relaxed">{briefing.briefing}</p>
        {briefing.actions && briefing.actions.length > 0 && (
          <ol className="list-decimal list-inside space-y-1.5 text-sm text-muted-foreground">
            {briefing.actions.map((action, i) => (
              <li key={i} className="leading-relaxed">
                {action}
              </li>
            ))}
          </ol>
        )}
        <div className="flex flex-wrap gap-3 text-xs">
          {(briefing.new_high_flags_24h ?? 0) > 0 && (
            <Badge variant="destructive" className="gap-1">
              <Siren className="h-3 w-3" />
              {briefing.new_high_flags_24h} new HIGH flags (24h)
            </Badge>
          )}
          {(briefing.oldest_open_days ?? 0) > 3 && (
            <Badge variant="outline" className="gap-1 border-amber-500 text-amber-600">
              <Clock className="h-3 w-3" />
              Oldest open: {briefing.oldest_open_days} days
            </Badge>
          )}
          {briefing.cluster_alert && (
            <Badge variant="outline" className="gap-1 border-red-400 text-red-500">
              <MapPin className="h-3 w-3" />
              {briefing.cluster_alert}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Flagged Account Table
// ---------------------------------------------------------------------------

function AccountTable({
  onSelectAccount,
  riskFilter,
  statusFilter,
}: {
  onSelectAccount: (id: string, preview?: AccountRowPreview) => void;
  riskFilter: RiskTier | null;
  statusFilter: StatusFilter | null;
}) {
  const queryClient = useQueryClient();
  const params: Record<string, string> = {};
  if (riskFilter) params.risk_tier = riskFilter;
  if (statusFilter) params.investigation_status = statusFilter;
  const hasParams = Object.keys(params).length > 0;
  const { data: accounts } = useListFlaggedAccountsSuspense({ ...selector(), params: hasParams ? params : undefined });

  if (accounts.length === 0) {
    const hasFilters = riskFilter || statusFilter;
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>
          {hasFilters
            ? `No accounts found matching the active filters.`
            : "Connect SQL Warehouse to load flagged accounts from anomaly_scores table"}
        </p>
        {!hasFilters && (
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => onSelectAccount("BG-0000001")}
          >
            Preview account BG-0000001
          </Button>
        )}
      </div>
    );
  }

  const tierColor = (tier: string) => {
    if (tier === "HIGH") return "destructive" as const;
    return "outline" as const;
  };

  const tierBadgeClass = (tier: string) => {
    if (tier === "MEDIUM") return "border-amber-500 text-amber-600";
    if (tier === "LOW") return "border-emerald-500 text-emerald-600";
    return "";
  };

  const statusBadgeClass = (status: string) => {
    if (status === "CONFIRMED_THEFT") return "border-red-500 text-red-600 bg-red-50 dark:bg-red-950/30";
    if (status === "IN_PROGRESS") return "border-blue-500 text-blue-600 bg-blue-50 dark:bg-blue-950/30";
    if (status === "CLOSED") return "border-gray-400 text-gray-500";
    return "";
  };

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Account</TableHead>
            <TableHead>Postcode</TableHead>
            <TableHead>Risk</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead className="text-right">Drop %</TableHead>
            <TableHead className="text-right">Gaps</TableHead>
            <TableHead>Fuel</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {accounts.map((a) => {
            const preview: AccountRowPreview = {
              account_id: a.account_id,
              risk_tier: a.risk_tier,
              composite_risk_score: a.composite_risk_score,
              consumption_drop_pct: a.consumption_drop_pct,
              comms_gap_count_30d: a.comms_gap_count_30d,
            };
            return (
              <TableRow
                key={a.account_id}
                className="cursor-pointer hover:bg-muted/50"
                onMouseEnter={() => {
                  queryClient.prefetchQuery({
                    queryKey: getAccountDetailKey({ account_id: a.account_id }),
                    queryFn: () =>
                      getAccountDetail({ account_id: a.account_id }, withModelHeaders()),
                  });
                  queryClient.prefetchQuery({
                    queryKey: getCaseSummaryWithPreviewKey(a.account_id, preview),
                    queryFn: () => getCaseSummaryWithPreview(a.account_id, preview),
                  });
                }}
                onClick={() => onSelectAccount(a.account_id, preview)}
              >
              <TableCell className="font-mono text-sm">
                {a.account_id}
              </TableCell>
              <TableCell>{a.postcode}</TableCell>
              <TableCell>
                <Badge
                  variant={tierColor(a.risk_tier)}
                  className={tierBadgeClass(a.risk_tier)}
                >
                  {a.risk_tier}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-mono">
                {a.composite_risk_score.toFixed(2)}
              </TableCell>
              <TableCell className="text-right">
                {a.consumption_drop_pct.toFixed(1)}%
              </TableCell>
              <TableCell className="text-right">
                {a.comms_gap_count_30d}
              </TableCell>
              <TableCell className="capitalize">{a.fuel_type}</TableCell>
              <TableCell>
                <Badge
                  variant="outline"
                  className={`text-xs ${statusBadgeClass(a.investigation_status)}`}
                >
                  {a.investigation_status.replace("_", " ")}
                </Badge>
              </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// LLM Case Summary — lazy-loaded behind its own Suspense boundary
// ---------------------------------------------------------------------------

function CaseSummarySkeleton({ preview }: { preview?: AccountRowPreview }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">LLM Case Summary</CardTitle>
          <ModelBadge showModel />
        </div>
        <div className="flex flex-wrap gap-2 text-xs mt-1">
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" style={{ color: AWS_ORANGE }} />
            Generating with Bedrock…
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {preview && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/30 px-3 py-2">
            <Badge variant="destructive">{preview.risk_tier}</Badge>
            <span className="text-sm text-muted-foreground">
              Score {preview.composite_risk_score.toFixed(2)} · Drop{" "}
              {preview.consumption_drop_pct.toFixed(1)}% · {preview.comms_gap_count_30d} comms gaps
            </span>
          </div>
        )}
        <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ backgroundColor: `${AWS_ORANGE}18` }}>
          <div
            className="h-full w-1/3 rounded-full animate-bedrock-progress"
            style={{ backgroundColor: AWS_ORANGE }}
          />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-5/6" />
        </div>
        <Skeleton className="h-4 w-2/3" />
      </CardContent>
    </Card>
  );
}

function CaseSummaryCard({
  accountId,
  accountPreview,
}: {
  accountId: string;
  accountPreview?: AccountRowPreview;
}) {
  const { data: summaryWrapper } = useSuspenseQuery({
    queryKey: getCaseSummaryWithPreviewKey(accountId, accountPreview),
    queryFn: () => getCaseSummaryWithPreview(accountId, accountPreview),
  });
  const summary = summaryWrapper.data;

  return (
    <Card className="animate-fade-slide-up">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">LLM Case Summary</CardTitle>
          <ModelBadge showModel />
        </div>
        <div className="flex flex-wrap gap-2 text-xs mt-1">
          <Link to="/governance" className="inline-flex items-center gap-1 text-accent hover:underline">
            <ShieldCheck className="h-3 w-3" /> AI Governance & Audit Trail
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Badge variant="destructive">{summary.priority}</Badge>
          <Badge variant="outline">{summary.risk_level}</Badge>
        </div>
        <div>
          <p className="text-sm font-medium mb-1">Key Signals:</p>
          <ul className="text-sm text-muted-foreground space-y-1">
            {summary.key_signals.map((s: string, i: number) => (
              <li key={i}>• {s}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-sm font-medium">Recommended Action:</p>
          <p className="text-sm text-muted-foreground">
            {summary.recommended_action}
          </p>
        </div>
        {summary.estimated_loss_per_month_gbp && (
          <div>
            <p className="text-sm font-medium">Estimated Monthly Loss:</p>
            <p className="text-lg font-bold text-red-600">
              £{summary.estimated_loss_per_month_gbp.toFixed(0)}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Account Detail Drawer
// ---------------------------------------------------------------------------

function DrawerDetailSkeleton() {
  return (
    <div className="space-y-6 mt-6">
      <Card>
        <CardContent className="pt-6">
          <div className="flex justify-between items-center">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-8 w-16" />
          </div>
          <Skeleton className="h-2 w-full mt-2" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-3 w-48" />
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-3 w-64 mt-1" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}

function AccountDetailDrawer({
  accountId,
  accountPreview,
}: {
  accountId: string;
  accountPreview?: AccountRowPreview;
}) {
  return (
    <>
      <SheetHeader>
        <SheetTitle className="font-mono">{accountId}</SheetTitle>
      </SheetHeader>
      <Suspense fallback={<DrawerDetailSkeleton />}>
        <AccountDetailSignals accountId={accountId} />
      </Suspense>
      <div className="space-y-6 mt-6">
        <Suspense fallback={<CaseSummarySkeleton preview={accountPreview} />}>
          <CaseSummaryCard accountId={accountId} accountPreview={accountPreview} />
        </Suspense>
        <Suspense fallback={<ChartSkeleton />}>
          <AccountDetailChartAndDispatch accountId={accountId} />
        </Suspense>
      </div>
    </>
  );
}

function AccountDetailSignals({ accountId }: { accountId: string }) {
  const { data: detailWrapper } = useGetAccountDetailSuspense({ params: { account_id: accountId } });
  const detail = detailWrapper.data;
  const signals = detail.signals;

  return (
    <>
      <div className="flex gap-2 items-center mt-2">
        <Badge variant="destructive">{detail.risk_tier}</Badge>
        <span className="text-sm text-muted-foreground">
          {detail.postcode} · {detail.region} · {detail.property_type} ·
          Band {detail.council_tax_band}
        </span>
      </div>

      <div className="space-y-6 mt-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                Composite Risk Score
              </span>
              <span className="text-3xl font-bold text-red-600">
                {detail.composite_risk_score.toFixed(2)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted mt-2 overflow-hidden">
              <div
                className="h-full rounded-full bg-red-500"
                style={{ width: `${detail.composite_risk_score * 100}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <CardTitle className="text-base">Signal Breakdown</CardTitle>
                <MLflowHood />
              </div>
              <Link to="/governance" className="inline-flex items-center gap-1 text-xs text-accent hover:underline">
                <ShieldCheck className="h-3 w-3" /> AI Governance
              </Link>
            </div>
            <p className="text-xs text-muted-foreground">
              Each signal is produced by a registered ML model or rule-based scorer.
              Click the info icon for details, or view all models in{" "}
              <Link to="/governance" className="text-accent hover:underline">AI Governance</Link>.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <SignalBar signalKey="isolation_forest" value={signals.isolation_forest_score} />
            <SignalBar signalKey="lstm_deviation" value={signals.lstm_deviation_score} />
            <SignalBar signalKey="cohort_deviation" value={signals.cohort_deviation_score} />
            <SignalBar signalKey="comms_gap" value={signals.comms_gap_normalised} />
            <SignalBar signalKey="consumption_drop" value={signals.consumption_drop_normalised} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function AccountDetailChartAndDispatch({ accountId }: { accountId: string }) {
  const { data: detailWrapper } = useGetAccountDetailSuspense({ params: { account_id: accountId } });
  const detail = detailWrapper.data;
  const { modelConfig } = useDemoSettings();

  const [dispatch, setDispatch] = useState<DispatchReport | null>(null);
  const [scheduled, setScheduled] = useState(false);
  const [showScheduledDialog, setShowScheduledDialog] = useState(false);
  const dispatchMutation = useGenerateDispatchReport();

  const handleGenerate = () => {
    dispatchMutation.mutate(
      { params: { account_id: accountId } },
      { onSuccess: (res) => setDispatch(res.data) },
    );
  };

  const handleDownloadPdf = () => {
    if (!dispatch) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.write(`<!DOCTYPE html><html><head>
      <title>Dispatch ${dispatch.case_reference}</title>
      <style>
        body{font-family:system-ui,sans-serif;max-width:700px;margin:40px auto;padding:0 20px;color:#1a1a1a;font-size:14px}
        h1{font-size:18px;border-bottom:2px solid #0A84C8;padding-bottom:8px}
        h2{font-size:14px;color:#0A84C8;margin-top:24px;margin-bottom:8px}
        .meta{display:flex;gap:24px;font-size:13px;color:#666;margin-bottom:16px}
        .priority{background:#dc2626;color:#fff;padding:2px 10px;border-radius:4px;font-weight:600;font-size:12px}
        .narrative{background:#f0f9ff;border-left:3px solid #0A84C8;padding:12px 16px;margin:16px 0;font-style:italic}
        ul{padding-left:20px} li{margin-bottom:4px}
        .safety{background:#fef2f2;border-left:3px solid #dc2626;padding:12px 16px;margin:16px 0}
        .footer{margin-top:32px;padding-top:12px;border-top:1px solid #e5e7eb;font-size:11px;color:#999}
      </style>
    </head><body>
      <h1>UKI Gas — Field Investigation Dispatch</h1>
      <div class="meta">
        <span><strong>Case:</strong> ${dispatch.case_reference}</span>
        <span class="priority">${dispatch.priority}</span>
        <span><strong>Date:</strong> ${dispatch.generated_at}</span>
      </div>
      <h2>Property Details</h2>
      <p>Account: ${dispatch.account_id} | Postcode: ${dispatch.postcode} | ${dispatch.region}<br/>
      Property: ${dispatch.property_type}, Band ${dispatch.council_tax_band} | Fuel: ${dispatch.fuel_type}</p>
      <h2>Risk Summary</h2>
      <p>Composite Score: <strong>${dispatch.composite_risk_score.toFixed(2)}</strong> / 1.0 |
      Consumption Drop: <strong>${dispatch.consumption_drop_pct.toFixed(1)}%</strong> |
      Comms Gaps: <strong>${dispatch.comms_gap_count_30d}</strong> in 30d</p>
      <h2>AI Briefing</h2>
      <div class="narrative">${dispatch.narrative}</div>
      <h2>Local Intelligence</h2>
      <p>${dispatch.nearby_high_risk_count} other HIGH-risk accounts in postcode sector.
      Prior confirmed theft in sector: ${dispatch.prior_theft_in_sector ? "Yes" : "No"}.</p>
      <h2>Recommended Actions</h2>
      <ul>${dispatch.recommended_actions.map((a) => `<li>${a}</li>`).join("")}</ul>
      <h2>Evidence Checklist</h2>
      <ul>${dispatch.evidence_checklist.map((e) => `<li>☐ ${e}</li>`).join("")}</ul>
      <h2>Safety Notes</h2>
      <div class="safety"><ul>${dispatch.safety_notes.map((s) => `<li>${s}</li>`).join("")}</ul></div>
      <h2>Estimated Financial Impact</h2>
      <p>Monthly loss: <strong>£${dispatch.estimated_monthly_loss_gbp.toFixed(0)}</strong> |
      Annual exposure: <strong>£${(dispatch.estimated_monthly_loss_gbp * 12).toFixed(0)}</strong></p>
      <div class="footer">Generated by Databricks AI Gateway (${modelConfig.model} via ${modelConfig.provider}) — all calls governed and audited in Unity Catalog.</div>
    </body></html>`);
    printWindow.document.close();
    printWindow.print();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">90-Day Consumption Profile</CardTitle>
          <p className="text-xs text-muted-foreground">
            Daily average kWh — account vs postcode-sector cohort
          </p>
        </CardHeader>
        <CardContent>
          <ConsumptionChart
            meterReads={detail.meter_reads}
            cohortReads={detail.cohort_avg_reads}
            anomalyOnset={detail.anomaly_onset ?? null}
          />
        </CardContent>
      </Card>

      {/* Field Dispatch */}
        {!dispatch ? (
          <Button
            className="w-full"
            size="lg"
            onClick={handleGenerate}
            disabled={dispatchMutation.isPending}
          >
            {dispatchMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating dispatch briefing...
              </>
            ) : (
              <>
                <FileText className="h-4 w-4 mr-2" />
                Generate Field Dispatch
              </>
            )}
          </Button>
        ) : (
          <Card className="border-accent/30">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-base">Field Investigation Dispatch</CardTitle>
                  <Badge variant="destructive" className="text-xs">{dispatch.priority}</Badge>
                </div>
                <ModelBadge />
              </div>
              <p className="text-xs text-muted-foreground">
                {dispatch.case_reference} · {dispatch.generated_at}
              </p>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="bg-accent/5 border-l-2 border-accent p-3 rounded-r text-sm italic text-muted-foreground">
                {dispatch.narrative}
              </div>

              <div>
                <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Local Intelligence</p>
                <p className="text-sm">
                  {dispatch.nearby_high_risk_count} other HIGH-risk accounts in sector
                  · Prior theft: {dispatch.prior_theft_in_sector ? "Yes" : "No"}
                </p>
              </div>

              <div>
                <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Recommended Actions</p>
                <ol className="list-decimal list-inside space-y-1 text-sm">
                  {dispatch.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}
                </ol>
              </div>

              <div>
                <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Evidence Checklist</p>
                <ul className="space-y-1 text-sm">
                  {dispatch.evidence_checklist.map((e, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-muted-foreground">☐</span> {e}
                    </li>
                  ))}
                </ul>
              </div>

              {dispatch.safety_notes.length > 0 && (
                <div className="bg-red-50 dark:bg-red-950/30 border-l-2 border-red-500 p-3 rounded-r">
                  <p className="font-medium text-xs text-red-700 dark:text-red-400 uppercase tracking-wide mb-1 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" /> Safety Notes
                  </p>
                  <ul className="space-y-1 text-sm text-red-800 dark:text-red-300">
                    {dispatch.safety_notes.map((s, i) => <li key={i}>• {s}</li>)}
                  </ul>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 border-t">
                <p className="text-sm">
                  Est. monthly loss: <span className="font-bold text-red-600">£{dispatch.estimated_monthly_loss_gbp.toFixed(0)}</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Annual: £{(dispatch.estimated_monthly_loss_gbp * 12).toFixed(0)}
                </p>
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={handleDownloadPdf} className="flex-1">
                  <Download className="h-3.5 w-3.5 mr-1.5" /> Download PDF
                </Button>
                {!scheduled ? (
                  <Button size="sm" onClick={() => { setScheduled(true); setShowScheduledDialog(true); }} className="flex-1">
                    <FileText className="h-3.5 w-3.5 mr-1.5" /> Schedule Investigation
                  </Button>
                ) : (
                  <Button size="sm" onClick={() => setShowScheduledDialog(true)} className="flex-1 bg-green-600 hover:bg-green-600 text-white">
                    <CheckCircle className="h-3.5 w-3.5 mr-1.5" /> Investigation Scheduled
                  </Button>
                )}
              </div>

              <Dialog open={showScheduledDialog} onOpenChange={setShowScheduledDialog}>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <CalendarCheck className="h-5 w-5 text-green-600" />
                      Investigation Scheduled
                    </DialogTitle>
                    <DialogDescription>
                      A field investigation has been scheduled for this account.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-3 py-2">
                    <div className="rounded-lg border bg-green-50 p-4 space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Account</span>
                        <span className="font-medium">{accountId}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Scheduled Date</span>
                        <span className="font-medium">
                          {new Date(Date.now() + 86400000).toLocaleDateString("en-GB", {
                            weekday: "long",
                            day: "numeric",
                            month: "long",
                            year: "numeric",
                          })}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Priority</span>
                        <span className="font-medium text-red-600">{dispatch?.priority ?? "HIGH"}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Case Ref</span>
                        <span className="font-mono text-xs">{dispatch?.case_reference ?? "—"}</span>
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button size="sm" onClick={() => setShowScheduledDialog(false)} className="bg-green-600 hover:bg-green-700 text-white">
                      Done
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        )}

        {dispatchMutation.isError && (
          <p className="text-sm text-destructive text-center">
            Failed to generate dispatch. Try again.
          </p>
        )}

        {/* Close Investigation */}
        <CloseInvestigationSection accountId={accountId} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Close Investigation
// ---------------------------------------------------------------------------

function CloseInvestigationSection({ accountId }: { accountId: string }) {
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState<"confirmed_theft" | "no_theft" | "inconclusive">("confirmed_theft");
  const [recoveredAmount, setRecoveredAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [closedDialog, setClosedDialog] = useState<{ outcome: string; recovered: number | null; message: string } | null>(null);
  const closeMutation = useCloseInvestigation();
  const queryClient = useQueryClient();

  const handleSubmit = () => {
    closeMutation.mutate(
      {
        params: { account_id: accountId },
        data: {
          outcome,
          recovered_amount: outcome === "confirmed_theft" && recoveredAmount ? parseFloat(recoveredAmount) : undefined,
          notes: notes || undefined,
        },
      },
      {
        onSuccess: (resp) => {
          setOpen(false);
          setClosedDialog({
            outcome: resp.data.outcome,
            recovered: resp.data.recovered_amount ?? null,
            message: resp.data.message ?? "Investigation closed successfully",
          });
          queryClient.invalidateQueries({ queryKey: listFlaggedAccountsKey() });
          queryClient.invalidateQueries({ queryKey: getInvestigationKPIsKey() });
          queryClient.invalidateQueries({ queryKey: getDashboardKPIsKey() });
        },
        onError: (err: unknown) => {
          const detail =
            err instanceof Error ? err.message : "Unknown error";
          toast.error(`Failed to close investigation: ${detail}`);
        },
      },
    );
  };

  return (
    <div className="pt-2">
      {!open ? (
        <Button
          variant="outline"
          className="w-full border-green-500/40 text-green-600 hover:bg-green-50"
          onClick={() => setOpen(true)}
        >
          <CheckCircle className="h-4 w-4 mr-2" />
          Close Investigation
        </Button>
      ) : (
        <Card className="border-green-500/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Close Investigation — {accountId}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Outcome</p>
              <div className="grid grid-cols-3 gap-2">
                {([
                  { value: "confirmed_theft", label: "Confirmed Theft", color: "border-red-500 bg-red-50 text-red-700" },
                  { value: "no_theft", label: "No Theft", color: "border-green-500 bg-green-50 text-green-700" },
                  { value: "inconclusive", label: "Inconclusive", color: "border-amber-500 bg-amber-50 text-amber-700" },
                ] as const).map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setOutcome(opt.value)}
                    className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                      outcome === opt.value ? opt.color + " ring-2 ring-offset-1 ring-current" : "border-muted bg-muted/30 text-muted-foreground"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {outcome === "confirmed_theft" && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Recovered Amount (£)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 4500.00"
                  value={recoveredAmount}
                  onChange={(e) => setRecoveredAmount(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                />
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Notes (optional)
              </label>
              <textarea
                placeholder="Investigation notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none"
              />
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                disabled={closeMutation.isPending}
                onClick={handleSubmit}
              >
                {closeMutation.isPending ? (
                  <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> Closing...</>
                ) : (
                  <><CheckCircle className="h-3.5 w-3.5 mr-1.5" /> Confirm Close</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={closedDialog !== null} onOpenChange={(v) => {
        if (!v) {
          const wasTh = closedDialog?.outcome === "THEFT_CONFIRMED" && closedDialog?.recovered;
          const amt = closedDialog?.recovered;
          setClosedDialog(null);
          if (wasTh && amt) {
            document.getElementById("investigation-kpis")?.scrollIntoView({ behavior: "smooth", block: "start" });
            setTimeout(() => {
              window.dispatchEvent(new CustomEvent("investigation-closed-theft", { detail: amt }));
            }, 400);
          }
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Investigation Closed
            </DialogTitle>
            <DialogDescription>
              The investigation outcome has been written to Lakebase.
            </DialogDescription>
          </DialogHeader>
          {closedDialog && (
            <div className="space-y-3 py-2">
              <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Account</span>
                  <span className="font-medium">{accountId}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Outcome</span>
                  <span className={`font-medium ${
                    closedDialog.outcome === "THEFT_CONFIRMED" ? "text-red-600" :
                    closedDialog.outcome === "FALSE_POSITIVE" ? "text-green-600" :
                    "text-amber-600"
                  }`}>
                    {closedDialog.outcome === "THEFT_CONFIRMED" ? "Confirmed Theft" :
                     closedDialog.outcome === "FALSE_POSITIVE" ? "No Theft" :
                     "Inconclusive"}
                  </span>
                </div>
                {closedDialog.recovered !== null && closedDialog.recovered > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Recovered</span>
                    <span className="font-medium text-green-700">
                      £{closedDialog.recovered.toLocaleString("en-GB", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Closed At</span>
                  <span className="font-medium">
                    {new Date().toLocaleDateString("en-GB", {
                      day: "numeric", month: "long", year: "numeric",
                    })}, {new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground text-center">{closedDialog.message}</p>
            </div>
          )}
          <DialogFooter>
            <Button size="sm" onClick={() => {
              const wasTh = closedDialog?.outcome === "THEFT_CONFIRMED" && closedDialog?.recovered;
              const amt = closedDialog?.recovered;
              setClosedDialog(null);
              if (wasTh && amt) {
                document.getElementById("investigation-kpis")?.scrollIntoView({ behavior: "smooth", block: "start" });
                setTimeout(() => {
                  window.dispatchEvent(new CustomEvent("investigation-closed-theft", { detail: amt }));
                }, 400);
              }
            }} className="bg-green-600 hover:bg-green-700 text-white">
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 90-Day Consumption Chart
// ---------------------------------------------------------------------------

const Plot = lazy(() => import("react-plotly.js"));

function ConsumptionChart({
  meterReads,
  cohortReads,
  anomalyOnset,
}: {
  meterReads: MeterReadPoint[];
  cohortReads: MeterReadPoint[];
  anomalyOnset: string | null;
}) {
  const { accountDates, accountVals, cohortDates, cohortVals, shapes, annotations } = useMemo(() => {
    const ad = meterReads.map((r) => r.read_timestamp);
    const av = meterReads.map((r) => r.consumption_kwh);
    const cd = cohortReads.map((r) => r.read_timestamp);
    const cv = cohortReads.map((r) => r.consumption_kwh);

    const sh: Plotly.Shape[] = [];
    const an: Plotly.Annotations[] = [];
    if (anomalyOnset) {
      sh.push({
        type: "line",
        x0: anomalyOnset,
        x1: anomalyOnset,
        y0: 0,
        y1: 1,
        yref: "paper",
        line: { color: "#dc2626", width: 2, dash: "dash" },
      } as never);
      an.push({
        x: anomalyOnset,
        y: 1,
        yref: "paper",
        text: "Anomaly flagged",
        showarrow: false,
        font: { size: 10, color: "#dc2626" },
        yanchor: "bottom",
        xanchor: "left",
        xshift: 4,
      } as never);
    }
    return { accountDates: ad, accountVals: av, cohortDates: cd, cohortVals: cv, shapes: sh, annotations: an };
  }, [meterReads, cohortReads, anomalyOnset]);

  if (meterReads.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-muted-foreground text-sm">
        No meter reads available for this account
      </div>
    );
  }

  return (
    <Suspense fallback={<div className="h-52 flex items-center justify-center text-muted-foreground text-sm">Loading chart…</div>}>
      <Plot
        data={[
          {
            x: accountDates,
            y: accountVals,
            type: "scatter",
            mode: "lines",
            name: "This account",
            line: { color: "#dc2626", width: 2 },
            fill: "tozeroy",
            fillcolor: "rgba(220,38,38,0.08)",
          },
          ...(cohortDates.length > 0
            ? [{
                x: cohortDates,
                y: cohortVals,
                type: "scatter" as const,
                mode: "lines" as const,
                name: "Cohort avg",
                line: { color: "#6b7280", width: 1.5, dash: "dot" as const },
              }]
            : []),
        ]}
        layout={{
          height: 210,
          margin: { t: 10, r: 10, b: 40, l: 50 },
          xaxis: { type: "date", tickformat: "%d %b", gridcolor: "#f3f4f6" },
          yaxis: { title: { text: "kWh", standoff: 8, font: { size: 11 } }, gridcolor: "#f3f4f6" },
          legend: { orientation: "h", y: -0.25, x: 0.5, xanchor: "center", font: { size: 10 } },
          shapes,
          annotations,
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { family: "system-ui, sans-serif", size: 11 },
        }}
        config={{ displayModeBar: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%" }}
      />
    </Suspense>
  );
}

// ---------------------------------------------------------------------------
// Under the Hood panels
// ---------------------------------------------------------------------------

function MLflowHood() {
  return (
    <UnderTheHood title="MLflow on Databricks — MLOps">
      <HoodSection title="How it's built" icon={Layers}>
        <HoodBullet icon={BookOpen} bold="Single open API">
          MLflow: tracking, registry, evaluation, and serving — same API in notebooks, jobs, and across clouds. Open-source, adopted by AWS, Azure, GCP.
        </HoodBullet>
        <HoodBullet icon={ShieldCheck} bold="UC-governed models">
          Models governed alongside data — same access control, tags, audit, and lineage. One permission model.
        </HoodBullet>
        <HoodBullet icon={Zap} bold="Serverless scoring">
          Jobs score 10K accounts, write to Delta, scale to zero. No separate ML infrastructure to manage.
        </HoodBullet>
      </HoodSection>

      <FabricCallout entryId="model-lifecycle" />
    </UnderTheHood>
  );
}

function BedrockHood() {
  return (
    <UnderTheHood title="AI Gateway & Bedrock — Multi-Cloud LLM">
      <HoodSection title="How it's built" icon={Layers}>
        <HoodBullet icon={Cpu} bold="One endpoint, any provider">
          Amazon Nova Lite on AWS Bedrock via a single Databricks API. Swap providers without code changes.
        </HoodBullet>
        <HoodBullet icon={Shield} bold="AI governance built in">
          Access control, guardrails, audit, rate limiting — all logged to UC system tables and inference tables. One place.
        </HoodBullet>
        <HoodBullet icon={Code} bold="Declared in DABs">
          Endpoint defined in{" "}
          <code className="text-[11px] bg-muted px-0.5 rounded font-mono">databricks.yml</code>. Deploy, promote, and audit across environments as code.
        </HoodBullet>
      </HoodSection>

      <FabricCallout entryId="ai-gateway" />
    </UnderTheHood>
  );
}

// ---------------------------------------------------------------------------
// Signal Bar (reused in drawer)
// ---------------------------------------------------------------------------

function SignalBar({ signalKey, value }: { signalKey: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 75 ? "bg-red-500" : pct >= 50 ? "bg-amber-500" : "bg-green-500";
  const meta = SIGNAL_META[signalKey];

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="flex items-center gap-1.5">
          <Link to="/governance" className="hover:text-accent hover:underline transition-colors">
            {meta?.label ?? signalKey}
          </Link>
          <Tooltip>
            <TooltipTrigger asChild>
              <button className="text-muted-foreground/50 hover:text-muted-foreground">
                <Info className="h-3 w-3" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[280px] text-xs space-y-1.5">
              <p>{meta?.tooltip}</p>
              <p className="text-accent font-medium">Model: {meta?.model}</p>
            </TooltipContent>
          </Tooltip>
        </span>
        <span className="font-mono text-muted-foreground">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeletons
// ---------------------------------------------------------------------------

function KPISkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="pt-4 pb-3 px-4">
            <Skeleton className="h-3 w-24 mb-2" />
            <Skeleton className="h-8 w-16" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function BriefingSkeleton() {
  return (
    <Card className="border-accent/20 bg-accent/[0.02]">
      <CardContent className="py-10">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <BedrockLogo className="h-10 w-10 animate-pulse" />
            <span
              className="absolute -top-1 -right-1 h-3 w-3 rounded-full animate-ping"
              style={{ backgroundColor: AWS_ORANGE }}
            />
          </div>
          <div className="text-center space-y-1.5">
            <p className="text-sm font-semibold" style={{ color: AWS_ORANGE }}>
              Amazon Bedrock AI Investigation Briefing
            </p>
            <p className="text-xs text-muted-foreground">
              Generating today's intelligence summary via Amazon Nova Lite…
            </p>
          </div>
          <div className="w-64 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full animate-[slideProgress_2s_ease-in-out_infinite]"
              style={{
                background: `linear-gradient(90deg, transparent 0%, ${AWS_ORANGE} 50%, transparent 100%)`,
                width: "30%",
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AccountTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}
