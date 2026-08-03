"""Role and permission management API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.deps import RequirePermission, forbidden_response
from app.authorization.permissions.registry import PERMISSIONS, P
from app.authorization.services.authorization_service import (
    AuthorizationContext,
    AuthorizationError,
    authorize,
    get_authorization_metrics,
    require_permission,
)
from app.authorization.services.role_service import (
    archive_role,
    assign_role_to_user,
    count_role_members,
    create_custom_role,
    get_role,
    list_roles,
)
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.models.authorization import AuthRolePermission, AuthUserRoleAssignment

router = APIRouter(prefix="/authorization", tags=["authorization"])


class PermissionDefinitionOut(BaseModel):
    key: str
    label: str
    description: str
    category: str
    resource_type: str
    supported_scopes: list[str]
    sensitive: bool
    assignable_to_custom_roles: bool
    delegable: bool
    dependencies: list[str]
    conflicts: list[str]
    inheritable_from_resource_types: list[str] = Field(default_factory=list)
    propagates_to_resource_types: list[str] = Field(default_factory=list)


class RolePermissionOut(BaseModel):
    permission_key: str
    effect: Literal["allow", "deny"]
    scope: str
    resource_type: str | None = None
    resource_ids: list[str] = Field(default_factory=list)
    with_grant_option: bool = False


class RoleOut(BaseModel):
    id: UUID
    workspace_id: UUID | None = None
    name: str
    slug: str
    description: str | None = None
    kind: Literal["system", "custom"]
    category: str = "functional"
    status: Literal["active", "archived", "deprecated"]
    is_default: bool
    is_immutable: bool
    is_managed: bool = False
    assignable_to_users: bool = True
    resource_type: str | None = None
    resource_id: UUID | None = None
    member_count: int = 0
    permissions: list[RolePermissionOut] = Field(default_factory=list)
    inherited_role_ids: list[UUID] = Field(default_factory=list)
    inheriting_role_ids: list[UUID] = Field(default_factory=list)


class RoleCreate(BaseModel):
    name: str
    description: str | None = None
    workspace_id: UUID | None = None
    permissions: list[RolePermissionOut] = Field(default_factory=list)
    parent_role_ids: list[UUID] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    role_id: UUID
    workspace_id: UUID | None = None


class AuthorizationCheckRequest(BaseModel):
    permission: str
    workspace_id: UUID | None = None
    resource_type: str | None = None
    resource_id: str | None = None


class AuthorizationCheckResponse(BaseModel):
    allowed: bool
    decision: dict[str, Any]


def _role_out(
    role,
    *,
    member_count: int,
    permissions: list[RolePermissionOut],
    inherited_role_ids: list[UUID] | None = None,
    inheriting_role_ids: list[UUID] | None = None,
) -> RoleOut:
    return RoleOut(
        id=role.id,
        workspace_id=role.workspace_id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        kind=role.kind.value,
        category=role.category.value if hasattr(role, "category") else "functional",
        status=role.status.value,
        is_default=role.is_default,
        is_immutable=role.is_immutable,
        is_managed=getattr(role, "is_managed", False),
        assignable_to_users=getattr(role, "assignable_to_users", True),
        resource_type=getattr(role, "resource_type", None),
        resource_id=getattr(role, "resource_id", None),
        member_count=member_count,
        permissions=permissions,
        inherited_role_ids=inherited_role_ids or [],
        inheriting_role_ids=inheriting_role_ids or [],
    )


@router.get("/permissions", response_model=list[PermissionDefinitionOut])
async def list_permission_definitions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionDefinitionOut]:
    await require_permission(db, user, P.ROLE_PERMISSIONS_READ)
    return [
        PermissionDefinitionOut(
            key=p.key,
            label=p.label,
            description=p.description,
            category=p.category,
            resource_type=getattr(p, "resource", p.key.split(".")[0]),
            supported_scopes=list(p.supported_scopes),
            sensitive=p.sensitive,
            assignable_to_custom_roles=p.assignable_to_custom_roles,
            delegable=p.delegable,
            dependencies=list(p.dependencies),
            conflicts=list(p.conflicts),
            inheritable_from_resource_types=list(getattr(p, "inheritable_from_resource_types", ())),
            propagates_to_resource_types=list(getattr(p, "propagates_to_resource_types", ())),
        )
        for p in PERMISSIONS
        if p.assignable_to_custom_roles
    ]


@router.get("/roles", response_model=list[RoleOut])
async def list_roles_route(
    workspace_id: UUID | None = None,
    category: str | None = None,
    kind: str | None = None,
    assignable_to_users: bool | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RoleOut]:
    await require_permission(db, user, P.ROLE_LIST)
    roles = await list_roles(
        db,
        workspace_id=workspace_id,
        category=category,
        kind=kind,
        assignable_to_users=assignable_to_users,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    out: list[RoleOut] = []
    for role in roles:
        perms = await db.execute(
            select(AuthRolePermission).where(AuthRolePermission.role_id == role.id)
        )
        perm_out = [
            RolePermissionOut(
                permission_key=row.permission_key,
                effect=row.effect.value,
                scope=row.scope.value,
                resource_type=row.resource_type,
                resource_ids=[str(x) for x in (row.resource_ids or [])],
            )
            for row in perms.scalars().all()
        ]
        out.append(
            _role_out(role, member_count=await count_role_members(db, role.id), permissions=perm_out)
        )
    return out


@router.get("/roles/{role_id}", response_model=RoleOut)
async def get_role_route(
    role_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoleOut:
    await require_permission(db, user, P.ROLE_READ)
    role = await get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    perms = await db.execute(select(AuthRolePermission).where(AuthRolePermission.role_id == role.id))
    perm_out = [
        RolePermissionOut(
            permission_key=row.permission_key,
            effect=row.effect.value,
            scope=row.scope.value,
            resource_type=row.resource_type,
            resource_ids=[str(x) for x in (row.resource_ids or [])],
        )
        for row in perms.scalars().all()
    ]
    from app.authorization.services.role_inheritance_service import (
        list_inherited_role_ids,
        list_inheriting_role_ids,
    )

    inherited = await list_inherited_role_ids(db, role.id)
    inheriting = await list_inheriting_role_ids(db, role.id)
    return _role_out(
        role,
        member_count=await count_role_members(db, role.id),
        permissions=perm_out,
        inherited_role_ids=inherited,
        inheriting_role_ids=inheriting,
    )


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role_route(
    payload: RoleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoleOut:
    try:
        await require_permission(db, user, P.ROLE_CREATE)
    except AuthorizationError as exc:
        raise forbidden_response(exc) from exc
    rows = [(p.permission_key, p.effect, p.scope) for p in payload.permissions]
    try:
        role = await create_custom_role(
            db,
            actor=user,
            name=payload.name,
            description=payload.description,
            workspace_id=payload.workspace_id,
            permission_rows=rows,
            parent_role_ids=payload.parent_role_ids,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await get_role_route(role.id, user, db)


@router.post("/roles/{role_id}/archive", response_model=RoleOut)
async def archive_role_route(
    role_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoleOut:
    await require_permission(db, user, P.ROLE_ARCHIVE)
    try:
        role = await archive_role(db, user, role_id)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await get_role_route(role.id, user, db)


@router.post("/users/{target_user_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_user_role(
    target_user_id: UUID,
    payload: AssignRoleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(db, user, P.USER_ROLES_ASSIGN)
    try:
        await assign_role_to_user(
            db,
            actor=user,
            target_user_id=target_user_id,
            role_id=payload.role_id,
            workspace_id=payload.workspace_id,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "assigned"}


@router.get("/users/{target_user_id}/roles")
async def list_user_roles(
    target_user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await require_permission(db, user, P.USER_ROLES_READ)
    rows = await db.execute(
        select(AuthUserRoleAssignment, AuthRole)
        .join(AuthRole, AuthRole.id == AuthUserRoleAssignment.role_id)
        .where(AuthUserRoleAssignment.user_id == target_user_id)
    )
    return [
        {
            "assignment_id": str(assignment.id),
            "role_id": str(role.id),
            "role_name": role.name,
            "kind": role.kind.value,
            "workspace_id": str(assignment.workspace_id) if assignment.workspace_id else None,
        }
        for assignment, role in rows.all()
    ]


@router.post("/check", response_model=AuthorizationCheckResponse)
async def check_authorization(
    payload: AuthorizationCheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthorizationCheckResponse:
    ctx = AuthorizationContext(
        workspace_id=payload.workspace_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    decision = await authorize(db, user, payload.permission, ctx)
    return AuthorizationCheckResponse(allowed=decision.allowed, decision=decision.to_dict())


@router.get("/me/permissions")
async def my_effective_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.models.authorization import AuthRole, AuthUserRoleAssignment

    assignments = await db.execute(
        select(AuthUserRoleAssignment, AuthRole)
        .join(AuthRole, AuthRole.id == AuthUserRoleAssignment.role_id)
        .where(AuthUserRoleAssignment.user_id == user.id)
    )
    roles = [
        {
            "role_id": str(role.id),
            "name": role.name,
            "category": role.category.value,
            "workspace_id": str(a.workspace_id) if a.workspace_id else None,
        }
        for a, role in assignments.all()
    ]
    keys = [p.key for p in PERMISSIONS]
    allowed = []
    for key in keys:
        if await authorize(db, user, key).allowed:
            allowed.append(key)
    return {
        "user_id": str(user.id),
        "roles": roles,
        "permissions": allowed,
        "grants_count": len(allowed),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "version": "layered-rbac-v1",
    }


@router.get("/metrics")
async def authorization_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, float | int]:
    await require_permission(db, user, P.AUDIT_READ)
    return get_authorization_metrics()


class ExplainAuthorizationRequest(BaseModel):
    user_id: UUID
    permission: str
    workspace_id: UUID | None = None
    resource_type: str | None = None
    resource_id: str | None = None


@router.post("/explain")
async def explain_authorization(
    payload: ExplainAuthorizationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await require_permission(db, user, P.AUTHORIZATION_EXPLAIN)
    target = await db.get(User, payload.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ctx = AuthorizationContext(
        workspace_id=payload.workspace_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    decision = await authorize(db, target, payload.permission, ctx)
    ancestry = None
    if payload.resource_type and payload.resource_id:
        from app.authorization.services.resource_ancestry_service import resolve_resource_ancestry

        ancestry = await resolve_resource_ancestry(
            db, payload.resource_type, UUID(payload.resource_id)
        )
    return {
        "decision": decision.to_dict(),
        "ancestry": {
            "workspace_id": str(ancestry.workspace_id) if ancestry else None,
            "ancestors": [
                {"resource_type": a.resource_type, "resource_id": str(a.resource_id)}
                for a in (ancestry.ancestors if ancestry else [])
            ],
        },
    }


class BatchAuthorizationCheck(BaseModel):
    checks: list[AuthorizationCheckRequest]


@router.post("/check-batch")
async def check_authorization_batch(
    payload: BatchAuthorizationCheck,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    results = []
    for check in payload.checks:
        ctx = AuthorizationContext(
            workspace_id=check.workspace_id,
            resource_type=check.resource_type,
            resource_id=check.resource_id,
        )
        decision = await authorize(db, user, check.permission, ctx)
        results.append({"permission": check.permission, "decision": decision.to_dict()})
    return {"results": results, "evaluated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/roles/{role_id}/inheritance")
async def get_role_inheritance(
    role_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await require_permission(db, user, P.ROLE_READ)
    from app.authorization.services.role_inheritance_service import (
        list_inherited_role_ids,
        list_inheriting_role_ids,
    )

    return {
        "role_id": str(role_id),
        "inherited_role_ids": [str(x) for x in await list_inherited_role_ids(db, role_id)],
        "inheriting_role_ids": [str(x) for x in await list_inheriting_role_ids(db, role_id)],
    }


class InheritedRolesRequest(BaseModel):
    inherited_role_ids: list[UUID] = Field(default_factory=list)


@router.post("/roles/{role_id}/inherited-roles")
async def add_inherited_roles(
    role_id: UUID,
    payload: InheritedRolesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(db, user, P.ROLE_INHERITANCE_MANAGE)
    from app.authorization.services.role_inheritance_service import validate_role_inheritance_change
    from app.models.authorization import AuthRoleInheritance

    for parent_id in payload.inherited_role_ids:
        result = await validate_role_inheritance_change(
            db, parent_role_id=parent_id, child_role_id=role_id
        )
        if not result.valid:
            raise HTTPException(status_code=400, detail="; ".join(result.errors))
        db.add(AuthRoleInheritance(child_role_id=role_id, parent_role_id=parent_id))
    await db.commit()
    return {"status": "updated"}


@router.delete("/roles/{role_id}/inherited-roles/{inherited_role_id}")
async def remove_inherited_role(
    role_id: UUID,
    inherited_role_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(db, user, P.ROLE_INHERITANCE_MANAGE)
    from sqlalchemy import delete
    from app.models.authorization import AuthRoleInheritance

    await db.execute(
        delete(AuthRoleInheritance).where(
            AuthRoleInheritance.child_role_id == role_id,
            AuthRoleInheritance.parent_role_id == inherited_role_id,
        )
    )
    await db.commit()
    return {"status": "removed"}


class UserOverrideCreate(BaseModel):
    permission_key: str
    effect: Literal["allow", "deny"]
    scope: str
    workspace_id: UUID | None = None
    resource_type: str | None = None
    resource_ids: list[str] = Field(default_factory=list)
    reason: str
    valid_until: datetime | None = None


@router.get("/users/{target_user_id}/overrides")
async def list_user_overrides(
    target_user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await require_permission(db, user, P.USER_PERMISSIONS_GRANT)
    from app.models.authorization import AuthUserPermissionOverride

    rows = (
        await db.execute(
            select(AuthUserPermissionOverride).where(
                AuthUserPermissionOverride.user_id == target_user_id
            )
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "permission_key": r.permission_key,
            "effect": r.effect.value,
            "scope": r.scope.value,
            "workspace_id": str(r.workspace_id) if r.workspace_id else None,
            "reason": r.reason,
        }
        for r in rows
    ]


@router.post("/users/{target_user_id}/overrides", status_code=status.HTTP_201_CREATED)
async def create_user_override(
    target_user_id: UUID,
    payload: UserOverrideCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(db, user, P.USER_PERMISSIONS_GRANT)
    from app.models.authorization import AuthUserPermissionOverride, PermissionEffect, PermissionScope
    from app.authorization.services.authorization_service import invalidate_user_cache

    row = AuthUserPermissionOverride(
        user_id=target_user_id,
        permission_key=payload.permission_key,
        effect=PermissionEffect(payload.effect),
        scope=PermissionScope(payload.scope),
        workspace_id=payload.workspace_id,
        resource_type=payload.resource_type,
        resource_ids=payload.resource_ids,
        reason=payload.reason,
        valid_until=payload.valid_until,
        created_by=user.id,
    )
    db.add(row)
    invalidate_user_cache(target_user_id)
    await db.commit()
    return {"status": "created", "id": str(row.id)}


@router.delete("/users/{target_user_id}/overrides/{override_id}")
async def delete_user_override(
    target_user_id: UUID,
    override_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(db, user, P.USER_PERMISSIONS_GRANT)
    from sqlalchemy import delete
    from app.models.authorization import AuthUserPermissionOverride
    from app.authorization.services.authorization_service import invalidate_user_cache

    await db.execute(
        delete(AuthUserPermissionOverride).where(
            AuthUserPermissionOverride.id == override_id,
            AuthUserPermissionOverride.user_id == target_user_id,
        )
    )
    invalidate_user_cache(target_user_id)
    await db.commit()
    return {"status": "deleted"}


@router.get("/gatherings/{gathering_id}/settings")
async def get_gathering_auth_settings(
    gathering_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await require_permission(
        db, user, P.WORKSPACE_READ, AuthorizationContext(workspace_id=gathering_id)
    )
    from app.models.authorization import AuthGatheringAuthorizationSettings

    row = await db.get(AuthGatheringAuthorizationSettings, gathering_id)
    if not row:
        return {"gathering_id": str(gathering_id), "access_mode": "owner_managed"}
    return {
        "gathering_id": str(gathering_id),
        "access_mode": row.access_mode.value,
        "access_manager_role_ids": row.access_manager_role_ids,
        "future_grants_enabled": row.future_grants_enabled,
    }


class GatheringAuthSettingsPatch(BaseModel):
    access_mode: Literal["owner_managed", "centrally_managed"] | None = None
    future_grants_enabled: bool | None = None


@router.patch("/gatherings/{gathering_id}/settings")
async def patch_gathering_auth_settings(
    gathering_id: UUID,
    payload: GatheringAuthSettingsPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await require_permission(
        db, user, P.AGENT_ACCESS_MANAGE, AuthorizationContext(workspace_id=gathering_id)
    )
    from app.models.authorization import AuthGatheringAuthorizationSettings, GatheringAccessMode

    row = await db.get(AuthGatheringAuthorizationSettings, gathering_id)
    if row is None:
        row = AuthGatheringAuthorizationSettings(gathering_id=gathering_id)
        db.add(row)
    if payload.access_mode:
        row.access_mode = GatheringAccessMode(payload.access_mode)
    if payload.future_grants_enabled is not None:
        row.future_grants_enabled = payload.future_grants_enabled
    row.updated_by_user_id = user.id
    await db.commit()
    return await get_gathering_auth_settings(gathering_id, user, db)


@router.get("/gatherings/{gathering_id}/future-grants")
async def list_gathering_future_grants(
    gathering_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await require_permission(
        db, user, P.AGENT_ACCESS_READ, AuthorizationContext(workspace_id=gathering_id)
    )
    from app.authorization.services.future_grant_service import list_future_grants

    rows = await list_future_grants(db, gathering_id)
    return [
        {
            "id": str(r.id),
            "role_id": str(r.role_id),
            "resource_type": r.resource_type,
            "permission_key": r.permission_key,
            "conditions": r.conditions,
        }
        for r in rows
    ]


class FutureGrantCreate(BaseModel):
    role_id: UUID
    resource_type: str
    permission_key: str
    conditions: dict | None = None


@router.post("/gatherings/{gathering_id}/future-grants", status_code=status.HTTP_201_CREATED)
async def create_gathering_future_grant(
    gathering_id: UUID,
    payload: FutureGrantCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(
        db, user, P.AGENT_ACCESS_MANAGE, AuthorizationContext(workspace_id=gathering_id)
    )
    from app.authorization.services.future_grant_service import create_future_grant

    row = await create_future_grant(
        db,
        actor_user_id=user.id,
        role_id=payload.role_id,
        workspace_id=gathering_id,
        resource_type=payload.resource_type,
        permission_key=payload.permission_key,
        conditions=payload.conditions,
    )
    await db.commit()
    return {"id": str(row.id)}


@router.get("/agents/{agent_id}/access")
async def get_agent_access(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await require_permission(
        db,
        user,
        P.AGENT_ACCESS_READ,
        AuthorizationContext(resource_type="agent", resource_id=agent_id),
    )
    from app.authorization.services.ownership_service import get_ownership
    from app.models import Agent

    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    ownership = await get_ownership(db, "agent", agent_id)
    return {
        "agent_id": str(agent_id),
        "responsible_user_id": str(agent.owner_user_id) if agent.owner_user_id else None,
        "ownership": {
            "owner_role_id": str(ownership.owner_role_id) if ownership else None,
        },
    }


class OwnershipTransferRequest(BaseModel):
    new_owner_role_id: UUID
    new_responsible_user_id: UUID | None = None
    reason: str | None = None


@router.post("/agents/{agent_id}/ownership")
async def transfer_agent_ownership(
    agent_id: UUID,
    payload: OwnershipTransferRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_permission(
        db,
        user,
        P.AGENT_OWNER_CHANGE,
        AuthorizationContext(resource_type="agent", resource_id=agent_id),
    )
    from app.authorization.services.ownership_service import transfer_ownership
    from app.models import Agent

    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if payload.new_responsible_user_id:
        agent.owner_user_id = payload.new_responsible_user_id
    await transfer_ownership(
        db,
        actor_user_id=user.id,
        resource_type="agent",
        resource_id=agent_id,
        new_owner_role_id=payload.new_owner_role_id,
        new_responsible_user_id=payload.new_responsible_user_id or agent.owner_user_id,
        reason=payload.reason,
    )
    await db.commit()
    return {"status": "transferred"}
