"""Agent type version migration: diffing definitions and moving an agent forward.

Deployed snapshots (``deployed_*`` columns) are never touched here — a deployed
agent stays reproducible on the exact version it was deployed with.
"""

from __future__ import annotations

from typing import Any, Mapping

from app.agent_types.schemas import (
    AgentTypeDefinition,
    AgentTypeParameterDefinition,
    ParameterDiff,
    TypeMigrationPreview,
)


def _diff_entry(parameter: AgentTypeParameterDefinition) -> ParameterDiff:
    return ParameterDiff(
        key=parameter.key,
        label=parameter.label,
        section=parameter.section.value,
        required=parameter.required,
        deployment_blocking=bool(
            parameter.deployment_blocking
            if parameter.deployment_blocking is not None
            else parameter.required
        ),
    )


def _signature(parameter: AgentTypeParameterDefinition) -> tuple[Any, ...]:
    return (
        parameter.type.value,
        parameter.section.value,
        parameter.required,
        tuple(sorted(option.value for option in parameter.options or [])),
        parameter.validation.model_dump_json() if parameter.validation else None,
        parameter.visible_when.model_dump_json() if parameter.visible_when else None,
        parameter.deployment_blocking,
    )


def preview(
    current: AgentTypeDefinition | None,
    target: AgentTypeDefinition,
    configuration: Mapping[str, Any],
) -> TypeMigrationPreview:
    current_by_key = (
        {item.key: item for item in current.parameter_definitions} if current else {}
    )
    target_by_key = {item.key: item for item in target.parameter_definitions}

    added = [_diff_entry(item) for key, item in target_by_key.items() if key not in current_by_key]
    removed = [
        _diff_entry(item) for key, item in current_by_key.items() if key not in target_by_key
    ]
    changed = [
        _diff_entry(item)
        for key, item in target_by_key.items()
        if key in current_by_key and _signature(item) != _signature(current_by_key[key])
    ]

    newly_required = sorted(
        item.key
        for item in target.parameter_definitions
        if item.required and _is_unset(configuration.get(item.key))
    )

    return TypeMigrationPreview(
        from_version=current.version if current else None,
        to_version=target.version,
        added_parameters=sorted(added, key=lambda item: item.key),
        removed_parameters=sorted(removed, key=lambda item: item.key),
        changed_parameters=sorted(changed, key=lambda item: item.key),
        newly_required_parameters=newly_required,
        blocks_deployment=bool(newly_required),
    )


def _is_unset(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) == 0
    return False
