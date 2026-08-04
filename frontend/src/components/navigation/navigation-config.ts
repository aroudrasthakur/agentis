import { Bot, LayoutGrid, Shield } from "lucide-react";
import type { NavigationSection, RouteMatchContext } from "./navigation-types";
import { NavPermissions } from "./navigation-permissions";

const AGENT_DESCRIPTION_PATH =
  /^\/dashboard\/guild\/agents\/[^/]+\/description(\/|$)/;
const AGENT_SETUP_PATH = /^\/dashboard\/guild\/agents\/[^/]+\/setup(\/|$)/;
const GUILD_ROLES_PATH = /^\/dashboard\/guild\/roles(\/|$)/;

function guildAgentsPath(ctx: RouteMatchContext): boolean {
  const { pathname, search } = ctx;
  return (
    pathname.startsWith("/dashboard/guild") &&
    !pathname.startsWith("/dashboard/guild/agent-types") &&
    pathname !== "/dashboard/guild/agents/descriptions" &&
    !AGENT_DESCRIPTION_PATH.test(pathname) &&
    !GUILD_ROLES_PATH.test(pathname) &&
    search.get("create") !== "agent"
  );
}

export const NAV_SECTIONS: NavigationSection[] = [
  {
    id: "gatherings",
    label: "Gatherings",
    icon: LayoutGrid,
    matchSection: ({ pathname }) =>
      pathname === "/dashboard" ||
      pathname.startsWith("/dashboard/gatherings") ||
      pathname.startsWith("/gathering/") ||
      pathname.startsWith("/session/"),
    groups: [
      {
        id: "gatherings-main",
        items: [
          {
            id: "gatherings-overview",
            label: "Overview",
            href: "/dashboard",
            match: ({ pathname }) => pathname === "/dashboard",
          },
          {
            id: "gatherings-create",
            label: "Create gathering",
            href: "/dashboard/gatherings/new",
            match: ({ pathname }) => pathname === "/dashboard/gatherings/new",
          },
        ],
      },
    ],
  },
  {
    id: "agents",
    label: "Agents",
    icon: Bot,
    matchSection: ({ pathname }) =>
      pathname.startsWith("/dashboard/guild") || pathname === "/agents",
    groups: [
      {
        id: "agents-workspace",
        label: "Workspace",
        items: [
          {
            id: "agents-guild",
            label: "Guild",
            href: "/dashboard/guild",
            match: guildAgentsPath,
          },
          {
            id: "agents-descriptions",
            label: "Agent descriptions",
            href: "/dashboard/guild/agents/descriptions",
            match: ({ pathname }) =>
              pathname === "/dashboard/guild/agents/descriptions" ||
              AGENT_DESCRIPTION_PATH.test(pathname) ||
              AGENT_SETUP_PATH.test(pathname),
          },
          {
            id: "agents-create",
            label: "Create agent",
            href: "/dashboard/guild?create=agent",
            match: ({ pathname, search }) =>
              pathname.startsWith("/dashboard/guild") && search.get("create") === "agent",
          },
        ],
      },
      {
        id: "agents-types",
        label: "Types",
        items: [
          {
            id: "agents-agent-types",
            label: "Agent types",
            href: "/dashboard/guild/agent-types",
            permission: NavPermissions.AGENT_TYPE_LIST,
            match: ({ pathname }) => pathname.startsWith("/dashboard/guild/agent-types"),
          },
        ],
      },
      {
        id: "agents-directory",
        label: "Directory",
        items: [
          {
            id: "agents-registry",
            label: "Agent registry",
            href: "/agents",
            match: ({ pathname }) => pathname === "/agents",
          },
        ],
      },
    ],
  },
  {
    id: "administration",
    label: "Administration",
    icon: Shield,
    matchSection: ({ pathname }) =>
      GUILD_ROLES_PATH.test(pathname) || pathname.startsWith("/dashboard/profile"),
    groups: [
      {
        id: "admin-access",
        label: "Access control",
        items: [
          {
            id: "admin-roles",
            label: "Roles",
            href: "/dashboard/guild/roles",
            permission: NavPermissions.ROLE_LIST,
            match: ({ pathname }) => GUILD_ROLES_PATH.test(pathname),
          },
        ],
      },
      {
        id: "admin-account",
        label: "Account",
        items: [
          {
            id: "admin-profile",
            label: "Profile",
            href: "/dashboard/profile",
            match: ({ pathname }) => pathname.startsWith("/dashboard/profile"),
          },
        ],
      },
    ],
  },
];
