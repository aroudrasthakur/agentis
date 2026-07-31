"use client";

import type { SessionEvent } from "@/lib/api";
import { OrgBadge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function Timeline({ events }: { events: SessionEvent[] }) {
  const sorted = [...events].sort((a, b) => a.sequence - b.sequence);
  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto pr-2">
      {sorted.length === 0 && (
        <p className="text-sm text-ink/50">No events yet. Attach agents and start the session.</p>
      )}
      {sorted.map((event) => (
        <EventBubble key={event.id} event={event} />
      ))}
    </div>
  );
}

function EventBubble({ event }: { event: SessionEvent }) {
  const name = event.participant?.name ?? "System";
  const org = event.participant?.org_tag ?? "Internal";
  const pending = event.type === "action_pending";
  const systemish = ["agent_attached", "agent_detached", "handoff", "redirect"].includes(
    event.type
  );

  return (
    <article
      className={cn(
        "animate-fade-up rounded-lg px-4 py-3",
        pending && "border border-coral/40 bg-coral-soft/60",
        event.type === "action_approved" && "border border-teal/30 bg-teal-soft/50",
        event.type === "action_denied" && "border border-ink/10 bg-ink/5",
        !pending &&
          event.type !== "action_approved" &&
          event.type !== "action_denied" &&
          "bg-white/70",
        systemish && "border border-dashed border-ink/15 bg-transparent"
      )}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className="text-sm font-semibold text-ink">{name}</span>
        <OrgBadge org={org} />
        <span className="text-[10px] uppercase tracking-wider text-ink/40">{event.type}</span>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink/85">{event.content}</p>
    </article>
  );
}
