"""Conditional visibility evaluation for schema-driven parameters."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.agent_types.schemas import AgentTypeParameterDefinition


def _matches(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "truthy":
        if isinstance(actual, (list, dict, str)):
            return len(actual) > 0
        return bool(actual)
    if operator == "contains":
        if isinstance(actual, (list, tuple, set)):
            return any(_scalar_equals(item, expected) for item in actual)
        if isinstance(actual, str):
            return str(expected) in actual
        return False
    if operator == "equals":
        return _scalar_equals(actual, expected)
    if operator == "not_equals":
        return not _scalar_equals(actual, expected)
    return True


def _scalar_equals(actual: Any, expected: Any) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, bool) or isinstance(expected, bool):
        return bool(actual) is bool(expected)
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return float(actual) == float(expected)
    return str(actual) == str(expected)


def is_visible(
    definition: AgentTypeParameterDefinition,
    configuration: Mapping[str, Any],
    by_key: Mapping[str, AgentTypeParameterDefinition] | None = None,
    _seen: frozenset[str] = frozenset(),
) -> bool:
    """A parameter is visible when its condition holds and its parent is visible too."""
    condition = definition.visible_when
    if condition is None:
        return True
    if definition.key in _seen:  # guard against cyclic visibleWhen chains
        return True

    parent_value = configuration.get(condition.parameter_key)
    if not _matches(condition.operator, parent_value, condition.value):
        return False

    if by_key is not None:
        parent = by_key.get(condition.parameter_key)
        if parent is not None:
            return is_visible(parent, configuration, by_key, _seen | {definition.key})
    return True


def visible_parameters(
    definitions: Iterable[AgentTypeParameterDefinition],
    configuration: Mapping[str, Any],
) -> list[AgentTypeParameterDefinition]:
    items = list(definitions)
    by_key = {item.key: item for item in items}
    return [item for item in items if is_visible(item, configuration, by_key)]
