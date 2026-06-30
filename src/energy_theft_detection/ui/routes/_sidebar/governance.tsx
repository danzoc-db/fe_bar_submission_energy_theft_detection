import { createFileRoute } from "@tanstack/react-router";
import { Suspense, useState, useRef, useLayoutEffect, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ModelBadge } from "@/components/model-badge";
import {
  Activity,
  Coins,
  Hash,
  AlertTriangle,
  CalendarClock,
  Database as DatabaseIcon,
  ExternalLink,
  X,
  Brain,
  Sparkles,
  Cloud,
  TableIcon,
  Layers,
  GitBranch,
  Lock,
  ShieldCheck,
  LayoutDashboard,
  TrendingUp,
  Gauge,
  RefreshCw,
} from "lucide-react";
import {
  useGetPIIMatrixSuspense,
  useGetAIComponentsSuspense,
  useGetAIGatewayAuditSuspense,
  useGetAuditSummarySuspense,
  useGetFinOpsSummarySuspense,
  useGetColumnMetadataSuspense,
  useGetExternalLineage,
  getAIComponents,
  getAIComponentsKey,
  getPIIMatrix,
  getPIIMatrixKey,
  getColumnMetadata,
  getColumnMetadataKey,
  getAIGatewayAudit,
  getAIGatewayAuditKey,
  getAuditSummary,
  getAuditSummaryKey,
  getFinOpsSummary,
  getFinOpsSummaryKey,
  type AIComponentRegistryItem,
  type AIGatewayAuditEntry,
  type ColumnMetadata,
  type ExternalLineageEdge,
  type ExternalLineageNode,
  type PIIFieldAccess,
} from "@/lib/api";
import selector from "@/lib/selector";
import {
  useWorkspaceConfig,
  catalogExplorerUrl,
  modelUrl,
  genieSpaceUrl,
  type WorkspaceConfig,
} from "@/lib/workspace-config";
import {
  UnderTheHood,
  HoodSection,
  HoodBullet,
  FabricCallout,
} from "@/components/under-the-hood";

const GOV_STALE = 10 * 60 * 1000;

function GovernancePending() {
  return (
    <div className="container mx-auto py-8 space-y-6 animate-pulse">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-10 w-80 rounded-lg" />
      <Skeleton className="h-72 rounded-xl" />
    </div>
  );
}

export const Route = createFileRoute("/_sidebar/governance")({
  loader: ({ context: { queryClient } }) => {
    queryClient.ensureQueryData({ queryKey: getColumnMetadataKey(), queryFn: getColumnMetadata, staleTime: GOV_STALE });
    // Bust backend governance cache on tab entry so audit/finops recover after model switches.
    queryClient.fetchQuery({
      queryKey: getAIGatewayAuditKey(),
      queryFn: () => getAIGatewayAudit({ refresh: true }),
      staleTime: 0,
    });
    queryClient.fetchQuery({
      queryKey: getAuditSummaryKey(),
      queryFn: () => getAuditSummary({ refresh: true }),
      staleTime: 0,
    });
    queryClient.fetchQuery({
      queryKey: getFinOpsSummaryKey(),
      queryFn: () => getFinOpsSummary({ refresh: true }),
      staleTime: 0,
    });

    return Promise.all([
      queryClient.ensureQueryData({ queryKey: getAIComponentsKey(), queryFn: getAIComponents, staleTime: GOV_STALE }),
      queryClient.ensureQueryData({ queryKey: getPIIMatrixKey(), queryFn: getPIIMatrix, staleTime: GOV_STALE }),
    ]);
  },
  pendingComponent: GovernancePending,
  component: GovernancePage,
});

