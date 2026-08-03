"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AgentDescriptionView } from "@/components/agents/AgentDescriptionView";
import { api, type AgentDescriptionProfile } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

export default function AgentDescriptionPage() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const agentId = params.agentId;
  const [profile, setProfile] = useState<AgentDescriptionProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProfile(await api.getAgentDescription(agentId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agent");
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void load();
  }, [load, router]);

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-6 pb-20 pt-4">
        <p className="text-sm text-ink/45">Loading agent…</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="mx-auto max-w-4xl px-6 pb-20 pt-4">
        <p className="text-sm text-coral">{error ?? "Agent not found."}</p>
        <Link className="mt-4 inline-block text-sm text-teal" href="/dashboard/guild">
          Back to Guild
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 pb-20 pt-4">
      <Link className="text-xs text-ink/45 hover:text-ink" href="/dashboard/guild/agents/descriptions">
        ← All agent descriptions
      </Link>
      <div className="mt-4">
        <AgentDescriptionView profile={profile} showActions />
      </div>
    </main>
  );
}
