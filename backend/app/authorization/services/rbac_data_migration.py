"""Idempotent migration from legacy roles to layered RBAC."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.constants.system_roles import (
    ACCESS_MANAGER_ROLE_ID,
    ACCOUNT_ADMIN_ROLE_ID,
    AGENT_CREATOR_ROLE_ID,
    AGENT_DEVELOPER_ROLE_ID,
    AGENT_MIGRATION_MANAGER_ROLE_ID,
    AGENT_OPERATOR_ROLE_ID,
    AGENT_OWNER_ROLE_ID,
    AGENT_TYPE_DESIGNER_ROLE_ID,
    AUDITOR_ROLE_ID,
    AUTHORIZATION_ADMIN_ROLE_ID,
    PLATFORM_ADMIN_ROLE_ID,
    SECURITY_ADMIN_ROLE_ID,
    USER_ADMIN_ROLE_ID,
    USER_ROLE_ID,
)
from app.authorization.services.audit_service import log_authorization_event
from app.authorization.services.rbac_catalog_bootstrap import (
    ensure_all_gathering_roles,
    ensure_gathering_access_roles,
    gathering_role_id,
)
from app.authorization.services.role_assignment_service import assign_role
from app.models import Agent, Gathering, GatheringMember, GatheringMemberRole, User
from app.models.authorization import AuthResourceOwnership, AuthUserRoleAssignment


async def _resolve_bootstrap_account_admin(db: AsyncSession) -> UUID | None:
    raw = os.environ.get("AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN", "").strip()
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        row = await db.execute(select(User.id).where(User.email == raw))
        return row.scalar_one_or_none()


async def migrate_legacy_user_roles(db: AsyncSession) -> dict[str, int]:
    """Map legacy Agent Owner / Authorization Admin assignments to functional/admin roles."""
    stats = {"users_migrated": 0, "account_admin_assigned": 0, "warnings": 0}
    bootstrap_admin = await _resolve_bootstrap_account_admin(db)

    users = (await db.execute(select(User.id))).scalars().all()
    for user_id in users:
        assignments = (
            await db.execute(
                select(AuthUserRoleAssignment.role_id).where(
                    AuthUserRoleAssignment.user_id == user_id
                )
            )
        ).scalars().all()
        role_set = set(assignments)

        if AGENT_OWNER_ROLE_ID in role_set:
            for rid in (
                AGENT_CREATOR_ROLE_ID,
                AGENT_DEVELOPER_ROLE_ID,
                AGENT_OPERATOR_ROLE_ID,
                AGENT_TYPE_DESIGNER_ROLE_ID,
                AGENT_MIGRATION_MANAGER_ROLE_ID,
            ):
                await assign_role(db, user_id=user_id, role_id=rid)
            stats["users_migrated"] += 1

        if AUTHORIZATION_ADMIN_ROLE_ID in role_set:
            for rid in (SECURITY_ADMIN_ROLE_ID, USER_ADMIN_ROLE_ID, AUDITOR_ROLE_ID):
                await assign_role(db, user_id=user_id, role_id=rid)
            if P_platform_needed(user_id):
                await assign_role(db, user_id=user_id, role_id=PLATFORM_ADMIN_ROLE_ID)
            stats["users_migrated"] += 1

        if bootstrap_admin and user_id == bootstrap_admin:
            await assign_role(db, user_id=user_id, role_id=ACCOUNT_ADMIN_ROLE_ID)
            stats["account_admin_assigned"] += 1
        elif AUTHORIZATION_ADMIN_ROLE_ID in role_set and not bootstrap_admin:
            stats["warnings"] += 1
            await log_authorization_event(
                db,
                event_type="LEGACY_ROLE_MIGRATION_WARNING",
                target_user_id=user_id,
                reason="AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN unset; ACCOUNT_ADMIN not auto-assigned",
            )

    return stats


def P_platform_needed(_user_id: UUID) -> bool:
    return True  # preserve application settings access for legacy authorization admins


async def migrate_gathering_memberships(db: AsyncSession) -> int:
    count = 0
    gatherings = (await db.execute(select(Gathering))).scalars().all()
    for gathering in gatherings:
        role_map = await ensure_gathering_access_roles(db, gathering)
        owner_role_id = role_map["owner"]
        reader_role_id = role_map["reader"]

        if gathering.owner_id:
            await assign_role(
                db,
                user_id=gathering.owner_id,
                role_id=owner_role_id,
                workspace_id=gathering.id,
            )
            count += 1

        members = (
            await db.execute(
                select(GatheringMember).where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.user_id.isnot(None),
                )
            )
        ).scalars().all()
        for member in members:
            if member.role == GatheringMemberRole.owner:
                continue
            if member.user_id:
                await assign_role(
                    db,
                    user_id=member.user_id,
                    role_id=reader_role_id,
                    workspace_id=gathering.id,
                )
                count += 1
    return count


async def migrate_agent_ownership_records(db: AsyncSession) -> int:
    count = 0
    agents = (await db.execute(select(Agent))).scalars().all()
    for agent in agents:
        existing = await db.execute(
            select(AuthResourceOwnership.id).where(
                AuthResourceOwnership.resource_type == "agent",
                AuthResourceOwnership.resource_id == agent.id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        from app.authorization.services.resource_ancestry_service import agent_gathering_id

        gid = await agent_gathering_id(db, agent.id)
        owner_role_id = gathering_role_id(gid, "owner") if gid else USER_ROLE_ID
        db.add(
            AuthResourceOwnership(
                resource_type="agent",
                resource_id=agent.id,
                owner_role_id=owner_role_id,
                responsible_user_id=agent.owner_user_id,
                workspace_id=gid,
            )
        )
        count += 1
    return count


async def run_rbac_data_migration(db: AsyncSession) -> dict[str, int]:
    await ensure_all_gathering_roles(db)
    user_stats = await migrate_legacy_user_roles(db)
    gathering_count = await migrate_gathering_memberships(db)
    ownership_count = await migrate_agent_ownership_records(db)
    return {
        **user_stats,
        "gathering_assignments": gathering_count,
        "ownership_records": ownership_count,
    }
