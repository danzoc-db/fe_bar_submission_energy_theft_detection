import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

// ── Model selector types ──

export type ModelKey = "bedrock" | "openai" | "llama";

export interface ModelConfig {
  key: ModelKey;
  label: string;
  provider: string;
  model: string;
  endpointName: string;
  color: string;
  iconColor: string;
  bgColor: string;
  borderColor: string;
}

export const MODEL_CONFIGS: Record<ModelKey, ModelConfig> = {
  bedrock: {
    key: "bedrock",
    label: "Amazon Bedrock",
    provider: "Amazon Bedrock",
    model: "Claude 3.5 Haiku",
    endpointName: "energy-theft-bedrock-gateway",
    color: "#FF9900",
    iconColor: "text-[#FF9900]",
    bgColor: "bg-[#FF9900]/[0.04]",
    borderColor: "border-[#FF9900]/30",
  },
  openai: {
    key: "openai",
    label: "OpenAI (FMAPI)",
    provider: "Foundation Model API",
    model: "GPT-4o Mini",
    endpointName: "energy-theft-openai-gateway",
    color: "#10A37F",
    iconColor: "text-[#10A37F]",
    bgColor: "bg-[#10A37F]/[0.04]",
    borderColor: "border-[#10A37F]/30",
  },
  llama: {
    key: "llama",
    label: "Meta Llama (FMAPI)",
    provider: "Foundation Model API",
    model: "Llama 3.1 70B",
    endpointName: "energy-theft-llama-gateway",
    color: "#0668E1",
    iconColor: "text-[#0668E1]",
    bgColor: "bg-[#0668E1]/[0.04]",
    borderColor: "border-[#0668E1]/30",
  },
};

// ── Context ──

interface DemoSettings {
  competeEnabled: boolean;
  setCompeteEnabled: (v: boolean) => void;
  modelKey: ModelKey;
  setModelKey: (k: ModelKey) => void;
  modelConfig: ModelConfig;
}

const DemoSettingsContext = createContext<DemoSettings | null>(null);

const STORAGE_KEY_COMPETE = "demo-compete-enabled";
const STORAGE_KEY_MODEL = "demo-model-key";

export function DemoSettingsProvider({ children }: { children: ReactNode }) {
  const [competeEnabled, setCompeteEnabled] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY_COMPETE) === "true";
    } catch {
      return false;
    }
  });

  const [modelKey, setModelKey] = useState<ModelKey>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_MODEL) as ModelKey | null;
      return stored && stored in MODEL_CONFIGS ? stored : "bedrock";
    } catch {
      return "bedrock";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_COMPETE, String(competeEnabled));
    } catch { /* noop */ }
  }, [competeEnabled]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_MODEL, modelKey);
    } catch { /* noop */ }
  }, [modelKey]);

  return (
    <DemoSettingsContext.Provider
      value={{
        competeEnabled,
        setCompeteEnabled,
        modelKey,
        setModelKey,
        modelConfig: MODEL_CONFIGS[modelKey],
      }}
    >
      {children}
    </DemoSettingsContext.Provider>
  );
}

export function useDemoSettings(): DemoSettings {
  const ctx = useContext(DemoSettingsContext);
  if (!ctx) throw new Error("useDemoSettings must be used within DemoSettingsProvider");
  return ctx;
}

export function getModelHeaders(): Record<string, string> {
  try {
    const key = localStorage.getItem(STORAGE_KEY_MODEL) || "bedrock";
    return { "x-model-key": key };
  } catch {
    return { "x-model-key": "bedrock" };
  }
}
