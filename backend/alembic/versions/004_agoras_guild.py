"""Users, agoras, guild agent sources, session nature."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_agoras_guild"
down_revision: Union[str, None] = "003_hitl_modes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE session_nature AS ENUM ('training', 'multi_agent')"
    )
    op.execute(
        "CREATE TYPE agent_source AS ENUM ('local', 'downloaded', 'directory')"
    )
    op.execute(
        "CREATE TYPE agora_member_role AS ENUM ('owner', 'member')"
    )

    session_nature = postgresql.ENUM(
        "training", "multi_agent", name="session_nature", create_type=False
    )
    agent_source = postgresql.ENUM(
        "local", "downloaded", "directory", name="agent_source", create_type=False
    )
    agora_member_role = postgresql.ENUM(
        "owner", "member", name="agora_member_role", create_type=False
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "agoras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "agora_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agora_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agoras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("invited_email", sa.String(length=320), nullable=True),
        sa.Column("role", agora_member_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.add_column(
        "agents",
        sa.Column("source", agent_source, nullable=False, server_default="directory"),
    )
    op.add_column(
        "agents",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "agents",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "agent_downloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "agent_id", name="uq_agent_downloads_user_agent"),
    )

    op.create_table(
        "agora_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agora_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agoras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("agora_id", "agent_id", name="uq_agora_agents_agora_agent"),
    )

    op.add_column(
        "sessions",
        sa.Column("nature", session_nature, nullable=False, server_default="multi_agent"),
    )
    op.add_column(
        "sessions",
        sa.Column("agora_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agoras.id", ondelete="SET NULL"), nullable=True),
    )

    # Seeded registry agents appear in the public directory
    op.execute("UPDATE agents SET is_public = true, source = 'directory'")


def downgrade() -> None:
    op.drop_column("sessions", "agora_id")
    op.drop_column("sessions", "nature")
    op.drop_table("agora_agents")
    op.drop_table("agent_downloads")
    op.drop_column("agents", "owner_user_id")
    op.drop_column("agents", "is_public")
    op.drop_column("agents", "source")
    op.drop_table("agora_members")
    op.drop_table("agoras")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE agora_member_role")
    op.execute("DROP TYPE agent_source")
    op.execute("DROP TYPE session_nature")
