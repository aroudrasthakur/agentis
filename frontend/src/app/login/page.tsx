"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { setAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login({ email, password });
      setAuth(res.access_token, res.user, res.session_role ?? null);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md flex-col justify-center px-6 pb-16">
      <h1 className="font-display text-4xl tracking-tight text-ink">Sign in</h1>
      <p className="mt-2 text-sm text-ink/55">Enter your dashboard of Gatherings.</p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <label className="block text-xs text-ink/55">
          Email
          <Input
            className="mt-1"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className="block text-xs text-ink/55">
          Password
          <Input
            className="mt-1"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="text-sm text-coral">{error}</p>}
        <Button type="submit" variant="teal" className="w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-ink/50">
        No account?{" "}
        <Link href="/signup" className="text-teal underline-offset-4 hover:underline">
          Create one
        </Link>
      </p>
    </main>
  );
}
