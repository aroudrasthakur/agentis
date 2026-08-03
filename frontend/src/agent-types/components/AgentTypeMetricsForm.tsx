"use client";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import type {
  AgentMetricConfiguration,
  AgentMetricDefinition,
  MetricConfigurationEntry,
} from "@/agent-types/schemas";

function numberOrNull(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

export function AgentTypeMetricsForm({
  metrics,
  configuration,
  onChange,
}: {
  metrics: AgentMetricDefinition[];
  configuration: AgentMetricConfiguration;
  onChange: (key: string, entry: MetricConfigurationEntry) => void;
}) {
  if (!metrics.length) {
    return (
      <p className="text-sm text-ink/45">This agent type does not recommend any metrics yet.</p>
    );
  }

  return (
    <div className="space-y-3">
      {metrics.map((metric) => {
        const entry: MetricConfigurationEntry = configuration[metric.key] ?? {
          enabled: metric.required,
          targetValue: null,
          warningThreshold: null,
          criticalThreshold: null,
        };
        return (
          <div
            key={metric.key}
            className="rounded-xl border border-ink/10 bg-surface/70 px-4 py-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="inline-flex items-center gap-2 text-sm font-medium text-ink">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-teal"
                      checked={entry.enabled}
                      disabled={metric.required}
                      onChange={(event) =>
                        onChange(metric.key, { ...entry, enabled: event.target.checked })
                      }
                    />
                    {metric.label}
                  </label>
                  {metric.required ? (
                    <Badge className="bg-coral-soft text-coral-deep">Required</Badge>
                  ) : (
                    <Badge className="bg-ink/5 text-ink/50">Optional</Badge>
                  )}
                  <Badge className="bg-ink/5 text-ink/50">{metric.category}</Badge>
                </div>
                <p className="mt-1 text-xs text-ink/45">
                  {metric.unit} · {metric.direction.replace(/_/g, " ")}
                </p>
              </div>
            </div>

            {entry.enabled && (
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <div>
                  <p className="mb-1 text-[11px] uppercase tracking-[0.18em] text-ink/35">
                    Target
                  </p>
                  <Input
                    type="number"
                    value={entry.targetValue ?? ""}
                    onChange={(event) =>
                      onChange(metric.key, {
                        ...entry,
                        targetValue: numberOrNull(event.target.value),
                      })
                    }
                  />
                </div>
                <div>
                  <p className="mb-1 text-[11px] uppercase tracking-[0.18em] text-ink/35">
                    Warning
                  </p>
                  <Input
                    type="number"
                    value={entry.warningThreshold ?? ""}
                    onChange={(event) =>
                      onChange(metric.key, {
                        ...entry,
                        warningThreshold: numberOrNull(event.target.value),
                      })
                    }
                  />
                </div>
                <div>
                  <p className="mb-1 text-[11px] uppercase tracking-[0.18em] text-ink/35">
                    Critical
                  </p>
                  <Input
                    type="number"
                    value={entry.criticalThreshold ?? ""}
                    onChange={(event) =>
                      onChange(metric.key, {
                        ...entry,
                        criticalThreshold: numberOrNull(event.target.value),
                      })
                    }
                  />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
