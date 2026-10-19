"""Unit and integration tests for Persistent Multi-Session Chat History (Section 2)."""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.security.user_store import user_store
from app.security.chat_store import chat_store
from app.security.auth import create_access_token


@pytest.mark.asyncio
async def test_conversation_crud_and_cascade_deletion():
    """Verify full conversation lifecycle: create, add messages, get, rename, and cascade delete."""
    await user_store.init_db()
    await chat_store.init_db()

    # Create two test users
    user_a = await user_store.get_or_create_google_user(
        email=f"user_a_{uuid.uuid4().hex[:6]}@privagraph.com",
        username="User A",
    )
    user_b = await user_store.get_or_create_google_user(
        email=f"user_b_{uuid.uuid4().hex[:6]}@privagraph.com",
        username="User B",
    )

    token_a, _, _ = create_access_token(user_id=user_a.id, username=user_a.username, email=user_a.email)
    token_b, _, _ = create_access_token(user_id=user_b.id, username=user_b.username, email=user_b.email)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. User A creates conversation
        create_res = await ac.post("/api/v1/conversations", json={"title": "HR Inquiries"}, headers=headers_a)
        assert create_res.status_code == 201
        conv_data = create_res.json()
        conv_id = conv_data["id"]
        assert conv_data["title"] == "HR Inquiries"

        # 2. Add messages via chat_store
        await chat_store.add_message(conv_id, "user", "What is the payroll schedule?")
        await chat_store.add_message(
            conv_id,
            "assistant",
            "Payroll is distributed bi-weekly.",
            citations=[{"doc_id": "HR-001", "title": "Employee Handbook"}],
            metadata={"model_used": "offline-synthesizer", "latency_ms": 12},
        )

        # 3. User A can retrieve full message history
        get_res = await ac.get(f"/api/v1/conversations/{conv_id}", headers=headers_a)
        assert get_res.status_code == 200
        detail = get_res.json()
        assert len(detail["messages"]) == 2
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["role"] == "assistant"
        assert detail["messages"][1]["citations"][0]["title"] == "Employee Handbook"

        # 4. Strict Ownership Protection: User B is forbidden from reading User A's conversation
        b_res = await ac.get(f"/api/v1/conversations/{conv_id}", headers=headers_b)
        assert b_res.status_code == 404

        # 5. User A renames conversation
        patch_res = await ac.patch(
            f"/api/v1/conversations/{conv_id}",
            json={"title": "Updated Payroll Discussion"},
            headers=headers_a,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Updated Payroll Discussion"

        # 6. List conversations shows the updated conversation
        list_res = await ac.get("/api/v1/conversations", headers=headers_a)
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(c["id"] == conv_id and c["title"] == "Updated Payroll Discussion" for c in items)

        # 7. User A deletes conversation
        del_res = await ac.delete(f"/api/v1/conversations/{conv_id}", headers=headers_a)
        assert del_res.status_code == 204

        # 8. Verify cascade deletion: conversation and messages are gone
        get_after = await ac.get(f"/api/v1/conversations/{conv_id}", headers=headers_a)
        assert get_after.status_code == 404

        msgs_after = await chat_store.get_messages(conv_id, user_a.id)
        assert len(msgs_after) == 0


@pytest.mark.asyncio
async def test_query_pipeline_conversation_persistence_and_auto_title():
    """Verify that submitting a query automatically tracks conversations and messages."""
    await user_store.init_db()
    await chat_store.init_db()

    user = await user_store.get_or_create_google_user(
        email=f"query_user_{uuid.uuid4().hex[:6]}@privagraph.com",
        username="Query Tester",
    )
    token, _, _ = create_access_token(user_id=user.id, username=user.username, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Submit query without conversation_id -> should auto-create conversation
        q_res = await ac.post(
            "/api/v1/query",
            json={"query": "Who is the lead architect for frontend infrastructure?"},
            headers=headers,
        )
        assert q_res.status_code == 200
        data = q_res.json()
        conv_id = data.get("conversation_id")
        assert conv_id is not None
        assert conv_id.startswith("conv_")

        # Verify conversation was auto-titled
        conv = await chat_store.get_conversation(conv_id, user.id)
        assert conv is not None
        assert "lead architect" in conv.title.lower()

        # Verify both messages (user + assistant) were persisted
        msgs = await chat_store.get_messages(conv_id, user.id)
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"
        assert len(msgs[1].content) > 0
