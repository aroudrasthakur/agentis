"use client";

import { Badge } from "@/components/ui/badge";
import type { AgentTypeSummary } from "@/agent-types/schemas";

const RISK_STYLES: Record<string, string> = {
  low: "bg-teal-soft text-teal-deep",
  medium: "bg-ink/10 text-ink/60",
  high: "bg-coral-soft text-coral-deep",
  critical: "bg-coral text-white",
};

export function AgentTypeSelector({
  types,
  selectedTypeId,
  onSelect,
}: {
  types: AgentTypeSummary[];
  selectedTypeId?: string | null;
  onSelect: (type: AgentTypeSummary) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {types.map((type) => {
        const selected = type.id === selectedTypeId;
        return (
          <button
            key={`${type.id}-${type.version}`}
            type="button"
            onClick={() => onSelect(type)}
            className={`rounded-xl border px-4 py-4 text-left transition ${
              selected
                ? "border-teal bg-teal-soft/40"
                : "border-ink/10 bg-surface/70 hover:border-ink/20"
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-medium text-ink">{type.name}</h3>
              {type.builtIn ? (
                <Badge className="bg-ink/5 text-ink/50">System</Badge>
              ) : (
                <Badge className="bg-teal-soft text-teal-deep">Custom v{type.version}</Badge>
              )}
              <Badge className={RISK_STYLES[type.defaultRiskLevel] ?? "bg-ink/5 text-ink/50"}>
                {type.defaultRiskLevel} risk
              </Badge>
              {type.status !== "active" && (
                <Badge className="bg-ink/10 text-ink/60">{type.status}</Badge>
              )}
            </div>
            <p className="mt-2 text-sm text-ink/60">{type.description}</p>
            {type.useCases.length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-ink/45">
                {type.useCases.slice(0, 3).map((useCase) => (
                  <li key={useCase}>· {useCase}</li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-[11px] uppercase tracking-[0.18em] text-ink/35">
              Autonomy {type.defaultAutonomyLevel} · {type.parameterCount} parameters ·{" "}
              {type.metricCount} metrics
            </p>
          </button>
        );
      })}
    </div>
  );
}
