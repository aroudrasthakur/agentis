"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Menu, X } from "lucide-react";
import { NAV_SECTIONS } from "./navigation-config";
import {
  collectGroupIdsForActiveRoute,
  filterNavigationSections,
  resolveSectionId,
} from "./navigation-utils";
import { useSidebarState } from "./use-sidebar-state";
import { useNavigationBreakpoint, usePrefersReducedMotion } from "./use-navigation-breakpoint";
import { PrimaryNavRail, SecondaryNavPanelContent } from "./primary-nav-rail";
import { usePermissions } from "@/hooks/usePermission";
import { clearAuth, getStoredUser } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function AppSidebarNavigation() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { can, loading: permissionsLoading } = usePermissions();
  const breakpoint = useNavigationBreakpoint();
  const reducedMotion = usePrefersReducedMotion();
  const mobileTriggerRef = useRef<HTMLButtonElement>(null);

  const ctx = useMemo(
    () => ({ pathname, search: searchParams }),
    [pathname, searchParams]
  );

  const filteredSections = useMemo(
    () => filterNavigationSections(NAV_SECTIONS, can, !permissionsLoading),
    [can, permissionsLoading]
  );

  const routeSectionId = useMemo(
    () => resolveSectionId(filteredSections, ctx, null),
    [filteredSections, ctx]
  );

  const [pickedSectionId, setPickedSectionId] = useState<string | null>(null);

  useEffect(() => {
    setPickedSectionId(routeSectionId);
  }, [routeSectionId]);

  const activeSectionId = pickedSectionId ?? routeSectionId;

  const sidebar = useSidebarState(activeSectionId);

  const activeSection = filteredSections.find((s) => s.id === activeSectionId);

  const autoExpandIds = useMemo(
    () => collectGroupIdsForActiveRoute(filteredSections, ctx),
    [filteredSections, ctx]
  );

  useEffect(() => {
    sidebar.ensureGroupsExpanded(autoExpandIds);
  }, [autoExpandIds, sidebar]);

  const isMobile = breakpoint === "mobile";
  const isTablet = breakpoint === "tablet";
  const showSecondaryInline =
    !isMobile && !isTablet && sidebar.isSecondaryPanelOpen && sidebar.hydrated;
  const showSecondaryOverlay =
    isTablet && sidebar.isTabletOverlayOpen && sidebar.isSecondaryPanelOpen;
  const showTooltips = !sidebar.isSecondaryPanelOpen || isMobile;

  const handleSelectSection = useCallback(
    (sectionId: string) => {
      if (sectionId === activeSectionId && !isMobile) {
        if (isTablet) {
          sidebar.setIsTabletOverlayOpen((open) => !open);
        } else {
          sidebar.toggleSecondaryPanel();
        }
        return;
      }
      setPickedSectionId(sectionId);
      sidebar.setSecondaryPanelOpen(true);
      if (isTablet) {
        sidebar.setIsTabletOverlayOpen(true);
      }
      if (isMobile) {
        sidebar.setIsMobileDrawerOpen(true);
      }
    },
    [activeSectionId, isMobile, isTablet, sidebar]
  );

  const closeMobileDrawer = useCallback(() => {
    sidebar.setIsMobileDrawerOpen(false);
    mobileTriggerRef.current?.focus();
  }, [sidebar]);

  const closeTabletOverlay = useCallback(() => {
    sidebar.setIsTabletOverlayOpen(false);
  }, [sidebar]);

  const onNavigate = useCallback(() => {
    if (isMobile) {
      closeMobileDrawer();
    }
    if (isTablet) {
      closeTabletOverlay();
    }
  }, [closeMobileDrawer, closeTabletOverlay, isMobile, isTablet]);

  useEffect(() => {
    if (!isMobile || !sidebar.isMobileDrawerOpen) {
      return;
    }
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeMobileDrawer();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [isMobile, sidebar.isMobileDrawerOpen, closeMobileDrawer]);

  useEffect(() => {
    if (!showSecondaryOverlay) {
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeTabletOverlay();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showSecondaryOverlay, closeTabletOverlay]);

  const [displayName, setDisplayName] = useState<string | null>(null);

  useEffect(() => {
    setDisplayName(getStoredUser()?.display_name ?? null);
  }, []);

  const signOut = () => {
    clearAuth();
    router.replace("/login");
  };

  const secondaryPanel = (
    <SecondaryNavPanelContent
      section={activeSection}
      ctx={ctx}
      permissionsLoading={permissionsLoading}
      expandedGroupIds={autoExpandIds}
      isGroupExpanded={sidebar.isGroupExpanded}
      onToggleGroup={sidebar.toggleGroupExpanded}
      onNavigate={onNavigate}
      reducedMotion={reducedMotion}
    />
  );

  if (isMobile) {
    return (
      <>
        <button
          ref={mobileTriggerRef}
          type="button"
          className="fixed bottom-4 left-4 z-40 flex h-11 w-11 items-center justify-center rounded-full border border-ink/10 bg-surface-elevated text-ink shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal/60"
          aria-label="Open navigation menu"
          aria-expanded={sidebar.isMobileDrawerOpen}
          onClick={() => sidebar.setIsMobileDrawerOpen(true)}
        >
          <Menu className="h-5 w-5" aria-hidden />
        </button>
        {sidebar.isMobileDrawerOpen && (
          <div className="fixed inset-0 z-50 flex" role="presentation">
            <button
              type="button"
              className="absolute inset-0 bg-scrim/60"
              aria-label="Close navigation menu"
              onClick={closeMobileDrawer}
            />
            <div
              className={cn(
                "relative flex h-full w-[min(100vw,320px)] bg-surface shadow-xl",
                !reducedMotion && "transition-transform duration-200"
              )}
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
            >
              <PrimaryNavRail
                sections={filteredSections}
                activeSectionId={activeSectionId}
                onSelectSection={handleSelectSection}
                onToggleCollapse={sidebar.toggleSecondaryPanel}
                onProfile={() => {
                  router.push("/dashboard/profile");
                  closeMobileDrawer();
                }}
                secondaryCollapsed={false}
                showTooltips={false}
                displayName={displayName}
                onSignOut={signOut}
              />
              <div className="min-w-0 flex-1 border-l border-ink/[0.08]">{secondaryPanel}</div>
              <button
                type="button"
                className="absolute right-3 top-3 rounded-md p-2 text-ink/60 hover:bg-ink/5 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal/60"
                aria-label="Close menu"
                onClick={closeMobileDrawer}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <PrimaryNavRail
        sections={filteredSections}
        activeSectionId={activeSectionId}
        onSelectSection={handleSelectSection}
        onToggleCollapse={sidebar.toggleSecondaryPanel}
        onProfile={() => router.push("/dashboard/profile")}
        secondaryCollapsed={!sidebar.isSecondaryPanelOpen}
        showTooltips={showTooltips}
        displayName={displayName}
        onSignOut={signOut}
      />
      <aside
        aria-label="Section navigation"
        data-collapsed={!showSecondaryInline}
        className={cn(
          "relative h-full overflow-hidden border-r border-ink/[0.08] bg-surface/35 transition-[width,opacity] ease-out",
          reducedMotion ? "duration-0" : "duration-200",
          showSecondaryInline ? "w-[var(--secondary-nav-width)] opacity-100" : "w-0 opacity-0"
        )}
      >
        <div className="h-full w-[var(--secondary-nav-width)]">{secondaryPanel}</div>
      </aside>
      {showSecondaryOverlay && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-30 bg-scrim/50"
            aria-label="Close section navigation"
            onClick={closeTabletOverlay}
          />
          <aside
            className={cn(
              "fixed left-[var(--primary-nav-width)] top-0 z-40 h-screen w-[var(--secondary-nav-width)] border-r border-ink/[0.08] bg-surface shadow-lg",
              !reducedMotion && "transition-transform duration-200"
            )}
            aria-label="Section navigation"
          >
            {secondaryPanel}
          </aside>
        </>
      )}
    </>
  );
}
