"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { X } from "lucide-react";
import { api, type Agent, type GatheringAccessMode } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const ACCESS_MODES: { value: GatheringAccessMode; label: string; hint: string }[] = [
  {
    value: "owner_managed",
    label: "Owner managed",
    hint: "Gathering owners grant access to their own members and agents.",
  },
  {
    value: "centrally_managed",
    label: "Centrally managed",
    hint: "Only access managers and security admins may change access here.",
  },
];

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-ink">
        {label}
      </label>
      {hint && <p className="text-xs text-ink/50">{hint}</p>}
      {children}
    </div>
  );
}

function Section({
  step,
  title,
  description,
  children,
}: {
  step: number;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-ink/10 bg-surface/60 px-5 py-5">
      <div className="mb-4 flex items-baseline gap-3">
        <span className="text-[11px] font-medium tracking-[0.16em] text-ink/35">
          {String(step).padStart(2, "0")}
        </span>
        <div>
          <h2 className="font-display text-xl text-ink">{title}</h2>
          <p className="mt-1 text-sm text-ink/55">{description}</p>
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

export default function NewGatheringPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [accessMode, setAccessMode] = useState<GatheringAccessMode>("owner_managed");
  const [futureGrants, setFutureGrants] = useState(true);

  const [emailDraft, setEmailDraft] = useState("");
  const [emails, setEmails] = useState<string[]>([]);
  const [emailError, setEmailError] = useState<string | null>(null);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentIds, setAgentIds] = useState<string[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void (async () => {
      try {
        setAgents(await api.attachableAgents());
      } catch {
        setAgents([]);
      } finally {
        setAgentsLoading(false);
      }
    })();
  }, [router]);

  function addEmail() {
    const email = emailDraft.trim().toLowerCase();
    if (!email) return;
    if (!EMAIL_PATTERN.test(email)) {
      setEmailError("Enter a valid email address");
      return;
    }
    if (emails.includes(email)) {
      setEmailError("Already added");
      return;
    }
    setEmails((current) => [...current, email]);
    setEmailDraft("");
    setEmailError(null);
  }

  function toggleAgent(agentId: string) {
    setAgentIds((current) =>
      current.includes(agentId)
        ? current.filter((id) => id !== agentId)
        : [...current, agentId]
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.provisionGathering({
        name: name.trim(),
        description: description.trim() || undefined,
        access_mode: accessMode,
        future_grants_enabled: futureGrants,
        invite_emails: emails,
        agent_ids: agentIds,
      });
      router.push(`/gathering/${result.gathering.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create gathering");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 pb-20 pt-4">
      <div className="mb-8">
        <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Gatherings</p>
        <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Create gathering</h1>
        <p className="mt-2 max-w-xl text-sm text-ink/55">
          A gathering is a workspace with its own access roles. Set it up here — you can change
          everything later from the gathering page.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        <Section
          step={1}
          title="Identity"
          description="How this workspace appears across the dashboard."
        >
          <Field label="Name" htmlFor="gathering-name">
            <Input
              id="gathering-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Platform reliability"
              autoFocus
              required
            />
          </Field>
          <Field
            label="Description"
            hint="Optional. Shown on the dashboard card and gathering header."
            htmlFor="gathering-description"
          >
            <textarea
              id="gathering-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="What this gathering is for, and who belongs in it."
              className="scroll-area flex w-full resize-y rounded-md border border-ink/15 bg-surface/80 px-3 py-2 text-sm text-ink placeholder:text-ink/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
            />
          </Field>
        </Section>

        <Section
          step={2}
          title="Access policy"
          description="Applies to the managed roles created alongside this gathering."
        >
          <Field label="Access mode">
            <div className="grid gap-2 sm:grid-cols-2">
              {ACCESS_MODES.map((mode) => {
                const selected = accessMode === mode.value;
                return (
                  <button
                    key={mode.value}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setAccessMode(mode.value)}
                    className={cn(
                      "rounded-lg border px-3.5 py-3 text-left transition-colors",
                      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal/60",
                      selected
                        ? "border-teal/50 bg-teal/10"
                        : "border-ink/10 bg-surface/50 hover:border-ink/20"
                    )}
                  >
                    <span className="block text-sm font-medium text-ink">{mode.label}</span>
                    <span className="mt-1 block text-xs text-ink/50">{mode.hint}</span>
                  </button>
                );
              })}
            </div>
          </Field>

          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-ink/10 bg-surface/50 px-3.5 py-3">
            <input
              type="checkbox"
              checked={futureGrants}
              onChange={(e) => setFutureGrants(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-teal"
            />
            <span>
              <span className="block text-sm font-medium text-ink">Enable future grants</span>
              <span className="mt-1 block text-xs text-ink/50">
                Agents added later automatically inherit the access rules configured for this
                gathering.
              </span>
            </span>
          </label>
        </Section>

        <Section
          step={3}
          title="People"
          description="Invitations are created immediately; people join when they sign in."
        >
          <Field label="Invite by email" htmlFor="gathering-invite">
            <div className="flex gap-2">
              <Input
                id="gathering-invite"
                type="email"
                value={emailDraft}
                onChange={(e) => {
                  setEmailDraft(e.target.value);
                  setEmailError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addEmail();
                  }
                }}
                placeholder="teammate@company.com"
              />
              <Button type="button" variant="outline" onClick={addEmail}>
                Add
              </Button>
            </div>
          </Field>
          {emailError && <p className="text-xs text-coral">{emailError}</p>}
          {emails.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {emails.map((email) => (
                <li key={email}>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-ink/10 bg-surface/70 py-1 pl-3 pr-1.5 text-xs text-ink/75">
                    {email}
                    <button
                      type="button"
                      onClick={() => setEmails((c) => c.filter((e) => e !== email))}
                      aria-label={`Remove ${email}`}
                      className="rounded-full p-0.5 text-ink/40 hover:bg-ink/10 hover:text-ink"
                    >
                      <X className="h-3 w-3" aria-hidden />
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section
          step={4}
          title="Agents"
          description="Only deployed agents can be attached. You can add more at any time."
        >
          {agentsLoading ? (
            <p className="text-sm text-ink/45">Loading agents…</p>
          ) : agents.length === 0 ? (
            <p className="text-sm text-ink/45">
              No deployed agents yet.{" "}
              <Link href="/dashboard/guild" className="text-teal hover:underline">
                Set one up in the Guild
              </Link>
              .
            </p>
          ) : (
            <ul className="scroll-area max-h-72 space-y-2 overflow-y-auto pr-1">
              {agents.map((agent) => {
                const selected = agentIds.includes(agent.id);
                return (
                  <li key={agent.id}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg border px-3.5 py-3 transition-colors",
                        selected
                          ? "border-teal/50 bg-teal/10"
                          : "border-ink/10 bg-surface/50 hover:border-ink/20"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleAgent(agent.id)}
                        className="mt-0.5 h-4 w-4 accent-teal"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-ink">{agent.name}</span>
                          <Badge className="bg-ink/5 text-ink/60">{agent.org_tag}</Badge>
                        </span>
                        {agent.description && (
                          <span className="mt-1 line-clamp-2 block text-xs text-ink/50">
                            {agent.description}
                          </span>
                        )}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>

        {error && <p className="text-sm text-coral">{error}</p>}

        <div className="flex items-center justify-between gap-3">
          <Link href="/dashboard" className="text-sm text-ink/45 hover:text-ink">
            ← Cancel
          </Link>
          <Button type="submit" variant="teal" disabled={busy || !name.trim()}>
            {busy ? "Creating…" : "Create gathering"}
          </Button>
        </div>
      </form>
    </main>
  );
}
