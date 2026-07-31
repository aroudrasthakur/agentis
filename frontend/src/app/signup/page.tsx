"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { setAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SignupPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.signup({
        email,
        display_name: displayName || email.split("@")[0],
        password,
      });
      setAuth(res.access_token, res.user);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md flex-col justify-center px-6 pb-16">
      <h1 className="font-display text-4xl tracking-tight text-ink">Create account</h1>
      <p className="mt-2 text-sm text-ink/55">Start building Gatherings for your agents.</p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <label className="block text-xs text-ink/55">
          Display name
          <Input
            className="mt-1"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ada"
          />
        </label>
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
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            required
          />
        </label>
        {error && <p className="text-sm text-coral">{error}</p>}
        <Button type="submit" variant="teal" className="w-full" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-ink/50">
        Already have an account?{" "}
        <Link href="/login" className="text-teal underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </main>
  );
}
