from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.schemas import (
    AgentTypeAssignment,
    AgentTypeConfigurationUpdate,
    AgentTypeDefinition,
    AgentTypeValidationResult,
    CompatibilityReport,
    DeploymentReadiness,
    TypeMigrationPreview,
    TypeMigrationRequest,
)
from app.agent_types.services import assignment, gating
from app.agent_types.services.readiness import build_readiness
from app.authorization.deps import forbidden_response
from app.authorization.permissions.registry import P
from app.authorization.services.authorization_service import (
    AuthorizationContext,
    AuthorizationError,
    authorize,
    require_permission,
)
from app.db import get_db
from app.deps import get_current_user
from app.models import Agent, AgentDownload, AgentSource, GatheringAgent, GatheringMember, HostingMode, User
from app.schemas import AgentDescriptionUpdate, AgentOut, AgentUpdate, LocalAgentCreate
from app.services.agent_description import (
    AgentDescriptionProfile,
    AgentDescriptionSummary,
    DESCRIPTION_FORMAT_KEY,
    build_profile,
    build_summary,
    resolve_type_name,
)

router = APIRouter(prefix="/guild", tags=["guild"])


class AgentTypeAssignmentResponse(BaseModel):
    agent: AgentOut
    validation: AgentTypeValidationResult
    compatibility: CompatibilityReport
    readiness: DeploymentReadiness
    definition: AgentTypeDefinition


class AgentTypeConfigurationResponse(BaseModel):
    agent: AgentOut
    validation: AgentTypeValidationResult
    readiness: DeploymentReadiness


class AgentDeployResponse(BaseModel):
    agent: AgentOut
    readiness: DeploymentReadiness


class AgentMigrationResponse(BaseModel):
    agent: AgentOut
    validation: AgentTypeValidationResult
    readiness: DeploymentReadiness
    preview: TypeMigrationPreview


def _agent_out(agent: Agent, *, downloaded: bool = False) -> AgentOut:
    return AgentOut.from_agent(agent, downloaded=downloaded)


async def _require_perm(
    db: AsyncSession,
    user: User,
    permission: str,
    *,
    agent_id: UUID | None = None,
    workspace_id: UUID | None = None,
) -> None:
    ctx = AuthorizationContext(
        workspace_id=workspace_id,
        resource_type="agent" if agent_id else None,
        resource_id=agent_id,
    )
    try:
        await require_permission(db, user, permission, ctx)
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc


async def _owned_agent(
    db: AsyncSession,
    agent_id: UUID,
    user: User,
    permission: str = P.AGENT_UPDATE,
) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Owned agent not found")
    try:
        await _require_perm(db, user, permission, agent_id=agent_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN and agent.owner_user_id != user.id:
            raise HTTPException(status_code=404, detail="Owned agent not found") from exc
        raise
    return agent


async def _viewable_agent(db: AsyncSession, agent_id: UUID, user: User) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent or (not agent.is_active and agent.owner_user_id != user.id):
        raise HTTPException(status_code=404, detail="Agent not found")
    decision = await authorize(
        db,
        user,
        P.AGENT_READ,
        AuthorizationContext(resource_type="agent", resource_id=agent_id),
    )
    if not decision.allowed:
        decision2 = await authorize(
            db,
            user,
            P.AGENT_READ_ACCESSIBLE,
            AuthorizationContext(resource_type="agent", resource_id=agent_id),
        )
        if not decision2.allowed:
            raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents", response_model=list[AgentOut])
async def list_guild_agents(
    tab: str = Query(default="local", pattern="^(local|downloaded|directory)$"),
    q: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    await _require_perm(db, user, P.AGENT_LIST_ACCESSIBLE)
    query_text = (q or "").strip().lower()

    if tab == "local":
        # Owned agents stay listed while inactive so their type setup can be finished.
        stmt = select(Agent).where(
            Agent.owner_user_id == user.id,
            Agent.source == AgentSource.local,
        )
        if query_text:
            stmt = stmt.where(
                or_(
                    Agent.name.ilike(f"%{query_text}%"),
                    Agent.description.ilike(f"%{query_text}%"),
                    Agent.agent_key.ilike(f"%{query_text}%"),
                )
            )
        result = await db.execute(stmt.order_by(Agent.created_at.desc()))
        return [_agent_out(a) for a in result.scalars().all()]

    if tab == "downloaded":
        stmt = (
            select(Agent)
            .join(AgentDownload, AgentDownload.agent_id == Agent.id)
            .where(AgentDownload.user_id == user.id, Agent.is_active.is_(True))
        )
        if query_text:
            stmt = stmt.where(
                or_(
                    Agent.name.ilike(f"%{query_text}%"),
                    Agent.description.ilike(f"%{query_text}%"),
                )
            )
        result = await db.execute(stmt.order_by(AgentDownload.created_at.desc()))
        return [_agent_out(a, downloaded=True) for a in result.scalars().all()]

    stmt = select(Agent).where(Agent.is_public.is_(True), Agent.is_active.is_(True))
    if query_text:
        stmt = stmt.where(
            or_(
                Agent.name.ilike(f"%{query_text}%"),
                Agent.description.ilike(f"%{query_text}%"),
                Agent.agent_key.ilike(f"%{query_text}%"),
            )
        )
    result = await db.execute(stmt.order_by(Agent.name.asc()))
    agents = list(result.scalars().all())

    downloaded_ids: set[UUID] = set()
    if agents:
        dl = await db.execute(
            select(AgentDownload.agent_id).where(
                AgentDownload.user_id == user.id,
                AgentDownload.agent_id.in_([a.id for a in agents]),
            )
        )
        downloaded_ids = set(dl.scalars().all())

    return [_agent_out(a, downloaded=a.id in downloaded_ids) for a in agents]


async def _description_profile(db: AsyncSession, agent: Agent) -> AgentDescriptionProfile:
    definition, type_name = await resolve_type_name(db, agent)
    return await build_profile(agent, definition, type_name=type_name)


@router.get("/agents/attachable", response_model=list[AgentOut])
async def list_attachable_agents(
    gathering_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    """Agents the user may attach in a session: local, downloaded, and gathering shelf."""
    by_id: dict[UUID, Agent] = {}

    local = await db.execute(
        select(Agent).where(
            Agent.owner_user_id == user.id,
            Agent.source == AgentSource.local,
            Agent.is_active.is_(True),
        )
    )
    for agent in local.scalars().all():
        by_id[agent.id] = agent

    downloaded = await db.execute(
        select(Agent)
        .join(AgentDownload, AgentDownload.agent_id == Agent.id)
        .where(AgentDownload.user_id == user.id, Agent.is_active.is_(True))
    )
    for agent in downloaded.scalars().all():
        by_id[agent.id] = agent

    downloaded_ids: set[UUID] = set()
    if by_id:
        dl = await db.execute(
            select(AgentDownload.agent_id).where(
                AgentDownload.user_id == user.id,
                AgentDownload.agent_id.in_(list(by_id.keys())),
            )
        )
        downloaded_ids = set(dl.scalars().all())

    if gathering_id is not None:
        member = await db.execute(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == user.id,
            )
        )
        if member.scalar_one_or_none():
            gathering_agents = await db.execute(
                select(Agent)
                .join(GatheringAgent, GatheringAgent.agent_id == Agent.id)
                .where(GatheringAgent.gathering_id == gathering_id, Agent.is_active.is_(True))
            )
            for agent in gathering_agents.scalars().all():
                by_id[agent.id] = agent
            if by_id:
                dl2 = await db.execute(
                    select(AgentDownload.agent_id).where(
                        AgentDownload.user_id == user.id,
                        AgentDownload.agent_id.in_(list(by_id.keys())),
                    )
                )
                downloaded_ids |= set(dl2.scalars().all())

    # Only agents with a deployed, valid agent type may join a session.
    ordered = sorted(
        (agent for agent in by_id.values() if gating.is_deployable(agent)),
        key=lambda a: a.name.lower(),
    )
    return [_agent_out(a, downloaded=a.id in downloaded_ids) for a in ordered]


@router.get("/agents/descriptions", response_model=list[AgentDescriptionSummary])
async def list_agent_descriptions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentDescriptionSummary]:
    """Short, readable list of your agents with description previews and setup status."""
    by_id: dict[UUID, Agent] = {}

    local = await db.execute(
        select(Agent).where(
            Agent.owner_user_id == user.id,
            Agent.source == AgentSource.local,
        )
    )
    for agent in local.scalars().all():
        by_id[agent.id] = agent

    downloaded = await db.execute(
        select(Agent)
        .join(AgentDownload, AgentDownload.agent_id == Agent.id)
        .where(AgentDownload.user_id == user.id)
    )
    for agent in downloaded.scalars().all():
        by_id[agent.id] = agent

    summaries: list[AgentDescriptionSummary] = []
    for agent in by_id.values():
        _, type_name = await resolve_type_name(db, agent)
        summaries.append(await build_summary(agent, type_name=type_name))
    return sorted(summaries, key=lambda item: item.name.lower())


@router.get("/agents/{agent_id}/description", response_model=AgentDescriptionProfile)
async def get_agent_description(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentDescriptionProfile:
    """Full, human-readable view of an agent's description and type configuration."""
    agent = await _viewable_agent(db, agent_id, user)
    return await _description_profile(db, agent)


@router.put("/agents/{agent_id}/description", response_model=AgentDescriptionProfile)
async def update_agent_description(
    agent_id: UUID,
    payload: AgentDescriptionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentDescriptionProfile:
    agent = await _owned_agent(db, agent_id, user, P.AGENT_UPDATE_INSTRUCTIONS)
    if payload.description is not None:
        text = payload.description.strip()
        agent.description = text or None
    if payload.description_format is not None:
        metadata = dict(agent.metadata_ or {})
        metadata[DESCRIPTION_FORMAT_KEY] = payload.description_format
        agent.metadata_ = metadata
    agent.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(agent)
    return await _description_profile(db, agent)


@router.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent_info(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentOut:
    agent = await _viewable_agent(db, agent_id, user)
    downloaded = False
    dl = await db.execute(
        select(AgentDownload).where(
            AgentDownload.user_id == user.id, AgentDownload.agent_id == agent_id
        )
    )
    downloaded = dl.scalar_one_or_none() is not None
    return _agent_out(agent, downloaded=downloaded)


@router.patch("/agents/{agent_id}", response_model=AgentOut)
async def update_agent_info(
    agent_id: UUID,
    payload: AgentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentOut:
    agent = await _owned_agent(db, agent_id, user)
    data = payload.model_dump(exclude_unset=True)

    # Activation and publication both require a deployed, valid agent type.
    if data.get("is_active") is True and not agent.is_active:
        blocked = gating.deployment_block_reason(agent)
        if blocked:
            raise HTTPException(status_code=400, detail=blocked)
    if data.get("is_public") is True and not agent.is_public:
        blocked = gating.deployment_block_reason(agent)
        if blocked:
            raise HTTPException(status_code=400, detail=blocked)

    if "metadata" in data:
        agent.metadata_ = data.pop("metadata") or {}
    for key, value in data.items():
        setattr(agent, key, value)
    agent.updated_at = datetime.now(timezone.utc)
    await assignment.refresh_validation_status(db, agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_out(agent)


@router.post("/agents/{agent_id}/type", response_model=AgentTypeAssignmentResponse)
async def assign_agent_type(
    agent_id: UUID,
    payload: AgentTypeAssignment,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentTypeAssignmentResponse:
    existing = await db.get(Agent, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Owned agent not found")
    perm = P.AGENT_TYPE_ASSIGN if not existing.agent_type_id else P.AGENT_TYPE_CHANGE
    agent = await _owned_agent(db, agent_id, user, perm)
    try:
        validation, report, definition = await assignment.assign_type(db, agent, payload)
    except assignment.AssignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AgentTypeAssignmentResponse(
        agent=_agent_out(agent),
        validation=validation,
        compatibility=report,
        readiness=await build_readiness(db, agent),
        definition=definition,
    )


@router.patch("/agents/{agent_id}/type/configuration", response_model=AgentTypeConfigurationResponse)
async def update_agent_type_configuration(
    agent_id: UUID,
    payload: AgentTypeConfigurationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentTypeConfigurationResponse:
    agent = await _owned_agent(db, agent_id, user, P.AGENT_UPDATE_CONFIGURATION)
    try:
        validation = await assignment.update_configuration(db, agent, payload)
    except assignment.AssignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AgentTypeConfigurationResponse(
        agent=_agent_out(agent),
        validation=validation,
        readiness=await build_readiness(db, agent),
    )


@router.post("/agents/{agent_id}/validate", response_model=AgentTypeValidationResult)
async def validate_agent_type_configuration(
    agent_id: UUID,
    payload: AgentTypeConfigurationUpdate | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentTypeValidationResult:
    """Dry-run validation; nothing is persisted."""
    from app.agent_types.services.validation import validate_agent

    agent = await _owned_agent(db, agent_id, user, P.AGENT_UPDATE_CONFIGURATION)
    metric_configuration = None
    if payload and payload.metric_configuration is not None:
        metric_configuration = {
            key: entry.model_dump(by_alias=True)
            for key, entry in payload.metric_configuration.items()
        }

    result, _definition = await validate_agent(
        db,
        agent,
        configuration=payload.configuration if payload else None,
        metric_configuration=metric_configuration,
    )
    return result


@router.get("/agents/{agent_id}/deployment-readiness", response_model=DeploymentReadiness)
async def get_deployment_readiness(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeploymentReadiness:
    agent = await _owned_agent(db, agent_id, user, P.AGENT_DEPLOYMENT_READ)
    return await build_readiness(db, agent)


@router.post("/agents/{agent_id}/deploy", response_model=AgentDeployResponse)
async def deploy_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentDeployResponse:
    agent = await _owned_agent(db, agent_id, user, P.AGENT_DEPLOY)
    try:
        await assignment.deploy(db, agent)
    except assignment.AssignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AgentDeployResponse(agent=_agent_out(agent), readiness=await build_readiness(db, agent))


@router.get("/agents/{agent_id}/type/migration-preview", response_model=TypeMigrationPreview)
async def preview_agent_type_migration(
    agent_id: UUID,
    target_version: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TypeMigrationPreview:
    agent = await _owned_agent(db, agent_id, user, P.AGENT_TYPE_MIGRATE)
    try:
        preview, _target = await assignment.migration_preview(db, agent, target_version)
    except assignment.AssignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return preview


@router.post("/agents/{agent_id}/type/migrate", response_model=AgentMigrationResponse)
async def migrate_agent_type(
    agent_id: UUID,
    payload: TypeMigrationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentMigrationResponse:
    agent = await _owned_agent(db, agent_id, user, P.AGENT_TYPE_MIGRATE)
    try:
        preview, _target = await assignment.migration_preview(db, agent, payload.target_version)
        validation, _definition = await assignment.migrate(db, agent, payload)
    except assignment.AssignmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AgentMigrationResponse(
        agent=_agent_out(agent),
        validation=validation,
        readiness=await build_readiness(db, agent),
        preview=preview,
    )


@router.post(
    "/agents/local",
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_local_agent(
    payload: LocalAgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentOut:
    await _require_perm(db, user, P.AGENT_CREATE)
    existing = await db.execute(select(Agent).where(Agent.agent_key == payload.agent_key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="agent_key already exists")
    if payload.hosting_mode == HostingMode.remote_mcp and not payload.endpoint_url:
        raise HTTPException(status_code=400, detail="endpoint_url required for remote_mcp")

    agent = Agent(
        name=payload.name.strip(),
        agent_key=payload.agent_key.strip(),
        org_tag=payload.org_tag,
        hosting_mode=payload.hosting_mode,
        endpoint_url=payload.endpoint_url,
        description=payload.description,
        capabilities=list(payload.capabilities or []),
        # A new agent stays inactive until it has a deployed agent type.
        is_active=False,
        source=AgentSource.local,
        is_public=False,
        owner_user_id=user.id,
        version=payload.version,
        tags=list(payload.tags or []),
        notes=payload.notes,
        metadata_=dict(payload.metadata or {}),
        agent_type_validation_status={"valid": False, "requiresTypeSetup": True},
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_out(agent)


@router.post("/agents/{agent_id}/download", response_model=AgentOut)
async def download_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentOut:
    agent = await db.get(Agent, agent_id)
    if not agent or not agent.is_active or not agent.is_public:
        raise HTTPException(status_code=404, detail="Public agent not found")

    existing = await db.execute(
        select(AgentDownload).where(
            AgentDownload.user_id == user.id, AgentDownload.agent_id == agent_id
        )
    )
    if not existing.scalar_one_or_none():
        db.add(AgentDownload(user_id=user.id, agent_id=agent_id))
        await db.commit()
    return _agent_out(agent, downloaded=True)
