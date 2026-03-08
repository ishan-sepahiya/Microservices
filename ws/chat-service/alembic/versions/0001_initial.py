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
        "chat_rooms",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name",       sa.String(100), nullable=False),
        sa.Column("is_active",  sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_rooms_id", "chat_rooms", ["id"])
    op.create_unique_constraint("uq_chat_rooms_name", "chat_rooms", ["name"])

    op.create_table(
        "chat_messages",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id",  sa.String(100), nullable=False),
        sa.Column("content",    sa.Text(),      nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_messages_id",         "chat_messages", ["id"])
    op.create_index("ix_chat_messages_room_id",    "chat_messages", ["room_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_rooms")
