"""Role inheritance graph validation.

Semantics: parent_role_id receives all privileges of child_role_id.
Storage: AuthRoleInheritance(child_role_id, parent_role_id) means the child role
inherits from the parent (evaluator expands assigned child -> includes parents).
API field inherited_role_ids lists parent roles whose privileges are received.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authorization import AuthRole, AuthRoleCategory, AuthRoleInheritance, AuthRoleStatus


@dataclass
class RoleInheritanceValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    cycles: list[list[UUID]] = field(default_factory=list)


async def _expand_parents(db: AsyncSession, role_id: UUID) -> set[UUID]:
    expanded = {role_id}
    queue = [role_id]
    while queue:
        child = queue.pop()
        rows = await db.execute(
            select(AuthRoleInheritance.parent_role_id).where(
                AuthRoleInheritance.child_role_id == child
            )
        )
        for (parent_id,) in rows.all():
            if parent_id not in expanded:
                expanded.add(parent_id)
                queue.append(parent_id)
    return expanded


async def validate_role_inheritance_change(
    db: AsyncSession,
    *,
    parent_role_id: UUID,
    child_role_id: UUID,
) -> RoleInheritanceValidationResult:
    errors: list[str] = []
    if parent_role_id == child_role_id:
        return RoleInheritanceValidationResult(valid=False, errors=["Self-inheritance is not allowed"])

    parent = await db.get(AuthRole, parent_role_id)
    child = await db.get(AuthRole, child_role_id)
    if not parent or not child:
        return RoleInheritanceValidationResult(valid=False, errors=["Role not found"])
    if parent.status != AuthRoleStatus.active or child.status != AuthRoleStatus.active:
        errors.append("Archived or deprecated roles cannot participate in inheritance")

    # Category rules (simplified)
    if child.category == AuthRoleCategory.baseline:
        errors.append("Baseline roles may not inherit arbitrary roles")
    if child.category == AuthRoleCategory.gathering_access and parent.category == AuthRoleCategory.gathering_access:
        if parent.workspace_id != child.workspace_id:
            errors.append("Gathering access roles cannot inherit across Gatherings")
    if child.category == AuthRoleCategory.resource_access and parent.category == AuthRoleCategory.functional:
        errors.append("Resource access roles cannot inherit functional roles")

    # Cycle: if child already reaches parent, adding parent as inherited by child creates cycle
    # New edge: child inherits parent (child_role_id=child, parent_role_id=parent in storage)
    # Evaluator: assigned child expands to parents. Adding (child, parent) means child gets parent's perms.
    # Cycle if parent expands to child
    parent_closure = await _expand_parents(db, parent_role_id)
    if child_role_id in parent_closure:
        errors.append("Inheritance cycle detected")

    return RoleInheritanceValidationResult(valid=not errors, errors=errors)


async def list_inherited_role_ids(db: AsyncSession, role_id: UUID) -> list[UUID]:
    """Parent role IDs this role inherits (receives privileges from)."""
    rows = await db.execute(
        select(AuthRoleInheritance.parent_role_id).where(AuthRoleInheritance.child_role_id == role_id)
    )
    return [r[0] for r in rows.all()]


async def list_inheriting_role_ids(db: AsyncSession, role_id: UUID) -> list[UUID]:
    """Child role IDs that inherit this role."""
    rows = await db.execute(
        select(AuthRoleInheritance.child_role_id).where(AuthRoleInheritance.parent_role_id == role_id)
    )
    return [r[0] for r in rows.all()]
