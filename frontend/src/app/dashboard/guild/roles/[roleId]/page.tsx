"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { RoleCategoryBadge } from "@/components/authorization/RoleCategoryBadge";
import { Badge } from "@/components/ui/badge";
import { api, type RoleSummary } from "@/lib/api";

export default function RoleDetailPage() {
  const params = useParams<{ roleId: string }>();
  const [role, setRole] = useState<RoleSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setRole(await api.getRole(params.roleId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load role");
      }
    })();
  }, [params.roleId]);

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-sm text-coral">{error}</p>
      </main>
    );
  }

  if (!role) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-sm text-ink/45">Loading…</p>
      </main>
    );
  }

  const grouped = role.permissions.reduce<Record<string, typeof role.permissions>>((acc, row) => {
    const prefix = row.permission_key.split(".")[0];
    acc[prefix] = acc[prefix] ?? [];
    acc[prefix].push(row);
    return acc;
  }, {});

  return (
    <main className="mx-auto max-w-4xl px-6 pb-20 pt-4">
      <Link className="text-xs text-ink/45 hover:text-ink" href="/dashboard/guild/roles">
        ← Roles
      </Link>
      <h1 className="mt-3 font-display text-3xl text-ink">{role.name}</h1>
      <div className="mt-2 flex flex-wrap gap-2">
        <Badge>{role.kind}</Badge>
        <RoleCategoryBadge category={role.category} />
        <Badge className="bg-ink/5">{role.status}</Badge>
        {role.is_managed && <Badge className="bg-ink/10">Managed</Badge>}
      </div>
      {role.description && <p className="mt-4 text-sm text-ink/60">{role.description}</p>}

      {(role.inherited_role_ids?.length ?? 0) > 0 && (
        <section className="mt-6">
          <h2 className="font-display text-lg text-ink">This role inherits</h2>
          <p className="mt-1 text-xs text-ink/45">
            Roles listed here are inherited via parent_role_id (privileges flow from parent to
            assigned child role).
          </p>
          <ul className="mt-2 font-mono text-xs text-ink/70">
            {role.inherited_role_ids!.map((id) => (
              <li key={id}>
                <Link className="text-teal hover:underline" href={`/dashboard/guild/roles/${id}`}>
                  {id}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(role.inheriting_role_ids?.length ?? 0) > 0 && (
        <section className="mt-6">
          <h2 className="font-display text-lg text-ink">Roles that inherit this role</h2>
          <ul className="mt-2 font-mono text-xs text-ink/70">
            {role.inheriting_role_ids!.map((id) => (
              <li key={id}>
                <Link className="text-teal hover:underline" href={`/dashboard/guild/roles/${id}`}>
                  {id}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-8">
        <h2 className="font-display text-xl text-ink">Direct permissions</h2>
        <div className="mt-4 space-y-4">
          {Object.entries(grouped).map(([group, rows]) => (
            <div key={group} className="rounded-lg border border-ink/10 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.14em] text-ink/40">{group}</p>
              <ul className="mt-2 space-y-1 text-sm text-ink/70">
                {rows.map((row) => (
                  <li key={`${row.permission_key}-${row.scope}-${row.effect}`}>
                    <span className="font-mono text-xs">{row.permission_key}</span>
                    <span className="text-ink/45"> · {row.effect} · {row.scope}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
