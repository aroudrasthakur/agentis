"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { User } from "@/lib/api";
import { api } from "@/lib/api";
import { isLoggedIn, setAuth, getToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [organization, setOrganization] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void (async () => {
      try {
        const me = await api.me();
        setUser(me);
        setDisplayName(me.display_name || "");
        setBio(me.bio || "");
        setOrganization(me.organization || "");
        setTitle(me.title || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load profile");
      }
    })();
  }, [router]);

  async function save() {
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      const next = await api.updateMe({
        display_name: displayName.trim(),
        bio: bio.trim() || undefined,
        organization: organization.trim() || undefined,
        title: title.trim() || undefined,
      });
      setUser(next);
      const token = getToken();
      if (token) setAuth(token, next);
      setSaved("Profile saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!user && !error) {
    return <main className="px-6 py-10 text-ink/50">Loading profile…</main>;
  }

  return (
    <main className="mx-auto max-w-xl px-6 pb-20 pt-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Account</p>
      <h1 className="mt-2 font-display text-4xl tracking-tight text-ink">Your profile</h1>
      <p className="mt-2 text-sm text-ink/55">
        Stored person information shown in gatherings you join.
      </p>

      <div className="mt-8 space-y-4">
        <label className="block text-xs text-ink/55">
          Email
          <Input className="mt-1" value={user?.email || ""} disabled />
        </label>
        <label className="block text-xs text-ink/55">
          Display name
          <Input
            className="mt-1"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </label>
        <label className="block text-xs text-ink/55">
          Title / role
          <Input
            className="mt-1"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Oversight lead"
          />
        </label>
        <label className="block text-xs text-ink/55">
          Organization
          <Input
            className="mt-1"
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
          />
        </label>
        <label className="block text-xs text-ink/55">
          Bio
          <textarea
            className="mt-1 min-h-[100px] w-full rounded-md border border-ink/15 bg-surface px-3 py-2 text-sm"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Short note about how you work with agents…"
          />
        </label>
        {error && <p className="text-sm text-coral">{error}</p>}
        {saved && <p className="text-sm text-teal-deep">{saved}</p>}
        <Button variant="teal" disabled={busy || !displayName.trim()} onClick={() => void save()}>
          {busy ? "Saving…" : "Save profile"}
        </Button>
      </div>
    </main>
  );
}
