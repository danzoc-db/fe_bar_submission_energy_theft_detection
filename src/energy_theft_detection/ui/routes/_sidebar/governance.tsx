import { createFileRoute } from "@tanstack/react-router";
import { Suspense, useState, useRef, useLayoutEffect, useCallback, useMemo } from "react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { BedrockBadge } from "@/components/bedrock-badge";
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
} from "lucide-react";
import {
  useGetPIIMatrixSuspense,
  useGetAIComponentsSuspense,
  useGetAIGatewayAuditSuspense,
  useGetAuditSummarySuspense,
  useGetColumnMetadataSuspense,
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
  getDashboardKPIs,
  getDashboardKPIsKey,
  getInvestigationKPIs,
  getInvestigationKPIsKey,
  getDailyBriefing,
  getDailyBriefingKey,
  listFlaggedAccounts,
  listFlaggedAccountsKey,
  type AIComponentRegistryItem,
  type AIGatewayAuditEntry,
  type ColumnMetadata,
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
    queryClient.ensureQueryData({ queryKey: getDashboardKPIsKey(), queryFn: getDashboardKPIs });
    queryClient.ensureQueryData({ queryKey: getInvestigationKPIsKey(), queryFn: getInvestigationKPIs });
    queryClient.ensureQueryData({ queryKey: getDailyBriefingKey(), queryFn: getDailyBriefing });
    queryClient.ensureQueryData({ queryKey: listFlaggedAccountsKey(), queryFn: () => listFlaggedAccounts() });

    queryClient.ensureQueryData({ queryKey: getColumnMetadataKey(), queryFn: getColumnMetadata, staleTime: GOV_STALE });
    queryClient.ensureQueryData({ queryKey: getAIGatewayAuditKey(), queryFn: () => getAIGatewayAudit() });
    queryClient.ensureQueryData({ queryKey: getAuditSummaryKey(), queryFn: getAuditSummary });

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
            Databricks AI Gateway provides a single, governed endpoint for Anthropic, Gemini, and OpenAI models.
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

      <FabricCallout category="Governance">
        <p>
          <strong>Fabric access control is split across 5 engines</strong> — workspace roles, OneLake Storage, SQL Warehouse, DAX row-level security, and KQL. Five permission models, limited automation, and no cross-lineage. Compliance blind spots are inevitable.
        </p>
        <p>
          Purview has no column-level lineage from data to model to LLM. No single audit log. UC solves this out of the box.
        </p>
      </FabricCallout>
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
type NodeKind = "source" | "ml" | "scored" | "llm" | "outcome";

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
      description: "Amazon Bedrock Claude via AI Gateway. Generates natural-language case summaries and field dispatch reports from account risk data.",
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
  ml: "border-l-[#002F87]",
  scored: "border-l-orange-500",
  llm: "border-l-[#FF9900]",
  outcome: "border-l-emerald-500",
};

