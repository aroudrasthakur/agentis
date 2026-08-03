"""Resource ownership records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.services.authorization_service import invalidate_user_cache
from app.authorization.services.audit_service import log_authorization_event
from app.models.authorization import AuthResourceOwnership


async def get_ownership(
    db: AsyncSession, resource_type: str, resource_id: UUID
) -> AuthResourceOwnership | None:
    row = await db.execute(
        select(AuthResourceOwnership).where(
            AuthResourceOwnership.resource_type == resource_type,
            AuthResourceOwnership.resource_id == resource_id,
        )
    )
    return row.scalar_one_or_none()


async def transfer_ownership(
    db: AsyncSession,
    *,
    actor_user_id: UUID,
    resource_type: str,
    resource_id: UUID,
    new_owner_role_id: UUID,
    new_responsible_user_id: UUID | None,
    reason: str | None = None,
) -> AuthResourceOwnership:
    row = await get_ownership(db, resource_type, resource_id)
    previous = None
    if row:
        previous = {
            "owner_role_id": str(row.owner_role_id),
            "responsible_user_id": str(row.responsible_user_id) if row.responsible_user_id else None,
        }
        row.owner_role_id = new_owner_role_id
        row.responsible_user_id = new_responsible_user_id
    else:
        row = AuthResourceOwnership(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_role_id=new_owner_role_id,
            responsible_user_id=new_responsible_user_id,
            assigned_by_user_id=actor_user_id,
        )
        db.add(row)
    await log_authorization_event(
        db,
        event_type="RESOURCE_OWNERSHIP_TRANSFERRED",
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=str(resource_id),
        previous_value=previous,
        new_value={
            "owner_role_id": str(new_owner_role_id),
            "responsible_user_id": str(new_responsible_user_id) if new_responsible_user_id else None,
        },
        reason=reason,
    )
    if new_responsible_user_id:
        invalidate_user_cache(new_responsible_user_id)
    if previous and previous.get("responsible_user_id"):
        invalidate_user_cache(UUID(previous["responsible_user_id"]))
    return row
