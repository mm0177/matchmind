"""Add match_conversations and match_messages tables

Revision ID: 004_match_chat
Revises: 003_location_age_prefs
Create Date: 2026-03-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_match_chat"
down_revision: Union[str, None] = "003_location_age_prefs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("match_id", sa.Uuid(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_a_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_b_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_match_conversations_id", "match_conversations", ["id"])
    op.create_index("ix_match_conversations_match_id", "match_conversations", ["match_id"])
    op.create_index("ix_match_conversations_user_a_id", "match_conversations", ["user_a_id"])
    op.create_index("ix_match_conversations_user_b_id", "match_conversations", ["user_b_id"])

    op.create_table(
        "match_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("match_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_match_messages_id", "match_messages", ["id"])
    op.create_index("ix_match_messages_conversation_id", "match_messages", ["conversation_id"])
    op.create_index("ix_match_messages_sender_id", "match_messages", ["sender_id"])
    op.create_index("ix_match_messages_created_at", "match_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("match_messages")
    op.drop_table("match_conversations")
