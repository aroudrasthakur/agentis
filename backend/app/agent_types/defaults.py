"""Default configuration and metric selection derived from a type definition."""

from __future__ import annotations

from typing import Any

from app.agent_types.schemas import AgentTypeDefinition, MetricConfigurationEntry


def default_configuration(definition: AgentTypeDefinition) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for parameter in definition.parameter_definitions:
        if parameter.default_value is not None:
            values[parameter.key] = parameter.default_value

    values.setdefault("autonomy_level", str(definition.default_autonomy_level))
    values.setdefault("risk_level", definition.default_risk_level)
    return values


def default_metric_configuration(
    definition: AgentTypeDefinition,
) -> dict[str, MetricConfigurationEntry]:
    """Required metrics start enabled; optional ones are opt-in."""
    return {
        metric.key: MetricConfigurationEntry(
            enabled=metric.required,
            target_value=metric.target_value,
            warning_threshold=metric.warning_threshold,
            critical_threshold=metric.critical_threshold,
        )
        for metric in definition.metric_definitions
    }
