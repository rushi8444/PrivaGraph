"""Unit and integration tests for Authentication & User Accounts."""

import uuid
from datetime import timedelta
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.security.user_store import user_store


@pytest.mark.asyncio
async def test_password_hashing():
    """Verify bcrypt password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_jwt_token_creation_and_decoding():
    """Verify JWT access token generation and payload decoding."""
    user_id = f"usr_{uuid.uuid4().hex[:10]}"
    token, jti, exp = create_access_token(
        user_id=user_id,
        username="SecurityAnalyst",
        email="analyst@privagraph.com",
        expires_delta=timedelta(minutes=15),
    )
    assert isinstance(token, str) and len(token) > 20
    assert jti.startswith("jti_")

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["username"] == "SecurityAnalyst"
    assert payload["email"] == "analyst@privagraph.com"
    assert payload["jti"] == jti


@pytest.mark.asyncio
async def test_auth_api_registration_login_me_logout_flow():
    """Verify complete end-to-end API lifecycle: register, login, me, logout, revoked token."""
    await user_store.init_db()
    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"user_{unique_suffix}@privagraph.com"
    test_username = f"user_{unique_suffix}"
    test_password = "SecurePassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register new user
        reg_payload = {
            "email": test_email,
            "username": test_username,
            "password": test_password,
        }
        reg_res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, reg_res.text
        reg_data = reg_res.json()
        assert "access_token" in reg_data
        assert reg_data["user"]["email"] == test_email.lower()
        token = reg_data["access_token"]

        # 2. Duplicate registration returns 409 Conflict
        dup_res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert dup_res.status_code == 409

        # 3. Login with valid credentials
        login_payload = {
            "email": test_email,
            "password": test_password,
        }
        login_res = await ac.post("/api/v1/auth/login", json=login_payload)
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        new_token = login_data["access_token"]

        # 4. Login with invalid password returns 401
        bad_login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "WrongPassword!"},
        )
        assert bad_login_res.status_code == 401

        # 5. Access /me without token returns 401
        unauth_me = await ac.get("/api/v1/auth/me")
        assert unauth_me.status_code == 401

        # 6. Access /me with Bearer token returns profile
        auth_header = {"Authorization": f"Bearer {new_token}"}
        auth_me = await ac.get("/api/v1/auth/me", headers=auth_header)
        assert auth_me.status_code == 200
        profile = auth_me.json()
        assert profile["email"] == test_email.lower()
        assert profile["username"] == test_username

        # 7. Logout revokes current session token
        logout_res = await ac.post("/api/v1/auth/logout", headers=auth_header)
        assert logout_res.status_code == 200

        # 8. Subsequent request using revoked token returns 401
        revoked_me = await ac.get("/api/v1/auth/me", headers=auth_header)
        assert revoked_me.status_code == 401
        assert "revoked" in revoked_me.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_oauth_user_store_and_config():
    """Verify Google OAuth user creation in PostgreSQL and public config endpoint."""
    unique_suffix = uuid.uuid4().hex[:8]
    google_email = f"google_user_{unique_suffix}@privagraph.com"
    google_name = f"Google User {unique_suffix}"
    avatar_url = "https://lh3.googleusercontent.com/a/test-avatar"

    # 1. Test get_or_create_google_user in store
    user = await user_store.get_or_create_google_user(
        email=google_email,
        username=google_name,
        avatar_url=avatar_url,
    )
    assert user.email == google_email.lower()
    assert user.auth_provider == "google"
    assert user.avatar_url == avatar_url

    # 2. Re-fetching existing returns same user ID
    user2 = await user_store.get_or_create_google_user(
        email=google_email,
        username=google_name,
    )
    assert user2.id == user.id

    # 3. Test config endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/auth/google/config")
        assert res.status_code == 200
        data = res.json()
        assert "client_id" in data
        assert "enabled" in data

