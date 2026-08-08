"""Future resource grants for Gatherings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.services.audit_service import log_authorization_event
from app.authorization.services.authorization_service import invalidate_user_cache
from app.models.authorization import AuthFutureResourceGrant, PermissionEffect


ALLOWED_CONDITION_KEYS = frozenset(
    {"agent_type_id", "agent_type_category", "deployment_environment", "risk_level", "resource_status"}
)


async def list_future_grants(db: AsyncSession, workspace_id: UUID) -> list[AuthFutureResourceGrant]:
    rows = await db.execute(
        select(AuthFutureResourceGrant).where(AuthFutureResourceGrant.workspace_id == workspace_id)
    )
    return list(rows.scalars().all())


async def create_future_grant(
    db: AsyncSession,
    *,
    actor_user_id: UUID,
    role_id: UUID,
    workspace_id: UUID,
    resource_type: str,
    permission_key: str,
    conditions: dict[str, Any] | None,
    actor_role_id: UUID | None = None,
) -> AuthFutureResourceGrant:
    if conditions:
        for key in conditions:
            if key not in ALLOWED_CONDITION_KEYS:
                raise ValueError(f"Unsupported condition field: {key}")
    row = AuthFutureResourceGrant(
        role_id=role_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        permission_key=permission_key,
        effect=PermissionEffect.allow,
        conditions=conditions,
        created_by_user_id=actor_user_id,
        created_by_role_id=actor_role_id,
    )
    db.add(row)
    await log_authorization_event(
        db,
        event_type="FUTURE_GRANT_CREATED",
        actor_user_id=actor_user_id,
        workspace_id=workspace_id,
        permission_key=permission_key,
        new_value={"resource_type": resource_type, "role_id": str(role_id)},
    )
    invalidate_user_cache()
    return row


def conditions_match(
    conditions: Mapping[str, Any] | None, context: Mapping[str, Any]
) -> bool:
    if not conditions:
        return True
    for key, expected in conditions.items():
        if context.get(key) != expected:
            return False
    return True
