"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { Agent, GuildTab, HostingMode } from "@/lib/api";
import { api } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const TABS: { id: GuildTab; label: string; hint: string }[] = [
  { id: "local", label: "Local", hint: "Private agents you own" },
  { id: "downloaded", label: "Downloaded", hint: "Agents saved from the directory" },
  { id: "directory", label: "Directory", hint: "Publicly posted agents" },
];

export default function GuildPage() {
  const router = useRouter();
  const [tab, setTab] = useState<GuildTab>("local");
  const [q, setQ] = useState("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [localOpen, setLocalOpen] = useState(false);
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [mode, setMode] = useState<HostingMode>("hosted");
  const [endpoint, setEndpoint] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.guildAgents(tab, q);
      setAgents(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load guild");
    } finally {
      setLoading(false);
    }
  }, [tab, q]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void load();
  }, [load, router]);

  async function createLocal() {
    setBusy(true);
    setError(null);
    try {
      await api.createLocalAgent({
        name,
        agent_key: key,
        hosting_mode: mode,
        endpoint_url: mode === "remote_mcp" ? endpoint : null,
      });
      setLocalOpen(false);
      setName("");
      setKey("");
      setEndpoint("");
      setTab("local");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function download(id: string) {
    try {
      await api.downloadAgent(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link
            href="/dashboard"
            className="text-[11px] uppercase tracking-[0.22em] text-ink/40 hover:text-ink/70"
          >
            ← Dashboard
          </Link>
          <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Guild</h1>
          <p className="mt-2 text-sm text-ink/55">
            Local, downloaded, and public directory agents.
          </p>
        </div>
        {tab === "local" && (
          <Dialog open={localOpen} onOpenChange={setLocalOpen}>
            <DialogTrigger asChild>
              <Button variant="teal">Register local agent</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Private local agent</DialogTitle>
              </DialogHeader>
              <div className="mt-3 space-y-3">
                <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
                <Input
                  placeholder="agent_key"
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                />
                <select
                  className="w-full rounded-md border border-ink/15 bg-white px-3 py-2 text-sm"
                  value={mode}
                  onChange={(e) => setMode(e.target.value as HostingMode)}
                >
                  <option value="hosted">Hosted</option>
                  <option value="remote_mcp">Remote MCP</option>
                </select>
                {mode === "remote_mcp" && (
                  <Input
                    placeholder="Endpoint URL"
                    value={endpoint}
                    onChange={(e) => setEndpoint(e.target.value)}
                  />
                )}
                <Button
                  variant="teal"
                  className="w-full"
                  disabled={busy || !name.trim() || !key.trim()}
                  onClick={() => void createLocal()}
                >
                  {busy ? "Saving…" : "Save local agent"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2 border-b border-ink/10 pb-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              tab === t.id
                ? "bg-ink text-sand"
                : "text-ink/55 hover:bg-ink/5 hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
        <div className="ml-auto w-full max-w-xs sm:w-64">
          <Input
            placeholder={tab === "directory" ? "Search directory…" : "Filter…"}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </div>
      <p className="mb-4 text-xs text-ink/40">{TABS.find((t) => t.id === tab)?.hint}</p>

      {error && <p className="mb-4 text-sm text-coral">{error}</p>}
      {loading ? (
        <p className="text-sm text-ink/45">Loading…</p>
      ) : agents.length === 0 ? (
        <p className="text-sm text-ink/45">No agents in this shelf.</p>
      ) : (
        <ul className="space-y-3">
          {agents.map((agent) => (
            <li
              key={agent.id}
              className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-ink/10 bg-white/70 px-4 py-4"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-medium text-ink">{agent.name}</h2>
                  <Badge className="bg-ink/5 text-ink/60">{agent.hosting_mode}</Badge>
                  {agent.source && (
                    <Badge className="bg-teal-soft text-teal-deep">{agent.source}</Badge>
                  )}
                </div>
                <p className="mt-1 text-xs text-ink/45">{agent.agent_key}</p>
                {agent.description && (
                  <p className="mt-2 max-w-2xl text-sm text-ink/60">{agent.description}</p>
                )}
              </div>
              {tab === "directory" && (
                <Button
                  size="sm"
                  variant={agent.downloaded ? "outline" : "teal"}
                  disabled={agent.downloaded}
                  onClick={() => void download(agent.id)}
                >
                  {agent.downloaded ? "Downloaded" : "Download"}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
