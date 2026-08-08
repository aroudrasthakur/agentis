"""RBAC persistence models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthRoleKind(str, enum.Enum):
    system = "system"
    custom = "custom"


class AuthRoleStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    deprecated = "deprecated"


class AuthRoleCategory(str, enum.Enum):
    baseline = "baseline"
    system_admin = "system_admin"
    functional = "functional"
    gathering_access = "gathering_access"
    resource_access = "resource_access"
    service = "service"
    legacy = "legacy"


class GrantSource(str, enum.Enum):
    system_seed = "system_seed"
    role_builder = "role_builder"
    resource_access = "resource_access"
    future_grant = "future_grant"
    migration = "migration"
    api = "api"


class GatheringAccessMode(str, enum.Enum):
    owner_managed = "owner_managed"
    centrally_managed = "centrally_managed"


class PermissionEffect(str, enum.Enum):
    allow = "allow"
    deny = "deny"


class PermissionScope(str, enum.Enum):
    system = "system"
    workspace = "workspace"
    owned = "owned"
    assigned = "assigned"
    resource = "resource"


auth_role_kind_enum = Enum(
    AuthRoleKind, name="auth_role_kind", values_callable=lambda x: [e.value for e in x]
)
auth_role_status_enum = Enum(
    AuthRoleStatus, name="auth_role_status", values_callable=lambda x: [e.value for e in x]
)
auth_role_category_enum = Enum(
    AuthRoleCategory, name="auth_role_category", values_callable=lambda x: [e.value for e in x]
)
grant_source_enum = Enum(
    GrantSource, name="grant_source", values_callable=lambda x: [e.value for e in x]
)
gathering_access_mode_enum = Enum(
    GatheringAccessMode,
    name="gathering_access_mode",
    values_callable=lambda x: [e.value for e in x],
)
permission_effect_enum = Enum(
    PermissionEffect, name="permission_effect", values_callable=lambda x: [e.value for e in x]
)
permission_scope_enum = Enum(
    PermissionScope, name="permission_scope", values_callable=lambda x: [e.value for e in x]
)


class AuthRole(Base):
    __tablename__ = "auth_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[AuthRoleKind] = mapped_column(auth_role_kind_enum, nullable=False)
    category: Mapped[AuthRoleCategory] = mapped_column(
        auth_role_category_enum, nullable=False, default=AuthRoleCategory.functional, index=True
    )
    status: Mapped[AuthRoleStatus] = mapped_column(
        auth_role_status_enum, default=AuthRoleStatus.active, nullable=False, index=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assignable_to_users: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_auth_roles_workspace_slug"),
    )


class AuthRolePermission(Base):
    __tablename__ = "auth_role_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    effect: Mapped[PermissionEffect] = mapped_column(permission_effect_enum, nullable=False)
    scope: Mapped[PermissionScope] = mapped_column(permission_scope_enum, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resource_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    conditions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    with_grant_option: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    grant_source: Mapped[GrantSource | None] = mapped_column(grant_source_enum, nullable=True)
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "role_id", "permission_key", "effect", "scope", "resource_type",
            name="uq_auth_role_perm_row",
        ),
    )


class AuthUserRoleAssignment(Base):
    __tablename__ = "auth_user_role_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "workspace_id", name="uq_auth_user_role_assignment"),
    )


class AuthUserPermissionOverride(Base):
    __tablename__ = "auth_user_permission_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    effect: Mapped[PermissionEffect] = mapped_column(permission_effect_enum, nullable=False)
    scope: Mapped[PermissionScope] = mapped_column(permission_scope_enum, nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AuthRoleInheritance(Base):
    """Parent role receives all privileges of child role (parent_role_id ← child_role_id)."""

    __tablename__ = "auth_role_inheritance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("child_role_id", "parent_role_id", name="uq_auth_role_inheritance"),
    )


class AuthAuthorizationAuditEvent(Base):
    __tablename__ = "auth_authorization_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    permission_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    previous_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class AuthResourceOwnership(Base):
    __tablename__ = "auth_resource_ownership"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="RESTRICT"), nullable=False
    )
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("resource_type", "resource_id", name="uq_auth_resource_ownership"),
    )


class AuthGatheringAuthorizationSettings(Base):
    __tablename__ = "auth_gathering_authorization_settings"

    gathering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gatherings.id", ondelete="CASCADE"), primary_key=True
    )
    access_mode: Mapped[GatheringAccessMode] = mapped_column(
        gathering_access_mode_enum,
        nullable=False,
        default=GatheringAccessMode.owner_managed,
    )
    access_manager_role_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    future_grants_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AuthFutureResourceGrant(Base):
    __tablename__ = "auth_future_resource_grants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    permission_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    effect: Mapped[PermissionEffect] = mapped_column(
        permission_effect_enum, nullable=False, default=PermissionEffect.allow
    )
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="SET NULL"), nullable=True
    )
