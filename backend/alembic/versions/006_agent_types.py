"""Agent type assignment, deployment snapshots, custom agent types."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_agent_types"
down_revision: Union[str, None] = "005_gatherings_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE custom_agent_type_status AS ENUM ('draft', 'active', 'archived')")
    custom_agent_type_status = postgresql.ENUM(
        "draft", "active", "archived", name="custom_agent_type_status", create_type=False
    )

    # Agent type assignment. Nullable for existing agents: they must select and
    # configure a type before their next deployment; nothing is inferred here.
    op.add_column("agents", sa.Column("agent_type_id", sa.String(length=128), nullable=True))
    op.add_column("agents", sa.Column("agent_type_version", sa.Integer(), nullable=True))
    for column in ("agent_type_configuration", "agent_metric_configuration", "agent_type_validation_status"):
        op.add_column(
            "agents",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )

    # Deployment snapshot: preserved verbatim so a deployed agent stays reproducible.
    op.add_column("agents", sa.Column("deployed_type_id", sa.String(length=128), nullable=True))
    op.add_column("agents", sa.Column("deployed_type_version", sa.Integer(), nullable=True))
    op.add_column(
        "agents",
        sa.Column("deployed_configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column(
            "deployed_metric_configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column("agents", sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "custom_agent_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("base_type_id", sa.String(length=128), nullable=True),
        sa.Column("status", custom_agent_type_status, nullable=False, server_default="draft"),
        sa.Column(
            "parameter_definitions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metric_definitions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("default_autonomy_level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("default_risk_level", sa.String(length=32), nullable=False, server_default="low"),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("family_id", "version", name="uq_custom_agent_types_family_version"),
    )
    op.create_index("ix_custom_agent_types_family_id", "custom_agent_types", ["family_id"])
    op.create_index("ix_custom_agent_types_slug", "custom_agent_types", ["slug"])

    # Existing agents keep every stored value; they are simply marked as needing setup.
    op.execute(
        "UPDATE agents SET agent_type_validation_status = "
        "'{\"valid\": false, \"requiresTypeSetup\": true}'::jsonb "
        "WHERE agent_type_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_custom_agent_types_slug", table_name="custom_agent_types")
    op.drop_index("ix_custom_agent_types_family_id", table_name="custom_agent_types")
    op.drop_table("custom_agent_types")
    op.drop_column("agents", "deployed_at")
    op.drop_column("agents", "deployed_metric_configuration")
    op.drop_column("agents", "deployed_configuration")
    op.drop_column("agents", "deployed_type_version")
    op.drop_column("agents", "deployed_type_id")
    op.drop_column("agents", "agent_type_validation_status")
    op.drop_column("agents", "agent_metric_configuration")
    op.drop_column("agents", "agent_type_configuration")
    op.drop_column("agents", "agent_type_version")
    op.drop_column("agents", "agent_type_id")
    op.execute("DROP TYPE custom_agent_type_status")
