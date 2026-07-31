"""Initial schema."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

org_tag = postgresql.ENUM("Internal", "External", name="org_tag", create_type=False)
hosting_mode = postgresql.ENUM("hosted", "remote_mcp", name="hosting_mode", create_type=False)
session_status = postgresql.ENUM("active", "paused", "completed", name="session_status", create_type=False)
participant_kind = postgresql.ENUM(
    "human", "internal_agent", "external_agent", name="participant_kind", create_type=False
)
event_type = postgresql.ENUM(
    "message",
    "action_pending",
    "action_approved",
    "action_denied",
    "redirect",
    "handoff",
    "agent_attached",
    "agent_detached",
    name="event_type",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE org_tag AS ENUM ('Internal', 'External')")
    op.execute("CREATE TYPE hosting_mode AS ENUM ('hosted', 'remote_mcp')")
    op.execute("CREATE TYPE session_status AS ENUM ('active', 'paused', 'completed')")
    op.execute(
        "CREATE TYPE participant_kind AS ENUM ('human', 'internal_agent', 'external_agent')"
    )
    op.execute(
        "CREATE TYPE event_type AS ENUM ("
        "'message', 'action_pending', 'action_approved', 'action_denied', "
        "'redirect', 'handoff', 'agent_attached', 'agent_detached')"
    )

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("agent_key", sa.String(255), nullable=False, unique=True),
        sa.Column("org_tag", org_tag, nullable=False),
        sa.Column("hosting_mode", hosting_mode, nullable=False),
        sa.Column("endpoint_url", sa.String(1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", session_status, nullable=False, server_default="active"),
        sa.Column("active_participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", participant_kind, nullable=False),
        sa.Column("org_tag", org_tag, nullable=False),
        sa.Column("hosting_mode", hosting_mode, nullable=True),
        sa.Column("endpoint_url", sa.String(1024), nullable=True),
        sa.Column("agent_key", sa.String(255), nullable=True),
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", event_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("sequence", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("participants")
    op.drop_table("sessions")
    op.drop_table("agents")
    op.execute("DROP TYPE event_type")
    op.execute("DROP TYPE participant_kind")
    op.execute("DROP TYPE session_status")
    op.execute("DROP TYPE hosting_mode")
    op.execute("DROP TYPE org_tag")
