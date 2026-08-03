"""Built-in agent type catalog.

Built-in types are code, not data: they cannot be deleted or edited by users and
are exposed as read-only system definitions. ``BUILT_IN_SCHEMA_VERSION`` is bumped
whenever a built-in parameter or metric definition changes.
"""

from __future__ import annotations

from app.agent_types.builtin import (
    action,
    custom,
    evaluation,
    governance,
    memory,
    operational,
    orchestration,
    retrieval_context,
    task_domain,
    user_facing,
)
from app.agent_types.builtin.base_parameters import BASE_PARAMETERS, BASE_PARAMETER_KEYS
from app.agent_types.guards import assert_no_human_loop_fields
from app.agent_types.schemas import AgentTypeDefinition

BUILT_IN_SCHEMA_VERSION = 1

_MODULES = (
    user_facing,
    orchestration,
    task_domain,
    action,
    evaluation,
    governance,
    retrieval_context,
    memory,
    operational,
    custom,
)


def _assemble(definition: AgentTypeDefinition) -> AgentTypeDefinition:
    """Prefix parameter/metric ids with the type id and prepend shared base parameters."""
    parameters = [
        item.model_copy(update={"id": f"{definition.id}.{item.key}"})
        for item in [*BASE_PARAMETERS, *definition.parameter_definitions]
    ]
    metrics = [
        item.model_copy(update={"id": f"{definition.id}.{item.key}"})
        for item in definition.metric_definitions
    ]
    return definition.model_copy(
        update={
            "version": BUILT_IN_SCHEMA_VERSION,
            "built_in": True,
            "status": "active",
            "parameter_definitions": parameters,
            "metric_definitions": metrics,
        }
    )


BUILT_IN_AGENT_TYPES: dict[str, AgentTypeDefinition] = {
    module.TYPE.id: _assemble(module.TYPE) for module in _MODULES
}

# Fail fast at import time if a built-in definition ever declares HITL configuration.
for _definition in BUILT_IN_AGENT_TYPES.values():
    assert_no_human_loop_fields(
        _definition.model_dump(mode="json", by_alias=True),
        label=f"Built-in agent type '{_definition.id}'",
    )

__all__ = [
    "BASE_PARAMETERS",
    "BASE_PARAMETER_KEYS",
    "BUILT_IN_AGENT_TYPES",
    "BUILT_IN_SCHEMA_VERSION",
]
