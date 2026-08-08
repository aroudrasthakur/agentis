"""Role-assignment persistence shared by bootstrap and migration services."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.services.authorization_service import invalidate_user_cache
from app.models.authorization import AuthUserRoleAssignment


async def assign_role(
    db: AsyncSession,
    *,
    user_id: UUID,
    role_id: UUID,
    workspace_id: UUID | None = None,
    assigned_by: UUID | None = None,
) -> AuthUserRoleAssignment:
    existing = await db.execute(
        select(AuthUserRoleAssignment).where(
            AuthUserRoleAssignment.user_id == user_id,
            AuthUserRoleAssignment.role_id == role_id,
            AuthUserRoleAssignment.workspace_id.is_(None)
            if workspace_id is None
            else AuthUserRoleAssignment.workspace_id == workspace_id,
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        return row
    row = AuthUserRoleAssignment(
        user_id=user_id,
        role_id=role_id,
        workspace_id=workspace_id,
        assigned_by=assigned_by,
    )
    db.add(row)
    await db.flush()
    invalidate_user_cache(user_id)
    return row
