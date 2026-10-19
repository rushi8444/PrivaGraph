"""Authentication API endpoints (register, login, me, logout)."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    UserContext,
)
from app.security.auth import (
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.security.user_store import user_store

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


async def get_current_user_with_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> tuple[UserContext, str, str, datetime]:
    """Dependency returning (UserContext, token, jti, exp)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    user_id = payload.get("sub")
    exp_timestamp = payload.get("exp")

    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check server-side revocation denylist
    if await user_store.is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_store.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    exp_dt = (
        datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        if exp_timestamp
        else datetime.now(timezone.utc)
    )

    user_ctx = UserContext(
        user_id=user.id,
        username=user.username,
        email=user.email,
        department="",
    )
    return user_ctx, token, jti, exp_dt


async def get_current_user(
    auth_data: tuple[UserContext, str, str, datetime] = Depends(get_current_user_with_token),
) -> UserContext:
    """Dependency returning the authenticated UserContext."""
    user_ctx, _, _, _ = auth_data
    return user_ctx


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest):
    """Register a new user account with hashed password and return access token."""
    try:
        user = await user_store.create_user(
            email=request.email,
            username=request.username,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    token, _, _ = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at.isoformat(),
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """Authenticate with email and password, returning an access token."""
    user = await user_store.get_user_by_email(request.email)
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, _, _ = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at.isoformat(),
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user_ctx: UserContext = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    user = await user_store.get_user_by_id(user_ctx.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at.isoformat(),
    )


@router.post("/logout")
async def logout(
    auth_data: tuple[UserContext, str, str, datetime] = Depends(get_current_user_with_token),
):
    """Revoke the current user session token."""
    user_ctx, _, jti, exp_dt = auth_data
    await user_store.revoke_token(jti=jti, user_id=user_ctx.user_id, expires_at=exp_dt)
    return {"message": "Logged out successfully", "user_id": user_ctx.user_id}


# =========================================================================
# Google OAuth 2.0 Integration
# =========================================================================

from fastapi.responses import RedirectResponse
import httpx
from app.config import settings
from app.models.auth import GoogleAuthRequest, GoogleConfigResponse


@router.get("/google/config", response_model=GoogleConfigResponse)
async def get_google_config():
    """Return public Google OAuth Client ID for frontend button rendering."""
    return GoogleConfigResponse(
        client_id=settings.GOOGLE_CLIENT_ID or "",
        enabled=bool(settings.GOOGLE_CLIENT_ID),
    )


@router.post("/google", response_model=TokenResponse)
async def authenticate_with_google(request: GoogleAuthRequest):
    """Authenticate or register user using a Google OAuth ID Token (One-Tap / Button)."""
    if not request.credential and not request.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google OAuth credential token or authorization code",
        )

    google_data = None

    # Flow A: Verifying Google ID Token directly
    if request.credential:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": request.credential},
                )
                if res.status_code == 200:
                    google_data = res.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Google OAuth credential token",
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to communicate with Google authentication service: {e}",
            )

    # Flow B: Exchanging authorization code for token
    elif request.code:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth Client ID/Secret not configured on server",
            )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_res = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "code": request.code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    },
                )
                if token_res.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to exchange authorization code with Google",
                    )
                token_payload = token_res.json()
                id_token = token_payload.get("id_token")
                # Now verify the id_token
                res = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": id_token},
                )
                if res.status_code == 200:
                    google_data = res.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Google code exchange failed: {e}",
            )

    if not google_data or not google_data.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve verified email address from Google",
        )

    email = google_data.get("email", "").lower()
    name = google_data.get("name") or google_data.get("given_name") or email.split("@")[0]
    avatar_url = google_data.get("picture", "")

    # Retrieve existing user or create a new user profile
    user = await user_store.get_or_create_google_user(
        email=email,
        username=name,
        avatar_url=avatar_url,
    )

    # Issue PrivaGraph JWT access token
    token, _, _ = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at.isoformat(),
        auth_provider=user.auth_provider,
        avatar_url=user.avatar_url,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
    )


@router.get("/google/login")
async def google_login_redirect():
    """Redirect user to Google OAuth2 consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured yet. Please configure GOOGLE_CLIENT_ID.",
        )

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"prompt=select_account"
    )
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(code: str | None = None, error: str | None = None):
    """Handle callback from Google OAuth redirect flow."""
    if error or not code:
        err_msg = error or "Authorization code missing"
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")

    try:
        token_resp = await authenticate_with_google(GoogleAuthRequest(code=code))
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?token={token_resp.access_token}"
        )
    except Exception as e:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={str(e)}")

