from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent_types.services import gating
from app.authorization.permissions.registry import P
from app.authorization.services.authorization_service import AuthorizationContext, require_permission
from app.db import get_db
from app.deps import get_current_user
from app.models import (
    Agent,
    Gathering,
    GatheringAgent,
    GatheringMember,
    GatheringMemberRole,
    OrgTag,
    Participant,
    ParticipantKind,
    Session,
    SessionStatus,
    User,
)
from app.schemas import (
    AgentOut,
    GatheringAddAgentsRequest,
    GatheringCreate,
    GatheringDetailOut,
    GatheringInviteRequest,
    GatheringMemberOut,
    GatheringOut,
    GatheringProvisionRequest,
    GatheringProvisionResponse,
    GatheringProvisionResult,
    GatheringSessionCreate,
    GatheringSessionSummary,
    SessionCreateResponse,
)
from app.services.auth import get_user_by_email
from app.services.session_service import (
    attach_agent_to_session,
    issue_session_invite,
    session_share_url,
)

router = APIRouter(prefix="/gatherings", tags=["gatherings"])


async def _require_member(
    db: AsyncSession, gathering_id: UUID, user: User
) -> tuple[Gathering, GatheringMember]:
    gathering = await db.get(Gathering, gathering_id)
    if not gathering:
        raise HTTPException(status_code=404, detail="Gathering not found")
    result = await db.execute(
        select(GatheringMember).where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.user_id == user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this gathering")
    return gathering, membership


async def _counts(db: AsyncSession, gathering_id: UUID) -> tuple[int, int, int]:
    members = await db.scalar(
        select(func.count())
        .select_from(GatheringMember)
        .where(GatheringMember.gathering_id == gathering_id)
    )
    agents = await db.scalar(
        select(func.count())
        .select_from(GatheringAgent)
        .where(GatheringAgent.gathering_id == gathering_id)
    )
    sessions = await db.scalar(
        select(func.count()).select_from(Session).where(Session.gathering_id == gathering_id)
    )
    return int(members or 0), int(agents or 0), int(sessions or 0)


def _gathering_out(
    gathering: Gathering,
    *,
    role: GatheringMemberRole | None,
    member_count: int,
    agent_count: int,
    session_count: int,
) -> GatheringOut:
    return GatheringOut(
        id=gathering.id,
        name=gathering.name,
        description=gathering.description,
        owner_id=gathering.owner_id,
        created_at=gathering.created_at,
        member_count=member_count,
        agent_count=agent_count,
        session_count=session_count,
        role=role,
    )


@router.get("", response_model=list[GatheringOut])
async def list_gatherings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GatheringOut]:
    result = await db.execute(
        select(Gathering, GatheringMember.role)
        .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
        .where(GatheringMember.user_id == user.id)
        .order_by(Gathering.created_at.desc())
    )
    out: list[GatheringOut] = []
    for gathering, role in result.all():
        mc, ac, sc = await _counts(db, gathering.id)
        out.append(
            _gathering_out(
                gathering, role=role, member_count=mc, agent_count=ac, session_count=sc
            )
        )
    return out


