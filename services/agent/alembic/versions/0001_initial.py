"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── registered_services ───────────────────────────────────────────────────
    op.create_table(
        "registered_services",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name",          sa.String(100),  nullable=False),
        sa.Column("service_type",  sa.Enum("rest", "websocket", name="servicetype"), nullable=False),
        sa.Column("base_url",      sa.String(255),  nullable=False),
        sa.Column("health_url",    sa.String(255),  nullable=False),
        sa.Column("description",   sa.Text(),       nullable=True),
        sa.Column("api_schema",    postgresql.JSON, nullable=True),
        sa.Column("instructions",  sa.Text(),       nullable=True),
        sa.Column("api_key",       sa.String(255),  nullable=True),
        sa.Column("meta",          postgresql.JSON, nullable=True),
        sa.Column("status",        sa.Enum("healthy", "degraded", "down", "active", "inactive", "error",
                                           name="servicestatus"), nullable=False, server_default="healthy"),
        sa.Column("is_active",     sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("last_seen",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_registered_services_id",   "registered_services", ["id"])
    op.create_unique_constraint("uq_registered_services_name", "registered_services", ["name"])

    # ── agent_actions ─────────────────────────────────────────────────────────
    op.create_table(
        "agent_actions",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type",   sa.String(100), nullable=False),
        sa.Column("reasoning",     sa.Text(),      nullable=True),
        sa.Column("request_data",  postgresql.JSON, nullable=True),
        sa.Column("response_data", postgresql.JSON, nullable=True),
        sa.Column("status",        sa.Enum("pending", "success", "failed", name="actionstatus"),
                  nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(),      nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_actions_id",          "agent_actions", ["id"])
    op.create_index("ix_agent_actions_service_id",  "agent_actions", ["service_id"])
    op.create_index("ix_agent_actions_action_type", "agent_actions", ["action_type"])

    # ── service_instructions ──────────────────────────────────────────────────
    op.create_table(
        "service_instructions",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("instruction",  sa.Text(),      nullable=False),
        sa.Column("set_by",       sa.String(50),  nullable=False, server_default="system"),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_service_instructions_service_id", "service_instructions", ["service_id"])


def downgrade() -> None:
    op.drop_table("service_instructions")
    op.drop_table("agent_actions")
    op.drop_table("registered_services")
    op.execute("DROP TYPE IF EXISTS actionstatus")
    op.execute("DROP TYPE IF EXISTS servicestatus")
    op.execute("DROP TYPE IF EXISTS servicetype")
