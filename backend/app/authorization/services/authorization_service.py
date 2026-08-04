"""Authorization evaluation, caching, and metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.permissions.registry import PERMISSION_BY_KEY, P
from app.authorization.permissions.aliases import resolve_permission_keys
from app.models import Agent, AgentDownload, GatheringMember, User
from app.models.authorization import (
    AuthRole,
    AuthRoleCategory,
    AuthRoleInheritance,
    AuthRolePermission,
    AuthRoleStatus,
    AuthUserPermissionOverride,
    AuthUserRoleAssignment,
    PermissionEffect,
    PermissionScope,
)
from app.authorization.services.resource_ancestry_service import resolve_resource_ancestry

# Simple in-process metrics (safe for single-worker dev; swap for Redis in production).
_METRICS: dict[str, float | int] = {
    "checks_total": 0,
    "allows_total": 0,
    "denies_total": 0,
    "cache_hits": 0,
    "cache_invalidations": 0,
}

# user_id -> (version, cached rules snapshot) — invalidated on assignment changes.
_USER_CACHE: dict[str, tuple[int, list["_Rule"]]] = {}
_CACHE_VERSION = 0


def invalidate_user_cache(user_id: UUID | None = None) -> None:
    global _CACHE_VERSION
    _CACHE_VERSION += 1
    _METRICS["cache_invalidations"] = int(_METRICS["cache_invalidations"]) + 1
    if user_id is None:
        _USER_CACHE.clear()
    else:
        _USER_CACHE.pop(str(user_id), None)


_CACHE_TTL_SECONDS = 120.0
_USER_CACHE_META: dict[str, tuple[int, float]] = {}


@dataclass
class _Rule:
    source: str
    source_id: str
    permission_key: str
    effect: PermissionEffect
    scope: PermissionScope
    workspace_id: UUID | None
    resource_type: str | None
    resource_ids: set[str]
    priority: int
    role_category: str | None = None
    role_workspace_id: UUID | None = None
    grant_source: str | None = None


@dataclass
class AuthorizationContext:
    workspace_id: UUID | None = None
    resource_type: str | None = None
    resource_id: UUID | str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationDecision:
    allowed: bool
    permission: str
    effect: str
    reason: str
    matched_role_ids: list[str] = field(default_factory=list)
    matched_rule_ids: list[str] = field(default_factory=list)
    scope: str | None = None
    evaluated_at: str = ""
    grant_source: str | None = None
    inheritance_path: list[str] = field(default_factory=list)
    workspace_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "permission": self.permission,
            "effect": self.effect,
            "reason": self.reason,
            "matched_role_ids": self.matched_role_ids,
            "matched_rule_ids": self.matched_rule_ids,
            "scope": self.scope,
            "evaluated_at": self.evaluated_at,
            "grant_source": self.grant_source,
            "inheritance_path": self.inheritance_path,
            "workspace_id": self.workspace_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
        }


class AuthorizationError(Exception):
    def __init__(
        self,
        permission: str,
        message: str = "Permission denied",
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.permission = permission
        self.resource_type = resource_type
        self.resource_id = resource_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assignment_active(row: AuthUserRoleAssignment) -> bool:
    now = _now()
    if row.valid_from and row.valid_from > now:
        return False
    if row.valid_until and row.valid_until <= now:
        return False
    return True


def _override_active(row: AuthUserPermissionOverride) -> bool:
    now = _now()
    if row.valid_from and row.valid_from > now:
        return False
    if row.valid_until and row.valid_until <= now:
        return False
    return True


async def _expand_role_ids(db: AsyncSession, role_ids: set[UUID]) -> set[UUID]:
    expanded = set(role_ids)
    queue = list(role_ids)
    while queue:
        child = queue.pop()
        parents = await db.execute(
            select(AuthRoleInheritance.parent_role_id).where(
                AuthRoleInheritance.child_role_id == child
            )
        )
        for (parent_id,) in parents.all():
            if parent_id not in expanded:
                expanded.add(parent_id)
                queue.append(parent_id)
    return expanded


async def _user_is_gathering_member(db: AsyncSession, user_id: UUID, workspace_id: UUID) -> bool:
    row = await db.execute(
        select(GatheringMember.id).where(
            GatheringMember.gathering_id == workspace_id,
            GatheringMember.user_id == user_id,
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def _load_rules(db: AsyncSession, user_id: UUID) -> list[_Rule]:
    from app.authorization.session_context import get_session_assignment_id

    session_assignment_id = get_session_assignment_id()
    cache_key = f"{user_id}:{session_assignment_id or 'none'}"
    cached = _USER_CACHE.get(cache_key)
    meta = _USER_CACHE_META.get(cache_key)
    now_ts = time.time()
    if cached and cached[0] == _CACHE_VERSION and meta and (now_ts - meta[1]) < _CACHE_TTL_SECONDS:
        _METRICS["cache_hits"] = int(_METRICS["cache_hits"]) + 1
        return cached[1]

    if session_assignment_id:
        assignment = await db.get(AuthUserRoleAssignment, session_assignment_id)
        if (
            assignment
            and assignment.user_id == user_id
            and _assignment_active(assignment)
        ):
            active_assignments = [assignment]
        else:
            active_assignments = []
    else:
        assignments = await db.execute(
            select(AuthUserRoleAssignment).where(AuthUserRoleAssignment.user_id == user_id)
        )
        active_assignments = [a for a in assignments.scalars().all() if _assignment_active(a)]

    role_ids = {a.role_id for a in active_assignments}
    if not role_ids:
        from app.authorization.constants.system_roles import USER_ROLE_ID

        role_ids.add(USER_ROLE_ID)

    roles = await db.execute(
        select(AuthRole).where(
            AuthRole.id.in_(role_ids),
            AuthRole.status.in_((AuthRoleStatus.active, AuthRoleStatus.deprecated)),
        )
    )
    role_by_id = {r.id: r for r in roles.scalars().all()}
    active_role_ids = set(role_by_id.keys())
    expanded_role_ids = await _expand_role_ids(db, active_role_ids)

    extra_roles = await db.execute(
        select(AuthRole).where(
            AuthRole.id.in_(expanded_role_ids - active_role_ids),
            AuthRole.status.in_((AuthRoleStatus.active, AuthRoleStatus.deprecated)),
        )
    )
    for r in extra_roles.scalars().all():
        role_by_id[r.id] = r

    role_perms = await db.execute(
        select(AuthRolePermission).where(AuthRolePermission.role_id.in_(expanded_role_ids))
    )
    overrides = await db.execute(
        select(AuthUserPermissionOverride).where(AuthUserPermissionOverride.user_id == user_id)
    )

    rules = []
    for rp in role_perms.scalars().all():
        role = role_by_id.get(rp.role_id)
        rule_workspace = role.workspace_id if role else None
        if role and role.category == AuthRoleCategory.gathering_access:
            priority = 35
        elif role and role.category == AuthRoleCategory.resource_access:
            priority = 36
        elif role and role.category == AuthRoleCategory.functional:
            priority = 32
        elif role and role.category == AuthRoleCategory.system_admin:
            priority = 31
        else:
            priority = 30
        rules.append(
            _Rule(
                source="role",
                source_id=str(rp.role_id),
                permission_key=rp.permission_key,
                effect=rp.effect,
                scope=rp.scope,
                workspace_id=rule_workspace,
                resource_type=rp.resource_type,
                resource_ids={str(x) for x in (rp.resource_ids or [])},
                priority=priority,
                role_category=role.category.value if role else None,
                role_workspace_id=role.workspace_id if role else None,
                grant_source=rp.grant_source.value if rp.grant_source else "system_role",
            )
        )
    for ov in overrides.scalars().all():
        if not _override_active(ov):
            continue
        rules.append(
            _Rule(
                source="override",
                source_id=str(ov.id),
                permission_key=ov.permission_key,
                effect=ov.effect,
                scope=ov.scope,
                workspace_id=ov.workspace_id,
                resource_type=ov.resource_type,
                resource_ids={str(x) for x in (ov.resource_ids or [])},
                priority=50 if ov.effect == PermissionEffect.deny else 40,
            )
        )

    _USER_CACHE[cache_key] = (_CACHE_VERSION, rules)
    _USER_CACHE_META[cache_key] = (_CACHE_VERSION, now_ts)
    return rules


def _permission_matches_rule(rule: _Rule, permission: str) -> bool:
    for key in resolve_permission_keys(permission):
        if rule.permission_key == key:
            return True
        if rule.permission_key.endswith(".*"):
            prefix = rule.permission_key[:-1]
            if key.startswith(prefix):
                return True
    return False


async def agent_is_accessible(db: AsyncSession, user: User, agent: Agent) -> bool:
    if agent.owner_user_id == user.id:
        return True
    if agent.is_public and agent.is_active:
        return True
    dl = await db.execute(
        select(AgentDownload.id).where(
            AgentDownload.user_id == user.id, AgentDownload.agent_id == agent.id
        )
    )
    return dl.scalar_one_or_none() is not None


def _permission_matches(rule: _Rule, permission: str) -> bool:
    return _permission_matches_rule(rule, permission)


async def _scope_matches(
    db: AsyncSession,
    rule: _Rule,
    *,
    user: User,
    agent: Agent | None,
    workspace_id: UUID | None,
    resource_type: str | None,
    resource_id: str | None,
    ancestry_workspace_id: UUID | None,
) -> bool:
    if rule.role_category == AuthRoleCategory.gathering_access.value and rule.role_workspace_id:
        if workspace_id and rule.role_workspace_id != workspace_id:
            if not ancestry_workspace_id or ancestry_workspace_id != rule.role_workspace_id:
                return False
        if rule.role_category == AuthRoleCategory.gathering_access.value and workspace_id is None:
            if ancestry_workspace_id != rule.role_workspace_id:
                return False

    if rule.scope == PermissionScope.system:
        return True
    if rule.scope == PermissionScope.workspace:
        effective_ws = workspace_id or ancestry_workspace_id
        if effective_ws is None:
            return False
        if rule.workspace_id and rule.workspace_id != effective_ws:
            return False
        if not await _user_is_gathering_member(db, user.id, effective_ws):
            return False
        return True
    if rule.scope == PermissionScope.owned:
        if agent is not None and agent.owner_user_id == user.id:
            return True
        if resource_type and resource_id:
            from app.models.authorization import AuthResourceOwnership
            from uuid import UUID as _UUID

            try:
                rid = _UUID(str(resource_id))
            except ValueError:
                return False
            row = await db.execute(
                select(AuthResourceOwnership.responsible_user_id).where(
                    AuthResourceOwnership.resource_type == (resource_type or "agent"),
                    AuthResourceOwnership.resource_id == rid,
                )
            )
            responsible = row.scalar_one_or_none()
            if responsible == user.id:
                return True
        return False
    if rule.scope == PermissionScope.resource:
        if not resource_id:
            return False
        if rule.resource_ids and str(resource_id) not in rule.resource_ids:
            return False
        if rule.resource_type and resource_type and rule.resource_type != resource_type:
            return False
        return True
    if rule.scope == PermissionScope.assigned:
        if rule.resource_ids and resource_id and str(resource_id) in rule.resource_ids:
            return True
        return False
    return False


async def authorize(
    db: AsyncSession,
    user: User,
    permission: str,
    ctx: AuthorizationContext | None = None,
) -> AuthorizationDecision:
    start = time.perf_counter()
    _METRICS["checks_total"] = int(_METRICS["checks_total"]) + 1
    ctx = ctx or AuthorizationContext()
    evaluated_at = _now().isoformat()

    from app.authorization.permissions.aliases import PERMISSION_ALIASES

    if permission not in PERMISSION_BY_KEY and permission not in PERMISSION_ALIASES:
        _METRICS["denies_total"] = int(_METRICS["denies_total"]) + 1
        return AuthorizationDecision(
            allowed=False,
            permission=permission,
            effect="deny",
            reason="Unknown permission",
            evaluated_at=evaluated_at,
        )

    if not user.is_active:
        _METRICS["denies_total"] = int(_METRICS["denies_total"]) + 1
        return AuthorizationDecision(
            allowed=False,
            permission=permission,
            effect="deny",
            reason="User account is disabled",
            evaluated_at=evaluated_at,
        )

    # Self-service profile permissions
    if permission in (P.PROFILE_READ_SELF, P.PROFILE_UPDATE_SELF):
        _METRICS["allows_total"] = int(_METRICS["allows_total"]) + 1
        return AuthorizationDecision(
            allowed=True,
            permission=permission,
            effect="allow",
            reason="Authenticated user may access own profile",
            evaluated_at=evaluated_at,
            scope="system",
        )

    agent: Agent | None = None
    resource_id_str: str | None = None
    if ctx.resource_id is not None:
        resource_id_str = str(ctx.resource_id)
    if ctx.resource_type == "agent" and ctx.resource_id:
        agent = await db.get(Agent, UUID(str(ctx.resource_id)))

    ancestry_workspace_id: UUID | None = None
    if ctx.resource_type and ctx.resource_id:
        try:
            ancestry = await resolve_resource_ancestry(
                db, ctx.resource_type, UUID(str(ctx.resource_id))
            )
            ancestry_workspace_id = ancestry.workspace_id
            if ctx.workspace_id is None:
                ctx.workspace_id = ancestry_workspace_id
        except (ValueError, TypeError):
            pass

    # --- Compatibility authorization rules ---
    if permission in (P.AGENT_READ_ACCESSIBLE, P.AGENT_LIST_ACCESSIBLE):
        if permission == P.AGENT_LIST_ACCESSIBLE:
            _METRICS["allows_total"] = int(_METRICS["allows_total"]) + 1
            return AuthorizationDecision(
                allowed=True,
                permission=permission,
                effect="allow",
                reason="Baseline list accessible agents",
                evaluated_at=evaluated_at,
                scope="system",
                grant_source="compatibility_rule",
            )
        if agent and await agent_is_accessible(db, user, agent):
            _METRICS["allows_total"] = int(_METRICS["allows_total"]) + 1
            return AuthorizationDecision(
                allowed=True,
                permission=permission,
                effect="allow",
                reason="Agent is accessible (owner, public, or downloaded)",
                evaluated_at=evaluated_at,
                scope="system",
                grant_source="compatibility_rule",
            )

    rules = await _load_rules(db, user.id)

    matched_allows: list[_Rule] = []
    matched_denies: list[_Rule] = []

    for rule in rules:
        if not _permission_matches(rule, permission):
            continue
        if not await _scope_matches(
            db,
            rule,
            user=user,
            agent=agent,
            workspace_id=ctx.workspace_id,
            resource_type=ctx.resource_type,
            resource_id=resource_id_str,
            ancestry_workspace_id=ancestry_workspace_id,
        ):
            continue
        if rule.effect == PermissionEffect.deny:
            matched_denies.append(rule)
        else:
            matched_allows.append(rule)

    if matched_denies:
        _METRICS["denies_total"] = int(_METRICS["denies_total"]) + 1
        return AuthorizationDecision(
            allowed=False,
            permission=permission,
            effect="deny",
            reason="Explicit deny rule matched",
            matched_role_ids=[r.source_id for r in matched_denies if r.source == "role"],
            matched_rule_ids=[r.source_id for r in matched_denies],
            scope=matched_denies[0].scope.value,
            evaluated_at=evaluated_at,
        )

    if matched_allows:
        best = sorted(matched_allows, key=lambda r: r.priority, reverse=True)[0]
        _METRICS["allows_total"] = int(_METRICS["allows_total"]) + 1
        return AuthorizationDecision(
            allowed=True,
            permission=permission,
            effect="allow",
            reason="Permission granted by role or override",
            matched_role_ids=[best.source_id] if best.source == "role" else [],
            matched_rule_ids=[best.source_id],
            scope=best.scope.value,
            evaluated_at=evaluated_at,
            grant_source=best.grant_source or ("user_override" if best.source == "override" else "system_role"),
            workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
            resource_type=ctx.resource_type,
            resource_id=resource_id_str,
        )

    # agent.read falls back to accessible read for viewable agents
    if permission == P.AGENT_READ and agent and await agent_is_accessible(db, user, agent):
        rules_acc = [r for r in rules if _permission_matches(r, P.AGENT_READ_ACCESSIBLE)]
        if rules_acc:
            _METRICS["allows_total"] = int(_METRICS["allows_total"]) + 1
            return AuthorizationDecision(
                allowed=True,
                permission=permission,
                effect="allow",
                reason="Readable via agent.read_accessible baseline",
                evaluated_at=evaluated_at,
                scope="system",
                grant_source="compatibility_rule",
            )

    _METRICS["denies_total"] = int(_METRICS["denies_total"]) + 1
    _ = time.perf_counter() - start
    return AuthorizationDecision(
        allowed=False,
        permission=permission,
        effect="deny",
        reason="Default deny — no matching allow rule",
        evaluated_at=evaluated_at,
    )


async def can(
    db: AsyncSession,
    user: User,
    permission: str,
    ctx: AuthorizationContext | None = None,
) -> bool:
    decision = await authorize(db, user, permission, ctx)
    return decision.allowed


async def require_permission(
    db: AsyncSession,
    user: User,
    permission: str,
    ctx: AuthorizationContext | None = None,
) -> AuthorizationDecision:
    decision = await authorize(db, user, permission, ctx)
    if not decision.allowed:
        raise AuthorizationError(
            permission,
            decision.reason,
            resource_type=ctx.resource_type if ctx else None,
            resource_id=str(ctx.resource_id) if ctx and ctx.resource_id else None,
        )
    return decision


def get_authorization_metrics() -> dict[str, float | int]:
    return dict(_METRICS)
