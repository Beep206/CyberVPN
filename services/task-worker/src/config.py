"""Configuration management for task-worker microservice.

Uses Pydantic Settings for type-safe configuration loading from environment variables.
Settings are cached as a singleton using lru_cache for performance.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = "postgresql+asyncpg://cybervpn:cybervpn@localhost:6767/cybervpn"

    # Cache Configuration
    redis_url: str = "redis://localhost:6379/0"

    # External Services
    remnawave_url: str = "http://localhost:3000"
    remnawave_api_token: SecretStr

    # Bot Tokens
    telegram_bot_token: SecretStr
    cryptobot_token: SecretStr

    # Admin Configuration — env var is comma-separated string, parsed to list[int]
    admin_telegram_ids: Annotated[list[int], NoDecode] = []

    # Worker Configuration
    worker_concurrency: int = 2
    result_ttl_seconds: int = 3600

    # Notification Settings
    notification_max_retries: int = 5
    notification_batch_size: int = 50

    # Health Check Configuration
    health_check_interval_seconds: int = 120

    # Cleanup Configuration
    cleanup_audit_retention_days: int = 90
    cleanup_webhook_retention_days: int = 30

    # Bulk Operations
    bulk_batch_size: int = 50

    # Monitoring
    metrics_port: int = 9091

    # Application Environment
    log_level: str = "INFO"
    environment: str = "development"

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_admin_telegram_ids(cls, v: str | list[int]) -> list[int]:
        """Parse comma-separated string of Telegram IDs into list of integers."""
        if isinstance(v, list):
            return v
        if not isinstance(v, str) or not v.strip():
            return []
        try:
            return [int(id_str.strip()) for id_str in v.split(",") if id_str.strip()]
        except ValueError as e:
            raise ValueError(f"ADMIN_TELEGRAM_IDS must be comma-separated integers: {e}") from e


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance. Returns singleton loaded from environment."""
    return Settings()
