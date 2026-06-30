import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = true }: LogoProps) {
  const content = (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/british-gas-logo.svg"
        alt="British Gas"
        className="h-10 w-auto"
      />
      {showText && (
        <div className="flex flex-col leading-tight">
          <span className="font-bold text-base tracking-tight">
            Revenue Protection
          </span>
          <span className="text-xs text-sidebar-foreground/60">
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
