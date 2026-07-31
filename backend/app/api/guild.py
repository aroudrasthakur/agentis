from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Agent, AgentDownload, AgentSource, HostingMode, User
from app.schemas import AgentOut, LocalAgentCreate

router = APIRouter(prefix="/guild", tags=["guild"])


def _agent_out(agent: Agent, *, downloaded: bool = False) -> AgentOut:
    data = AgentOut.model_validate(agent)
    data.downloaded = downloaded
    return data


@router.get("/agents", response_model=list[AgentOut])
async def list_guild_agents(
    tab: str = Query(default="local", pattern="^(local|downloaded|directory)$"),
    q: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    """
    Guild inventory:
    - local: private agents owned by the current user
    - downloaded: agents the user downloaded from the directory
    - directory: publicly posted agents (optional search)
    """
    query_text = (q or "").strip().lower()

    if tab == "local":
        stmt = select(Agent).where(
            Agent.owner_user_id == user.id,
            Agent.source == AgentSource.local,
            Agent.is_active.is_(True),
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

    # directory
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
        is_active=True,
        source=AgentSource.local,
        is_public=False,
        owner_user_id=user.id,
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
