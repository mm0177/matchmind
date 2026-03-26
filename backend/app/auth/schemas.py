import uuid
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    preferred_gender: Optional[str] = None
    location: Optional[str] = None
    age_pref_min: Optional[int] = None
    age_pref_max: Optional[int] = None
    is_open_to_long_distance: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    preferred_gender: Optional[str] = None
    location: Optional[str] = None
    age_pref_min: Optional[int] = None
    age_pref_max: Optional[int] = None
    is_open_to_long_distance: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    gender: Optional[str]
    birth_date: Optional[date]
    preferred_gender: Optional[str] = None
    is_verified: bool
    is_matchable: bool
    onboarding_completed: bool = False
    location: Optional[str] = None
    age_pref_min: Optional[int] = None
    age_pref_max: Optional[int] = None
    is_open_to_long_distance: bool = False

    model_config = {"from_attributes": True}
