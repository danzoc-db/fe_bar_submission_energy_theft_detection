import { fabricCompete, type CompeteEntry } from "../../compete/fabric";

export type { CompeteEntry };

export const competeConfig: Record<string, CompeteEntry> = Object.fromEntries(
  fabricCompete.map((e) => [e.id, e])
);
