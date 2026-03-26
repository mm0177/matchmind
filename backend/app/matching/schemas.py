import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class MatchResponse(BaseModel):
    id: uuid.UUID
    user_a_id: uuid.UUID
    user_b_id: uuid.UUID
    score: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchDetailResponse(BaseModel):
    """User-facing match response — shows ONLY partner name and age."""
    id: uuid.UUID
    partner_display_name: str
    partner_age: int | None
    conversation_id: uuid.UUID | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchRunResponse(BaseModel):
    id: uuid.UUID
    run_date: date
    total_users: int
    total_matches: int
    algorithm_ver: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Match Chat schemas ───────────────────────────────────────────────────────

class MatchMessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMatchMessageRequest(BaseModel):
    content: str
