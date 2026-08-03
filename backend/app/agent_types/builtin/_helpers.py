"""Factories for declaring built-in agent type parameters and metrics."""

from __future__ import annotations

from typing import Any, Sequence

from app.agent_types.schemas import (
    AgentMetricCategory,
    AgentMetricDefinition,
    AgentMetricDirection,
    AgentMetricUnit,
    AgentParameterSection,
    AgentParameterType,
    AgentTypeParameterDefinition,
    ParameterOption,
    ParameterValidation,
    ParameterVisibility,
)

OptionInput = str | tuple[str, str] | ParameterOption


def options(values: Sequence[OptionInput]) -> list[ParameterOption]:
    built: list[ParameterOption] = []
    for value in values:
        if isinstance(value, ParameterOption):
            built.append(value)
        elif isinstance(value, tuple):
            built.append(ParameterOption(value=value[0], label=value[1]))
        else:
            built.append(ParameterOption(value=value, label=_titleize(value)))
    return built


def _titleize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().capitalize()


def param(
    key: str,
    label: str,
    type: AgentParameterType,
    section: AgentParameterSection,
    *,
    required: bool = False,
    description: str | None = None,
    default: Any = None,
    choices: Sequence[OptionInput] | None = None,
    min: float | None = None,
    max: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    visible_when: ParameterVisibility | None = None,
    deployment_blocking: bool | None = None,
    editable_after_deployment: bool = True,
    inherited: bool = False,
) -> AgentTypeParameterDefinition:
    validation: ParameterValidation | None = None
    if any(value is not None for value in (min, max, min_length, max_length, pattern)):
        validation = ParameterValidation(
            min=min,
            max=max,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        )

    return AgentTypeParameterDefinition(
        id=key,
        key=key,
        label=label,
        description=description,
        type=type,
        section=section,
        required=required,
        default_value=default,
        options=options(choices) if choices else None,
        validation=validation,
        visible_when=visible_when,
        deployment_blocking=deployment_blocking if deployment_blocking is not None else required,
        editable_after_deployment=editable_after_deployment,
        inherited=inherited,
    )


def when(parameter_key: str, operator: str, value: Any = None) -> ParameterVisibility:
    return ParameterVisibility(parameter_key=parameter_key, operator=operator, value=value)  # type: ignore[arg-type]


def metric(
    key: str,
    label: str,
    category: AgentMetricCategory,
    unit: AgentMetricUnit,
    direction: AgentMetricDirection,
    *,
    required: bool = False,
    description: str | None = None,
    target_value: float | None = None,
    warning_threshold: float | None = None,
    critical_threshold: float | None = None,
) -> AgentMetricDefinition:
    return AgentMetricDefinition(
        id=key,
        key=key,
        label=label,
        description=description,
        category=category,
        unit=unit,
        direction=direction,
        target_value=target_value,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        required=required,
    )


# Shorthands used heavily by the built-in type modules.
TEXT = AgentParameterType.text
TEXTAREA = AgentParameterType.textarea
NUMBER = AgentParameterType.number
BOOLEAN = AgentParameterType.boolean
SELECT = AgentParameterType.select
MULTI_SELECT = AgentParameterType.multi_select
JSON = AgentParameterType.json
TOOL_SELECTOR = AgentParameterType.tool_selector
AGENT_SELECTOR = AgentParameterType.agent_selector
MODEL_SELECTOR = AgentParameterType.model_selector
DATA_SOURCE_SELECTOR = AgentParameterType.data_source_selector

IDENTITY = AgentParameterSection.identity
CAPABILITIES = AgentParameterSection.capabilities
AUTONOMY = AgentParameterSection.autonomy
TOOLS = AgentParameterSection.tools
DATA = AgentParameterSection.data
ACTIONS = AgentParameterSection.actions
WORKFLOW = AgentParameterSection.workflow
EVALUATION = AgentParameterSection.evaluation
SAFETY = AgentParameterSection.safety
METRICS = AgentParameterSection.metrics
DEPLOYMENT = AgentParameterSection.deployment
CUSTOM = AgentParameterSection.custom

QUALITY = AgentMetricCategory.quality
TASK_SUCCESS = AgentMetricCategory.task_success
RELIABILITY = AgentMetricCategory.reliability
PERFORMANCE = AgentMetricCategory.performance
COST = AgentMetricCategory.cost
SAFETY_CATEGORY = AgentMetricCategory.safety
USER_EXPERIENCE = AgentMetricCategory.user_experience
BUSINESS = AgentMetricCategory.business

PERCENTAGE = AgentMetricUnit.percentage
COUNT = AgentMetricUnit.count
MILLISECONDS = AgentMetricUnit.milliseconds
SECONDS = AgentMetricUnit.seconds
CURRENCY = AgentMetricUnit.currency
SCORE = AgentMetricUnit.score
RATIO = AgentMetricUnit.ratio

HIGHER_IS_BETTER = AgentMetricDirection.higher_is_better
LOWER_IS_BETTER = AgentMetricDirection.lower_is_better
TARGET = AgentMetricDirection.target
