import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
  /** Sidebar uses a stacked layout so the wordmark and title fit in 16rem. */
  variant?: "default" | "sidebar";
}

export function Logo({
  to = "/",
  className = "",
  showText = true,
  variant = "default",
}: LogoProps) {
  const isSidebar = variant === "sidebar";

  const content = (
    <div
      className={cn(
        "min-w-0",
        isSidebar ? "flex w-full flex-col gap-2" : "flex items-center gap-3",
        className,
      )}
    >
      <img
        src="/bg-icon.svg"
        alt="UKI Gas"
        className={cn(
          "w-auto shrink-0",
          isSidebar ? "h-8 max-w-full object-contain object-left" : "h-10",
        )}
      />
      {showText && (
        <div className={cn("flex min-w-0 flex-col leading-tight", isSidebar && "w-full")}>
          <span
            className={cn(
              "font-bold tracking-tight",
              isSidebar ? "text-sm leading-snug" : "text-base",
            )}
          >
            Revenue Protection
          </span>
          <span
            className={cn(
              isSidebar
                ? "text-[11px] leading-snug text-sidebar-foreground/60"
                : "text-xs text-muted-foreground/60",
            )}
          >
            Energy Theft Detection
          </span>
        </div>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="block min-w-0 hover:opacity-80 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}

export default Logo;
