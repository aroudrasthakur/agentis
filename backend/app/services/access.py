"""Enforce participant access tokens before tool execution."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Participant, Session, SessionStatus
from app.services.tokens import (
    CapabilityDenied,
    TokenError,
    assert_capability,
    parse_agent_access_token,
    revoke_jti,
)


async def reload_participant(db: AsyncSession, participant_id: UUID) -> Participant:
    participant = await db.get(Participant, participant_id)
    if not participant:
        raise TokenError("Participant not found")
    await db.refresh(participant)
    return participant


async def assert_participant_can_call_tool(
    db: AsyncSession,
    participant_id: UUID,
    tool_name: str,
) -> Participant:
    """
    Reload participant from DB and verify token is valid, unrevoked, and grants tool_name.
    Raises TokenError / CapabilityDenied on failure.
    """
    participant = await reload_participant(db, participant_id)
    if participant.token_revoked_at is not None:
        raise TokenError("Participant access token has been revoked")
    if not participant.access_token:
        raise TokenError("Participant has no access token")

    session = await db.get(Session, participant.session_id)
    if not session:
        raise TokenError("Session not found")
    if session.status == SessionStatus.completed:
        raise TokenError("Session is completed; access ended")

    claims = parse_agent_access_token(participant.access_token)
    if claims.participant_id != participant.id or claims.session_id != participant.session_id:
        raise TokenError("Token claims do not match participant")
    if participant.token_jti and claims.jti != participant.token_jti:
        raise TokenError("Token jti mismatch")

    # Prefer DB granted_capabilities (source of truth after attach) intersected with token
    granted = list(participant.granted_capabilities or claims.capabilities)
    assert_capability(granted, tool_name)
    return participant


def revoke_participant_token(participant: Participant) -> None:
    participant.token_revoked_at = datetime.now(timezone.utc)
    revoke_jti(participant.token_jti)
    # Keep access_token for audit, but it will fail checks via revoked_at + jti set
