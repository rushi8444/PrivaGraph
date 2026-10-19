"""PostgreSQL chat and conversation persistence store using asyncpg."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.security.user_store import user_store


@dataclass
class ConversationRecord:
    """Represents a chat conversation session."""

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


@dataclass
class MessageRecord:
    """Represents an individual message in a conversation."""

    id: str
    conversation_id: str
    role: str
    content: str
    citations: list[dict[str, Any]]
    zero_pii_proof: dict[str, Any] | None
    metadata: dict[str, Any]
    created_at: datetime


class ChatStore:
    """Manages conversations and messages persistence in PostgreSQL."""

    async def init_db(self) -> None:
        """Create conversations and messages tables if they don't exist."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations (updated_at DESC);

                CREATE TABLE IF NOT EXISTS messages (
                    id VARCHAR(64) PRIMARY KEY,
                    conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    citations JSONB DEFAULT '[]'::jsonb,
                    zero_pii_proof JSONB DEFAULT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at ASC);

                CREATE TABLE IF NOT EXISTS conversation_documents (
                    conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    doc_id VARCHAR(128) NOT NULL,
                    attached_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (conversation_id, doc_id)
                );
                CREATE INDEX IF NOT EXISTS idx_conv_docs_conv_id ON conversation_documents (conversation_id);
                """
            )

    async def create_conversation(
        self,
        user_id: str,
        title: str = "New Chat",
        conversation_id: str | None = None,
    ) -> ConversationRecord:
        """Create a new conversation session for a user."""
        pool = await user_store.get_pool()
        conv_id = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        safe_title = title.strip()[:255] or "New Chat"

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                conv_id,
                user_id,
                safe_title,
                now,
                now,
            )

        return ConversationRecord(
            id=conv_id,
            user_id=user_id,
            title=safe_title,
            created_at=now,
            updated_at=now,
            message_count=0,
        )

    async def list_conversations(self, user_id: str) -> list[ConversationRecord]:
        """List all conversations belonging to a user, ordered by most recently updated."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
                       COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = $1
                GROUP BY c.id, c.user_id, c.title, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC
                """,
                user_id,
            )

        return [
            ConversationRecord(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=row["message_count"],
            )
            for row in rows
        ]

    async def get_conversation(self, conversation_id: str, user_id: str) -> ConversationRecord | None:
        """Fetch a single conversation record and verify ownership."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
                       COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.id = $1 AND c.user_id = $2
                GROUP BY c.id, c.user_id, c.title, c.created_at, c.updated_at
                """,
                conversation_id,
                user_id,
            )

        if not row:
            return None

        return ConversationRecord(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=row["message_count"],
        )

    async def update_title(self, conversation_id: str, user_id: str, title: str) -> bool:
        """Update conversation title if owned by user."""
        pool = await user_store.get_pool()
        safe_title = title.strip()[:255]
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE conversations
                SET title = $1, updated_at = CURRENT_TIMESTAMP
                WHERE id = $2 AND user_id = $3
                """,
                safe_title,
                conversation_id,
                user_id,
            )
            return "UPDATE 1" in result

    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete conversation and cascade delete its messages if owned by user."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM conversations
                WHERE id = $1 AND user_id = $2
                """,
                conversation_id,
                user_id,
            )
            return "DELETE 1" in result

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        zero_pii_proof: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageRecord:
        """Add a message to a conversation and touch its updated_at timestamp."""
        pool = await user_store.get_pool()
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        safe_citations = json.dumps(citations or [])
        safe_proof = json.dumps(zero_pii_proof) if zero_pii_proof else None
        safe_metadata = json.dumps(metadata or {})

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, citations, zero_pii_proof, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8)
                    """,
                    msg_id,
                    conversation_id,
                    role,
                    content,
                    safe_citations,
                    safe_proof,
                    safe_metadata,
                    now,
                )
                await conn.execute(
                    """
                    UPDATE conversations
                    SET updated_at = $1
                    WHERE id = $2
                    """,
                    now,
                    conversation_id,
                )

        return MessageRecord(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations or [],
            zero_pii_proof=zero_pii_proof,
            metadata=metadata or {},
            created_at=now,
        )

    async def get_messages(self, conversation_id: str, user_id: str) -> list[MessageRecord]:
        """Retrieve chronological messages for a conversation after verifying ownership."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            # Check ownership
            owner = await conn.fetchval(
                "SELECT user_id FROM conversations WHERE id = $1",
                conversation_id,
            )
            if not owner or owner != user_id:
                return []

            rows = await conn.fetch(
                """
                SELECT id, conversation_id, role, content, citations, zero_pii_proof, metadata, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
                """,
                conversation_id,
            )

        messages = []
        for r in rows:
            cits = r["citations"]
            if isinstance(cits, str):
                cits = json.loads(cits)
            proof = r["zero_pii_proof"]
            if isinstance(proof, str):
                proof = json.loads(proof)
            meta = r["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)

            messages.append(
                MessageRecord(
                    id=r["id"],
                    conversation_id=r["conversation_id"],
                    role=r["role"],
                    content=r["content"],
                    citations=cits or [],
                    zero_pii_proof=proof,
                    metadata=meta or {},
                    created_at=r["created_at"],
                )
            )

        return messages

    async def attach_document(self, conversation_id: str, doc_id: str) -> None:
        """Attach a document to a conversation scope."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_documents (conversation_id, doc_id)
                VALUES ($1, $2)
                ON CONFLICT (conversation_id, doc_id) DO NOTHING
                """,
                conversation_id,
                doc_id,
            )

    async def detach_document(self, conversation_id: str, doc_id: str) -> bool:
        """Detach a document from a conversation scope."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute(
                """
                DELETE FROM conversation_documents
                WHERE conversation_id = $1 AND doc_id = $2
                """,
                conversation_id,
                doc_id,
            )
            return "DELETE 1" in res

    async def get_conversation_documents(self, conversation_id: str) -> list[str]:
        """Fetch all document IDs attached to a conversation."""
        pool = await user_store.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT doc_id FROM conversation_documents
                WHERE conversation_id = $1
                ORDER BY attached_at ASC
                """,
                conversation_id,
            )
            return [row["doc_id"] for row in rows]


# Global singleton instance
chat_store = ChatStore()
