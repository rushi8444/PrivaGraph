"""Conversation management and chat history API endpoints."""

from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, status

from app.api.dependencies import get_current_user_or_default, get_state
from app.models.auth import UserContext
from app.models.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationSummary,
    ConversationDetail,
    ChatMessage,
    AttachDocumentRequest,
)
from app.security.chat_store import chat_store

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_user_conversations(
    user: UserContext = Depends(get_current_user_or_default),
):
    """Retrieve all conversations belonging to the authenticated user."""
    records = await chat_store.list_conversations(user.user_id)
    return [
        ConversationSummary(
            id=r.id,
            title=r.title,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
            message_count=r.message_count,
        )
        for r in records
    ]


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    payload: ConversationCreate | None = None,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Create a new conversation session for the authenticated user."""
    title = (payload.title if payload and payload.title else "New Chat").strip()
    conv = await chat_store.create_conversation(user_id=user.user_id, title=title)
    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        message_count=0,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_history(
    conversation_id: str,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Retrieve complete message history and attached documents for a specific conversation."""
    conv = await chat_store.get_conversation(conversation_id, user.user_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )

    messages = await chat_store.get_messages(conversation_id, user.user_id)
    doc_ids = await chat_store.get_conversation_documents(conversation_id)
    state = get_state()
    attached_docs = []
    for d in doc_ids:
        meta = getattr(state, "documents", {}).get(d, {})
        attached_docs.append({
            "doc_id": d,
            "title": meta.get("title") or Path(d).stem.replace("_", " ").title(),
            "classification": meta.get("classification", "INTERNAL"),
            "department": meta.get("department", "General"),
        })

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=[
            ChatMessage(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                citations=m.citations,
                zero_pii_proof=m.zero_pii_proof,
                metadata=m.metadata,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
        documents=attached_docs,
    )


@router.get("/{conversation_id}/documents")
async def get_conversation_attached_documents(
    conversation_id: str,
    user: UserContext = Depends(get_current_user_or_default),
):
    """List documents attached to this conversation scope."""
    conv = await chat_store.get_conversation(conversation_id, user.user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    doc_ids = await chat_store.get_conversation_documents(conversation_id)
    state = get_state()
    return [
        {
            "doc_id": d,
            "title": getattr(state, "documents", {}).get(d, {}).get("title") or Path(d).stem.replace("_", " ").title(),
            "classification": getattr(state, "documents", {}).get(d, {}).get("classification", "INTERNAL"),
            "department": getattr(state, "documents", {}).get(d, {}).get("department", "General"),
        }
        for d in doc_ids
    ]


@router.post("/{conversation_id}/documents")
async def attach_document_to_conversation(
    conversation_id: str,
    payload: AttachDocumentRequest,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Attach a document to a conversation scope."""
    conv = await chat_store.get_conversation(conversation_id, user.user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await chat_store.attach_document(conversation_id, payload.doc_id)
    doc_ids = await chat_store.get_conversation_documents(conversation_id)
    state = get_state()
    return [
        {
            "doc_id": d,
            "title": getattr(state, "documents", {}).get(d, {}).get("title") or Path(d).stem.replace("_", " ").title(),
            "classification": getattr(state, "documents", {}).get(d, {}).get("classification", "INTERNAL"),
            "department": getattr(state, "documents", {}).get(d, {}).get("department", "General"),
        }
        for d in doc_ids
    ]


@router.delete("/{conversation_id}/documents/{doc_id}")
async def detach_document_from_conversation(
    conversation_id: str,
    doc_id: str,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Detach a document from a conversation scope."""
    conv = await chat_store.get_conversation(conversation_id, user.user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await chat_store.detach_document(conversation_id, doc_id)
    doc_ids = await chat_store.get_conversation_documents(conversation_id)
    state = get_state()
    return [
        {
            "doc_id": d,
            "title": getattr(state, "documents", {}).get(d, {}).get("title") or Path(d).stem.replace("_", " ").title(),
            "classification": getattr(state, "documents", {}).get(d, {}).get("classification", "INTERNAL"),
            "department": getattr(state, "documents", {}).get(d, {}).get("department", "General"),
        }
        for d in doc_ids
    ]


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Update conversation title."""
    updated = await chat_store.update_title(
        conversation_id=conversation_id,
        user_id=user.user_id,
        title=payload.title,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )

    conv = await chat_store.get_conversation(conversation_id, user.user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        message_count=conv.message_count,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_session(
    conversation_id: str,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Delete a conversation session and all its stored messages."""
    deleted = await chat_store.delete_conversation(conversation_id, user.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )
    return None
