"""Declarative schema model for agent types, parameters, and metrics.

JSON field names are camelCase (matching the agent-type spec and the frontend
types); Python attribute names stay snake_case like the rest of the backend.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AgentTypeCamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


AgentTypeId = Literal[
    "user_facing",
    "orchestration",
    "task_domain",
    "action",
    "evaluation",
    "governance",
    "retrieval_context",
    "memory",
    "operational",
    "custom",
]

BUILT_IN_TYPE_IDS: tuple[str, ...] = (
    "user_facing",
    "orchestration",
    "task_domain",
    "action",
    "evaluation",
    "governance",
    "retrieval_context",
    "memory",
    "operational",
    "custom",
)

CUSTOM_TYPE_PREFIX = "custom:"

AutonomyLevel = Literal[0, 1, 2, 3, 4, 5]
RiskLevel = Literal["low", "medium", "high", "critical"]
StateMode = Literal["stateless", "session", "workflow", "long_term", "event_based"]
ExecutionMode = Literal[
    "request_response",
    "event_driven",
    "scheduled",
    "batch",
    "continuous_monitoring",
    "interactive_workflow",
    "multi_agent",
]
FallbackBehavior = Literal[
    "fail",
    "retry",
    "fallback_agent",
    "fallback_model",
    "return_control_to_runtime",
]


class AgentParameterType(str, enum.Enum):
    text = "text"
    textarea = "textarea"
    number = "number"
    boolean = "boolean"
    select = "select"
    multi_select = "multi_select"
    json = "json"
    tool_selector = "tool_selector"
    agent_selector = "agent_selector"
    model_selector = "model_selector"
    data_source_selector = "data_source_selector"


class AgentParameterSection(str, enum.Enum):
    identity = "identity"
    capabilities = "capabilities"
    autonomy = "autonomy"
    tools = "tools"
    data = "data"
    actions = "actions"
    workflow = "workflow"
    evaluation = "evaluation"
    safety = "safety"
    metrics = "metrics"
    deployment = "deployment"
    custom = "custom"


class AgentMetricCategory(str, enum.Enum):
    quality = "quality"
    task_success = "task_success"
    reliability = "reliability"
    performance = "performance"
    cost = "cost"
    safety = "safety"
    user_experience = "user_experience"
    business = "business"


class AgentMetricUnit(str, enum.Enum):
    percentage = "percentage"
    count = "count"
    milliseconds = "milliseconds"
    seconds = "seconds"
    currency = "currency"
    score = "score"
    ratio = "ratio"


class AgentMetricDirection(str, enum.Enum):
    higher_is_better = "higher_is_better"
    lower_is_better = "lower_is_better"
    target = "target"


class ParameterOption(AgentTypeCamelModel):
    label: str
    value: str


class ParameterValidation(AgentTypeCamelModel):
    min: float | None = None
    max: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None


class ParameterVisibility(AgentTypeCamelModel):
    parameter_key: str
    operator: Literal["equals", "not_equals", "contains", "truthy"]
    value: Any = None


class AgentTypeParameterDefinition(AgentTypeCamelModel):
    id: str
    key: str
    label: str
    description: str | None = None

    type: AgentParameterType
    section: AgentParameterSection

    required: bool = False
    default_value: Any = None

    options: list[ParameterOption] | None = None
    validation: ParameterValidation | None = None
    visible_when: ParameterVisibility | None = None

    deployment_blocking: bool | None = None
    editable_after_deployment: bool | None = None

    # True for the parameters shared by every agent type.
    inherited: bool = False


class AgentMetricDefinition(AgentTypeCamelModel):
    id: str
    key: str
    label: str
    description: str | None = None

    category: AgentMetricCategory
    unit: AgentMetricUnit
    direction: AgentMetricDirection

    target_value: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None

    required: bool = False


class AgentTypeDefinition(AgentTypeCamelModel):
    """A resolved agent type: built-in registry entry or custom type version."""

    id: str
    name: str
    slug: str
    description: str
    version: int = 1
    status: Literal["draft", "active", "archived"] = "active"

    built_in: bool = True
    base_type_id: str | None = None
    icon: str | None = None

    use_cases: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)

    default_autonomy_level: int = 1
    default_risk_level: RiskLevel = "low"

    parameter_definitions: list[AgentTypeParameterDefinition] = Field(default_factory=list)
    metric_definitions: list[AgentMetricDefinition] = Field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: UUID | None = None
    family_id: UUID | None = None


class AgentTypeSummary(AgentTypeCamelModel):
    id: str
    name: str
    slug: str
    description: str
    version: int
    status: Literal["draft", "active", "archived"]
    built_in: bool
    base_type_id: str | None = None
    icon: str | None = None
    use_cases: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    default_autonomy_level: int
    default_risk_level: RiskLevel
    parameter_count: int = 0
    metric_count: int = 0
    family_id: UUID | None = None


class ValidationIssue(AgentTypeCamelModel):
    parameter_key: str | None = None
    section: str | None = None
    message: str
    severity: Literal["error", "warning"] = "error"


class AgentTypeValidationResult(AgentTypeCamelModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    missing_required_parameters: list[str] = Field(default_factory=list)
    deployment_blockers: list[str] = Field(default_factory=list)


class MetricConfigurationEntry(AgentTypeCamelModel):
    enabled: bool = True
    target_value: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None


class AgentTypeAssignment(AgentTypeCamelModel):
    type_id: str
    type_version: int | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    metric_configuration: dict[str, MetricConfigurationEntry] = Field(default_factory=dict)
    # Drop values that no longer belong to the selected type instead of erroring.
    discard_incompatible: bool = True


class AgentTypeConfigurationUpdate(AgentTypeCamelModel):
    configuration: dict[str, Any] | None = None
    metric_configuration: dict[str, MetricConfigurationEntry] | None = None


class CompatibilityReport(AgentTypeCamelModel):
    preserved_keys: list[str] = Field(default_factory=list)
    incompatible_keys: list[str] = Field(default_factory=list)
    newly_required_keys: list[str] = Field(default_factory=list)


class DeploymentReadiness(AgentTypeCamelModel):
    agent_id: UUID
    agent_name: str
    type_id: str | None = None
    type_name: str | None = None
    type_version: int | None = None
    type_status: str | None = None
    built_in: bool | None = None

    requires_type_setup: bool = True
    configuration_completeness: float = 0.0
    configured_parameter_count: int = 0
    total_parameter_count: int = 0

    validation: AgentTypeValidationResult
    missing_required_parameters: list[str] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    deployment_blockers: list[str] = Field(default_factory=list)

    risk_level: str | None = None
    autonomy_level: int | None = None
    state_mode: str | None = None
    execution_mode: str | None = None
    enabled_tools: list[str] = Field(default_factory=list)
    enabled_actions: list[str] = Field(default_factory=list)
    allowed_data_sources: list[str] = Field(default_factory=list)
    fallback_behavior: str | None = None
    configured_metrics: list[dict[str, Any]] = Field(default_factory=list)
    tracing_enabled: bool = False
    audit_logging_enabled: bool = False
    evaluation_enabled: bool = False

    deployed_type_id: str | None = None
    deployed_type_version: int | None = None
    deployed_at: datetime | None = None
    can_deploy: bool = False


class CustomAgentTypeCreate(AgentTypeCamelModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = None
    base_type_id: str | None = None
    parameter_definitions: list[AgentTypeParameterDefinition] = Field(default_factory=list)
    metric_definitions: list[AgentMetricDefinition] = Field(default_factory=list)
    default_autonomy_level: int = 1
    default_risk_level: RiskLevel = "low"
    status: Literal["draft", "active"] = "draft"


class CustomAgentTypeUpdate(AgentTypeCamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = None
    base_type_id: str | None = None
    parameter_definitions: list[AgentTypeParameterDefinition] | None = None
    metric_definitions: list[AgentMetricDefinition] | None = None
    default_autonomy_level: int | None = None
    default_risk_level: RiskLevel | None = None
    status: Literal["draft", "active", "archived"] | None = None


class CustomAgentTypeOut(AgentTypeCamelModel):
    id: str
    family_id: UUID
    version: int
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    base_type_id: str | None = None
    status: Literal["draft", "active", "archived"]
    parameter_definitions: list[AgentTypeParameterDefinition] = Field(default_factory=list)
    metric_definitions: list[AgentMetricDefinition] = Field(default_factory=list)
    default_autonomy_level: int
    default_risk_level: RiskLevel
    in_use: bool = False
    created_at: datetime
    updated_at: datetime | None = None
    created_by: UUID | None = None


class ParameterDiff(AgentTypeCamelModel):
    key: str
    label: str
    section: str
    required: bool = False
    deployment_blocking: bool = False


class TypeMigrationPreview(AgentTypeCamelModel):
    from_version: int | None = None
    to_version: int
    added_parameters: list[ParameterDiff] = Field(default_factory=list)
    removed_parameters: list[ParameterDiff] = Field(default_factory=list)
    changed_parameters: list[ParameterDiff] = Field(default_factory=list)
    newly_required_parameters: list[str] = Field(default_factory=list)
    blocks_deployment: bool = False


class TypeMigrationRequest(AgentTypeCamelModel):
    target_version: int | None = None
    configuration: dict[str, Any] | None = None
    metric_configuration: dict[str, MetricConfigurationEntry] | None = None
