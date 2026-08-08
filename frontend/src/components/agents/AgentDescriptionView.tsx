"use client";

import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  AGENT_DEPLOYMENT_STATUS_STYLES,
  DEFAULT_AGENT_DEPLOYMENT_STATUS_STYLE,
} from "@/components/agents/agent-description-styles";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AgentDescriptionProfile } from "@/lib/api";

export function AgentDescriptionView({
  profile,
  showActions,
}: {
  profile: AgentDescriptionProfile;
  showActions?: boolean;
}) {
  const hasDescription = Boolean(profile.description?.trim());

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-ink/40">Agent</p>
            <h1 className="font-display text-3xl tracking-tight text-ink">{profile.name}</h1>
            <p className="mt-1 text-xs text-ink/45">{profile.agent_key}</p>
          </div>
          <Badge
            className={
              AGENT_DEPLOYMENT_STATUS_STYLES[profile.deployment_status] ??
              DEFAULT_AGENT_DEPLOYMENT_STATUS_STYLE
            }
          >
            {profile.deployment_status_label}
          </Badge>
        </div>

        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-[11px] uppercase tracking-[0.14em] text-ink/35">Agent type</dt>
            <dd className="text-ink/75">
              {profile.type_name ?? "Not selected"}
              {profile.type_version != null ? ` · v${profile.type_version}` : ""}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-[0.14em] text-ink/35">Hosting</dt>
            <dd className="text-ink/75">{profile.hosting_mode}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-[0.14em] text-ink/35">Organization</dt>
            <dd className="text-ink/75">{profile.org_tag}</dd>
          </div>
        </dl>

        {profile.highlights.length > 0 && (
          <ul className="mt-4 space-y-1 text-xs text-ink/55">
            {profile.highlights.map((line) => (
              <li key={line}>· {line}</li>
            ))}
          </ul>
        )}

        {showActions && (
          <div className="mt-4 flex flex-wrap gap-2">
            <Button asChild size="sm" variant="outline">
              <Link href={`/dashboard/guild/agents/${profile.agent_id}/setup`}>Edit setup</Link>
            </Button>
          </div>
        )}
      </header>

      <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="font-display text-xl text-ink">Description</h2>
          <Badge className="bg-ink/5 text-ink/50">
            {profile.description_format === "markdown" ? "Markdown" : "Plain text"}
          </Badge>
        </div>
        {!hasDescription ? (
          <p className="text-sm text-ink/45">
            No description yet. Add one during setup so teammates know what this agent is for.
          </p>
        ) : profile.description_format === "markdown" ? (
          <div className="prose prose-sm prose-invert max-w-none text-ink/80">
            <ReactMarkdown>{profile.description ?? ""}</ReactMarkdown>
          </div>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink/75">
            {profile.description}
          </p>
        )}
      </section>

      {profile.configuration_sections.length > 0 && (
        <section className="space-y-4">
          <div>
            <h2 className="font-display text-xl text-ink">Configuration</h2>
            <p className="mt-1 text-sm text-ink/55">
              Values from the agent type setup, grouped by section. Only fields visible for the
              current configuration are shown.
            </p>
          </div>
          {profile.configuration_sections.map((section) => (
            <div
              key={section.section}
              className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-4"
            >
              <h3 className="font-medium text-ink">{section.section_label}</h3>
              <dl className="mt-3 divide-y divide-ink/5">
                {section.fields.map((field) => (
                  <div
                    key={field.key}
                    className="grid gap-1 py-3 sm:grid-cols-[minmax(0,220px)_1fr]"
                  >
                    <dt className="text-sm font-medium text-ink/70">{field.label}</dt>
                    <dd
                      className={`text-sm ${field.is_set ? "text-ink/80 whitespace-pre-wrap" : "text-ink/35 italic"}`}
                    >
                      {field.value_display}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </section>
      )}

      {profile.metrics.length > 0 && (
        <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
          <h2 className="font-display text-xl text-ink">Metrics</h2>
          <ul className="mt-3 space-y-2">
            {profile.metrics.map((metric) => (
              <li
                key={metric.key}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-ink/5 px-3 py-2 text-sm"
              >
                <span className="text-ink/80">{metric.label}</span>
                <span className="text-xs text-ink/45">
                  {metric.enabled ? "Enabled" : "Off"}
                  {metric.required ? " · Required" : ""}
                  {metric.target_display ? ` · Target ${metric.target_display}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(profile.capabilities.length > 0 || profile.tags.length > 0 || profile.notes) && (
        <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
          <h2 className="font-display text-xl text-ink">Record details</h2>
          {profile.capabilities.length > 0 && (
            <p className="mt-2 text-sm text-ink/70">
              <span className="font-medium text-ink/55">Capabilities: </span>
              {profile.capabilities.join(", ")}
            </p>
          )}
          {profile.tags.length > 0 && (
            <p className="mt-2 text-sm text-ink/70">
              <span className="font-medium text-ink/55">Tags: </span>
              {profile.tags.join(", ")}
            </p>
          )}
          {profile.notes && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-ink/70">
              <span className="font-medium text-ink/55">Notes: </span>
              {profile.notes}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
