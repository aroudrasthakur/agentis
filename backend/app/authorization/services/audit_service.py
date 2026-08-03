"""Authorization audit logging."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authorization import AuthAuthorizationAuditEvent


async def log_authorization_event(
    db: AsyncSession,
    *,
    event_type: str,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    role_id: UUID | None = None,
    permission_key: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    previous_value: Any | None = None,
    new_value: Any | None = None,
    reason: str | None = None,
) -> None:
    db.add(
        AuthAuthorizationAuditEvent(
            event_type=event_type,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            workspace_id=workspace_id,
            role_id=role_id,
            permission_key=permission_key,
            resource_type=resource_type,
            resource_id=resource_id,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
        )
    )
