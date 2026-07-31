"use client";

import { Reveal } from "@/components/landing/Reveal";

const AGENTS = [
  "Claude",
  "GPT",
  "Gemini",
  "Internal MCP",
  "GitHub",
  "Slack",
  "Browser",
  "Databases",
  "Custom Agents",
];

export function Architecture() {
  return (
    <section className="border-t border-ink/[0.06] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-7xl">
        <Reveal>
          <p className="text-[11px] uppercase tracking-[0.24em] text-ink/40">Architecture</p>
          <h2 className="mt-3 max-w-xl font-display text-3xl tracking-tight text-ink md:text-5xl">
            One timeline. Many connections.
          </h2>
          <p className="mt-4 max-w-lg text-ink/55">
            Humans stay at the center. Agents and tools attach through a shared, visible timeline.
          </p>
        </Reveal>

        <Reveal delayMs={80}>
          <div className="panel relative mt-14 overflow-hidden px-6 py-12 md:px-14 md:py-16">
            <div
              className="pointer-events-none absolute inset-0 opacity-40"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 50% 20%, rgba(13,124,124,0.06), transparent 45%)",
              }}
            />

            <div className="relative flex flex-col items-center">
              <Node label="Human" emphasis />
              <div className="relative my-1 flex h-10 w-px items-end justify-center">
                <div className="absolute inset-0 bg-ink/12" />
                <span className="absolute bottom-0 h-1.5 w-1.5 rounded-full bg-teal animate-soft-pulse" />
              </div>
              <Node label="Shared Timeline" />
              <div className="relative my-1 h-10 w-px bg-ink/12">
                <span className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink/25" />
              </div>

              <p className="mb-5 text-[10px] uppercase tracking-[0.2em] text-ink/35">
                Connected agents
              </p>

              <div className="relative w-full max-w-3xl">
                <svg
                  className="pointer-events-none absolute left-1/2 top-0 hidden h-8 w-full -translate-x-1/2 -translate-y-full text-ink/40 sm:block"
                  viewBox="0 0 600 32"
                  preserveAspectRatio="none"
                  aria-hidden
                >
                  <path
                    d="M300 0 V12 M60 12 H540 M60 12 V32 M180 12 V32 M300 12 V32 M420 12 V32 M540 12 V32"
                    fill="none"
                    stroke="currentColor"
                    strokeOpacity="0.4"
                    strokeWidth="1"
                  />
                </svg>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {AGENTS.map((name, idx) => (
                    <div
                      key={name}
                      className="rounded-2xl border border-ink/[0.07] bg-surface/85 px-3 py-3 text-center text-sm text-ink/70 transition hover:border-teal/25 hover:text-ink"
                      style={{ animationDelay: `${idx * 0.15}s` }}
                    >
                      {name}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Node({ label, emphasis }: { label: string; emphasis?: boolean }) {
  return (
    <div
      className={
        emphasis
          ? "rounded-2xl border border-teal/25 bg-teal-soft/40 px-7 py-3.5 text-sm font-medium text-ink"
          : "rounded-2xl border border-ink/[0.08] bg-surface px-7 py-3.5 text-sm font-medium text-ink shadow-[0_0_0_4px_rgb(var(--teal)_/_0.08)]"
      }
    >
      {label}
    </div>
  );
}
