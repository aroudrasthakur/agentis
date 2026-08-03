import type {
  AgentMetricConfiguration,
  AgentTypeConfiguration,
  AgentTypeDefinition,
  AgentTypeParameterDefinition,
  ParameterVisibility,
} from "@/agent-types/schemas";

function scalarEquals(actual: unknown, expected: unknown): boolean {
  if (actual === null || actual === undefined || expected === null || expected === undefined) {
    return actual === expected;
  }
  if (typeof actual === "boolean" || typeof expected === "boolean") {
    return Boolean(actual) === Boolean(expected);
  }
  if (typeof actual === "number" && typeof expected === "number") {
    return actual === expected;
  }
  return String(actual) === String(expected);
}

function conditionHolds(condition: ParameterVisibility, value: unknown): boolean {
  switch (condition.operator) {
    case "truthy":
      if (Array.isArray(value) || typeof value === "string") return value.length > 0;
      if (value && typeof value === "object") return Object.keys(value).length > 0;
      return Boolean(value);
    case "contains":
      if (Array.isArray(value)) return value.some((item) => scalarEquals(item, condition.value));
      if (typeof value === "string") return value.includes(String(condition.value));
      return false;
    case "equals":
      return scalarEquals(value, condition.value);
    case "not_equals":
      return !scalarEquals(value, condition.value);
    default:
      return true;
  }
}

export function isParameterVisible(
  parameter: AgentTypeParameterDefinition,
  configuration: AgentTypeConfiguration,
  byKey: Map<string, AgentTypeParameterDefinition>,
  seen: Set<string> = new Set()
): boolean {
  const condition = parameter.visibleWhen;
  if (!condition) return true;
  if (seen.has(parameter.key)) return true;

  if (!conditionHolds(condition, configuration[condition.parameterKey])) return false;

  const parent = byKey.get(condition.parameterKey);
  if (!parent) return true;
  const nextSeen = new Set(seen);
  nextSeen.add(parameter.key);
  return isParameterVisible(parent, configuration, byKey, nextSeen);
}

export function visibleParameters(
  parameters: AgentTypeParameterDefinition[],
  configuration: AgentTypeConfiguration
): AgentTypeParameterDefinition[] {
  const byKey = new Map(parameters.map((item) => [item.key, item]));
  return parameters.filter((item) => isParameterVisible(item, configuration, byKey));
}

export function isBlank(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value as object).length === 0;
  return false;
}

export function isDeploymentBlocking(parameter: AgentTypeParameterDefinition): boolean {
  return parameter.deploymentBlocking ?? parameter.required;
}

export function defaultConfiguration(
  definition: AgentTypeDefinition
): AgentTypeConfiguration {
  const values: AgentTypeConfiguration = {};
  for (const parameter of definition.parameterDefinitions) {
    if (parameter.defaultValue !== null && parameter.defaultValue !== undefined) {
      values[parameter.key] = parameter.defaultValue;
    }
  }
  if (values.autonomy_level === undefined) {
    values.autonomy_level = String(definition.defaultAutonomyLevel);
  }
  if (values.risk_level === undefined) values.risk_level = definition.defaultRiskLevel;
  return values;
}

export function defaultMetricConfiguration(
  definition: AgentTypeDefinition
): AgentMetricConfiguration {
  const entries: AgentMetricConfiguration = {};
  for (const metric of definition.metricDefinitions) {
    entries[metric.key] = {
      enabled: metric.required,
      targetValue: metric.targetValue ?? null,
      warningThreshold: metric.warningThreshold ?? null,
      criticalThreshold: metric.criticalThreshold ?? null,
    };
  }
  return entries;
}

/** Values the target type can still represent, used when switching types. */
export function incompatibleKeys(
  definition: AgentTypeDefinition,
  configuration: AgentTypeConfiguration
): string[] {
  const byKey = new Map(definition.parameterDefinitions.map((item) => [item.key, item]));
  return Object.entries(configuration)
    .filter(([key, value]) => {
      if (isBlank(value)) return false;
      const parameter = byKey.get(key);
      if (!parameter) return true;
      const options = parameter.options ?? [];
      if (!options.length) return false;
      const allowed = new Set(options.map((option) => option.value));
      if (Array.isArray(value)) return !value.every((item) => allowed.has(String(item)));
      return !allowed.has(String(value));
    })
    .map(([key]) => key);
}
