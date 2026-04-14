import { useState, useEffect, useRef, type ReactNode } from "react";
import { X, Wrench, type LucideIcon } from "lucide-react";
import { createPortal } from "react-dom";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useDemoSettings } from "@/lib/demo-settings";

const DB_ORANGE = "#FF3621";

interface UnderTheHoodProps {
  title: string;
  children: ReactNode;
}

export function UnderTheHood({ title, children }: UnderTheHoodProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onClick(e: MouseEvent) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const panel = open
    ? createPortal(
        <div
          ref={panelRef}
          className="fixed z-50 animate-in slide-in-from-left-4 fade-in-0 duration-200"
          style={{
            top: 80,
            left: 72,
            width: 420,
            maxHeight: "calc(100vh - 100px)",
          }}
        >
          <div className="rounded-xl border bg-card shadow-2xl overflow-hidden flex flex-col" style={{ maxHeight: "calc(100vh - 100px)" }}>
            {/* Orange header */}
            <div
              className="px-4 py-2.5 flex items-center justify-between shrink-0"
              style={{ background: DB_ORANGE }}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Wrench className="h-3.5 w-3.5 text-white shrink-0" />
                <div className="min-w-0">
                  <p className="text-white text-xs font-semibold leading-tight truncate">
                    Under the Hood
                  </p>
                  <p className="text-white/70 text-[10px] leading-tight truncate">
                    {title}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-white/60 hover:text-white transition-colors shrink-0 ml-2"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="overflow-y-auto px-4 py-3 space-y-3">
              {children}
            </div>
          </div>
        </div>,
        document.body,
      )
    : null;

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            ref={triggerRef}
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center justify-center h-7 w-7 rounded-md transition-colors hover:bg-[#FF3621]/10 group"
            aria-label="Under the Hood"
          >
            <Wrench
              className="h-4.5 w-4.5 transition-colors group-hover:drop-shadow-sm"
              style={{ color: DB_ORANGE }}
            />
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          Under the Hood
        </TooltipContent>
      </Tooltip>
      {panel}
    </>
  );
}

export function HoodSection({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon?: LucideIcon;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <h4 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {Icon && <Icon className="h-3 w-3" style={{ color: DB_ORANGE }} />}
        {title}
      </h4>
      <div className="text-[12px] leading-snug text-foreground space-y-1">
        {children}
      </div>
    </div>
  );
}

export function HoodBullet({
  icon: Icon,
  bold,
  children,
}: {
  icon?: LucideIcon;
  bold: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-start gap-1.5">
      {Icon ? (
        <Icon
          className="mt-0.5 h-3 w-3 shrink-0"
          style={{ color: DB_ORANGE }}
        />
      ) : (
        <span
          className="mt-1.5 h-1.5 w-1.5 rounded-full shrink-0"
          style={{ background: DB_ORANGE }}
        />
      )}
      <p>
        <strong>{bold}</strong> — {children}
      </p>
    </div>
  );
}

const CATEGORY_COLORS: Record<string, string> = {
  Cost: "border-amber-500/60 text-amber-700 dark:text-amber-400",
  Speed: "border-blue-500/60 text-blue-700 dark:text-blue-400",
  Governance: "border-purple-500/60 text-purple-700 dark:text-purple-400",
};

export function FabricCallout({
  children,
  category,
}: {
  children: ReactNode;
  category?: "Cost" | "Speed" | "Governance";
}) {
  const { competeEnabled } = useDemoSettings();
  if (!competeEnabled) return null;

  return (
    <div className="rounded-lg border border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/30 p-2.5 space-y-1">
      <div className="flex items-center gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-red-700 dark:text-red-400">
          Why not Fabric?
        </p>
        {category && (
          <span
            className={`inline-flex items-center rounded-full border px-1.5 py-0 text-[9px] font-semibold uppercase tracking-wider ${CATEGORY_COLORS[category]}`}
          >
            {category}
          </span>
        )}
      </div>
      <div className="text-[12px] leading-snug text-red-900 dark:text-red-200 space-y-1">
        {children}
      </div>
    </div>
  );
}
