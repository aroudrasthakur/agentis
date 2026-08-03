"use client";

import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import type {
  AgentTypeConfiguration,
  AgentTypeDefinition,
  AgentTypeParameterDefinition,
  AgentParameterSection,
  SelectorCatalogs,
  ValidationIssue,
} from "@/agent-types/schemas";
import { SECTION_LABELS, SECTION_ORDER } from "@/agent-types/schemas";
import { visibleParameters } from "@/agent-types/utils";
import { AgentTypeParameterField } from "./AgentTypeParameterField";

export function AgentTypeConfigForm({
  definition,
  configuration,
  issues,
  catalogs,
  onChange,
}: {
  definition: AgentTypeDefinition;
  configuration: AgentTypeConfiguration;
  issues: ValidationIssue[];
  catalogs: SelectorCatalogs | null;
  onChange: (key: string, value: unknown) => void;
}) {
  const sections = useMemo(() => {
    const visible = visibleParameters(definition.parameterDefinitions, configuration);
    const grouped = new Map<AgentParameterSection, AgentTypeParameterDefinition[]>();
    for (const parameter of visible) {
      const bucket = grouped.get(parameter.section) ?? [];
      bucket.push(parameter);
      grouped.set(parameter.section, bucket);
    }
    return SECTION_ORDER.filter((section) => grouped.has(section)).map((section) => ({
      section,
      parameters: grouped.get(section) ?? [],
    }));
  }, [definition, configuration]);

  const issuesByKey = useMemo(() => {
    const map = new Map<string, ValidationIssue[]>();
    for (const issue of issues) {
      if (!issue.parameterKey) continue;
      const bucket = map.get(issue.parameterKey) ?? [];
      bucket.push(issue);
      map.set(issue.parameterKey, bucket);
    }
    return map;
  }, [issues]);

  return (
    <div className="space-y-6">
      {sections.map(({ section, parameters }) => (
        <section
          key={section}
          className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5"
        >
          <div className="mb-4 flex items-center gap-2">
            <h3 className="font-display text-lg text-ink">{SECTION_LABELS[section]}</h3>
            <Badge className="bg-ink/5 text-ink/50">{parameters.length}</Badge>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            {parameters.map((parameter) => (
              <AgentTypeParameterField
                key={parameter.key}
                parameter={parameter}
                value={configuration[parameter.key]}
                issues={issuesByKey.get(parameter.key) ?? []}
                catalogs={catalogs}
                onChange={onChange}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
