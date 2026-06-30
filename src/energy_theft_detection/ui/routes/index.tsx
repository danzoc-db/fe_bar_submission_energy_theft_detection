import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ArrowRight,
  BarChart3,
  Bot,
  LayoutDashboard,
  Search,
  Info,
  Brain,
  Sparkles,
  Shield,
  Zap,
  FileText,
  MapPin,
  ClipboardList,
  Route as RouteIcon,
  AlertTriangle,
  Eye,
  ChevronDown,
} from "lucide-react";
import { ArchitectureDiagram } from "@/components/architecture-diagram";
import { useDemoSettings, MODEL_CONFIGS, type ModelKey } from "@/lib/demo-settings";
import {
  healthCheck,
  healthCheckKey,
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
  getAIComponents,
  getAIComponentsKey,
  getPIIMatrix,
  getPIIMatrixKey,
  getColumnMetadata,
  getColumnMetadataKey,
} from "@/lib/api";

export const Route = createFileRoute("/")({
  component: () => <Index />,
});

// ---------------------------------------------------------------------------
// Sourced metrics — every figure is defensible
// ---------------------------------------------------------------------------

const ENEL_CASE_STUDY_URL = "https://www.bestpractice.ai/ai-case-study-best-practice/enel_improved_the_average_energy_recovered_per_non-technical_loss_inspection_by_70%25_in_italy_and_more_than_300%25_in_spain_using_machine_learning";

const METRICS: readonly { value: string; label: string; source: React.ReactNode }[] = [
  {
    value: "£323M/yr",
    label: "Energy theft exposure",
    source:
      "RECCo (Retail Energy Code Company — the industry body that administers the Retail Energy Code for GB) commissioned Capgemini to produce the Theft Estimation Methodology (Jan 2023). Estimated: up to 1,069 GWh gas + 2,837 GWh electricity stolen/year = up to £1.4bn at Ofgem Default Tariff Cap prices. British Gas share: 23.1% domestic market share × £1.4bn = £323M. Includes both detected and unrecovered theft — detection ≠ recovery.",
  },
  {
    value: "£163M",
    label: "Divisional profit",
    source: "British Gas Home Energy divisional operating profit FY2025 (down 39% YoY) — British Gas Preliminary Results, Feb 2026.",
  },
  {
    value: "£6.2M/wk",
    label: "Cost of inaction",
    source: "Derived: £323M annual exposure ÷ 52 weeks = £6.2M per week of unrecovered theft.",
  },
  {
    value: "£97M",
    label: "ML-recoverable",
    source: (
      <>
        30% ML-assisted recovery rate × £323M exposure = £97M — equivalent to 59% of British Gas divisional profit. Conservative benchmark:{" "}
        <a href={ENEL_CASE_STUDY_URL} target="_blank" rel="noopener noreferrer" className="underline font-bold text-white hover:text-white/80">
          Enel, Europe's largest utility, achieved a 70% improvement in energy recovered per inspection across 20M+ smart meters in Italy
        </a>.
      </>
    ),
  },
];

const GROUP_METRICS = [
  {
    value: "£814M",
    label: "Group adj. operating profit",
    source: "British Gas Group adjusted operating profit FY2025 (down from £1.55bn in FY2024) — British Gas Preliminary Results, Feb 2026. Includes upstream energy, business solutions, British Gas, and international divisions.",
  },
  {
    value: "40%",
    label: "of Group profit in exposure",
    source: "£323M British Gas theft exposure ÷ £814M Group adj. operating profit = 40%. This is scale context, not a direct P&L line: theft losses are partially socialised via bad-debt provisions and network charging, and recovery rates are typically ~40%. The figure shows the magnitude of the problem relative to Group earnings, not a pound-for-pound profit drag.",
  },
  {
    value: "70%",
    label: "ML recovery uplift at scale",
    source: "Enel's deployment of ML-based detection across 20 million smart meters in Italy — using 500+ features from seven source systems — delivered a 70% improvement in energy recovered per inspection (Enel/C3.ai), demonstrating that the approach scales.",
  },
  {
    value: "12%",
    label: "Group profit recoverable",
    source: "£97M ML-recoverable (30% of £323M British Gas exposure) ÷ £814M Group adj. operating profit = 12%. Recovering theft losses from one division alone would materially move Group-level earnings.",
  },
] as const;


// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

function usePrefetchAll() {
  const qc = useQueryClient();
  useEffect(() => {
    qc.prefetchQuery({ queryKey: healthCheckKey(), queryFn: healthCheck });

    qc.prefetchQuery({ queryKey: getDashboardKPIsKey(), queryFn: getDashboardKPIs });
    qc.prefetchQuery({ queryKey: getDashboardRecoveryOpportunityKey(), queryFn: getDashboardRecoveryOpportunity });
    qc.prefetchQuery({ queryKey: getModelPerformanceKey(), queryFn: getModelPerformance });
    qc.prefetchQuery({ queryKey: getInvestigationKPIsKey(), queryFn: getInvestigationKPIs });
    qc.prefetchQuery({ queryKey: getDailyBriefingKey(), queryFn: getDailyBriefing });
    qc.prefetchQuery({ queryKey: listFlaggedAccountsKey(), queryFn: () => listFlaggedAccounts() });

    qc.prefetchQuery({ queryKey: getAIComponentsKey(), queryFn: getAIComponents });
    qc.prefetchQuery({ queryKey: getPIIMatrixKey(), queryFn: getPIIMatrix });
    qc.prefetchQuery({ queryKey: getColumnMetadataKey(), queryFn: getColumnMetadata });
    // Audit/finops are governance-tab only — prefetching here cached empty rows when SQL was broken.
  }, [qc]);
}

