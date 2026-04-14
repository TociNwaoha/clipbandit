import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserTier


class UserBase(BaseModel):
    email: EmailStr
    tier: UserTier = UserTier.starter
    videos_used: int = 0


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str
