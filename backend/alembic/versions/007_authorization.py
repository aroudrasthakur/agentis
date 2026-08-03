"""Role-based access control tables and system role seed."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_authorization"
down_revision: Union[str, None] = "006_agent_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.execute("CREATE TYPE auth_role_kind AS ENUM ('system', 'custom')")
    op.execute("CREATE TYPE auth_role_status AS ENUM ('active', 'archived')")
    op.execute("CREATE TYPE permission_effect AS ENUM ('allow', 'deny')")
    op.execute(
        "CREATE TYPE permission_scope AS ENUM ('system', 'workspace', 'owned', 'assigned', 'resource')"
    )

    auth_role_kind = postgresql.ENUM("system", "custom", name="auth_role_kind", create_type=False)
    auth_role_status = postgresql.ENUM("active", "archived", name="auth_role_status", create_type=False)
    permission_effect = postgresql.ENUM("allow", "deny", name="permission_effect", create_type=False)
    permission_scope = postgresql.ENUM(
        "system",
        "workspace",
        "owned",
        "assigned",
        "resource",
        name="permission_scope",
        create_type=False,
    )

    op.create_table(
        "auth_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("kind", auth_role_kind, nullable=False),
        sa.Column("status", auth_role_status, nullable=False, server_default="active"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_auth_roles_workspace_slug"),
    )
    op.create_index("ix_auth_roles_workspace_id", "auth_roles", ["workspace_id"])
    op.create_index("ix_auth_roles_slug", "auth_roles", ["slug"])
    op.create_index("ix_auth_roles_status", "auth_roles", ["status"])

    op.create_table(
        "auth_role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_key", sa.String(128), nullable=False),
        sa.Column("effect", permission_effect, nullable=False),
        sa.Column("scope", permission_scope, nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("conditions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint(
            "role_id",
            "permission_key",
            "effect",
            "scope",
            "resource_type",
            name="uq_auth_role_perm_row",
        ),
    )
    op.create_index("ix_auth_role_permissions_role_id", "auth_role_permissions", ["role_id"])
    op.create_index("ix_auth_role_permissions_permission_key", "auth_role_permissions", ["permission_key"])

    op.create_table(
        "auth_user_role_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "role_id", "workspace_id", name="uq_auth_user_role_assignment"),
    )
    op.create_index("ix_auth_user_role_assignments_user_id", "auth_user_role_assignments", ["user_id"])
    op.create_index("ix_auth_user_role_assignments_role_id", "auth_user_role_assignments", ["role_id"])
    op.create_index("ix_auth_user_role_assignments_valid_until", "auth_user_role_assignments", ["valid_until"])

    op.create_table(
        "auth_user_permission_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_key", sa.String(128), nullable=False),
        sa.Column("effect", permission_effect, nullable=False),
        sa.Column("scope", permission_scope, nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_auth_user_permission_overrides_user_id", "auth_user_permission_overrides", ["user_id"])

    op.create_table(
        "auth_role_inheritance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("child_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("child_role_id", "parent_role_id", name="uq_auth_role_inheritance"),
    )

    op.create_table(
        "auth_authorization_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("permission_key", sa.String(128), nullable=True),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("previous_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_auth_audit_event_type", "auth_authorization_audit_events", ["event_type"])
    op.create_index("ix_auth_audit_created_at", "auth_authorization_audit_events", ["created_at"])

    # System roles (permissions seeded at app startup via bootstrap for maintainability)
    op.execute(
        """
        INSERT INTO auth_roles (id, name, slug, description, kind, status, is_default, is_immutable)
        VALUES
        ('00000000-0000-4000-8000-000000000001'::uuid, 'USER', 'user', 'Default role for every account.', 'system', 'active', true, true),
        ('00000000-0000-4000-8000-000000000002'::uuid, 'Agent Owner', 'agent-owner', 'Create and manage owned agents.', 'system', 'active', false, true),
        ('00000000-0000-4000-8000-000000000003'::uuid, 'Authorization Admin', 'authorization-admin', 'Manage roles and permissions.', 'system', 'active', false, true)
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO auth_user_role_assignments (id, user_id, role_id)
        SELECT gen_random_uuid(), u.id, r.id
        FROM users u
        CROSS JOIN auth_roles r
        WHERE r.id IN (
            '00000000-0000-4000-8000-000000000001'::uuid,
            '00000000-0000-4000-8000-000000000002'::uuid,
            '00000000-0000-4000-8000-000000000003'::uuid
        )
        AND NOT EXISTS (
            SELECT 1 FROM auth_user_role_assignments a
            WHERE a.user_id = u.id AND a.role_id = r.id AND a.workspace_id IS NULL
        )
        """
    )


def downgrade() -> None:
    op.drop_table("auth_authorization_audit_events")
    op.drop_table("auth_role_inheritance")
    op.drop_table("auth_user_permission_overrides")
    op.drop_table("auth_user_role_assignments")
    op.drop_table("auth_role_permissions")
    op.drop_table("auth_roles")
    op.drop_column("users", "is_active")
    op.execute("DROP TYPE IF EXISTS permission_scope")
    op.execute("DROP TYPE IF EXISTS permission_effect")
    op.execute("DROP TYPE IF EXISTS auth_role_status")
    op.execute("DROP TYPE IF EXISTS auth_role_kind")
