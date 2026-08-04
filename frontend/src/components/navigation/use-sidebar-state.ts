"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { SidebarPersistedState } from "./navigation-types";
import { SIDEBAR_STORAGE_KEY } from "./navigation-types";

const DEFAULT_PERSISTED: SidebarPersistedState = {
  isSecondaryPanelOpen: true,
  expandedGroupIds: [],
};

function readPersisted(): SidebarPersistedState {
  if (typeof window === "undefined") {
    return DEFAULT_PERSISTED;
  }
  try {
    const raw = localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_PERSISTED;
    }
    const parsed = JSON.parse(raw) as Partial<SidebarPersistedState>;
    return {
      isSecondaryPanelOpen:
        parsed.isSecondaryPanelOpen ?? DEFAULT_PERSISTED.isSecondaryPanelOpen,
      expandedGroupIds: Array.isArray(parsed.expandedGroupIds)
        ? parsed.expandedGroupIds
        : DEFAULT_PERSISTED.expandedGroupIds,
    };
  } catch {
    return DEFAULT_PERSISTED;
  }
}

function writePersisted(state: SidebarPersistedState) {
  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota errors */
  }
}

export function useSidebarState(activeSectionId: string | null) {
  const [hydrated, setHydrated] = useState(false);
  const [isSecondaryPanelOpen, setIsSecondaryPanelOpen] = useState(true);
  const [expandedGroupIds, setExpandedGroupIds] = useState<string[]>([]);
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const [isTabletOverlayOpen, setIsTabletOverlayOpen] = useState(false);

  useEffect(() => {
    const persisted = readPersisted();
    setIsSecondaryPanelOpen(persisted.isSecondaryPanelOpen);
    setExpandedGroupIds(persisted.expandedGroupIds);
    setHydrated(true);
  }, []);

  const persist = useCallback(
    (next: Partial<SidebarPersistedState>) => {
      const merged = {
        isSecondaryPanelOpen: next.isSecondaryPanelOpen ?? isSecondaryPanelOpen,
        expandedGroupIds: next.expandedGroupIds ?? expandedGroupIds,
      };
      writePersisted(merged);
    },
    [expandedGroupIds, isSecondaryPanelOpen]
  );

  const toggleSecondaryPanel = useCallback(() => {
    setIsSecondaryPanelOpen((open) => {
      const next = !open;
      persist({ isSecondaryPanelOpen: next });
      return next;
    });
  }, [persist]);

  const setSecondaryPanelOpen = useCallback(
    (open: boolean) => {
      setIsSecondaryPanelOpen(open);
      persist({ isSecondaryPanelOpen: open });
    },
    [persist]
  );

  const toggleGroupExpanded = useCallback(
    (groupId: string) => {
      setExpandedGroupIds((ids) => {
        const next = ids.includes(groupId)
          ? ids.filter((id) => id !== groupId)
          : [...ids, groupId];
        persist({ expandedGroupIds: next });
        return next;
      });
    },
    [persist]
  );

  const ensureGroupsExpanded = useCallback(
    (groupIds: string[]) => {
      if (groupIds.length === 0) {
        return;
      }
      setExpandedGroupIds((ids) => {
        const merged = [...ids];
        let changed = false;
        for (const id of groupIds) {
          if (!merged.includes(id)) {
            merged.push(id);
            changed = true;
          }
        }
        if (changed) {
          persist({ expandedGroupIds: merged });
        }
        return changed ? merged : ids;
      });
    },
    [persist]
  );

  const isGroupExpanded = useCallback(
    (groupId: string) => expandedGroupIds.includes(groupId),
    [expandedGroupIds]
  );

  return useMemo(
    () => ({
      hydrated,
      isSecondaryPanelOpen,
      toggleSecondaryPanel,
      setSecondaryPanelOpen,
      expandedGroupIds,
      toggleGroupExpanded,
      ensureGroupsExpanded,
      isGroupExpanded,
      isMobileDrawerOpen,
      setIsMobileDrawerOpen,
      isTabletOverlayOpen,
      setIsTabletOverlayOpen,
      activeSectionId,
    }),
    [
      hydrated,
      isSecondaryPanelOpen,
      toggleSecondaryPanel,
      setSecondaryPanelOpen,
      expandedGroupIds,
      toggleGroupExpanded,
      ensureGroupsExpanded,
      isGroupExpanded,
      isMobileDrawerOpen,
      isTabletOverlayOpen,
      activeSectionId,
    ]
  );
}
