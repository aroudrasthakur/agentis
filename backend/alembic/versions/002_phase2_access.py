"""Phase 2: capabilities, access tokens, session invites."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_phase2_access"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("sessions", sa.Column("invite_jti", sa.String(length=64), nullable=True))
    op.add_column("sessions", sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("participants", sa.Column("access_token", sa.Text(), nullable=True))
    op.add_column(
        "participants",
        sa.Column("granted_capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("participants", sa.Column("token_jti", sa.String(length=64), nullable=True))
    op.add_column("participants", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("participants", sa.Column("token_revoked_at", sa.DateTime(timezone=True), nullable=True))

    # Seed capabilities for known agents
    op.execute(
        """
        UPDATE agents SET capabilities = '["lookup_order","get_customer_summary","propose_refund"]'::jsonb
        WHERE agent_key = 'support_agent'
        """
    )
    op.execute(
        """
        UPDATE agents SET capabilities = '[]'::jsonb
        WHERE agent_key = 'triage_agent'
        """
    )
    op.execute(
        """
        UPDATE agents SET capabilities = '["check_billing_status","process_refund"]'::jsonb
        WHERE agent_key = 'vendor_billing'
        """
    )


def downgrade() -> None:
    op.drop_column("participants", "token_revoked_at")
    op.drop_column("participants", "token_expires_at")
    op.drop_column("participants", "token_jti")
    op.drop_column("participants", "granted_capabilities")
    op.drop_column("participants", "access_token")
    op.drop_column("sessions", "invite_expires_at")
    op.drop_column("sessions", "invite_jti")
    op.drop_column("agents", "capabilities")
