import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ExternalLink, Cloud } from "lucide-react";
import { useWorkspaceConfig } from "@/lib/workspace-config";
import { useDemoSettings } from "@/lib/demo-settings";

interface ModelBadgeProps {
  size?: "sm" | "md";
  showModel?: boolean;
  className?: string;
}

export function ModelBadge({
  size = "sm",
  showModel = false,
  className = "",
}: ModelBadgeProps) {
  const { modelConfig } = useDemoSettings();
  const { data: wsConfig } = useWorkspaceConfig();
  const endpointUrl = wsConfig
    ? `${wsConfig.workspace_url}/#mlflow/endpoints/${modelConfig.endpointName}`
    : "#";
  const iconSize = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
  const textSize = size === "sm" ? "text-xs" : "text-sm";
  const linkSize = size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <a
          href={endpointUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 transition-colors ${textSize} ${className}`}
          style={{
            borderColor: `${modelConfig.color}40`,
            backgroundColor: `${modelConfig.color}08`,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <Cloud className={iconSize} style={{ color: modelConfig.color }} />
          <span className="font-medium" style={{ color: modelConfig.color }}>
            {showModel ? modelConfig.model : modelConfig.provider}
          </span>
          <ExternalLink
            className={`${linkSize} opacity-40`}
            style={{ color: modelConfig.color }}
          />
        </a>
      </TooltipTrigger>
      <TooltipContent
        side="bottom"
        className="max-w-[320px] text-xs space-y-2 bg-gray-900 text-white border-gray-700"
      >
        <div className="flex items-center gap-2">
          <Cloud className="h-5 w-5" style={{ color: modelConfig.color }} />
          <div>
            <p className="font-semibold" style={{ color: modelConfig.color }}>
              {modelConfig.provider} — {modelConfig.model}
            </p>
            <p className="text-gray-300">via Databricks AI Gateway</p>
          </div>
        </div>
        <p className="text-gray-300 leading-relaxed">
          Primary LLM routed through the Databricks AI Gateway endpoint{" "}
          <code className="text-[10px] bg-gray-700 text-gray-200 px-1 py-0.5 rounded">
            {modelConfig.endpointName}
          </code>
          . All requests are logged with caller identity, token usage, latency,
          and guardrail status in Unity Catalog system tables.
        </p>
        <a
          href={endpointUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] font-medium block hover:underline"
          style={{ color: modelConfig.color }}
          onClick={(e) => e.stopPropagation()}
        >
          Click to view the Model Serving endpoint →
        </a>
      </TooltipContent>
    </Tooltip>
  );
}
