"""Apply future resource grants when resources are created."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.permissions.registry import PERMISSION_BY_KEY
from app.authorization.services.audit_service import log_authorization_event
from app.authorization.services.authorization_service import invalidate_user_cache
from app.authorization.services.future_grant_service import conditions_match, list_future_grants
from app.models.authorization import (
    AuthGatheringAuthorizationSettings,
    AuthRolePermission,
    GrantSource,
    PermissionEffect,
    PermissionScope,
)


async def apply_future_grants_for_resource(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    resource_type: str,
    resource_id: UUID,
    context: dict | None = None,
    actor_user_id: UUID | None = None,
) -> int:
    """Apply matching future grants by adding resource-scoped role permissions."""
    settings = await db.get(AuthGatheringAuthorizationSettings, workspace_id)
    if settings is not None and not settings.future_grants_enabled:
        return 0

    ctx = context or {}
    applied = 0
    grants = await list_future_grants(db, workspace_id)
    for grant in grants:
        if grant.resource_type != resource_type:
            continue
        if grant.effect != PermissionEffect.allow:
            continue
        if not conditions_match(grant.conditions, ctx):
            continue
        definition = PERMISSION_BY_KEY.get(grant.permission_key)
        if not definition:
            continue
        perm = AuthRolePermission(
            role_id=grant.role_id,
            permission_key=grant.permission_key,
            effect=PermissionEffect.allow,
            scope=PermissionScope.resource,
            resource_type=resource_type,
            resource_ids=[str(resource_id)],
            grant_source=GrantSource.future_grant,
            created_by=actor_user_id,
        )
        db.add(perm)
        applied += 1
        await log_authorization_event(
            db,
            event_type="FUTURE_GRANT_APPLIED",
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            permission_key=grant.permission_key,
            resource_type=resource_type,
            resource_id=str(resource_id),
            new_value={"role_id": str(grant.role_id), "grant_id": str(grant.id)},
        )
    if applied:
        invalidate_user_cache()
    return applied
