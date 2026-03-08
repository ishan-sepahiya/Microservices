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
        "payments",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount",         sa.Numeric(10, 2), nullable=False),
        sa.Column("currency",       sa.String(3), nullable=False, server_default="USD"),
        sa.Column("method",         sa.Enum("card", "wallet", "bank", name="paymentmethod"), nullable=False),
        sa.Column("status",         sa.Enum("pending", "completed", "failed", "refunded",
                                            name="paymentstatus"),
                  nullable=False, server_default="pending"),
        sa.Column("reference",      sa.String(255), nullable=True),
        sa.Column("failure_reason", sa.Text(),      nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_payments_id",       "payments", ["id"])
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_user_id",  "payments", ["user_id"])
    op.create_index("ix_payments_status",   "payments", ["status"])


def downgrade() -> None:
    op.drop_table("payments")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS paymentmethod")
