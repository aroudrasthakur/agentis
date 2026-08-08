import type {
  NavigationGroup,
  NavigationItem,
  NavigationSection,
  RouteMatchContext,
} from "./navigation-types";

export function isWorkspacePath(pathname: string): boolean {
  return (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/gathering/") ||
    pathname.startsWith("/session/") ||
    pathname === "/agents"
  );
}

export function itemMatches(item: NavigationItem, ctx: RouteMatchContext): boolean {
  if (item.match) {
    return item.match(ctx);
  }
  if (!item.href) {
    return false;
  }
  const base = item.href.split("?")[0];
  if (item.href.includes("?")) {
    const url = new URL(item.href, "http://local");
    let queryMatch = true;
    url.searchParams.forEach((value, key) => {
      if (ctx.search.get(key) !== value) {
        queryMatch = false;
      }
    });
    if (!queryMatch) {
      return false;
    }
    return ctx.pathname === base;
  }
  return ctx.pathname === base;
}

export function findActiveItemId(
  sections: NavigationSection[],
  ctx: RouteMatchContext
): { sectionId: string; itemId: string; groupId: string } | null {
  for (const section of sections) {
    for (const group of section.groups) {
      for (const item of flattenItems(group.items)) {
        if (itemMatches(item, ctx)) {
          return { sectionId: section.id, itemId: item.id, groupId: group.id };
        }
      }
    }
  }
  return null;
}

function flattenItems(items: NavigationItem[]): NavigationItem[] {
  const out: NavigationItem[] = [];
  for (const item of items) {
    out.push(item);
    if (item.children?.length) {
      out.push(...flattenItems(item.children));
    }
  }
  return out;
}

export function resolveSectionId(
  sections: NavigationSection[],
  ctx: RouteMatchContext,
  fallbackSectionId: string | null
): string {
  const active = findActiveItemId(sections, ctx);
  if (active) {
    return active.sectionId;
  }
  for (const section of sections) {
    if (section.matchSection?.(ctx)) {
      return section.id;
    }
  }
  return fallbackSectionId ?? sections[0]?.id ?? "gatherings";
}

export function filterItemByPermission(
  item: NavigationItem,
  can: (key: string) => boolean,
  permissionsReady: boolean
): NavigationItem | null {
  if (item.permission) {
    if (!permissionsReady) {
      return null;
    }
    if (!can(item.permission)) {
      return null;
    }
  }
  const children = item.children
    ?.map((child) => filterItemByPermission(child, can, permissionsReady))
    .filter((c): c is NavigationItem => c !== null);
  if (item.children?.length && (!children || children.length === 0)) {
    return null;
  }
  return { ...item, children: children?.length ? children : undefined };
}

export function filterNavigationSections(
  sections: NavigationSection[],
  can: (key: string) => boolean,
  permissionsReady: boolean
): NavigationSection[] {
  return sections
    .map((section) => {
      if (section.permission) {
        if (!permissionsReady || !can(section.permission)) {
          return null;
        }
      }
      const groups = section.groups
        .map((group) => filterGroup(group, can, permissionsReady))
        .filter((g): g is NavigationGroup => g !== null);
      if (groups.length === 0) {
        return null;
      }
      return { ...section, groups };
    })
    .filter((s): s is NavigationSection => s !== null);
}

function filterGroup(
  group: NavigationGroup,
  can: (key: string) => boolean,
  permissionsReady: boolean
): NavigationGroup | null {
  const items = group.items
    .map((item) => filterItemByPermission(item, can, permissionsReady))
    .filter((i): i is NavigationItem => i !== null);
  if (items.length === 0) {
    return null;
  }
  return { ...group, items };
}

export function collectGroupIdsForActiveRoute(
  sections: NavigationSection[],
  ctx: RouteMatchContext
): string[] {
  const active = findActiveItemId(sections, ctx);
  if (!active) {
    return [];
  }
  return [active.groupId];
}
