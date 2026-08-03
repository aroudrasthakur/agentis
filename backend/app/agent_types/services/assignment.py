"""Assigning types to agents, saving configuration, and deploying.

Deployment writes an immutable snapshot (``deployed_*``); later type edits never
mutate it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.defaults import default_configuration, default_metric_configuration
from app.agent_types.schemas import (
    AgentTypeAssignment,
    AgentTypeConfigurationUpdate,
    AgentTypeDefinition,
    AgentTypeValidationResult,
    CompatibilityReport,
    TypeMigrationRequest,
)
from app.agent_types.services import compatibility, migration, registry
from app.agent_types.services.validation import validate_agent
from app.models import Agent


class AssignmentError(ValueError):
    """Raised when a type cannot be assigned to an agent."""


def _metric_payload(entries: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, entry in entries.items():
        output[key] = entry.model_dump(by_alias=True) if hasattr(entry, "model_dump") else dict(entry)
    return output


async def refresh_validation_status(db: AsyncSession, agent: Agent) -> AgentTypeValidationResult:
    """Recompute and persist the agent's validation status."""
    result, _definition = await validate_agent(db, agent)
    agent.agent_type_validation_status = {
        **result.model_dump(mode="json", by_alias=True),
        "requiresTypeSetup": agent.agent_type_id is None,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
    return result


async def assign_type(
    db: AsyncSession, agent: Agent, payload: AgentTypeAssignment
) -> tuple[AgentTypeValidationResult, CompatibilityReport, AgentTypeDefinition]:
    """Select (or change) an agent's type, preserving values the new type supports."""
    try:
        definition = await registry.resolve_definition(db, payload.type_id, payload.type_version)
    except registry.AgentTypeNotFoundError as exc:
        raise AssignmentError(str(exc)) from exc

    if definition.status == "archived" and agent.agent_type_id != definition.id:
        raise AssignmentError(
            f"Agent type '{definition.name}' is archived and cannot be assigned to an agent."
        )
    if definition.id == "custom":
        raise AssignmentError(
            "Select a specific custom agent type built in the Custom Agent Type builder."
        )

    previous_definition: AgentTypeDefinition | None = None
    if agent.agent_type_id:
        try:
            previous_definition = await registry.resolve_definition(
                db, agent.agent_type_id, agent.agent_type_version
            )
        except registry.AgentTypeNotFoundError:
            previous_definition = None

    existing = dict(agent.agent_type_configuration or {})
    report = compatibility.analyze(definition, existing, previous=previous_definition)
    carried = compatibility.carry_over(
        definition, existing, keep_incompatible=not payload.discard_incompatible
    )

    configuration = {**default_configuration(definition), **carried, **dict(payload.configuration)}

    metrics = _metric_payload(default_metric_configuration(definition))
    for key, entry in (agent.agent_metric_configuration or {}).items():
        if key in metrics and isinstance(entry, dict):
            metrics[key] = {**metrics[key], **entry}
    for key, entry in payload.metric_configuration.items():
        metrics[key] = entry.model_dump(by_alias=True)

    agent.agent_type_id = definition.id
    agent.agent_type_version = definition.version
    agent.agent_type_configuration = configuration
    agent.agent_metric_configuration = metrics

    result = await refresh_validation_status(db, agent)
    await db.commit()
    await db.refresh(agent)
    return result, report, definition


async def update_configuration(
    db: AsyncSession, agent: Agent, payload: AgentTypeConfigurationUpdate
) -> AgentTypeValidationResult:
    if agent.agent_type_id is None:
        raise AssignmentError("Select an agent type before configuring it.")

    if payload.configuration is not None:
        agent.agent_type_configuration = dict(payload.configuration)
    if payload.metric_configuration is not None:
        agent.agent_metric_configuration = _metric_payload(dict(payload.metric_configuration))

    result = await refresh_validation_status(db, agent)
    await db.commit()
    await db.refresh(agent)
    return result


async def deploy(db: AsyncSession, agent: Agent) -> AgentTypeValidationResult:
    """Validate server-side, then snapshot the exact type version and configuration."""
    result = await refresh_validation_status(db, agent)
    if not result.valid:
        await db.commit()
        raise AssignmentError(
            "; ".join(result.deployment_blockers)
            or "The agent type configuration is not valid for deployment."
        )

    agent.deployed_type_id = agent.agent_type_id
    agent.deployed_type_version = agent.agent_type_version
    agent.deployed_configuration = dict(agent.agent_type_configuration or {})
    agent.deployed_metric_configuration = dict(agent.agent_metric_configuration or {})
    agent.deployed_at = datetime.now(timezone.utc)
    agent.is_active = True

    await db.commit()
    await db.refresh(agent)
    return result


async def migration_preview(db: AsyncSession, agent: Agent, target_version: int | None):
    if not agent.agent_type_id:
        raise AssignmentError("This agent has no type to migrate.")

    current = None
    try:
        current = await registry.resolve_definition(
            db, agent.agent_type_id, agent.agent_type_version
        )
    except registry.AgentTypeNotFoundError:
        current = None

    try:
        target = await registry.resolve_definition(db, agent.agent_type_id, target_version)
    except registry.AgentTypeNotFoundError as exc:
        raise AssignmentError(str(exc)) from exc

    return migration.preview(current, target, dict(agent.agent_type_configuration or {})), target


async def migrate(
    db: AsyncSession, agent: Agent, payload: TypeMigrationRequest
) -> tuple[AgentTypeValidationResult, AgentTypeDefinition]:
    preview_result, target = await migration_preview(db, agent, payload.target_version)

    configuration = dict(agent.agent_type_configuration or {})
    if payload.configuration is not None:
        configuration.update(payload.configuration)
    # Values the new version cannot represent are dropped rather than silently kept.
    configuration = {
        **default_configuration(target),
        **compatibility.carry_over(target, configuration),
    }

    metrics = _metric_payload(default_metric_configuration(target))
    for key, entry in (agent.agent_metric_configuration or {}).items():
        if key in metrics and isinstance(entry, dict):
            metrics[key] = {**metrics[key], **entry}
    if payload.metric_configuration is not None:
        for key, entry in payload.metric_configuration.items():
            metrics[key] = entry.model_dump(by_alias=True)

    agent.agent_type_version = target.version
    agent.agent_type_configuration = configuration
    agent.agent_metric_configuration = metrics

    result = await refresh_validation_status(db, agent)
    await db.commit()
    await db.refresh(agent)
    _ = preview_result
    return result, target
