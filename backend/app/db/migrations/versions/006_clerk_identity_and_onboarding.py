"""Add Clerk identity mapping and onboarding status

Revision ID: 006_clerk_identity_onboarding
Revises: 005_long_distance_religion
Create Date: 2026-03-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_clerk_identity_onboarding"
down_revision: Union[str, None] = "005_long_distance_religion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(length=20), nullable=False, server_default="local"),
    )
    op.add_column(
        "users",
        sa.Column("external_auth_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(op.f("ix_users_external_auth_id"), "users", ["external_auth_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_external_auth_id"), table_name="users")
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "external_auth_id")
    op.drop_column("users", "auth_provider")
