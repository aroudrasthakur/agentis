"""Agent type catalog and custom agent type management."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.catalogs import DATA_SOURCE_CATALOG, model_catalog, tool_catalog
from app.agent_types.defaults import default_configuration, default_metric_configuration
from app.agent_types.schemas import (
    AgentMetricDefinition,
    AgentTypeCamelModel,
    AgentTypeDefinition,
    AgentTypeSummary,
    CustomAgentTypeCreate,
    CustomAgentTypeOut,
    CustomAgentTypeUpdate,
    MetricConfigurationEntry,
)
from app.agent_types.services import custom_types, registry
from app.authorization.deps import forbidden_response
from app.authorization.permissions.registry import P
from app.authorization.services.authorization_service import AuthorizationContext, AuthorizationError, require_permission
from app.db import get_db
from app.deps import get_current_user
from app.models import Agent, AgentDownload, AgentSource, User

router = APIRouter(prefix="/agent-types", tags=["agent-types"])


class SelectorOption(AgentTypeCamelModel):
    value: str
    label: str


class SelectorCatalogs(AgentTypeCamelModel):
    tools: list[SelectorOption] = Field(default_factory=list)
    models: list[SelectorOption] = Field(default_factory=list)
    data_sources: list[SelectorOption] = Field(default_factory=list)
    agents: list[SelectorOption] = Field(default_factory=list)


class AgentTypeDefaults(AgentTypeCamelModel):
    configuration: dict[str, Any] = Field(default_factory=dict)
    metric_configuration: dict[str, MetricConfigurationEntry] = Field(default_factory=dict)


def _options(pairs: Iterable[tuple[str, str]]) -> list[SelectorOption]:
    return [SelectorOption(value=value, label=label) for value, label in pairs]


@router.get("", response_model=list[AgentTypeSummary])
async def list_agent_types(
    include_archived: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentTypeSummary]:
    await require_permission(db, user, P.AGENT_TYPE_LIST)
    built_in = registry.list_built_in_summaries()
    custom = await registry.list_custom_summaries(
        db, user.id, include_archived=include_archived
    )
    return built_in + custom


@router.get("/built-in", response_model=list[AgentTypeSummary])
async def list_built_in_agent_types(
    _: User = Depends(get_current_user),
) -> list[AgentTypeSummary]:
    return registry.list_built_in_summaries()


@router.get("/catalogs", response_model=SelectorCatalogs)
async def get_selector_catalogs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SelectorCatalogs:
    """Reference data the schema-driven form needs for selector parameters."""
    owned = await db.execute(
        select(Agent).where(Agent.owner_user_id == user.id, Agent.source == AgentSource.local)
    )
    downloaded = await db.execute(
        select(Agent)
        .join(AgentDownload, AgentDownload.agent_id == Agent.id)
        .where(AgentDownload.user_id == user.id)
    )
    agents = {agent.id: agent for agent in [*owned.scalars().all(), *downloaded.scalars().all()]}

    return SelectorCatalogs(
        tools=_options(tool_catalog()),
        models=_options(model_catalog()),
        data_sources=_options(DATA_SOURCE_CATALOG),
        agents=[
            SelectorOption(value=str(agent.id), label=agent.name)
            for agent in sorted(agents.values(), key=lambda item: item.name.lower())
        ],
    )


@router.get("/custom", response_model=list[CustomAgentTypeOut])
async def list_custom_agent_types(
    include_archived: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CustomAgentTypeOut]:
    summaries = await registry.list_custom_summaries(
        db, user.id, include_archived=include_archived
    )
    output: list[CustomAgentTypeOut] = []
    for summary in summaries:
        if summary.family_id is None:
            continue
        row = await registry.latest_custom_row(db, summary.family_id)
        if row is None:
            continue
        in_use = await registry.custom_type_in_use(db, summary.family_id)
        output.append(registry.custom_row_to_out(row, in_use=in_use))
    return output


@router.post("/custom", response_model=CustomAgentTypeOut, status_code=status.HTTP_201_CREATED)
async def create_custom_agent_type(
    payload: CustomAgentTypeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomAgentTypeOut:
    try:
        await require_permission(db, user, P.AGENT_TYPE_CREATE)
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc
    try:
        row = await custom_types.create_custom_type(db, user, payload)
    except custom_types.CustomAgentTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return registry.custom_row_to_out(row)


@router.get("/custom/{family_id}", response_model=CustomAgentTypeOut)
async def get_custom_agent_type(
    family_id: UUID,
    version: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomAgentTypeOut:
    row = await registry.custom_row(db, family_id, version)
    if row is None or row.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Custom agent type not found")
    in_use = await registry.custom_type_in_use(db, family_id)
    return registry.custom_row_to_out(row, in_use=in_use)


@router.get("/custom/{family_id}/versions", response_model=list[CustomAgentTypeOut])
async def list_custom_agent_type_versions(
    family_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CustomAgentTypeOut]:
    rows = await registry.custom_versions(db, family_id)
    if not rows or rows[0].owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Custom agent type not found")
    output: list[CustomAgentTypeOut] = []
    for row in rows:
        in_use = await registry.custom_type_in_use(db, family_id, version=row.version)
        output.append(registry.custom_row_to_out(row, in_use=in_use))
    return output


@router.patch("/custom/{family_id}", response_model=CustomAgentTypeOut)
async def update_custom_agent_type(
    family_id: UUID,
    payload: CustomAgentTypeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomAgentTypeOut:
    try:
        await require_permission(
            db,
            user,
            P.AGENT_TYPE_UPDATE,
            AuthorizationContext(resource_type="agent_type", resource_id=str(family_id)),
        )
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc
    try:
        row, _forked = await custom_types.update_custom_type(db, user, family_id, payload)
    except custom_types.CustomAgentTypeError as exc:
        detail = str(exc)
        code = 404 if detail == "Custom agent type not found" else 400
        raise HTTPException(status_code=code, detail=detail) from exc
    in_use = await registry.custom_type_in_use(db, family_id, version=row.version)
    return registry.custom_row_to_out(row, in_use=in_use)


@router.post(
    "/custom/{family_id}/duplicate",
    response_model=CustomAgentTypeOut,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_custom_agent_type(
    family_id: UUID,
    version: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomAgentTypeOut:
    try:
        row = await custom_types.duplicate_custom_type(db, user, family_id, version)
    except custom_types.CustomAgentTypeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return registry.custom_row_to_out(row)


@router.post("/custom/{family_id}/archive", response_model=CustomAgentTypeOut)
async def archive_custom_agent_type(
    family_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomAgentTypeOut:
    try:
        rows = await custom_types.archive_custom_type(db, user, family_id)
    except custom_types.CustomAgentTypeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    in_use = await registry.custom_type_in_use(db, family_id)
    return registry.custom_row_to_out(rows[-1], in_use=in_use)


@router.get("/{type_id}", response_model=AgentTypeDefinition)
async def get_agent_type(
    type_id: str,
    version: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentTypeDefinition:
    definition = await _resolve_or_404(db, user, type_id, version)
    return definition


@router.get("/{type_id}/metrics", response_model=list[AgentMetricDefinition])
async def get_agent_type_metrics(
    type_id: str,
    version: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentMetricDefinition]:
    definition = await _resolve_or_404(db, user, type_id, version)
    return definition.metric_definitions


@router.get("/{type_id}/defaults", response_model=AgentTypeDefaults)
async def get_agent_type_defaults(
    type_id: str,
    version: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentTypeDefaults:
    definition = await _resolve_or_404(db, user, type_id, version)
    return AgentTypeDefaults(
        configuration=default_configuration(definition),
        metric_configuration={
            key: entry.model_dump(by_alias=True)
            for key, entry in default_metric_configuration(definition).items()
        },
    )


async def _resolve_or_404(
    db: AsyncSession, user: User, type_id: str, version: int | None
) -> AgentTypeDefinition:
    await require_permission(db, user, P.AGENT_TYPE_READ_DEF)
    if registry.is_custom_type_id(type_id):
        family_id = registry.custom_family_id(type_id)
        row = await registry.custom_row(db, family_id, version)
        if row is None or row.owner_user_id != user.id:
            raise HTTPException(status_code=404, detail="Agent type not found")
        return registry.custom_row_to_definition(row)

    try:
        return await registry.resolve_definition(db, type_id, version)
    except registry.AgentTypeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
