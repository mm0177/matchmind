"""Add financial character, self-perception columns and user_entities table

Revision ID: 002_fin_sp_entities
Revises: 001_authenticity
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "002_fin_sp_entities"
down_revision: Union[str, None] = "001_authenticity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New columns on persona_snapshots ──────────────────────────────────
    op.add_column("persona_snapshots", sa.Column("fin_scarcity_response", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("fin_wealth_vision", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("fin_risk_tolerance", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("self_perception_gap", sa.Float(), nullable=True))
    op.add_column("persona_snapshots", sa.Column("empathy_vs_apathy", sa.Float(), nullable=True))

    # ── New table: user_entities ──────────────────────────────────────────
    op.create_table(
        "user_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("relationship", sa.String(50), nullable=False, server_default="other"),
        sa.Column("emotional_weight", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("context_note", sa.Text(), nullable=True),
        sa.Column("extracted_from_message_id", UUID(as_uuid=True), nullable=True),
        sa.Column("day_extracted", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_entities")
    op.drop_column("persona_snapshots", "empathy_vs_apathy")
    op.drop_column("persona_snapshots", "self_perception_gap")
    op.drop_column("persona_snapshots", "fin_risk_tolerance")
    op.drop_column("persona_snapshots", "fin_wealth_vision")
    op.drop_column("persona_snapshots", "fin_scarcity_response")
