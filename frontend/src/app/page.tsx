"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AgentMesh } from "@/components/landing/AgentMesh";
import { isLoggedIn } from "@/lib/auth";

export default function HomePage() {
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(isLoggedIn());
  }, []);

  return (
    <div className="landing-shell -mt-[4.5rem] min-h-screen">
      {/* Hero: one composition — brand, line, sentence, CTAs, mesh plane */}
      <section className="relative flex min-h-screen flex-col overflow-hidden pt-[4.5rem]">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.4]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(15,28,31,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(15,28,31,0.04) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            maskImage: "radial-gradient(ellipse 80% 70% at 70% 45%, black 20%, transparent 75%)",
          }}
        />

        <div className="relative z-10 mx-auto grid w-full max-w-7xl flex-1 items-center gap-8 px-6 pb-16 pt-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-4 lg:pb-24">
          <div className="animate-fade-up max-w-xl">
            <p className="mb-4 text-[11px] font-medium uppercase tracking-[0.28em] text-ink/40">
              Multi-agent collaboration
            </p>
            <h1 className="font-display text-[clamp(3.5rem,9vw,6.5rem)] leading-[0.92] tracking-tight text-ink">
              Agentis
            </h1>
            <p className="mt-6 max-w-sm text-lg leading-relaxed text-ink/60 md:text-xl">
              Humans and agents in one live session — with oversight that stays in the room.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Link href={loggedIn ? "/dashboard" : "/login"}>
                <Button size="lg" variant="teal">
                  {loggedIn ? "Open dashboard" : "Enter Agentis"}
                </Button>
              </Link>
              <Link
                href={loggedIn ? "/dashboard/guild" : "/signup"}
                className="text-sm text-ink/55 underline-offset-4 transition-colors hover:text-ink hover:underline"
              >
                {loggedIn ? "Open Guild" : "Create account"}
              </Link>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-2xl animate-fade-up lg:max-w-none lg:translate-x-4">
            <AgentMesh className="h-auto w-full drop-shadow-[0_20px_60px_rgba(13,124,124,0.08)]" />
          </div>
        </div>

        <div className="relative z-10 border-t border-ink/[0.06] px-6 py-4">
          <p className="mx-auto max-w-7xl text-[11px] uppercase tracking-[0.2em] text-ink/35">
            Hosted · remote · human-in-the-loop
          </p>
        </div>
      </section>

      {/* One job: how the mesh works */}
      <section className="border-t border-ink/[0.06] bg-white/70 px-6 py-24">
        <div className="mx-auto max-w-7xl">
          <h2 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
            One room. Many minds.
          </h2>
          <p className="mt-3 max-w-lg text-ink/55">
            Attach agents, watch the shared timeline, and gate high-impact actions before they run.
          </p>

          <div className="mt-16 grid gap-12 md:grid-cols-3 md:gap-8">
            <Feature
              index="01"
              title="Shared session"
              body="Humans and agents write to one ordered timeline — no private side channels."
              mark={<IconSession />}
            />
            <Feature
              index="02"
              title="Scoped agents"
              body="Hosted or remote MCP agents attach with capability ceilings and revocable tokens."
              mark={<IconAgents />}
            />
            <Feature
              index="03"
              title="Live oversight"
              body="Step-by-step, confidence gates, or plan-then-execute — pause anytime."
              mark={<IconGate />}
            />
          </div>
        </div>
      </section>

      <footer className="border-t border-ink/[0.06] px-6 py-10">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <span className="font-display text-lg text-ink/80">Agentis</span>
          <p className="text-xs text-ink/40">Silicon-clear collaboration for agentic work.</p>
        </div>
      </footer>
    </div>
  );
}

function Feature({
  index,
  title,
  body,
  mark,
}: {
  index: string;
  title: string;
  body: string;
  mark: ReactNode;
}) {
  return (
    <div className="animate-fade-up">
      <div className="mb-5 flex h-14 w-14 items-center justify-center text-teal">{mark}</div>
      <p className="text-[10px] uppercase tracking-[0.22em] text-ink/35">{index}</p>
      <h3 className="mt-2 font-display text-xl text-ink">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink/55">{body}</p>
    </div>
  );
}

function IconSession() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <rect x="4" y="8" width="32" height="24" rx="2" stroke="currentColor" strokeWidth="1.2" />
      <path d="M10 16h20M10 21h14M10 26h10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function IconAgents() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <circle cx="20" cy="20" r="4" fill="currentColor" />
      <circle cx="8" cy="12" r="3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="32" cy="12" r="3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="10" cy="30" r="3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="30" cy="30" r="3" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M11 14L17 18M29 14L23 18M12 28L17 23M28 28L23 23"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeOpacity="0.5"
      />
    </svg>
  );
}

function IconGate() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <path d="M8 20h10M22 20h10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <rect x="15" y="14" width="10" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="20" cy="20" r="2" fill="currentColor" />
    </svg>
  );
}
