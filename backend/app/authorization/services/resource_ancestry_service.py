"""Resource ancestry resolution for authorization."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, CustomAgentType, Gathering, GatheringAgent, Participant, Session


@dataclass
class ResourceAncestor:
    resource_type: str
    resource_id: UUID


@dataclass
class ResourceAncestry:
    target_type: str
    target_id: UUID
    ancestors: list[ResourceAncestor] = field(default_factory=list)
    workspace_id: UUID | None = None


async def resolve_resource_ancestry(
    db: AsyncSession,
    resource_type: str,
    resource_id: UUID,
) -> ResourceAncestry:
    ancestors: list[ResourceAncestor] = []
    workspace_id: UUID | None = None

    if resource_type == "gathering":
        workspace_id = resource_id
        ancestors.append(ResourceAncestor("gathering", resource_id))

    elif resource_type == "agent":
        agent = await db.get(Agent, resource_id)
        if agent:
            ga = await db.execute(
                select(GatheringAgent.gathering_id).where(GatheringAgent.agent_id == agent.id).limit(1)
            )
            gid = ga.scalar_one_or_none()
            if gid:
                workspace_id = gid
                ancestors.append(ResourceAncestor("gathering", gid))
            ancestors.append(ResourceAncestor("agent", agent.id))

    elif resource_type == "run":
        participant = await db.get(Participant, resource_id)
        if participant and participant.agent_id:
            sub = await resolve_resource_ancestry(db, "agent", participant.agent_id)
            ancestors.extend(sub.ancestors)
            workspace_id = sub.workspace_id
        elif participant:
            sess = await db.get(Session, participant.session_id)
            if sess and sess.gathering_id:
                workspace_id = sess.gathering_id
                ancestors.append(ResourceAncestor("gathering", sess.gathering_id))

    elif resource_type == "agent_type":
        row = await db.execute(
            select(CustomAgentType).where(CustomAgentType.family_id == resource_id).limit(1)
        )
        cat = row.scalar_one_or_none()
        if cat and cat.owner_user_id:
            ancestors.append(ResourceAncestor("agent_type", resource_id))

    elif resource_type == "account":
        pass

    return ResourceAncestry(
        target_type=resource_type,
        target_id=resource_id,
        ancestors=ancestors,
        workspace_id=workspace_id,
    )


async def agent_gathering_id(db: AsyncSession, agent_id: UUID) -> UUID | None:
    result = await db.execute(
        select(GatheringAgent.gathering_id).where(GatheringAgent.agent_id == agent_id).limit(1)
    )
    return result.scalar_one_or_none()


async def gathering_exists(db: AsyncSession, gathering_id: UUID) -> bool:
    return await db.get(Gathering, gathering_id) is not None
