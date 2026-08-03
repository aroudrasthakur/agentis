"""Deployment readiness: what the agent type says about deploying this agent.

Readiness never includes human approval or review state — those belong to the
runtime, not to the agent type model.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.conditions import visible_parameters
from app.agent_types.schemas import AgentTypeDefinition, DeploymentReadiness
from app.agent_types.services.validation import validate_agent
from app.models import Agent


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _configured_metrics(
    definition: AgentTypeDefinition | None, metric_configuration: dict[str, Any]
) -> list[dict[str, Any]]:
    if definition is None:
        return []
    configured: list[dict[str, Any]] = []
    for metric in definition.metric_definitions:
        entry = metric_configuration.get(metric.key)
        entry = entry if isinstance(entry, dict) else {}
        enabled = bool(entry.get("enabled", False))
        if not enabled and not metric.required:
            continue
        configured.append(
            {
                "key": metric.key,
                "label": metric.label,
                "category": metric.category.value,
                "unit": metric.unit.value,
                "direction": metric.direction.value,
                "required": metric.required,
                "enabled": enabled,
                "targetValue": entry.get("targetValue", entry.get("target_value")),
                "warningThreshold": entry.get("warningThreshold", entry.get("warning_threshold")),
                "criticalThreshold": entry.get(
                    "criticalThreshold", entry.get("critical_threshold")
                ),
            }
        )
    return configured


async def build_readiness(db: AsyncSession, agent: Agent) -> DeploymentReadiness:
    configuration = dict(agent.agent_type_configuration or {})
    metric_configuration = dict(agent.agent_metric_configuration or {})
    validation, definition = await validate_agent(db, agent)

    total = 0
    configured = 0
    if definition is not None:
        visible = visible_parameters(definition.parameter_definitions, configuration)
        total = len(visible)
        configured = sum(
            1
            for parameter in visible
            if configuration.get(parameter.key) not in (None, "", [], {})
        )

    warnings = [issue for issue in validation.errors if issue.severity == "warning"]

    return DeploymentReadiness(
        agent_id=agent.id,
        agent_name=agent.name,
        type_id=agent.agent_type_id,
        type_name=definition.name if definition else None,
        type_version=definition.version if definition else agent.agent_type_version,
        type_status=definition.status if definition else None,
        built_in=definition.built_in if definition else None,
        requires_type_setup=agent.agent_type_id is None,
        configuration_completeness=round(configured / total, 4) if total else 0.0,
        configured_parameter_count=configured,
        total_parameter_count=total,
        validation=validation,
        missing_required_parameters=validation.missing_required_parameters,
        warnings=warnings,
        deployment_blockers=validation.deployment_blockers,
        risk_level=configuration.get("risk_level")
        or (definition.default_risk_level if definition else None),
        autonomy_level=_autonomy(configuration, definition),
        state_mode=configuration.get("state_mode"),
        execution_mode=configuration.get("execution_mode"),
        enabled_tools=_as_list(configuration.get("allowed_tools")) or list(agent.capabilities or []),
        enabled_actions=_as_list(configuration.get("allowed_actions"))
        or _as_list(configuration.get("action_catalog")),
        allowed_data_sources=_as_list(configuration.get("allowed_data_sources")),
        fallback_behavior=configuration.get("fallback_behavior"),
        configured_metrics=_configured_metrics(definition, metric_configuration),
        tracing_enabled=bool(configuration.get("tracing_enabled")),
        audit_logging_enabled=bool(configuration.get("audit_logging_enabled")),
        evaluation_enabled=bool(configuration.get("evaluation_enabled")),
        deployed_type_id=agent.deployed_type_id,
        deployed_type_version=agent.deployed_type_version,
        deployed_at=agent.deployed_at,
        can_deploy=validation.valid,
    )


def _autonomy(configuration: dict[str, Any], definition: AgentTypeDefinition | None) -> int | None:
    raw = configuration.get("autonomy_level")
    if raw is None:
        return definition.default_autonomy_level if definition else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
