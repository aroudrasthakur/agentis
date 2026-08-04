"use client";

import Link from "next/link";
import { LogOut, PanelLeftClose, PanelLeftOpen, User } from "lucide-react";
import type { NavigationSection, RouteMatchContext } from "./navigation-types";
import { PrimaryNavItem } from "./primary-nav-item";
import { NavGroupBlock } from "./secondary-nav-panel";
import { SessionRoleSelector } from "@/components/authorization/SessionRoleSelector";
import { cn } from "@/lib/utils";

type PrimaryNavRailProps = {
  sections: NavigationSection[];
  activeSectionId: string | null;
  onSelectSection: (sectionId: string) => void;
  onToggleCollapse: () => void;
  onProfile: () => void;
  secondaryCollapsed: boolean;
  showTooltips: boolean;
  displayName: string | null;
  onSignOut: () => void;
};

export function PrimaryNavRail({
  sections,
  activeSectionId,
  onSelectSection,
  onToggleCollapse,
  onProfile,
  secondaryCollapsed,
  showTooltips,
  displayName,
  onSignOut,
}: PrimaryNavRailProps) {
  return (
    <nav
      aria-label="Primary"
      className="flex h-full w-[var(--primary-nav-width)] flex-col items-center border-r border-ink/[0.08] bg-surface/50"
    >
      <div className="flex h-12 w-full shrink-0 items-center justify-center border-b border-ink/[0.08]">
        <Link
          href="/dashboard"
          className="flex h-9 w-9 items-center justify-center rounded-lg font-display text-lg text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal/60"
          aria-label="Agentis home"
        >
          A
        </Link>
      </div>

      <div className="flex flex-1 flex-col items-center gap-1 py-3">
        {sections.map((section) => (
          <PrimaryNavItem
            key={section.id}
            label={section.label}
            icon={section.icon}
            active={activeSectionId === section.id}
            showTooltip={showTooltips}
            onClick={() => onSelectSection(section.id)}
          />
        ))}
      </div>

      <div className="mt-auto flex w-full flex-col items-center gap-1 border-t border-ink/[0.08] py-3">
        <PrimaryNavItem
          label={secondaryCollapsed ? "Expand panel" : "Collapse panel"}
          icon={secondaryCollapsed ? PanelLeftOpen : PanelLeftClose}
          active={false}
          showTooltip={showTooltips}
          onClick={onToggleCollapse}
        />
        <SessionRoleSelector showTooltip={showTooltips} />
        <PrimaryNavItem
          label={displayName ? `Profile — ${displayName}` : "Profile"}
          icon={User}
          active={false}
          showTooltip={showTooltips}
          onClick={onProfile}
        />
        <button
          type="button"
          onClick={onSignOut}
          aria-label="Sign out"
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg text-ink/45 transition-colors hover:bg-ink/[0.06] hover:text-ink",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal/60"
          )}
        >
          <LogOut className="h-[21px] w-[21px]" strokeWidth={1.75} aria-hidden />
        </button>
      </div>
    </nav>
  );
}

export function SecondaryNavPanelContent({
  section,
  ctx,
  permissionsLoading,
  expandedGroupIds,
  isGroupExpanded,
  onToggleGroup,
  onNavigate,
  reducedMotion,
}: {
  section: NavigationSection | undefined;
  ctx: RouteMatchContext;
  permissionsLoading: boolean;
  expandedGroupIds: string[];
  isGroupExpanded: (id: string) => boolean;
  onToggleGroup: (id: string) => void;
  onNavigate?: () => void;
  reducedMotion: boolean;
}) {
  if (!section) {
    return null;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-ink/[0.08] px-4">
        <h2 className="truncate text-sm font-semibold text-ink">{section.label}</h2>
      </div>
      <div className="scroll-area flex-1 overflow-y-auto px-2 py-3">
        {permissionsLoading ? (
          <p className="px-2.5 text-xs text-ink/45" aria-live="polite">
            Loading navigation…
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {section.groups.map((group) => (
              <NavGroupBlock
                key={group.id}
                groupId={group.id}
                label={group.label}
                items={group.items}
                ctx={ctx}
                expanded={
                  group.label
                    ? isGroupExpanded(group.id) || expandedGroupIds.includes(group.id)
                    : true
                }
                onToggle={() => onToggleGroup(group.id)}
                onNavigate={onNavigate}
                reducedMotion={reducedMotion}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
