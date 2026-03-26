"""Add location and age preference columns to users

Revision ID: 003_location_age_prefs
Revises: 002_fin_sp_entities
Create Date: 2026-03-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_location_age_prefs"
down_revision: Union[str, None] = "002_fin_sp_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("location", sa.String(150), nullable=True))
    op.add_column("users", sa.Column("age_pref_min", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("age_pref_max", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "age_pref_max")
    op.drop_column("users", "age_pref_min")
    op.drop_column("users", "location")
