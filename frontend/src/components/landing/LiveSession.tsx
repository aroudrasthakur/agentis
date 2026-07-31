"use client";

import { useEffect, useState } from "react";
import { Reveal } from "@/components/landing/Reveal";
import { cn } from "@/lib/utils";

const MESSAGES = [
  { who: "Research Agent", body: "Searching SEC filings…", kind: "agent" },
  { who: "Finance Agent", body: "Analyzing revenue…", kind: "agent" },
  { who: "Legal Agent", body: "Checking disclosures…", kind: "agent" },
  { who: "Human", body: "Approve Finance", kind: "human" },
  { who: "Finance", body: "Generating charts…", kind: "agent" },
  { who: "Execution Agent", body: "Creating report…", kind: "agent" },
  { who: "System", body: "Completed", kind: "done" },
] as const;

export function LiveSession() {
  const [count, setCount] = useState(1);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setCount(MESSAGES.length);
      return;
    }
    let i = 1;
    const id = window.setInterval(() => {
      i = i >= MESSAGES.length ? 1 : i + 1;
      setCount(i);
    }, 1800);
    return () => window.clearInterval(id);
  }, []);

  return (
    <section id="live-session" className="border-t border-ink/[0.06] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-7xl">
        <Reveal>
          <p className="text-[11px] uppercase tracking-[0.24em] text-ink/40">Live session</p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink md:text-5xl">
            Watch a workspace think out loud.
          </h2>
          <p className="mt-4 max-w-xl text-ink/55">
            A realistic session mock — the same shared room where humans and agents coordinate
            under oversight.
          </p>
        </Reveal>

        <Reveal delayMs={100}>
          <div className="panel mx-auto mt-14 max-w-3xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-ink/[0.06] px-5 py-4">
              <div>
                <p className="font-display text-xl text-ink">Build Quarterly Report</p>
                <p className="mt-1 text-xs text-ink/40">Multi-agent · Human in the loop</p>
              </div>
              <span className="rounded-full bg-teal-soft px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-teal-deep">
                Live
              </span>
            </div>
            <div className="space-y-3 p-5">
              {MESSAGES.slice(0, count).map((msg, idx) => (
                <div
                  key={`${msg.who}-${idx}`}
                  className={cn(
                    "animate-fade-up rounded-2xl border px-4 py-3",
                    msg.kind === "human" && "border-teal/25 bg-teal-soft/35",
                    msg.kind === "done" && "border-ink/10 bg-mist/50",
                    msg.kind === "agent" && "border-ink/[0.07] bg-surface/90"
                  )}
                >
                  <p className="text-[10px] uppercase tracking-[0.16em] text-ink/40">{msg.who}</p>
                  <p className="mt-1 text-sm text-ink/80">{msg.body}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
