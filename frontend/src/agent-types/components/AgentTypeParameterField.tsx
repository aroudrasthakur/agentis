"use client";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import type {
  AgentTypeParameterDefinition,
  SelectorCatalogs,
  SelectorOption,
  ValidationIssue,
} from "@/agent-types/schemas";
import { isDeploymentBlocking } from "@/agent-types/utils";

const selectClass =
  "w-full rounded-md border border-ink/15 bg-surface/80 px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal";

function catalogFor(
  parameter: AgentTypeParameterDefinition,
  catalogs: SelectorCatalogs | null
): SelectorOption[] {
  if (!catalogs) return [];
  switch (parameter.type) {
    case "tool_selector":
      return catalogs.tools;
    case "agent_selector":
      return catalogs.agents;
    case "model_selector":
      return catalogs.models;
    case "data_source_selector":
      return catalogs.dataSources;
    default:
      return [];
  }
}

function MultiSelect({
  options,
  value,
  onChange,
  emptyHint,
}: {
  options: SelectorOption[];
  value: string[];
  onChange: (next: string[]) => void;
  emptyHint: string;
}) {
  if (!options.length) {
    return <p className="text-xs text-ink/45">{emptyHint}</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const selected = value.includes(option.value);
        return (
          <button
            key={option.value}
            type="button"
            onClick={() =>
              onChange(
                selected
                  ? value.filter((item) => item !== option.value)
                  : [...value, option.value]
              )
            }
            className={`rounded-md border px-2.5 py-1 text-xs transition ${
              selected
                ? "border-teal bg-teal-soft text-teal-deep"
                : "border-ink/15 text-ink/60 hover:bg-ink/5"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function AgentTypeParameterField({
  parameter,
  value,
  issues,
  catalogs,
  disabled,
  onChange,
}: {
  parameter: AgentTypeParameterDefinition;
  value: unknown;
  issues: ValidationIssue[];
  catalogs: SelectorCatalogs | null;
  disabled?: boolean;
  onChange: (key: string, value: unknown) => void;
}) {
  const errors = issues.filter((issue) => issue.severity === "error");
  const warnings = issues.filter((issue) => issue.severity === "warning");
  const asArray = Array.isArray(value) ? (value as unknown[]).map(String) : [];

  function renderControl() {
    switch (parameter.type) {
      case "textarea":
        return (
          <textarea
            className={`${selectClass} min-h-[96px]`}
            value={typeof value === "string" ? value : ""}
            disabled={disabled}
            maxLength={parameter.validation?.maxLength ?? undefined}
            onChange={(event) => onChange(parameter.key, event.target.value)}
          />
        );
      case "number":
        return (
          <Input
            type="number"
            value={value === null || value === undefined ? "" : String(value)}
            disabled={disabled}
            min={parameter.validation?.min ?? undefined}
            max={parameter.validation?.max ?? undefined}
            onChange={(event) =>
              onChange(
                parameter.key,
                event.target.value === "" ? null : Number(event.target.value)
              )
            }
          />
        );
      case "boolean":
        return (
          <label className="inline-flex items-center gap-2 text-sm text-ink/70">
            <input
              type="checkbox"
              className="h-4 w-4 accent-teal"
              checked={Boolean(value)}
              disabled={disabled}
              onChange={(event) => onChange(parameter.key, event.target.checked)}
            />
            {Boolean(value) ? "Enabled" : "Disabled"}
          </label>
        );
      case "select":
        return (
          <select
            className={selectClass}
            value={value === null || value === undefined ? "" : String(value)}
            disabled={disabled}
            onChange={(event) => onChange(parameter.key, event.target.value || null)}
          >
            <option value="">Not set</option>
            {(parameter.options ?? []).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );
      case "multi_select":
        return (
          <MultiSelect
            options={parameter.options ?? []}
            value={asArray}
            onChange={(next) => onChange(parameter.key, next)}
            emptyHint="No options defined for this parameter."
          />
        );
      case "json":
        return (
          <textarea
            className={`${selectClass} min-h-[96px] font-mono text-xs`}
            value={
              typeof value === "string"
                ? value
                : value === null || value === undefined
                  ? ""
                  : JSON.stringify(value, null, 2)
            }
            disabled={disabled}
            spellCheck={false}
            onChange={(event) => {
              const text = event.target.value;
              try {
                onChange(parameter.key, text.trim() ? JSON.parse(text) : null);
              } catch {
                onChange(parameter.key, text);
              }
            }}
          />
        );
      case "tool_selector":
      case "agent_selector":
      case "data_source_selector":
        return (
          <MultiSelect
            options={catalogFor(parameter, catalogs)}
            value={asArray}
            onChange={(next) => onChange(parameter.key, next)}
            emptyHint="Nothing available to select yet."
          />
        );
      case "model_selector":
        return (
          <select
            className={selectClass}
            value={asArray[0] ?? ""}
            disabled={disabled}
            onChange={(event) =>
              onChange(parameter.key, event.target.value ? [event.target.value] : [])
            }
          >
            <option value="">Not set</option>
            {catalogFor(parameter, catalogs).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );
      default:
        return (
          <Input
            value={typeof value === "string" ? value : ""}
            disabled={disabled}
            maxLength={parameter.validation?.maxLength ?? undefined}
            onChange={(event) => onChange(parameter.key, event.target.value)}
          />
        );
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm font-medium text-ink">{parameter.label}</label>
        {parameter.required ? (
          <Badge className="bg-coral-soft text-coral-deep">Required</Badge>
        ) : (
          <Badge className="bg-ink/5 text-ink/50">Optional</Badge>
        )}
        {isDeploymentBlocking(parameter) && (
          <Badge className="bg-ink/10 text-ink/60">Blocks deployment</Badge>
        )}
        {parameter.inherited && (
          <Badge className="bg-teal-soft text-teal-deep">Inherited</Badge>
        )}
      </div>
      {parameter.description && (
        <p className="text-xs text-ink/50">{parameter.description}</p>
      )}
      {renderControl()}
      {errors.map((issue, index) => (
        <p key={`e-${index}`} className="text-xs text-coral">
          {issue.message}
        </p>
      ))}
      {warnings.map((issue, index) => (
        <p key={`w-${index}`} className="text-xs text-ink/45">
          {issue.message}
        </p>
      ))}
    </div>
  );
}