const NODE_HEADER_BADGE: Record<NodeKind, { label: string; cls: string }> = {
  source: { label: "Source", cls: "bg-accent/10 text-accent border-accent/30" },
  ml: { label: "ML Model", cls: "bg-[#002F87]/10 text-[#002F87] border-[#002F87]/30 dark:text-blue-300" },
  scored: { label: "Scored", cls: "bg-orange-500/10 text-orange-600 border-orange-500/30" },
  llm: { label: "LLM", cls: "bg-[#FF9900]/10 text-[#FF9900] border-[#FF9900]/30" },
  outcome: { label: "Output", cls: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" },
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

function LineageDAG() {
  const { data: wsConfig } = useWorkspaceConfig();
  const { data: colMetaWrapper } = useGetColumnMetadataSuspense();
  const colMeta = colMetaWrapper?.data ?? [];

  const LINEAGE_NODES = useMemo(() => {
    if (!wsConfig) return [];
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
  const containerRef = useRef<HTMLDivElement>(null);
  const fieldRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [edges, setEdges] = useState<{ x1: number; y1: number; x2: number; y2: number; piiTraceGroup?: string; pii: PiiTag }[]>([]);
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
      const newEdges = LINEAGE_EDGES.map((e) => {
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
        };
      }).filter(Boolean) as typeof edges;
      setEdges(newEdges);
    };
    calc();
    const ro = new ResizeObserver(calc);
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  const highlightedNodes = new Set<string>();
  if (selectedTrace) {
    for (const e of LINEAGE_EDGES) {
      if (e.piiTraceGroup === selectedTrace) {
        highlightedNodes.add(e.from.split(".")[0]);
        highlightedNodes.add(e.to.split(".")[0]);
      }
    }
  }

  const columns = [
    { label: "Source", kinds: ["source"] as NodeKind[] },
    { label: "ML Models", kinds: ["ml"] as NodeKind[] },
    { label: "Scored Output", kinds: ["scored"] as NodeKind[] },
    { label: "LLM / Outputs", kinds: ["llm", "outcome"] as NodeKind[] },
  ];

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Unity Catalog Lineage</CardTitle>
              <p className="text-sm text-muted-foreground">
                Column-level data flow — click any{" "}
                <Badge variant="outline" className="text-[10px] px-1 py-0 bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800">PII</Badge>{" "}
                badge to trace its lineage, or click a node to inspect
              </p>
            </div>
            {selectedTrace && (
              <button
                onClick={() => setSelectedTrace(null)}
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md border px-2 py-1"
              >
                <X className="h-3 w-3" /> Clear trace
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
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
              </defs>
              {edges.map((e, i) => {
                const isTraced = selectedTrace ? e.piiTraceGroup === selectedTrace : false;
                const dim = selectedTrace && !isTraced;
                const dx = e.x2 - e.x1;
                const stroke = isTraced ? piiEdgeStroke(e.pii) : "#94a3b8";
                const markerEnd = isTraced
                  ? e.pii?.includes("derived") ? "url(#arrowhead-blue)" : e.pii?.includes("staff") ? "url(#arrowhead-emerald)" : "url(#arrowhead-red)"
                  : "url(#arrowhead)";
                return (
                  <path
                    key={i}
                    d={`M ${e.x1} ${e.y1} C ${e.x1 + dx * 0.4} ${e.y1}, ${e.x2 - dx * 0.4} ${e.y2}, ${e.x2} ${e.y2}`}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={isTraced ? 2.5 : 1}
                    strokeDasharray={dim ? "4 4" : "none"}
                    opacity={dim ? 0.15 : isTraced ? 1 : 0.35}
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
                            const isFieldTraced = selectedTrace && LINEAGE_EDGES.some(
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
                                      const traceGroup = LINEAGE_EDGES.find(
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
              {Object.entries(NODE_HEADER_BADGE).map(([kind, meta]) => (
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
                      const upstreams = LINEAGE_EDGES
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
                      const downstreams = LINEAGE_EDGES
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
                  View in Databricks
                </a>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}

const AUDIT_REFETCH_MS = 30_000;

function AuditPanel() {
  const { data: entries } = useGetAIGatewayAuditSuspense({
    ...selector(),
    query: { ...selector().query, refetchInterval: AUDIT_REFETCH_MS },
  } as Parameters<typeof useGetAIGatewayAuditSuspense>[0]);
  const { data: summary } = useGetAuditSummarySuspense({
    ...selector(),
    query: { ...selector().query, refetchInterval: AUDIT_REFETCH_MS },
  } as Parameters<typeof useGetAuditSummarySuspense>[0]);

  const fmtTokens = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);

  const fmtCost = (n: number) =>
    n >= 1 ? `$${n.toFixed(2)}` : n >= 0.01 ? `$${n.toFixed(3)}` : `$${n.toFixed(4)}`;

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
          <div className="flex items-center justify-between">
            <CardTitle>AI Gateway Audit Trail</CardTitle>
            <BedrockBadge showModel />
          </div>
          <p className="text-sm text-muted-foreground">
            LLM calls from <code className="text-xs bg-muted px-1 py-0.5 rounded">system.serving.endpoint_usage</code> —
            every call logged with caller, tokens, cost, and status
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
                        <TableCell className="text-xs max-w-[160px] truncate">
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
