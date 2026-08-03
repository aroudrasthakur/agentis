/**
 * Agent type schema contracts. These mirror `backend/app/agent_types/schemas.py`
 * (camelCase on the wire).
 */

export type AgentTypeId =
  | "user_facing"
  | "orchestration"
  | "task_domain"
  | "action"
  | "evaluation"
  | "governance"
  | "retrieval_context"
  | "memory"
  | "operational"
  | "custom";

export type AgentParameterType =
  | "text"
  | "textarea"
  | "number"
  | "boolean"
  | "select"
  | "multi_select"
  | "json"
  | "tool_selector"
  | "agent_selector"
  | "model_selector"
  | "data_source_selector";

export type AgentParameterSection =
  | "identity"
  | "capabilities"
  | "autonomy"
  | "tools"
  | "data"
  | "actions"
  | "workflow"
  | "evaluation"
  | "safety"
  | "metrics"
  | "deployment"
  | "custom";

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type AgentTypeStatus = "draft" | "active" | "archived";

export type AgentMetricCategory =
  | "quality"
  | "task_success"
  | "reliability"
  | "performance"
  | "cost"
  | "safety"
  | "user_experience"
  | "business";

export type AgentMetricUnit =
  | "percentage"
  | "count"
  | "milliseconds"
  | "seconds"
  | "currency"
  | "score"
  | "ratio";

export type AgentMetricDirection = "higher_is_better" | "lower_is_better" | "target";

export interface ParameterOption {
  label: string;
  value: string;
}

export interface ParameterValidation {
  min?: number | null;
  max?: number | null;
  minLength?: number | null;
  maxLength?: number | null;
  pattern?: string | null;
}

export interface ParameterVisibility {
  parameterKey: string;
  operator: "equals" | "not_equals" | "contains" | "truthy";
  value?: unknown;
}

export interface AgentTypeParameterDefinition {
  id: string;
  key: string;
  label: string;
  description?: string | null;
  type: AgentParameterType;
  section: AgentParameterSection;
  required: boolean;
  defaultValue?: unknown;
  options?: ParameterOption[] | null;
  validation?: ParameterValidation | null;
  visibleWhen?: ParameterVisibility | null;
  deploymentBlocking?: boolean | null;
  editableAfterDeployment?: boolean | null;
  inherited: boolean;
}

export interface AgentMetricDefinition {
  id: string;
  key: string;
  label: string;
  description?: string | null;
  category: AgentMetricCategory;
  unit: AgentMetricUnit;
  direction: AgentMetricDirection;
  targetValue?: number | null;
  warningThreshold?: number | null;
  criticalThreshold?: number | null;
  required: boolean;
}

export interface AgentTypeDefinition {
  id: string;
  name: string;
  slug: string;
  description: string;
  version: number;
  status: AgentTypeStatus;
  builtIn: boolean;
  baseTypeId?: string | null;
  icon?: string | null;
  useCases: string[];
  capabilities: string[];
  defaultAutonomyLevel: number;
  defaultRiskLevel: RiskLevel;
  parameterDefinitions: AgentTypeParameterDefinition[];
  metricDefinitions: AgentMetricDefinition[];
  familyId?: string | null;
}

export interface AgentTypeSummary {
  id: string;
  name: string;
  slug: string;
  description: string;
  version: number;
  status: AgentTypeStatus;
  builtIn: boolean;
  baseTypeId?: string | null;
  icon?: string | null;
  useCases: string[];
  capabilities: string[];
  defaultAutonomyLevel: number;
  defaultRiskLevel: RiskLevel;
  parameterCount: number;
  metricCount: number;
  familyId?: string | null;
}

export interface ValidationIssue {
  parameterKey?: string | null;
  section?: string | null;
  message: string;
  severity: "error" | "warning";
}

export interface AgentTypeValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  missingRequiredParameters: string[];
  deploymentBlockers: string[];
}

export interface MetricConfigurationEntry {
  enabled: boolean;
  targetValue?: number | null;
  warningThreshold?: number | null;
  criticalThreshold?: number | null;
}

export type AgentTypeConfiguration = Record<string, unknown>;
export type AgentMetricConfiguration = Record<string, MetricConfigurationEntry>;

export interface CompatibilityReport {
  preservedKeys: string[];
  incompatibleKeys: string[];
  newlyRequiredKeys: string[];
}

export interface ConfiguredMetric {
  key: string;
  label: string;
  category: AgentMetricCategory;
  unit: AgentMetricUnit;
  direction: AgentMetricDirection;
  required: boolean;
  enabled: boolean;
  targetValue?: number | null;
  warningThreshold?: number | null;
  criticalThreshold?: number | null;
}

export interface DeploymentReadiness {
  agentId: string;
  agentName: string;
  typeId?: string | null;
  typeName?: string | null;
  typeVersion?: number | null;
  typeStatus?: string | null;
  builtIn?: boolean | null;
  requiresTypeSetup: boolean;
  configurationCompleteness: number;
  configuredParameterCount: number;
  totalParameterCount: number;
  validation: AgentTypeValidationResult;
  missingRequiredParameters: string[];
  warnings: ValidationIssue[];
  deploymentBlockers: string[];
  riskLevel?: string | null;
  autonomyLevel?: number | null;
  stateMode?: string | null;
  executionMode?: string | null;
  enabledTools: string[];
  enabledActions: string[];
  allowedDataSources: string[];
  fallbackBehavior?: string | null;
  configuredMetrics: ConfiguredMetric[];
  tracingEnabled: boolean;
  auditLoggingEnabled: boolean;
  evaluationEnabled: boolean;
  deployedTypeId?: string | null;
  deployedTypeVersion?: number | null;
  deployedAt?: string | null;
  canDeploy: boolean;
}

export interface SelectorOption {
  value: string;
  label: string;
}

export interface SelectorCatalogs {
  tools: SelectorOption[];
  models: SelectorOption[];
  dataSources: SelectorOption[];
  agents: SelectorOption[];
}

export interface CustomAgentType {
  id: string;
  familyId: string;
  version: number;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  baseTypeId?: string | null;
  status: AgentTypeStatus;
  parameterDefinitions: AgentTypeParameterDefinition[];
  metricDefinitions: AgentMetricDefinition[];
  defaultAutonomyLevel: number;
  defaultRiskLevel: RiskLevel;
  inUse: boolean;
  createdAt: string;
  updatedAt?: string | null;
  createdBy?: string | null;
}

export interface ParameterDiff {
  key: string;
  label: string;
  section: string;
  required: boolean;
  deploymentBlocking: boolean;
}

export interface TypeMigrationPreview {
  fromVersion?: number | null;
  toVersion: number;
  addedParameters: ParameterDiff[];
  removedParameters: ParameterDiff[];
  changedParameters: ParameterDiff[];
  newlyRequiredParameters: string[];
  blocksDeployment: boolean;
}

export const SECTION_LABELS: Record<AgentParameterSection, string> = {
  identity: "Identity",
  capabilities: "Capabilities",
  autonomy: "Autonomy and risk",
  tools: "Tools",
  data: "Data",
  actions: "Actions",
  workflow: "Workflow",
  evaluation: "Evaluation",
  safety: "Safety",
  metrics: "Metrics",
  deployment: "Deployment",
  custom: "Custom",
};

export const SECTION_ORDER: AgentParameterSection[] = [
  "identity",
  "capabilities",
  "autonomy",
  "tools",
  "data",
  "actions",
  "workflow",
  "evaluation",
  "safety",
  "metrics",
  "deployment",
  "custom",
];
