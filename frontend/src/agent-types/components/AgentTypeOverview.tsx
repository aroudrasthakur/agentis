"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AgentTypeDefinition } from "@/agent-types/schemas";

export function AgentTypeOverview({
  definition,
  onChangeType,
}: {
  definition: AgentTypeDefinition;
  onChangeType?: () => void;
}) {
  return (
    <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-xl text-ink">{definition.name}</h2>
            <Badge className="bg-ink/5 text-ink/50">v{definition.version}</Badge>
            {definition.builtIn ? (
              <Badge className="bg-ink/5 text-ink/50">Read-only system type</Badge>
            ) : (
              <Badge className="bg-teal-soft text-teal-deep">Custom type</Badge>
            )}
            {definition.status !== "active" && (
              <Badge className="bg-coral-soft text-coral-deep">{definition.status}</Badge>
            )}
          </div>
          <p className="mt-2 max-w-2xl text-sm text-ink/60">{definition.description}</p>
        </div>
        {onChangeType && (
          <Button variant="outline" size="sm" onClick={onChangeType}>
            Change type
          </Button>
        )}
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-ink/35">Use cases</p>
          <ul className="mt-1 space-y-1 text-xs text-ink/55">
            {definition.useCases.length ? (
              definition.useCases.map((item) => <li key={item}>· {item}</li>)
            ) : (
              <li className="text-ink/35">Defined by this custom type</li>
            )}
          </ul>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-ink/35">
            Expected capabilities
          </p>
          <ul className="mt-1 space-y-1 text-xs text-ink/55">
            {definition.capabilities.length ? (
              definition.capabilities.map((item) => <li key={item}>· {item}</li>)
            ) : (
              <li className="text-ink/35">Defined by this custom type</li>
            )}
          </ul>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-ink/35">Type defaults</p>
          <p className="mt-1 text-xs text-ink/55">
            Risk {definition.defaultRiskLevel} · Autonomy {definition.defaultAutonomyLevel}
          </p>
          <p className="mt-1 text-xs text-ink/45">
            {definition.parameterDefinitions.length} parameters ·{" "}
            {definition.metricDefinitions.length} recommended metrics
          </p>
        </div>
      </div>
    </section>
  );
}
