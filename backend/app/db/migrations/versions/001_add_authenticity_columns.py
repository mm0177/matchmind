"""Add authenticity columns to persona_snapshots

Revision ID: 001_authenticity
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_authenticity"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("persona_snapshots", sa.Column("authenticity_score", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("social_desirability_score", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("specificity_score", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("self_awareness_score", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("consistency_score_llm", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("persona_snapshots", "consistency_score_llm")
    op.drop_column("persona_snapshots", "self_awareness_score")
    op.drop_column("persona_snapshots", "specificity_score")
    op.drop_column("persona_snapshots", "social_desirability_score")
    op.drop_column("persona_snapshots", "authenticity_score")
