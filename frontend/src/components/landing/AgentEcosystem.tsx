"use client";

import { useState } from "react";
import { Reveal } from "@/components/landing/Reveal";
import { cn } from "@/lib/utils";

const AGENTS = [
  { name: "Research", summary: "Web search, citations, source synthesis." },
  { name: "Legal", summary: "Policy checks, disclosure review, risk flags." },
  { name: "Finance", summary: "Numbers, filings, chart generation." },
  { name: "Planning", summary: "Roadmaps, sequencing, dependency maps." },
  { name: "Sales", summary: "Pipeline briefs, outreach drafts." },
  { name: "Support", summary: "Customer context, refund proposals." },
  { name: "Coding", summary: "Repos edits, reviews, test plans." },
  { name: "Browser", summary: "Live browsing under scoped access." },
  { name: "Vision", summary: "Document and image understanding." },
  { name: "Custom MCP", summary: "Attach remote tools via MCP." },
];

export function AgentEcosystem() {
  const [active, setActive] = useState<string | null>("Research");

  return (
    <section className="border-t border-ink/[0.06] bg-surface/40 px-6 py-24 md:py-32">
      <div className="mx-auto max-w-7xl">
        <Reveal>
          <p className="text-[11px] uppercase tracking-[0.24em] text-ink/40">Agent ecosystem</p>
          <h2 className="mt-3 max-w-xl font-display text-3xl tracking-tight text-ink md:text-5xl">
            Specialized minds, one room.
          </h2>
          <p className="mt-4 max-w-lg text-ink/55">
            Hover an agent to see what it brings into the gathering.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
          {AGENTS.map((agent, idx) => {
            const isActive = active === agent.name;
            return (
              <Reveal key={agent.name} delayMs={idx * 40}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(agent.name)}
                  onFocus={() => setActive(agent.name)}
                  className={cn(
                    "panel animate-agent-float w-full px-4 py-5 text-left transition",
                    isActive && "border-teal/30 bg-surface"
                  )}
                  style={{ animationDelay: `${idx * 0.2}s` }}
                >
                  <p className="text-sm font-medium text-ink">{agent.name}</p>
                  <p
                    className={cn(
                      "mt-2 text-xs leading-relaxed text-ink/45 transition-opacity",
                      isActive ? "opacity-100" : "opacity-0 sm:opacity-70"
                    )}
                  >
                    {agent.summary}
                  </p>
                </button>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
