"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  AGENT_DEPLOYMENT_STATUS_STYLES,
  DEFAULT_AGENT_DEPLOYMENT_STATUS_STYLE,
} from "@/components/agents/agent-description-styles";
import { Badge } from "@/components/ui/badge";
import { api, type AgentDescriptionSummary } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

export default function AgentDescriptionsListPage() {
  const router = useRouter();
  const [items, setItems] = useState<AgentDescriptionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await api.listAgentDescriptions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void load();
  }, [load, router]);

  return (
    <main className="mx-auto max-w-4xl px-6 pb-20 pt-4">
      <Link className="text-xs text-ink/45 hover:text-ink" href="/dashboard/guild">
        ← Guild
      </Link>
      <h1 className="mt-2 font-display text-4xl tracking-tight text-ink">Agent descriptions</h1>
      <p className="mt-2 text-sm text-ink/55">
        A readable overview of each agent&apos;s purpose, type, and configuration. Open any card for
        the full detail view.
      </p>

      {error && <p className="mt-4 text-sm text-coral">{error}</p>}
      {loading ? (
        <p className="mt-8 text-sm text-ink/45">Loading…</p>
      ) : items.length === 0 ? (
        <p className="mt-8 text-sm text-ink/45">No agents yet. Create one from the Guild shelf.</p>
      ) : (
        <ul className="mt-8 space-y-3">
          {items.map((item) => (
            <li key={item.agent_id}>
              <Link
                href={`/dashboard/guild/agents/${item.agent_id}/description`}
                className="block rounded-xl border border-ink/10 bg-surface/70 px-4 py-4 transition hover:border-ink/20"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h2 className="font-medium text-ink">{item.name}</h2>
                    <p className="text-xs text-ink/45">{item.agent_key}</p>
                  </div>
                  <Badge
                    className={
                      AGENT_DEPLOYMENT_STATUS_STYLES[item.deployment_status] ??
                      DEFAULT_AGENT_DEPLOYMENT_STATUS_STYLE
                    }
                  >
                    {item.deployment_status_label}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-ink/60">
                  {item.has_description
                    ? item.description_preview
                    : "No description yet — add one during setup."}
                </p>
                <p className="mt-2 text-xs text-ink/40">
                  {item.type_name ?? "No type"} ·{" "}
                  {item.description_format === "markdown" ? "Markdown" : "Plain text"}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
