"""Application configuration via Pydantic Settings (env-based)."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    # --- Application ---
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # --- Security ---
    VAULT_MASTER_KEY: str = Field(
        default="0" * 64,
        description="Hex-encoded 32-byte AES-256 master key for the encrypted vault.",
    )
    TOKENIZER_SECRET_KEY: str = Field(
        default="default-tokenizer-secret",
        description="HMAC secret used for deterministic entity tokenization.",
    )
    JWT_SECRET_KEY: str = "default-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # --- Database ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "privagraph_vault"
    POSTGRES_USER: str = "privagraph"
    POSTGRES_PASSWORD: str = ""

    # --- LLM Provider ---
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    DEFAULT_MODEL: str = "gpt-4o"

    # --- NER ---
    SPACY_MODEL: str = "en_core_web_sm"
    DEFAULT_MIN_CONFIDENCE: float = 0.85

    # --- Paths ---
    DATA_DIR: Path = Path("data")
    AUDIT_LOG_PATH: Path = Path("data/audit.jsonl")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def vault_key_bytes(self) -> bytes:
        """Return the vault master key as raw bytes."""
        return bytes.fromhex(self.VAULT_MASTER_KEY)


settings = Settings()
