"use client";

import { useState } from "react";
import type { Agent, Participant } from "@/lib/api";
import { Badge, OrgBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export function ParticipantsPanel({
  participants,
  activeParticipantId,
  agents,
  onAttach,
  onDetach,
}: {
  participants: Participant[];
  activeParticipantId: string | null;
  agents: Agent[];
  onAttach: (agentIds: string[]) => Promise<void>;
  onDetach: (participantId: string) => Promise<void>;
}) {
  const attachedAgentIds = new Set(
    participants
      .filter((p) => p.agent_id && !p.token_revoked)
      .map((p) => p.agent_id)
  );
  const available = agents.filter((a) => a.is_active && !attachedAgentIds.has(a.id));

  return (
    <aside className="flex h-full flex-col gap-4 border-l border-ink/10 bg-white/40 p-4">
      <div>
        <h2 className="font-display text-lg text-ink">Participants</h2>
        <p className="text-xs text-ink/50">Humans and attached agents</p>
      </div>
      <ul className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {participants.map((p) => (
          <li
            key={p.id}
            className={cn(
              "rounded-lg border border-ink/10 bg-white/80 px-3 py-2",
              activeParticipantId === p.id && "ring-2 ring-teal"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-ink">{p.name}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  <OrgBadge org={p.org_tag} />
                  {p.hosting_mode && (
                    <Badge className="bg-ink/5 text-ink/70">
                      {p.hosting_mode === "hosted" ? "Hosted" : "Remote"}
                    </Badge>
                  )}
                  {activeParticipantId === p.id && (
                    <Badge className="bg-teal text-white">Active</Badge>
                  )}
                  {p.token_revoked && (
                    <Badge className="bg-coral-soft text-coral-deep">Revoked</Badge>
                  )}
                </div>
                {p.granted_capabilities && p.granted_capabilities.length > 0 && (
                  <p className="mt-1 text-[10px] leading-snug text-ink/45">
                    caps: {p.granted_capabilities.join(", ")}
                  </p>
                )}
              </div>
              {p.kind !== "human" && !p.token_revoked && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onDetach(p.id)}
                  className="text-ink/40 hover:text-coral"
                >
                  Detach
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
      <AttachAgentDialog available={available} onAttach={onAttach} />
    </aside>
  );
}

function AttachAgentDialog({
  available,
  onAttach,
}: {
  available: Agent[];
  onAttach: (agentIds: string[]) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!selected.length) return;
    setBusy(true);
    try {
      await onAttach(selected);
      setSelected([]);
      setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="teal" className="w-full">
          Attach agent
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Attach agents</DialogTitle>
        </DialogHeader>
        {available.length === 0 ? (
          <p className="text-sm text-ink/60">
            No more agents available. Register more on the Agents page.
          </p>
        ) : (
          <ul className="mb-4 max-h-64 space-y-2 overflow-y-auto">
            {available.map((agent) => {
              const checked = selected.includes(agent.id);
              return (
                <li key={agent.id}>
                  <button
                    type="button"
                    onClick={() =>
                      setSelected((prev) =>
                        checked ? prev.filter((id) => id !== agent.id) : [...prev, agent.id]
                      )
                    }
                    className={cn(
                      "flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left",
                      checked ? "border-teal bg-teal-soft/40" : "border-ink/10 bg-white"
                    )}
                  >
                    <span>
                      <span className="block text-sm font-medium">{agent.name}</span>
                      <span className="text-xs text-ink/50">
                        {agent.hosting_mode === "hosted" ? "Hosted" : "Remote"} · {agent.org_tag}
                      </span>
                    </span>
                    <OrgBadge org={agent.org_tag} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        <Button variant="teal" disabled={!selected.length || busy} onClick={submit}>
          {busy ? "Attaching…" : "Attach selected"}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
