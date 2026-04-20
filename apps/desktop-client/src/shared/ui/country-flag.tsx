import { ComponentType, SVGProps } from "react";
import * as Flags3x2 from "country-flag-icons/react/3x2";
import { Globe2 } from "lucide-react";

import { cn } from "@/lib/utils";

const Flags = Flags3x2 as Record<string, ComponentType<SVGProps<SVGSVGElement>>>;

interface CountryFlagProps extends SVGProps<SVGSVGElement> {
  code?: string | null;
  fallbackClassName?: string;
  flagTitle?: string;
}

export function CountryFlag({
  code,
  className,
  fallbackClassName,
  flagTitle,
  ...props
}: CountryFlagProps) {
  const normalizedCode = code?.trim().toUpperCase() ?? "";
  const FlagComponent = normalizedCode ? Flags[normalizedCode] : undefined;

  if (!FlagComponent) {
    return (
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center rounded-[0.2rem] border border-border/70 bg-[color:var(--panel-subtle)]/72 text-muted-foreground",
          fallbackClassName ?? className
        )}
        title={flagTitle ?? (normalizedCode || "Global")}
      >
        <Globe2 size={12} />
      </span>
    );
  }

  return (
    <FlagComponent
      aria-hidden
      className={className}
      {...props}
    />
  );
}
