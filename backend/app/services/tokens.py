"""Session-scoped JWTs for agent capabilities and session invites."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from app.config import get_settings

# Immediate revocation set — checked before every tool call (in addition to DB flag)
_revoked_jtis: set[str] = set()


class TokenError(Exception):
    pass


class CapabilityDenied(TokenError):
    pass


@dataclass
class AgentAccessClaims:
    session_id: UUID
    participant_id: UUID
    capabilities: list[str]
    jti: str
    exp: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _secret() -> str:
    return get_settings().jwt_secret


def mint_agent_access_token(
    *,
    session_id: UUID,
    participant_id: UUID,
    capabilities: list[str],
    ttl_seconds: int | None = None,
) -> tuple[str, AgentAccessClaims]:
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.agent_token_ttl_seconds
    jti = uuid.uuid4().hex
    exp = _now() + timedelta(seconds=ttl)
    payload = {
        "typ": "agent_access",
        "sid": str(session_id),
        "pid": str(participant_id),
        "caps": list(capabilities),
        "jti": jti,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, _secret(), algorithm="HS256")
    claims = AgentAccessClaims(
        session_id=session_id,
        participant_id=participant_id,
        capabilities=list(capabilities),
        jti=jti,
        exp=exp,
    )
    return token, claims


def mint_session_invite(
    *,
    session_id: UUID,
    ttl_seconds: int | None = None,
) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at)."""
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.session_invite_ttl_seconds
    jti = uuid.uuid4().hex
    exp = _now() + timedelta(seconds=ttl)
    payload = {
        "typ": "session_invite",
        "sid": str(session_id),
        "jti": jti,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, _secret(), algorithm="HS256")
    return token, jti, exp


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc


def verify_session_invite(token: str, session_id: UUID, expected_jti: str | None = None) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") != "session_invite":
        raise TokenError("Not a session invite token")
    if payload.get("sid") != str(session_id):
        raise TokenError("Invite does not match session")
    jti = payload.get("jti")
    if not jti:
        raise TokenError("Invite missing jti")
    if jti in _revoked_jtis:
        raise TokenError("Invite revoked")
    if expected_jti and jti != expected_jti:
        raise TokenError("Invite does not match session record")
    return payload


def parse_agent_access_token(token: str) -> AgentAccessClaims:
    payload = decode_token(token)
    if payload.get("typ") != "agent_access":
        raise TokenError("Not an agent access token")
    jti = payload.get("jti")
    if not jti:
        raise TokenError("Token missing jti")
    if jti in _revoked_jtis:
        raise TokenError("Token revoked")
    return AgentAccessClaims(
        session_id=UUID(payload["sid"]),
        participant_id=UUID(payload["pid"]),
        capabilities=list(payload.get("caps") or []),
        jti=jti,
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


def revoke_jti(jti: str | None) -> None:
    if jti:
        _revoked_jtis.add(jti)


def assert_capability(capabilities: list[str] | None, tool_name: str) -> None:
    caps = capabilities or []
    if tool_name not in caps:
        raise CapabilityDenied(f"Capability '{tool_name}' is not granted for this participant")


def intersect_capabilities(declared: list[str] | None, requested: list[str] | None) -> list[str]:
    """Grant = requested ∩ declared. If requested is None, grant full declared ceiling."""
    ceiling = list(declared or [])
    if requested is None:
        return ceiling
    ceiling_set = set(ceiling)
    unknown = [c for c in requested if c not in ceiling_set]
    if unknown:
        raise TokenError(f"Requested capabilities exceed agent ceiling: {unknown}")
    return [c for c in requested if c in ceiling_set]
