"""
Application configuration using Pydantic Settings.
All secrets MUST be provided via environment variables — never hardcoded.
"""
import secrets
import logging
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ────────────────────────────────────────────────────────────────
    APP_NAME: str = "Drone Booking Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development | staging | production

    # ─── Server ─────────────────────────────────────────────────────────────
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ─── CORS — strict allow-list, no wildcard ───────────────────────────────
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # ─── Database (PostgreSQL) ───────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "drone_user"
    DB_PASSWORD: str = ""
    DB_NAME: str = "drone_booking"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ─── Redis ──────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_SLOT_LOCK_TTL_SECONDS: int = 300  # 5 minutes

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ─── RabbitMQ ───────────────────────────────────────────────────────────
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_BOOKING_EXCHANGE: str = "booking.events"

    # ─── JWT — NEVER hardcode secrets ────────────────────────────────────────
    # Resolution: Env var → ephemeral random + WARNING log
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Booking Business Rules ──────────────────────────────────────────────
    BOOKING_MIN_HOUR: int = 6   # 06:00
    BOOKING_MAX_HOUR: int = 18  # 18:00
    BOOKING_EXPIRY_MINUTES: int = 30  # auto-expire unpaid bookings

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def resolve_jwt_secret(cls, v: str) -> str:
        """
        Resolve JWT secret key with secure fallback.
        NEVER uses a hardcoded literal. Falls back to ephemeral random key
        with a critical warning (not suitable for multi-instance deployments).
        """
        if v:
            return v
        # TODO(security): In production, always set JWT_SECRET_KEY via env/KMS.
        ephemeral = secrets.token_hex(32)
        logger.warning(
            "JWT_SECRET_KEY not set! Using ephemeral random key. "
            "This is NOT suitable for production or multi-instance deployments. "
            "Set JWT_SECRET_KEY environment variable."
        )
        return ephemeral


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
