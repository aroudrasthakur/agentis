"""Session role selection — one active assignment determines RBAC for the JWT session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gathering
from app.models.authorization import AuthRole, AuthRoleStatus, AuthUserRoleAssignment


def _assignment_active(row: AuthUserRoleAssignment) -> bool:
    now = datetime.now(timezone.utc)
    if row.valid_from and row.valid_from > now:
        return False
    if row.valid_until and row.valid_until <= now:
        return False
    return True


@dataclass
class SessionRoleOption:
    assignment_id: UUID
    role_id: UUID
    role_name: str
    role_slug: str
    category: str
    workspace_id: UUID | None
    workspace_name: str | None


async def list_session_role_options(
    db: AsyncSession, user_id: UUID
) -> list[SessionRoleOption]:
    rows = await db.execute(
        select(AuthUserRoleAssignment, AuthRole)
        .join(AuthRole, AuthRole.id == AuthUserRoleAssignment.role_id)
        .where(
            AuthUserRoleAssignment.user_id == user_id,
            AuthRole.status.in_((AuthRoleStatus.active, AuthRoleStatus.deprecated)),
        )
        .order_by(AuthRole.name)
    )
    options: list[SessionRoleOption] = []
    gathering_names: dict[UUID, str] = {}
    for assignment, role in rows.all():
        if not _assignment_active(assignment):
            continue
        ws_name: str | None = None
        if assignment.workspace_id:
            if assignment.workspace_id not in gathering_names:
                g = await db.get(Gathering, assignment.workspace_id)
                gathering_names[assignment.workspace_id] = g.name if g else "Gathering"
            ws_name = gathering_names[assignment.workspace_id]
        options.append(
            SessionRoleOption(
                assignment_id=assignment.id,
                role_id=role.id,
                role_name=role.name,
                role_slug=role.slug,
                category=role.category.value,
                workspace_id=assignment.workspace_id,
                workspace_name=ws_name,
            )
        )
    return options


async def resolve_default_session_assignment_id(db: AsyncSession, user_id: UUID) -> UUID | None:
    options = await list_session_role_options(db, user_id)
    if not options:
        return None
    preferred = (
        "user",
        "agent-creator",
        "agent-developer",
        "agent-operator",
    )
    by_slug = {o.role_slug: o for o in options}
    for slug in preferred:
        if slug in by_slug:
            return by_slug[slug].assignment_id
    return options[0].assignment_id


async def validate_session_assignment(
    db: AsyncSession, user_id: UUID, assignment_id: UUID
) -> AuthUserRoleAssignment:
    row = await db.get(AuthUserRoleAssignment, assignment_id)
    if not row or row.user_id != user_id:
        raise ValueError("Invalid role assignment")
    if not _assignment_active(row):
        raise ValueError("Role assignment is not active")
    role = await db.get(AuthRole, row.role_id)
    if not role or role.status not in (AuthRoleStatus.active, AuthRoleStatus.deprecated):
        raise ValueError("Role is not available")
    return row


async def option_for_assignment(
    db: AsyncSession, assignment: AuthUserRoleAssignment
) -> SessionRoleOption:
    role = await db.get(AuthRole, assignment.role_id)
    if not role:
        raise ValueError("Role not found")
    ws_name = None
    if assignment.workspace_id:
        g = await db.get(Gathering, assignment.workspace_id)
        ws_name = g.name if g else None
    return SessionRoleOption(
        assignment_id=assignment.id,
        role_id=role.id,
        role_name=role.name,
        role_slug=role.slug,
        category=role.category.value,
        workspace_id=assignment.workspace_id,
        workspace_name=ws_name,
    )
