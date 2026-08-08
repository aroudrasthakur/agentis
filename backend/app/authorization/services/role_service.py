"""Role CRUD, validation, and delegation safeguards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.constants.system_roles import SYSTEM_ROLE_IDS, USER_ROLE_ID
from app.authorization.permissions.registry import PERMISSION_BY_KEY, PERMISSIONS
from app.authorization.services.audit_service import log_authorization_event
from app.authorization.services.authorization_service import AuthorizationContext, can, invalidate_user_cache
from app.authorization.services.role_assignment_service import assign_role
from app.models import User
from app.models.authorization import (
    AuthRole,
    AuthRoleCategory,
    AuthRoleInheritance,
    AuthRoleKind,
    AuthRolePermission,
    AuthRoleStatus,
    AuthUserRoleAssignment,
    PermissionEffect,
    PermissionScope,
)


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base[:120] or "role"


@dataclass
class RoleValidationIssue:
    field: str | None
    permission_key: str | None
    message: str
    severity: str


@dataclass
class RoleValidationResult:
    valid: bool
    errors: list[RoleValidationIssue]
    missing_dependencies: list[str]
    conflicts: list[str]
    privilege_escalation_risks: list[str]


def validate_role_permissions(
    permission_rows: list[tuple[str, str, str]],
) -> RoleValidationResult:
    errors: list[RoleValidationIssue] = []
    missing: set[str] = set()
    conflicts: set[str] = set()
    allowed_keys = {key for key, effect, _scope in permission_rows if effect == "allow"}

    for key, effect, scope in permission_rows:
        definition = PERMISSION_BY_KEY.get(key)
        if not definition:
            errors.append(
                RoleValidationIssue(None, key, f"Unknown permission: {key}", "error")
            )
            continue
        if scope not in definition.supported_scopes:
            errors.append(
                RoleValidationIssue(
                    "scope",
                    key,
                    f"Scope '{scope}' is not supported for {key}",
                    "error",
                )
            )
        if effect == "allow":
            for dep in definition.dependencies:
                if dep not in allowed_keys and dep not in {k for k, e, _ in permission_rows if e == "allow"}:
                    missing.add(dep)

    return RoleValidationResult(
        valid=not errors and not missing,
        errors=errors,
        missing_dependencies=sorted(missing),
        conflicts=sorted(conflicts),
        privilege_escalation_risks=[],
    )


async def actor_can_delegate_permissions(
    db: AsyncSession,
    actor: User,
    permission_rows: list[tuple[str, str, str]],
) -> list[str]:
    """Return permission keys the actor cannot delegate."""
    blocked: list[str] = []
    for key, effect, scope in permission_rows:
        if effect != "allow":
            continue
        definition = PERMISSION_BY_KEY.get(key)
        if not definition or not definition.delegable:
            blocked.append(key)
            continue
        ctx = AuthorizationContext(context={"delegation_scope": scope})
        if not await can(db, actor, "role.permissions.manage", ctx):
            blocked.append(key)
            continue
        if not await can(db, actor, key, ctx):
            blocked.append(key)
    return blocked


async def list_roles(
    db: AsyncSession,
    *,
    workspace_id: UUID | None = None,
    category: str | None = None,
    kind: str | None = None,
    assignable_to_users: bool | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
) -> list[AuthRole]:
    stmt = select(AuthRole).where(AuthRole.status == AuthRoleStatus.active)
    if workspace_id is not None:
        stmt = stmt.where(
            (AuthRole.workspace_id.is_(None)) | (AuthRole.workspace_id == workspace_id)
        )
    if category:
        stmt = stmt.where(AuthRole.category == AuthRoleCategory(category))
    if kind:
        stmt = stmt.where(AuthRole.kind == AuthRoleKind(kind))
    if assignable_to_users is not None:
        stmt = stmt.where(AuthRole.assignable_to_users == assignable_to_users)
    if resource_type:
        stmt = stmt.where(AuthRole.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuthRole.resource_id == resource_id)
    result = await db.execute(stmt.order_by(AuthRole.name))
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: UUID) -> AuthRole | None:
    return await db.get(AuthRole, role_id)


async def create_custom_role(
    db: AsyncSession,
    *,
    actor: User,
    name: str,
    description: str | None,
    workspace_id: UUID | None,
    permission_rows: list[tuple[str, str, str]],
    parent_role_ids: list[UUID] | None = None,
) -> AuthRole:
    validation = validate_role_permissions(permission_rows)
    if not validation.valid:
        raise ValueError("Role validation failed")
    blocked = await actor_can_delegate_permissions(db, actor, permission_rows)
    if blocked:
        raise ValueError(f"Cannot delegate permissions: {', '.join(blocked)}")

    slug = _slugify(name)
    existing = await db.execute(
        select(AuthRole.id).where(
            AuthRole.slug == slug,
            AuthRole.workspace_id.is_(None) if workspace_id is None else AuthRole.workspace_id == workspace_id,
        )
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid4().hex[:6]}"

    role = AuthRole(
        id=uuid4(),
        workspace_id=workspace_id,
        name=name.strip(),
        slug=slug,
        description=description,
        kind=AuthRoleKind.custom,
        category=AuthRoleCategory.functional,
        status=AuthRoleStatus.active,
        is_default=False,
        is_immutable=False,
        is_managed=False,
        assignable_to_users=True,
        created_by=actor.id,
    )
    db.add(role)
    await db.flush()

    for key, effect, scope in permission_rows:
        db.add(
            AuthRolePermission(
                role_id=role.id,
                permission_key=key,
                effect=PermissionEffect.allow if effect == "allow" else PermissionEffect.deny,
                scope=PermissionScope(scope),
                created_by=actor.id,
            )
        )

    for parent_id in parent_role_ids or []:
        if parent_id == role.id:
            raise ValueError("Role cannot inherit from itself")
        db.add(AuthRoleInheritance(child_role_id=role.id, parent_role_id=parent_id))

    await log_authorization_event(
        db,
        event_type="role.created",
        actor_user_id=actor.id,
        role_id=role.id,
        new_value={"name": name, "permissions": permission_rows},
    )
    invalidate_user_cache()
    return role


async def archive_role(db: AsyncSession, actor: User, role_id: UUID) -> AuthRole:
    role = await db.get(AuthRole, role_id)
    if not role:
        raise ValueError("Role not found")
    if role.id in SYSTEM_ROLE_IDS or role.is_immutable:
        raise ValueError("Protected system role cannot be archived")
    role.status = AuthRoleStatus.archived
    role.updated_by = actor.id
    await log_authorization_event(
        db, event_type="role.archived", actor_user_id=actor.id, role_id=role.id
    )
    invalidate_user_cache()
    return role


async def assign_role_to_user(
    db: AsyncSession,
    *,
    actor: User,
    target_user_id: UUID,
    role_id: UUID,
    workspace_id: UUID | None = None,
) -> AuthUserRoleAssignment:
    if target_user_id == actor.id and role_id != USER_ROLE_ID:
        if not await can(db, actor, "user.roles.assign"):
            raise ValueError("Cannot assign roles to yourself without permission")

    role = await db.get(AuthRole, role_id)
    if not role or role.status not in (AuthRoleStatus.active, AuthRoleStatus.deprecated):
        raise ValueError("Role is not assignable")
    if role.status == AuthRoleStatus.deprecated:
        raise ValueError("Deprecated role cannot be assigned")
    if not role.assignable_to_users:
        is_gathering_owner = (
            role.category == AuthRoleCategory.gathering_access and role.slug.endswith("-owner")
        )
        if not is_gathering_owner:
            raise ValueError("This access role cannot be assigned directly to users")

    row = await assign_role(
        db,
        user_id=target_user_id,
        role_id=role_id,
        workspace_id=workspace_id,
        assigned_by=actor.id,
    )
    await log_authorization_event(
        db,
        event_type="role.assigned",
        actor_user_id=actor.id,
        target_user_id=target_user_id,
        role_id=role_id,
        workspace_id=workspace_id,
    )
    return row


async def count_role_members(db: AsyncSession, role_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(AuthUserRoleAssignment)
        .where(AuthUserRoleAssignment.role_id == role_id)
    )
    return int(result.scalar_one())
