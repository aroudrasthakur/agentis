"""Delegation and scope narrowing checks."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.permissions.registry import PERMISSION_BY_KEY
from app.authorization.services.authorization_service import AuthorizationContext, authorize
from app.models import User


SCOPE_ORDER = {"resource": 0, "assigned": 1, "owned": 2, "workspace": 3, "system": 4}


@dataclass
class DelegationDecision:
    allowed: bool
    reason: str


def scope_is_narrower_or_equal(grantor: str, requested: str) -> bool:
    return SCOPE_ORDER.get(requested, -1) <= SCOPE_ORDER.get(grantor, 99)


async def can_delegate_grant(
    db: AsyncSession,
    actor_user_id: UUID,
    permission_key: str,
    requested_scope: str,
    requested_workspace_id: UUID | None,
    requested_resource_type: str | None,
    requested_resource_ids: list[UUID] | None,
) -> DelegationDecision:
    user = await db.get(User, actor_user_id)
    if not user:
        return DelegationDecision(False, "User not found")
    definition = PERMISSION_BY_KEY.get(permission_key)
    if not definition or not definition.delegable:
        return DelegationDecision(False, "Permission is not delegable")
    ctx = AuthorizationContext(
        workspace_id=requested_workspace_id,
        resource_type=requested_resource_type,
        resource_id=str(requested_resource_ids[0]) if requested_resource_ids else None,
    )
    decision = await authorize(db, user, "role.permissions.manage", ctx)
    if not decision.allowed:
        return DelegationDecision(False, "Missing role.permissions.manage")
    hold = await authorize(db, user, permission_key, ctx)
    if not hold.allowed:
        return DelegationDecision(False, "Grantor does not hold permission in requested context")
    if hold.scope and not scope_is_narrower_or_equal(hold.scope, requested_scope):
        return DelegationDecision(False, "Requested scope is broader than grantor scope")
    return DelegationDecision(True, "Delegation allowed")
