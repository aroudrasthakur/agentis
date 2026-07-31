"use client";

import type { SessionEvent } from "@/lib/api";
import { parsePlanContent } from "@/lib/api";
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
  const pending = event.type === "action_pending" || event.type === "plan_proposed";
  const systemish = ["agent_attached", "agent_detached", "handoff", "redirect"].includes(
    event.type
  );
  const planish = event.type.startsWith("plan_");
  const executed = event.type === "action_executed";

  let body = event.content;
  if (planish || event.type === "action_pending" || executed) {
    try {
      const parsed = JSON.parse(event.content) as Record<string, unknown>;
      if (event.type === "plan_proposed" || event.type === "plan_approved") {
        const plan = parsePlanContent(event.content);
        if (plan) {
          body = [
            plan.title,
            ...plan.steps.map(
              (s, i) =>
                `${i + 1}. ${s.action_type}${s.description ? ` — ${s.description}` : ""}`
            ),
          ].join("\n");
        }
      } else if (typeof parsed.tool === "string") {
        const conf =
          typeof parsed.confidence === "number" ? ` · confidence ${parsed.confidence}` : "";
        const mode = typeof parsed.mode === "string" ? ` · ${parsed.mode}` : "";
        const decision =
          typeof parsed.decision === "string" ? ` · ${parsed.decision}` : "";
        body = `${parsed.tool}${mode}${decision}${conf}\n${JSON.stringify(parsed.arguments ?? parsed.result ?? parsed, null, 2)}`;
      }
    } catch {
      // keep raw content
    }
  }

  return (
    <article
      className={cn(
        "animate-fade-up rounded-lg px-4 py-3",
        pending && "border border-coral/40 bg-coral-soft/60",
        event.type === "action_approved" && "border border-teal/30 bg-teal-soft/50",
        event.type === "plan_approved" && "border border-teal/30 bg-teal-soft/50",
        event.type === "action_denied" && "border border-ink/10 bg-ink/5",
        event.type === "plan_denied" && "border border-ink/10 bg-ink/5",
        executed && "border border-teal/20 bg-teal-soft/30",
        !pending &&
          !executed &&
          event.type !== "action_approved" &&
          event.type !== "action_denied" &&
          event.type !== "plan_approved" &&
          event.type !== "plan_denied" &&
          "bg-white/70",
        systemish && "border border-dashed border-ink/15 bg-transparent"
      )}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className="text-sm font-semibold text-ink">{name}</span>
        <OrgBadge org={org} />
        <span className="text-[10px] uppercase tracking-wider text-ink/40">{event.type}</span>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink/85">{body}</p>
    </article>
  );
}
