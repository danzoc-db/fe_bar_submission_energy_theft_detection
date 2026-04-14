import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ExternalLink } from "lucide-react";
import { useWorkspaceConfig } from "@/lib/workspace-config";

const ENDPOINT_NAME = "energy-theft-bedrock-gateway";
const MODEL_ID = "Claude 3.5 Haiku";
const PROVIDER = "Amazon Bedrock";

const AWS_ORANGE = "#FF9900";

function BedrockLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 2L3 7v10l9 5 9-5V7l-9-5z"
        stroke={AWS_ORANGE}
        strokeWidth="1.5"
        fill={`${AWS_ORANGE}20`}
      />
      <path
        d="M12 6.5l-4.5 2.5v5L12 16.5l4.5-2.5V9L12 6.5z"
        fill={AWS_ORANGE}
        opacity="0.6"
      />
      <circle cx="12" cy="11.5" r="2" fill={AWS_ORANGE} />
    </svg>
  );
}

interface BedrockBadgeProps {
  size?: "sm" | "md";
  showModel?: boolean;
  className?: string;
}

export function BedrockBadge({
  size = "sm",
  showModel = false,
  className = "",
}: BedrockBadgeProps) {
  const { data: wsConfig } = useWorkspaceConfig();
  const endpointUrl = wsConfig
    ? `${wsConfig.workspace_url}/#mlflow/endpoints/${ENDPOINT_NAME}`
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
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 transition-colors
            border-[${AWS_ORANGE}]/30 bg-[${AWS_ORANGE}]/5 hover:bg-[${AWS_ORANGE}]/10
            hover:border-[${AWS_ORANGE}]/50 ${textSize} ${className}`}
          style={{
            borderColor: `${AWS_ORANGE}40`,
            backgroundColor: `${AWS_ORANGE}08`,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <BedrockLogo className={iconSize} />
          <span
            className="font-medium"
            style={{ color: AWS_ORANGE }}
          >
            {showModel ? MODEL_ID : PROVIDER}
          </span>
          <ExternalLink
            className={`${linkSize} opacity-40`}
            style={{ color: AWS_ORANGE }}
          />
        </a>
      </TooltipTrigger>
      <TooltipContent
        side="bottom"
        className="max-w-[320px] text-xs space-y-2 bg-gray-900 text-white border-gray-700"
      >
        <div className="flex items-center gap-2">
          <BedrockLogo className="h-5 w-5" />
          <div>
            <p className="font-semibold" style={{ color: AWS_ORANGE }}>
              {PROVIDER} — {MODEL_ID}
            </p>
            <p className="text-gray-300">
              via Databricks AI Gateway
            </p>
          </div>
        </div>
        <p className="text-gray-300 leading-relaxed">
          Every LLM call is routed through the Databricks AI Gateway endpoint{" "}
          <code className="text-[10px] bg-gray-700 text-gray-200 px-1 py-0.5 rounded">
            {ENDPOINT_NAME}
          </code>
          . All requests are logged with caller identity, token usage, latency,
          and guardrail status in Unity Catalog system tables.
        </p>
        <a
          href={endpointUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] font-medium block hover:underline"
          style={{ color: AWS_ORANGE }}
          onClick={(e) => e.stopPropagation()}
        >
          Click to view the Model Serving endpoint →
        </a>
      </TooltipContent>
    </Tooltip>
  );
}

export { BedrockLogo, AWS_ORANGE, MODEL_ID, PROVIDER, ENDPOINT_NAME };
