"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  AgentMetricDefinition,
  AgentParameterSection,
  AgentParameterType,
  AgentTypeParameterDefinition,
  AgentTypeSummary,
  CustomAgentType,
  RiskLevel,
} from "@/agent-types/schemas";
import { SECTION_LABELS, SECTION_ORDER } from "@/agent-types/schemas";
import { AgentTypeConfigForm } from "./AgentTypeConfigForm";

const PARAMETER_TYPES: AgentParameterType[] = [
  "text",
  "textarea",
  "number",
  "boolean",
  "select",
  "multi_select",
  "json",
  "tool_selector",
  "agent_selector",
  "model_selector",
  "data_source_selector",
];

const METRIC_CATEGORIES = [
  "quality",
  "task_success",
  "reliability",
  "performance",
  "cost",
  "safety",
  "user_experience",
  "business",
] as const;

const METRIC_UNITS = [
  "percentage",
  "count",
  "milliseconds",
  "seconds",
  "currency",
  "score",
  "ratio",
] as const;

const RISK_LEVELS: RiskLevel[] = ["low", "medium", "high", "critical"];

const selectClass =
  "w-full rounded-md border border-ink/15 bg-surface/80 px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal";

export interface CustomTypeDraft {
  name: string;
  description: string;
  icon: string;
  baseTypeId: string;
  defaultAutonomyLevel: number;
  defaultRiskLevel: RiskLevel;
  status: "draft" | "active";
  parameterDefinitions: AgentTypeParameterDefinition[];
  metricDefinitions: AgentMetricDefinition[];
}

export function emptyDraft(): CustomTypeDraft {
  return {
    name: "",
    description: "",
    icon: "",
    baseTypeId: "",
    defaultAutonomyLevel: 1,
    defaultRiskLevel: "low",
    status: "draft",
    parameterDefinitions: [],
    metricDefinitions: [],
  };
}

export function draftFromCustomType(type: CustomAgentType): CustomTypeDraft {
  return {
    name: type.name,
    description: type.description ?? "",
    icon: type.icon ?? "",
    baseTypeId: type.baseTypeId ?? "",
    defaultAutonomyLevel: type.defaultAutonomyLevel,
    defaultRiskLevel: type.defaultRiskLevel,
    status: type.status === "archived" ? "draft" : type.status,
    parameterDefinitions: type.parameterDefinitions,
    metricDefinitions: type.metricDefinitions,
  };
}

function newParameter(index: number): AgentTypeParameterDefinition {
  return {
    id: "",
    key: `parameter_${index + 1}`,
    label: `Parameter ${index + 1}`,
    description: "",
    type: "text",
    section: "custom",
    required: false,
    defaultValue: null,
    options: [],
    validation: null,
    visibleWhen: null,
    deploymentBlocking: false,
    editableAfterDeployment: true,
    inherited: false,
  };
}

function newMetric(index: number): AgentMetricDefinition {
  return {
    id: "",
    key: `metric_${index + 1}`,
    label: `Metric ${index + 1}`,
    description: "",
    category: "quality",
    unit: "percentage",
    direction: "higher_is_better",
    targetValue: null,
    warningThreshold: null,
    criticalThreshold: null,
    required: false,
  };
}

