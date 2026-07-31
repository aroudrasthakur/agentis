"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startSession() {
    setBusy(true);
    setError(null);
    try {
      const session = await api.createSession({ title: "Customer refund request" });
      router.push(`/session/${session.id}?invite=${encodeURIComponent(session.invite)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl flex-col justify-center px-6 pb-24">
      <div className="max-w-2xl animate-fade-up">
        <h1 className="font-display text-6xl leading-[1.05] tracking-tight text-ink md:text-7xl">
          Agentis
        </h1>
        <p className="mt-5 max-w-md text-lg text-ink/70">
          Humans and agents, one live session.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <Button size="lg" variant="teal" disabled={busy} onClick={startSession}>
            {busy ? "Starting…" : "Start session"}
          </Button>
          <Link href="/agents" className="text-sm text-ink/60 underline-offset-4 hover:underline">
            Browse agents
          </Link>
        </div>
        {error && <p className="mt-4 text-sm text-coral">{error}</p>}
      </div>
    </main>
  );
}
