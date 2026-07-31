"""Rename Agora→Gathering; add people and agent profile storage."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_gatherings_profiles"
down_revision: Union[str, None] = "004_agoras_guild"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # People profile fields
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("organization", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=1024), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Agent information fields
    op.add_column("agents", sa.Column("version", sa.String(length=64), nullable=True))
    op.add_column(
        "agents",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("agents", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "agents",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Rename agora → gathering tables / columns / enum
    op.execute("ALTER TYPE agora_member_role RENAME TO gathering_member_role")
    op.rename_table("agoras", "gatherings")
    op.rename_table("agora_members", "gathering_members")
    op.rename_table("agora_agents", "gathering_agents")
    op.alter_column("gathering_members", "agora_id", new_column_name="gathering_id")
    op.alter_column("gathering_agents", "agora_id", new_column_name="gathering_id")
    op.alter_column("sessions", "agora_id", new_column_name="gathering_id")

    # Rename unique constraints if present
    op.execute(
        "ALTER TABLE gathering_agents RENAME CONSTRAINT uq_agora_agents_agora_agent "
        "TO uq_gathering_agents_gathering_agent"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE gathering_agents RENAME CONSTRAINT uq_gathering_agents_gathering_agent "
        "TO uq_agora_agents_agora_agent"
    )
    op.alter_column("sessions", "gathering_id", new_column_name="agora_id")
    op.alter_column("gathering_agents", "gathering_id", new_column_name="agora_id")
    op.alter_column("gathering_members", "gathering_id", new_column_name="agora_id")
    op.rename_table("gathering_agents", "agora_agents")
    op.rename_table("gathering_members", "agora_members")
    op.rename_table("gatherings", "agoras")
    op.execute("ALTER TYPE gathering_member_role RENAME TO agora_member_role")

    op.drop_column("agents", "updated_at")
    op.drop_column("agents", "metadata")
    op.drop_column("agents", "notes")
    op.drop_column("agents", "tags")
    op.drop_column("agents", "version")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "profile")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "title")
    op.drop_column("users", "organization")
    op.drop_column("users", "bio")
