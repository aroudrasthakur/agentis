"""Value compatibility when an agent switches type or type version."""

from __future__ import annotations

from typing import Any, Mapping

from app.agent_types.schemas import (
    AgentParameterType,
    AgentTypeDefinition,
    AgentTypeParameterDefinition,
    CompatibilityReport,
)

_TEXTUAL = {AgentParameterType.text, AgentParameterType.textarea, AgentParameterType.select}
_LISTY = {
    AgentParameterType.multi_select,
    AgentParameterType.tool_selector,
    AgentParameterType.agent_selector,
    AgentParameterType.data_source_selector,
}


def value_fits(parameter: AgentTypeParameterDefinition, value: Any) -> bool:
    """True when an existing value can be carried over to this parameter."""
    if value is None:
        return True

    kind = parameter.type
    if kind is AgentParameterType.boolean:
        return isinstance(value, bool)
    if kind is AgentParameterType.number:
        return not isinstance(value, bool) and isinstance(value, (int, float))
    if kind is AgentParameterType.json:
        return isinstance(value, (dict, list, str))
    if kind in _LISTY:
        if not isinstance(value, list):
            return False
        allowed = {option.value for option in parameter.options or []}
        return not allowed or all(str(item) in allowed for item in value)
    if kind in _TEXTUAL:
        if not isinstance(value, (str, int, float)):
            return False
        allowed = {option.value for option in parameter.options or []}
        return not allowed or str(value) in allowed
    return isinstance(value, (str, int, float, list, dict))


def analyze(
    target: AgentTypeDefinition,
    configuration: Mapping[str, Any],
    *,
    previous: AgentTypeDefinition | None = None,
) -> CompatibilityReport:
    by_key = {parameter.key: parameter for parameter in target.parameter_definitions}
    preserved: list[str] = []
    incompatible: list[str] = []

    for key, value in configuration.items():
        parameter = by_key.get(key)
        if parameter is None or not value_fits(parameter, value):
            incompatible.append(key)
        else:
            preserved.append(key)

    previous_keys = (
        {parameter.key for parameter in previous.parameter_definitions} if previous else set()
    )
    newly_required = [
        parameter.key
        for parameter in target.parameter_definitions
        if parameter.required
        and parameter.key not in previous_keys
        and parameter.key not in configuration
    ]

    return CompatibilityReport(
        preserved_keys=sorted(preserved),
        incompatible_keys=sorted(incompatible),
        newly_required_keys=sorted(newly_required),
    )


def carry_over(
    target: AgentTypeDefinition,
    configuration: Mapping[str, Any],
    *,
    keep_incompatible: bool = False,
) -> dict[str, Any]:
    """Keep values the target type can still use; drop the rest unless asked otherwise."""
    by_key = {parameter.key: parameter for parameter in target.parameter_definitions}
    result: dict[str, Any] = {}
    for key, value in configuration.items():
        parameter = by_key.get(key)
        if parameter is not None and value_fits(parameter, value):
            result[key] = value
        elif keep_incompatible:
            result[key] = value
    return result
