"""Configuration management for task-worker microservice.

Uses Pydantic Settings for type-safe configuration loading from environment variables.
Settings are cached as a singleton using lru_cache for performance.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator, model_validator
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
    metrics_enabled: bool = True
    metrics_protect: bool = True
    metrics_port: int = 9091
    metrics_allowed_ips: Annotated[list[str], NoDecode] = []
    metrics_basic_auth_user: str | None = None
    metrics_basic_auth_password: SecretStr | None = None

    # Application Environment
    log_level: str = "INFO"
    environment: str = "development"

    # Sentry (Observability)
    sentry_dsn: str = ""  # Sentry DSN for error tracking (optional, empty = disabled)

    # Email Provider Configuration (OTP)
    # Primary: Resend.com (initial OTP)
    resend_api_key: SecretStr | None = None
    resend_from_email: str = "CyberVPN <verify@cybervpn.io>"

    # Secondary: Brevo (resend OTP)
    brevo_api_key: SecretStr | None = None
    brevo_from_email: str = "CyberVPN <noreply@cybervpn.io>"

    # Dev/Test environment: Use Mailpit cluster for email testing
    # Set EMAIL_DEV_MODE=true to use SMTP instead of API providers
    email_dev_mode: bool = False

    # Mailpit SMTP servers (round-robin for provider rotation testing)
    # Format: host:port,host:port,host:port
    smtp_servers: Annotated[list[str], NoDecode] = ["localhost:1025", "localhost:1026", "localhost:1027"]
    smtp_from_email: str = "CyberVPN <verify@cybervpn.local>"

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

    @field_validator("metrics_allowed_ips", mode="before")
    @classmethod
    def parse_metrics_allowed_ips(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        if not isinstance(v, str) or not v.strip():
            return []
        return [ip.strip() for ip in v.split(",") if ip.strip()]

    @field_validator("smtp_servers", mode="before")
    @classmethod
    def parse_smtp_servers(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated SMTP servers (host:port format)."""
        if isinstance(v, list):
            return v
        if not isinstance(v, str) or not v.strip():
            return ["localhost:1025", "localhost:1026", "localhost:1027"]
        return [s.strip() for s in v.split(",") if s.strip()]

    @model_validator(mode="after")
    def validate_metrics_settings(self) -> "Settings":
        if self.metrics_basic_auth_user is None and self.metrics_basic_auth_password is not None:
            msg = "METRICS_BASIC_AUTH_USER is required when password is set"
            raise ValueError(msg)
        if self.metrics_basic_auth_user is not None and self.metrics_basic_auth_password is None:
            msg = "METRICS_BASIC_AUTH_PASSWORD is required when user is set"
            raise ValueError(msg)
        if self.metrics_protect and not self.metrics_allowed_ips and self.metrics_basic_auth_user is None:
            msg = "METRICS_ALLOWED_IPS or METRICS_BASIC_AUTH_* required when METRICS_PROTECT=true"
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance. Returns singleton loaded from environment."""
    return Settings()
