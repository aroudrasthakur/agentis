"use client";

import { Reveal } from "@/components/landing/Reveal";
import { theme } from "@/theme/tokens";

export function FeatureShowcase() {
  return (
    <section className="border-t border-ink/[0.06] bg-surface/50 px-6 py-24 md:py-32">
      <div className="mx-auto max-w-7xl">
        <Reveal>
          <p className="text-[11px] uppercase tracking-[0.24em] text-ink/40">Core features</p>
          <h2 className="mt-3 max-w-xl font-display text-3xl tracking-tight text-ink md:text-5xl">
            Built for control, not just generation.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          <Reveal delayMs={0}>
            <article className="panel flex h-full flex-col p-6">
              <h3 className="font-display text-2xl text-ink">Shared Timeline</h3>
              <p className="mt-3 text-sm leading-relaxed text-ink/55">
                Every conversation, tool call, approval, and artifact exists inside one ordered
                timeline.
              </p>
              <div className="mt-8 flex-1 space-y-2 rounded-2xl border border-ink/[0.06] bg-mist/40 p-4">
                {[
                  ["Human", "Attach Research + Legal"],
                  ["Research", "Found 12 sources"],
                  ["Legal", "Needs approval"],
                  ["Human", "Approved"],
                ].map(([who, what], i) => (
                  <div
                    key={what}
                    className="flex items-center gap-3 rounded-xl bg-surface/80 px-3 py-2 text-xs"
                    style={{ opacity: 1 - i * 0.08 }}
                  >
                    <span className="w-16 shrink-0 font-medium text-ink/70">{who}</span>
                    <span className="text-ink/50">{what}</span>
                  </div>
                ))}
              </div>
            </article>
          </Reveal>

          <Reveal delayMs={80}>
            <article className="panel flex h-full flex-col p-6">
              <h3 className="font-display text-2xl text-ink">Scoped Agents</h3>
              <p className="mt-3 text-sm leading-relaxed text-ink/55">
                Each attached agent only receives the permissions required for its task.
              </p>
              <div className="mt-8 flex flex-1 items-center justify-center rounded-2xl border border-ink/[0.06] bg-mist/40 p-6">
                <svg viewBox="0 0 220 140" className="h-auto w-full max-w-[240px]" aria-hidden>
                  <circle
                    cx="110"
                    cy="70"
                    r="18"
                    fill={theme.surface}
                    stroke={theme.tealDeep}
                    strokeWidth="1.2"
                  />
                  <text x="110" y="74" textAnchor="middle" fontSize="8" fill={theme.ink}>
                    Human
                  </text>
                  {[
                    [40, 30, "Read"],
                    [180, 30, "Search"],
                    [40, 110, "Draft"],
                    [180, 110, "Exec"],
                  ].map(([x, y, label], i) => (
                    <g key={String(label)}>
                      <line
                        x1="110"
                        y1="70"
                        x2={Number(x)}
                        y2={Number(y)}
                        stroke={theme.ink}
                        strokeOpacity="0.16"
                      />
                      <circle
                        cx={Number(x)}
                        cy={Number(y)}
                        r="16"
                        fill={theme.surface}
                        stroke={theme.ink}
                        strokeOpacity="0.16"
                      />
                      <text
                        x={Number(x)}
                        y={Number(y) + 3}
                        textAnchor="middle"
                        fontSize="7"
                        fill={theme.ink}
                        fillOpacity="0.58"
                      >
                        {label}
                      </text>
                      <circle
                        cx={Number(x)}
                        cy={Number(y)}
                        r="2"
                        fill={theme.tealDeep}
                        className="animate-soft-pulse"
                        style={{ animationDelay: `${i * 0.3}s` }}
                      />
                    </g>
                  ))}
                </svg>
              </div>
            </article>
          </Reveal>

          <Reveal delayMs={160}>
            <article className="panel flex h-full flex-col p-6">
              <h3 className="font-display text-2xl text-ink">Human Oversight</h3>
              <p className="mt-3 text-sm leading-relaxed text-ink/55">
                Approve, reject, pause, retry, or delegate before important actions execute.
              </p>
              <div className="mt-8 flex-1 rounded-2xl border border-ink/[0.06] bg-mist/40 p-4">
                <div className="rounded-xl border border-coral/25 bg-surface/90 px-4 py-3">
                  <p className="text-[10px] uppercase tracking-[0.16em] text-coral">
                    Action pending
                  </p>
                  <p className="mt-2 text-sm font-medium text-ink">process_refund · $89.99</p>
                  <p className="mt-1 text-xs text-ink/45">Requires human approval</p>
                  <div className="mt-4 flex gap-2">
                    <span className="rounded-lg bg-teal px-3 py-1.5 text-xs text-white">Approve</span>
                    <span className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs text-ink/60">
                      Deny
                    </span>
                    <span className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs text-ink/60">
                      Pause
                    </span>
                  </div>
                </div>
              </div>
            </article>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