function GovernancePage() {
  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">AI Governance</h1>
            <UCHood />
          </div>
          <p className="text-muted-foreground">
            PII access control, model registry, and AI Gateway audit trail —
            aligned to Ofgem DAPF, ELEXON BSC, and UK GDPR
          </p>
        </div>
        <Badge variant="outline" className="text-accent border-accent/50">
          Unity Catalog Governed
        </Badge>
      </div>

      <div className="rounded-lg border border-accent/30 bg-accent/[0.04] px-5 py-4 flex items-start gap-4">
        <ShieldCheck className="h-6 w-6 text-accent shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-foreground">
            AI Gateway — Your Models, Your Security Perimeter
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Databricks AI Gateway provides a single, governed endpoint for Anthropic, Google Gemini, OpenAI, and Meta Llama models.
            Because every call routes through Databricks, your data never leaves the security perimeter — external
            providers cannot access your tables, PII, or prompts. Customers get access to the newest model
            capabilities with the same security guarantees they trust for their most sensitive data.
          </p>
        </div>
      </div>

      <Tabs defaultValue="components" className="space-y-4">
        <TabsList>
          <TabsTrigger value="components">AI Component Registry</TabsTrigger>
          <TabsTrigger value="pii">PII Access Matrix</TabsTrigger>
          <TabsTrigger value="lineage">UC Lineage</TabsTrigger>
          <TabsTrigger value="audit">AI Gateway Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="components">
          <Suspense fallback={<TableSkeleton rows={4} />}>
            <ComponentRegistry />
          </Suspense>
        </TabsContent>

        <TabsContent value="pii">
          <Suspense fallback={<TableSkeleton rows={13} />}>
            <PIIMatrix />
          </Suspense>
        </TabsContent>

        <TabsContent value="lineage">
          <Suspense fallback={<TableSkeleton rows={6} />}>
            <LineageDAG />
          </Suspense>
        </TabsContent>

        <TabsContent value="audit">
          <Suspense fallback={<TableSkeleton rows={8} />}>
            <AuditPanel />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Under the Hood — Unity Catalog
// ---------------------------------------------------------------------------

function UCHood() {
  return (
    <UnderTheHood title="Unity Catalog — One Governance Model">
      <HoodSection title="How it's built" icon={Layers}>
        <HoodBullet icon={DatabaseIcon} bold="One catalog, everything governed">
          Tables, ML models, LLMs, Genie, Metric Views — one access control model, one audit log, one lineage graph.
        </HoodBullet>
        <HoodBullet icon={GitBranch} bold="Column-level lineage + PII">
          Meter reads → features → ML scores → LLM output → cases. Every field tagged with classification & regulation (Ofgem, GDPR), enforced at query time.
        </HoodBullet>
        <HoodBullet icon={Lock} bold="Row, column & AI security">
          Region-scoped rows, masked PII columns, AI component registry — all declarative in UC. No separate admin portal.
        </HoodBullet>
      </HoodSection>

      <FabricCallout entryId="unified-governance" />
    </UnderTheHood>
  );
}

function ComponentRegistry() {
  const { data: components } = useGetAIComponentsSuspense(selector());

  return (
    <TooltipProvider delayDuration={200}>
      <Card>
        <CardHeader>
          <CardTitle>AI Component Registry</CardTitle>
          <p className="text-sm text-muted-foreground">
            ML models, LLMs, and Genie — with PII access classification and last batch run
          </p>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Component</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Last Batch Run</TableHead>
                  <TableHead className="text-right">Records</TableHead>
                  <TableHead>PII Fields Accessed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {components.map((c: AIComponentRegistryItem) => (
                  <TableRow key={c.component_name} className={c.databricks_url ? "cursor-pointer hover:bg-muted/50" : ""}>
                    <TableCell className="font-medium">
                      {c.databricks_url ? (
                        <a
                          href={c.databricks_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-foreground hover:text-accent transition-colors"
                        >
                          {c.component_name}
                          <ExternalLink className="h-3 w-3 text-muted-foreground" />
                        </a>
                      ) : (
                        c.component_name
                      )}
                    </TableCell>
                    <TableCell>
                      {c.databricks_url ? (
                        <a href={c.databricks_url} target="_blank" rel="noopener noreferrer">
                          <Badge
                            variant="outline"
                            className={`cursor-pointer hover:opacity-80 transition-opacity ${
                              c.component_type.includes("ML")
                                ? "border-accent text-accent"
                                : c.component_type.includes("LLM")
                                  ? "border-bg-orange text-bg-orange"
                                  : "border-bg-lime text-bg-lime"
                            }`}
                          >
                            {c.component_type}
                          </Badge>
                        </a>
                      ) : (
                        <Badge
                          variant="outline"
                          className={
                            c.component_type.includes("ML")
                              ? "border-accent text-accent"
                              : c.component_type.includes("LLM")
                                ? "border-bg-orange text-bg-orange"
                                : "border-bg-lime text-bg-lime"
                          }
                        >
                          {c.component_type}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {c.databricks_url ? (
                        <a
                          href={c.databricks_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-accent transition-colors"
                        >
                          {c.model_name}
                        </a>
                      ) : (
                        c.model_name
                      )}
                    </TableCell>
                    <TableCell>
                      {c.last_run ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex items-center gap-1.5 text-sm">
                              <CalendarClock className="h-3.5 w-3.5 text-accent" />
                              {c.last_run}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="text-xs">
                            Last scoring batch run timestamp from anomaly_scores
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {c.records_scored != null ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex items-center gap-1.5 text-sm font-mono">
                              <DatabaseIcon className="h-3.5 w-3.5 text-muted-foreground" />
                              {c.records_scored.toLocaleString()}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="text-xs">
                            Total records scored in anomaly_scores table
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {c.pii_fields_accessed.map((field: string) => (
                          <Badge
                            key={field}
                            variant="outline"
                            className="text-xs bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800"
                          >
                            {field}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}

function PIIMatrix() {
  const { data: fields } = useGetPIIMatrixSuspense(selector());

  const piiTagColor = (tag: string) => {
    if (tag === "PII") return "bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800";
    if (tag.includes("Quasi")) return "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950 dark:text-orange-300 dark:border-orange-800";
    if (tag.includes("derived")) return "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800";
    if (tag.includes("staff")) return "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800";
    return "bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800";
  };

  const tables = [...new Set(fields.map((f: PIIFieldAccess) => f.table_name))];

  return (
    <Card>
      <CardHeader>
        <CardTitle>PII Field Classification</CardTitle>
        <p className="text-sm text-muted-foreground">
          Field-level PII tags per Ofgem DAPF, ELEXON BSC, ICO guidance, and UK GDPR
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-red-200 border border-red-400 dark:bg-red-900 dark:border-red-700" />
            PII
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-orange-200 border border-orange-400 dark:bg-orange-900 dark:border-orange-700" />
            Quasi-PII
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-blue-200 border border-blue-400 dark:bg-blue-900 dark:border-blue-700" />
            PII (derived)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-emerald-200 border border-emerald-400 dark:bg-emerald-900 dark:border-emerald-700" />
            PII (staff)
          </span>
        </div>

        {tables.map((table: string) => (
          <div key={table} className="space-y-2">
            <h3 className="font-mono text-sm font-semibold">{table}</h3>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-48">Field</TableHead>
                    <TableHead className="w-36">PII Tag</TableHead>
                    <TableHead>Regulatory Basis</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fields
                    .filter((f: PIIFieldAccess) => f.table_name === table)
                    .map((f: PIIFieldAccess) => (
                      <TableRow key={`${f.table_name}.${f.field_name}`}>
                        <TableCell className="font-mono text-sm">
                          {f.field_name}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={piiTagColor(f.pii_tag)}
                          >
                            {f.pii_tag}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {f.regulatory_basis}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Interactive Column-Level Lineage Graph
// ---------------------------------------------------------------------------

type PiiTag = "PII" | "Quasi-PII" | "PII (derived)" | "PII (staff)" | null;
type NodeKind = "source" | "ml" | "scored" | "llm" | "outcome" | "external_bi";

// Power BI accent — used for the external_bi node border, badge, roadmap
// callout, and edge stroke when the External Lineage toggle is on.
const POWER_BI_YELLOW = "#F2C811";

interface LineageColumn {
  name: string;
  pii: PiiTag;
}

interface LineageNode {
  id: string;
  label: string;
  kind: NodeKind;
  columns: LineageColumn[];
  databricksUrl: string;
  description: string;
  icon: typeof DatabaseIcon;
  // External BI-only metadata. Present iff kind === "external_bi".
  externalUrl?: string;
  entityType?: "dashboard" | "report";
  externalBadge?: string; // e.g. "Power BI · Dashboard"
}

interface LineageEdge {
  from: string; // "nodeId.columnName"
  to: string;
  piiTraceGroup?: string; // groups edges into a PII trace path
}

type PiiLookup = Map<string, PiiTag>;

function buildPiiLookup(colMeta: ColumnMetadata[]): PiiLookup {
  const lookup: PiiLookup = new Map();
  for (const c of colMeta) {
    if (c.pii_tag) {
      lookup.set(`${c.table_name}.${c.column_name}`, c.pii_tag as PiiTag);
    }
  }
  return lookup;
}

function piiFor(lookup: PiiLookup, tableId: string, colName: string): PiiTag {
  return lookup.get(`${tableId}.${colName}`) ?? null;
}

function buildLineageNodes(ws: WorkspaceConfig, piiLookup: PiiLookup, descriptions: Map<string, string>): LineageNode[] {
  const desc = (tableId: string, fallback: string) => descriptions.get(tableId) || fallback;

  return [
    {
      id: "smart_meter_reads",
      label: "smart_meter_reads",
      kind: "source",
      icon: TableIcon,
      databricksUrl: catalogExplorerUrl(ws, "smart_meter_reads"),
      description: desc("smart_meter_reads", "Raw half-hourly smart meter consumption reads — the primary data source for all downstream ML and analytics."),
      columns: [
        { name: "account_id", pii: piiFor(piiLookup, "smart_meter_reads", "account_id") || "PII" },
        { name: "consumption_kwh", pii: piiFor(piiLookup, "smart_meter_reads", "consumption_kwh") || "PII" },
        { name: "postcode", pii: piiFor(piiLookup, "smart_meter_reads", "postcode") || "PII" },
        { name: "fuel_type", pii: piiFor(piiLookup, "smart_meter_reads", "fuel_type") },
        { name: "read_quality", pii: piiFor(piiLookup, "smart_meter_reads", "read_quality") },
      ],
    },
    {
      id: "isolation_forest",
      label: "Isolation Forest v3",
      kind: "ml",
      icon: Brain,
      databricksUrl: modelUrl(ws, "isolation_forest_theft_v3"),
      description: "Unsupervised anomaly detection model. Ingests consumption patterns and property features to produce an isolation score per account.",
      columns: [
        { name: "account_id", pii: "PII" },
        { name: "consumption_features", pii: null },
        { name: "isolation_score", pii: null },
      ],
    },
    {
      id: "lstm_model",
      label: "LSTM Consumption v2",
      kind: "ml",
      icon: Brain,
      databricksUrl: modelUrl(ws, "lstm_consumption_v2"),
      description: "Sequence-based deep learning model. Detects temporal deviations in consumption patterns that indicate meter tampering.",
      columns: [
        { name: "account_id", pii: "PII" },
        { name: "consumption_sequence", pii: null },
        { name: "deviation_score", pii: null },
      ],
    },
    {
      id: "anomaly_scores",
      label: "anomaly_scores",
      kind: "scored",
      icon: TableIcon,
      databricksUrl: catalogExplorerUrl(ws, "anomaly_scores"),
      description: desc("anomaly_scores", "Composite risk scores per account — the weighted ensemble of Isolation Forest, LSTM, and rule-based signals. Drives the flagged accounts table."),
      columns: [
        { name: "account_id", pii: piiFor(piiLookup, "anomaly_scores", "account_id") || "PII" },
        { name: "postcode_sector", pii: piiFor(piiLookup, "anomaly_scores", "postcode_sector") || "PII" },
        { name: "composite_risk_score", pii: piiFor(piiLookup, "anomaly_scores", "composite_risk_score") },
        { name: "risk_tier", pii: piiFor(piiLookup, "anomaly_scores", "risk_tier") },
      ],
    },
    {
      id: "bedrock_llm",
      label: "Bedrock LLM",
      kind: "llm",
      icon: Cloud,
      databricksUrl: `${ws.workspace_url}/ml/endpoints/energy-theft-bedrock-gateway`,
      description: "Amazon Bedrock Nova Lite via AI Gateway. Generates natural-language case summaries and field dispatch reports from account risk data.",
      columns: [
        { name: "account_id", pii: "PII" },
        { name: "risk_score_input", pii: null },
        { name: "llm_summary_output", pii: piiFor(piiLookup, "investigation_cases", "llm_summary") || "PII (derived)" },
      ],
    },
    {
      id: "investigation_cases",
      label: "investigation_cases",
      kind: "outcome",
      icon: TableIcon,
      databricksUrl: catalogExplorerUrl(ws, "investigation_cases"),
      description: desc("investigation_cases", "Final investigation records — including LLM-generated summaries, investigation outcomes, and recovered revenue. Feeds Susie's KPIs."),
      columns: [
        { name: "account_id", pii: piiFor(piiLookup, "investigation_cases", "account_id") || "PII" },
        { name: "llm_summary", pii: piiFor(piiLookup, "investigation_cases", "llm_summary") || "PII (derived)" },
        { name: "investigator_id", pii: piiFor(piiLookup, "investigation_cases", "investigator_id") || "PII (staff)" },
        { name: "outcome", pii: piiFor(piiLookup, "investigation_cases", "outcome") },
        { name: "revenue_recovered", pii: piiFor(piiLookup, "investigation_cases", "revenue_recovered_gbp") },
      ],
    },
    {
      id: "genie_space",
      label: "Genie Space",
      kind: "outcome",
      icon: Sparkles,
      databricksUrl: genieSpaceUrl(ws),
      description: "Natural language SQL interface for executive queries. Governed by UC — users only see data they have access to.",
      columns: [
        { name: "all_governed_fields", pii: null },
      ],
    },
  ];
}

const LINEAGE_EDGES: LineageEdge[] = [
  // account_id trace
  { from: "smart_meter_reads.account_id", to: "isolation_forest.account_id", piiTraceGroup: "account_id" },
  { from: "smart_meter_reads.account_id", to: "lstm_model.account_id", piiTraceGroup: "account_id" },
  { from: "isolation_forest.account_id", to: "anomaly_scores.account_id", piiTraceGroup: "account_id" },
  { from: "lstm_model.account_id", to: "anomaly_scores.account_id", piiTraceGroup: "account_id" },
  { from: "anomaly_scores.account_id", to: "bedrock_llm.account_id", piiTraceGroup: "account_id" },
  { from: "bedrock_llm.account_id", to: "investigation_cases.account_id", piiTraceGroup: "account_id" },
  // consumption trace
  { from: "smart_meter_reads.consumption_kwh", to: "isolation_forest.consumption_features", piiTraceGroup: "consumption_kwh" },
  { from: "smart_meter_reads.consumption_kwh", to: "lstm_model.consumption_sequence", piiTraceGroup: "consumption_kwh" },
  { from: "isolation_forest.isolation_score", to: "anomaly_scores.composite_risk_score", piiTraceGroup: "consumption_kwh" },
  { from: "lstm_model.deviation_score", to: "anomaly_scores.composite_risk_score", piiTraceGroup: "consumption_kwh" },
  // postcode trace
  { from: "smart_meter_reads.postcode", to: "anomaly_scores.postcode_sector", piiTraceGroup: "postcode" },
  // LLM trace
  { from: "anomaly_scores.composite_risk_score", to: "bedrock_llm.risk_score_input" },
  { from: "bedrock_llm.llm_summary_output", to: "investigation_cases.llm_summary", piiTraceGroup: "llm_summary" },
  // Genie reads from scored + cases
  { from: "anomaly_scores.composite_risk_score", to: "genie_space.all_governed_fields" },
  { from: "investigation_cases.revenue_recovered", to: "genie_space.all_governed_fields" },
];

const NODE_BORDER_COLOR: Record<NodeKind, string> = {
  source: "border-l-accent",
  ml: "border-l-[#00539F]",
  scored: "border-l-[#0072CE]",
  llm: "border-l-[#FF9900]",
  outcome: "border-l-emerald-500",
  external_bi: "border-l-[#F2C811]",
};

const NODE_HEADER_BADGE: Record<NodeKind, { label: string; cls: string }> = {
  source: { label: "Source", cls: "bg-accent/10 text-accent border-accent/30" },
  ml: { label: "ML Model", cls: "bg-[#00539F]/10 text-[#00539F] border-[#00539F]/30 dark:text-blue-300" },
  scored: { label: "Scored", cls: "bg-[#0072CE]/10 text-[#0072CE] border-[#0072CE]/30" },
  llm: { label: "LLM", cls: "bg-[#FF9900]/10 text-[#FF9900] border-[#FF9900]/30" },
  outcome: { label: "Output", cls: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" },
  external_bi: { label: "Power BI", cls: "bg-[#F2C811]/10 text-[#A38000] border-[#F2C811]/40 dark:text-[#F2C811]" },
};

function piiColor(pii: PiiTag) {
  if (!pii) return "";
  if (pii === "PII") return "bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800";
  if (pii.includes("Quasi")) return "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950 dark:text-orange-300 dark:border-orange-800";
  if (pii.includes("derived")) return "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800";
  if (pii.includes("staff")) return "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800";
  return "";
}

function piiEdgeStroke(pii: PiiTag) {
  if (!pii) return "#94a3b8"; // slate-400
  if (pii === "PII") return "#dc2626";
  if (pii.includes("derived")) return "#2563eb";
  if (pii.includes("staff")) return "#059669";
  return "#dc2626";
}

// ---------------------------------------------------------------------------
// External Lineage merge — Power BI reports as a 5th DAG column
// ---------------------------------------------------------------------------

function buildExternalNodes(extNodes: ExternalLineageNode[]): LineageNode[] {
  return extNodes.map((n) => ({
    id: n.name,
    label: n.display,
    kind: "external_bi" as const,
    icon: LayoutDashboard,
    databricksUrl: n.url, // click-through opens the (fake) PBI report
    description: n.description,
    externalUrl: n.url,
    entityType: (n.entity_type === "dashboard" ? "dashboard" : "report") as
      | "dashboard"
      | "report",
    externalBadge: `Power BI · ${
      n.entity_type === "dashboard" ? "Dashboard" : "Report"
    }`,
    columns: n.columns.map((c) => ({ name: c, pii: null as PiiTag })),
  }));
}

function buildExternalEdges(extEdges: ExternalLineageEdge[]): LineageEdge[] {
  return extEdges.map((e) => ({
    from: `${e.source_table}.${e.source_column}`,
    to: `${e.target_external}.${e.target_column}`,
    piiTraceGroup: "external_bi",
  }));
}

function LineageDAG() {
  const { data: wsConfig } = useWorkspaceConfig();
  const { data: colMetaWrapper } = useGetColumnMetadataSuspense();
  const colMeta = colMetaWrapper?.data ?? [];

  // External Lineage toggle — defaults OFF so the existing DAG renders
  // exactly as today. Flipping it on fetches /api/governance/external-lineage
  // lazily (suspense-free useQuery), then merges those nodes/edges into the
  // existing arrays so the SVG renderer and PII trace highlighting work
  // unchanged.
  const [showExternal, setShowExternal] = useState<boolean>(false);
  const externalQuery = useGetExternalLineage({
    query: { enabled: showExternal, staleTime: 10 * 60 * 1000 },
  } as Parameters<typeof useGetExternalLineage>[0]);
  // Generated hooks can return either a raw payload or an envelope { data }.
  // Normalize both shapes so External BI nodes render consistently.
  const externalLineage = ((externalQuery.data as { data?: unknown } | undefined)?.data ??
    externalQuery.data) as
    | {
        nodes: ExternalLineageNode[];
        edges: ExternalLineageEdge[];
        source?: "live" | "fallback";
      }
    | undefined;

  const baseLineageNodes = useMemo(() => {
    if (!wsConfig) return [] as LineageNode[];
    const piiLookup = buildPiiLookup(colMeta);
    const descMap = new Map<string, string>();
    const tableComments = new Map<string, string>();
    for (const c of colMeta) {
      if (c.comment && !tableComments.has(c.table_name)) {
        tableComments.set(c.table_name, c.table_name);
      }
    }
    return buildLineageNodes(wsConfig, piiLookup, descMap);
  }, [wsConfig, colMeta]);

  const LINEAGE_NODES = useMemo(() => {
    if (!showExternal || !externalLineage) return baseLineageNodes;
    return [...baseLineageNodes, ...buildExternalNodes(externalLineage.nodes)];
  }, [baseLineageNodes, showExternal, externalLineage]);

  // When External Lineage is enabled, swap the downstream lane from
  // "LLM / Outputs" to "External BI" for a cleaner visual story:
  // Source -> ML Models -> Scored Output -> External BI
  // (instead of rendering both downstream families at once).
  const allEdges = useMemo(() => {
    if (!showExternal) return LINEAGE_EDGES;
    const baseWithoutLlmOutcome = LINEAGE_EDGES.filter((e) => {
      const fromNode = e.from.split(".")[0];
      const toNode = e.to.split(".")[0];
      const from = LINEAGE_NODES.find((n) => n.id === fromNode);
      const to = LINEAGE_NODES.find((n) => n.id === toNode);
      const isLlmOutcomeEdge = from?.kind === "llm" || from?.kind === "outcome" || to?.kind === "llm" || to?.kind === "outcome";
      return !isLlmOutcomeEdge;
    });
    return externalLineage ? [...baseWithoutLlmOutcome, ...buildExternalEdges(externalLineage.edges)] : baseWithoutLlmOutcome;
  }, [showExternal, externalLineage, LINEAGE_NODES]);

  const containerRef = useRef<HTMLDivElement>(null);
  const fieldRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [edges, setEdges] = useState<{ x1: number; y1: number; x2: number; y2: number; piiTraceGroup?: string; pii: PiiTag; isExternal?: boolean }[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null);

  const registerRef = useCallback((key: string, el: HTMLDivElement | null) => {
    fieldRefs.current[key] = el;
  }, []);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const calc = () => {
      const rect = container.getBoundingClientRect();
      const newEdges = allEdges.map((e) => {
        const fromEl = fieldRefs.current[e.from];
        const toEl = fieldRefs.current[e.to];
        if (!fromEl || !toEl) return null;
        const fr = fromEl.getBoundingClientRect();
        const tr = toEl.getBoundingClientRect();
        const fromCol = LINEAGE_NODES.find((n) => n.id === e.from.split(".")[0])?.columns.find((c) => c.name === e.from.split(".")[1]);
        return {
          x1: fr.right - rect.left,
          y1: fr.top + fr.height / 2 - rect.top,
          x2: tr.left - rect.left,
          y2: tr.top + tr.height / 2 - rect.top,
          piiTraceGroup: e.piiTraceGroup,
          pii: fromCol?.pii ?? null,
          isExternal: e.piiTraceGroup === "external_bi",
        };
      }).filter(Boolean) as typeof edges;
      setEdges(newEdges);
    };
    // Defer one frame so the new external column is in the DOM before we
    // measure refs — otherwise the merged edges would all be null.
    const raf = requestAnimationFrame(calc);
    const ro = new ResizeObserver(calc);
    ro.observe(container);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [LINEAGE_NODES, allEdges]);

  const highlightedNodes = new Set<string>();
  if (selectedTrace) {
    for (const e of allEdges) {
      if (e.piiTraceGroup === selectedTrace) {
        highlightedNodes.add(e.from.split(".")[0]);
        highlightedNodes.add(e.to.split(".")[0]);
      }
    }
  }

  const columns = useMemo(() => {
    if (showExternal) {
      return [
        { label: "Source", kinds: ["source"] as NodeKind[] },
        { label: "ML Models", kinds: ["ml"] as NodeKind[] },
        { label: "Scored Output", kinds: ["scored"] as NodeKind[] },
        { label: "External BI", kinds: ["external_bi"] as NodeKind[] },
      ];
    }
    return [
      { label: "Source", kinds: ["source"] as NodeKind[] },
      { label: "ML Models", kinds: ["ml"] as NodeKind[] },
      { label: "Scored Output", kinds: ["scored"] as NodeKind[] },
      { label: "LLM / Outputs", kinds: ["llm", "outcome"] as NodeKind[] },
    ];
  }, [showExternal]);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle>Unity Catalog Lineage</CardTitle>
              <p className="text-sm text-muted-foreground">
                Column-level data flow — click any{" "}
                <Badge variant="outline" className="text-[10px] px-1 py-0 bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800">PII</Badge>{" "}
                badge to trace its lineage, or click a node to inspect
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {selectedTrace && (
                <button
                  onClick={() => setSelectedTrace(null)}
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md border px-2 py-1"
                >
                  <X className="h-3 w-3" /> Clear trace
                </button>
              )}
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <LayoutDashboard className="h-3.5 w-3.5 text-[#F2C811]" />
                <span className="text-xs text-muted-foreground">External Lineage</span>
                <Switch
                  checked={showExternal}
                  onCheckedChange={setShowExternal}
                  aria-label="Toggle external Power BI lineage column"
                />
              </label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {showExternal && (
            <div className="mb-4 rounded-md border border-[#F2C811]/40 bg-[#F2C811]/5 px-3 py-2 flex items-start gap-2">
              <Sparkles className="h-3.5 w-3.5 text-[#F2C811] mt-0.5 shrink-0" />
              <p className="text-xs text-muted-foreground leading-relaxed">
                Databricks features are roadmapped to make it even easier to get Power BI lineage into Unity Catalog
                &mdash; native PBI semantic-model capture, Lakeflow Connect for Power BI, and richer Microsoft Fabric
                cross-lineage are all on the way. Today this view is powered by the GA{" "}
                <a
                  className="underline hover:text-foreground"
                  href="https://learn.microsoft.com/en-gb/azure/databricks/data-governance/unity-catalog/external-lineage"
                  target="_blank"
                  rel="noreferrer"
                >
                  External Metadata &amp; External Lineage APIs
                </a>
                {externalLineage?.source === "fallback" && (
                  <>
                    {" "}<span className="text-[10px] opacity-75">(showing demo defaults — run the bootstrap notebook to register objects in your metastore)</span>
                  </>
                )}
                {externalLineage?.source === "live" && (
                  <>
                    {" "}<span className="text-[10px] opacity-75">(reading live from your metastore via WorkspaceClient.external_metadata)</span>
                  </>
                )}.
              </p>
            </div>
          )}
          <div ref={containerRef} className="relative rounded-lg border bg-muted/30 p-6 overflow-x-auto">
            {/* SVG edge overlay */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
              <defs>
                <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
                </marker>
                <marker id="arrowhead-red" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#dc2626" />
                </marker>
                <marker id="arrowhead-blue" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#2563eb" />
                </marker>
                <marker id="arrowhead-emerald" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#059669" />
                </marker>
                <marker id="arrowhead-yellow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill={POWER_BI_YELLOW} />
                </marker>
              </defs>
              {edges.map((e, i) => {
                const isTraced = selectedTrace ? e.piiTraceGroup === selectedTrace : false;
                const dim = selectedTrace && !isTraced;
                const dx = e.x2 - e.x1;
                const baseStroke = e.isExternal ? POWER_BI_YELLOW : "#94a3b8";
                const stroke = isTraced ? piiEdgeStroke(e.pii) : baseStroke;
                const markerEnd = isTraced
                  ? e.pii?.includes("derived") ? "url(#arrowhead-blue)" : e.pii?.includes("staff") ? "url(#arrowhead-emerald)" : "url(#arrowhead-red)"
                  : e.isExternal ? "url(#arrowhead-yellow)" : "url(#arrowhead)";
                return (
                  <path
                    key={i}
                    d={`M ${e.x1} ${e.y1} C ${e.x1 + dx * 0.4} ${e.y1}, ${e.x2 - dx * 0.4} ${e.y2}, ${e.x2} ${e.y2}`}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={isTraced ? 2.5 : e.isExternal ? 1.4 : 1}
                    strokeDasharray={e.isExternal && !isTraced ? "5 3" : dim ? "4 4" : "none"}
                    opacity={dim ? 0.15 : isTraced ? 1 : e.isExternal ? 0.7 : 0.35}
                    markerEnd={markerEnd}
                  />
                );
              })}
            </svg>

            {/* Node grid */}
            <div className="relative grid grid-cols-4 gap-x-16 gap-y-4" style={{ zIndex: 2 }}>
              {columns.map((col) => (
                <div key={col.label} className="space-y-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground text-center">
                    {col.label}
                  </p>
                  {LINEAGE_NODES.filter((n) => col.kinds.includes(n.kind)).map((node) => {
                    const dim = selectedTrace && highlightedNodes.size > 0 && !highlightedNodes.has(node.id);
                    return (
                      <div
                        key={node.id}
                        className={`rounded-lg border-l-4 border bg-background p-3 transition-all cursor-pointer hover:shadow-md ${NODE_BORDER_COLOR[node.kind]} ${dim ? "opacity-20" : ""}`}
                        onClick={() => setSelectedNode(node)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-mono text-[11px] font-semibold truncate">{node.label}</p>
                          <Badge variant="outline" className={`text-[9px] px-1.5 py-0 ${NODE_HEADER_BADGE[node.kind].cls}`}>
                            {NODE_HEADER_BADGE[node.kind].label}
                          </Badge>
                        </div>
                        <div className="space-y-1">
                          {node.columns.map((col) => {
                            const key = `${node.id}.${col.name}`;
                            const isFieldTraced = selectedTrace && allEdges.some(
                              (e) => e.piiTraceGroup === selectedTrace && (e.from === key || e.to === key)
                            );
                            return (
                              <div
                                key={col.name}
                                ref={(el) => registerRef(key, el)}
                                className={`flex items-center gap-1.5 py-0.5 px-1 rounded text-[11px] transition-all ${isFieldTraced ? "bg-red-50 dark:bg-red-950/30 ring-1 ring-red-300 dark:ring-red-800" : ""}`}
                              >
                                {col.pii ? (
                                  <Badge
                                    variant="outline"
                                    className={`text-[9px] px-1 py-0 cursor-pointer hover:ring-2 hover:ring-offset-1 transition-shadow ${piiColor(col.pii)}`}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      const traceGroup = allEdges.find(
                                        (edge) => (edge.from === key || edge.to === key) && edge.piiTraceGroup
                                      )?.piiTraceGroup ?? null;
                                      setSelectedTrace((prev) => prev === traceGroup ? null : traceGroup);
                                    }}
                                  >
                                    {col.pii}
                                  </Badge>
                                ) : (
                                  <span className="w-1 h-1 rounded-full bg-muted-foreground/30 shrink-0" />
                                )}
                                <span className={`font-mono truncate ${col.pii ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                                  {col.name}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Legend */}
            <div className="mt-6 pt-4 border-t border-border/50 flex flex-wrap items-center gap-x-5 gap-y-2 text-[10px] text-muted-foreground">
              <span className="font-semibold uppercase tracking-wider mr-1">Nodes</span>
              {Object.entries(NODE_HEADER_BADGE)
                .filter(([kind]) => showExternal || kind !== "external_bi")
                .map(([kind, meta]) => (
                  <span key={kind} className="flex items-center gap-1">
                    <span className={`w-2.5 h-2.5 rounded border ${meta.cls}`} />
                    {meta.label}
                  </span>
                ))}
              <span className="mx-2 text-border">|</span>
              <span className="font-semibold uppercase tracking-wider mr-1">PII Tags</span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-red-200 border border-red-400" /> PII
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-orange-200 border border-orange-400" /> Quasi-PII
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-blue-200 border border-blue-400" /> PII (derived)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-emerald-200 border border-emerald-400" /> PII (staff)
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Node detail side pane */}
      <Sheet open={!!selectedNode} onOpenChange={(open) => { if (!open) setSelectedNode(null); }}>
        <SheetContent className="w-[420px] sm:w-[480px] overflow-y-auto">
          {selectedNode && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2">
                  <selectedNode.icon className="h-5 w-5 text-muted-foreground" />
                  <SheetTitle className="font-mono text-base">{selectedNode.label}</SheetTitle>
                </div>
                <Badge variant="outline" className={`w-fit text-[10px] ${NODE_HEADER_BADGE[selectedNode.kind].cls}`}>
                  {NODE_HEADER_BADGE[selectedNode.kind].label}
                </Badge>
              </SheetHeader>

              <div className="mt-6 space-y-6">
                <div>
                  <p className="text-sm text-muted-foreground">{selectedNode.description}</p>
                </div>

                {selectedNode.kind === "external_bi" && (
                  <div className="rounded-md border border-[#F2C811]/40 bg-[#F2C811]/5 px-3 py-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px] border-[#F2C811]/50 bg-[#F2C811]/10 text-[#A38000] dark:text-[#F2C811]">
                        External Power BI {selectedNode.entityType === "dashboard" ? "Dashboard" : "Report"}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">
                        Registered as UC <code className="font-mono text-[10px]">external_metadata</code>
                      </span>
                    </div>
                    {selectedNode.externalUrl && (
                      <a
                        href={selectedNode.externalUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-[#A38000] dark:text-[#F2C811] hover:underline truncate max-w-full"
                      >
                        <ExternalLink className="h-3 w-3 shrink-0" />
                        <span className="truncate">{selectedNode.externalUrl}</span>
                      </a>
                    )}
                    {(() => {
                      const upstreamTable = allEdges
                        .filter((e) => e.to.startsWith(selectedNode.id + "."))
                        .map((e) => e.from.split(".")[0])
                        .find((id) => id && id !== "external_bi");
                      const upstreamUcUrl = upstreamTable && wsConfig
                        ? catalogExplorerUrl(wsConfig, upstreamTable)
                        : "";
                      const schemaUcUrl = wsConfig
                        ? `${wsConfig.workspace_url}/explore/data/${wsConfig.catalog}/${wsConfig.schema_name}`
                        : "";
                      return (
                        <div className="flex flex-wrap gap-2 pt-1">
                          {upstreamUcUrl && (
                            <a
                              href={upstreamUcUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-1 rounded-md border border-[#F2C811]/50 bg-[#F2C811]/10 text-[#A38000] dark:text-[#F2C811] hover:underline"
                            >
                              <ExternalLink className="h-3 w-3" />
                              View upstream UC table lineage
                            </a>
                          )}
                          {schemaUcUrl && (
                            <a
                              href={schemaUcUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-1 rounded-md border border-[#F2C811]/50 bg-[#F2C811]/10 text-[#A38000] dark:text-[#F2C811] hover:underline"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Open Unity Catalog schema
                            </a>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Columns</h4>
                  <div className="rounded-md border divide-y">
                    {selectedNode.columns.map((col) => {
                      const ucComment = colMeta.find(
                        (m) => m.table_name === selectedNode.id && m.column_name === col.name
                      )?.comment;
                      return (
                        <div key={col.name} className="px-3 py-2">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-sm">{col.name}</span>
                            {col.pii && (
                              <Badge variant="outline" className={`text-[10px] ${piiColor(col.pii)}`}>
                                {col.pii}
                              </Badge>
                            )}
                          </div>
                          {ucComment && (
                            <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">{ucComment}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Upstream</h4>
                  <div className="space-y-1">
                    {(() => {
                      const upstreams = allEdges
                        .filter((e) => e.to.startsWith(selectedNode.id + "."))
                        .map((e) => ({ edge: e, sourceNode: LINEAGE_NODES.find((n) => n.id === e.from.split(".")[0]) }))
                        .filter((x) => x.sourceNode);
                      if (upstreams.length === 0) return <p className="text-xs text-muted-foreground italic">No upstream dependencies (source table)</p>;
                      return upstreams.map(({ edge, sourceNode }) => (
                        <div key={edge.from + edge.to} className="flex items-center gap-2 text-xs">
                          <span className="font-mono text-muted-foreground">{sourceNode!.label}</span>
                          <span className="text-muted-foreground">.</span>
                          <span className="font-mono font-medium">{edge.from.split(".")[1]}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className="font-mono font-medium">{edge.to.split(".")[1]}</span>
                        </div>
                      ));
                    })()}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Downstream</h4>
                  <div className="space-y-1">
                    {(() => {
                      const downstreams = allEdges
                        .filter((e) => e.from.startsWith(selectedNode.id + "."))
                        .map((e) => ({ edge: e, targetNode: LINEAGE_NODES.find((n) => n.id === e.to.split(".")[0]) }))
                        .filter((x) => x.targetNode);
                      if (downstreams.length === 0) return <p className="text-xs text-muted-foreground italic">No downstream consumers (terminal table)</p>;
                      return downstreams.map(({ edge, targetNode }) => (
                        <div key={edge.from + edge.to} className="flex items-center gap-2 text-xs">
                          <span className="font-mono font-medium">{edge.from.split(".")[1]}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className="font-mono text-muted-foreground">{targetNode!.label}</span>
                          <span className="text-muted-foreground">.</span>
                          <span className="font-mono font-medium">{edge.to.split(".")[1]}</span>
                        </div>
                      ));
                    })()}
                  </div>
                </div>

                <a
                  href={selectedNode.databricksUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:underline"
                >
                  <ExternalLink className="h-4 w-4" />
                  {selectedNode.kind === "external_bi" ? "Open in Power BI" : "View in Databricks"}
                </a>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}

const ENDPOINT_DISPLAY: Record<string, { label: string; color: string }> = {
  "energy-theft-bedrock-gateway": { label: "Nova Lite", color: "border-[#FF9900] text-[#FF9900] bg-[#FF9900]/5" },
  "energy-theft-gemini-gateway": { label: "Gemini", color: "border-blue-500 text-blue-600 bg-blue-500/5" },
  "energy-theft-openai-gateway": { label: "Claude", color: "border-emerald-500 text-emerald-600 bg-emerald-500/5" },
  "energy-theft-llama-gateway": { label: "Llama", color: "border-purple-500 text-purple-600 bg-purple-500/5" },
};

function EndpointBadge({ name }: { name: string }) {
  const display = ENDPOINT_DISPLAY[name] ?? { label: name, color: "border-muted text-muted-foreground" };
  return (
    <Badge variant="outline" className={`text-[10px] whitespace-nowrap ${display.color}`}>
      {display.label}
    </Badge>
  );
}

const AUDIT_REFETCH_MS = 30_000;

function AuditPanel() {
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const auditQuery = {
    ...selector(),
    query: {
      ...selector().query,
      refetchInterval: AUDIT_REFETCH_MS,
      refetchOnMount: "always" as const,
      staleTime: 0,
    },
  };
  const { data: entries } = useGetAIGatewayAuditSuspense(
    auditQuery as Parameters<typeof useGetAIGatewayAuditSuspense>[0],
  );
  const { data: summary } = useGetAuditSummarySuspense(
    auditQuery as Parameters<typeof useGetAuditSummarySuspense>[0],
  );
  const { data: finops } = useGetFinOpsSummarySuspense(
    auditQuery as Parameters<typeof useGetFinOpsSummarySuspense>[0],
  );

  const refreshAudit = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        queryClient.fetchQuery({
          queryKey: getAIGatewayAuditKey(),
          queryFn: () => getAIGatewayAudit({ refresh: true }),
          staleTime: 0,
        }),
        queryClient.fetchQuery({
          queryKey: getAuditSummaryKey(),
          queryFn: () => getAuditSummary({ refresh: true }),
          staleTime: 0,
        }),
        queryClient.fetchQuery({
          queryKey: getFinOpsSummaryKey(),
          queryFn: () => getFinOpsSummary({ refresh: true }),
          staleTime: 0,
        }),
      ]);
    } finally {
      setRefreshing(false);
    }
  }, [queryClient]);

  const fmtTokens = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);

  const fmtCost = (n: number) =>
    n >= 1 ? `$${n.toFixed(2)}` : n >= 0.01 ? `$${n.toFixed(3)}` : `$${n.toFixed(4)}`;
  const fmtCostCompact = (n: number) =>
    n >= 1 ? `$${n.toFixed(2)}` : n >= 0.01 ? `$${n.toFixed(3)}` : n >= 0.0001 ? `$${n.toFixed(4)}` : "<$0.0001";
  const pctClass = (pct: number) =>
    pct >= 100 ? "bg-red-500" : pct >= 85 ? "bg-amber-500" : pct >= 70 ? "bg-yellow-500" : "bg-emerald-500";

  const summaryCards = [
    { label: "Total Calls", value: summary.total_calls.toLocaleString(), icon: Activity, color: "text-accent" },
    { label: "Input Tokens", value: fmtTokens(summary.total_input_tokens), icon: Hash, color: "text-blue-500" },
    { label: "Output Tokens", value: fmtTokens(summary.total_output_tokens), icon: Hash, color: "text-emerald-500" },
    { label: "Total Cost", value: fmtCost(summary.total_cost_usd), icon: Coins, color: "text-amber-500" },
    { label: "Errors", value: String(summary.error_count), icon: AlertTriangle, color: summary.error_count > 0 ? "text-red-500" : "text-muted-foreground" },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {summaryCards.map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-4 pb-3 px-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{s.label}</p>
                  <p className="text-xl font-bold tracking-tight mt-1">{s.value}</p>
                </div>
                <s.icon className={`h-5 w-5 ${s.color}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>AI Gateway Audit Trail</CardTitle>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 gap-1.5"
                onClick={() => void refreshAudit()}
                disabled={refreshing}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              <ModelBadge showModel />
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            LLM calls from <code className="text-xs bg-muted px-1 py-0.5 rounded">system.serving.endpoint_usage</code> —
            all four AI Gateway endpoints (Bedrock, Claude, Llama, Gemini); every call logged with caller, tokens, cost, and status
          </p>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <div className="h-40 flex flex-col items-center justify-center text-muted-foreground text-sm gap-1">
              <span>No audit entries yet — make an LLM call to generate data</span>
              <span className="text-xs">System tables may take up to 5 minutes to ingest new records. This panel auto-refreshes every 30s.</span>
            </div>
          ) : (
            <div className="rounded-md border max-h-[480px] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead>Caller</TableHead>
                    <TableHead className="text-right">Input</TableHead>
                    <TableHead className="text-right">Output</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Cost</TableHead>
                    <TableHead className="text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((e: AIGatewayAuditEntry, i: number) => {
                    const ts = new Date(e.request_timestamp);
                    const isError = (e.status_code ?? 200) >= 400;
                    return (
                      <TableRow key={i} className={isError ? "bg-red-50/50 dark:bg-red-950/20" : ""}>
                        <TableCell className="text-xs font-mono whitespace-nowrap">
                          {ts.toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}{" "}
                          {ts.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                        </TableCell>
                        <TableCell>
                          <EndpointBadge name={e.endpoint_name} />
                        </TableCell>
                        <TableCell className="text-xs max-w-[140px] truncate">
                          {e.request_user}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {e.input_token_count.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {e.output_token_count.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs font-semibold">
                          {e.total_token_count.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant="outline"
                            className={`text-xs font-mono ${
                              e.cost_usd >= 0.01
                                ? "border-amber-500 text-amber-600"
                                : "border-emerald-500 text-emerald-600"
                            }`}
                          >
                            {fmtCost(e.cost_usd)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant={isError ? "destructive" : "outline"}
                            className={`text-xs ${!isError ? "border-emerald-500 text-emerald-600" : ""}`}
                          >
                            {e.status_code ?? 200}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Gateway FinOps Story (Monthly)</CardTitle>
          <p className="text-sm text-muted-foreground">
            Source of truth is <code className="text-xs bg-muted px-1 py-0.5 rounded">system.serving.endpoint_usage</code> and
            Unity Catalog investigations. This connects governance controls directly to business impact.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "MTD AI Cost", value: fmtCost(finops.total_cost_usd_mtd), icon: Coins, color: "text-amber-500" },
              { label: "MTD Tokens", value: fmtTokens(finops.total_tokens_mtd), icon: Hash, color: "text-blue-500" },
              { label: "Blocked by Guardrails", value: String(finops.total_blocked_requests_mtd), icon: ShieldCheck, color: finops.total_blocked_requests_mtd > 0 ? "text-orange-500" : "text-emerald-500" },
              { label: "Confirmed Cases MTD", value: finops.investigations_mtd.toLocaleString(), icon: Activity, color: "text-violet-500" },
              { label: "AI Cost / Investigation", value: fmtCostCompact(finops.cost_per_investigation_usd), icon: Gauge, color: "text-fuchsia-500" },
            ].map((s) => (
              <Card key={s.label}>
                <CardContent className="pt-4 pb-3 px-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{s.label}</p>
                      <p className="text-xl font-bold tracking-tight mt-1">{s.value}</p>
                    </div>
                    <s.icon className={`h-5 w-5 ${s.color}`} />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <p className="text-xs text-muted-foreground -mt-1">
            AI Cost / Investigation = month-to-date AI Gateway spend divided by month-to-date confirmed theft cases closed in UC.
          </p>

          <div className="grid md:grid-cols-2 gap-3">
            {finops.endpoint_budgets.map((b) => (
              <div key={b.endpoint_name} className="rounded-lg border p-3 space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <EndpointBadge name={b.endpoint_name} />
                    <span className="text-sm font-medium">{b.display_name}</span>
                    {b.display_name.includes("Bedrock") && (
                      <Badge variant="outline" className="text-[10px] border-amber-500 text-amber-600">
                        Lowest budget by design
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    RL: {b.rate_limit_endpoint_calls_per_min}/min endpoint · {b.rate_limit_user_calls_per_min}/min user
                  </div>
                </div>
                <div className="grid md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Token Budget</span>
                      <span className="font-medium">{fmtTokens(b.used_tokens_mtd)} / {fmtTokens(b.monthly_token_budget)} ({b.token_budget_pct.toFixed(1)}%)</span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div className={`h-full ${pctClass(b.token_budget_pct)}`} style={{ width: `${Math.min(100, b.token_budget_pct)}%` }} />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Cost Budget</span>
                      <span className="font-medium">{fmtCost(b.used_cost_usd_mtd)} / {fmtCost(b.monthly_usd_budget)} ({b.usd_budget_pct.toFixed(1)}%)</span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div className={`h-full ${pctClass(b.usd_budget_pct)}`} style={{ width: `${Math.min(100, b.usd_budget_pct)}%` }} />
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Blocked/denied calls this month: <span className="font-semibold">{b.blocked_request_count_mtd}</span> ·
                  demonstrates guardrail enforcement reducing unsafe data exfiltration risk.
                </p>
              </div>
            ))}
          </div>

          <div className={`rounded-lg border p-3 ${finops.anomaly_alert.active ? "border-red-300 bg-red-50/50 dark:bg-red-950/20" : "border-emerald-300 bg-emerald-50/50 dark:bg-emerald-950/20"}`}>
            <div className="flex items-start gap-2">
              <TrendingUp className={`h-4 w-4 mt-0.5 ${finops.anomaly_alert.active ? "text-red-500" : "text-emerald-500"}`} />
              <div className="text-sm">
                <p className="font-medium">
                  {finops.anomaly_alert.active ? "Budget anomaly detector: spike detected" : "Budget anomaly detector: normal"}
                </p>
                <p className="text-muted-foreground text-xs mt-0.5">
                  {finops.anomaly_alert.message}
                  {finops.anomaly_alert.active && (
                    <>
                      {" "}({finops.anomaly_alert.latest_day}: {fmtTokens(finops.anomaly_alert.latest_tokens)} vs trailing {fmtTokens(Math.round(finops.anomaly_alert.trailing_avg_tokens))}, {finops.anomaly_alert.spike_ratio.toFixed(2)}x)
                    </>
                  )}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </CardContent>
    </Card>
  );
}
