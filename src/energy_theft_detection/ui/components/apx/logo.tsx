import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = true }: LogoProps) {
  const content = (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img
        src="/bg-icon.svg"
        alt="UKI Gas"
        className="h-7 w-auto"
      />
      {showText && (
        <div className="flex flex-col leading-tight">
          <span className="font-semibold text-sm tracking-tight">
            Revenue Protection
          </span>
          <span className="text-[10px] text-sidebar-foreground/60">
            Energy Theft Detection
          </span>
        </div>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="hover:opacity-80 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}

export default Logo;
