import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Bot,
  Sparkles,
  Loader2,
  FileText,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  Database,
  Clock,
  Shield,
  BarChart3,
  MapPin,
  Brain,
  Download,
  Zap,
  DollarSign,
  Blocks,
  GitBranch,
  Wrench,
  Search,
  MessageSquare,
  Globe,
  ExternalLink,
} from "lucide-react";
import { ModelBadge } from "@/components/model-badge";
import { GeminiBadge, GOOGLE_BLUE } from "@/components/gemini-badge";
import {
  UnderTheHood,
  HoodSection,
  HoodBullet,
  FabricCallout,
} from "@/components/under-the-hood";
import { useGenerateBoardReport } from "@/lib/api";
import type { BoardReport, AgentStep } from "@/lib/api";
import { useWorkspaceConfig, masEndpointUrl } from "@/lib/workspace-config";

export const Route = createFileRoute("/_sidebar/board-report")({
  component: BoardReportPage,
});

function BoardReportPage() {
  const [report, setReport] = useState<BoardReport | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);
  const { data: wsConfig } = useWorkspaceConfig();
  const masUrl = wsConfig ? masEndpointUrl(wsConfig) : "";

  const mutation = useGenerateBoardReport({
    mutation: {
      onSuccess: (resp) => setReport(resp.data),
    },
  });

  return (
    <TooltipProvider delayDuration={200}>
      <div className="container mx-auto py-8 space-y-6 max-w-5xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Agent Atlas</h1>
              <p className="text-sm text-muted-foreground">
                Multi-Agent Board Report Supervisor
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {masUrl && (
              <a
                href={masUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-violet-600 dark:text-violet-400 hover:underline transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                View in Databricks
              </a>
            )}
            <AgentAtlasHood />
          </div>
        </div>

        {/* What is Agent Bricks */}
        <Card className="border-violet-500/20 bg-violet-500/[0.02]">
          <CardContent className="py-5 space-y-4">
            <div className="flex items-center gap-2">
              <Blocks className="h-4 w-4 text-violet-500" />
              <p className="text-xs font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400">
                Built with Databricks Agent Bricks
              </p>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Agent Bricks are pre-built AI tiles in Databricks for building production agents declaratively.
              Choose a use case — <strong>Knowledge Assistant</strong> (RAG over documents),{" "}
              <strong>Genie Space</strong> (natural language → SQL), or{" "}
              <strong>Multi-Agent Supervisor</strong> (orchestrate multiple agents + MCP servers + Genie) —
              and Databricks provisions the endpoint, wires governance, and handles serving. No framework code, no infra management.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-lg border p-3 text-center space-y-1">
                <Search className="h-5 w-5 mx-auto text-violet-500" />
                <p className="text-[11px] font-semibold">Information Extraction</p>
                <p className="text-[10px] text-muted-foreground">Classify &amp; extract from documents</p>
              </div>
              <div className="rounded-lg border p-3 text-center space-y-1">
                <MessageSquare className="h-5 w-5 mx-auto text-violet-500" />
                <p className="text-[11px] font-semibold">Knowledge Assistant</p>
                <p className="text-[10px] text-muted-foreground">RAG over PDFs &amp; docs in Volumes</p>
              </div>
              <div className="rounded-lg border border-violet-500/30 bg-violet-500/[0.04] p-3 text-center space-y-1">
                <Bot className="h-5 w-5 mx-auto text-violet-500" />
                <p className="text-[11px] font-semibold">Multi-Agent Supervisor</p>
                <p className="text-[10px] text-muted-foreground">Agents + MCP + Genie</p>
              </div>
              <div className="rounded-lg border p-3 text-center space-y-1">
                <Brain className="h-5 w-5 mx-auto text-violet-500" />
                <p className="text-[11px] font-semibold">Custom LLM</p>
                <p className="text-[10px] text-muted-foreground">Domain-specific chat endpoint</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="text-[9px] bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full px-2 py-0.5 font-medium">UC-native ACLs</span>
              <span className="text-[9px] bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full px-2 py-0.5 font-medium">Auto-provisioned endpoints</span>
              <span className="text-[9px] bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full px-2 py-0.5 font-medium">MCP Catalog &amp; Marketplace</span>
              <span className="text-[9px] bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full px-2 py-0.5 font-medium">Copilot Studio interop</span>
              <span className="text-[9px] bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full px-2 py-0.5 font-medium">Price/quality auto-routing</span>
              <span className="text-[9px] bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full px-2 py-0.5 font-medium">MLflow traced</span>
            </div>
          </CardContent>
        </Card>

        {/* Agent Atlas Architecture — styled diagram */}
        <Card className="border-violet-500/20 bg-violet-500/[0.02]">
          <CardContent className="py-5 space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground text-center">
              Agent Atlas — Supervisor Architecture
            </p>
            {/* Supervisor box */}
            <div className="rounded-xl border-2 border-dashed border-violet-500/30 p-5 space-y-5">
              {/* Agent Bricks orchestrator header */}
              <div className="flex flex-col items-center gap-2">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
                  <Blocks className="h-5 w-5 text-white" />
                </div>
                <div className="text-center">
                  <p className="text-xs font-bold text-violet-600 dark:text-violet-400 uppercase tracking-wide">Agent Atlas — Supervisor Agent</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Orchestrated by <span className="font-semibold text-violet-600 dark:text-violet-400">Databricks Agent Bricks</span></p>
                </div>
              </div>

              {/* Sub-agents grid — 50/50 split */}
              <div className="grid grid-cols-2 gap-3 items-stretch">
                {/* KPI Collector — expanded with Genie questions */}
                <div className="rounded-lg border-2 border-emerald-500/30 bg-emerald-500/[0.04] p-4 space-y-2.5">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md shadow-emerald-500/20">
                      <Database className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <p className="text-[12px] font-bold">KPI Collector</p>
                      <p className="text-[9px] text-muted-foreground">Genie API + UC Metric Views</p>
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    {[
                      "Total HIGH risk accounts and combined estimated annual loss",
                      "Top 5 postcode sectors by HIGH risk flagged accounts",
                      "Average composite risk score and precision rate",
                      "Cases closed this month and total revenue recovered",
                    ].map((q) => (
                      <div key={q} className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
                        <Search className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-[2px]" />
                        <span>{q}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* LLM agents — stacked vertically, 35% width */}
                <div className="flex flex-col gap-3">
                  {/* Narrative Writer — Bedrock */}
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/[0.04] p-3 text-center space-y-1.5 flex-1">
                    <Brain className="h-5 w-5 mx-auto text-[#FF9900]" />
                    <p className="text-[11px] font-bold">Narrative Writer</p>
                    <p className="text-[9px] text-muted-foreground leading-snug">
                      Bedrock via AI Gateway
                    </p>
                  </div>

                  {/* Market Intelligence — Gemini */}
                  <div className="rounded-lg border p-3 text-center space-y-1.5 flex-1" style={{ borderColor: `${GOOGLE_BLUE}40`, backgroundColor: `${GOOGLE_BLUE}06` }}>
                    <Globe className="h-5 w-5 mx-auto" style={{ color: GOOGLE_BLUE }} />
                    <p className="text-[11px] font-bold">Market Intelligence</p>
                    <p className="text-[9px] text-muted-foreground leading-snug">
                      Gemini via AI Gateway
                    </p>
                  </div>
                </div>
              </div>

              {/* Arrow down */}
              <div className="flex justify-center">
                <div className="flex flex-col items-center gap-1">
                  <div className="w-px h-4 bg-violet-500/30" />
                  <ChevronDown className="h-4 w-4 text-violet-500/50" />
                </div>
              </div>

              {/* Report assembler */}
              <div className="rounded-lg border border-violet-500/30 bg-violet-500/[0.04] p-3 text-center mx-auto max-w-xs">
                <FileText className="h-5 w-5 mx-auto text-violet-500" />
                <p className="text-[11px] font-bold mt-1">Report Assembler</p>
                <p className="text-[10px] text-muted-foreground">Markdown / PDF</p>
              </div>
            </div>
            {/* Governance footer */}
            <div className="flex items-center justify-center gap-4 pt-1">
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <Shield className="h-3 w-3 text-accent" />
                Unity Catalog (governed data)
              </div>
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <Zap className="h-3 w-3 text-accent" />
                AI Gateway (audited LLM calls)
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Agent Bricks screenshot */}
        <Card className="border-violet-500/20 bg-violet-500/[0.02] overflow-hidden">
          <CardContent className="py-4 flex justify-center">
            <img
              src="/agent-bricks-overview.png"
              alt="Databricks Agent Bricks UI showing use cases — Information Extraction, Knowledge Assistant, Multi-Agent Supervisor, and Custom LLM"
              className="max-h-[320px] w-auto rounded-lg"
            />
          </CardContent>
        </Card>

        {/* Generate Button */}
        {!report && (
          <Button
            size="lg"
            className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="flex flex-col items-start">
                  <span>Agent Atlas is working...</span>
                  <span className="text-xs opacity-75 font-normal">Agent Bricks MAS routing to Genie + Gemini + Bedrock</span>
                </span>
              </span>
            ) : (
              <>
                <Bot className="h-5 w-5 mr-2" />
                Generate Board Report
              </>
            )}
          </Button>
        )}

        {mutation.isError && (
          <Card className="border-red-500/30 bg-red-500/5">
            <CardContent className="py-4 text-sm text-red-600">
              Report generation failed: {mutation.error?.message ?? "Unknown error"}
            </CardContent>
          </Card>
        )}

        {/* Report Output */}
        {report && (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Report Header Card */}
            <Card className="border-accent/30">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-violet-500" />
                    <div>
                      <CardTitle className="text-lg">{report.report_title}</CardTitle>
                      <p className="text-xs text-muted-foreground">
                        Generated {report.generated_at} · {report.genie_questions_asked} Genie queries
                        {report.bedrock_tokens_used > 0 ? ` · ${report.bedrock_tokens_used} Bedrock tokens` : ""}
                      </p>
                      {report.bedrock_tokens_used === 0 && (
                        <p className="text-[10px] text-amber-600 dark:text-amber-400 mt-0.5">
                          Data-driven report — LLM narrative unavailable, showing KPIs from Genie + SQL
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <GeminiBadge />
                    <ModelBadge />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {/* Executive Summary */}
                <div className="bg-accent/5 border-l-2 border-accent p-4 rounded-r">
                  <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-2">
                    Executive Summary
                  </p>
                  <p className="text-sm leading-relaxed">{report.executive_summary}</p>
                </div>

                {/* KPI Highlights */}
                {report.kpi_highlights.length > 0 && (
                  <div>
                    <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-3">
                      Key Performance Indicators
                    </p>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {report.kpi_highlights.map((kpi, i) => (
                        <div key={i} className="rounded-lg border bg-card p-3 space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-xs text-muted-foreground">{kpi.label}</p>
                            <TrendIcon trend={kpi.trend} />
                          </div>
                          <p className="text-lg font-bold">{kpi.value}</p>
                          {kpi.context && (
                            <p className="text-[10px] text-muted-foreground leading-snug">{kpi.context}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Revenue Protection Overview */}
                {report.revenue_protection_overview && (
                  <div>
                    <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                      <BarChart3 className="h-3 w-3" /> Revenue Protection Overview
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground">{report.revenue_protection_overview}</p>
                  </div>
                )}

                {/* Regional Analysis */}
                {report.regional_analysis && (
                  <div>
                    <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> Regional Analysis
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground">{report.regional_analysis}</p>
                  </div>
                )}

                {/* Market & Regulatory Intelligence */}
                {report.market_intelligence && (
                  <div>
                    <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                      <Globe className="h-3 w-3" style={{ color: GOOGLE_BLUE }} /> Market &amp; Regulatory Intelligence
                      <span className="ml-1 text-[9px] font-normal px-1.5 py-0.5 rounded-full" style={{ backgroundColor: `${GOOGLE_BLUE}15`, color: GOOGLE_BLUE }}>
                        via Gemini
                      </span>
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground">{report.market_intelligence}</p>
                  </div>
                )}

                {/* Model Performance */}
                {report.model_performance_summary && (
                  <div>
                    <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                      <Brain className="h-3 w-3" /> Model Performance
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground">{report.model_performance_summary}</p>
                  </div>
                )}

                {/* Recommendations */}
                {report.recommendations.length > 0 && (
                  <div>
                    <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-2">
                      Board Recommendations
                    </p>
                    <ol className="list-decimal list-inside space-y-1.5 text-sm">
                      {report.recommendations.map((rec, i) => (
                        <li key={i} className="leading-relaxed">{rec}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="gap-1 border-violet-500/30 text-violet-600">
                      <Bot className="h-3 w-3" /> Agent Atlas
                    </Badge>
                    <Badge variant="outline" className="gap-1 border-emerald-500/30 text-emerald-600">
                      <Database className="h-3 w-3" /> {report.genie_questions_asked} Genie queries
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => handlePrintReport(report)}>
                      <Download className="h-3.5 w-3.5 mr-1.5" /> Export PDF
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => { setReport(null); mutation.reset(); }}
                    >
                      Regenerate
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Agent Trace (collapsible) */}
            {report.agent_trace.length > 0 && (
              <Card className="border-violet-500/10">
                <button
                  onClick={() => setTraceOpen((o) => !o)}
                  className="w-full"
                >
                  <CardHeader className="pb-0 cursor-pointer hover:bg-muted/30 transition-colors rounded-t-xl">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-sm">Agent Orchestration Trace</CardTitle>
                        <Badge variant="secondary" className="text-[10px]">
                          {report.agent_trace.length} steps
                        </Badge>
                      </div>
                      <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${traceOpen ? "rotate-180" : ""}`} />
                    </div>
                  </CardHeader>
                </button>
                {traceOpen && (
                  <CardContent className="pt-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                    {report.agent_trace.map((step, i) => (
                      <TraceStep key={i} step={step} index={i} />
                    ))}
                  </CardContent>
                )}
              </Card>
            )}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "up") return <TrendingUp className="h-3.5 w-3.5 text-green-500" />;
  if (trend === "down") return <TrendingDown className="h-3.5 w-3.5 text-red-500" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
}

function TraceStep({ step, index }: { step: AgentStep; index: number }) {
  const isGenie = step.agent === "genie";
  const isGemini = step.agent === "gemini";
  const isSupervisor = step.agent === "supervisor";
  const agentColor = isSupervisor ? "#8B5CF6" : isGenie ? "#10B981" : isGemini ? GOOGLE_BLUE : "#FF9900";
  const agentLabel = isSupervisor ? "Supervisor" : isGenie ? "Genie" : isGemini ? "Gemini" : "Bedrock";
  const Icon = isSupervisor ? Bot : isGenie ? Database : isGemini ? Globe : Brain;

  return (
    <div className="rounded-lg border p-3 space-y-1.5"
      style={{
        borderColor: `${agentColor}33`,
        backgroundColor: `${agentColor}05`,
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center"
            style={{ backgroundColor: `${agentColor}1A` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: agentColor }} />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: agentColor }}>
            Step {index + 1} — {agentLabel}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <Clock className="h-2.5 w-2.5" />
          {(step.duration_ms / 1000).toFixed(1)}s
        </div>
      </div>
      <p className="text-xs font-medium">{step.question}</p>
      <p className="text-xs text-muted-foreground leading-relaxed">{step.answer}</p>
      {step.sql && (
        <details className="text-[10px]">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">SQL query</summary>
          <pre className="mt-1 p-2 rounded bg-muted text-[10px] overflow-x-auto font-mono">{step.sql}</pre>
        </details>
      )}
      {step.data && step.data.length > 0 && (
        <details className="text-[10px]">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Data ({step.data.length} rows)
          </summary>
          <div className="mt-1 p-2 rounded bg-muted overflow-x-auto">
            <table className="text-[10px] w-full">
              <thead>
                <tr>
                  {Object.keys(step.data[0]).map((k) => (
                    <th key={k} className="text-left px-1 py-0.5 font-semibold border-b">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {step.data.slice(0, 10).map((row, ri) => (
                  <tr key={ri}>
                    {Object.values(row).map((v, ci) => (
                      <td key={ci} className="px-1 py-0.5 border-b border-muted-foreground/10">{String(v ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}

function AgentAtlasHood() {
  return (
    <UnderTheHood title="Agent Atlas — Multi-Agent Supervisor">
      <HoodSection title="How it works" icon={Bot}>
        <HoodBullet icon={Database} bold="Multi-agent orchestration">
          The supervisor routes queries to Genie (NL→SQL over UC Metric Views), Gemini (market intelligence via Google), and Bedrock (narrative via AWS) — two LLM providers, one governance layer, all via AI Gateway.
        </HoodBullet>
        <HoodBullet icon={Shield} bold="Governed end-to-end">
          Every Genie query runs against governed UC tables. Every LLM call is logged with token usage, latency, and guardrail status in inference tables. Same PII filters, same audit trail.
        </HoodBullet>
      </HoodSection>

      <HoodSection title="Agent Bricks" icon={Blocks}>
        <HoodBullet icon={GitBranch} bold="Supervisor routing">
          The supervisor automatically routes each sub-question to the right agent (Genie for data, KA for policy docs, Bedrock for narrative), then assembles the final output. No manual LangChain DAG wiring.
        </HoodBullet>
        <HoodBullet icon={Shield} bold="UC-native governance">
          Every brick inherits Unity Catalog ACLs, lineage, and audit. Agent endpoints are registered in UC with full model versioning and rollback.
        </HoodBullet>
      </HoodSection>

      <HoodSection title="Price / Quality Auto-Optimisation" icon={DollarSign}>
        <HoodBullet icon={Zap} bold="Automatic model routing">
          Agent Bricks can cascade across model tiers — route simple queries to cheaper models (e.g. Nova Lite) and complex reasoning to premium models (e.g. Sonnet/Opus) — all behind a single endpoint. No code changes.
        </HoodBullet>
        <HoodBullet icon={DollarSign} bold="AI Gateway cost controls">
          Rate limits, per-endpoint budgets, and usage tracking via AI Gateway. Set a monthly spend cap and the gateway enforces it, with automatic fallback to lower-cost models before hitting limits.
        </HoodBullet>
        <HoodBullet icon={BarChart3} bold="MLflow quality feedback loop">
          Production traces feed into MLflow evaluation scorers. If quality drifts, the system auto-flags and can trigger re-routing to higher-quality models — optimising the cost/quality Pareto frontier continuously.
        </HoodBullet>
      </HoodSection>

      <HoodSection title="Copilot Interop via MCP" icon={Blocks}>
        <HoodBullet icon={GitBranch} bold="Copilot Studio → Databricks in &lt;10 min">
          Managed MCP servers for UC Functions, Genie, Vector Search, and DBSQL connect to Copilot Studio via OAuth. Bidirectional — Databricks agents also consume Microsoft 365 MCP servers.
        </HoodBullet>
        <HoodBullet icon={Blocks} bold="MCP Catalog & Marketplace">
          Discover, share, and govern MCP servers org-wide via UC. Third-party servers (S&amp;P Global, Moody&apos;s, FactSet) available from Databricks Marketplace.
        </HoodBullet>
      </HoodSection>

      <FabricCallout category="Governance">
        <p>
          <strong>AI Foundry Connected Agents</strong> offer similar routing — but agents don&apos;t inherit data ACLs from a unified catalog. Governance requires separate Azure RBAC, AI Services keys, and Purview configuration with no single lineage from data → agent → LLM → output.
        </p>
        <p>
          <strong>Agent Bricks differentiators:</strong> UC-native governance inherited by every brick, built-in price/quality model cascading behind one endpoint, MCP Catalog for org-wide tool discovery, and an MLflow feedback loop from production traces to model selection.
        </p>
      </FabricCallout>
    </UnderTheHood>
  );
}

function handlePrintReport(report: BoardReport) {
  const html = `<!DOCTYPE html>
<html><head>
<meta charset="utf-8" />
<title>${report.report_title}</title>
<style>
  body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 800px; margin: 40px auto; color: #1a1a2e; line-height: 1.6; }
  h1 { color: #0A84C8; font-size: 22px; border-bottom: 2px solid #0A84C8; padding-bottom: 8px; }
  h2 { color: #333; font-size: 16px; margin-top: 24px; text-transform: uppercase; letter-spacing: 0.05em; }
  .meta { color: #666; font-size: 13px; margin-bottom: 24px; }
  .summary { background: #f0f7ff; border-left: 3px solid #0A84C8; padding: 12px 16px; border-radius: 0 6px 6px 0; margin: 16px 0; }
  .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }
  .kpi { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
  .kpi-value { font-size: 20px; font-weight: bold; color: #0A84C8; }
  .kpi-label { font-size: 12px; color: #666; }
  ol { padding-left: 20px; }
  li { margin-bottom: 6px; }
  .footer { margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 12px; color: #999; font-size: 11px; }
  @media print { body { margin: 20px; } }
</style>
</head><body>
<h1>${report.report_title}</h1>
<p class="meta">Generated ${report.generated_at} by Agent Atlas · ${report.genie_questions_asked} Genie queries · Bedrock (Amazon Nova Lite) + Gemini 2.0 Flash</p>

<div class="summary"><strong>Executive Summary</strong><br/>${report.executive_summary}</div>

${report.kpi_highlights.length > 0 ? `
<h2>Key Performance Indicators</h2>
<div class="kpi-grid">
  ${report.kpi_highlights.map((k) => `<div class="kpi"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-label">${k.context}</div></div>`).join("")}
</div>` : ""}

${report.revenue_protection_overview ? `<h2>Revenue Protection Overview</h2><p>${report.revenue_protection_overview}</p>` : ""}
${report.regional_analysis ? `<h2>Regional Analysis</h2><p>${report.regional_analysis}</p>` : ""}
${report.market_intelligence ? `<h2>Market &amp; Regulatory Intelligence <span style="font-size:11px;color:#4285F4;">(via Gemini)</span></h2><p>${report.market_intelligence}</p>` : ""}
${report.model_performance_summary ? `<h2>Model Performance</h2><p>${report.model_performance_summary}</p>` : ""}

${report.recommendations.length > 0 ? `
<h2>Board Recommendations</h2>
<ol>${report.recommendations.map((r) => `<li>${r}</li>`).join("")}</ol>` : ""}

<div class="footer">
  Agent Atlas · Databricks Agent Bricks Supervisor Agent · Bedrock + Gemini via AI Gateway · Unity Catalog Governed
</div>
</body></html>`;

  const w = window.open("", "_blank");
  if (w) {
    w.document.write(html);
    w.document.close();
    setTimeout(() => w.print(), 300);
  }
}
