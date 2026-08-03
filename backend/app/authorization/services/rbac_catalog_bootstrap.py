"""Seed built-in roles, inheritance, and gathering access roles for layered RBAC."""

from __future__ import annotations

import re
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.constants.system_roles import (
    ACCESS_MANAGER_ROLE_ID,
    ACCOUNT_ADMIN_ROLE_ID,
    AGENT_CREATOR_ROLE_ID,
    AGENT_DEVELOPER_ROLE_ID,
    AGENT_MIGRATION_MANAGER_ROLE_ID,
    AGENT_OPERATOR_ROLE_ID,
    AGENT_OWNER_ROLE_ID,
    AGENT_REVIEWER_ROLE_ID,
    AGENT_TYPE_DESIGNER_ROLE_ID,
    AUDITOR_ROLE_ID,
    AUTHORIZATION_ADMIN_ROLE_ID,
    FUNCTIONAL_ROLE_IDS,
    GATHERING_ACCESS_ROLE_SUFFIXES,
    GATHERING_ROLE_NAMESPACE,
    OBSERVABILITY_ANALYST_ROLE_ID,
    PLATFORM_ADMIN_ROLE_ID,
    SECURITY_ADMIN_ROLE_ID,
    SYSTEM_ADMIN_ROLE_IDS,
    USER_ADMIN_ROLE_ID,
    USER_ROLE_ID,
)
from app.authorization.permissions.registry import (
    AGENT_OWNER_PERMISSIONS,
    AUTH_ADMIN_PERMISSIONS,
    P,
    USER_BASELINE_PERMISSIONS,
)
from app.models import Gathering
from app.models.authorization import (
    AuthRole,
    AuthRoleCategory,
    AuthRoleInheritance,
    AuthRoleKind,
    AuthRolePermission,
    AuthRoleStatus,
    AuthGatheringAuthorizationSettings,
    GatheringAccessMode,
    GrantSource,
    PermissionEffect,
    PermissionScope,
)


def _scope(name: str) -> PermissionScope:
    return PermissionScope(name)


def gathering_role_id(gathering_id: UUID, suffix: str) -> UUID:
    return uuid.uuid5(GATHERING_ROLE_NAMESPACE, f"{gathering_id}:{suffix}")