@router.post("", response_model=GatheringOut, status_code=status.HTTP_201_CREATED)
async def create_gathering(
    payload: GatheringCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GatheringOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    gathering = Gathering(name=name, description=payload.description, owner_id=user.id)
    db.add(gathering)
    await db.flush()
    db.add(
        GatheringMember(
            gathering_id=gathering.id,
            user_id=user.id,
            invited_email=user.email,
            role=GatheringMemberRole.owner,
        )
    )
    await db.commit()
    await db.refresh(gathering)
    return _gathering_out(
        gathering,
        role=GatheringMemberRole.owner,
        member_count=1,
        agent_count=0,
        session_count=0,
    )


@router.post(
    "/provision",
    response_model=GatheringProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_gathering(
    payload: GatheringProvisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GatheringProvisionResponse:
    """Create a gathering together with its access roles, members and agents."""
    from app.authorization.services.authorization_service import invalidate_user_cache
    from app.authorization.services.bootstrap import assign_role
    from app.authorization.services.future_grant_apply import apply_future_grants_for_resource
    from app.authorization.services.rbac_catalog_bootstrap import ensure_gathering_access_roles
    from app.models.authorization import (
        AuthGatheringAuthorizationSettings,
        GatheringAccessMode,
    )

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    gathering = Gathering(name=name, description=payload.description, owner_id=user.id)
    db.add(gathering)
    await db.flush()
    db.add(
        GatheringMember(
            gathering_id=gathering.id,
            user_id=user.id,
            invited_email=user.email,
            role=GatheringMemberRole.owner,
        )
    )

    role_map = await ensure_gathering_access_roles(db, gathering)
    await db.flush()

    settings = await db.get(AuthGatheringAuthorizationSettings, gathering.id)
    if settings is None:
        settings = AuthGatheringAuthorizationSettings(gathering_id=gathering.id)
        db.add(settings)
    settings.access_mode = GatheringAccessMode(payload.access_mode)
    settings.future_grants_enabled = payload.future_grants_enabled

    await assign_role(
        db,
        user_id=user.id,
        role_id=role_map["owner"],
        workspace_id=gathering.id,
        assigned_by=user.id,
    )

    invited: list[str] = []
    skipped: list[str] = []
    seen = {user.email.lower()}
    for raw_email in payload.invite_emails:
        email = raw_email.lower().strip()
        if not email or email in seen:
            if email:
                skipped.append(email)
            continue
        seen.add(email)
        invited_user = await get_user_by_email(db, email)
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id=invited_user.id if invited_user else None,
                invited_email=email,
                role=GatheringMemberRole.member,
            )
        )
        invited.append(email)

    attached: list[UUID] = []
    for agent_id in payload.agent_ids:
        agent = await db.get(Agent, agent_id)
        if not agent or not agent.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid agent: {agent_id}")
        blocked = gating.deployment_block_reason(agent)
        if blocked:
            raise HTTPException(status_code=400, detail=blocked)
        if agent_id in attached:
            continue
        db.add(GatheringAgent(gathering_id=gathering.id, agent_id=agent_id))
        await apply_future_grants_for_resource(
            db,
            workspace_id=gathering.id,
            resource_type="agent",
            resource_id=agent_id,
            context={"resource_status": "active"},
            actor_user_id=user.id,
        )
        attached.append(agent_id)

    await db.commit()
    await db.refresh(gathering)
    invalidate_user_cache(user.id)

    return GatheringProvisionResponse(
        gathering=_gathering_out(
            gathering,
            role=GatheringMemberRole.owner,
            member_count=1 + len(invited),
            agent_count=len(attached),
            session_count=0,
        ),
        provisioning=GatheringProvisionResult(
            invited_emails=invited,
            skipped_emails=skipped,
            attached_agent_ids=attached,
            access_role_slugs=sorted(role_map.keys()),
        ),
    )


@router.get("/{gathering_id}", response_model=GatheringDetailOut)
async def get_gathering(
    gathering_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GatheringDetailOut:
    gathering, membership = await _require_member(db, gathering_id, user)

    members_result = await db.execute(
        select(GatheringMember)
        .where(GatheringMember.gathering_id == gathering_id)
        .options(selectinload(GatheringMember.user))
        .order_by(GatheringMember.created_at.asc())
    )
    members = []
    for m in members_result.scalars().all():
        members.append(
            GatheringMemberOut(
                id=m.id,
                gathering_id=m.gathering_id,
                user_id=m.user_id,
                invited_email=m.invited_email,
                role=m.role,
                display_name=m.user.display_name if m.user else None,
                email=m.user.email if m.user else m.invited_email,
                bio=m.user.bio if m.user else None,
                organization=m.user.organization if m.user else None,
                title=m.user.title if m.user else None,
                created_at=m.created_at,
            )
        )

    agents_result = await db.execute(
        select(Agent)
        .join(GatheringAgent, GatheringAgent.agent_id == Agent.id)
        .where(GatheringAgent.gathering_id == gathering_id)
        .order_by(Agent.name.asc())
    )
    agents = [AgentOut.from_agent(a) for a in agents_result.scalars().all()]

    sessions_result = await db.execute(
        select(Session)
        .where(Session.gathering_id == gathering_id)
        .order_by(Session.created_at.desc())
    )
    sessions = [
        GatheringSessionSummary(
            id=s.id,
            title=s.title,
            status=s.status,
            nature=s.nature,
            created_at=s.created_at,
        )
        for s in sessions_result.scalars().all()
    ]

    mc, ac, sc = await _counts(db, gathering_id)
    base = _gathering_out(
        gathering, role=membership.role, member_count=mc, agent_count=ac, session_count=sc
    )
    return GatheringDetailOut(
        **base.model_dump(), members=members, agents=agents, sessions=sessions
    )


@router.post("/{gathering_id}/invite", response_model=GatheringMemberOut)
async def invite_to_gathering(
    gathering_id: UUID,
    payload: GatheringInviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GatheringMemberOut:
    _, membership = await _require_member(db, gathering_id, user)
    await require_permission(
        db,
        user,
        P.WORKSPACE_MEMBERS_MANAGE,
        AuthorizationContext(workspace_id=gathering_id),
    )
    if membership.role != GatheringMemberRole.owner:
        raise HTTPException(status_code=403, detail="Only owners can invite")

    email = payload.email.lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    dup = await db.execute(
        select(GatheringMember).where(GatheringMember.gathering_id == gathering_id)
    )
    for m in dup.scalars().all():
        if m.invited_email and m.invited_email.lower() == email:
            raise HTTPException(status_code=409, detail="Already invited")
        if m.user_id:
            u = await db.get(User, m.user_id)
            if u and u.email.lower() == email:
                raise HTTPException(status_code=409, detail="Already a member")

    invited_user = await get_user_by_email(db, email)
    member = GatheringMember(
        gathering_id=gathering_id,
        user_id=invited_user.id if invited_user else None,
        invited_email=email,
        role=GatheringMemberRole.member,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return GatheringMemberOut(
        id=member.id,
        gathering_id=member.gathering_id,
        user_id=member.user_id,
        invited_email=member.invited_email,
        role=member.role,
        display_name=invited_user.display_name if invited_user else None,
        email=email,
        bio=invited_user.bio if invited_user else None,
        organization=invited_user.organization if invited_user else None,
        title=invited_user.title if invited_user else None,
        created_at=member.created_at,
    )


@router.post("/{gathering_id}/agents", response_model=list[AgentOut])
async def add_agents_to_gathering(
    gathering_id: UUID,
    payload: GatheringAddAgentsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    await _require_member(db, gathering_id, user)
    if not payload.agent_ids:
        raise HTTPException(status_code=400, detail="agent_ids required")

    for agent_id in payload.agent_ids:
        agent = await db.get(Agent, agent_id)
        if not agent or not agent.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid agent: {agent_id}")
        blocked = gating.deployment_block_reason(agent)
        if blocked:
            raise HTTPException(status_code=400, detail=blocked)
        exists = await db.execute(
            select(GatheringAgent).where(
                GatheringAgent.gathering_id == gathering_id,
                GatheringAgent.agent_id == agent_id,
            )
        )
        if not exists.scalar_one_or_none():
            db.add(GatheringAgent(gathering_id=gathering_id, agent_id=agent_id))
            from app.authorization.services.future_grant_apply import apply_future_grants_for_resource

            await apply_future_grants_for_resource(
                db,
                workspace_id=gathering_id,
                resource_type="agent",
                resource_id=agent_id,
                context={"resource_status": "active" if agent.is_active else "inactive"},
                actor_user_id=user.id,
            )

    await db.commit()
    agents_result = await db.execute(
        select(Agent)
        .join(GatheringAgent, GatheringAgent.agent_id == Agent.id)
        .where(GatheringAgent.gathering_id == gathering_id)
        .order_by(Agent.name.asc())
    )
    return [AgentOut.from_agent(a) for a in agents_result.scalars().all()]


@router.post(
    "/{gathering_id}/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gathering_session(
    gathering_id: UUID,
    payload: GatheringSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionCreateResponse:
    """Create a session inside a gathering. `nature` is immutable after this call."""
    await _require_member(db, gathering_id, user)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    explicit_agent_ids = bool(payload.agent_ids)
    if payload.agent_ids:
        for agent_id in payload.agent_ids:
            link = await db.execute(
                select(GatheringAgent).where(
                    GatheringAgent.gathering_id == gathering_id,
                    GatheringAgent.agent_id == agent_id,
                )
            )
            if not link.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Agent {agent_id} is not added to this gathering",
                )
        agent_ids = list(payload.agent_ids)
    else:
        result = await db.execute(
            select(GatheringAgent.agent_id).where(GatheringAgent.gathering_id == gathering_id)
        )
        agent_ids = list(result.scalars().all())

    session = Session(
        title=title,
        status=SessionStatus.active,
        nature=payload.nature,
        gathering_id=gathering_id,
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
            if explicit_agent_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid or inactive agent_id: {agent_id}",
                )
            continue
        blocked = gating.deployment_block_reason(agent)
        if blocked:
            if explicit_agent_ids:
                raise HTTPException(status_code=400, detail=blocked)
            continue
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
        gathering_id=session.gathering_id,
    )


@router.post(
    "/{gathering_id}/sessions/{session_id}/open",
    response_model=SessionCreateResponse,
)
async def open_gathering_session(
    gathering_id: UUID,
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionCreateResponse:
    await _require_member(db, gathering_id, user)
    session = await db.get(Session, session_id)
    if not session or session.gathering_id != gathering_id:
        raise HTTPException(status_code=404, detail="Session not found in this gathering")
    invite = issue_session_invite(session)
    await db.commit()
    return SessionCreateResponse(
        id=session.id,
        share_url=session_share_url(session.id, invite),
        invite=invite,
        title=session.title,
        status=session.status,
        nature=session.nature,
        gathering_id=session.gathering_id,
    )
