"use client";

import { Reveal } from "@/components/landing/Reveal";

const STEPS = [
  "Ask Question",
  "Research Agent joins",
  "Planner joins",
  "Legal reviews",
  "Human approves",
  "Execution",
  "Final Answer",
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-ink/[0.06] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-7xl">
        <Reveal>
          <p className="text-[11px] uppercase tracking-[0.24em] text-ink/40">How it works</p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink md:text-5xl">
            A question becomes a coordinated room.
          </h2>
          <p className="mt-4 max-w-xl text-ink/55">
            Agents join the same workspace in sequence — research, plan, review, approve, execute —
            without leaving the shared timeline.
          </p>
        </Reveal>

        <div className="mt-14 overflow-x-auto pb-2">
          <ol className="flex min-w-max items-stretch gap-3 md:gap-4">
            {STEPS.map((step, idx) => (
              <li key={step} className="flex items-center gap-3 md:gap-4">
                <Reveal delayMs={idx * 70}>
                  <div className="panel w-[168px] px-4 py-5 md:w-[180px]">
                    <p className="text-[10px] uppercase tracking-[0.2em] text-ink/35">
                      {String(idx + 1).padStart(2, "0")}
                    </p>
                    <p className="mt-3 text-sm font-medium leading-snug text-ink">{step}</p>
                  </div>
                </Reveal>
                {idx < STEPS.length - 1 && (
                  <div
                    className="h-px w-6 origin-left bg-ink/15 animate-line-draw md:w-8"
                    style={{ animationDelay: `${idx * 80}ms` }}
                  />
                )}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
