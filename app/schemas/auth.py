from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User's email address", examples=["teacher@example.com"])
    password: str = Field(..., min_length=6, description="User password (min 6 chars)", examples=["SecurePassword123!"])


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User's email address", examples=["teacher@example.com"])
    password: str = Field(..., description="User password", examples=["SecurePassword123!"])


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer access token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field("bearer", description="Token authorization type", examples=["bearer"])


class UserResponse(BaseModel):
    id: int = Field(..., description="Unique user identifier", examples=[1])
    email: str = Field(..., description="User's email address", examples=["teacher@example.com"])
    created_at: datetime = Field(..., description="Timestamp of user account creation", examples=["2026-09-19T10:00:00Z"])

    model_config = ConfigDict(from_attributes=True)
