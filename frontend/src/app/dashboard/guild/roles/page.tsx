"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { PermissionGate } from "@/components/authorization/PermissionGate";
import { RoleCategoryBadge } from "@/components/authorization/RoleCategoryBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type RoleSummary } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

const GROUP_ORDER = [
  "baseline",
  "system_admin",
  "functional",
  "gathering_access",
  "resource_access",
  "service",
  "legacy",
];

export default function RolesPage() {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) return;
    void (async () => {
      setLoading(true);
      try {
        setRoles(await api.listRoles());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load roles");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, RoleSummary[]>();
    for (const role of roles) {
      const cat = role.category ?? "functional";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(role);
    }
    return GROUP_ORDER.filter((g) => map.has(g)).map((g) => ({ category: g, roles: map.get(g)! }));
  }, [roles]);

  return (
    <main className="mx-auto max-w-5xl px-6 pb-20 pt-4">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Access control</p>
          <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Roles</h1>
          <p className="mt-2 max-w-2xl text-sm text-ink/55">
            Layered roles: baseline and admin roles, functional job roles, and Gathering or resource
            access roles. This role inherits / roles that inherit this role are shown on each detail
            page.
          </p>
        </div>
        <PermissionGate permission="role.create">
          <Button variant="outline" size="sm" disabled title="Use the role editor API to create roles">
            New role (API)
          </Button>
        </PermissionGate>
      </div>

      {error && <p className="mb-4 text-sm text-coral">{error}</p>}
      {loading ? (
        <p className="text-sm text-ink/45">Loading roles…</p>
      ) : roles.length === 0 ? (
        <p className="text-sm text-ink/45">No roles visible for your account.</p>
      ) : (
        <div className="space-y-10">
          {grouped.map(({ category, roles: groupRoles }) => (
            <section key={category}>
              <h2 className="mb-3 font-display text-lg text-ink">
                <RoleCategoryBadge category={category} />
              </h2>
              <ul className="space-y-3">
                {groupRoles.map((role) => (
                  <li
                    key={role.id}
                    className="rounded-xl border border-ink/10 bg-surface/70 px-4 py-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-medium text-ink">{role.name}</h3>
                      <Badge className="bg-ink/5 text-ink/60">{role.kind}</Badge>
                      {role.is_default && (
                        <Badge className="bg-teal-soft text-teal-deep">Default</Badge>
                      )}
                      {role.is_managed && (
                        <Badge className="bg-ink/10 text-ink/50">Managed</Badge>
                      )}
                      {role.status === "deprecated" && (
                        <Badge className="bg-coral/10 text-coral">Deprecated</Badge>
                      )}
                    </div>
                    {role.description && (
                      <p className="mt-2 text-sm text-ink/60">{role.description}</p>
                    )}
                    <p className="mt-2 text-xs text-ink/45">
                      {role.member_count} member{role.member_count === 1 ? "" : "s"} ·{" "}
                      {role.permissions.length} direct permission rule
                      {role.permissions.length === 1 ? "" : "s"}
                      {role.workspace_id ? ` · Gathering ${role.workspace_id.slice(0, 8)}…` : ""}
                    </p>
                    <PermissionGate permission="role.read">
                      <Link
                        className="mt-3 inline-block text-sm text-teal hover:underline"
                        href={`/dashboard/guild/roles/${role.id}`}
                      >
                        View details
                      </Link>
                    </PermissionGate>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
      <Link className="mt-8 inline-block text-sm text-ink/45 hover:text-ink" href="/dashboard/guild">
        ← Guild
      </Link>
    </main>
  );
}
