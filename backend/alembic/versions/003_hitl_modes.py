"""HITL oversight modes: event types, action_policies, policy_change_events."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_hitl_modes"
down_revision: Union[str, None] = "002_phase2_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Native PG enums cannot ADD VALUE inside a normal transaction on older patterns;
    # autocommit_block is the supported Alembic approach.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE event_type ADD VALUE IF NOT EXISTS 'plan_proposed'")
        op.execute("ALTER TYPE event_type ADD VALUE IF NOT EXISTS 'plan_approved'")
        op.execute("ALTER TYPE event_type ADD VALUE IF NOT EXISTS 'plan_denied'")
        op.execute("ALTER TYPE event_type ADD VALUE IF NOT EXISTS 'action_executed'")

    op.execute(
        "CREATE TYPE action_policy_mode AS ENUM "
        "('step_by_step', 'confidence_gated', 'plan_then_execute')"
    )
    action_policy_mode = postgresql.ENUM(
        "step_by_step",
        "confidence_gated",
        "plan_then_execute",
        name="action_policy_mode",
        create_type=False,
    )

    op.create_table(
        "action_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action_type", sa.String(length=255), nullable=False, unique=True),
        sa.Column("mode", action_policy_mode, nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "policy_change_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action_type", sa.String(length=255), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_policy_change_events_action_type",
        "policy_change_events",
        ["action_type"],
    )

    op.execute(
        """
        INSERT INTO action_policies (id, action_type, mode, config)
        VALUES (
            gen_random_uuid(),
            'process_refund',
            'step_by_step',
            '{}'::jsonb
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_policy_change_events_action_type", table_name="policy_change_events")
    op.drop_table("policy_change_events")
    op.drop_table("action_policies")
    op.execute("DROP TYPE action_policy_mode")
    # Postgres cannot easily remove enum values from event_type; leave them in place.
