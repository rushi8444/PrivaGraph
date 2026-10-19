"""Authentication and user context models."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr
    username: str = Field(min_length=2, max_length=50, description="Display username")
    password: str = Field(min_length=6, max_length=128, description="User password")


class UserLoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Payload for Google OAuth authentication."""

    credential: str | None = Field(default=None, description="Google ID Token (GIS One-Tap / Button)")
    code: str | None = Field(default=None, description="Google OAuth2 authorization code")


class GoogleConfigResponse(BaseModel):
    """Public Google OAuth client configuration."""

    client_id: str
    enabled: bool


class UserResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    username: str
    created_at: str
    auth_provider: str = "local"
    avatar_url: str = ""


class TokenResponse(BaseModel):
    """Authentication token response payload."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserContext(BaseModel):
    """Represents the authenticated user making a request across the pipeline."""

    user_id: str
    username: str
    email: str = ""
    department: str = ""
    avatar_url: str = ""
