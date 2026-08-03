"""Resolution of agent type definitions (built-in registry + custom type rows)."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.builtin import BASE_PARAMETERS, BUILT_IN_AGENT_TYPES, BUILT_IN_SCHEMA_VERSION
from app.agent_types.schemas import (
    CUSTOM_TYPE_PREFIX,
    AgentTypeDefinition,
    AgentTypeSummary,
    CustomAgentTypeOut,
)
from app.models import Agent, CustomAgentType, CustomAgentTypeStatus


class AgentTypeNotFoundError(LookupError):
    """Raised when a type id or version cannot be resolved."""


def is_custom_type_id(type_id: str | None) -> bool:
    return bool(type_id) and str(type_id).startswith(CUSTOM_TYPE_PREFIX)


def custom_family_id(type_id: str) -> UUID:
    try:
        return UUID(type_id[len(CUSTOM_TYPE_PREFIX) :])
    except ValueError as exc:  # pragma: no cover - defensive
        raise AgentTypeNotFoundError(f"Malformed custom agent type id: {type_id}") from exc


def custom_type_id(family_id: UUID) -> str:
    return f"{CUSTOM_TYPE_PREFIX}{family_id}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "custom-type"


def built_in_definition(type_id: str) -> AgentTypeDefinition | None:
    return BUILT_IN_AGENT_TYPES.get(type_id)


def list_built_in_summaries() -> list[AgentTypeSummary]:
    return [_summary(definition) for definition in BUILT_IN_AGENT_TYPES.values()]


def _summary(definition: AgentTypeDefinition) -> AgentTypeSummary:
    return AgentTypeSummary(
        id=definition.id,
        name=definition.name,
        slug=definition.slug,
        description=definition.description,
        version=definition.version,
        status=definition.status,
        built_in=definition.built_in,
        base_type_id=definition.base_type_id,
        icon=definition.icon,
        use_cases=definition.use_cases,
        capabilities=definition.capabilities,
        default_autonomy_level=definition.default_autonomy_level,
        default_risk_level=definition.default_risk_level,
        parameter_count=len(definition.parameter_definitions),
        metric_count=len(definition.metric_definitions),
        family_id=definition.family_id,
    )


def custom_row_to_definition(row: CustomAgentType) -> AgentTypeDefinition:
    """Compose a resolvable definition: base parameters + optional base type + custom ones."""
    base_definition = (
        BUILT_IN_AGENT_TYPES.get(row.base_type_id) if row.base_type_id else None
    )

    inherited: list = []
    seen_keys: set[str] = set()
    if base_definition:
        for parameter in base_definition.parameter_definitions:
            inherited.append(parameter.model_copy(update={"inherited": True}))
            seen_keys.add(parameter.key)
    else:
        for parameter in BASE_PARAMETERS:
            inherited.append(parameter.model_copy(update={"inherited": True}))
            seen_keys.add(parameter.key)

    own = [
        parameter.model_copy(update={"inherited": False})
        for parameter in _parse_parameters(row.parameter_definitions)
        # A custom parameter with the same key overrides the inherited one.
    ]
    own_keys = {parameter.key for parameter in own}
    merged = [item for item in inherited if item.key not in own_keys] + own

    metrics = list(_parse_metrics(row.metric_definitions))
    if base_definition:
        base_metric_keys = {metric.key for metric in metrics}
        metrics = [
            metric
            for metric in base_definition.metric_definitions
            if metric.key not in base_metric_keys
        ] + metrics

    return AgentTypeDefinition(
        id=custom_type_id(row.family_id),
        name=row.name,
        slug=row.slug,
        description=row.description or "",
        version=row.version,
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        built_in=False,
        base_type_id=row.base_type_id,
        icon=row.icon,
        use_cases=[],
        capabilities=[],
        default_autonomy_level=row.default_autonomy_level,
        default_risk_level=row.default_risk_level,  # type: ignore[arg-type]
        parameter_definitions=merged,
        metric_definitions=metrics,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        family_id=row.family_id,
    )


def _parse_parameters(raw: object) -> list:
    from app.agent_types.schemas import AgentTypeParameterDefinition

    return [AgentTypeParameterDefinition.model_validate(item) for item in (raw or [])]


def _parse_metrics(raw: object) -> list:
    from app.agent_types.schemas import AgentMetricDefinition

    return [AgentMetricDefinition.model_validate(item) for item in (raw or [])]


def custom_row_to_out(row: CustomAgentType, *, in_use: bool = False) -> CustomAgentTypeOut:
    return CustomAgentTypeOut(
        id=custom_type_id(row.family_id),
        family_id=row.family_id,
        version=row.version,
        name=row.name,
        slug=row.slug,
        description=row.description,
        icon=row.icon,
        base_type_id=row.base_type_id,
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        parameter_definitions=_parse_parameters(row.parameter_definitions),
        metric_definitions=_parse_metrics(row.metric_definitions),
        default_autonomy_level=row.default_autonomy_level,
        default_risk_level=row.default_risk_level,  # type: ignore[arg-type]
        in_use=in_use,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
    )


async def latest_custom_row(
    db: AsyncSession, family_id: UUID, *, include_archived: bool = True
) -> CustomAgentType | None:
    stmt = select(CustomAgentType).where(CustomAgentType.family_id == family_id)
    if not include_archived:
        stmt = stmt.where(CustomAgentType.status != CustomAgentTypeStatus.archived)
    result = await db.execute(stmt.order_by(CustomAgentType.version.desc()))
    return result.scalars().first()


async def custom_row(
    db: AsyncSession, family_id: UUID, version: int | None
) -> CustomAgentType | None:
    if version is None:
        return await latest_custom_row(db, family_id)
    result = await db.execute(
        select(CustomAgentType).where(
            CustomAgentType.family_id == family_id, CustomAgentType.version == version
        )
    )
    return result.scalar_one_or_none()


async def custom_versions(db: AsyncSession, family_id: UUID) -> list[CustomAgentType]:
    result = await db.execute(
        select(CustomAgentType)
        .where(CustomAgentType.family_id == family_id)
        .order_by(CustomAgentType.version.asc())
    )
    return list(result.scalars().all())


async def resolve_definition(
    db: AsyncSession, type_id: str | None, version: int | None = None
) -> AgentTypeDefinition:
    """Resolve a type id (+ optional version) to a full definition."""
    if not type_id:
        raise AgentTypeNotFoundError("No agent type selected")

    if not is_custom_type_id(type_id):
        definition = BUILT_IN_AGENT_TYPES.get(type_id)
        if definition is None:
            raise AgentTypeNotFoundError(f"Unknown agent type: {type_id}")
        if version is not None and version != BUILT_IN_SCHEMA_VERSION:
            raise AgentTypeNotFoundError(
                f"Agent type '{type_id}' has no version {version}"
            )
        return definition

    row = await custom_row(db, custom_family_id(type_id), version)
    if row is None:
        raise AgentTypeNotFoundError(
            f"Custom agent type {type_id} version {version if version is not None else 'latest'} not found"
        )
    return custom_row_to_definition(row)


async def list_custom_summaries(
    db: AsyncSession, owner_user_id: UUID, *, include_archived: bool = False
) -> list[AgentTypeSummary]:
    """Latest version per family owned by the user."""
    result = await db.execute(
        select(CustomAgentType)
        .where(CustomAgentType.owner_user_id == owner_user_id)
        .order_by(CustomAgentType.family_id, CustomAgentType.version.desc())
    )
    latest: dict[UUID, CustomAgentType] = {}
    for row in result.scalars().all():
        if row.family_id not in latest:
            latest[row.family_id] = row

    summaries: list[AgentTypeSummary] = []
    for row in latest.values():
        if not include_archived and row.status == CustomAgentTypeStatus.archived:
            continue
        summaries.append(_summary(custom_row_to_definition(row)))
    return sorted(summaries, key=lambda item: item.name.lower())


async def custom_type_in_use(
    db: AsyncSession, family_id: UUID, *, version: int | None = None
) -> bool:
    """True when an agent is assigned to (or deployed on) this custom type."""
    type_id = custom_type_id(family_id)
    stmt = select(Agent.id).where(
        (Agent.agent_type_id == type_id) | (Agent.deployed_type_id == type_id)
    )
    if version is not None:
        stmt = stmt.where(
            (Agent.agent_type_version == version) | (Agent.deployed_type_version == version)
        )
    result = await db.execute(stmt.limit(1))
    return result.first() is not None


async def custom_type_deployed(db: AsyncSession, family_id: UUID, version: int) -> bool:
    result = await db.execute(
        select(Agent.id)
        .where(
            Agent.deployed_type_id == custom_type_id(family_id),
            Agent.deployed_type_version == version,
        )
        .limit(1)
    )
    return result.first() is not None
