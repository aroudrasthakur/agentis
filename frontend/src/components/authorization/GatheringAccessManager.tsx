"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function GatheringAccessManager({ gatheringId }: { gatheringId: string }) {
  const [settings, setSettings] = useState<{
    access_mode: string;
    future_grants_enabled?: boolean;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setSettings(await api.getGatheringAuthSettings(gatheringId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load access settings");
      }
    })();
  }, [gatheringId]);

  if (error) return <p className="text-sm text-coral">{error}</p>;
  if (!settings) return <p className="text-sm text-ink/45">Loading authorization…</p>;

  return (
    <div className="rounded-xl border border-ink/10 bg-surface/70 p-4 text-sm text-ink/70">
      <p>
        Access mode: <strong className="text-ink">{settings.access_mode}</strong>
      </p>
      {settings.future_grants_enabled != null && (
        <p className="mt-1">Future grants: {settings.future_grants_enabled ? "enabled" : "disabled"}</p>
      )}
      <p className="mt-2 text-xs text-ink/45">
        Managed Gathering access roles are created automatically. Use Roles to inspect inheritance.
      </p>
    </div>
  );
}
