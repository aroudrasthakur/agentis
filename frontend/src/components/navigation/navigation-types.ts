import type { LucideIcon } from "lucide-react";

export type RouteMatchContext = {
  pathname: string;
  search: URLSearchParams;
};

export type NavigationItem = {
  id: string;
  label: string;
  href?: string;
  permission?: string;
  children?: NavigationItem[];
  match?: (ctx: RouteMatchContext) => boolean;
};

export type NavigationGroup = {
  id: string;
  label?: string;
  items: NavigationItem[];
};

export type NavigationSection = {
  id: string;
  label: string;
  icon: LucideIcon;
  permission?: string;
  groups: NavigationGroup[];
  matchSection?: (ctx: RouteMatchContext) => boolean;
};

export type SidebarPersistedState = {
  isSecondaryPanelOpen: boolean;
  expandedGroupIds: string[];
};

export type SidebarState = SidebarPersistedState & {
  activeSectionId: string | null;
  isMobileDrawerOpen: boolean;
  isTabletOverlayOpen: boolean;
};

export const SIDEBAR_STORAGE_KEY = "agentis-sidebar-v1";
