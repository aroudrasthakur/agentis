"use client";

import { useMemo, useState } from "react";
import type { Participant, SessionEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function ControlBar({
  events,
  participants,
  status,
  onAction,
  onStart,
}: {
  events: SessionEvent[];
  participants: Participant[];
  status: string;
  onAction: (payload: Record<string, unknown>) => void;
  onStart: () => Promise<void>;
}) {
  const latest = useMemo(
    () => [...events].sort((a, b) => b.sequence - a.sequence)[0],
    [events]
  );
  const needsPlanApproval =
    Boolean(latest?.requires_approval) && latest?.type === "plan_proposed";
  const needsActionApproval =
    Boolean(latest?.requires_approval) && latest?.type === "action_pending";
  const agents = participants.filter((p) => p.kind !== "human" && !p.token_revoked);
  const [redirectOpen, setRedirectOpen] = useState(false);
  const [redirectMsg, setRedirectMsg] = useState("");
  const [handoffOpen, setHandoffOpen] = useState(false);
  const [starting, setStarting] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-ink/10 bg-surface/50 px-4 py-3">
      <Button
        size="sm"
        variant="outline"
        disabled={starting}
        onClick={async () => {
          setStarting(true);
          try {
            await onStart();
          } finally {
            setStarting(false);
          }
        }}
      >
        {starting ? "Starting…" : "Start"}
      </Button>
      {status === "paused" ? (
        <Button size="sm" variant="teal" onClick={() => onAction({ action: "resume" })}>
          Resume
        </Button>
      ) : (
        <Button size="sm" variant="outline" onClick={() => onAction({ action: "pause" })}>
          Pause
        </Button>
      )}

      <Dialog open={redirectOpen} onOpenChange={setRedirectOpen}>
        <DialogTrigger asChild>
          <Button size="sm" variant="outline">
            Redirect
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redirect agents</DialogTitle>
          </DialogHeader>
          <Input
            placeholder="Inject a message that changes what happens next…"
            value={redirectMsg}
            onChange={(e) => setRedirectMsg(e.target.value)}
          />
          <Button
            className="mt-3"
            variant="teal"
            disabled={!redirectMsg.trim()}
            onClick={() => {
              onAction({ action: "redirect", message: redirectMsg.trim() });
              setRedirectMsg("");
              setRedirectOpen(false);
            }}
          >
            Send redirect
          </Button>
        </DialogContent>
      </Dialog>

      {needsPlanApproval ? (
        <>
          <Button
            size="sm"
            variant="teal"
            onClick={() => onAction({ action: "approve_plan", removed_step_ids: [] })}
          >
            Approve plan
          </Button>
          <Button
            size="sm"
            variant="coral"
            onClick={() => onAction({ action: "deny_plan" })}
          >
            Deny plan
          </Button>
        </>
      ) : (
        <>
          <Button
            size="sm"
            variant="teal"
            disabled={!needsActionApproval}
            onClick={() => onAction({ action: "approve" })}
          >
            Approve
          </Button>
          <Button
            size="sm"
            variant="coral"
            disabled={!needsActionApproval}
            onClick={() => onAction({ action: "deny" })}
          >
            Deny
          </Button>
        </>
      )}

      <Dialog open={handoffOpen} onOpenChange={setHandoffOpen}>
        <DialogTrigger asChild>
          <Button size="sm" variant="outline" disabled={!agents.length}>
            Handoff
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Hand off to agent</DialogTitle>
          </DialogHeader>
          <ul className="space-y-2">
            {agents.map((agent) => (
              <li key={agent.id}>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => {
                    onAction({ action: "handoff", participant_id: agent.id });
                    setHandoffOpen(false);
                  }}
                >
                  {agent.name}
                </Button>
              </li>
            ))}
          </ul>
        </DialogContent>
      </Dialog>
    </div>
  );
}
