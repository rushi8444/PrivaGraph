"""Chat history and conversation models."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Payload to create a new conversation session."""

    title: str = Field(default="New Chat", max_length=255)


class ConversationUpdate(BaseModel):
    """Payload to update conversation title."""

    title: str = Field(min_length=1, max_length=255)


class ConversationSummary(BaseModel):
    """Summary representation for conversation sidebar listing."""

    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ChatMessage(BaseModel):
    """Individual chat message item."""

    id: str
    conversation_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = []
    zero_pii_proof: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}
    created_at: str


class AttachDocumentRequest(BaseModel):
    """Payload to attach a document to a conversation."""

    doc_id: str


class ConversationDetail(BaseModel):
    """Full conversation detail with chronological messages and attached documents."""

    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = []
    documents: list[dict[str, Any]] = []
