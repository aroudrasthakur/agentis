"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const AGENTS = [
  { name: "Research Agent", status: "Searching…", tone: "active" as const },
  { name: "Legal Agent", status: "Waiting for approval…", tone: "wait" as const },
  { name: "Planning Agent", status: "Building roadmap…", tone: "active" as const },
  { name: "Execution Agent", status: "Running…", tone: "run" as const },
];

const EVENTS = [
  "Research joined",
  "Searching…",
  "Sources found",
  "Human approved",
  "Execution started",
  "Completed",
];

export function HeroProduct() {
  const [visibleEvents, setVisibleEvents] = useState(1);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setVisibleEvents(EVENTS.length);
      return;
    }
    let i = 1;
    const id = window.setInterval(() => {
      i = i >= EVENTS.length ? 1 : i + 1;
      setVisibleEvents(i);
    }, 1600);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-ink/[0.06] px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-teal animate-soft-pulse" />
          <span className="text-xs font-medium tracking-wide text-ink/70">Live session</span>
        </div>
        <span className="text-[10px] uppercase tracking-[0.18em] text-ink/35">Shared room</span>
      </div>

      <div className="grid gap-0 md:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-3 border-b border-ink/[0.06] p-5 md:border-b-0 md:border-r">
          <div className="rounded-2xl border border-teal/20 bg-teal-soft/40 px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.18em] text-teal-deep">Human</p>
            <p className="mt-1 text-sm font-medium text-ink">Overseeing the room</p>
          </div>
          {AGENTS.map((agent, idx) => (
            <div
              key={agent.name}
              className="animate-fade-up rounded-2xl border border-ink/[0.07] bg-surface/80 px-4 py-3"
              style={{ animationDelay: `${120 + idx * 90}ms` }}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-ink">{agent.name}</p>
                <StatusDot tone={agent.tone} />
              </div>
              <p className="mt-1 text-xs text-ink/50">{agent.status}</p>
            </div>
          ))}
        </div>

        <div className="p-5">
          <p className="mb-3 text-[10px] uppercase tracking-[0.18em] text-ink/35">
            Shared activity
          </p>
          <ul className="space-y-2.5">
            {EVENTS.slice(0, visibleEvents).map((event, idx) => (
              <li
                key={`${event}-${idx}`}
                className="animate-timeline-in flex items-start gap-3 text-sm text-ink/70"
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                <span
                  className={cn(
                    "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                    idx === visibleEvents - 1 ? "bg-teal animate-soft-pulse" : "bg-ink/25"
                  )}
                />
                <span>{event}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function StatusDot({ tone }: { tone: "active" | "wait" | "run" }) {
  return (
    <span
      className={cn(
        "h-1.5 w-1.5 rounded-full",
        tone === "wait" && "bg-ink/25",
        tone === "active" && "bg-teal animate-soft-pulse",
        tone === "run" && "bg-teal-deep animate-soft-pulse"
      )}
    />
  );
}
