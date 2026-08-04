import { describe, expect, it } from "vitest";
import { NAV_SECTIONS } from "@/components/navigation/navigation-config";
import {
  filterNavigationSections,
  findActiveItemId,
  isWorkspacePath,
  itemMatches,
  resolveSectionId,
} from "@/components/navigation/navigation-utils";

function ctx(pathname: string, search = "") {
  return { pathname, search: new URLSearchParams(search) };
}

describe("isWorkspacePath", () => {
  it("includes dashboard and agents registry", () => {
    expect(isWorkspacePath("/dashboard")).toBe(true);
    expect(isWorkspacePath("/dashboard/guild/roles")).toBe(true);
    expect(isWorkspacePath("/agents")).toBe(true);
    expect(isWorkspacePath("/gathering/abc")).toBe(true);
    expect(isWorkspacePath("/session/abc")).toBe(true);
    expect(isWorkspacePath("/login")).toBe(false);
  });
});

describe("route matching", () => {
  it("highlights guild and query-based create links", () => {
    const guild = NAV_SECTIONS.find((s) => s.id === "agents")!.groups[0].items[0];
    expect(itemMatches(guild, ctx("/dashboard/guild"))).toBe(true);
    expect(itemMatches(guild, ctx("/dashboard/guild", "create=agent"))).toBe(false);

    const create = NAV_SECTIONS.find((s) => s.id === "agents")!.groups[0].items[2];
    expect(itemMatches(create, ctx("/dashboard/guild", "create=agent"))).toBe(true);
  });

  it("resolves section from pathname", () => {
    expect(resolveSectionId(NAV_SECTIONS, ctx("/dashboard/guild"), null)).toBe("agents");
    expect(resolveSectionId(NAV_SECTIONS, ctx("/dashboard"), null)).toBe("gatherings");
    expect(resolveSectionId(NAV_SECTIONS, ctx("/dashboard/gatherings/new"), null)).toBe(
      "gatherings"
    );
  });

  it("separates gathering overview from the create page", () => {
    const [overview, create] = NAV_SECTIONS.find((s) => s.id === "gatherings")!.groups[0].items;
    expect(itemMatches(overview, ctx("/dashboard"))).toBe(true);
    expect(itemMatches(overview, ctx("/dashboard/gatherings/new"))).toBe(false);
    expect(itemMatches(create, ctx("/dashboard/gatherings/new"))).toBe(true);
    expect(itemMatches(create, ctx("/dashboard"))).toBe(false);
  });

  it("finds active item for roles", () => {
    const active = findActiveItemId(NAV_SECTIONS, ctx("/dashboard/guild/roles/abc"));
    expect(active?.sectionId).toBe("administration");
    expect(active?.itemId).toBe("admin-roles");
  });
});

describe("permission filtering", () => {
  const can = (key: string) => key === "role.list";

  it("hides role-gated items until permissions ready", () => {
    const loading = filterNavigationSections(NAV_SECTIONS, can, false);
    const admin = loading.find((s) => s.id === "administration");
    expect(admin?.groups.some((g) => g.items.some((i) => i.id === "admin-roles"))).toBe(false);
  });

  it("shows roles when permitted", () => {
    const ready = filterNavigationSections(NAV_SECTIONS, can, true);
    const admin = ready.find((s) => s.id === "administration");
    expect(admin?.groups.some((g) => g.items.some((i) => i.id === "admin-roles"))).toBe(true);
  });

  it("keeps profile when role.list is denied", () => {
    const denied = filterNavigationSections(NAV_SECTIONS, () => false, true);
    const admin = denied.find((s) => s.id === "administration");
    expect(admin).toBeDefined();
    expect(admin?.groups.some((g) => g.items.some((i) => i.id === "admin-profile"))).toBe(true);
    expect(admin?.groups.some((g) => g.items.some((i) => i.id === "admin-roles"))).toBe(false);
  });
});

describe("sidebar persistence key", () => {
  it("uses stable storage key", async () => {
    const { SIDEBAR_STORAGE_KEY } = await import("@/components/navigation/navigation-types");
    expect(SIDEBAR_STORAGE_KEY).toBe("agentis-sidebar-v1");
  });
});
