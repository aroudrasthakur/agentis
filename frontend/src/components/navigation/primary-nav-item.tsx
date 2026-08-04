"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { NavTooltip } from "./nav-tooltip";

type PrimaryNavItemProps = {
  label: string;
  icon: LucideIcon;
  active: boolean;
  onClick: () => void;
  showTooltip: boolean;
};

export function PrimaryNavItem({
  label,
  icon: Icon,
  active,
  onClick,
  showTooltip,
}: PrimaryNavItemProps) {
  const button = (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-current={active ? "true" : undefined}
      className={cn(
        "relative flex h-10 w-10 items-center justify-center rounded-lg text-ink/55 transition-colors duration-150",
        "hover:bg-ink/[0.06] hover:text-ink",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal/60",
        active && "bg-ink/[0.08] text-ink"
      )}
    >
      {active && (
        <span
          className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-teal"
          aria-hidden
        />
      )}
      <Icon className="h-[21px] w-[21px] shrink-0" strokeWidth={1.75} aria-hidden />
    </button>
  );

  if (showTooltip) {
    return <NavTooltip label={label}>{button}</NavTooltip>;
  }
  return button;
}
