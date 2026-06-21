// Compete messaging config — source of truth mirrored from
// ~/.cursor/skills/show-me-dont-tell-me/compete/fabric.yaml
// Update the YAML first, then sync here. Last reviewed: 2026-06-21

export interface CompeteMessaging {
  tooltip: string;
  callout: string;
  depth?: string[];
  source: string;
}

export interface CompeteEntry {
  id: string;
  databricks: { component: string; products: string[]; product_keys: string[] };
  competitor: { equivalent: string; services: string[] };
  category: "Cost" | "Speed" | "Governance" | "DevEx" | "Architecture";
  messaging: CompeteMessaging;
  last_reviewed: string;
}

export const fabricCompete: CompeteEntry[] = [
  {
    id: "serverless-compute",
    databricks: {
      component: "Serverless SQL Warehouse",
      products: ["Databricks SQL", "Serverless Compute"],
      product_keys: ["sql_warehouse", "serverless_compute"],
    },
    competitor: { equivalent: "Fabric Capacity Units (CU)", services: ["Microsoft Fabric"] },
    category: "Cost",
    messaging: {
      tooltip:
        "Opaque, shared-capacity pricing — ETL, BI, Copilot, AI, and RTI all compete for one Fabric CU pool. When exhausted, workloads throttle or freeze.",
      callout:
        "Moving between CU bands costs double and requires careful capacity planning — overhead at the risk of downtime. Databricks serverless auto-scales per workload with transparent per-query pricing. Every component in this application runs on serverless compute — the SQL Warehouse auto-scales for queries, Genie runs on independent compute, Model Serving scales per-token. There is no idle cost.",
      depth: [
        "Fabric's capacity model shares a single compute pool across all workloads: dashboards, pipelines, AI, and Copilot",
        "When capacity is exhausted, Fabric throttles and then freezes the entire capacity — all workloads halt",
        "Pause-and-restart is the documented workaround, but it disrupts active queries and immediately bills accumulated overage",
      ],
      source: "go/fabric-compete-pricing (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "capacity-throttle",
    databricks: {
      component: "Serverless Compute + Lakeflow",
      products: ["Databricks SQL", "Serverless Compute", "Lakeflow"],
      product_keys: ["sql_warehouse", "serverless_compute", "lakeflow"],
    },
    competitor: {
      equivalent: "Fabric Capacity Units (CU) — shared pool",
      services: ["Microsoft Fabric"],
    },
    category: "Cost",
    messaging: {
      tooltip:
        "Fabric shares Capacity Units across all workloads — one pipeline spike throttles dashboards, AI, and BI simultaneously. No scale-to-zero; reserved capacity bills whether idle or not.",
      callout:
        "Fabric shares Capacity Units across all workloads — one spike throttles everything. No scale-to-zero; you pay for reserved capacity idle or not. Duplicated security & access control overhead: UC policies are not replicated into Fabric, so engineering time is spent re-aligning permission models for compliance. Another permission model to maintain.",
      depth: [
        "Fabric has no workload isolation — a rogue pipeline consumes CUs that would otherwise serve dashboards or Copilot",
        "Fabric's OneLake Storage, SQL Warehouse, DAX row-level security, and KQL each run independent permission models",
        "Databricks serverless bills per-query with automatic scale-to-zero — no reserved-capacity waste",
      ],
      source: "go/fabric-compete-pricing (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "genie-vs-pbi",
    databricks: {
      component: "Genie Space",
      products: ["Genie Space", "Unity Catalog"],
      product_keys: ["genie_space", "unity_catalog"],
    },
    competitor: {
      equivalent: "Power BI Copilot + Premium licensing",
      services: ["Power BI", "Microsoft Fabric"],
    },
    category: "Cost",
    messaging: {
      tooltip:
        "No per-user Copilot licence required — Genie queries Delta tables directly under Unity Catalog. Power BI Pro/Premium + Copilot each layer separate per-user or per-capacity billing.",
      callout:
        "Power BI Pro/Premium + Copilot each require per-user or per-capacity licensing. With Genie, you only pay for what you use — no licence to talk to your data. Genie queries Delta tables directly under UC: same governance, same user identity, same lineage. No need to mirror into Fabric, no UC policies to recreate, no propagation lag. KPIs are governed at the source.",
      depth: [
        "Power BI Copilot requires a pre-built DAX semantic model — schema changes break it silently with no automated alert",
        "No in-dashboard conversational capability in Fabric — users must context-switch to a separate Copilot interface",
        "Embedding NL analytics into custom applications via REST API remains in preview for Fabric",
      ],
      source: "go/genie-vs-pbi-compete (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "metric-views",
    databricks: {
      component: "Unity Catalog Metric Views",
      products: ["Unity Catalog", "Genie Space"],
      product_keys: ["unity_catalog", "genie_space"],
    },
    competitor: {
      equivalent: "Power BI Semantic Models (DAX)",
      services: ["Power BI", "Microsoft Fabric"],
    },
    category: "Governance",
    messaging: {
      tooltip:
        "One SQL Metric View replaces 20+ manually maintained DAX measures at different granularities — governed by UC, queryable everywhere. DAX formulas live outside the governance perimeter.",
      callout:
        "Legacy BI semantic models require proprietary languages, specialist skill sets, and 20+ measures manually maintained at different granularities. Formulas live outside the governance perimeter and can drift silently. Databricks Metric Views define KPIs once in SQL, governed by Unity Catalog — queryable in Apps, Genie, Agents, and any downstream BI tool. One object replaces the entire semantic layer.",
      depth: [
        "Power BI DAX semantic models require specialist skills and break silently when the underlying schema changes",
        "DAX measures are not governed objects — they live inside Power BI Desktop files, not in a catalogued data platform",
        "UC Metric Views are version-controlled, permissioned, and usable by LLMs without hallucination risk",
      ],
      source: "go/metric-views-vs-pbi-compete (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "unified-governance",
    databricks: {
      component: "Unity Catalog",
      products: ["Unity Catalog"],
      product_keys: ["unity_catalog"],
    },
    competitor: {
      equivalent: "Microsoft Purview + Azure ML + AI Foundry (split governance)",
      services: ["Microsoft Purview", "Microsoft Fabric", "Azure Machine Learning", "Azure AI Foundry"],
    },
    category: "Governance",
    messaging: {
      tooltip:
        "Single catalog for data, models, LLMs, Genie, and lineage — not Purview for data, Azure ML for models, AI Foundry for LLMs, each with separate audit logs.",
      callout:
        "When AI governance is spread across multiple services — a model registry in one portal, an LLM audit log in another, data lineage in a third — assembling a coherent audit trail requires manual stitching. Each seam is a gap that a regulator or internal auditor can challenge. Unity Catalog provides column-level lineage from raw data through model input to investigation output, with PII badges and automated data classification.",
      depth: [
        "In typical Azure architectures, ML governance sits in one service, LLM governance in another, and data governance in a third",
        "Item-level lineage (knowing which table was used) is insufficient — column-level lineage (which PII fields the model consumed) is required for compliance",
        "Without automated data classification, PII tagging must be maintained manually across every access point",
      ],
      source: "go/uc-vs-purview-compete (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "platform-apps",
    databricks: {
      component: "Databricks Apps",
      products: ["Databricks Apps"],
      product_keys: ["databricks_apps"],
    },
    competitor: {
      equivalent: "Azure App Service + Power BI Embedded + AI Foundry",
      services: ["Azure App Service", "Power BI Embedded", "Azure AI Foundry", "Microsoft Fabric"],
    },
    category: "Architecture",
    messaging: {
      tooltip:
        "One Databricks App replaces 5+ Azure services — App Service, Power BI Embedded, AI Foundry, Fabric SQL, and Purview — each with its own billing, auth, and admin portal.",
      callout:
        "In a typical Azure architecture, building equivalent functionality requires assembling a web application framework, a separate BI embedding layer, a separate AI service, and a separate analytics endpoint — each with its own authentication, billing, and security model. The integration overhead delays time-to-value, and each seam is a potential point of failure. A Databricks App runs within one deployment, one identity model, and one governance perimeter.",
      depth: [
        "Azure App Service (web app) + Power BI Embedded (dashboards) + Azure AI Foundry (LLM) + Fabric SQL (queries) + Purview (governance) = 5+ services, 4+ admin portals, 5 permission models",
        "Microsoft's own documentation positions AI Foundry as something Fabric 'integrates with', not a native component",
        "Each service has its own admin console, permissions model, and billing line",
      ],
      source: "go/apps-vs-azure-compete (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "model-lifecycle",
    databricks: {
      component: "MLflow + Unity Catalog Model Registry",
      products: ["MLflow", "Model Serving", "Unity Catalog"],
      product_keys: ["mlflow", "model_serving", "unity_catalog"],
    },
    competitor: { equivalent: "Azure ML", services: ["Azure Machine Learning"] },
    category: "DevEx",
    messaging: {
      tooltip:
        "ML models, training data, scoring outputs, and serving endpoints governed under the same catalog — not split across Azure ML and a separate data platform.",
      callout:
        "When the ML lifecycle is split across a data platform and a separate ML service, retraining requires data extraction across service boundaries. Model monitoring requires a third tool. The feedback loop between outcomes and model retraining becomes a multi-sprint integration project. In Databricks, both models are registered in MLflow within Unity Catalog — the same catalog governs training tables, feature engineering, scores, and labels for retraining.",
      depth: [
        "In Fabric, ML models must be trained and served through Azure ML — a separate service with its own portal, authentication, and cost centre",
        "No GPU compute available within Fabric's Spark environment — deep learning workloads require leaving the platform entirely",
        "No native feature store, model monitoring, or drift detection within the analytics platform",
      ],
      source: "go/mlflow-vs-azureml-compete (internal)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "ai-gateway",
    databricks: {
      component: "Unity AI Gateway",
      products: ["Model Serving", "AI Gateway", "Unity Catalog"],
      product_keys: ["model_serving", "ai_gateway", "unity_catalog"],
    },
    competitor: {
      equivalent: "Azure AI Foundry",
      services: ["Azure AI Foundry", "Azure Monitor", "Azure Content Safety"],
    },
    category: "Architecture",
    messaging: {
      tooltip:
        "Multi-cloud model routing (GPT, Claude, Bedrock, Gemini) through a single Unity AI Gateway — unified audit, OBO identity, and agentic governance in Unity Catalog. AI Foundry proxies all partner models through Azure infrastructure with no Google model support and no data lineage.",
      callout:
        "Azure AI Foundry is the model hub for Azure OpenAI and a curated subset of models — all partner traffic is proxied through Azure infrastructure, Google models (Gemini/Gemma) are absent, and routing to Bedrock requires leaving the platform. Governance is siloed: no cross-project lineage, no unified asset catalog, and audit lives in Azure Monitor/App Insights rather than alongside your data. Unity AI Gateway provides a single control plane for models, MCP servers, and agents — governed by Unity Catalog with OBO identity passthrough so agents respect user permissions automatically. Note: Unity AI Gateway is currently in beta (Public Preview targeting July 2026) — validate current GA status before customer commitments.",
      depth: [
        "AI Foundry has no Google model support (Gemini/Gemma absent); all partner model traffic is Azure-proxied with undisclosed markup and delayed access to new provider features",
        "AI Foundry governance is siloed per project with no cross-workspace lineage, no unified asset catalog, and no documented data lineage (battlecard: ❌ None documented)",
        "Audit logging lives in Azure Monitor/App Insights, not in the Foundry portal — per-principal audit requires Entra ID activity logs; agent tracing is Preview-only",
        "Unity AI Gateway OBO execution: agents inherit the requesting user's exact permissions via credential passthrough — no manual RBAC setup required",
        "Unity AI Gateway governs models, MCP servers, and agents as UC securables — the same catalog that governs your training data governs your AI stack",
      ],
      source: "go/aigateway-vs-foundry-compete (internal) | go/aigateway (demo + FAQ)",
    },
    last_reviewed: "2026-06-21",
  },
  {
    id: "agent-governance",
    databricks: {
      component: "Agent Bricks + Unity Catalog",
      products: ["Databricks Apps", "Unity Catalog", "MLflow", "AI Gateway"],
      product_keys: ["databricks_apps", "unity_catalog", "mlflow", "ai_gateway"],
    },
    competitor: {
      equivalent: "Azure AI Foundry Connected Agents + Azure RBAC + Purview",
      services: ["Azure AI Foundry", "Microsoft Purview", "Azure Monitor"],
    },
    category: "Governance",
    messaging: {
      tooltip:
        "Agent Bricks inherit Unity Catalog ACLs automatically — no separate RBAC, AI Services keys, or Purview config. Full lineage from data source to agent output in one catalog.",
      callout:
        "AI Foundry Connected Agents offer similar routing — but agents don't inherit data ACLs from a unified catalog. Governance requires separate Azure RBAC, AI Services keys, and Purview configuration with no single lineage from data → agent → LLM → output. Agent Bricks differentiators: UC-native governance inherited by every brick, built-in price/quality model cascading behind one endpoint, MCP Catalog for org-wide tool discovery, and an MLflow feedback loop from production traces to model selection.",
      depth: [
        "AI Foundry Connected Agents require separate Azure RBAC roles, AI Services keys, and Purview classification — three config surfaces for one governance outcome",
        "No single lineage graph from raw data through agent tool calls to LLM output in the Azure stack",
        "MLflow feedback loop: Unity AI Gateway logs every inference trace; Agent Bricks can retrain or reweight model selection from production signal",
      ],
      source: "go/agent-bricks-vs-foundry-compete (internal)",
    },
    last_reviewed: "2026-06-21",
  },
];