export function CustomAgentTypeBuilder({
  draft,
  baseTypes,
  saving,
  lockedNotice,
  onChange,
  onSave,
  onCancel,
}: {
  draft: CustomTypeDraft;
  baseTypes: AgentTypeSummary[];
  saving?: boolean;
  lockedNotice?: string | null;
  onChange: (next: CustomTypeDraft) => void;
  onSave: () => void;
  onCancel?: () => void;
}) {
  const [showPreview, setShowPreview] = useState(false);

  const previewDefinition = useMemo(
    () => ({
      id: "preview",
      name: draft.name || "Untitled type",
      slug: "preview",
      description: draft.description,
      version: 1,
      status: "draft" as const,
      builtIn: false,
      baseTypeId: draft.baseTypeId || null,
      icon: draft.icon || null,
      useCases: [],
      capabilities: [],
      defaultAutonomyLevel: draft.defaultAutonomyLevel,
      defaultRiskLevel: draft.defaultRiskLevel,
      parameterDefinitions: draft.parameterDefinitions,
      metricDefinitions: draft.metricDefinitions,
    }),
    [draft]
  );

  function updateParameter(index: number, patch: Partial<AgentTypeParameterDefinition>) {
    const next = [...draft.parameterDefinitions];
    next[index] = { ...next[index], ...patch };
    onChange({ ...draft, parameterDefinitions: next });
  }

  function moveParameter(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= draft.parameterDefinitions.length) return;
    const next = [...draft.parameterDefinitions];
    [next[index], next[target]] = [next[target], next[index]];
    onChange({ ...draft, parameterDefinitions: next });
  }

  function updateMetric(index: number, patch: Partial<AgentMetricDefinition>) {
    const next = [...draft.metricDefinitions];
    next[index] = { ...next[index], ...patch };
    onChange({ ...draft, metricDefinitions: next });
  }

  return (
    <div className="space-y-6">
      {lockedNotice && (
        <p className="rounded-lg border border-ink/10 bg-surface/70 px-3 py-2 text-xs text-ink/55">
          {lockedNotice}
        </p>
      )}

      <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
        <h3 className="mb-4 font-display text-lg text-ink">Type details</h3>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="mb-1 text-xs text-ink/45">Name</p>
            <Input
              value={draft.name}
              onChange={(event) => onChange({ ...draft, name: event.target.value })}
            />
          </div>
          <div>
            <p className="mb-1 text-xs text-ink/45">Icon (optional)</p>
            <Input
              value={draft.icon}
              placeholder="e.g. shield"
              onChange={(event) => onChange({ ...draft, icon: event.target.value })}
            />
          </div>
          <div className="md:col-span-2">
            <p className="mb-1 text-xs text-ink/45">Description</p>
            <textarea
              className={`${selectClass} min-h-[72px]`}
              value={draft.description}
              onChange={(event) => onChange({ ...draft, description: event.target.value })}
            />
          </div>
          <div>
            <p className="mb-1 text-xs text-ink/45">Base type to extend</p>
            <select
              className={selectClass}
              value={draft.baseTypeId}
              onChange={(event) => onChange({ ...draft, baseTypeId: event.target.value })}
            >
              <option value="">None (shared base parameters only)</option>
              {baseTypes
                .filter((type) => type.builtIn && type.id !== "custom")
                .map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-1 text-xs text-ink/45">Default autonomy</p>
              <select
                className={selectClass}
                value={draft.defaultAutonomyLevel}
                onChange={(event) =>
                  onChange({ ...draft, defaultAutonomyLevel: Number(event.target.value) })
                }
              >
                {[0, 1, 2, 3, 4, 5].map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <p className="mb-1 text-xs text-ink/45">Default risk</p>
              <select
                className={selectClass}
                value={draft.defaultRiskLevel}
                onChange={(event) =>
                  onChange({ ...draft, defaultRiskLevel: event.target.value as RiskLevel })
                }
              >
                {RISK_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <p className="mt-4 text-xs text-ink/40">
          Custom types are declarative only. Human review and intervention stay with the
          application runtime, so approval and reviewer fields cannot be added here.
        </p>
      </section>

      <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-display text-lg text-ink">Parameters</h3>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onChange({
                ...draft,
                parameterDefinitions: [
                  ...draft.parameterDefinitions,
                  newParameter(draft.parameterDefinitions.length),
                ],
              })
            }
          >
            Add parameter
          </Button>
        </div>

        {draft.parameterDefinitions.length === 0 && (
          <p className="text-sm text-ink/45">
            No parameters yet. Inherited base parameters still apply to every agent.
          </p>
        )}

        <div className="space-y-4">
          {draft.parameterDefinitions.map((parameter, index) => (
            <div key={index} className="rounded-lg border border-ink/10 px-4 py-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <Badge className="bg-ink/5 text-ink/50">#{index + 1}</Badge>
                <div className="flex gap-1">
                  <Button size="sm" variant="ghost" onClick={() => moveParameter(index, -1)}>
                    ↑
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => moveParameter(index, 1)}>
                    ↓
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      onChange({
                        ...draft,
                        parameterDefinitions: draft.parameterDefinitions.filter(
                          (_, position) => position !== index
                        ),
                      })
                    }
                  >
                    Remove
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-1 text-xs text-ink/45">Key</p>
                  <Input
                    value={parameter.key}
                    onChange={(event) => updateParameter(index, { key: event.target.value })}
                  />
                </div>
                <div>
                  <p className="mb-1 text-xs text-ink/45">Label</p>
                  <Input
                    value={parameter.label}
                    onChange={(event) => updateParameter(index, { label: event.target.value })}
                  />
                </div>
                <div>
                  <p className="mb-1 text-xs text-ink/45">Type</p>
                  <select
                    className={selectClass}
                    value={parameter.type}
                    onChange={(event) =>
                      updateParameter(index, {
                        type: event.target.value as AgentParameterType,
                      })
                    }
                  >
                    {PARAMETER_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <p className="mb-1 text-xs text-ink/45">Section</p>
                  <select
                    className={selectClass}
                    value={parameter.section}
                    onChange={(event) =>
                      updateParameter(index, {
                        section: event.target.value as AgentParameterSection,
                      })
                    }
                  >
                    {SECTION_ORDER.map((section) => (
                      <option key={section} value={section}>
                        {SECTION_LABELS[section]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-2">
                  <p className="mb-1 text-xs text-ink/45">Description</p>
                  <Input
                    value={parameter.description ?? ""}
                    onChange={(event) =>
                      updateParameter(index, { description: event.target.value })
                    }
                  />
                </div>

                {(parameter.type === "select" || parameter.type === "multi_select") && (
                  <div className="md:col-span-2">
                    <p className="mb-1 text-xs text-ink/45">
                      Allowed values (one `value|Label` per line)
                    </p>
                    <textarea
                      className={`${selectClass} min-h-[72px] font-mono text-xs`}
                      value={(parameter.options ?? [])
                        .map((option) => `${option.value}|${option.label}`)
                        .join("\n")}
                      onChange={(event) =>
                        updateParameter(index, {
                          options: event.target.value
                            .split("\n")
                            .map((line) => line.trim())
                            .filter(Boolean)
                            .map((line) => {
                              const [value, label] = line.split("|");
                              return { value: value.trim(), label: (label ?? value).trim() };
                            }),
                        })
                      }
                    />
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3 md:col-span-2">
                  <div>
                    <p className="mb-1 text-xs text-ink/45">Min / minLength</p>
                    <Input
                      type="number"
                      value={
                        parameter.type === "number"
                          ? (parameter.validation?.min ?? "")
                          : (parameter.validation?.minLength ?? "")
                      }
                      onChange={(event) => {
                        const raw = event.target.value;
                        const value = raw === "" ? null : Number(raw);
                        updateParameter(index, {
                          validation: {
                            ...(parameter.validation ?? {}),
                            ...(parameter.type === "number"
                              ? { min: value }
                              : { minLength: value }),
                          },
                        });
                      }}
                    />
                  </div>
                  <div>
                    <p className="mb-1 text-xs text-ink/45">Max / maxLength</p>
                    <Input
                      type="number"
                      value={
                        parameter.type === "number"
                          ? (parameter.validation?.max ?? "")
                          : (parameter.validation?.maxLength ?? "")
                      }
                      onChange={(event) => {
                        const raw = event.target.value;
                        const value = raw === "" ? null : Number(raw);
                        updateParameter(index, {
                          validation: {
                            ...(parameter.validation ?? {}),
                            ...(parameter.type === "number"
                              ? { max: value }
                              : { maxLength: value }),
                          },
                        });
                      }}
                    />
                  </div>
                </div>

                <div className="md:col-span-2">
                  <p className="mb-1 text-xs text-ink/45">
                    Visible when (parameter key, operator, value)
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    <Input
                      placeholder="parameter_key"
                      value={parameter.visibleWhen?.parameterKey ?? ""}
                      onChange={(event) =>
                        updateParameter(index, {
                          visibleWhen: event.target.value
                            ? {
                                parameterKey: event.target.value,
                                operator: parameter.visibleWhen?.operator ?? "truthy",
                                value: parameter.visibleWhen?.value,
                              }
                            : null,
                        })
                      }
                    />
                    <select
                      className={selectClass}
                      value={parameter.visibleWhen?.operator ?? "truthy"}
                      disabled={!parameter.visibleWhen}
                      onChange={(event) =>
                        parameter.visibleWhen &&
                        updateParameter(index, {
                          visibleWhen: {
                            ...parameter.visibleWhen,
                            operator: event.target
                              .value as NonNullable<
                              AgentTypeParameterDefinition["visibleWhen"]
                            >["operator"],
                          },
                        })
                      }
                    >
                      <option value="truthy">truthy</option>
                      <option value="equals">equals</option>
                      <option value="not_equals">not_equals</option>
                      <option value="contains">contains</option>
                    </select>
                    <Input
                      placeholder="value"
                      value={String(parameter.visibleWhen?.value ?? "")}
                      disabled={!parameter.visibleWhen}
                      onChange={(event) =>
                        parameter.visibleWhen &&
                        updateParameter(index, {
                          visibleWhen: {
                            ...parameter.visibleWhen,
                            value: event.target.value,
                          },
                        })
                      }
                    />
                  </div>
                </div>

                <div className="flex flex-wrap gap-4 md:col-span-2">
                  <label className="inline-flex items-center gap-2 text-xs text-ink/60">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-teal"
                      checked={parameter.required}
                      onChange={(event) =>
                        updateParameter(index, { required: event.target.checked })
                      }
                    />
                    Required
                  </label>
                  <label className="inline-flex items-center gap-2 text-xs text-ink/60">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-teal"
                      checked={Boolean(parameter.deploymentBlocking)}
                      onChange={(event) =>
                        updateParameter(index, { deploymentBlocking: event.target.checked })
                      }
                    />
                    Blocks deployment
                  </label>
                  <label className="inline-flex items-center gap-2 text-xs text-ink/60">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-teal"
                      checked={parameter.editableAfterDeployment !== false}
                      onChange={(event) =>
                        updateParameter(index, {
                          editableAfterDeployment: event.target.checked,
                        })
                      }
                    />
                    Editable after deployment
                  </label>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-display text-lg text-ink">Recommended metrics</h3>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onChange({
                ...draft,
                metricDefinitions: [
                  ...draft.metricDefinitions,
                  newMetric(draft.metricDefinitions.length),
                ],
              })
            }
          >
            Add metric
          </Button>
        </div>

        <div className="space-y-3">
          {draft.metricDefinitions.map((metric, index) => (
            <div
              key={index}
              className="grid gap-3 rounded-lg border border-ink/10 px-4 py-3 md:grid-cols-5"
            >
              <Input
                value={metric.key}
                onChange={(event) => updateMetric(index, { key: event.target.value })}
              />
              <Input
                value={metric.label}
                onChange={(event) => updateMetric(index, { label: event.target.value })}
              />
              <select
                className={selectClass}
                value={metric.category}
                onChange={(event) =>
                  updateMetric(index, {
                    category: event.target.value as AgentMetricDefinition["category"],
                  })
                }
              >
                {METRIC_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
              <select
                className={selectClass}
                value={metric.unit}
                onChange={(event) =>
                  updateMetric(index, {
                    unit: event.target.value as AgentMetricDefinition["unit"],
                  })
                }
              >
                {METRIC_UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </select>
              <div className="flex items-center justify-between gap-2">
                <label className="inline-flex items-center gap-2 text-xs text-ink/60">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-teal"
                    checked={metric.required}
                    onChange={(event) =>
                      updateMetric(index, { required: event.target.checked })
                    }
                  />
                  Required
                </label>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    onChange({
                      ...draft,
                      metricDefinitions: draft.metricDefinitions.filter(
                        (_, position) => position !== index
                      ),
                    })
                  }
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <Button variant="teal" disabled={saving || !draft.name.trim()} onClick={onSave}>
          {saving ? "Saving…" : "Save type"}
        </Button>
        <Button variant="outline" onClick={() => setShowPreview((value) => !value)}>
          {showPreview ? "Hide preview" : "Preview setup form"}
        </Button>
        <label className="inline-flex items-center gap-2 text-xs text-ink/60">
          <input
            type="checkbox"
            className="h-4 w-4 accent-teal"
            checked={draft.status === "active"}
            onChange={(event) =>
              onChange({ ...draft, status: event.target.checked ? "active" : "draft" })
            }
          />
          Publish as active (draft types cannot be deployed)
        </label>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>

      {showPreview && (
        <section className="space-y-3">
          <h3 className="font-display text-lg text-ink">Generated setup form</h3>
          <AgentTypeConfigForm
            definition={previewDefinition}
            configuration={{}}
            issues={[]}
            catalogs={null}
            onChange={() => undefined}
          />
        </section>
      )}
    </div>
  );
}
