from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import (
    Agent,
    Event,
    EventType,
    OrgTag,
    Participant,
    ParticipantKind,
    Session,
    SessionStatus,
)
from app.schemas import (
    AttachAgentsRequest,
    EventOut,
    ParticipantOut,
    SessionCreate,
    SessionCreateResponse,
    SessionOut,
)
from app.services import orchestration
from app.services.access import revoke_participant_token
from app.services.session_service import (
    attach_agent_to_session,
    create_event,
    get_session_full,
    issue_session_invite,
    session_share_url,
)
from app.services.tokens import TokenError, verify_session_invite
from app.ws.manager import manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _participant_out(p: Participant) -> ParticipantOut:
    return ParticipantOut(
        id=p.id,
        session_id=p.session_id,
        agent_id=p.agent_id,
        name=p.name,
        kind=p.kind,
        org_tag=p.org_tag,
        hosting_mode=p.hosting_mode,
        endpoint_url=p.endpoint_url,
        agent_key=p.agent_key,
        granted_capabilities=list(p.granted_capabilities) if p.granted_capabilities is not None else None,
        token_expires_at=p.token_expires_at,
        token_revoked=p.token_revoked_at is not None,
    )


def _serialize_session(session: Session, invite: str | None = None) -> SessionOut:
    events = []
    for ev in sorted(session.events, key=lambda e: e.sequence):
        events.append(
            EventOut(
                id=ev.id,
                session_id=ev.session_id,
                participant_id=ev.participant_id,
                type=ev.type,
                content=ev.content,
                requires_approval=ev.requires_approval,
                created_at=ev.created_at,
                sequence=ev.sequence,
                participant=_participant_out(ev.participant) if ev.participant else None,
            )
        )
    return SessionOut(
        id=session.id,
        title=session.title,
        status=session.status,
        active_participant_id=session.active_participant_id,
        created_at=session.created_at,
        share_url=session_share_url(session.id, invite),
        invite_expires_at=session.invite_expires_at,
        participants=[_participant_out(p) for p in session.participants],
        events=events,
    )


def _require_invite(session: Session, invite: str | None) -> None:
    if not invite:
        raise HTTPException(
            status_code=401,
            detail="Missing session invite token. Use the signed share link.",
        )
    try:
        verify_session_invite(invite, session.id, expected_jti=session.invite_jti)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate, db: AsyncSession = Depends(get_db)
) -> SessionCreateResponse:
    session = Session(title=payload.title, status=SessionStatus.active)
    db.add(session)
    await db.flush()

    invite = issue_session_invite(session)

    human = Participant(
        session_id=session.id,
        agent_id=None,
        name="Human",
        kind=ParticipantKind.human,
        org_tag=OrgTag.internal,
        hosting_mode=None,
        endpoint_url=None,
        agent_key=None,
    )
    db.add(human)
    await db.flush()

    for agent_id in payload.agent_ids:
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
    )


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: UUID,
    invite: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await get_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_invite(session, invite)
    return _serialize_session(session, invite=invite)


@router.post("/{session_id}/agents", response_model=SessionOut)
async def attach_agents(
    session_id: UUID,
    payload: AttachAgentsRequest,
    invite: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await get_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_invite(session, invite)

    active_agent_ids = {
        p.agent_id for p in session.participants if p.agent_id and p.token_revoked_at is None
    }
    human = next(p for p in session.participants if p.kind == ParticipantKind.human)
    caps_map = payload.capabilities or {}

    broadcast_events: list[Event] = []
    for agent_id in payload.agent_ids:
        if agent_id in active_agent_ids:
            continue
        agent = await db.get(Agent, agent_id)
        if not agent or not agent.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid agent_id: {agent_id}")
        requested = caps_map.get(str(agent_id))
        try:
            _, event = await attach_agent_to_session(
                db, session, agent, human=human, requested_capabilities=requested
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        broadcast_events.append(event)
        active_agent_ids.add(agent_id)

    await db.commit()
    db.expire_all()
    session = await get_session_full(db, session_id)
    assert session is not None

    for event in broadcast_events:
        result = await db.execute(
            select(Event).where(Event.id == event.id).options(selectinload(Event.participant))
        )
        event = result.scalar_one()
        payload_out = EventOut(
            id=event.id,
            session_id=event.session_id,
            participant_id=event.participant_id,
            type=event.type,
            content=event.content,
            requires_approval=event.requires_approval,
            created_at=event.created_at,
            sequence=event.sequence,
            participant=_participant_out(event.participant),
        )
        await manager.broadcast(
            session_id,
            {"type": "event", "event": payload_out.model_dump(mode="json")},
        )
    await manager.broadcast(
        session_id,
        {
            "type": "session_updated",
            "session": _serialize_session(session, invite=invite).model_dump(mode="json"),
        },
    )
    return _serialize_session(session, invite=invite)


@router.delete("/{session_id}/agents/{participant_id}", response_model=SessionOut)
async def detach_agent(
    session_id: UUID,
    participant_id: UUID,
    invite: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await get_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_invite(session, invite)

    participant = next((p for p in session.participants if p.id == participant_id), None)
    if not participant or participant.kind == ParticipantKind.human:
        raise HTTPException(status_code=400, detail="Cannot detach this participant")

    if participant.token_revoked_at is not None:
        raise HTTPException(status_code=400, detail="Participant already detached/revoked")

    human = next(p for p in session.participants if p.kind == ParticipantKind.human)
    name = participant.name

    # Kill access immediately (in-memory jti + DB flag). Keep the row for audit attribution.
    revoke_participant_token(participant)

    if session.active_participant_id == participant.id:
        session.active_participant_id = None

    event = await create_event(
        db,
        session_id=session.id,
        participant_id=human.id,
        event_type=EventType.agent_detached,
        content=f"Detached {name} — access token revoked immediately",
    )
    await db.commit()
    db.expire_all()

    session = await get_session_full(db, session_id)
    assert session is not None

    result = await db.execute(
        select(Event).where(Event.id == event.id).options(selectinload(Event.participant))
    )
    event = result.scalar_one()
    payload_out = EventOut(
        id=event.id,
        session_id=event.session_id,
        participant_id=event.participant_id,
        type=event.type,
        content=event.content,
        requires_approval=event.requires_approval,
        created_at=event.created_at,
        sequence=event.sequence,
        participant=_participant_out(event.participant),
    )
    await manager.broadcast(session_id, {"type": "event", "event": payload_out.model_dump(mode="json")})
    await manager.broadcast(
        session_id,
        {
            "type": "session_updated",
            "session": _serialize_session(session, invite=invite).model_dump(mode="json"),
        },
    )
    return _serialize_session(session, invite=invite)


@router.post("/{session_id}/start", response_model=SessionOut)
async def start_session(
    session_id: UUID,
    invite: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await get_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_invite(session, invite)
    try:
        await orchestration.start_session(db, session_id, invite=invite)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session = await get_session_full(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session, invite=invite)
