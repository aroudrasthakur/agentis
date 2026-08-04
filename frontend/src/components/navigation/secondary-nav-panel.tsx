"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NavigationItem, RouteMatchContext } from "./navigation-types";
import { itemMatches } from "./navigation-utils";

export function SecondaryNavLink({
  item,
  ctx,
  onNavigate,
}: {
  item: NavigationItem;
  ctx: RouteMatchContext;
  onNavigate?: () => void;
}) {
  if (!item.href) {
    return null;
  }
  const active = itemMatches(item, ctx);

  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      title={item.label}
      className={cn(
        "block truncate rounded-md px-2.5 py-2 text-[13px] leading-snug transition-colors duration-150",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal/60",
        active
          ? "bg-teal/15 font-medium text-ink"
          : "text-ink/65 hover:bg-ink/[0.05] hover:text-ink"
      )}
    >
      {item.label}
    </Link>
  );
}

export function NavGroupBlock({
  groupId,
  label,
  items,
  ctx,
  expanded,
  onToggle,
  onNavigate,
  reducedMotion,
}: {
  groupId: string;
  label?: string;
  items: NavigationItem[];
  ctx: RouteMatchContext;
  expanded: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
  reducedMotion: boolean;
}) {
  if (!label) {
    return (
      <div className="flex flex-col gap-0.5">
        {items.map((item) => (
          <SecondaryNavLink key={item.id} item={item} ctx={ctx} onNavigate={onNavigate} />
        ))}
      </div>
    );
  }

  const regionId = `nav-group-${groupId}`;

  return (
    <div className="flex flex-col gap-0.5">
      <button
        type="button"
        id={`${regionId}-trigger`}
        aria-expanded={expanded}
        aria-controls={regionId}
        onClick={onToggle}
        className={cn(
          "flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-[11px] font-medium uppercase tracking-wide text-ink/35",
          "hover:bg-ink/[0.04] hover:text-ink/50",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal/60"
        )}
      >
        <span className="truncate">{label}</span>
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 shrink-0 transition-transform duration-150",
            expanded && "rotate-90",
            reducedMotion && "transition-none"
          )}
          aria-hidden
        />
      </button>
      <div
        id={regionId}
        role="region"
        aria-labelledby={`${regionId}-trigger`}
        className={cn(
          "grid transition-[grid-template-rows] duration-200 ease-out",
          reducedMotion && "transition-none",
          expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        )}
      >
        <div className="overflow-hidden">
          <div className="flex flex-col gap-0.5 border-l border-ink/[0.06] pl-2 ml-2.5">
            {items.map((item) => (
              <SecondaryNavLink key={item.id} item={item} ctx={ctx} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
