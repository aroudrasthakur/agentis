from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Agent, HostingMode
from app.schemas import AgentCreate, AgentOut, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)) -> list[Agent]:
    result = await db.execute(select(Agent).order_by(Agent.created_at.asc()))
    return list(result.scalars().all())


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)) -> Agent:
    if payload.hosting_mode == HostingMode.remote_mcp and not payload.endpoint_url:
        raise HTTPException(status_code=400, detail="endpoint_url is required for remote_mcp agents")
    existing = await db.execute(select(Agent).where(Agent.agent_key == payload.agent_key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="agent_key already exists")
    agent = Agent(**payload.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: UUID, payload: AgentUpdate, db: AsyncSession = Depends(get_db)
) -> Agent:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent
