from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.services import gating
from app.authorization.deps import forbidden_response
from app.authorization.permissions.registry import P
from app.authorization.services.authorization_service import (
    AuthorizationContext,
    AuthorizationError,
    require_permission,
)
from app.db import get_db
from app.deps import get_current_user
from app.models import Agent, HostingMode, User
from app.schemas import AgentCreate, AgentOut, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Agent]:
    try:
        await require_permission(db, user, P.AGENT_LIST)
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc
    result = await db.execute(select(Agent).order_by(Agent.created_at.asc()))
    return list(result.scalars().all())


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    try:
        await require_permission(db, user, P.AGENT_CREATE)
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc
    if payload.hosting_mode == HostingMode.remote_mcp and not payload.endpoint_url:
        raise HTTPException(status_code=400, detail="endpoint_url is required for remote_mcp agents")
    existing = await db.execute(select(Agent).where(Agent.agent_key == payload.agent_key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="agent_key already exists")
    data = payload.model_dump()
    data["is_active"] = False
    agent = Agent(**data)
    agent.owner_user_id = user.id
    agent.agent_type_validation_status = {"valid": False, "requiresTypeSetup": True}
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        await require_permission(
            db,
            user,
            P.AGENT_READ,
            AuthorizationContext(resource_type="agent", resource_id=agent_id),
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    return agent


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        await require_permission(
            db,
            user,
            P.AGENT_UPDATE,
            AuthorizationContext(resource_type="agent", resource_id=agent_id),
        )
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_active") is True and not agent.is_active:
        blocked = gating.deployment_block_reason(agent)
        if blocked:
            raise HTTPException(status_code=400, detail=blocked)
    for key, value in data.items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent
