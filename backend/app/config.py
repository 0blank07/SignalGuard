from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "SignalGuard"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = Field(
        default="signalguard-development-secret-key-32-bytes-minimum",
        min_length=16,
    )
    API_KEY_HEADER_NAME: str = "X-SignalGuard-API-Key"
    REQUIRE_API_KEY: bool = False
    API_KEY: str | None = None

    # Database
    DATABASE_URL: str = "sqlite:///./signalguard.db"

    # Engine & Scheduler configuration
    MAX_CONCURRENT_CHECKS: int = Field(default=50, ge=1, le=500)
    DEFAULT_CHECK_INTERVAL_SECONDS: int = Field(default=30, ge=5)
    DEFAULT_TIMEOUT_SECONDS: int = Field(default=10, ge=1, le=60)
    MIN_CHECK_INTERVAL_SECONDS: int = 5
    MAX_TIMEOUT_SECONDS: int = 60
    MAX_BODY_PREVIEW_BYTES: int = 16384  # 16 KB max capture

    # Retry Policy
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5
    RETRY_JITTER_MAX: float = 0.5

    # Flapping / Incident Hysteresis
    CONSECUTIVE_FAILURES_FOR_INCIDENT: int = 2
    CONSECUTIVE_SUCCESSES_FOR_RECOVERY: int = 2

    # SSRF Protection
    ALLOW_PRIVATE_IPS: bool = False
    DNS_RESOLUTION_TIMEOUT_SECONDS: float = 3.0

    @field_validator("DEFAULT_CHECK_INTERVAL_SECONDS")
    @classmethod
    def validate_check_interval(cls, v: int) -> int:
        if v < 5:
            raise ValueError("DEFAULT_CHECK_INTERVAL_SECONDS must be at least 5 seconds")
        return v

    @field_validator("DEFAULT_TIMEOUT_SECONDS")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v > 60:
            raise ValueError("DEFAULT_TIMEOUT_SECONDS cannot exceed 60 seconds")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
