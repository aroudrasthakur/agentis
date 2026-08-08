"""Seed system roles and default assignments."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.constants.system_roles import (
    AGENT_CREATOR_ROLE_ID,
    AGENT_DEVELOPER_ROLE_ID,
    AGENT_MIGRATION_MANAGER_ROLE_ID,
    AGENT_OPERATOR_ROLE_ID,
    AGENT_OWNER_ROLE_ID,
    AGENT_TYPE_DESIGNER_ROLE_ID,
    AUTHORIZATION_ADMIN_ROLE_ID,
    USER_ROLE_ID,
)
from app.authorization.services.role_assignment_service import assign_role


async def ensure_system_roles(db: AsyncSession) -> None:
    from app.authorization.services.rbac_catalog_bootstrap import ensure_rbac_catalog
    from app.authorization.services.rbac_data_migration import run_rbac_data_migration

    await ensure_rbac_catalog(db)
    await run_rbac_data_migration(db)


_DEFAULT_FUNCTIONAL_ROLE_IDS = (
    AGENT_CREATOR_ROLE_ID,
    AGENT_DEVELOPER_ROLE_ID,
    AGENT_OPERATOR_ROLE_ID,
    AGENT_TYPE_DESIGNER_ROLE_ID,
    AGENT_MIGRATION_MANAGER_ROLE_ID,
)


async def assign_default_roles_for_new_user(db: AsyncSession, user_id: UUID) -> None:
    await ensure_system_roles(db)
    await assign_role(db, user_id=user_id, role_id=USER_ROLE_ID)
    for role_id in _DEFAULT_FUNCTIONAL_ROLE_IDS:
        await assign_role(db, user_id=user_id, role_id=role_id)


async def migrate_existing_users(db: AsyncSession) -> int:
    """Idempotent: USER for everyone; AGENT_OWNER + AUTH_ADMIN for users missing assignments."""
    from app.models import User

    await ensure_system_roles(db)
    users = (await db.execute(select(User.id))).scalars().all()
    count = 0
    for user_id in users:
        await assign_role(db, user_id=user_id, role_id=USER_ROLE_ID)
        await assign_role(db, user_id=user_id, role_id=AGENT_OWNER_ROLE_ID)
        await assign_role(db, user_id=user_id, role_id=AUTHORIZATION_ADMIN_ROLE_ID)
        count += 1
    return count
