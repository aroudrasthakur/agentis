"use client";

import { useEffect, useState } from "react";
import type { Agent, HostingMode, OrgTag } from "@/lib/api";
import { api } from "@/lib/api";
import { Badge, OrgBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [agentKey, setAgentKey] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("http://localhost:8100/mcp");
  const [mode, setMode] = useState<HostingMode>("remote_mcp");
  const [orgTag, setOrgTag] = useState<OrgTag>("External");
  const [capabilities, setCapabilities] = useState("check_billing_status, process_refund");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setAgents(await api.listAgents());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function register(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const caps = capabilities
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      await api.createAgent({
        name,
        agent_key: agentKey || name.toLowerCase().replace(/\s+/g, "_"),
        org_tag: orgTag,
        hosting_mode: mode,
        endpoint_url: mode === "remote_mcp" ? endpointUrl : null,
        description: mode === "hosted" ? "Hosted agent registered from UI" : "Remote MCP agent",
        capabilities: caps,
      });
      setName("");
      setAgentKey("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to register agent");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 pb-16">
      <div className="mb-8">
        <h1 className="font-display text-4xl text-ink">Agents</h1>
        <p className="mt-2 text-ink/60">
          Register hosted (in-app) or remote (MCP) agents, then attach them to sessions.
        </p>
      </div>

      <section className="mb-10 rounded-xl border border-ink/10 bg-surface/60 p-5">
        <h2 className="mb-4 font-display text-xl">Register agent</h2>
        <form onSubmit={register} className="grid gap-3 md:grid-cols-2">
          <Input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Input
            placeholder="agent_key (unique)"
            value={agentKey}
            onChange={(e) => setAgentKey(e.target.value)}
          />
          <select
            className="h-10 rounded-md border border-ink/15 bg-surface/80 px-3 text-sm"
            value={mode}
            onChange={(e) => {
              const next = e.target.value as HostingMode;
              setMode(next);
              setOrgTag(next === "hosted" ? "Internal" : "External");
            }}
          >
            <option value="remote_mcp">Remote MCP</option>
            <option value="hosted">Hosted (in-app)</option>
          </select>
          <select
            className="h-10 rounded-md border border-ink/15 bg-surface/80 px-3 text-sm"
            value={orgTag}
            onChange={(e) => setOrgTag(e.target.value as OrgTag)}
          >
            <option value="Internal">Internal</option>
            <option value="External">External</option>
          </select>
          {mode === "remote_mcp" && (
            <Input
              className="md:col-span-2"
              placeholder="Endpoint URL (e.g. http://localhost:8100/mcp)"
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              required
            />
          )}
          <Input
            className="md:col-span-2"
            placeholder="Capabilities (comma-separated ceiling)"
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
          />
          <div className="md:col-span-2">
            <Button type="submit" variant="teal" disabled={busy || !name}>
              {busy ? "Saving…" : "Register"}
            </Button>
          </div>
        </form>
        {error && <p className="mt-3 text-sm text-coral">{error}</p>}
      </section>

      <section className="space-y-3">
        {agents.map((agent) => (
          <article
            key={agent.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink/10 bg-surface/70 px-4 py-3 animate-fade-up"
          >
            <div>
              <h3 className="font-semibold text-ink">{agent.name}</h3>
              <p className="text-xs text-ink/50">
                {agent.agent_key}
                {agent.endpoint_url ? ` · ${agent.endpoint_url}` : ""}
              </p>
              {agent.description && (
                <p className="mt-1 text-sm text-ink/65">{agent.description}</p>
              )}
              <p className="mt-1 text-xs text-ink/45">
                ceiling:{" "}
                {(agent.capabilities || []).length
                  ? agent.capabilities.join(", ")
                  : "none"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <OrgBadge org={agent.org_tag} />
              <Badge className="bg-ink/5 text-ink/70">
                {agent.hosting_mode === "hosted" ? "Hosted" : "Remote"}
              </Badge>
              <Badge
                className={
                  agent.is_active ? "bg-teal-soft text-teal-deep" : "bg-ink/10 text-ink/50"
                }
              >
                {agent.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
          </article>
        ))}
        {!agents.length && !error && (
          <p className="text-sm text-ink/50">No agents yet. Register one above.</p>
        )}
      </section>
    </main>
  );
}
