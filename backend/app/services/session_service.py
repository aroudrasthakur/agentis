from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    Agent,
    Event,
    EventType,
    HostingMode,
    OrgTag,
    Participant,
    ParticipantKind,
    Session,
)
from app.services.tokens import (
    TokenError,
    intersect_capabilities,
    mint_agent_access_token,
    mint_session_invite,
)


DEFAULT_CAPABILITIES: dict[str, list[str]] = {
    "support_agent": ["lookup_order", "get_customer_summary", "propose_refund"],
    "triage_agent": [],
    "vendor_billing": ["check_billing_status", "process_refund"],
}


async def next_sequence(db: AsyncSession, session_id: UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Event.sequence), 0)).where(Event.session_id == session_id)
    )
    return int(result.scalar_one()) + 1


async def create_event(
    db: AsyncSession,
    *,
    session_id: UUID,
    participant_id: UUID,
    event_type: EventType,
    content: str,
    requires_approval: bool = False,
) -> Event:
    seq = await next_sequence(db, session_id)
    event = Event(
        session_id=session_id,
        participant_id=participant_id,
        type=event_type,
        content=content,
        requires_approval=requires_approval,
        sequence=seq,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


def kind_for_agent(agent: Agent) -> ParticipantKind:
    if agent.hosting_mode == HostingMode.hosted:
        return ParticipantKind.internal_agent
    return ParticipantKind.external_agent


async def attach_agent_to_session(
    db: AsyncSession,
    session: Session,
    agent: Agent,
    human: Participant | None = None,
    requested_capabilities: list[str] | None = None,
) -> tuple[Participant, Event]:
    try:
        granted = intersect_capabilities(agent.capabilities, requested_capabilities)
    except TokenError as exc:
        raise ValueError(str(exc)) from exc

    participant = Participant(
        session_id=session.id,
        agent_id=agent.id,
        name=agent.name,
        kind=kind_for_agent(agent),
        org_tag=agent.org_tag,
        hosting_mode=agent.hosting_mode,
        endpoint_url=agent.endpoint_url,
        agent_key=agent.agent_key,
        granted_capabilities=granted,
    )
    db.add(participant)
    await db.flush()

    token, claims = mint_agent_access_token(
        session_id=session.id,
        participant_id=participant.id,
        capabilities=granted,
    )
    participant.access_token = token
    participant.token_jti = claims.jti
    participant.token_expires_at = claims.exp
    participant.token_revoked_at = None

    actor = human
    if actor is None:
        result = await db.execute(
            select(Participant).where(
                Participant.session_id == session.id,
                Participant.kind == ParticipantKind.human,
            )
        )
        actor = result.scalar_one()

    caps_label = ", ".join(granted) if granted else "none"
    event = await create_event(
        db,
        session_id=session.id,
        participant_id=actor.id,
        event_type=EventType.agent_attached,
        content=(
            f"Attached {agent.name} ({agent.org_tag.value}, {agent.hosting_mode.value}) "
            f"with scoped capabilities: [{caps_label}]"
        ),
    )
    return participant, event


async def get_session_full(db: AsyncSession, session_id: UUID) -> Session | None:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(
            selectinload(Session.participants),
            selectinload(Session.events).selectinload(Event.participant),
        )
    )
    return result.scalar_one_or_none()


async def seed_default_agents(db: AsyncSession) -> None:
    settings = get_settings()
    defaults = [
        Agent(
            name="Support Agent",
            agent_key="support_agent",
            org_tag=OrgTag.internal,
            hosting_mode=HostingMode.hosted,
            endpoint_url=None,
            description="Internal hosted support agent for refunds and customer help.",
            capabilities=DEFAULT_CAPABILITIES["support_agent"],
            is_active=True,
        ),
        Agent(
            name="Triage Agent",
            agent_key="triage_agent",
            org_tag=OrgTag.internal,
            hosting_mode=HostingMode.hosted,
            endpoint_url=None,
            description="Lightweight hosted triage stub.",
            capabilities=DEFAULT_CAPABILITIES["triage_agent"],
            is_active=True,
        ),
        Agent(
            name="Vendor Billing",
            agent_key="vendor_billing",
            org_tag=OrgTag.external,
            hosting_mode=HostingMode.remote_mcp,
            endpoint_url=settings.vendor_mcp_url,
            description="External billing agent via Streamable HTTP MCP.",
            capabilities=DEFAULT_CAPABILITIES["vendor_billing"],
            is_active=True,
        ),
    ]
    for agent in defaults:
        existing = await db.execute(select(Agent).where(Agent.agent_key == agent.agent_key))
        row = existing.scalar_one_or_none()
        if row is None:
            db.add(agent)
        else:
            # Keep capabilities in sync for seeded agents if empty
            if not row.capabilities:
                row.capabilities = list(agent.capabilities)
            if agent.agent_key == "vendor_billing" and not row.endpoint_url:
                row.endpoint_url = settings.vendor_mcp_url
    await db.commit()


def issue_session_invite(session: Session) -> str:
    token, jti, exp = mint_session_invite(session_id=session.id)
    session.invite_jti = jti
    session.invite_expires_at = exp
    return token


def session_share_url(session_id: UUID, invite: str | None = None) -> str:
    settings = get_settings()
    base = f"{settings.frontend_origin.rstrip('/')}/session/{session_id}"
    if invite:
        return f"{base}?invite={invite}"
    return base
