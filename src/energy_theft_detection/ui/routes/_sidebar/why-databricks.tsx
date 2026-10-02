import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp } from "lucide-react";

export const Route = createFileRoute("/_sidebar/why-databricks")({
  component: WhyDatabricksPage,
});

const SECTIONS = [
  {
    title: "Speed to Investigation — Why Platform Fragmentation Costs Cases",
    problem:
      "Robbie's team investigates 25–30 accounts per analyst per week. Each investigation takes ~40 minutes of manual data gathering, cross-referencing, and report writing. At £2,400–4,000 recovered per confirmed case, investigator throughput directly determines revenue recovery. Any friction in the toolchain reduces the number of cases that reach the field.",
    requirement:
      "A single environment where the investigator can view flagged accounts, query anomaly data, read AI-generated case summaries, and dispatch field engineers — all within one identity model and one security boundary.",
    solution:
      "This application is a single Databricks App. Robbie's Investigation Workbench, Susie's Executive Dashboard, the Genie conversational interface, and the Bedrock LLM case summaries all run within one deployment, one identity model, and one governance perimeter. There is no integration layer to build or maintain.",
    risk:
      "Building equivalent functionality typically requires assembling a web application framework, a separate BI embedding layer, a separate AI service, and a separate analytics endpoint — each with its own authentication, billing, and security model. The integration overhead delays time-to-value, and each seam is a potential point of failure during a live investigation.",
    depth: [
      "In a typical Azure architecture, this would require Azure App Service (web app), Power BI Embedded (dashboards), Azure AI Foundry (LLM), and Fabric SQL endpoints (data queries) — four services, four security models",
      "Microsoft's own documentation positions AI Foundry as something Fabric 'integrates with', not a native component",
      "Each service has its own admin console, permissions model, and billing line",
    ],
  },
  {
    title:
      "Executive Decision Speed — Why Governed NL Queries Matter",
    problem:
      "Susie presents to the UKI Gas Home Energy CFO quarterly on theft exposure and recovery. When the CFO asks 'Are we on track to hit the £97m recovery target?', Susie needs the answer in 30 seconds, not two days. If the answer is wrong — if the KPI formula has drifted — the financial narrative to the board is unreliable.",
    requirement:
      "A natural language interface that queries live operational data directly, with KPI definitions governed centrally so the formula cannot diverge between reports.",
    solution:
      "Susie's Genie Space queries Delta tables directly. The Theft Detection Precision Rate is defined in a UC Metric View — a governed formula that cannot be overridden by the query engine. This is anti-hallucination through governance: the platform guarantees consistent answers regardless of who asks.",
    risk:
      "Traditional NL-over-data approaches typically require a pre-built semantic model. When the underlying schema changes, the semantic model breaks silently. The dashboard still loads, but the answers are wrong, and no one is alerted. At the scale of UKI Gas's financial reporting, a silently wrong KPI creates audit risk.",
    depth: [
      "Power BI Copilot requires a pre-built DAX semantic model — schema changes break it silently with no automated alert",
      "No in-dashboard conversational capability in Fabric — users must context-switch to a separate Copilot interface",
      "Embedding NL analytics into custom applications via REST API remains in preview",
    ],
  },
  {
    title:
      "Regulatory Audit Trail — Why AI Governance Is Not Optional",
    problem:
      "Under Ofgem licence conditions and the new Energy Theft Unit (ETU, REC R0233, June 2025), UKI Gas must evidence how it detects and investigates theft. This includes demonstrating that AI-assisted decisions are auditable, that PII is handled per the Data Access and Privacy Framework, and that there is a clear chain of evidence from data ingestion through model scoring to investigation outcome.",
    requirement:
      "A single audit log covering every AI component: ML scoring runs, LLM calls (with token counts, latency, and guardrail outcomes), and NL query interactions. Column-level lineage from raw data through model input to investigation output.",
    solution:
      "The AI Governance page provides a unified audit trail across all AI components. The PII Access Matrix maps each model and LLM prompt to the personal data fields it accesses, with the regulatory basis documented per access pattern. The UC lineage DAG traces column-level data flow with PII badges.",
    risk:
      "When AI governance is spread across multiple services — a model registry in one portal, an LLM audit log in another, data lineage in a third — assembling a coherent audit trail requires manual stitching. Each seam is a gap that a regulator or internal auditor can challenge.",
    depth: [
      "In typical alternative architectures, ML governance sits in one service, LLM governance in another, and data governance in a third — each with separate audit logs that must be correlated manually",
      "Item-level lineage (knowing which table was used) is insufficient — column-level lineage (which PII fields the model consumed) is required for Ofgem/ELEXON compliance",
      "Without automated data classification, PII tagging must be maintained manually across every access point",
    ],
  },
  {
    title:
      "Model Lifecycle — Why ML Must Live Next to the Data",
    problem:
      "The Isolation Forest and LSTM models that detect meter anomalies must be retrained as theft patterns evolve. Organised theft rings adapt their methods; seasonal consumption shifts change the baseline. If models, training data, and serving infrastructure live in separate services, retraining cycles slow down. At ~£97m recoverable annually, even a 5% degradation in model precision means ~£4.9m in missed detections per year.",
    requirement:
      "The ML models, their training data, scoring outputs, and serving endpoints must be governed under the same catalog. Model performance metrics must be monitorable without leaving the platform.",
    solution:
      "Both models are registered in MLflow Model Registry within Unity Catalog. The same catalog governs training tables, feature engineering, anomaly scores, and investigation cases that provide labels for retraining. The model performance log tracks precision and recall by model version.",
    risk:
      "When the ML lifecycle is split across a data platform and a separate ML service, retraining requires data extraction across service boundaries. Model monitoring requires a third tool. The feedback loop between investigation outcomes and model retraining becomes a multi-sprint integration project.",
    depth: [
      "In Fabric, ML models must be trained and served through Azure ML — a separate service with its own portal, authentication, and cost centre",
      "No GPU compute available within Fabric's Spark environment — deep learning workloads require leaving the platform entirely",
      "No native feature store, model monitoring, or drift detection within the analytics platform",
    ],
  },
  {
    title:
      "Cost Governance — Why Consumption Pricing Protects the Business Case",
    problem:
      "UKI Gas processes ~360 million smart meter events per day. The detection pipeline runs daily batch scoring, the executive dashboard is queried intermittently, and the investigation workbench sees concentrated usage during business hours. Demand is inherently spiky. A platform that charges for reserved capacity regardless of utilisation erodes the ROI of the detection programme itself.",
    requirement:
      "Every compute layer — data querying, ML scoring, LLM inference, NL queries — must scale independently and bill only for actual usage.",
    solution:
      "Every component in this application runs on serverless compute. The SQL Warehouse auto-scales for queries. Genie runs on independent compute. Model Serving scales per-token. ML scoring jobs scale to the data volume and terminate. There is no idle cost.",
    risk:
      "Capacity-based pricing models require upfront commitment. If sized for peak load, you pay for idle resources. If sized conservatively, workloads compete during peak — a batch scoring job can throttle the executive dashboard.",
    depth: [
      "Fabric's capacity model shares a single compute pool across all workloads: dashboards, pipelines, AI, and Copilot",
      "When capacity is exhausted, Fabric throttles and then freezes the entire capacity — all workloads halt",
      "Pause-and-restart is the documented workaround, but it disrupts active queries and immediately bills accumulated overage",
    ],
  },
  {
    title: "Architecture Summary",
    problem:
      "The question is not which platform has more features. The question is: how quickly can UKI Gas get a governed, auditable theft detection programme into the hands of its investigators — and what is the cost of delay?",
    requirement: "",
    solution: "",
    risk: "",
    depth: [],
    isSummary: true,
  },
] as const;

