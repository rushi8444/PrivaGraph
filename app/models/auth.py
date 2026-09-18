"""Authentication and user context models."""

from __future__ import annotations

from pydantic import BaseModel


class UserContext(BaseModel):
    """Represents the authenticated user making a request."""

    user_id: str
    username: str
    department: str = ""
