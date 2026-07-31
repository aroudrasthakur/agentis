"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { isLoggedIn } from "@/lib/auth";
import { HeroProduct } from "@/components/landing/HeroProduct";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { FeatureShowcase } from "@/components/landing/FeatureShowcase";
import { LiveSession } from "@/components/landing/LiveSession";
import { AgentEcosystem } from "@/components/landing/AgentEcosystem";
import { Architecture } from "@/components/landing/Architecture";
import { Reveal } from "@/components/landing/Reveal";

const BADGES = [
  "Human in the loop",
  "Multi-agent collaboration",
  "Persistent sessions",
  "Hosted & Remote",
  "MCP Compatible",
];

const CAPABILITIES = [
  {
    title: "Realtime Collaboration",
    body: "Multiple agents work simultaneously rather than sequentially — still under one shared clock.",
  },
  {
    title: "Persistent Sessions",
    body: "Return to the same workspace with complete history. Nothing evaporates between turns.",
  },
  {
    title: "Governance",
    body: "Every action is reviewable, auditable, and controlled before it leaves the room.",
  },
  {
    title: "Shared Context",
    body: "Agents collaborate using the same continuously evolving context — no private side channels.",
  },
];

const TRUST = [
  "Human Approval",
  "Transparent Actions",
  "Scoped Permissions",
  "Persistent Audit Trail",
  "Hosted or Remote",
  "No Hidden Side Channels",
];

