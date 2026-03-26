import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    day_number: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class DayStatusResponse(BaseModel):
    current_day: int
    theme: str
    goal: str
    is_complete: bool   # True after day 10
    days_covered: list[int]
