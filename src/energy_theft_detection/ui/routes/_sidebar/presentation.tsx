import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import SlideDeck from "@/components/slide-deck";
import {
  ArrowDown,
  BarChart3,
  Brain,
  Cloud,
  Database,
  FileSearch,
  Layers,
  Lock,
  MessageSquare,
  Monitor,
  Shield,
  Sparkles,
  Target,
  Zap,
  ArrowRight,
  Info,
  TrendingDown,
  PoundSterling,
  AlertTriangle,
  Timer,
  Globe,
} from "lucide-react";

export const Route = createFileRoute("/_sidebar/presentation")({
  component: PresentationPage,
});

// ---------------------------------------------------------------------------
// Sourced metric helper
// ---------------------------------------------------------------------------
function SourcedMetric({
  value,
  label,
  source,
  accent = false,
}: {
  value: string;
  label: string;
  source: string;
  accent?: boolean;
}) {
  return (
    <div className="relative rounded-xl border bg-card p-5 text-center group hover:border-accent/40 transition-colors">
      <Tooltip>
        <TooltipTrigger asChild>
          <button className="absolute top-2 right-2 opacity-30 group-hover:opacity-70 transition-opacity">
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-[280px] text-xs">
          {source}
        </TooltipContent>
      </Tooltip>
      <p className={`text-3xl font-bold ${accent ? "text-accent" : "text-destructive"}`}>
        {value}
      </p>
      <p className="text-sm text-muted-foreground mt-1">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. Title Slide
// ---------------------------------------------------------------------------
function TitleSlide() {
  return (
    <section className="flex flex-col items-center justify-center min-h-[500px] text-center space-y-6">
      <Badge variant="outline" className="text-accent border-accent/50">
        Databricks x British Gas
      </Badge>
      <h1 className="text-3xl md:text-5xl font-bold tracking-tight leading-tight max-w-3xl">
        <span className="text-accent">£1.4 billion</span> is stolen from
        UK energy suppliers every year.{" "}
        <span className="text-muted-foreground">40% goes undetected.</span>
      </h1>
      <p className="text-xl font-medium max-w-2xl">
        How might British Gas turn{" "}
        <span className="text-accent">£323M</span> of loss exposure into
        recovered revenue, faster, with Data & AI?
      </p>
      <p className="text-base text-muted-foreground max-w-2xl">
        ML predictions, talk to your data with Genie, and governed LLM
        summaries — one platform, no data movement, AI governance at the
        heart.
      </p>
      <p className="text-sm font-medium text-accent/80 tracking-wide italic">
        Energise a fairer future, faster with energy theft detection on Databricks
      </p>
      <Separator className="max-w-xs" />
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>British Gas / Centrica</span>
        <span>·</span>
        <span>Databricks Field Engineering</span>
        <span>·</span>
        <span>March 2026</span>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 2. The Financial Challenge
// ---------------------------------------------------------------------------
function ChallengeSlide() {
  return (
    <TooltipProvider delayDuration={200}>
      <section className="space-y-8">
        <h2 className="text-3xl font-bold">The Financial Challenge</h2>
        <p className="text-muted-foreground max-w-2xl">
          British Gas&rsquo;s energy theft exposure doesn&rsquo;t just erode
          margin — it exceeds the entire Home Energy divisional profit.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SourcedMetric
            value="£323M/yr"
            label="BG energy theft exposure"
            source="RECCo (Retail Energy Code Company) commissioned Capgemini to estimate UK energy theft (Jan 2023): up to £1.4bn/yr across GB. BG share: 23.1% domestic market (Cornwall Insights / Ofgem, Jan 2025) × £1.4bn = £323M."
          />
          <SourcedMetric
            value="£163M"
            label="Divisional profit"
            source="British Gas Home Energy divisional operating profit — Centrica Preliminary Results, Feb 2026."
            accent
          />
          <SourcedMetric
            value="£6.2M/wk"
            label="Cost of every week without ML"
            source="Derived: £323M annual exposure / 52 weeks."
          />
          <SourcedMetric
            value="£97M"
            label="ML-recoverable (30% benchmark)"
            source="Industry benchmark: 30% ML-assisted recovery rate applied to £323M exposure."
            accent
          />
        </div>

        <div className="grid md:grid-cols-2 gap-3 pt-2">
          <Card className="border-destructive/30">
            <CardContent className="pt-4 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-destructive/10 shrink-0">
                <TrendingDown className="h-4 w-4 text-destructive" />
              </div>
              <div>
                <p className="text-sm font-medium">198% of divisional profit at risk</p>
                <p className="text-xs text-muted-foreground">
                  Theft exposure (£323M) is nearly 2x the Home Energy operating
                  profit (£163M). This is an existential P&L problem.
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="border-destructive/30">
            <CardContent className="pt-4 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-destructive/10 shrink-0">
                <AlertTriangle className="h-4 w-4 text-destructive" />
              </div>
              <div>
                <p className="text-sm font-medium">Human cost</p>
                <p className="text-xs text-muted-foreground">
                  ~£50/yr added to every honest household bill [RECCo, Feb 2026].
                  ~1 death every 10 days from tampered meters [Ofgem ETU R0233, June 2025].
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-muted/30">
          <CardContent className="pt-4 flex items-start gap-3">
            <div className="p-2 rounded-lg bg-accent/10 shrink-0">
              <Timer className="h-4 w-4 text-accent" />
            </div>
            <div>
              <p className="text-sm font-medium">Regulatory pressure</p>
              <p className="text-xs text-muted-foreground">
                Ofgem DAPF mandates audit trails for PII used in ML models.
                ELEXON BSC P453 requires theft detection programmes.
                ~40% industry detection rate vs target — Ofgem is watching.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// 3. Meet Susie
// ---------------------------------------------------------------------------
function MeetSusieSlide() {
  return (
    <section className="space-y-8">
      <div className="flex items-center gap-4">
        <div className="h-16 w-16 rounded-full bg-gradient-to-br from-accent to-bg-cyan flex items-center justify-center text-3xl shrink-0">
          👩‍💼
        </div>
        <div>
          <h2 className="text-3xl font-bold">Meet Susie</h2>
          <p className="text-muted-foreground">
            Head of Revenue Protection & Financial Crime, British Gas Home Energy
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Susie&rsquo;s Goals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {[
                "Reduce theft exposure",
                "Increase recovery rate",
                "Satisfy Ofgem compliance",
                "Protect divisional profit",
              ].map((g) => (
                <span key={g} className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent shrink-0" />
                  {g}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Susie&rsquo;s Databricks Tools</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p><strong className="text-foreground">Executive Dashboard</strong> — KPI tiles, risk heatmap, trend charts</p>
            <p><strong className="text-foreground">Talk to your data with Genie</strong> — natural language queries over governed Metric Views</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-muted/30 border-accent/20">
        <CardContent className="pt-4">
          <p className="text-sm italic text-muted-foreground">
            &ldquo;I need to tell the CFO exactly how much revenue we&rsquo;re
            losing and recovering — without waiting for a report.&rdquo;
          </p>
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button className="gap-2" asChild>
          <Link to="/dashboard">
            Open Susie&rsquo;s Dashboard <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 4. Meet Robbie
// ---------------------------------------------------------------------------
function MeetRobbieSlide() {
  return (
    <section className="space-y-8">
      <div className="flex items-center gap-4">
        <div className="h-16 w-16 rounded-full bg-gradient-to-br from-bg-orange to-bg-red flex items-center justify-center text-3xl shrink-0">
          🕵️
        </div>
        <div>
          <h2 className="text-3xl font-bold">Meet Robbie</h2>
          <p className="text-muted-foreground">
            Senior Revenue Protection Analyst — Theft Detection
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Robbie&rsquo;s Goals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {[
                "Investigate HIGH flags faster",
                "Reduce false positives below 40%",
                "Generate field dispatch docs",
                "Close 25+ cases per week",
              ].map((g) => (
                <span key={g} className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-bg-orange shrink-0" />
                  {g}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Robbie&rsquo;s Databricks Tools</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p><strong className="text-foreground">Investigation Workbench</strong> — flagged accounts, signal breakdown, 90-day charts</p>
            <p><strong className="text-foreground">LLM Case Summary</strong> — Bedrock via AI Gateway generates investigation packs</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-muted/30 border-bg-orange/20">
        <CardContent className="pt-4">
          <p className="text-sm italic text-muted-foreground">
            &ldquo;Every day I delay investigating a flagged account is
            another day of stolen revenue.&rdquo;
          </p>
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button variant="outline" className="gap-2 border-bg-orange/40 text-bg-orange hover:bg-bg-orange/10" asChild>
          <Link to="/investigation">
            Open Robbie&rsquo;s Workbench <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 5. Architecture
// ---------------------------------------------------------------------------
function ArchitectureSlide() {
  return (
    <TooltipProvider delayDuration={200}>
    <section className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold">One Platform. End-to-End.</h2>
        <p className="text-muted-foreground mt-1">
          From raw smart meter reads to investigation — no data movement, no
          metadata silos, one governance plane. <span className="text-accent font-medium">Hover any box for detail.</span>
        </p>
      </div>

      <div className="rounded-2xl border-2 bg-muted/30 p-5 space-y-3">
        <p className="text-xs font-bold uppercase tracking-widest text-accent text-center">Databricks Data Intelligence Platform</p>

        {/* Horizontal flow */}
        <div className="grid grid-cols-[1.2fr_auto_1.2fr_auto_1.2fr_auto_0.4fr] items-start gap-0">

          {/* Data Lakehouse */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#CD7F32]/40 bg-[#CD7F32]/[0.06] px-3 py-2.5 text-center cursor-help flex-1">
                  <Database className="h-4 w-4 text-[#CD7F32] mx-auto mb-0.5" />
                  <p className="text-xs font-bold text-[#CD7F32]">Bronze</p>
                  <p className="text-xs font-bold">2.88M</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[240px] text-xs space-y-1">
                <p className="font-semibold">Raw ingestion — Auto Loader</p>
                <p>2.88M half-hourly reads · 2K accounts × 90d × 2 fuels</p>
                <p>4K meters · 11 UK regions · 3 tamper signatures</p>
              </TooltipContent></Tooltip>
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#A0A0A0]/40 bg-[#A0A0A0]/[0.06] px-3 py-2.5 text-center cursor-help flex-1">
                  <Database className="h-4 w-4 text-[#808080] mx-auto mb-0.5" />
                  <p className="text-xs font-bold text-[#808080]">Silver</p>
                  <p className="text-xs font-bold">ML Features</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[240px] text-xs space-y-1">
                <p className="font-semibold">Cleansed reads + ML features</p>
                <p>Smart meters filtered · 7 features per account</p>
              </TooltipContent></Tooltip>
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#D4A017]/40 bg-[#D4A017]/[0.06] px-3 py-2.5 text-center cursor-help flex-1">
                  <Database className="h-4 w-4 text-[#B8860B] mx-auto mb-0.5" />
                  <p className="text-xs font-bold text-[#B8860B]">Gold</p>
                  <p className="text-xs font-bold">Biz Agg.</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[240px] text-xs space-y-1">
                <p className="font-semibold">Business aggregates for dashboards</p>
                <p>daily_consumption · model_performance_log</p>
              </TooltipContent></Tooltip>
            </div>
            <div className="rounded border bg-card px-2 py-1.5 text-center">
              <p className="text-[10px] font-semibold">Lakeflow</p>
              <p className="text-[9px] text-muted-foreground">Spark Declarative Pipelines</p>
            </div>
          </div>

          <div className="flex items-center pt-6 px-1"><ArrowRight className="h-4 w-4 text-muted-foreground/30" /></div>

          {/* ML Models */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#0194E2]/30 bg-[#0194E2]/[0.04] px-3 py-2.5 text-center cursor-help flex-1">
                  <Brain className="h-4 w-4 text-[#0194E2] mx-auto mb-0.5" />
                  <p className="text-xs font-bold">Anomaly</p>
                  <p className="text-[9px] text-muted-foreground">0–100% risk</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                <p className="font-semibold">Isolation Forest — Anomaly Score</p>
                <p><strong>Output:</strong> 0–100% anomaly score — probability of abnormal usage across 7 dimensions.</p>
                <p><strong>1. Comms gap rate</strong> — 15-30% tampered vs 0.5% normal</p>
                <p><strong>2. Consumption drop %</strong> — 55-95% step-down in theft</p>
                <p className="text-muted-foreground">+ std dev, morning/evening ratio, mean, min, max</p>
                <p className="italic text-muted-foreground">Unsupervised · MLflow @champion · sklearn</p>
              </TooltipContent></Tooltip>
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#0194E2]/30 bg-[#0194E2]/[0.04] px-3 py-2.5 text-center cursor-help flex-1">
                  <Brain className="h-4 w-4 text-[#0194E2] mx-auto mb-0.5" />
                  <p className="text-xs font-bold">Temporal</p>
                  <p className="text-[9px] text-muted-foreground">deviation</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                <p className="font-semibold">LSTM Autoencoder — Deviation Score</p>
                <p><strong>Output:</strong> Deviation score — learns 90 days of normal usage, flags how far current behaviour deviates.</p>
                <p><strong>1. Sudden step-down</strong> — 55-95% drop overnight</p>
                <p><strong>2. Gradual decline</strong> — slow fade over 14-28 days</p>
                <p className="text-muted-foreground">Also detects intermittent zeroes and comms gap correlation</p>
                <p className="italic text-muted-foreground">Catches trends snapshots miss · MLflow @champion · PyTorch</p>
              </TooltipContent></Tooltip>
            </div>
            <Tooltip><TooltipTrigger asChild>
              <div className="rounded border bg-card px-2 py-1.5 text-center cursor-help">
                <p className="text-[10px] font-semibold">Customer ML Models on MLflow</p>
                <p className="text-[9px] text-muted-foreground">Registry · Scoring · Composite Risk</p>
              </div>
            </TooltipTrigger><TooltipContent side="bottom" className="max-w-[280px] text-xs space-y-1">
              <p className="font-semibold">Composite Risk Score</p>
              <p>35% Anomaly + 30% Temporal + 20% Cohort + 10% Comms + 5% Drop</p>
              <p>HIGH &ge; 0.62 · MEDIUM &ge; 0.40</p>
            </TooltipContent></Tooltip>
          </div>

          <div className="flex items-center pt-6 px-1"><ArrowRight className="h-4 w-4 text-muted-foreground/30" /></div>

          {/* DB SQL + Genie (side-by-side) + LLM */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#7B2FF7]/40 bg-[#7B2FF7]/[0.06] px-3 py-2.5 text-center cursor-help flex-1">
                  <Database className="h-4 w-4 text-[#7B2FF7] mx-auto mb-0.5" />
                  <p className="text-[10px] font-bold text-[#7B2FF7]">DB SQL</p>
                  <p className="text-[8px] text-muted-foreground">Enterprise DW</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[260px] text-xs space-y-1">
                <p className="font-semibold">Databricks SQL — Enterprise Data Warehouse</p>
                <p>Serverless SQL Warehouse serving Gold tables & Metric Views. Photon-accelerated.</p>
              </TooltipContent></Tooltip>
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#10B981]/40 bg-[#10B981]/[0.06] px-3 py-2.5 text-center cursor-help flex-1">
                  <Sparkles className="h-4 w-4 text-[#10B981] mx-auto mb-0.5" />
                  <p className="text-[10px] font-bold text-[#10B981]">Genie</p>
                  <p className="text-[8px] text-muted-foreground">NL → SQL</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[260px] text-xs space-y-1">
                <p className="font-semibold">Databricks Genie Space</p>
                <p>Queries DB SQL via UC Metric Views — governed answers, not hallucination</p>
              </TooltipContent></Tooltip>
            </div>
            <div className="flex items-center gap-2 px-1">
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#FF9900]/30 bg-[#FF9900]/[0.04] px-3 py-2.5 text-center cursor-help flex-1">
                  <Cloud className="h-4 w-4 text-[#FF9900] mx-auto mb-0.5" />
                  <p className="text-[10px] font-bold">Bedrock</p>
                  <p className="text-[8px] text-muted-foreground">Claude 3.5</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[280px] text-xs space-y-1">
                <p className="font-semibold">Amazon Bedrock via AI Gateway</p>
                <p>Daily Briefing · Case Summary · Field Dispatch</p>
                <p>PII blocked · safety guardrails · rate-limited · inference tables</p>
              </TooltipContent></Tooltip>
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-[#4285F4]/30 bg-[#4285F4]/[0.04] px-3 py-2.5 text-center cursor-help flex-1">
                  <Globe className="h-4 w-4 text-[#4285F4] mx-auto mb-0.5" />
                  <p className="text-[10px] font-bold text-[#4285F4]">Gemini</p>
                  <p className="text-[8px] text-muted-foreground">2.0 Flash</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[280px] text-xs space-y-1">
                <p className="font-semibold">Google Gemini via AI Gateway</p>
                <p>Market &amp; Regulatory Intelligence</p>
                <p>Same governance — guardrails · rate-limited · inference tables</p>
              </TooltipContent></Tooltip>
            </div>
            <div className="rounded border bg-card px-2 py-1.5 text-center">
              <p className="text-[10px] font-semibold">DB SQL · Genie · Model Serving</p>
              <p className="text-[9px] text-muted-foreground">AI Gateway · Multi-cloud LLMs · Inference Tables</p>
            </div>
          </div>

          <div className="flex items-center pt-6 px-1"><ArrowRight className="h-4 w-4 text-muted-foreground/30" /></div>

          {/* App — aligned with model boxes */}
          <div className="space-y-2">
            <div className="px-1">
              <Tooltip><TooltipTrigger asChild>
                <div className="rounded-lg border border-primary/30 bg-primary/[0.04] px-3 py-2.5 text-center cursor-help">
                  <Monitor className="h-4 w-4 text-primary mx-auto mb-0.5" />
                  <p className="text-xs font-bold">Databricks</p>
                  <p className="text-xs font-bold">App</p>
                  <p className="text-[9px] text-muted-foreground">3 views</p>
                </div>
              </TooltipTrigger><TooltipContent side="bottom" className="max-w-[260px] text-xs space-y-1">
                <p className="font-semibold">Databricks App — FastAPI + React</p>
                <p>Dashboard · Investigation · Governance</p>
                <p>OBO auth — acts as logged-in user</p>
              </TooltipContent></Tooltip>
            </div>
            <div className="rounded border bg-card px-1 py-1.5 text-center">
              <p className="text-[9px] font-semibold">Application Layer</p>
              <p className="text-[8px] text-muted-foreground">Interact with your data & insights</p>
            </div>
          </div>
        </div>

        {/* Foundation bars */}
        <div className="space-y-2 pt-1">
          <div className="rounded-lg border border-bg-lime/30 bg-bg-lime/[0.04] px-3 py-2 text-center">
            <p className="text-[10px] font-bold"><Zap className="h-3.5 w-3.5 text-bg-lime inline mr-1" />Serverless Compute — Pay for What You Consume</p>
            <p className="text-[9px] text-muted-foreground">SQL Warehouse · Model Serving · Apps — scale to zero</p>
          </div>
          <div className="rounded-xl border border-accent/30 bg-accent/5 p-3 space-y-2">
            <div className="flex flex-col items-center text-center gap-0.5">
              <div className="flex items-center gap-1.5">
                <Shield className="h-4 w-4 text-accent" />
                <p className="text-sm font-bold text-accent">Unity Catalog</p>
              </div>
              <p className="text-[9px] text-muted-foreground">One governance model for data, ML models, LLMs, and Genie — no data movement</p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border bg-card px-2 py-2 space-y-1 text-center">
                <div className="flex items-center justify-center gap-1">
                  <Lock className="h-2.5 w-2.5 text-accent" />
                  <p className="text-[9px] font-semibold text-accent uppercase tracking-wide">Data Governance</p>
                </div>
                <p className="text-[8px] text-muted-foreground">Automated classification, access control, and lineage — Ofgem & UK GDPR aligned.</p>
                <div className="flex flex-wrap gap-1 justify-center">
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">PII Tags</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Row Filters</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Column Masking</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Lineage</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Audit</span>
                </div>
              </div>
              <div className="rounded-lg border bg-card px-2 py-2 space-y-1 text-center">
                <div className="flex items-center justify-center gap-1">
                  <BarChart3 className="h-2.5 w-2.5 text-accent" />
                  <p className="text-[9px] font-semibold text-accent uppercase tracking-wide">Business Semantics</p>
                </div>
                <p className="text-[8px] text-muted-foreground">Governed KPI definitions shared across dashboard, Genie, and all consumers.</p>
                <div className="flex flex-wrap gap-1 justify-center">
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Metric Views</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Glossary</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Column Descriptions</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Genie Context</span>
                </div>
              </div>
              <div className="rounded-lg border bg-card px-2 py-2 space-y-1 text-center">
                <div className="flex items-center justify-center gap-1">
                  <Brain className="h-2.5 w-2.5 text-accent" />
                  <p className="text-[9px] font-semibold text-accent uppercase tracking-wide">AI Governance</p>
                </div>
                <p className="text-[8px] text-muted-foreground">Govern custom ML, foundation, and external models with full auditability.</p>
                <div className="flex flex-wrap gap-1 justify-center">
                  <span className="text-[7px] bg-[#0194E2]/10 text-[#0194E2] rounded px-1 py-0.5">Custom ML</span>
                  <span className="text-[7px] bg-[#0194E2]/10 text-[#0194E2] rounded px-1 py-0.5">Foundation</span>
                  <span className="text-[7px] bg-[#FF9900]/10 text-[#FF9900] rounded px-1 py-0.5">External</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">AI Gateway</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Rate Limits</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Guardrails</span>
                  <span className="text-[7px] bg-accent/10 text-accent rounded px-1 py-0.5">Inference Tables</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// 6. Demo Walkthrough
// ---------------------------------------------------------------------------
function DemoWalkthroughSlide() {
  const steps = [
    { num: 1, icon: BarChart3, title: "Susie's Executive Dashboard", desc: "KPI tiles, risk heatmap, trend charts — the daily command centre for revenue protection leadership.", route: "/dashboard" },
    { num: 2, icon: MessageSquare, title: "Talk to your data with Genie", desc: "'Which regions have the most theft this quarter?' — answered from governed data, not hallucinated.", route: "/dashboard" },
    { num: 3, icon: FileSearch, title: "Robbie's Investigation Workbench", desc: "Triage flagged accounts, review signal breakdowns, open cases — minutes instead of days.", route: "/investigation" },
    { num: 4, icon: Brain, title: "Multi-cloud LLM Agents", desc: "Bedrock (AWS) + Gemini (Google) orchestrated via AI Gateway — every call audited and governed.", route: "/investigation" },
    { num: 5, icon: Lock, title: "AI Governance", desc: "PII matrix, component registry, UC lineage, Gateway audit trail — all Ofgem-ready.", route: "/governance" },
    { num: 6, icon: Target, title: "Why Databricks", desc: "Advisory platform context: speed to investigation, governance, cost, model lifecycle.", route: "/why-databricks" },
  ];
  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-bold">Live Demo Walkthrough</h2>
      <div className="grid md:grid-cols-2 gap-3">
        {steps.map((s) => (
          <Card key={s.num} className="hover:border-accent/50 transition-colors">
            <CardContent className="pt-4 flex items-start gap-3">
              <span className="flex items-center justify-center h-7 w-7 rounded-full bg-primary text-primary-foreground text-xs font-bold shrink-0">
                {s.num}
              </span>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <s.icon className="h-4 w-4 text-accent" />
                  <span className="font-medium text-sm">{s.title}</span>
                </div>
                <p className="text-xs text-muted-foreground">{s.desc}</p>
              </div>
              <Link to={s.route}>
                <Button size="sm" variant="ghost" className="text-xs gap-1">
                  Open <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 7. Governance
// ---------------------------------------------------------------------------
function GovernanceSlide() {
  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-bold">AI Governance at the Heart</h2>
      <p className="text-muted-foreground">
        Every PII field tagged. Every LLM call audited. Every model versioned.
        One governance plane — not five.
      </p>
      <div className="grid md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-accent" />
              <CardTitle className="text-sm">PII Access Matrix</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground space-y-1">
            <p>13 PII fields across 5 tables</p>
            <p>Ofgem DAPF, ELEXON BSC, UK GDPR basis</p>
            <p>4 tag types: PII, Quasi-PII, Derived, Staff</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-accent" />
              <CardTitle className="text-sm">AI Component Registry</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground space-y-1">
            <p>Isolation Forest (batch scorer)</p>
            <p>LSTM v2 (sequence anomaly)</p>
            <p>Claude 3 Sonnet (case summary)</p>
            <p>Genie Space (executive NL)</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-accent" />
              <CardTitle className="text-sm">UC Lineage + Audit</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground space-y-1">
            <p>Full data → model → output lineage</p>
            <p>PII badges on every node</p>
            <p>AI Gateway logs every LLM call</p>
            <p>Input/output tokens, latency, guardrails</p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 8. Why Databricks
// ---------------------------------------------------------------------------
function WhyDatabricksSlide() {
  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-bold">Why Databricks</h2>
      <p className="text-muted-foreground max-w-2xl">
        This isn&rsquo;t a feature comparison. It&rsquo;s about how fast British Gas
        can move from exposure to recovered revenue.
      </p>
      <div className="grid md:grid-cols-2 gap-4">
        {[
          {
            icon: Zap,
            title: "Speed to investigation",
            desc: "From anomaly signal to investigation case in minutes — not days of manual spreadsheet triage across disconnected systems.",
          },
          {
            icon: MessageSquare,
            title: "Talk to your data with Genie",
            desc: "Susie asks 'Are we on track for £97M recovery?' and gets a governed answer from live data — not a hallucinated guess.",
          },
          {
            icon: Shield,
            title: "One governance plane",
            desc: "Unity Catalog governs data, models, LLMs, and Genie in one place. Not Azure Purview + AI Foundry + Power BI + Azure ML — four auth models.",
          },
          {
            icon: PoundSterling,
            title: "Pay for what you use",
            desc: "Serverless SQL Warehouse + Databricks Apps = zero idle cost. Stop paying for capacity ceilings.",
          },
        ].map((p) => (
          <Card key={p.title}>
            <CardHeader className="flex flex-row items-center gap-3 pb-2">
              <div className="p-2 rounded-lg bg-accent/10">
                <p.icon className="h-5 w-5 text-accent" />
              </div>
              <CardTitle className="text-base">{p.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{p.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 9. Next Steps
// ---------------------------------------------------------------------------
function NextStepsSlide() {
  const steps = [
    { phase: "Phase 1", title: "PoC Scoping", desc: "Connect production smart meter feed. Validate ML accuracy on real data.", weeks: "2 weeks" },
    { phase: "Phase 2", title: "Technical Validation", desc: "Register models in MLflow. Wire Genie to live Metric Views. Enable monitoring.", weeks: "4 weeks" },
    { phase: "Phase 3", title: "Production MVP", desc: "Scale from 10K demo to 7.5M estate. Integrate field dispatch workflow.", weeks: "6 weeks" },
    { phase: "Phase 4", title: "Full Rollout", desc: "All BG regions. Robbie's operational Genie. Self-serve analytics.", weeks: "Ongoing" },
  ];
  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-bold">Next Steps</h2>
      <div className="grid md:grid-cols-4 gap-4">
        {steps.map((s) => (
          <Card key={s.phase} className="relative">
            <CardHeader className="pb-2">
              <Badge variant="outline" className="w-fit mb-1">{s.phase}</Badge>
              <CardTitle className="text-sm">{s.title}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground space-y-2">
              <p>{s.desc}</p>
              <Badge className="bg-accent/10 text-accent">{s.weeks}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
function PresentationPage() {
  const slides = [
    <TitleSlide />,
    <ChallengeSlide />,
    <MeetSusieSlide />,
    <MeetRobbieSlide />,
    <ArchitectureSlide />,
    <DemoWalkthroughSlide />,
    <GovernanceSlide />,
    <WhyDatabricksSlide />,
    <NextStepsSlide />,
  ];

  return (
    <div className="container mx-auto py-8 px-4">
      <SlideDeck
        slides={slides}
        title="British Gas Revenue Protection"
      />
    </div>
  );
}
