"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { Agora } from "@/lib/api";
import { api } from "@/lib/api";
import { clearAuth, getStoredUser, isLoggedIn } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export default function DashboardPage() {
  const router = useRouter();
  const [agoras, setAgoras] = useState<Agora[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const user = getStoredUser();

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void (async () => {
      try {
        const list = await api.listAgoras();
        setAgoras(list);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load agoras");
      }
    })();
  }, [router]);

  async function createAgora() {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const agora = await api.createAgora({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setOpen(false);
      setName("");
      setDescription("");
      router.push(`/agora/${agora.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agora");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Dashboard</p>
          <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">
            Your Agoras
          </h1>
          <p className="mt-2 max-w-lg text-sm text-ink/55">
            Workspaces for training agents and multi-agent sessions.
            {user ? ` Signed in as ${user.display_name}.` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/guild">
            <Button variant="outline">Guild</Button>
          </Link>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="teal">New Agora</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create agora</DialogTitle>
              </DialogHeader>
              <div className="mt-3 space-y-3">
                <Input
                  placeholder="Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <Input
                  placeholder="Description (optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                <Button
                  variant="teal"
                  className="w-full"
                  disabled={busy || !name.trim()}
                  onClick={() => void createAgora()}
                >
                  {busy ? "Creating…" : "Create"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          <Button
            variant="ghost"
            onClick={() => {
              clearAuth();
              router.replace("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-coral">{error}</p>}

      {agoras.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ink/15 bg-white/50 px-8 py-16 text-center">
          <p className="font-display text-2xl text-ink">No agoras yet</p>
          <p className="mt-2 text-sm text-ink/50">
            Create a workspace, invite people, and add agents from the Guild.
          </p>
          <Button className="mt-6" variant="teal" onClick={() => setOpen(true)}>
            Create your first agora
          </Button>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agoras.map((agora) => (
            <li key={agora.id}>
              <Link
                href={`/agora/${agora.id}`}
                className="block rounded-xl border border-ink/10 bg-white/70 px-5 py-5 transition hover:border-teal/40 hover:bg-white"
              >
                <h2 className="font-display text-xl text-ink">{agora.name}</h2>
                {agora.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-ink/50">{agora.description}</p>
                )}
                <p className="mt-4 text-[11px] uppercase tracking-[0.16em] text-ink/35">
                  {agora.session_count} sessions · {agora.agent_count} agents ·{" "}
                  {agora.member_count} people
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
