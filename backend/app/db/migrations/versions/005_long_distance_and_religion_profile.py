"""Add long-distance preference and religious profile fields

Revision ID: 005_long_distance_religion
Revises: 004_match_chat
Create Date: 2026-03-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_long_distance_religion"
down_revision: Union[str, None] = "004_match_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_open_to_long_distance", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.add_column("persona_snapshots", sa.Column("religion_affiliation", sa.String(length=100), nullable=True))
    op.add_column("persona_snapshots", sa.Column("religion_observance_level", sa.String(length=30), nullable=True))
    op.add_column("persona_snapshots", sa.Column("religion_partner_requirement", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("persona_snapshots", "religion_partner_requirement")
    op.drop_column("persona_snapshots", "religion_observance_level")
    op.drop_column("persona_snapshots", "religion_affiliation")
    op.drop_column("users", "is_open_to_long_distance")
