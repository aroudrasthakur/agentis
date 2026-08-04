"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { Gathering } from "@/lib/api";
import { api } from "@/lib/api";
import { getStoredUser, isLoggedIn } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const router = useRouter();
  const [gatherings, setGatherings] = useState<Gathering[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);

  useEffect(() => {
    setDisplayName(getStoredUser()?.display_name ?? null);
  }, []);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void (async () => {
      try {
        setGatherings(await api.listGatherings());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load gatherings");
      }
    })();
  }, [router]);

  return (
    <main className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Dashboard</p>
          <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">
            Your Gatherings
          </h1>
          <p className="mt-2 max-w-lg text-sm text-ink/55">
            Workspaces for training agents and multi-agent sessions.
            {displayName ? ` Signed in as ${displayName}.` : null}
          </p>
        </div>
        <Button asChild variant="teal">
          <Link href="/dashboard/gatherings/new">Create gathering</Link>
        </Button>
      </div>

      {error && <p className="mb-4 text-sm text-coral">{error}</p>}

      {gatherings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ink/15 bg-surface/50 px-8 py-16 text-center">
          <p className="font-display text-2xl text-ink">No gatherings yet</p>
          <p className="mt-2 text-sm text-ink/50">
            Create a workspace, invite people, and add agents from the Guild.
          </p>
          <Button asChild className="mt-6" variant="teal">
            <Link href="/dashboard/gatherings/new">Create your first gathering</Link>
          </Button>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {gatherings.map((gathering) => (
            <li key={gathering.id}>
              <Link
                href={`/gathering/${gathering.id}`}
                className="block rounded-xl border border-ink/10 bg-surface/70 px-5 py-5 transition hover:border-teal/40 hover:bg-surface"
              >
                <h2 className="font-display text-xl text-ink">{gathering.name}</h2>
                {gathering.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-ink/50">
                    {gathering.description}
                  </p>
                )}
                <p className="mt-4 text-[11px] uppercase tracking-[0.16em] text-ink/35">
                  {gathering.session_count} sessions · {gathering.agent_count} agents ·{" "}
                  {gathering.member_count} people
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
