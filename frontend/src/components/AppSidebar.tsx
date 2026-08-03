"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Bot,
  FileText,
  LayoutGrid,
  Library,
  LogOut,
  Plus,
  Shield,
  Shapes,
  User,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { clearAuth, getStoredUser } from "@/lib/auth";
import { useEffect, useState } from "react";

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  isActive?: (ctx: { pathname: string; search: URLSearchParams }) => boolean;
};

const PRIMARY: NavItem[] = [
  {
    label: "Gatherings",
    href: "/dashboard",
    icon: LayoutGrid,
    isActive: ({ pathname }) =>
      pathname === "/dashboard" || pathname.startsWith("/gathering/"),
  },
  {
    label: "Create gathering",
    href: "/dashboard?create=gathering",
    icon: Plus,
    isActive: ({ pathname, search }) =>
      pathname === "/dashboard" && search.get("create") === "gathering",
  },
];

const AGENT_DESCRIPTION_PATH =
  /^\/dashboard\/guild\/agents\/[^/]+\/description(\/|$)/;
const GUILD_ROLES_PATH = /^\/dashboard\/guild\/roles(\/|$)/;

const AGENTS: NavItem[] = [
  {
    label: "Guild",
    href: "/dashboard/guild",
    icon: Users,
    isActive: ({ pathname, search }) =>
      pathname.startsWith("/dashboard/guild") &&
      !pathname.startsWith("/dashboard/guild/agent-types") &&
      pathname !== "/dashboard/guild/agents/descriptions" &&
      !AGENT_DESCRIPTION_PATH.test(pathname) &&
      !GUILD_ROLES_PATH.test(pathname) &&
      search.get("create") !== "agent",
  },
  {
    label: "Agent descriptions",
    href: "/dashboard/guild/agents/descriptions",
    icon: FileText,
    isActive: ({ pathname }) =>
      pathname === "/dashboard/guild/agents/descriptions" ||
      AGENT_DESCRIPTION_PATH.test(pathname),
  },
  {
    label: "Roles",
    href: "/dashboard/guild/roles",
    icon: Shield,
    isActive: ({ pathname }) => GUILD_ROLES_PATH.test(pathname),
  },
  {
    label: "Agent types",
    href: "/dashboard/guild/agent-types",
    icon: Shapes,
    isActive: ({ pathname }) => pathname.startsWith("/dashboard/guild/agent-types"),
  },
  {
    label: "Create agent",
    href: "/dashboard/guild?create=agent",
    icon: Bot,
    isActive: ({ pathname, search }) =>
      pathname.startsWith("/dashboard/guild") && search.get("create") === "agent",
  },
  {
    label: "Agent registry",
    href: "/agents",
    icon: Library,
    isActive: ({ pathname }) => pathname === "/agents",
  },
];

const ACCOUNT: NavItem[] = [
  {
    label: "Profile",
    href: "/dashboard/profile",
    icon: User,
    isActive: ({ pathname }) => pathname.startsWith("/dashboard/profile"),
  },
];

function NavLink({
  item,
  pathname,
  search,
}: {
  item: NavItem;
  pathname: string;
  search: URLSearchParams;
}) {
  const Icon = item.icon;
  const active = item.isActive
    ? item.isActive({ pathname, search })
    : pathname === item.href.split("?")[0];

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
        active
          ? "border border-teal/25 bg-teal/15 text-ink"
          : "border border-transparent text-ink/60 hover:bg-ink/5 hover:text-ink"
      )}
    >
      <Icon className="h-4 w-4 shrink-0 opacity-80" />
      <span>{item.label}</span>
    </Link>
  );
}

function AppSidebarInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    setName(getStoredUser()?.display_name ?? null);
  }, [pathname]);

  return (
    <aside className="flex w-[15.5rem] shrink-0 flex-col border-r border-ink/[0.08] bg-surface/40 px-3 py-5">
      <p className="px-3 text-[10px] font-medium uppercase tracking-[0.22em] text-ink/35">
        Workspace
      </p>
      <nav className="mt-2 flex flex-col gap-1">
        {PRIMARY.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            pathname={pathname}
            search={searchParams}
          />
        ))}
      </nav>

      <p className="mt-8 px-3 text-[10px] font-medium uppercase tracking-[0.22em] text-ink/35">
        Agents
      </p>
      <nav className="mt-2 flex flex-col gap-1">
        {AGENTS.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            pathname={pathname}
            search={searchParams}
          />
        ))}
      </nav>

      <p className="mt-8 px-3 text-[10px] font-medium uppercase tracking-[0.22em] text-ink/35">
        Account
      </p>
      <nav className="mt-2 flex flex-col gap-1">
        {ACCOUNT.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            pathname={pathname}
            search={searchParams}
          />
        ))}
      </nav>

      <div className="mt-auto border-t border-ink/[0.08] pt-4">
        {name && (
          <p className="mb-3 truncate px-3 text-xs text-ink/45" title={name}>
            {name}
          </p>
        )}
        <button
          type="button"
          onClick={() => {
            clearAuth();
            router.replace("/login");
          }}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink/55 transition hover:bg-ink/5 hover:text-ink"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sign out
        </button>
      </div>
    </aside>
  );
}

export function AppSidebar() {
  return <AppSidebarInner />;
}

export function isWorkspacePath(pathname: string) {
  return (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/gathering/") ||
    pathname.startsWith("/session/") ||
    pathname === "/agents"
  );
}
