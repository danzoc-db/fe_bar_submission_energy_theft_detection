import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ArrowLeftRight,
  ArrowRight,
  BarChart3,
  Brain,
  Cloud,
  Database,
  HardDrive,
  Lock,
  Monitor,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import {
  UnderTheHood,
  HoodSection,
  HoodBullet,
  FabricCallout,
} from "@/components/under-the-hood";
import { useDemoSettings } from "@/lib/demo-settings";

function AppArchHood() {
  return (
    <UnderTheHood title="Databricks App & Serverless Architecture">
      <HoodSection title="What's happening">
        <p>
          This entire application — the frontend you're looking at and the
          backend serving the data — runs as a single{" "}
          <strong>Databricks App</strong>, deployed and managed via Databricks
          Asset Bundles.
        </p>
      </HoodSection>

      <HoodSection title="How it's built">
        <HoodBullet bold="One Databricks App">
          FastAPI + React, deployed via{" "}
          <code className="text-xs bg-muted px-1 py-0.5 rounded font-mono">
            databricks apps deploy
          </code>
          . No Azure App Service, no separate hosting — one command.
        </HoodBullet>
        <HoodBullet bold="Infrastructure as code">
          <code className="text-xs bg-muted px-1 py-0.5 rounded font-mono">
            databricks.yml
          </code>{" "}
          declares app, warehouse, model serving, and Genie Space. Version,
          promote, deploy across environments.
        </HoodBullet>
        <HoodBullet bold="Serverless & user-identity">
          Every component scales to zero and bills on use. OBO auth means the
          app acts as the logged-in user — not a shared service principal.
        </HoodBullet>
      </HoodSection>

      <FabricCallout category="Cost">
        <p>
          <strong>Opaque, shared-capacity pricing</strong> — ETL, BI, Copilot,
          AI, and RTI all compete for one Fabric CU pool. When it's exhausted,
          workloads throttle or freeze. Moving between CU bands costs double and
          requires careful capacity planning — overhead at the risk of downtime.
        </p>
        <p>
          Replicating this app requires <strong>5+ services</strong> (App
          Service, Power BI Embedded, AI Foundry, Fabric, Purview) — each with
          its own billing, auth, and admin portal.
        </p>
      </FabricCallout>
    </UnderTheHood>
  );
}

function PrimaryModelBox() {
  const { modelConfig } = useDemoSettings();
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`rounded-lg border ${modelConfig.borderColor} ${modelConfig.bgColor} px-3 py-2.5 text-center cursor-help transition-colors`}
          style={{ borderColor: `${modelConfig.color}33`, backgroundColor: `${modelConfig.color}0A` }}
        >
          <Cloud className="h-5 w-5 mx-auto mb-1" style={{ color: modelConfig.color }} />
          <p className="text-sm font-bold text-foreground">{modelConfig.provider}</p>
          <p className="text-[10px] text-muted-foreground">{modelConfig.model}</p>
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-[320px] text-xs space-y-1">
        <p className="font-semibold">{modelConfig.provider} via AI Gateway</p>
        <p>{modelConfig.model} accessed through Databricks Model Serving endpoint with AI Gateway guardrails.</p>
        <p><strong>Daily Briefing</strong> — morning triage for investigations team</p>
        <p><strong>Case Summary</strong> — structured narrative per flagged account</p>
        <p><strong>Field Dispatch</strong> — checklist + risk context for engineers</p>
        <p className="text-muted-foreground italic">PII blocked · safety guardrails · rate-limited · inference tables</p>
        <p className="font-semibold pt-1 border-t border-border/50">AI Gateway Security Perimeter</p>
        <p>All LLM providers are accessed via AI Gateway — every call stays within Databricks. Switch models from the hero page to compare.</p>
      </TooltipContent>
    </Tooltip>
  );
}

export function ArchitectureDiagram() {
  return (
    <div className="min-w-[900px] mx-auto">
      <div className="rounded-2xl border-2 bg-muted/30 p-4 sm:p-6 space-y-5">
        <div className="flex items-center justify-center gap-1.5">
          <p className="text-sm sm:text-base font-bold uppercase tracking-widest text-accent text-center">
            Energise a Fairer Future, Faster with Energy Theft Detection on Databricks
          </p>
          <AppArchHood />
        </div>

        {/* ── Horizontal architecture flow — two-row grid for alignment ── */}
        {/* Row 1: Main boxes */}
        <div className="grid grid-cols-[1.2fr_auto_1.2fr_auto_1.2fr_auto_0.4fr] items-stretch gap-x-0">

          {/* Column 1: Medallion */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 px-1 flex-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="rounded-lg border border-[#CD7F32]/40 bg-[#CD7F32]/[0.06] px-3 py-2.5 text-center cursor-help flex-1 hover:border-[#CD7F32]/60 transition-colors">
                    <Database className="h-5 w-5 text-[#CD7F32] mx-auto mb-1" />
                    <p className="text-sm font-bold text-[#CD7F32]">Bronze</p>
                    <p className="text-sm font-bold text-foreground">2.88M</p>
                    <p className="text-[10px] text-muted-foreground">reads</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[260px] text-xs space-y-1">
                  <p className="font-semibold">Raw ingestion via Auto Loader</p>
                  <p>2.88M half-hourly smart meter reads — 2K accounts × 90 days × 2 fuels (elec + gas)</p>
                  <p>4K meters · 2K properties · 11 UK regions</p>
                  <p>3 tamper signatures injected · 3% tampered, 2% edge cases</p>
                  <p className="text-muted-foreground italic">4 Delta tables · incremental · multi-BU ready</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="rounded-lg border border-[#A0A0A0]/40 bg-[#A0A0A0]/[0.06] px-3 py-2.5 text-center cursor-help flex-1 hover:border-[#A0A0A0]/60 transition-colors">
                    <Database className="h-5 w-5 text-[#808080] mx-auto mb-1" />
                    <p className="text-sm font-bold text-[#808080]">Silver</p>
                    <p className="text-xs font-bold text-foreground whitespace-nowrap">Model Features</p>
                    <p className="text-[10px] text-muted-foreground">Tables</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[280px] text-xs space-y-1">
                  <p className="font-semibold">Cleansed reads + ML feature engineering</p>
                  <p>Smart meters filtered · 7 ML features per account</p>
                  <p>Quality flags: actual, estimated, suspect</p>
                  <p className="text-muted-foreground italic">8 data quality expectations — consumption, timestamps, fuel types, postcodes, regions, ML feature bounds — validated inline as SDP EXPECT clauses</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="rounded-lg border border-[#D4A017]/40 bg-[#D4A017]/[0.06] px-3 py-2.5 text-center cursor-help flex-1 hover:border-[#D4A017]/60 transition-colors">
                    <Database className="h-5 w-5 text-[#B8860B] mx-auto mb-1" />
                    <p className="text-sm font-bold text-[#B8860B]">Gold</p>
                    <p className="text-sm font-bold text-foreground">Business</p>
                    <p className="text-[10px] text-muted-foreground">Aggregates</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[260px] text-xs space-y-1">
                  <p className="font-semibold">Business aggregates for dashboards & Genie</p>
                  <p><strong>daily_consumption</strong> — daily kWh rollup per account/fuel</p>
                  <p><strong>account_features</strong> — now in silver layer (ML features)</p>
                  <p><strong>model_performance_log</strong> — 24-month precision/recall/F1</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="rounded-lg border bg-card px-3 py-2 text-center cursor-help hover:border-accent/40 transition-colors mt-auto">
                  <p className="text-xs font-semibold text-foreground">Lakeflow</p>
                  <p className="text-[10px] text-muted-foreground">Spark Declarative Pipelines</p>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[320px] text-xs space-y-1.5">
                <p className="font-semibold">Lakeflow Spark Declarative Pipelines</p>
                <p>Bronze/Silver/Gold medallion with <strong>11 declarative data quality expectations</strong> baked into the pipeline SQL. Invalid reads, bad postcodes, future dates, and out-of-range ML features are flagged as warnings — visible in the Pipeline UI — without blocking data flow.</p>
                <p className="text-muted-foreground italic">Fabric Data Factory has no equivalent inline data quality expectation framework.</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Arrow */}
          <div className="flex items-center justify-center px-1.5 pt-6">
            <ArrowRight className="h-5 w-5 text-muted-foreground/30" />
          </div>

          {/* Column 2: ML Models */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 px-1 flex-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="rounded-lg border border-[#0194E2]/30 bg-[#0194E2]/[0.04] px-3 py-2.5 text-center cursor-help flex-1 hover:border-[#0194E2]/50 transition-colors">
                    <Brain className="h-5 w-5 text-[#0194E2] mx-auto mb-1" />
                    <p className="text-sm font-bold text-foreground">Anomaly</p>
                    <p className="text-sm font-bold text-foreground">Detector</p>
                    <p className="text-[10px] text-muted-foreground">0–100% risk</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[320px] text-xs space-y-1.5">
                  <p className="font-semibold">Isolation Forest — Consumption Anomaly Score</p>
                  <p><strong>Output:</strong> 0–100% anomaly score per account — the probability that a meter&rsquo;s consumption profile is inconsistent with normal usage, scored across 7 behavioural dimensions simultaneously.</p>
                  <p className="font-semibold text-[11px]">Key features (by importance):</p>
                  <p><strong>1. Comms gap rate</strong> — 15-30% for tampered meters vs 0.5% normal. Strongest single indicator of physical meter interference.</p>
                  <p><strong>2. Consumption drop %</strong> — 55-95% step-down in confirmed theft cases. Measures severity of the usage reduction.</p>
                  <p className="text-muted-foreground">+ std dev, morning/evening ratio, mean kWh, min, max</p>
                  <p className="text-muted-foreground italic">Unsupervised · no labelled data needed · MLflow @champion · sklearn</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="rounded-lg border border-[#0194E2]/30 bg-[#0194E2]/[0.04] px-3 py-2.5 text-center cursor-help flex-1 hover:border-[#0194E2]/50 transition-colors">
                    <Brain className="h-5 w-5 text-[#0194E2] mx-auto mb-1" />
                    <p className="text-sm font-bold text-foreground">Temporal</p>
                    <p className="text-sm font-bold text-foreground">Pattern</p>
                    <p className="text-[10px] text-muted-foreground">deviation score</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[320px] text-xs space-y-1.5">
                  <p className="font-semibold">LSTM Autoencoder — Temporal Deviation Score</p>
                  <p><strong>Output:</strong> Deviation score per account — the model learns 90 days of &ldquo;normal&rdquo; daily kWh usage, then measures how far current behaviour deviates from expected patterns. Higher score = greater likelihood of tampering.</p>
                  <p className="font-semibold text-[11px]">Tampering patterns detected:</p>
                  <p><strong>1. Sudden step-down</strong> — 55-95% consumption drop overnight. The most common bypass signature.</p>
                  <p><strong>2. Gradual decline</strong> — slow fade over 14-28 days. Harder to spot in snapshots, but the temporal model catches the trend.</p>
                  <p className="text-muted-foreground">Also detects intermittent zeroes and comms gap correlation</p>
                  <p className="text-muted-foreground italic">Catches what the snapshot model misses · MLflow @champion · PyTorch</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="rounded-lg border bg-card px-3 py-2 text-center cursor-help hover:border-[#0194E2]/40 transition-colors mt-auto">
                  <p className="text-xs font-semibold text-foreground">Customer ML Models on MLflow</p>
                  <p className="text-[10px] text-muted-foreground">Model Registry · Batch Scoring · Composite Risk</p>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                <p className="font-semibold">MLflow Model Registry & Lifecycle</p>
                <p>Both models registered with @champion alias. Batch scoring combines outputs into a composite risk score:</p>
                <p><strong>35%</strong> Anomaly + <strong>30%</strong> Temporal + <strong>20%</strong> Cohort + <strong>10%</strong> Comms + <strong>5%</strong> Drop</p>
                <p>HIGH &ge; 0.62 · MEDIUM &ge; 0.40 · LOW &lt; 0.40</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Bi-directional arrow: Lakehouse ↔ Serving (Lakebase sync + reads) */}
          <div className="flex items-center justify-center px-1.5 pt-6">
            <ArrowLeftRight className="h-5 w-5 text-muted-foreground/30" />
          </div>

          {/* Column 3: Lakebase + DB SQL + Genie + Model Serving */}
          <div className="flex flex-col gap-3">
            <div className="space-y-2 px-1 flex-1">
              <div className="grid grid-cols-3 gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="rounded-lg border border-[#0093F5]/40 bg-[#0093F5]/[0.06] px-2 py-2.5 text-center cursor-help hover:border-[#0093F5]/60 transition-colors">
                      <HardDrive className="h-5 w-5 text-[#0093F5] mx-auto mb-1" />
                      <p className="text-xs font-bold text-[#0093F5]">Lakebase</p>
                      <p className="text-xs font-bold text-foreground">Case OLTP</p>
                      <p className="text-[10px] text-muted-foreground">low-latency R/W</p>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                    <p className="font-semibold">Lakebase — Managed PostgreSQL</p>
                    <p>Low-latency OLTP database for case management interactions. The app reads/writes investigation cases here for instant response times.</p>
                    <p><strong>Forward ETL (Lakehouse Sync)</strong> replicates closed cases to Delta tables for executive reporting and Genie analytics.</p>
                    <p><strong>Reverse ETL</strong> syncs ML scoring outputs (risk tiers, anomaly scores) from the Lakehouse into Lakebase so the app serves fresh model results at OLTP speed.</p>
                    <p className="text-muted-foreground italic">Sub-10ms reads · transactional writes · bi-directional sync</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="rounded-lg border border-[#7B2FF7]/40 bg-[#7B2FF7]/[0.06] px-2 py-2.5 text-center cursor-help hover:border-[#7B2FF7]/60 transition-colors">
                      <Database className="h-5 w-5 text-[#7B2FF7] mx-auto mb-1" />
                      <p className="text-xs font-bold text-[#7B2FF7]">DB SQL</p>
                      <p className="text-xs font-bold text-foreground">Enterprise DW</p>
                      <p className="text-[10px] text-muted-foreground">Photon-accelerated</p>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                    <p className="font-semibold">Databricks SQL — Enterprise Data Warehouse</p>
                    <p>Serverless SQL Warehouse powering executive dashboards, Metric Views, and analytical queries. Lakehouse Sync moves closed-case data here for reporting.</p>
                    <p><strong>Metric Views materialised every 6h</strong> — theft_detection_metrics, risk_exposure_metrics</p>
                    <p className="text-muted-foreground italic">Serverless · auto-scales · zero idle cost · Photon-accelerated</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="rounded-lg border border-[#10B981]/40 bg-[#10B981]/[0.06] px-2 py-2.5 text-center cursor-help hover:border-[#10B981]/60 transition-colors">
                      <Sparkles className="h-5 w-5 text-[#10B981] mx-auto mb-1" />
                      <p className="text-xs font-bold text-[#10B981]">Genie</p>
                      <p className="text-xs font-bold text-foreground">NL → SQL</p>
                      <p className="text-[10px] text-muted-foreground">queries DB SQL</p>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                    <p className="font-semibold">Databricks Genie Space</p>
                    <p>Natural language interface that queries DB SQL via UC Metric Views. Converts user questions into governed SQL — answers grounded in live warehouse data, not hallucinated.</p>
                    <p><strong>theft_detection_metrics</strong> — recovery, precision by month/region</p>
                    <p><strong>risk_exposure_metrics</strong> — HIGH count, avg score by postcode/fuel</p>
                    <p className="text-muted-foreground italic">Embedded in-app via Genie Conversation API</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <PrimaryModelBox />
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="rounded-lg border bg-card px-3 py-2 text-center cursor-help hover:border-[#FF9900]/40 transition-colors mt-auto">
                  <p className="text-xs font-semibold text-foreground">Lakebase · DB SQL · Genie · Model Serving</p>
                  <p className="text-[10px] text-muted-foreground">AI Gateway · Guardrails · Lakehouse Sync</p>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[300px] text-xs space-y-1">
                <p className="font-semibold">Serving & Intelligence Layer</p>
                <p>Lakebase serves low-latency case interactions (OLTP). Lakehouse Sync moves closed cases to DB SQL for analytical reporting. Genie queries the Lakehouse via natural language. AI Gateway proxies LLM calls with guardrails.</p>
                <p>Every query and LLM call is auditable — stored in Unity Catalog inference tables.</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Bi-directional arrow: App ↔ DB SQL + Lakebase + Genie + Model Serving */}
          <div className="flex items-center justify-center px-1.5 pt-6">
            <ArrowLeftRight className="h-5 w-5 text-muted-foreground/30" />
          </div>

          {/* Column 4: Databricks App — stretches full height to align with serving layer */}
          <div className="flex flex-col gap-3">
            <div className="px-1 flex-1 flex items-stretch">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="rounded-lg border border-primary/30 bg-primary/[0.04] px-3 py-2.5 text-center cursor-help hover:border-primary/50 transition-colors w-full flex flex-col items-center justify-center">
                    <Monitor className="h-5 w-5 text-primary mb-1" />
                    <p className="text-sm font-bold text-foreground">Databricks</p>
                    <p className="text-sm font-bold text-foreground">App</p>
                    <p className="text-[10px] text-muted-foreground">3 views</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[280px] text-xs space-y-1">
                  <p className="font-semibold">Databricks App — FastAPI + React</p>
                  <p>OBO auth — acts as logged-in user, not a service principal.</p>
                  <p><strong>Executive Dashboard</strong> — KPIs, heatmap, trends, Genie</p>
                  <p><strong>Investigation Workbench</strong> — triage, signals, LLM dispatch</p>
                  <p><strong>AI Governance Console</strong> — PII, audit, lineage, registry</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="rounded-lg border bg-card px-1 py-2 text-center mt-auto">
              <p className="text-xs font-semibold text-foreground">Application Layer</p>
              <p className="text-[10px] text-muted-foreground leading-tight">Interact with your data & insights</p>
            </div>
          </div>
        </div>

        {/* ── Full-width foundation bars ── */}
        <div className="space-y-3 pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="rounded-lg border border-bg-lime/30 bg-bg-lime/[0.04] px-5 py-3 cursor-help hover:border-bg-lime/50 transition-colors">
                <div className="flex items-center justify-center gap-3">
                  <Zap className="h-5 w-5 text-bg-lime shrink-0" />
                  <div className="text-center">
                    <p className="text-xs font-bold text-foreground">Serverless Compute — Pay for What You Consume</p>
                    <p className="text-[10px] text-muted-foreground">SQL Warehouse · Model Serving · Databricks Apps — scale to zero, no idle cost</p>
                  </div>
                </div>
              </div>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-[300px] text-xs space-y-1">
              <p className="font-semibold">Zero infrastructure to manage</p>
              <p>Every component auto-scales: SQL Warehouse for queries, Model Serving for batch scoring, App compute for the frontend.</p>
              <p>No clusters to size, no VMs to manage. Bills only on active usage — zero idle cost between demo sessions.</p>
            </TooltipContent>
          </Tooltip>

          <div className="rounded-xl border border-accent/30 bg-accent/5 p-5 space-y-4">
            <div className="flex flex-col items-center text-center gap-1">
              <div className="flex items-center gap-2">
                <Shield className="h-6 w-6 text-accent" />
                <p className="text-base font-bold text-accent">Unity Catalog</p>
              </div>
              <p className="text-xs text-muted-foreground">One governance model for data, ML models, LLMs, and Genie — no data movement</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
                <div className="flex items-center justify-center gap-1">
                  <Lock className="h-3 w-3 text-accent" />
                  <p className="text-xs font-semibold text-accent uppercase tracking-wide">Data Governance</p>
                </div>
                <p className="text-[10px] text-muted-foreground text-center">Automated classification, access control, and lineage for every table and column — Ofgem and UK GDPR aligned.</p>
                <div className="flex flex-wrap gap-1.5 justify-center">
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">PII Tags & Classification</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Row Filters</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Column Masking</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Column-Level Lineage</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Audit Trails</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Access Control (ACLs)</span>
                </div>
              </div>
              <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
                <div className="flex items-center justify-center gap-1">
                  <BarChart3 className="h-3 w-3 text-accent" />
                  <p className="text-xs font-semibold text-accent uppercase tracking-wide">Business Semantics</p>
                </div>
                <p className="text-[10px] text-muted-foreground text-center">Governed KPI definitions shared across the dashboard, Genie, and all downstream consumers — one source of truth.</p>
                <div className="flex flex-wrap gap-1.5 justify-center">
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">UC Metric Views</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">6h Materialisation</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Column Descriptions</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Business Glossary</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Genie Context</span>
                </div>
              </div>
              <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
                <div className="flex items-center justify-center gap-1">
                  <Brain className="h-3 w-3 text-accent" />
                  <p className="text-xs font-semibold text-accent uppercase tracking-wide">AI Governance</p>
                </div>
                <p className="text-[10px] text-muted-foreground text-center">Govern every model type — custom ML, foundation, and external — with versioning, guardrails, and full auditability.</p>
                <div className="flex flex-wrap gap-1.5 justify-center">
                  <span className="text-[9px] bg-[#0194E2]/10 text-[#0194E2] rounded px-1.5 py-0.5">Custom ML Models</span>
                  <span className="text-[9px] bg-[#0194E2]/10 text-[#0194E2] rounded px-1.5 py-0.5">Foundation Models</span>
                  <span className="text-[9px] bg-[#FF9900]/10 text-[#FF9900] rounded px-1.5 py-0.5">External (Bedrock)</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">MLflow Registry</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">AI Gateway</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Rate Limits</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Safety Guardrails</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Endpoint Permissions</span>
                  <span className="text-[9px] bg-accent/10 text-accent rounded px-1.5 py-0.5">Inference Tables</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
