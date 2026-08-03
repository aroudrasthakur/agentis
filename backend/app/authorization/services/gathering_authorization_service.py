"""Gathering centralized access mode checks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.constants.system_roles import (
    ACCOUNT_ADMIN_ROLE_ID,
    SECURITY_ADMIN_ROLE_ID,
)
from app.authorization.services.authorization_service import AuthorizationContext, can
from app.models import User
from app.models.authorization import AuthGatheringAuthorizationSettings, GatheringAccessMode


async def can_modify_gathering_access(
    db: AsyncSession,
    user: User,
    gathering_id: UUID,
) -> bool:
    settings = await db.get(AuthGatheringAuthorizationSettings, gathering_id)
    mode = settings.access_mode if settings else GatheringAccessMode.owner_managed
    ctx = AuthorizationContext(workspace_id=gathering_id)

    if await can(db, user, "agent.access.manage", ctx):
        return True
    if await can(db, user, "gathering.access.manage", ctx):
        return True

    if mode == GatheringAccessMode.centrally_managed:
        from sqlalchemy import select

        from app.models.authorization import AuthUserRoleAssignment

        rows = (
            await db.execute(
                select(AuthUserRoleAssignment.role_id).where(
                    AuthUserRoleAssignment.user_id == user.id
                )
            )
        ).scalars().all()
        role_ids = set(rows)
        if ACCOUNT_ADMIN_ROLE_ID in role_ids or SECURITY_ADMIN_ROLE_ID in role_ids:
            return True
        if settings and settings.access_manager_role_ids:
            if role_ids.intersection(set(settings.access_manager_role_ids)):
                return True
        return False

    return False
