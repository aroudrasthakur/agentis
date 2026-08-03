"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ParameterDiff, TypeMigrationPreview } from "@/agent-types/schemas";

function DiffList({ title, items }: { title: string; items: ParameterDiff[] }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.18em] text-ink/35">
        {title} ({items.length})
      </p>
      {items.length ? (
        <ul className="mt-1 space-y-1 text-xs text-ink/60">
          {items.map((item) => (
            <li key={item.key} className="flex flex-wrap items-center gap-2">
              <span>· {item.label}</span>
              {item.required && (
                <Badge className="bg-coral-soft text-coral-deep">Required</Badge>
              )}
              <span className="text-ink/30">{item.section}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-xs text-ink/35">None</p>
      )}
    </div>
  );
}

export function AgentTypeVersionMigration({
  preview,
  busy,
  onMigrate,
}: {
  preview: TypeMigrationPreview;
  busy?: boolean;
  onMigrate: () => void;
}) {
  const upToDate = preview.fromVersion === preview.toVersion;

  return (
    <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-lg text-ink">Type version</h3>
          <p className="mt-1 text-xs text-ink/50">
            This agent uses version {preview.fromVersion ?? "?"}; the latest is version{" "}
            {preview.toVersion}.
            {" "}
            Deployed configurations are never changed automatically.
          </p>
        </div>
        {!upToDate && (
          <Button variant="outline" size="sm" disabled={busy} onClick={onMigrate}>
            {busy ? "Migrating…" : `Migrate to v${preview.toVersion}`}
          </Button>
        )}
      </div>

      {!upToDate && (
        <>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <DiffList title="Added" items={preview.addedParameters} />
            <DiffList title="Removed" items={preview.removedParameters} />
            <DiffList title="Changed" items={preview.changedParameters} />
          </div>
          {preview.newlyRequiredParameters.length > 0 && (
            <p className="mt-3 text-xs text-coral">
              Newly required and unset: {preview.newlyRequiredParameters.join(", ")}. Deployment
              stays blocked until these are configured.
            </p>
          )}
        </>
      )}
    </section>
  );
}
