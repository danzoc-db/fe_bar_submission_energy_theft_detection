import { useQuery, useSuspenseQuery } from "@tanstack/react-query";

export interface WorkspaceConfig {
  workspace_url: string;
  catalog: string;
  schema_name: string;
  genie_space_id: string;
  mas_endpoint: string;
}

const WORKSPACE_CONFIG_KEY = ["workspace-config"] as const;

async function fetchWorkspaceConfig(): Promise<WorkspaceConfig> {
  const res = await fetch("/api/workspace-config");
  if (!res.ok) throw new Error("Failed to fetch workspace config");
  return res.json();
}

export const workspaceConfigQueryOptions = {
  queryKey: WORKSPACE_CONFIG_KEY,
  queryFn: fetchWorkspaceConfig,
  staleTime: Infinity,
  gcTime: Infinity,
} as const;

export function useWorkspaceConfig() {
  return useQuery(workspaceConfigQueryOptions);
}

export function useWorkspaceConfigSuspense() {
  return useSuspenseQuery(workspaceConfigQueryOptions);
}

export function genieSpaceUrl(config: WorkspaceConfig) {
  return `${config.workspace_url}/genie/rooms/${config.genie_space_id}`;
}

export function catalogExplorerUrl(config: WorkspaceConfig, table: string) {
  return `${config.workspace_url}/explore/data/${config.catalog}/${config.schema_name}/${table}`;
}

export function modelUrl(config: WorkspaceConfig, model: string) {
  return `${config.workspace_url}/explore/data/models/${config.catalog}/${config.schema_name}/${model}`;
}

export function masEndpointUrl(config: WorkspaceConfig) {
  if (!config.mas_endpoint) return "";
  return `${config.workspace_url}/ml/endpoints/${config.mas_endpoint}`;
}

export function fqn(config: WorkspaceConfig) {
  return `${config.catalog}.${config.schema_name}`;
}

export interface JobUrl {
  job_url: string;
  job_id: string;
}

const JOB_URL_KEY = ["pipeline-url"] as const;

async function fetchJobUrl(): Promise<JobUrl> {
  const res = await fetch("/api/pipeline-url");
  if (!res.ok) throw new Error("Failed to fetch job URL");
  return res.json();
}

export function useJobUrl() {
  return useQuery({
    queryKey: JOB_URL_KEY,
    queryFn: fetchJobUrl,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}