function Index() {
  usePrefetchAll();
  const { competeEnabled, setCompeteEnabled, modelKey, setModelKey, modelConfig } = useDemoSettings();
  const [agentsOpen, setAgentsOpen] = useState(false);
  const [archOpen, setArchOpen] = useState(false);

  useEffect(() => {
    if (window.location.hash === "#architecture") {
      setArchOpen(true);
      requestAnimationFrame(() => {
        document.getElementById("architecture")?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
  }, []);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="relative min-h-screen w-screen overflow-x-hidden bg-background text-foreground">
        {/* Nav bar */}
        <nav className="flex items-center justify-between px-8 py-4">
          <div className="flex items-center gap-3">
            <img src="/british-gas-logo.svg" alt="British Gas" className="h-14 w-auto" />
            <div className="flex flex-col leading-tight">
              <span className="font-bold text-lg tracking-tight text-foreground">
                Revenue Protection
              </span>
              <span className="text-xs text-muted-foreground/70">
                Energy Theft Detection
              </span>
            </div>
          </div>
          <span className="text-sm text-muted-foreground">
            March 2026 — British Gas
          </span>
        </nav>

        {/* Hero */}
        <main className="flex flex-col items-center px-8 pt-6 pb-4">
          <div className="max-w-4xl space-y-6 text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#FF8A3D]/40 bg-[#FF8A3D]/10 px-4 py-1.5 text-xs font-medium text-[#FF8A3D]">
              Databricks x British Gas
            </span>

            <div className="space-y-3">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight leading-tight text-[#FF8A3D]">
                <span className="text-[#FF8A3D]">£1.4 billion</span> is stolen from
                UK energy suppliers every year.
              </h1>
              <p className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-muted-foreground">
                40% goes undetected.
              </p>
              <p className="text-sm text-muted-foreground/40 font-medium tracking-wide">
                detection ≠ recovery
              </p>
            </div>

          </div>
        </main>

        {/* Exposure — immediately after "detection ≠ recovery" */}
        <section className="px-8 pt-0 pb-4">
          <div className="max-w-4xl mx-auto space-y-4">
            <h2 className="text-center text-lg font-semibold text-muted-foreground uppercase tracking-widest">
              The Exposure — British Gas
            </h2>
            <div className="grid grid-cols-4 gap-4">
              {METRICS.map((m) => (
                <div
                  key={m.label}
                  className="relative rounded-xl border bg-card p-5 text-center group hover:border-accent/40 transition-colors"
                >
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="absolute top-3 right-3 text-muted-foreground/30 group-hover:text-muted-foreground/70 transition-opacity">
                        <Info className="h-3.5 w-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[280px] text-xs">
                      {m.source}
                    </TooltipContent>
                  </Tooltip>
                  <p className="text-3xl md:text-4xl font-bold text-[#FF8A3D]">
                    {m.value}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">{m.label}</p>
                </div>
              ))}
            </div>

            {/* Group-wide scale */}
            <div className="pt-1 space-y-2">
              <p className="text-center text-xs font-semibold text-muted-foreground uppercase tracking-widest">
                British Gas Group Impact
              </p>
              <div className="grid grid-cols-4 gap-3">
                {GROUP_METRICS.map((m) => (
                  <div
                    key={m.label}
                    className="relative rounded-lg border border-dashed bg-muted/30 px-4 py-3 text-center group hover:border-accent/40 transition-colors"
                  >
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button className="absolute top-2 right-2 text-muted-foreground/30 group-hover:text-muted-foreground/70 transition-opacity">
                          <Info className="h-3 w-3" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="max-w-[280px] text-xs">
                        {m.source}
                      </TooltipContent>
                    </Tooltip>
                    <p className="text-xl font-bold text-[#FF9F5A]">{m.value}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{m.label}</p>
                  </div>
                ))}
              </div>
              <p className="text-center text-[11px] text-muted-foreground/50 italic">
                British Gas residential is 23.1% of GB domestic energy supply — all figures sourced from public filings and RECCo
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-0">
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-muted-foreground/20 bg-muted/40 px-4 py-1.5 text-xs text-muted-foreground cursor-default">
                    ~£29–48/yr added to every honest household bill
                    <Info className="h-3 w-3 text-muted-foreground/40" />
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[320px] text-xs">
                      RECCo (the Retail Energy Code Company) administers the Retail Energy Code for Great Britain and commissioned Capgemini to estimate UK energy theft levels. Their Jan 2023 report estimated up to £1.4bn/yr stolen. Theft losses are socialised across all bill-paying customers via supplier bad-debt provisions and network charging — adding ~£29–48 to each household's annual bill.
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-muted-foreground/20 bg-muted/40 px-4 py-1.5 text-xs text-muted-foreground cursor-default">
                    ~1 death every 10 days from tampered meters
                    <Info className="h-3 w-3 text-muted-foreground/40" />
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[320px] text-xs">
                  Ofgem / RECCo Energy Theft data. Meter tampering creates gas leak and electrocution risks — disproportionately affecting vulnerable households. RECCo works with Crimestoppers via the Stay Energy Safe campaign (0800 023 2777) to enable anonymous reporting.
                </TooltipContent>
              </Tooltip>
            </div>

            {/* How might we — below the pills */}
            <div className="space-y-3 pt-2">
              <p className="text-xl md:text-2xl font-medium max-w-3xl mx-auto leading-relaxed text-foreground text-center">
                How might British Gas turn{" "}
                <span className="text-[#FF8A3D] font-bold">£323M</span> of loss exposure into
                recovered revenue, faster, with Data Intelligence?
              </p>
            </div>
          </div>
        </section>

        {/* Architecture Envelope */}
        <section id="architecture" className="px-2 sm:px-4 pb-10 scroll-mt-24">
          <div className="max-w-[96rem] mx-auto">
            <div className="rounded-xl border bg-card overflow-hidden">
              <button
                onClick={() => setArchOpen((v) => !v)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <LayoutDashboard className="h-5 w-5 text-accent" />
                  <div>
                    <p className="text-sm font-semibold">Show me the Architecture</p>
                    <p className="text-xs text-muted-foreground">
                      How we replicate value-driving use cases on your Databricks Data Intelligence Platform
                    </p>
                  </div>
                </div>
                <ChevronDown
                  className={`h-5 w-5 text-muted-foreground transition-transform duration-200 ${
                    archOpen ? "rotate-180" : ""
                  }`}
                />
              </button>
              {archOpen && (
                <div className="px-2 pb-6 pt-2 animate-in fade-in-0 slide-in-from-top-2 duration-200 overflow-x-auto">
                  <ArchitectureDiagram />
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Meet the team */}
        <section className="px-8 py-10">
          <div className="max-w-4xl mx-auto space-y-8">
            <h2 className="text-center text-lg font-semibold text-muted-foreground uppercase tracking-widest">
              Meet the Energy Theft Protection Team
            </h2>
            <p className="text-center text-sm text-muted-foreground/60 -mt-4">Team Vanguard</p>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Susie */}
              <div className="rounded-xl border bg-card p-6 flex flex-col">
                <div className="flex items-center gap-4">
                  <div className="h-20 w-20 rounded-full bg-gradient-to-br from-accent to-accent/40 flex items-center justify-center text-4xl shrink-0">
                    👩‍💼
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Meet Susie</h3>
                    <p className="text-sm text-muted-foreground">
                      Head of Fraud & Intelligence
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mt-4">
                  {[
                    "Reduce theft exposure",
                    "Increase recovery rate",
                    "Satisfy Ofgem compliance",
                    "Protect divisional profit",
                  ].map((g) => (
                    <span key={g} className="flex items-start gap-1.5 min-h-[1.75rem]">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent shrink-0 mt-[0.4rem]" />
                      {g}
                    </span>
                  ))}
                </div>

                <div className="rounded-lg bg-muted/50 border p-3 text-sm italic text-muted-foreground mt-4 flex-1">
                  &ldquo;I need to tell the CFO exactly how much revenue
                  we&rsquo;re losing and recovering — without waiting for a
                  report.&rdquo;
                </div>

                <Button
                  variant="outline"
                  className="w-full border-accent/40 text-accent hover:bg-accent/10 gap-2 mt-4"
                  asChild
                >
                  <Link to="/dashboard">
                    Open Susie&rsquo;s Dashboard
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>

              {/* Robbie */}
              <div className="rounded-xl border bg-card p-6 flex flex-col">
                <div className="flex items-center gap-4">
                  <div className="h-20 w-20 rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center text-4xl shrink-0">
                    🕵️
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Meet Robbie</h3>
                    <p className="text-sm text-muted-foreground">
                      Senior Revenue Protection Analyst
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mt-4">
                  {[
                    "Triage HIGH flags fast",
                    "Reduce false positives",
                    "Generate dispatch docs",
                    "Close 25+ cases/week",
                  ].map((g) => (
                    <span key={g} className="flex items-start gap-1.5 min-h-[1.75rem]">
                      <span className="h-1.5 w-1.5 rounded-full bg-orange-500 shrink-0 mt-[0.4rem]" />
                      {g}
                    </span>
                  ))}
                </div>

                <div className="rounded-lg bg-muted/50 border p-3 text-sm italic text-muted-foreground mt-4 flex-1">
                  &ldquo;Every day I delay investigating a flagged account is
                  another day of stolen revenue.&rdquo;
                </div>

                <Button
                  variant="outline"
                  className="w-full border-orange-400 text-orange-500 hover:bg-orange-50 gap-2 mt-4"
                  asChild
                >
                  <Link to="/investigation">
                    Open Robbie&rsquo;s Workbench
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* AI Agents — collapsible section */}
        <section className="px-8 py-10">
          <div className="max-w-4xl mx-auto space-y-8">
            <button
              onClick={() => setAgentsOpen((o) => !o)}
              className="w-full group cursor-pointer"
            >
              <div className="rounded-xl border border-violet-500/30 bg-violet-500/[0.04] px-6 py-5 flex items-center justify-between transition-colors hover:bg-violet-500/[0.08]">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0">
                    <Bot className="h-5 w-5 text-violet-500" />
                  </div>
                  <div className="text-left">
                    <h2 className="text-lg font-semibold text-foreground">
                      Enhance the Team with AI Agents
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      Autonomous workflows that orchestrate, summarise, and deliver — governed end-to-end in Unity Catalog
                    </p>
                  </div>
                </div>
                <ChevronDown className={`h-5 w-5 text-muted-foreground transition-transform duration-200 ${agentsOpen ? "rotate-180" : ""}`} />
              </div>
            </button>

            {agentsOpen && (<div className="space-y-8 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="text-center">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-500/40 bg-violet-500/10 px-4 py-1.5 text-xs font-medium text-violet-600 dark:text-violet-400">
                <Bot className="h-3.5 w-3.5" />
                Databricks Agent Bricks
              </span>
              <p className="text-sm text-muted-foreground/60 max-w-2xl mx-auto mt-2">
                Susie and Robbie have dashboards and LLM-assisted tools. Agents take the next step —
                autonomous workflows that orchestrate, summarise, and deliver, governed end-to-end in Unity Catalog.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Agent Atlas — Susie's agent */}
              <div className="rounded-xl border border-violet-500/30 bg-card p-6 flex flex-col relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-violet-500/[0.06] to-transparent rounded-bl-full" />
                <div className="flex items-center gap-4">
                  <div className="h-20 w-20 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-4xl shrink-0 shadow-lg shadow-violet-500/20">
                    <Bot className="h-10 w-10 text-white" />
                  </div>
                  <div>
                    <Link to="/board-report" className="text-xl font-bold hover:text-violet-500 transition-colors underline decoration-violet-500/30 underline-offset-2 hover:decoration-violet-500">Agent Atlas</Link>
                    <p className="text-sm text-muted-foreground">
                      Monthly Board Report Generator
                    </p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                        Built for Susie
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-600 dark:text-violet-400">
                        Supervisor Agent
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground mt-4 leading-relaxed">
                  Susie spends <strong className="text-foreground">2&ndash;3 days every month</strong> assembling
                  the Revenue Protection board pack for the CFO. Atlas does it in minutes &mdash; pulling KPIs from
                  UC Metric Views, analysing regional trends, and generating an executive narrative.
                </p>

                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mt-4">
                  {[
                    { icon: BarChart3, text: "Queries all board KPIs via Genie" },
                    { icon: Sparkles, text: "Analyses MoM trends & anomalies" },
                    { icon: FileText, text: "Generates CFO-ready narrative" },
                    { icon: ClipboardList, text: "Assembles board pack (PDF)" },
                  ].map((item) => (
                    <span key={item.text} className="flex items-start gap-1.5 min-h-[1.75rem]">
                      <item.icon className="h-3.5 w-3.5 text-violet-500 shrink-0 mt-[0.2rem]" />
                      <span className="text-muted-foreground">{item.text}</span>
                    </span>
                  ))}
                </div>

                {/* Agent architecture mini-diagram */}
                <div className="rounded-lg border border-violet-500/20 bg-violet-500/[0.03] p-3 mt-4 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400">
                    Multi-Agent Architecture
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { label: "KPI Collector", sub: "Genie + Metric Views" },
                      { label: "Narrative Writer", sub: "Bedrock via Gateway" },
                      { label: "Market Intelligence", sub: "Gemini via Gateway" },
                    ].map((a) => (
                      <div key={a.label} className="rounded border bg-card px-2 py-1.5 text-center">
                        <p className="text-[10px] font-semibold">{a.label}</p>
                        <p className="text-[8px] text-muted-foreground">{a.sub}</p>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-center gap-1.5 text-[9px] text-muted-foreground">
                    <Shield className="h-2.5 w-2.5 text-accent" />
                    UC governed &middot; AI Gateway audited &middot; MLflow traced
                  </div>
                </div>

                <div className="rounded-lg bg-muted/50 border p-3 text-sm italic text-muted-foreground mt-4 flex-1">
                  &ldquo;I used to spend the first week of every month building
                  the board pack. Now I review what Atlas drafted over coffee and
                  send it before lunch.&rdquo;
                </div>

                <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex items-center gap-1 cursor-default">
                        <Zap className="h-3 w-3 text-violet-500" />
                        <strong className="text-foreground">2&ndash;3 days &rarr; 15 min</strong>
                        monthly report assembly
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[280px] text-xs">
                      Atlas orchestrates KPI collection, trend analysis, and narrative generation
                      as a Databricks Agent Bricks Supervisor Agent &mdash; scheduled monthly via Databricks Jobs.
                      Every figure sourced from UC Metric Views, every LLM call audited through AI Gateway.
                    </TooltipContent>
                  </Tooltip>
                </div>

                <Link
                  to="/board-report"
                  className="mt-4 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-violet-500/20 hover:from-violet-700 hover:to-indigo-700 transition-all"
                >
                  <Bot className="h-4 w-4" />
                  Try Agent Atlas
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>

              {/* Agent Sentinel — Robbie's agent */}
              <div className="rounded-xl border border-emerald-500/30 bg-card p-6 flex flex-col relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-emerald-500/[0.06] to-transparent rounded-bl-full" />
                <div className="flex items-center gap-4">
                  <div className="h-20 w-20 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-4xl shrink-0 shadow-lg shadow-emerald-500/20">
                    <Eye className="h-10 w-10 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Agent Sentinel</h3>
                    <p className="text-sm text-muted-foreground">
                      Investigation Triage & Dispatch Supervisor
                    </p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="inline-flex items-center gap-1 rounded-full bg-orange-500/10 px-2 py-0.5 text-[10px] font-medium text-orange-600">
                        Built for Robbie
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                        Supervisor Agent
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground mt-4 leading-relaxed">
                  Robbie targets <strong className="text-foreground">25&ndash;30 cases per week</strong>, but
                  each takes 30&ndash;40 minutes of manual triage. Sentinel orchestrates the entire batch &mdash;
                  triage, cluster, summarise, dispatch &mdash; so Robbie reviews and approves instead of assembles.
                </p>

                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mt-4">
                  {[
                    { icon: Search, text: "Ranks overnight HIGH flags" },
                    { icon: MapPin, text: "Clusters by postcode sector" },
                    { icon: RouteIcon, text: "Optimises field engineer routes" },
                    { icon: AlertTriangle, text: "Flags organised crime patterns" },
                  ].map((item) => (
                    <span key={item.text} className="flex items-start gap-1.5 min-h-[1.75rem]">
                      <item.icon className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-[0.2rem]" />
                      <span className="text-muted-foreground">{item.text}</span>
                    </span>
                  ))}
                </div>

                {/* Agent architecture mini-diagram */}
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/[0.03] p-3 mt-4 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">
                    Multi-Agent Architecture
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { label: "Triage Agent", sub: "SQL + anomaly_scores" },
                      { label: "Cluster Agent", sub: "H3 geospatial" },
                      { label: "Dispatch Agent", sub: "Bedrock via Gateway" },
                    ].map((a) => (
                      <div key={a.label} className="rounded border bg-card px-2 py-1.5 text-center">
                        <p className="text-[10px] font-semibold">{a.label}</p>
                        <p className="text-[8px] text-muted-foreground">{a.sub}</p>
                      </div>
                    ))}
                  </div>
                  <div className="rounded border bg-card px-2 py-1 text-center">
                    <p className="text-[10px] font-semibold text-red-600">ETU Alert Monitor</p>
                    <p className="text-[8px] text-muted-foreground">3+ HIGH accounts within 0.5 mi &rarr; auto-referral</p>
                  </div>
                  <div className="flex items-center justify-center gap-1.5 text-[9px] text-muted-foreground">
                    <Shield className="h-2.5 w-2.5 text-accent" />
                    UC governed &middot; AI Gateway audited &middot; MLflow traced
                  </div>
                </div>

                <div className="rounded-lg bg-muted/50 border p-3 text-sm italic text-muted-foreground mt-4 flex-1">
                  &ldquo;Sentinel had my morning queue triaged, clustered, and
                  dispatch-ready before I&rsquo;d finished my first coffee. I just
                  review, approve, and the field team is rolling.&rdquo;
                </div>

                <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex items-center gap-1 cursor-default">
                        <Zap className="h-3 w-3 text-emerald-500" />
                        <strong className="text-foreground">4 hours &rarr; 20 min</strong>
                        daily triage + 30&ndash;40% truck-roll saving
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[280px] text-xs">
                      Sentinel orchestrates triage, geospatial clustering (H3 indexing), and batch dispatch
                      as a Databricks Agent Bricks Supervisor Agent &mdash; triggered daily via Databricks Jobs.
                      Geographic clustering alone reduces field engineer travel cost by an estimated 30&ndash;40%.
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
            </div>

            {/* Why Agent Bricks — compact strip */}
            <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.02] p-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-center text-violet-600 dark:text-violet-400">
                Why Databricks Agent Bricks?
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { icon: Shield, label: "UC Governance", desc: "Same PII tags, audit trail, and permissions as the data" },
                  { icon: Brain, label: "AI Gateway", desc: "PII blocking, guardrails, rate limits — every LLM call logged" },
                  { icon: Sparkles, label: "Genie as a Tool", desc: "Agents query Metric Views via NL — no hallucinated KPIs" },
                  { icon: Zap, label: "Serverless Jobs", desc: "Schedule monthly or daily, scale to zero between runs" },
                ].map((item) => (
                  <div key={item.label} className="flex items-start gap-2.5 text-sm">
                    <div className="h-8 w-8 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0">
                      <item.icon className="h-4 w-4 text-violet-500" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-foreground">{item.label}</p>
                      <p className="text-[10px] text-muted-foreground leading-snug">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-center text-muted-foreground/50 italic">
                One platform. No stitching Azure AI Foundry + Logic Apps + Power Automate + Purview.
              </p>
            </div>
            </div>)}
          </div>
        </section>

        {/* Quick links */}
        <section className="px-8 py-8 pb-8">
          <div className="max-w-4xl mx-auto">
            <div className={`grid ${competeEnabled ? "grid-cols-2" : "grid-cols-1 max-w-md mx-auto"} gap-3`}>
              <Link
                to="/governance"
                className="group flex items-center gap-3 p-4 rounded-lg border bg-card hover:border-accent/40 transition-colors"
              >
                <Search className="h-5 w-5 text-muted-foreground group-hover:text-accent transition-colors" />
                <div>
                  <p className="text-sm font-medium">AI Governance</p>
                  <p className="text-xs text-muted-foreground">PII, audit trail, Ofgem compliance</p>
                </div>
                <ArrowRight className="h-4 w-4 ml-auto opacity-0 group-hover:opacity-70 transition-opacity" />
              </Link>
              {competeEnabled && (
                <Link
                  to="/why-databricks"
                  className="group flex items-center gap-3 p-4 rounded-lg border bg-card hover:border-accent/40 transition-colors"
                >
                  <LayoutDashboard className="h-5 w-5 text-muted-foreground group-hover:text-accent transition-colors" />
                  <div>
                    <p className="text-sm font-medium">Why Databricks</p>
                    <p className="text-xs text-muted-foreground">Platform advisory context</p>
                  </div>
                  <ArrowRight className="h-4 w-4 ml-auto opacity-0 group-hover:opacity-70 transition-opacity" />
                </Link>
              )}
            </div>
          </div>
        </section>

        {/* Demo Settings */}
        <section className="px-8 pb-10">
          <div className="max-w-4xl mx-auto">
            <div className="rounded-xl border border-dashed border-muted-foreground/20 bg-muted/20 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50 mb-3 text-center">
                Demo Configuration
              </p>
              <div className="flex flex-wrap items-center justify-center gap-6">
                {/* Compete toggle */}
                <label className="flex items-center gap-2.5 cursor-pointer group">
                  <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                    Compete Insights
                  </span>
                  <button
                    role="switch"
                    aria-checked={competeEnabled}
                    onClick={() => setCompeteEnabled(!competeEnabled)}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                      competeEnabled ? "bg-red-500" : "bg-muted-foreground/30"
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                        competeEnabled ? "translate-x-4" : "translate-x-0"
                      }`}
                    />
                  </button>
                </label>

                <div className="h-6 w-px bg-muted-foreground/20" />

                {/* Model selector */}
                <div className="flex items-center gap-2.5">
                  <span className="text-xs text-muted-foreground">
                    Primary Model
                  </span>
                  <select
                    value={modelKey}
                    onChange={(e) => setModelKey(e.target.value as ModelKey)}
                    className="rounded-md border bg-background px-2.5 py-1 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                  >
                    {Object.values(MODEL_CONFIGS).map((m) => (
                      <option key={m.key} value={m.key}>
                        {m.label} — {m.model}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <p className="text-[10px] text-muted-foreground/40 text-center mt-2">
                {competeEnabled ? "Fabric compete messaging visible on all pages" : "Compete messaging hidden"} · Primary LLM: {modelConfig.provider} ({modelConfig.model})
              </p>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="text-center text-xs text-muted-foreground/50 pb-6">
          Databricks &times; British Gas Revenue Protection
        </footer>
      </div>
    </TooltipProvider>
  );
}