export default function HomePage() {
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(isLoggedIn());
  }, []);

  const primaryHref = loggedIn ? "/dashboard" : "/login";

  return (
    <div className="landing-shell -mt-[4.5rem] min-h-screen">
      {/* Hero */}
      <section className="relative flex min-h-screen flex-col overflow-hidden pt-[4.5rem]">
        <div
          className="landing-grid pointer-events-none absolute inset-0 opacity-50"
          style={{
            maskImage:
              "radial-gradient(ellipse 85% 70% at 70% 40%, black 15%, transparent 72%)",
          }}
        />

        <div className="relative z-10 mx-auto grid w-full max-w-7xl flex-1 items-center gap-10 px-6 pb-16 pt-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-12 lg:pb-24">
          <div className="animate-fade-up max-w-xl">
            <p className="mb-4 text-[11px] font-medium uppercase tracking-[0.28em] text-ink/40">
              Operating system for AI teams
            </p>
            <h1 className="font-display text-[clamp(3.25rem,8vw,5.75rem)] leading-[0.94] tracking-tight text-ink">
              Agentis
            </h1>
            <p className="mt-5 font-display text-2xl leading-snug tracking-tight text-ink/80 md:text-3xl">
              Humans. Agents. One shared session.
            </p>
            <p className="mt-5 max-w-md text-base leading-relaxed text-ink/55 md:text-lg">
              Humans and specialized AI agents collaborate inside one persistent workspace where
              every action, decision, and approval remains visible.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link href={primaryHref}>
                <Button size="lg" variant="teal">
                  Launch Workspace
                </Button>
              </Link>
              <a href="#live-session">
                <Button size="lg" variant="outline">
                  See Live Demo
                </Button>
              </a>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-4 gap-y-2">
              {BADGES.map((badge) => (
                <li key={badge} className="text-xs text-ink/45">
                  <span className="mr-1.5 text-teal">✓</span>
                  {badge}
                </li>
              ))}
            </ul>
          </div>

          <div className="animate-fade-up" style={{ animationDelay: "120ms" }}>
            <HeroProduct />
          </div>
        </div>
      </section>

      <HowItWorks />
      <FeatureShowcase />
      <LiveSession />
      <AgentEcosystem />
      <Architecture />

      {/* Capabilities */}
      <section className="border-t border-ink/[0.06] bg-surface/50 px-6 py-24 md:py-32">
        <div className="mx-auto max-w-7xl space-y-20">
          {CAPABILITIES.map((item, idx) => (
            <Reveal key={item.title} delayMs={idx * 40}>
              <div
                className={`grid items-center gap-8 md:grid-cols-2 md:gap-16 ${
                  idx % 2 === 1 ? "md:[&>*:first-child]:order-2" : ""
                }`}
              >
                <div>
                  <p className="text-[10px] uppercase tracking-[0.22em] text-ink/35">
                    {String(idx + 1).padStart(2, "0")}
                  </p>
                  <h2 className="mt-3 font-display text-3xl tracking-tight text-ink md:text-4xl">
                    {item.title}
                  </h2>
                  <p className="mt-4 max-w-md text-ink/55">{item.body}</p>
                </div>
                <div className="panel h-40 md:h-48">
                  <CapabilityVisual index={idx} />
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Trust */}
      <section className="border-t border-ink/[0.06] px-6 py-24 md:py-28">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <p className="text-[11px] uppercase tracking-[0.24em] text-ink/40">Principles</p>
            <h2 className="mt-3 font-display text-3xl tracking-tight text-ink md:text-4xl">
              Operational trust, not slogans.
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {TRUST.map((item, idx) => (
              <Reveal key={item} delayMs={idx * 50}>
                <div className="panel px-5 py-5">
                  <p className="text-sm font-medium text-ink">{item}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-ink/[0.06] px-6 py-24 md:py-32">
        <Reveal>
          <div className="panel mx-auto max-w-4xl px-8 py-14 text-center md:px-16">
            <h2 className="font-display text-3xl tracking-tight text-ink md:text-5xl">
              Ready to build with AI teams?
            </h2>
            <p className="mx-auto mt-4 max-w-md text-ink/55">
              Launch your first collaborative session.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <Link href={primaryHref}>
                <Button size="lg" variant="teal">
                  Start Workspace
                </Button>
              </Link>
              <a href="#how-it-works">
                <Button size="lg" variant="outline">
                  Documentation
                </Button>
              </a>
            </div>
          </div>
        </Reveal>
        <footer className="mx-auto mt-16 flex max-w-7xl flex-wrap items-center justify-between gap-4 border-t border-ink/[0.06] pt-8">
          <span className="font-display text-lg text-ink/70">Agentis</span>
          <p className="text-xs text-ink/40">
            The operating system for human–AI collaboration.
          </p>
        </footer>
      </section>
    </div>
  );
}

function CapabilityVisual({ index }: { index: number }) {
  if (index === 0) {
    return (
      <div className="flex h-full items-end gap-2 px-8 py-8">
        {[40, 70, 55, 85, 60].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-t-lg bg-teal/25"
            style={{ height: `${h}%`, animationDelay: `${i * 0.1}s` }}
          />
        ))}
      </div>
    );
  }
  if (index === 1) {
    return (
      <div className="flex h-full flex-col justify-center gap-2 px-8">
        {[1, 2, 3].map((n) => (
          <div key={n} className="h-3 rounded-full bg-ink/[0.06]">
            <div className="h-full rounded-full bg-teal/40" style={{ width: `${40 + n * 18}%` }} />
          </div>
        ))}
      </div>
    );
  }
  if (index === 2) {
    return (
      <div className="flex h-full items-center justify-center gap-3">
        <span className="rounded-xl border border-ink/10 bg-surface px-4 py-2 text-xs text-ink/50">
          Pending
        </span>
        <span className="h-px w-8 bg-ink/15" />
        <span className="rounded-xl bg-teal px-4 py-2 text-xs text-white">Approved</span>
      </div>
    );
  }
  return (
    <div className="flex h-full items-center justify-center">
      <div className="relative h-24 w-24">
        <div className="absolute inset-0 rounded-full border border-ink/10" />
        <div className="absolute inset-4 rounded-full border border-teal/30" />
        <div className="absolute inset-9 rounded-full bg-teal/20 animate-soft-pulse" />
      </div>
    </div>
  );
}
