"use client";

import { useId, useState } from "react";
import { cn } from "@/lib/utils";

export function NavTooltip({
  label,
  children,
  side = "right",
}: {
  label: string;
  children: React.ReactElement;
  side?: "right" | "bottom";
}) {
  const [visible, setVisible] = useState(false);
  const tipId = useId();

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      <span
        id={tipId}
        role="tooltip"
        className={cn(
          "pointer-events-none absolute z-50 whitespace-nowrap rounded-md border border-ink/10 bg-surface-elevated px-2 py-1 text-xs text-ink shadow-sm transition-opacity duration-150",
          side === "right" && "left-full top-1/2 ml-2 -translate-y-1/2",
          side === "bottom" && "left-1/2 top-full mt-2 -translate-x-1/2",
          visible ? "opacity-100" : "opacity-0"
        )}
      >
        {label}
      </span>
    </span>
  );
}
