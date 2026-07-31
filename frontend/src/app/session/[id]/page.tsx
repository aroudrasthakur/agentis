"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import type { Agent, Session, SessionEvent } from "@/lib/api";
import { api } from "@/lib/api";
import { useSessionSocket } from "@/hooks/useSessionSocket";
import { Timeline } from "@/components/session/Timeline";
import { ParticipantsPanel } from "@/components/session/ParticipantsPanel";
import { ControlBar } from "@/components/session/ControlBar";
import { PlanReviewPanel } from "@/components/session/PlanReviewPanel";
import { ShareButton } from "@/components/session/ShareButton";
import { Badge } from "@/components/ui/badge";

function SessionRoom() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const sessionId = params.id;
  const invite = searchParams.get("invite");
  const [session, setSession] = useState<Session | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const onEvent = useCallback((event: SessionEvent) => {
    setSession((prev) => {
      if (!prev) return prev;
      if (prev.events.some((e) => e.id === event.id || e.sequence === event.sequence)) {
        return prev;
      }
      return { ...prev, events: [...prev.events, event] };
    });
  }, []);

  const onSession = useCallback((next: Session) => {
    setSession(next);
  }, []);

  const { connected, send } = useSessionSocket(sessionId, invite, onEvent, onSession);

  useEffect(() => {
    if (!invite) {
      setError("Missing invite token. Open this session from a signed share link.");
      return;
    }
    void (async () => {
      try {
        const [s, a] = await Promise.all([
          api.getSession(sessionId, invite),
          api.listAgents(),
        ]);
        setSession(s);
        setAgents(a);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load session");
      }
    })();
  }, [sessionId, invite]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.events.length]);

  async function attach(agentIds: string[]) {
    if (!invite) return;
    const next = await api.attachAgents(sessionId, invite, agentIds);
    setSession(next);
  }

  async function detach(participantId: string) {
    if (!invite) return;
    const next = await api.detachAgent(sessionId, invite, participantId);
    setSession(next);
  }

  async function start() {
    if (!invite) return;
    const next = await api.startSession(sessionId, invite);
    setSession(next);
  }

  if (error) {
    return <main className="px-6 py-10 text-coral">{error}</main>;
  }

  if (!session) {
    return <main className="px-6 py-10 text-ink/50">Loading session…</main>;
  }

  const shareUrl =
    session.share_url ||
    (typeof window !== "undefined" && invite
      ? `${window.location.origin}/session/${session.id}?invite=${encodeURIComponent(invite)}`
      : "");

  return (
    <main className="mx-auto flex h-[calc(100vh-4.5rem)] max-w-7xl flex-col px-4 pb-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink">{session.title}</h1>
          <p className="text-xs text-ink/45">
            {connected ? "Live" : "Reconnecting…"}
            {session.nature
              ? ` · ${session.nature === "training" ? "Training" : "Multi-agent"}`
              : ""}{" "}
            · {session.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            className={
              session.status === "paused"
                ? "bg-coral-soft text-coral-deep"
                : session.status === "completed"
                  ? "bg-ink/10 text-ink/60"
                  : "bg-teal-soft text-teal-deep"
            }
          >
            {session.status}
          </Badge>
          <ShareButton url={shareUrl} />
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden rounded-xl border border-ink/10 bg-surface/30 md:grid-cols-[1fr_280px]">
        <div className="flex min-h-0 flex-col">
          <div className="min-h-0 flex-1 p-4">
            <Timeline events={session.events} />
            <div ref={bottomRef} />
          </div>
          <PlanReviewPanel events={session.events} onAction={send} />
          <ControlBar
            events={session.events}
            participants={session.participants}
            status={session.status}
            onAction={send}
            onStart={start}
          />
        </div>
        <ParticipantsPanel
          participants={session.participants}
          activeParticipantId={session.active_participant_id}
          agents={agents}
          onAttach={attach}
          onDetach={detach}
        />
      </div>
    </main>
  );
}

export default function SessionPage() {
  return (
    <Suspense fallback={<main className="px-6 py-10 text-ink/50">Loading session…</main>}>
      <SessionRoom />
    </Suspense>
  );
}
