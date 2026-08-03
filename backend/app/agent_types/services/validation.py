"""Centralized agent type configuration validation.

The same rules run for client previews (`POST /guild/agents/{id}/validate`) and
for deployment, so deployment can never rely on client-side checks alone.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.builtin.action import HIGH_RISK_METADATA_KEYS
from app.agent_types.catalogs import DATA_SOURCE_KEYS, model_keys, tool_keys
from app.agent_types.conditions import visible_parameters
from app.agent_types.guards import find_forbidden_terms
from app.agent_types.schemas import (
    AgentMetricDefinition,
    AgentParameterType,
    AgentTypeDefinition,
    AgentTypeParameterDefinition,
    AgentTypeValidationResult,
    ValidationIssue,
)
from app.agent_types.services import registry
from app.models import Agent

RISK_LEVELS_REQUIRING_METADATA = {"high", "critical"}


class ValidationContext:
    """References the validator checks configuration values against."""

    def __init__(
        self,
        *,
        tools: frozenset[str],
        agent_ids: frozenset[str],
        data_sources: frozenset[str],
        models: frozenset[str],
    ) -> None:
        self.tools = tools
        self.agent_ids = agent_ids
        self.data_sources = data_sources
        self.models = models


async def build_context(db: AsyncSession, agent: Agent | None = None) -> ValidationContext:
    result = await db.execute(select(Agent.id))
    agent_ids = {str(value) for value in result.scalars().all()}

    tools = set(tool_keys())
    if agent is not None:
        tools |= {str(item) for item in (agent.capabilities or [])}

    return ValidationContext(
        tools=frozenset(tools),
        agent_ids=frozenset(agent_ids),
        data_sources=frozenset(DATA_SOURCE_KEYS),
        models=frozenset(model_keys()),
    )


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def validate_configuration(
    definition: AgentTypeDefinition,
    configuration: Mapping[str, Any],
    metric_configuration: Mapping[str, Any] | None,
    context: ValidationContext,
    *,
    agent_is_new_assignment: bool = False,
) -> AgentTypeValidationResult:
    errors: list[ValidationIssue] = []
    missing_required: list[str] = []
    blockers: list[str] = []

    if definition.status == "archived":
        message = f"Agent type '{definition.name}' is archived"
        if agent_is_new_assignment:
            errors.append(ValidationIssue(message=f"{message} and cannot be assigned.", severity="error"))
        else:
            errors.append(
                ValidationIssue(
                    message=f"{message}; migrate the agent to an active version before deploying.",
                    severity="error",
                )
            )
        blockers.append(message)

    if definition.status == "draft":
        errors.append(
            ValidationIssue(
                message=f"Agent type '{definition.name}' is still a draft.",
                severity="error",
            )
        )
        blockers.append(f"Agent type '{definition.name}' is a draft")

    # A schema must never carry human approval / review / intervention configuration.
    forbidden = find_forbidden_terms(definition.model_dump(mode="json", by_alias=True))
    if forbidden:
        errors.append(
            ValidationIssue(
                message=(
                    "Agent type schema declares unsupported human-in-the-loop configuration. "
                    "Human review is handled by the application runtime."
                ),
                severity="error",
            )
        )
        blockers.append("Agent type schema contains unsupported fields")

    parameters = definition.parameter_definitions
    visible = visible_parameters(parameters, configuration)
    visible_keys = {item.key for item in visible}
    known_keys = {item.key for item in parameters}

    for parameter in visible:
        value = configuration.get(parameter.key)
        blocking = (
            parameter.deployment_blocking
            if parameter.deployment_blocking is not None
            else parameter.required
        )

        if _is_empty(value):
            if parameter.required:
                missing_required.append(parameter.key)
                errors.append(
                    ValidationIssue(
                        parameter_key=parameter.key,
                        section=parameter.section.value,
                        message=f"{parameter.label} is required.",
                        severity="error",
                    )
                )
                if blocking:
                    blockers.append(f"{parameter.label} is required")
            continue

        issues = _validate_value(parameter, value, context)
        errors.extend(issues)
        if issues and blocking:
            blockers.extend(issue.message for issue in issues if issue.severity == "error")

    # Values present for parameters that are not part of this type / not visible.
    for key in configuration:
        if key not in known_keys:
            errors.append(
                ValidationIssue(
                    parameter_key=key,
                    message=f"'{key}' is not part of this agent type and will be ignored.",
                    severity="warning",
                )
            )
        elif key not in visible_keys and not _is_empty(configuration[key]):
            errors.append(
                ValidationIssue(
                    parameter_key=key,
                    message=f"'{key}' is hidden by the current configuration and will be ignored.",
                    severity="warning",
                )
            )

    errors.extend(_validate_fallback(configuration, context, blockers))
    errors.extend(_validate_actions(definition, configuration, blockers))
    errors.extend(_validate_risk_metadata(definition, configuration, blockers))
    errors.extend(
        _validate_metrics(definition.metric_definitions, metric_configuration or {}, blockers)
    )

    valid = not blockers and not any(issue.severity == "error" for issue in errors)
    return AgentTypeValidationResult(
        valid=valid,
        errors=errors,
        missing_required_parameters=missing_required,
        deployment_blockers=_dedupe(blockers),
    )


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _issue(parameter: AgentTypeParameterDefinition, message: str) -> ValidationIssue:
    return ValidationIssue(
        parameter_key=parameter.key,
        section=parameter.section.value,
        message=message,
        severity="error",
    )


def _validate_value(
    parameter: AgentTypeParameterDefinition, value: Any, context: ValidationContext
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    kind = parameter.type

    if kind in (AgentParameterType.text, AgentParameterType.textarea):
        if not isinstance(value, str):
            return [_issue(parameter, f"{parameter.label} must be text.")]
        issues.extend(_validate_text(parameter, value))

    elif kind is AgentParameterType.number:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return [_issue(parameter, f"{parameter.label} must be a number.")]
        issues.extend(_validate_number(parameter, float(value)))

    elif kind is AgentParameterType.boolean:
        if not isinstance(value, bool):
            return [_issue(parameter, f"{parameter.label} must be true or false.")]

    elif kind is AgentParameterType.select:
        allowed = {option.value for option in parameter.options or []}
        if allowed and str(value) not in allowed:
            issues.append(_issue(parameter, f"'{value}' is not an allowed value for {parameter.label}."))

    elif kind is AgentParameterType.multi_select:
        if not isinstance(value, list):
            return [_issue(parameter, f"{parameter.label} must be a list of values.")]
        allowed = {option.value for option in parameter.options or []}
        if allowed:
            invalid = [item for item in value if str(item) not in allowed]
            if invalid:
                issues.append(
                    _issue(parameter, f"Unsupported values for {parameter.label}: {', '.join(map(str, invalid))}.")
                )

    elif kind is AgentParameterType.json:
        if isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError:
                issues.append(_issue(parameter, f"{parameter.label} must be valid JSON."))
        elif not isinstance(value, (dict, list)):
            issues.append(_issue(parameter, f"{parameter.label} must be a JSON object or array."))

    elif kind is AgentParameterType.tool_selector:
        unknown = [item for item in _as_list(value) if str(item) not in context.tools]
        if unknown:
            issues.append(_issue(parameter, f"Unknown tools: {', '.join(map(str, unknown))}."))

    elif kind is AgentParameterType.agent_selector:
        unknown = [item for item in _as_list(value) if not _is_known_agent(item, context)]
        if unknown:
            issues.append(_issue(parameter, f"Referenced agents do not exist: {', '.join(map(str, unknown))}."))

    elif kind is AgentParameterType.model_selector:
        unknown = [item for item in _as_list(value) if str(item) not in context.models]
        if unknown:
            issues.append(_issue(parameter, f"Unknown models: {', '.join(map(str, unknown))}."))

    elif kind is AgentParameterType.data_source_selector:
        unknown = [item for item in _as_list(value) if str(item) not in context.data_sources]
        if unknown:
            issues.append(_issue(parameter, f"Unknown data sources: {', '.join(map(str, unknown))}."))

    return issues


def _is_known_agent(value: Any, context: ValidationContext) -> bool:
    try:
        return str(UUID(str(value))) in context.agent_ids
    except ValueError:
        return False


def _validate_text(
    parameter: AgentTypeParameterDefinition, value: str
) -> list[ValidationIssue]:
    import re

    rules = parameter.validation
    if rules is None:
        return []
    issues: list[ValidationIssue] = []
    if rules.min_length is not None and len(value) < rules.min_length:
        issues.append(_issue(parameter, f"{parameter.label} must be at least {rules.min_length} characters."))
    if rules.max_length is not None and len(value) > rules.max_length:
        issues.append(_issue(parameter, f"{parameter.label} must be at most {rules.max_length} characters."))
    if rules.pattern and not re.fullmatch(rules.pattern, value):
        issues.append(_issue(parameter, f"{parameter.label} has an invalid format."))
    return issues


def _validate_number(
    parameter: AgentTypeParameterDefinition, value: float
) -> list[ValidationIssue]:
    rules = parameter.validation
    if rules is None:
        return []
    issues: list[ValidationIssue] = []
    if rules.min is not None and value < rules.min:
        issues.append(_issue(parameter, f"{parameter.label} must be at least {rules.min}."))
    if rules.max is not None and value > rules.max:
        issues.append(_issue(parameter, f"{parameter.label} must be at most {rules.max}."))
    return issues


def _validate_fallback(
    configuration: Mapping[str, Any], context: ValidationContext, blockers: list[str]
) -> list[ValidationIssue]:
    behavior = configuration.get("fallback_behavior")
    issues: list[ValidationIssue] = []

    if behavior == "fallback_agent":
        target = configuration.get("fallback_agent_id")
        if _is_empty(target):
            issues.append(
                ValidationIssue(
                    parameter_key="fallback_agent_id",
                    section="workflow",
                    message="A fallback agent must be selected for the chosen fallback behavior.",
                )
            )
            blockers.append("Fallback agent is not configured")
        elif not all(_is_known_agent(item, context) for item in _as_list(target)):
            issues.append(
                ValidationIssue(
                    parameter_key="fallback_agent_id",
                    section="workflow",
                    message="The configured fallback agent does not exist.",
                )
            )
            blockers.append("Fallback agent does not exist")

    if behavior == "fallback_model" and _is_empty(configuration.get("fallback_model_id")):
        issues.append(
            ValidationIssue(
                parameter_key="fallback_model_id",
                section="workflow",
                message="A fallback model must be selected for the chosen fallback behavior.",
            )
        )
        blockers.append("Fallback model is not configured")

    return issues


def _validate_actions(
    definition: AgentTypeDefinition, configuration: Mapping[str, Any], blockers: list[str]
) -> list[ValidationIssue]:
    """Only Action agents may declare side-effecting actions."""
    issues: list[ValidationIssue] = []
    declared_actions = configuration.get("allowed_actions") or []
    is_action_type = definition.id == "action" or definition.base_type_id == "action"

    if declared_actions and not is_action_type:
        issues.append(
            ValidationIssue(
                parameter_key="allowed_actions",
                section="actions",
                message=(
                    "Allowed actions can only be configured on an Action agent type. "
                    "Change the type or clear this value."
                ),
            )
        )
        blockers.append("Allowed actions require the Action agent type")

    if is_action_type:
        catalog = configuration.get("action_catalog") or []
        permissions = configuration.get("required_permissions") or []
        if catalog and not permissions:
            issues.append(
                ValidationIssue(
                    parameter_key="required_permissions",
                    section="safety",
                    message="Actions are declared but no permissions are required for them.",
                )
            )
            blockers.append("Action permissions are not configured")

    return issues


def _validate_risk_metadata(
    definition: AgentTypeDefinition, configuration: Mapping[str, Any], blockers: list[str]
) -> list[ValidationIssue]:
    """High-risk work must expose enough metadata for the runtime to act on."""
    issues: list[ValidationIssue] = []
    risk = str(configuration.get("risk_level") or definition.default_risk_level)
    if risk not in RISK_LEVELS_REQUIRING_METADATA:
        return issues

    if configuration.get("audit_logging_enabled") is False:
        issues.append(
            ValidationIssue(
                parameter_key="audit_logging_enabled",
                section="deployment",
                message="Audit logging must stay enabled for high-risk agents.",
            )
        )
        blockers.append("Audit logging is disabled on a high-risk agent")

    if configuration.get("tracing_enabled") is False:
        issues.append(
            ValidationIssue(
                parameter_key="tracing_enabled",
                section="deployment",
                message="Tracing must stay enabled for high-risk agents.",
            )
        )
        blockers.append("Tracing is disabled on a high-risk agent")

    is_action_type = definition.id == "action" or definition.base_type_id == "action"
    if is_action_type:
        for key in HIGH_RISK_METADATA_KEYS:
            if _is_empty(configuration.get(key)):
                issues.append(
                    ValidationIssue(
                        parameter_key=key,
                        section="safety",
                        message=(
                            f"High-risk action agents must publish '{key}' so the runtime can "
                            "decide how to handle the action."
                        ),
                    )
                )
                blockers.append(f"Missing high-risk action metadata: {key}")

    return issues


def _validate_metrics(
    definitions: list[AgentMetricDefinition],
    metric_configuration: Mapping[str, Any],
    blockers: list[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    known = {definition.key for definition in definitions}

    for definition in definitions:
        entry = metric_configuration.get(definition.key)
        enabled = bool(entry.get("enabled", True)) if isinstance(entry, dict) else False
        if definition.required and not enabled:
            issues.append(
                ValidationIssue(
                    parameter_key=definition.key,
                    section="metrics",
                    message=f"Required metric '{definition.label}' must be configured.",
                )
            )
            blockers.append(f"Required metric not configured: {definition.label}")
            continue

        if enabled and isinstance(entry, dict):
            issues.extend(_validate_metric_thresholds(definition, entry))

    for key in metric_configuration:
        if key not in known:
            issues.append(
                ValidationIssue(
                    parameter_key=key,
                    section="metrics",
                    message=f"Metric '{key}' is not defined by this agent type.",
                    severity="warning",
                )
            )

    return issues


def _validate_metric_thresholds(
    definition: AgentMetricDefinition, entry: Mapping[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in ("targetValue", "target_value", "warningThreshold", "warning_threshold", "criticalThreshold", "critical_threshold"):
        value = entry.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            issues.append(
                ValidationIssue(
                    parameter_key=definition.key,
                    section="metrics",
                    message=f"Threshold '{field}' for '{definition.label}' must be numeric.",
                )
            )
    if definition.direction.value == "target":
        target = entry.get("targetValue", entry.get("target_value"))
        if target is None:
            issues.append(
                ValidationIssue(
                    parameter_key=definition.key,
                    section="metrics",
                    message=f"'{definition.label}' is a target metric and needs a target value.",
                    severity="warning",
                )
            )
    return issues


async def validate_agent(
    db: AsyncSession,
    agent: Agent,
    *,
    configuration: Mapping[str, Any] | None = None,
    metric_configuration: Mapping[str, Any] | None = None,
    type_id: str | None = None,
    type_version: int | None = None,
) -> tuple[AgentTypeValidationResult, AgentTypeDefinition | None]:
    """Validate an agent's (or a proposed) type configuration."""
    resolved_type_id = type_id if type_id is not None else agent.agent_type_id
    resolved_version = type_version if type_id is not None else agent.agent_type_version

    if not resolved_type_id:
        return (
            AgentTypeValidationResult(
                valid=False,
                errors=[
                    ValidationIssue(
                        message="Select an agent type before deploying this agent.",
                        severity="error",
                    )
                ],
                missing_required_parameters=["agent_type_id"],
                deployment_blockers=["No agent type selected"],
            ),
            None,
        )

    try:
        definition = await registry.resolve_definition(db, resolved_type_id, resolved_version)
    except registry.AgentTypeNotFoundError as exc:
        return (
            AgentTypeValidationResult(
                valid=False,
                errors=[ValidationIssue(message=str(exc), severity="error")],
                deployment_blockers=[str(exc)],
            ),
            None,
        )

    context = await build_context(db, agent)
    result = validate_configuration(
        definition,
        dict(configuration if configuration is not None else agent.agent_type_configuration or {}),
        dict(
            metric_configuration
            if metric_configuration is not None
            else agent.agent_metric_configuration or {}
        ),
        context,
    )
    return result, definition
