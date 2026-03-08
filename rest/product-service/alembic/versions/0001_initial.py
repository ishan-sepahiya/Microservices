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
        "products",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name",           sa.String(255),  nullable=False),
        sa.Column("description",    sa.Text(),        nullable=True),
        sa.Column("sku",            sa.String(100),  nullable=False),
        sa.Column("price",          sa.Numeric(10, 2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("is_active",      sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_products_id",   "products", ["id"])
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_sku",  "products", ["sku"])
    op.create_unique_constraint("uq_products_sku", "products", ["sku"])


def downgrade() -> None:
    op.drop_table("products")
