"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { GatheringDetail, Agent, SessionNature } from "@/lib/api";
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

export default function GatheringPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const gatheringId = params.id;
  const [gathering, setGathering] = useState<GatheringDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);

  const [guildAgents, setGuildAgents] = useState<Agent[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  const [sessionOpen, setSessionOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [nature, setNature] = useState<SessionNature>("multi_agent");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setGathering(await api.getGathering(gatheringId));
  }, [gatheringId]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void (async () => {
      try {
        await reload();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load gathering");
      }
    })();
  }, [reload, router]);

  async function invite() {
    setBusy(true);
    setError(null);
    try {
      await api.inviteToGathering(gatheringId, inviteEmail.trim());
      setInviteEmail("");
      setInviteOpen(false);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    } finally {
      setBusy(false);
    }
  }

  async function openAddAgents() {
    setAddOpen(true);
    try {
      setGuildAgents(await api.attachableAgents(gatheringId));
      setSelected([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    }
  }

  async function addAgents() {
    if (!selected.length) return;
    setBusy(true);
    try {
      await api.addAgentsToGathering(gatheringId, selected);
      setAddOpen(false);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add agents");
    } finally {
      setBusy(false);
    }
  }

  async function createSession() {
    if (!title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const session = await api.createGatheringSession(gatheringId, {
        title: title.trim(),
        nature,
        agent_ids: gathering?.agents.filter((a) => a.is_active).map((a) => a.id) ?? [],
      });
      router.push(
        `/session/${session.id}?invite=${encodeURIComponent(session.invite)}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
      setBusy(false);
    }
  }

  async function openSession(sessionId: string) {
    setBusy(true);
    setError(null);
    try {
      const session = await api.openGatheringSession(gatheringId, sessionId);
      router.push(
        `/session/${session.id}?invite=${encodeURIComponent(session.invite)}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open session");
      setBusy(false);
    }
  }

  if (!gathering && !error) {
    return <main className="px-6 py-10 text-ink/50">Loading gathering…</main>;
  }

  if (!gathering) {
    return <main className="px-6 py-10 text-coral">{error}</main>;
  }

  const already = new Set(gathering.agents.map((a) => a.id));

  return (
    <main className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Gathering</p>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl tracking-tight text-ink">
            {gathering.name}
          </h1>
          {gathering.description && (
            <p className="mt-2 max-w-xl text-sm text-ink/55">{gathering.description}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">Invite people</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invite to gathering</DialogTitle>
              </DialogHeader>
              <Input
                className="mt-3"
                type="email"
                placeholder="colleague@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
              <Button
                className="mt-3 w-full"
                variant="teal"
                disabled={busy || !inviteEmail.trim()}
                onClick={() => void invite()}
              >
                Send invite
              </Button>
            </DialogContent>
          </Dialog>

          <Dialog
            open={addOpen}
            onOpenChange={(v) => {
              if (v) void openAddAgents();
              else setAddOpen(false);
            }}
          >
            <DialogTrigger asChild>
              <Button variant="outline">Add agents</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add from Guild</DialogTitle>
              </DialogHeader>
              <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto">
                {guildAgents
                  .filter((a) => !already.has(a.id))
                  .map((agent) => {
                    const checked = selected.includes(agent.id);
                    return (
                      <li key={agent.id}>
                        <button
                          type="button"
                          className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm ${
                            checked
                              ? "border-teal bg-teal-soft/40"
                              : "border-ink/10 bg-surface"
                          }`}
                          onClick={() =>
                            setSelected((prev) =>
                              checked
                                ? prev.filter((id) => id !== agent.id)
                                : [...prev, agent.id]
                            )
                          }
                        >
                          <span>{agent.name}</span>
                          <span className="text-[10px] uppercase text-ink/40">
                            {agent.source || "agent"}
                          </span>
                        </button>
                      </li>
                    );
                  })}
              </ul>
              <Button
                className="mt-3 w-full"
                variant="teal"
                disabled={!selected.length || busy}
                onClick={() => void addAgents()}
              >
                Add selected
              </Button>
            </DialogContent>
          </Dialog>

          <Dialog open={sessionOpen} onOpenChange={setSessionOpen}>
            <DialogTrigger asChild>
              <Button variant="teal">New session</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create session</DialogTitle>
              </DialogHeader>
              <p className="text-xs text-ink/45">
                Session nature is locked at creation and cannot be changed later.
              </p>
              <Input
                className="mt-3"
                placeholder="Session title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <div className="mt-3 space-y-2">
                <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-ink/10 px-3 py-3">
                  <input
                    type="radio"
                    name="nature"
                    checked={nature === "multi_agent"}
                    onChange={() => setNature("multi_agent")}
                  />
                  <span>
                    <span className="block text-sm font-medium">Multi-agent</span>
                    <span className="text-xs text-ink/50">
                      Agents interact together in a live oversight room.
                    </span>
                  </span>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-ink/10 px-3 py-3">
                  <input
                    type="radio"
                    name="nature"
                    checked={nature === "training"}
                    onChange={() => setNature("training")}
                  />
                  <span>
                    <span className="block text-sm font-medium">Training</span>
                    <span className="text-xs text-ink/50">
                      Focused session to train or evaluate an agent.
                    </span>
                  </span>
                </label>
              </div>
              <Button
                className="mt-4 w-full"
                variant="teal"
                disabled={busy || !title.trim()}
                onClick={() => void createSession()}
              >
                {busy ? "Creating…" : "Create session"}
              </Button>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-coral">{error}</p>}

      <div className="mt-12 grid gap-10 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="font-display text-xl text-ink">Sessions</h2>
          <ul className="mt-4 space-y-2">
            {gathering.sessions.length === 0 && (
              <li className="text-sm text-ink/45">No sessions yet.</li>
            )}
            {gathering.sessions.map((s) => (
              <li
                key={s.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-ink/10 bg-surface/70 px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-ink">{s.title}</p>
                  <p className="text-[11px] uppercase tracking-wider text-ink/40">
                    {s.nature.replace("_", " ")} · {s.status}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className="bg-mist text-ink/70">
                    {s.nature === "training" ? "Training" : "Multi-agent"}
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void openSession(s.id)}
                  >
                    Open
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <div className="space-y-10">
          <section>
            <h2 className="font-display text-xl text-ink">People</h2>
            <ul className="mt-4 space-y-2">
              {gathering.members.map((m) => (
                <li
                  key={m.id}
                  className="rounded-lg border border-ink/10 bg-surface/70 px-3 py-2 text-sm"
                >
                  <p className="font-medium text-ink">
                    {m.display_name || m.email || m.invited_email}
                  </p>
                  {(m.title || m.organization) && (
                    <p className="text-xs text-ink/50">
                      {[m.title, m.organization].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  {m.bio && <p className="mt-1 text-xs text-ink/45">{m.bio}</p>}
                  <p className="mt-1 text-[11px] uppercase tracking-wider text-ink/40">
                    {m.role}
                    {!m.user_id && " · pending"}
                  </p>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="font-display text-xl text-ink">Agents</h2>
            <ul className="mt-4 space-y-2">
              {gathering.agents.length === 0 && (
                <li className="text-sm text-ink/45">Add agents from your Guild.</li>
              )}
              {gathering.agents.map((a) => (
                <li
                  key={a.id}
                  className="rounded-lg border border-ink/10 bg-surface/70 px-3 py-2 text-sm"
                >
                  <p className="font-medium text-ink">{a.name}</p>
                  <p className="text-[11px] text-ink/40">{a.agent_key}</p>
                  {a.version && (
                    <p className="text-[11px] text-ink/40">v{a.version}</p>
                  )}
                  {a.notes && <p className="mt-1 text-xs text-ink/50">{a.notes}</p>}
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </main>
  );
}
