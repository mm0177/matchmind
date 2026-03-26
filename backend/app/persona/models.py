import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Float, Date, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.database import Base
from app.config import settings


class PersonaSnapshot(Base):
    __tablename__ = "persona_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Big Five scores (0.0 – 1.0)
    openness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    openness_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    conscientiousness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    conscientiousness_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraversion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraversion_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    agreeableness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    agreeableness_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    neuroticism: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    neuroticism_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # MBTI derived label
    mbti_label: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Communication style (0.0 – 1.0)
    comm_directness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comm_humor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comm_formality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comm_empathy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Values (0.0 – 1.0)
    val_family: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_career: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_adventure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_spirituality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_creativity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_stability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationship profile
    attachment_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # secure/anxious/avoidant
    conflict_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)    # collaborative/competitive/avoidant
    relationship_pace: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # slow/moderate/fast
    religion_affiliation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    religion_observance_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    religion_partner_requirement: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    dealbreakers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    must_haves: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Flags for inconsistencies found by LLM
    consistency_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Financial character (0.0 – 1.0)
    fin_scarcity_response: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # 0=panic, 0.5=shut_down, 1=strategize
    fin_wealth_vision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)       # 0=luxury/consumption, 0.5=freedom, 1=legacy/purpose
    fin_risk_tolerance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # 0=risk_averse, 1=risk_seeking

    # Self-perception & complex index (0.0 – 1.0)
    self_perception_gap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)     # 0=inferiority, 0.5=balanced, 1=superiority
    empathy_vs_apathy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)       # 0=apathetic/self-centered, 1=deeply empathetic

    # Authenticity analysis (0.0 – 1.0, higher = more authentic)
    authenticity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    social_desirability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    specificity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    self_awareness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    consistency_score_llm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Vector embedding for semantic similarity matching (bge-small-en-v1.5, dim=384)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(384), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserEntity(Base):
    """People and relationships mentioned by the user during conversations.
    Extracted during days 1-2 and used to generate personalised scenarios on later days."""
    __tablename__ = "user_entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)              # e.g. "younger brother", "college best friend"
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)         # family | friend | colleague | ex_partner | other
    emotional_weight: Mapped[str] = mapped_column(String(20), default="medium")   # high | medium | low
    context_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # extra detail from chat
    extracted_from_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    day_extracted: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonaFact(Base):
    __tablename__ = "persona_facts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persona_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)   # big_five | values | communication_style | relationship
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_message_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