def _slugify_gathering(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "gathering"


async def _ensure_role(
    db: AsyncSession,
    *,
    role_id: UUID,
    name: str,
    slug: str,
    description: str,
    category: AuthRoleCategory,
    is_default: bool,
    is_immutable: bool,
    is_managed: bool,
    assignable_to_users: bool,
    workspace_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    status: AuthRoleStatus = AuthRoleStatus.active,
) -> AuthRole:
    role = await db.get(AuthRole, role_id)
    if role is None:
        role = AuthRole(
            id=role_id,
            name=name,
            slug=slug,
            description=description,
            kind=AuthRoleKind.system,
            category=category,
            status=status,
            is_default=is_default,
            is_immutable=is_immutable,
            is_managed=is_managed,
            assignable_to_users=assignable_to_users,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.add(role)
        await db.flush()
    else:
        role.category = category
        role.is_managed = is_managed
        role.assignable_to_users = assignable_to_users
        if status == AuthRoleStatus.deprecated:
            role.status = AuthRoleStatus.deprecated
    return role


async def _ensure_perm(
    db: AsyncSession,
    role_id: UUID,
    key: str,
    scope: str,
    *,
    workspace_id: UUID | None = None,
    resource_type: str | None = None,
    resource_ids: list[UUID] | None = None,
) -> None:
    q = select(AuthRolePermission.id).where(
        AuthRolePermission.role_id == role_id,
        AuthRolePermission.permission_key == key,
        AuthRolePermission.scope == _scope(scope),
        AuthRolePermission.effect == PermissionEffect.allow,
    )
    if resource_type:
        q = q.where(AuthRolePermission.resource_type == resource_type)
    existing = (await db.execute(q.limit(1))).scalar_one_or_none()
    if existing:
        return
    db.add(
        AuthRolePermission(
            role_id=role_id,
            permission_key=key,
            effect=PermissionEffect.allow,
            scope=_scope(scope),
            resource_type=resource_type,
            resource_ids=[str(x) for x in (resource_ids or [])],
            grant_source=GrantSource.system_seed,
        )
    )


async def _ensure_inheritance(db: AsyncSession, child_id: UUID, parent_id: UUID) -> None:
    dup = await db.execute(
        select(AuthRoleInheritance.id).where(
            AuthRoleInheritance.child_role_id == child_id,
            AuthRoleInheritance.parent_role_id == parent_id,
        )
    )
    if dup.scalar_one_or_none():
        return
    db.add(AuthRoleInheritance(child_role_id=child_id, parent_role_id=parent_id))


# Permission bundles (system scope unless noted)
ACCOUNT_ADMIN_PERMS = (
    (P.PROFILE_READ_SELF, "system"),
    (P.PROFILE_UPDATE_SELF, "system"),
)

SECURITY_ADMIN_PERMS = (
    (P.ROLE_LIST, "system"),
    (P.ROLE_READ, "system"),
    (P.ROLE_CREATE, "system"),
    (P.ROLE_UPDATE, "system"),
    (P.ROLE_ARCHIVE, "system"),
    (P.ROLE_PERMISSIONS_READ, "system"),
    (P.ROLE_PERMISSIONS_MANAGE, "system"),
    (P.ROLE_INHERITANCE_READ, "system"),
    (P.ROLE_INHERITANCE_MANAGE, "system"),
    (P.ROLE_ASSIGN, "system"),
    (P.ROLE_UNASSIGN, "system"),
    (P.USER_LIST, "system"),
    (P.USER_READ, "system"),
    (P.USER_ROLES_READ, "system"),
    (P.USER_ROLES_ASSIGN, "system"),
    (P.USER_PERMISSIONS_GRANT, "system"),
    (P.USER_PERMISSIONS_DENY, "system"),
    (P.AGENT_ACCESS_READ, "system"),
    (P.AGENT_ACCESS_MANAGE, "system"),
    (P.AGENT_OWNER_CHANGE, "system"),
    (P.AGENT_TYPE_PERMISSIONS_MANAGE, "system"),
    (P.AUDIT_READ, "system"),
    (P.AUDIT_EXPORT, "system"),
    (P.AUTHORIZATION_EXPLAIN, "system"),
)

USER_ADMIN_PERMS = (
    (P.USER_LIST, "system"),
    (P.USER_READ, "system"),
    (P.USER_ROLES_READ, "system"),
    (P.USER_ROLES_ASSIGN, "system"),
    (P.WORKSPACE_MEMBERS_READ, "workspace"),
    (P.WORKSPACE_MEMBERS_MANAGE, "workspace"),
)

PLATFORM_ADMIN_PERMS = (
    (P.AGENT_LIST, "system"),
    (P.AGENT_READ, "system"),
    (P.AGENT_CREATE, "system"),
    (P.AGENT_UPDATE, "system"),
    (P.AGENT_UPDATE_CONFIGURATION, "system"),
    (P.AGENT_UPDATE_INSTRUCTIONS, "system"),
    (P.AGENT_DELETE, "system"),
    (P.AGENT_TYPE_READ, "system"),
    (P.AGENT_TYPE_ASSIGN, "system"),
    (P.AGENT_TYPE_CHANGE, "system"),
    (P.AGENT_TYPE_MIGRATE, "system"),
    (P.AGENT_DEPLOY, "system"),
    (P.AGENT_UNDEPLOY, "system"),
    (P.AGENT_DEPLOYMENT_READ, "system"),
    (P.AGENT_RUN_CREATE, "system"),
    (P.AGENT_RUN_READ, "system"),
    (P.AGENT_RUN_INTERACT, "system"),
    (P.AGENT_TYPE_LIST, "system"),
    (P.AGENT_TYPE_READ_DEF, "system"),
    (P.AGENT_TYPE_CREATE, "system"),
    (P.AGENT_TYPE_UPDATE, "system"),
    (P.AGENT_TYPE_ARCHIVE, "system"),
    (P.WORKSPACE_READ, "workspace"),
)

AUDITOR_PERMS = (
    (P.AUDIT_READ, "system"),
    (P.AGENT_READ, "system"),
    (P.AGENT_DEPLOYMENT_READ, "system"),
    (P.AGENT_RUN_READ, "system"),
    (P.ROLE_LIST, "system"),
    (P.ROLE_READ, "system"),
    (P.ROLE_PERMISSIONS_READ, "system"),
    (P.USER_LIST, "system"),
    (P.USER_READ, "system"),
    (P.USER_ROLES_READ, "system"),
    (P.WORKSPACE_READ, "workspace"),
    (P.WORKSPACE_MEMBERS_READ, "workspace"),
)

FUNCTIONAL_BUNDLES: dict[UUID, tuple[tuple[str, str], ...]] = {
    AGENT_CREATOR_ROLE_ID: (
        (P.AGENT_CREATE, "system"),
        (P.AGENT_LIST_ACCESSIBLE, "system"),
        (P.AGENT_READ_ACCESSIBLE, "system"),
    ),
    AGENT_DEVELOPER_ROLE_ID: (
        (P.AGENT_READ, "workspace"),
        (P.AGENT_UPDATE, "owned"),
        (P.AGENT_UPDATE_CONFIGURATION, "owned"),
        (P.AGENT_UPDATE_INSTRUCTIONS, "owned"),
        (P.AGENT_TYPE_READ, "owned"),
        (P.AGENT_DEPLOYMENT_READ, "owned"),
        (P.AGENT_RUN_READ, "owned"),
    ),
    AGENT_OPERATOR_ROLE_ID: (
        (P.AGENT_READ, "workspace"),
        (P.AGENT_DEPLOYMENT_READ, "owned"),
        (P.AGENT_DEPLOY, "owned"),
        (P.AGENT_UNDEPLOY, "owned"),
        (P.AGENT_RUN_CREATE, "owned"),
        (P.AGENT_RUN_READ, "owned"),
        (P.AGENT_RUN_INTERACT, "owned"),
    ),
    AGENT_REVIEWER_ROLE_ID: (
        (P.AGENT_READ, "workspace"),
        (P.AGENT_DEPLOYMENT_READ, "workspace"),
        (P.AGENT_RUN_READ, "workspace"),
        (P.AGENT_TYPE_READ_DEF, "system"),
    ),
    AGENT_TYPE_DESIGNER_ROLE_ID: (
        (P.AGENT_TYPE_LIST, "system"),
        (P.AGENT_TYPE_READ_DEF, "system"),
        (P.AGENT_TYPE_CREATE, "workspace"),
        (P.AGENT_TYPE_UPDATE, "owned"),
        (P.AGENT_TYPE_ARCHIVE, "owned"),
    ),
    AGENT_MIGRATION_MANAGER_ROLE_ID: (
        (P.AGENT_READ, "owned"),
        (P.AGENT_UPDATE_CONFIGURATION, "owned"),
        (P.AGENT_TYPE_READ, "owned"),
        (P.AGENT_TYPE_ASSIGN, "owned"),
        (P.AGENT_TYPE_CHANGE, "owned"),
        (P.AGENT_TYPE_MIGRATE, "owned"),
        (P.AGENT_TYPE_READ_DEF, "system"),
    ),
    OBSERVABILITY_ANALYST_ROLE_ID: (
        (P.AGENT_READ, "workspace"),
        (P.AGENT_DEPLOYMENT_READ, "workspace"),
        (P.AGENT_RUN_READ, "workspace"),
        (P.AUDIT_READ, "system"),
    ),
    ACCESS_MANAGER_ROLE_ID: (
        (P.WORKSPACE_READ, "workspace"),
        (P.AGENT_ACCESS_READ, "workspace"),
        (P.AGENT_ACCESS_MANAGE, "workspace"),
        (P.AGENT_TYPE_PERMISSIONS_MANAGE, "workspace"),
    ),
}


async def ensure_rbac_catalog(db: AsyncSession) -> None:
    await _ensure_role(
        db,
        role_id=USER_ROLE_ID,
        name="USER",
        slug="user",
        description="Default baseline role for every account.",
        category=AuthRoleCategory.baseline,
        is_default=True,
        is_immutable=True,
        is_managed=True,
        assignable_to_users=True,
    )
    for key, effect, scope in USER_BASELINE_PERMISSIONS:
        if effect == "allow":
            await _ensure_perm(db, USER_ROLE_ID, key, scope)

    await _ensure_role(
        db,
        role_id=AGENT_OWNER_ROLE_ID,
        name="Agent Owner",
        slug="agent-owner",
        description="Legacy operator role (deprecated).",
        category=AuthRoleCategory.legacy,
        is_default=False,
        is_immutable=True,
        is_managed=True,
        assignable_to_users=False,
        status=AuthRoleStatus.deprecated,
    )
    for key, effect, scope in AGENT_OWNER_PERMISSIONS:
        if effect == "allow":
            await _ensure_perm(db, AGENT_OWNER_ROLE_ID, key, scope)

    await _ensure_role(
        db,
        role_id=AUTHORIZATION_ADMIN_ROLE_ID,
        name="Authorization Admin",
        slug="authorization-admin",
        description="Legacy authorization admin (deprecated).",
        category=AuthRoleCategory.legacy,
        is_default=False,
        is_immutable=True,
        is_managed=True,
        assignable_to_users=False,
        status=AuthRoleStatus.deprecated,
    )
    for key, effect, scope in AUTH_ADMIN_PERMISSIONS:
        if effect == "allow":
            await _ensure_perm(db, AUTHORIZATION_ADMIN_ROLE_ID, key, scope)

    admin_specs = [
        (ACCOUNT_ADMIN_ROLE_ID, "ACCOUNT_ADMIN", "account-admin", "Top-level account administration.", AuthRoleCategory.system_admin),
        (SECURITY_ADMIN_ROLE_ID, "SECURITY_ADMIN", "security-admin", "Security and authorization administration.", AuthRoleCategory.system_admin),
        (USER_ADMIN_ROLE_ID, "USER_ADMIN", "user-admin", "User and membership administration.", AuthRoleCategory.system_admin),
        (PLATFORM_ADMIN_ROLE_ID, "PLATFORM_ADMIN", "platform-admin", "Platform resource administration.", AuthRoleCategory.system_admin),
        (AUDITOR_ROLE_ID, "AUDITOR", "auditor", "Read-only audit and operational visibility.", AuthRoleCategory.system_admin),
    ]
    for rid, name, slug, desc, cat in admin_specs:
        await _ensure_role(
            db,
            role_id=rid,
            name=name,
            slug=slug,
            description=desc,
            category=cat,
            is_default=False,
            is_immutable=True,
            is_managed=True,
            assignable_to_users=True,
        )

    for key, scope in ACCOUNT_ADMIN_PERMS:
        await _ensure_perm(db, ACCOUNT_ADMIN_ROLE_ID, key, scope)
    for key, scope in SECURITY_ADMIN_PERMS:
        await _ensure_perm(db, SECURITY_ADMIN_ROLE_ID, key, scope)
    for key, scope in USER_ADMIN_PERMS:
        await _ensure_perm(db, USER_ADMIN_ROLE_ID, key, scope)
    for key, scope in PLATFORM_ADMIN_PERMS:
        await _ensure_perm(db, PLATFORM_ADMIN_ROLE_ID, key, scope)
    for key, scope in AUDITOR_PERMS:
        await _ensure_perm(db, AUDITOR_ROLE_ID, key, scope)

    await _ensure_inheritance(db, ACCOUNT_ADMIN_ROLE_ID, SECURITY_ADMIN_ROLE_ID)
    await _ensure_inheritance(db, ACCOUNT_ADMIN_ROLE_ID, PLATFORM_ADMIN_ROLE_ID)
    await _ensure_inheritance(db, ACCOUNT_ADMIN_ROLE_ID, AUDITOR_ROLE_ID)
    await _ensure_inheritance(db, SECURITY_ADMIN_ROLE_ID, USER_ADMIN_ROLE_ID)

    functional_specs = [
        (AGENT_CREATOR_ROLE_ID, "AGENT_CREATOR", "agent-creator"),
        (AGENT_DEVELOPER_ROLE_ID, "AGENT_DEVELOPER", "agent-developer"),
        (AGENT_OPERATOR_ROLE_ID, "AGENT_OPERATOR", "agent-operator"),
        (AGENT_REVIEWER_ROLE_ID, "AGENT_REVIEWER", "agent-reviewer"),
        (AGENT_TYPE_DESIGNER_ROLE_ID, "AGENT_TYPE_DESIGNER", "agent-type-designer"),
        (AGENT_MIGRATION_MANAGER_ROLE_ID, "AGENT_MIGRATION_MANAGER", "agent-migration-manager"),
        (OBSERVABILITY_ANALYST_ROLE_ID, "OBSERVABILITY_ANALYST", "observability-analyst"),
        (ACCESS_MANAGER_ROLE_ID, "ACCESS_MANAGER", "access-manager"),
    ]
    for rid, name, slug in functional_specs:
        await _ensure_role(
            db,
            role_id=rid,
            name=name,
            slug=slug,
            description=f"Functional role: {name}.",
            category=AuthRoleCategory.functional,
            is_default=False,
            is_immutable=True,
            is_managed=True,
            assignable_to_users=True,
        )
        for key, scope in FUNCTIONAL_BUNDLES.get(rid, ()):
            await _ensure_perm(db, rid, key, scope)


async def ensure_gathering_access_roles(db: AsyncSession, gathering: Gathering) -> dict[str, UUID]:
    """Create managed gathering access roles; return suffix -> role_id."""
    gslug = _slugify_gathering(gathering.name)
    role_map: dict[str, UUID] = {}
    specs = [
        ("reader", f"{gslug.upper()}_READER", f"{gslug}-reader", False),
        ("contributor", f"{gslug.upper()}_CONTRIBUTOR", f"{gslug}-contributor", False),
        ("agent-developer", f"{gslug.upper()}_AGENT_DEVELOPER", f"{gslug}-agent-developer", False),
        ("operator", f"{gslug.upper()}_OPERATOR", f"{gslug}-operator", False),
        ("type-designer", f"{gslug.upper()}_TYPE_DESIGNER", f"{gslug}-type-designer", False),
        ("access-manager", f"{gslug.upper()}_ACCESS_MANAGER", f"{gslug}-access-manager", False),
        ("owner", f"{gslug.upper()}_OWNER", f"{gslug}-owner", True),
    ]
    for suffix, display, slug, assignable in specs:
        rid = gathering_role_id(gathering.id, suffix)
        role_map[suffix] = rid
        await _ensure_role(
            db,
            role_id=rid,
            name=display,
            slug=slug,
            description=f"Gathering access role for {gathering.name}.",
            category=AuthRoleCategory.gathering_access,
            is_default=False,
            is_immutable=True,
            is_managed=True,
            assignable_to_users=assignable,
            workspace_id=gathering.id,
        )

    reader_id = role_map["reader"]
    ws = "workspace"
    reader_perms = (
        (P.WORKSPACE_READ, ws),
        (P.AGENT_LIST, ws),
        (P.AGENT_READ, ws),
        (P.AGENT_DEPLOYMENT_READ, ws),
        (P.AGENT_RUN_READ, ws),
        (P.AGENT_TYPE_LIST, ws),
        (P.AGENT_TYPE_READ_DEF, ws),
    )
    for key, scope in reader_perms:
        await _ensure_perm(db, reader_id, key, scope)

    for suffix, extra in (
        ("contributor", ((P.AGENT_RUN_CREATE, ws), (P.AGENT_RUN_INTERACT, ws))),
        ("agent-developer", (
            (P.AGENT_CREATE, ws),
            (P.AGENT_UPDATE, ws),
            (P.AGENT_UPDATE_CONFIGURATION, ws),
            (P.AGENT_UPDATE_INSTRUCTIONS, ws),
        )),
        ("operator", (
            (P.AGENT_DEPLOY, ws),
            (P.AGENT_UNDEPLOY, ws),
            (P.AGENT_RUN_CREATE, ws),
            (P.AGENT_RUN_INTERACT, ws),
        )),
        ("type-designer", (
            (P.AGENT_TYPE_CREATE, ws),
            (P.AGENT_TYPE_UPDATE, ws),
        )),
        ("access-manager", (
            (P.AGENT_ACCESS_READ, ws),
            (P.AGENT_ACCESS_MANAGE, ws),
        )),
        ("owner", (
            (P.WORKSPACE_MEMBERS_READ, ws),
            (P.WORKSPACE_MEMBERS_MANAGE, ws),
        )),
    ):
        await _ensure_inheritance(db, role_map[suffix], reader_id)
        for key, scope in extra:
            await _ensure_perm(db, role_map[suffix], key, scope)

    for child_suffix, parent_suffix in (
        ("owner", "agent-developer"),
        ("owner", "operator"),
        ("owner", "type-designer"),
        ("owner", "access-manager"),
    ):
        await _ensure_inheritance(db, role_map["owner"], role_map[parent_suffix])

    settings = await db.get(AuthGatheringAuthorizationSettings, gathering.id)
    if settings is None:
        db.add(
            AuthGatheringAuthorizationSettings(
                gathering_id=gathering.id,
                access_mode=GatheringAccessMode.owner_managed,
            )
        )
    return role_map


async def ensure_all_gathering_roles(db: AsyncSession) -> None:
    gatherings = (await db.execute(select(Gathering))).scalars().all()
    for g in gatherings:
        await ensure_gathering_access_roles(db, g)
