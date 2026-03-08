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
    op.create_table(
        "metric_snapshots",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name",     sa.String(100), nullable=False),
        sa.Column("cpu_percent",      sa.Float(),     nullable=False),
        sa.Column("memory_percent",   sa.Float(),     nullable=False),
        sa.Column("request_count",    sa.Integer(),   server_default="0"),
        sa.Column("error_count",      sa.Integer(),   server_default="0"),
        sa.Column("recorded_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_metric_snapshots_service_name", "metric_snapshots", ["service_name"])
    op.create_index("ix_metric_snapshots_recorded_at",  "metric_snapshots", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("metric_snapshots")
