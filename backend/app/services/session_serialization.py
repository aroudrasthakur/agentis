from __future__ import annotations

from app.models import Event, Participant, Session
from app.schemas import EventOut, ParticipantOut, SessionOut
from app.services.session_service import session_share_url


def participant_out(participant: Participant) -> ParticipantOut:
    return ParticipantOut(
        id=participant.id,
        session_id=participant.session_id,
        agent_id=participant.agent_id,
        name=participant.name,
        kind=participant.kind,
        org_tag=participant.org_tag,
        hosting_mode=participant.hosting_mode,
        endpoint_url=participant.endpoint_url,
        agent_key=participant.agent_key,
        granted_capabilities=(
            list(participant.granted_capabilities)
            if participant.granted_capabilities is not None
            else None
        ),
        token_expires_at=participant.token_expires_at,
        token_revoked=participant.token_revoked_at is not None,
    )


def event_out(event: Event) -> EventOut:
    return EventOut(
        id=event.id,
        session_id=event.session_id,
        participant_id=event.participant_id,
        type=event.type,
        content=event.content,
        requires_approval=event.requires_approval,
        created_at=event.created_at,
        sequence=event.sequence,
        participant=participant_out(event.participant) if event.participant else None,
    )


def session_out(session: Session, invite: str | None = None) -> SessionOut:
    return SessionOut(
        id=session.id,
        title=session.title,
        status=session.status,
        nature=session.nature,
        gathering_id=session.gathering_id,
        active_participant_id=session.active_participant_id,
        created_at=session.created_at,
        share_url=session_share_url(session.id, invite),
        invite_expires_at=session.invite_expires_at,
        participants=[participant_out(participant) for participant in session.participants],
        events=[event_out(event) for event in sorted(session.events, key=lambda item: item.sequence)],
    )
