"""Layered RBAC schema extensions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_layered_rbac"
down_revision: Union[str, None] = "007_authorization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New enum values must commit before use (PostgreSQL).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auth_role_status ADD VALUE IF NOT EXISTS 'deprecated'")
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE auth_role_category AS ENUM (
                'baseline', 'system_admin', 'functional', 'gathering_access',
                'resource_access', 'service', 'legacy'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE grant_source AS ENUM (
                'system_seed', 'role_builder', 'resource_access',
                'future_grant', 'migration', 'api'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE gathering_access_mode AS ENUM ('owner_managed', 'centrally_managed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    auth_role_category = postgresql.ENUM(
        "baseline",
        "system_admin",
        "functional",
        "gathering_access",
        "resource_access",
        "service",
        "legacy",
        name="auth_role_category",
        create_type=False,
    )
    grant_source = postgresql.ENUM(
        "system_seed",
        "role_builder",
        "resource_access",
        "future_grant",
        "migration",
        "api",
        name="grant_source",
        create_type=False,
    )
    gathering_access_mode = postgresql.ENUM(
        "owner_managed",
        "centrally_managed",
        name="gathering_access_mode",
        create_type=False,
    )

    op.add_column(
        "auth_roles",
        sa.Column(
            "category",
            auth_role_category,
            nullable=False,
            server_default="functional",
        ),
    )
    op.add_column(
        "auth_roles",
        sa.Column("is_managed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "auth_roles",
        sa.Column(
            "assignable_to_users",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "auth_roles",
        sa.Column("resource_type", sa.String(64), nullable=True),
    )
    op.add_column(
        "auth_roles",
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_auth_roles_category", "auth_roles", ["category"])
    op.create_index("ix_auth_roles_resource", "auth_roles", ["resource_type", "resource_id"])

    op.add_column(
        "auth_role_permissions",
        sa.Column("with_grant_option", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "auth_role_permissions",
        sa.Column("grant_source", grant_source, nullable=True),
    )
    op.add_column(
        "auth_role_permissions",
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "auth_role_permissions",
        sa.Column("granted_by_role_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "auth_role_permissions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    op.create_table(
        "auth_resource_ownership",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "owner_role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_roles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "responsible_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gatherings.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "assigned_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_by_role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("resource_type", "resource_id", name="uq_auth_resource_ownership"),
    )
    op.create_index(
        "ix_auth_resource_ownership_responsible",
        "auth_resource_ownership",
        ["responsible_user_id"],
    )

    op.create_table(
        "auth_gathering_authorization_settings",
        sa.Column(
            "gathering_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gatherings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "access_mode",
            gathering_access_mode,
            nullable=False,
            server_default="owner_managed",
        ),
        sa.Column(
            "access_manager_role_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("future_grants_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    permission_effect = postgresql.ENUM("allow", "deny", name="permission_effect", create_type=False)
    op.create_table(
        "auth_future_resource_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gatherings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("permission_key", sa.String(128), nullable=False),
        sa.Column("effect", permission_effect, nullable=False, server_default="allow"),
        sa.Column("conditions", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_auth_future_grants_workspace", "auth_future_resource_grants", ["workspace_id"])
    op.create_index("ix_auth_future_grants_resource_type", "auth_future_resource_grants", ["resource_type"])

    # Backfill role categories for existing system roles
    op.execute(
        """
        UPDATE auth_roles SET category = 'baseline', is_managed = true, assignable_to_users = true
        WHERE id = '00000000-0000-4000-8000-000000000001'::uuid
        """
    )
    op.execute(
        """
        UPDATE auth_roles SET category = 'legacy', is_managed = true, assignable_to_users = false
        WHERE id IN (
            '00000000-0000-4000-8000-000000000002'::uuid,
            '00000000-0000-4000-8000-000000000003'::uuid
        )
        """
    )


def downgrade() -> None:
    op.drop_table("auth_future_resource_grants")
    op.drop_table("auth_gathering_authorization_settings")
    op.drop_table("auth_resource_ownership")
    op.drop_column("auth_role_permissions", "updated_at")
    op.drop_column("auth_role_permissions", "granted_by_role_id")
    op.drop_column("auth_role_permissions", "granted_by_user_id")
    op.drop_column("auth_role_permissions", "grant_source")
    op.drop_column("auth_role_permissions", "with_grant_option")
    op.drop_index("ix_auth_roles_resource", table_name="auth_roles")
    op.drop_index("ix_auth_roles_category", table_name="auth_roles")
    op.drop_column("auth_roles", "resource_id")
    op.drop_column("auth_roles", "resource_type")
    op.drop_column("auth_roles", "assignable_to_users")
    op.drop_column("auth_roles", "is_managed")
    op.drop_column("auth_roles", "category")
    op.execute("DROP TYPE IF EXISTS gathering_access_mode")
    op.execute("DROP TYPE IF EXISTS grant_source")
    op.execute("DROP TYPE IF EXISTS auth_role_category")
