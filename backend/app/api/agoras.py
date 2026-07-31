from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import get_current_user
from app.models import (
    Agent,
    Agora,
    AgoraAgent,
    AgoraMember,
    AgoraMemberRole,
    OrgTag,
    Participant,
    ParticipantKind,
    Session,
    SessionStatus,
    User,
)
from app.schemas import (
    AgoraAddAgentsRequest,
    AgoraCreate,
    AgoraDetailOut,
    AgoraInviteRequest,
    AgoraMemberOut,
    AgoraOut,
    AgoraSessionCreate,
    AgoraSessionSummary,
    AgentOut,
    SessionCreateResponse,
)
from app.services.auth import get_user_by_email
from app.services.session_service import (
    attach_agent_to_session,
    issue_session_invite,
    session_share_url,
)

router = APIRouter(prefix="/agoras", tags=["agoras"])


async def _require_agora_member(
    db: AsyncSession, agora_id: UUID, user: User
) -> tuple[Agora, AgoraMember]:
    agora = await db.get(Agora, agora_id)
    if not agora:
        raise HTTPException(status_code=404, detail="Agora not found")
    result = await db.execute(
        select(AgoraMember).where(
            AgoraMember.agora_id == agora_id, AgoraMember.user_id == user.id
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this agora")
    return agora, membership


async def _counts(db: AsyncSession, agora_id: UUID) -> tuple[int, int, int]:
    members = await db.scalar(
        select(func.count()).select_from(AgoraMember).where(AgoraMember.agora_id == agora_id)
    )
    agents = await db.scalar(
        select(func.count()).select_from(AgoraAgent).where(AgoraAgent.agora_id == agora_id)
    )
    sessions = await db.scalar(
        select(func.count()).select_from(Session).where(Session.agora_id == agora_id)
    )
    return int(members or 0), int(agents or 0), int(sessions or 0)


def _agora_out(
    agora: Agora, *, role: AgoraMemberRole | None, member_count: int, agent_count: int, session_count: int
) -> AgoraOut:
    return AgoraOut(
        id=agora.id,
        name=agora.name,
        description=agora.description,
        owner_id=agora.owner_id,
        created_at=agora.created_at,
        member_count=member_count,
        agent_count=agent_count,
        session_count=session_count,
        role=role,
    )


@router.get("", response_model=list[AgoraOut])
async def list_agoras(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgoraOut]:
    result = await db.execute(
        select(Agora, AgoraMember.role)
        .join(AgoraMember, AgoraMember.agora_id == Agora.id)
        .where(AgoraMember.user_id == user.id)
        .order_by(Agora.created_at.desc())
    )
    rows = result.all()
    out: list[AgoraOut] = []
    for agora, role in rows:
        mc, ac, sc = await _counts(db, agora.id)
        out.append(
            _agora_out(agora, role=role, member_count=mc, agent_count=ac, session_count=sc)
        )
    return out


@router.post("", response_model=AgoraOut, status_code=status.HTTP_201_CREATED)
async def create_agora(
    payload: AgoraCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgoraOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    agora = Agora(name=name, description=payload.description, owner_id=user.id)
    db.add(agora)
    await db.flush()
    db.add(
        AgoraMember(
            agora_id=agora.id,
            user_id=user.id,
            invited_email=user.email,
            role=AgoraMemberRole.owner,
        )
    )
    await db.commit()
    await db.refresh(agora)
    return _agora_out(
        agora, role=AgoraMemberRole.owner, member_count=1, agent_count=0, session_count=0
    )


@router.get("/{agora_id}", response_model=AgoraDetailOut)
async def get_agora(
    agora_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgoraDetailOut:
    agora, membership = await _require_agora_member(db, agora_id, user)

    members_result = await db.execute(
        select(AgoraMember)
        .where(AgoraMember.agora_id == agora_id)
        .options(selectinload(AgoraMember.user))
        .order_by(AgoraMember.created_at.asc())
    )
    members = []
    for m in members_result.scalars().all():
        members.append(
            AgoraMemberOut(
                id=m.id,
                agora_id=m.agora_id,
                user_id=m.user_id,
                invited_email=m.invited_email,
                role=m.role,
                display_name=m.user.display_name if m.user else None,
                email=m.user.email if m.user else m.invited_email,
                created_at=m.created_at,
            )
        )

    agents_result = await db.execute(
        select(Agent)
        .join(AgoraAgent, AgoraAgent.agent_id == Agent.id)
        .where(AgoraAgent.agora_id == agora_id)
        .order_by(Agent.name.asc())
    )
    agents = [AgentOut.model_validate(a) for a in agents_result.scalars().all()]

    sessions_result = await db.execute(
        select(Session).where(Session.agora_id == agora_id).order_by(Session.created_at.desc())
    )
    sessions = [
        AgoraSessionSummary(
            id=s.id,
            title=s.title,
            status=s.status,
            nature=s.nature,
            created_at=s.created_at,
            invite=None,
            share_url=None,
        )
        for s in sessions_result.scalars().all()
    ]

    mc, ac, sc = await _counts(db, agora_id)
    base = _agora_out(
        agora, role=membership.role, member_count=mc, agent_count=ac, session_count=sc
    )
    return AgoraDetailOut(**base.model_dump(), members=members, agents=agents, sessions=sessions)


@router.post("/{agora_id}/invite", response_model=AgoraMemberOut)
async def invite_to_agora(
    agora_id: UUID,
    payload: AgoraInviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgoraMemberOut:
    _, membership = await _require_agora_member(db, agora_id, user)
    if membership.role != AgoraMemberRole.owner:
        raise HTTPException(status_code=403, detail="Only owners can invite")

    email = payload.email.lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    dup = await db.execute(select(AgoraMember).where(AgoraMember.agora_id == agora_id))
    for m in dup.scalars().all():
        if m.invited_email and m.invited_email.lower() == email:
            raise HTTPException(status_code=409, detail="Already invited")
        if m.user_id:
            u = await db.get(User, m.user_id)
            if u and u.email.lower() == email:
                raise HTTPException(status_code=409, detail="Already a member")

    invited_user = await get_user_by_email(db, email)
    member = AgoraMember(
        agora_id=agora_id,
        user_id=invited_user.id if invited_user else None,
        invited_email=email,
        role=AgoraMemberRole.member,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return AgoraMemberOut(
        id=member.id,
        agora_id=member.agora_id,
        user_id=member.user_id,
        invited_email=member.invited_email,
        role=member.role,
        display_name=invited_user.display_name if invited_user else None,
        email=email,
        created_at=member.created_at,
    )


@router.post("/{agora_id}/agents", response_model=list[AgentOut])
async def add_agents_to_agora(
    agora_id: UUID,
    payload: AgoraAddAgentsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    await _require_agora_member(db, agora_id, user)
    if not payload.agent_ids:
        raise HTTPException(status_code=400, detail="agent_ids required")

    for agent_id in payload.agent_ids:
        agent = await db.get(Agent, agent_id)
        if not agent or not agent.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid agent: {agent_id}")
        exists = await db.execute(
            select(AgoraAgent).where(
                AgoraAgent.agora_id == agora_id, AgoraAgent.agent_id == agent_id
            )
        )
        if exists.scalar_one_or_none():
            continue
        db.add(AgoraAgent(agora_id=agora_id, agent_id=agent_id))

    await db.commit()
    agents_result = await db.execute(
        select(Agent)
        .join(AgoraAgent, AgoraAgent.agent_id == Agent.id)
        .where(AgoraAgent.agora_id == agora_id)
        .order_by(Agent.name.asc())
    )
    return [AgentOut.model_validate(a) for a in agents_result.scalars().all()]


@router.post(
    "/{agora_id}/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agora_session(
    agora_id: UUID,
    payload: AgoraSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionCreateResponse:
    """Create a session inside an agora. `nature` is immutable after this call."""
    await _require_agora_member(db, agora_id, user)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    # Prefer agents already on the agora; allow explicit ids that are on agora
    if payload.agent_ids:
        for agent_id in payload.agent_ids:
            link = await db.execute(
                select(AgoraAgent).where(
                    AgoraAgent.agora_id == agora_id, AgoraAgent.agent_id == agent_id
                )
            )
            if not link.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Agent {agent_id} is not added to this agora",
                )
        agent_ids = list(payload.agent_ids)
    else:
        result = await db.execute(
            select(AgoraAgent.agent_id).where(AgoraAgent.agora_id == agora_id)
        )
        agent_ids = list(result.scalars().all())

    session = Session(
        title=title,
        status=SessionStatus.active,
        nature=payload.nature,
        agora_id=agora_id,
    )
    db.add(session)
    await db.flush()
    invite = issue_session_invite(session)

    human = Participant(
        session_id=session.id,
        agent_id=None,
        name=user.display_name,
        kind=ParticipantKind.human,
        org_tag=OrgTag.internal,
        hosting_mode=None,
        endpoint_url=None,
        agent_key=None,
    )
    db.add(human)
    await db.flush()

    for agent_id in agent_ids:
        agent = await db.get(Agent, agent_id)
        if not agent or not agent.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid agent_id: {agent_id}")
        try:
            await attach_agent_to_session(db, session, agent, human=human)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    return SessionCreateResponse(
        id=session.id,
        share_url=session_share_url(session.id, invite),
        invite=invite,
        title=session.title,
        status=session.status,
        nature=session.nature,
        agora_id=session.agora_id,
    )


@router.post("/{agora_id}/sessions/{session_id}/open", response_model=SessionCreateResponse)
async def open_agora_session(
    agora_id: UUID,
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionCreateResponse:
    """Re-issue a session invite for an agora member (nature remains unchanged)."""
    await _require_agora_member(db, agora_id, user)
    session = await db.get(Session, session_id)
    if not session or session.agora_id != agora_id:
        raise HTTPException(status_code=404, detail="Session not found in this agora")
    invite = issue_session_invite(session)
    await db.commit()
    return SessionCreateResponse(
        id=session.id,
        share_url=session_share_url(session.id, invite),
        invite=invite,
        title=session.title,
        status=session.status,
        nature=session.nature,
        agora_id=session.agora_id,
    )