function WhyDatabricksPage() {
  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Why Databricks</h1>
          <p className="text-muted-foreground">
            Advisory platform context — framed around the UKI Gas energy
            theft detection use case
          </p>
        </div>
        <Badge variant="outline" className="text-accent border-accent/50">
          Advisory — Not a Feature Comparison
        </Badge>
      </div>

      <Card className="border-accent/30 bg-accent/5">
        <CardContent className="pt-6">
          <p className="text-sm leading-relaxed">
            UKI Gas's estimated theft exposure (~£323m) exceeds its entire
            Home Energy divisional operating profit (£163m) by nearly 2×. Every
            week of delay in deploying an effective detection platform costs
            approximately £6.2m in unrecovered revenue. The platform choice is
            not a technology preference. It is a financial and regulatory
            decision with material consequences.
          </p>
        </CardContent>
      </Card>

      {SECTIONS.map((section, i) =>
        "isSummary" in section && section.isSummary ? (
          <ArchitectureSummary key={i} />
        ) : (
          <AdvisorySection key={i} index={i + 1} section={section} />
        ),
      )}
    </div>
  );
}

function AdvisorySection({
  index,
  section,
}: {
  index: number;
  section: (typeof SECTIONS)[number];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {index}. {section.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
            The Problem
          </p>
          <p className="text-sm leading-relaxed">{section.problem}</p>
        </div>

        {section.requirement && (
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
              What the Architecture Requires
            </p>
            <p className="text-sm leading-relaxed">{section.requirement}</p>
          </div>
        )}

        {section.solution && (
          <div className="rounded-lg border-l-4 border-accent bg-accent/5 p-3">
            <p className="text-xs font-semibold uppercase text-accent mb-1">
              How This Demo Solves It
            </p>
            <p className="text-sm leading-relaxed">{section.solution}</p>
          </div>
        )}

        {section.risk && (
          <div className="rounded-lg border-l-4 border-bg-orange bg-bg-orange/5 p-3">
            <p className="text-xs font-semibold uppercase text-bg-orange mb-1">
              The Risk with Alternative Approaches
            </p>
            <p className="text-sm leading-relaxed">{section.risk}</p>
          </div>
        )}

        {section.depth.length > 0 && (
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <ChevronUp className="h-3 w-3 mr-1" />
              ) : (
                <ChevronDown className="h-3 w-3 mr-1" />
              )}
              Technical Depth
            </Button>
            {expanded && (
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground list-disc ml-4">
                {section.depth.map((point, j) => (
                  <li key={j}>{point}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ArchitectureSummary() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">6. Architecture Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-lg border-2 border-accent p-4 space-y-3">
            <h3 className="font-semibold text-accent">
              Unified Approach (This Demo)
            </h3>
            <ul className="text-sm space-y-1">
              <li>✓ One Databricks App (FastAPI + React)</li>
              <li>✓ One SQL Warehouse (serverless)</li>
              <li>✓ One Unity Catalog (data, models, LLMs, Genie, lineage, PII)</li>
              <li>✓ One AI Gateway (Bedrock LLM, audit, guardrails)</li>
              <li>✓ One Genie Space (executive NL queries)</li>
              <li>✓ One MLflow Registry (model lifecycle)</li>
            </ul>
          </div>

          <div className="rounded-lg border-2 border-bg-orange p-4 space-y-3">
            <h3 className="font-semibold text-bg-orange">
              Fragmented Alternative
            </h3>
            <ul className="text-sm space-y-1 text-muted-foreground">
              <li>→ Azure App Service (web application)</li>
              <li>→ Power BI Embedded (dashboard components)</li>
              <li>→ Azure AI Foundry (LLM calls)</li>
              <li>→ Azure ML (model training and serving)</li>
              <li>→ Fabric SQL Endpoint (data queries)</li>
              <li>→ Microsoft Purview (governance and audit)</li>
              <li>→ Entra ID (per-service identity config)</li>
              <li className="font-medium text-bg-orange">
                = 7 services, 4+ admin portals, 5 permission models
              </li>
            </ul>
          </div>
        </div>

        <p className="mt-6 text-sm text-center text-muted-foreground italic">
          The question is not which platform has more features. The question is:
          how quickly can UKI Gas get a governed, auditable theft detection
          programme into the hands of its investigators — and what is the cost
          of delay?
        </p>
        <p className="mt-4 text-xs text-center text-muted-foreground">
          Platform choices are recorded as ADRs in docs/architecture-decisions.md.
          The four-phase plan is docs/ROADMAP.md (Phase 1 delivered; Atlas and
          Sentinel next).
        </p>
      </CardContent>
    </Card>
  );
}
