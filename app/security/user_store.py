"""PostgreSQL user and token revocation store using asyncpg."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncpg

from app.config import settings
from app.security.auth import hash_password


@dataclass
class UserRecord:
    """Internal user record representation."""

    id: str
    email: str
    username: str
    hashed_password: str
    created_at: datetime
    auth_provider: str = "local"
    avatar_url: str = ""


class UserStore:
    """Manages asynchronous persistence for users and revoked JWT tokens in PostgreSQL."""

    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    async def get_pool(self) -> asyncpg.Pool:
        """Get or initialize the asyncpg connection pool bound to current event loop."""
        import asyncio

        current_loop = asyncio.get_running_loop()
        if (
            self._pool is None
            or getattr(self._pool, "_loop", None) is not current_loop
            or (getattr(self._pool, "_loop", None) and self._pool._loop.is_closed())
        ):
            self._pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                min_size=1,
                max_size=10,
            )
        return self._pool

    async def init_db(self) -> None:
        """Create users and token_denylist tables if they don't exist."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(64) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    auth_provider VARCHAR(32) DEFAULT 'local',
                    avatar_url TEXT DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

                ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(32) DEFAULT 'local';
                ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT DEFAULT '';

                CREATE TABLE IF NOT EXISTS token_denylist (
                    jti VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    revoked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMPTZ NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_token_denylist_expires ON token_denylist (expires_at);
                """
            )

    async def create_user(
        self,
        email: str,
        username: str,
        password: str,
    ) -> UserRecord:
        """Create a new user with salted bcrypt password.

        Raises:
            ValueError: If a user with this email already exists.
        """
        normalized_email = email.strip().lower()
        pool = await self.get_pool()
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        pwd_hash = hash_password(password)
        now = datetime.now(timezone.utc)

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (id, email, username, hashed_password, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id,
                    normalized_email,
                    username.strip(),
                    pwd_hash,
                    now,
                )
                return UserRecord(
                    id=user_id,
                    email=normalized_email,
                    username=username.strip(),
                    hashed_password=pwd_hash,
                    created_at=now,
                )
        except asyncpg.UniqueViolationError:
            raise ValueError(f"User with email '{normalized_email}' already exists.")

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        """Fetch a user record by email."""
        pool = await self.get_pool()
        normalized_email = email.strip().lower()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, username, hashed_password, created_at,
                       COALESCE(auth_provider, 'local') as auth_provider,
                       COALESCE(avatar_url, '') as avatar_url
                FROM users
                WHERE email = $1
                """,
                normalized_email,
            )
            if not row:
                return None
            return UserRecord(
                id=row["id"],
                email=row["email"],
                username=row["username"],
                hashed_password=row["hashed_password"],
                created_at=row["created_at"],
                auth_provider=row["auth_provider"],
                avatar_url=row["avatar_url"],
            )

    async def get_user_by_id(self, user_id: str) -> UserRecord | None:
        """Fetch a user record by user ID."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, username, hashed_password, created_at,
                       COALESCE(auth_provider, 'local') as auth_provider,
                       COALESCE(avatar_url, '') as avatar_url
                FROM users
                WHERE id = $1
                """,
                user_id,
            )
            if not row:
                return None
            return UserRecord(
                id=row["id"],
                email=row["email"],
                username=row["username"],
                hashed_password=row["hashed_password"],
                created_at=row["created_at"],
                auth_provider=row["auth_provider"],
                avatar_url=row["avatar_url"],
            )

    async def get_or_create_google_user(
        self,
        email: str,
        username: str,
        avatar_url: str = "",
    ) -> UserRecord:
        """Get existing user or create a new user authenticated via Google OAuth."""
        normalized_email = email.strip().lower()
        existing = await self.get_user_by_email(normalized_email)
        if existing:
            # If avatar changed, update it
            if avatar_url and avatar_url != existing.avatar_url:
                pool = await self.get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE users SET avatar_url = $1 WHERE id = $2",
                        avatar_url,
                        existing.id,
                    )
                existing.avatar_url = avatar_url
            return existing

        # Create new Google user
        pool = await self.get_pool()
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        # Random placeholder bcrypt hash for non-password users
        placeholder_hash = hash_password(uuid.uuid4().hex)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, username, hashed_password, auth_provider, avatar_url, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id,
                normalized_email,
                username.strip() or normalized_email.split("@")[0],
                placeholder_hash,
                "google",
                avatar_url,
                now,
            )

        return UserRecord(
            id=user_id,
            email=normalized_email,
            username=username.strip() or normalized_email.split("@")[0],
            hashed_password=placeholder_hash,
            created_at=now,
            auth_provider="google",
            avatar_url=avatar_url,
        )

    async def revoke_token(self, jti: str, user_id: str, expires_at: datetime) -> None:
        """Add a token to the server-side denylist."""
        pool = await self.get_pool()
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO token_denylist (jti, user_id, revoked_at, expires_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (jti) DO NOTHING
                """,
                jti,
                user_id,
                now,
                expires_at,
            )

    async def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been explicitly revoked."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM token_denylist WHERE jti = $1",
                jti,
            )
            return row is not None

    async def cleanup_revoked_tokens(self) -> int:
        """Purge expired tokens from the denylist to keep table size compact."""
        pool = await self.get_pool()
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM token_denylist WHERE expires_at < $1",
                now,
            )
            # Result format is usually "DELETE <count>"
            parts = result.split()
            return int(parts[-1]) if len(parts) > 1 and parts[-1].isdigit() else 0

    async def close(self) -> None:
        """Close connection pool cleanly."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


# Global singleton instance
user_store = UserStore()
