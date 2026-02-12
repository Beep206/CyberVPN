"""CyberVPN Telegram Bot — Pydantic Settings configuration.

All environment variables are defined here using pydantic-settings BaseSettings
with nested model support, validators, and a cached singleton accessor.
"""

from __future__ import annotations

from functools import lru_cache
import ipaddress
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Nested sub-models ────────────────────────────────────────────────────────


class WebhookSettings(BaseSettings):
    """Webhook-specific settings (used when BOT_MODE=webhook)."""

    model_config = SettingsConfigDict(env_prefix="WEBHOOK_")

    url: AnyHttpUrl | None = None
    path: str = "/webhook/telegram"
    port: int = Field(default=8080, ge=1024, le=65535)
    secret_token: SecretStr | None = None


class BackendSettings(BaseSettings):
    """CyberVPN Backend API connection settings."""

    model_config = SettingsConfigDict(env_prefix="BACKEND_")

    api_url: AnyHttpUrl
    api_key: SecretStr
    timeout: Annotated[int, Field(gt=0, le=120)] = 30
    max_retries: Annotated[int, Field(ge=0, le=10)] = 3
    retry_backoff: Annotated[float, Field(gt=0)] = 0.5


class RedisSettings(BaseSettings):
    """Redis/Valkey connection settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379"
    db: Annotated[int, Field(ge=0, le=15)] = 1
    password: SecretStr | None = None
    key_prefix: str = "cybervpn:bot:"
    ttl_seconds: Annotated[int, Field(gt=0)] = 3600

    @property
    def dsn(self) -> str:
        """Build full Redis DSN with DB number."""
        base = self.url.rstrip("/")
        return f"{base}/{self.db}"


class CryptoBotSettings(BaseSettings):
    """Crypto Bot (CryptoBot) payment gateway settings."""

    model_config = SettingsConfigDict(env_prefix="CRYPTOBOT_")

    enabled: bool = True
    token: SecretStr | None = None
    network: Literal["mainnet", "testnet"] = "mainnet"

    @model_validator(mode="after")
    def _validate_token_when_enabled(self) -> CryptoBotSettings:
        if self.enabled and self.token is None:
            msg = "CRYPTOBOT_TOKEN is required when CRYPTOBOT_ENABLED=true"
            raise ValueError(msg)
        return self


class YooKassaSettings(BaseSettings):
    """YooKassa payment gateway settings."""

    model_config = SettingsConfigDict(env_prefix="YOOKASSA_")

    enabled: bool = False
    shop_id: str | None = None
    secret_key: SecretStr | None = None
    test_mode: bool = False

    @model_validator(mode="after")
    def _validate_credentials_when_enabled(self) -> YooKassaSettings:
        if self.enabled and (self.shop_id is None or self.secret_key is None):
            msg = "YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY are required when YOOKASSA_ENABLED=true"
            raise ValueError(msg)
        return self


class TelegramStarsSettings(BaseSettings):
    """Telegram Stars payment settings."""

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_STARS_")

    enabled: bool = True


class TrialSettings(BaseSettings):
    """Trial subscription settings."""

    model_config = SettingsConfigDict(env_prefix="TRIAL_")

    enabled: bool = True
    days: Annotated[int, Field(gt=0, le=30)] = 2
    traffic_gb: Annotated[int, Field(gt=0, le=100)] = 2


class ReferralSettings(BaseSettings):
    """Referral program settings."""

    model_config = SettingsConfigDict(env_prefix="REFERRAL_")

    enabled: bool = True
    bonus_days: Annotated[int, Field(gt=0)] = 3
    max_referrals: Annotated[int, Field(gt=0)] = 100


class LoggingSettings(BaseSettings):
    """Logging and observability settings."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_format: bool = True
    show_locals: bool = False


class PrometheusSettings(BaseSettings):
    """Prometheus metrics settings."""

    model_config = SettingsConfigDict(env_prefix="PROMETHEUS_")

    enabled: bool = True
    protect: bool = True
    port: Annotated[int, Field(ge=1024, le=65535)] = 9090
    path: str = "/metrics"
    allowed_ips: list[str] = Field(default_factory=list)
    trust_proxy: bool = False
    trusted_proxy_ips: list[str] = Field(default_factory=list)
    basic_auth_user: str | None = None
    basic_auth_password: SecretStr | None = None
    require_tls: bool = False

    @field_validator("allowed_ips", mode="before")
    @classmethod
    def parse_allowed_ips(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def parse_trusted_proxy_ips(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v

    @model_validator(mode="after")
    def _validate_security(self) -> PrometheusSettings:
        if self.basic_auth_user is None and self.basic_auth_password is not None:
            msg = "PROMETHEUS_BASIC_AUTH_USER is required when password is set"
            raise ValueError(msg)
        if self.basic_auth_user is not None and self.basic_auth_password is None:
            msg = "PROMETHEUS_BASIC_AUTH_PASSWORD is required when user is set"
            raise ValueError(msg)
        if self.protect and not self.allowed_ips and self.basic_auth_user is None:
            msg = "PROMETHEUS_ALLOWED_IPS or PROMETHEUS_BASIC_AUTH_* required when PROMETHEUS_PROTECT=true"
            raise ValueError(msg)
        if self.trust_proxy and not self.trusted_proxy_ips:
            msg = "PROMETHEUS_TRUSTED_PROXY_IPS required when PROMETHEUS_TRUST_PROXY=true"
            raise ValueError(msg)
        for raw in self.trusted_proxy_ips:
            try:
                network = ipaddress.ip_network(raw, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid PROMETHEUS_TRUSTED_PROXY_IPS entry: {raw}") from exc
            if network.prefixlen == 0:
                raise ValueError("PROMETHEUS_TRUSTED_PROXY_IPS cannot include 0.0.0.0/0 or ::/0")
        return self


# ── Root settings ────────────────────────────────────────────────────────────


class BotSettings(BaseSettings):
    """Root settings for CyberVPN Telegram Bot.

    All environment variables are loaded from .env file and/or environment.
    Nested settings use per-group prefixes (e.g. BACKEND_API_URL, REDIS_URL).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=True,
        extra="ignore",
    )

    # ── Bot core ─────────────────────────────────────────────────────────
    bot_token: SecretStr
    bot_username: str | None = None
    bot_mode: Literal["webhook", "polling"] = "polling"
    environment: Literal["development", "staging", "production"] = "production"

    # ── Admin ────────────────────────────────────────────────────────────
    admin_ids: list[int] = Field(default_factory=list)
    support_username: str = "CyberVPNSupport"

    # ── i18n ─────────────────────────────────────────────────────────────
    default_language: str = "ru"
    available_languages: list[str] = Field(
        default_factory=lambda: [
            "am", "ar", "be", "bn", "cs", "de", "en", "es", "fa", "fil",
            "fr", "ha", "he", "hi", "hu", "id", "it", "ja", "kk", "ko",
            "ku", "ms", "my", "nl", "pl", "pt", "ro", "ru", "sv", "th",
            "tk", "tr", "uk", "ur", "uz", "vi", "yo", "zh", "zh-Hant",
        ]
    )

    # ── Nested groups ────────────────────────────────────────────────────
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    backend: BackendSettings
    redis: RedisSettings = Field(default_factory=RedisSettings)
    cryptobot: CryptoBotSettings = Field(default_factory=CryptoBotSettings)
    yookassa: YooKassaSettings = Field(default_factory=YooKassaSettings)
    telegram_stars: TelegramStarsSettings = Field(default_factory=TelegramStarsSettings)
    trial: TrialSettings = Field(default_factory=TrialSettings)
    referral: ReferralSettings = Field(default_factory=ReferralSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    prometheus: PrometheusSettings = Field(default_factory=PrometheusSettings)

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list[int]) -> list[int]:
        """Parse comma-separated string of admin IDs into list[int].

        Accepts: "123,456,789" or [123, 456, 789]
        """
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(id_.strip()) for id_ in v.split(",") if id_.strip()]
        if isinstance(v, list):
            return [int(i) for i in v]
        return v

    @field_validator("available_languages", mode="before")
    @classmethod
    def parse_available_languages(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated languages or pass list through."""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",") if lang.strip()]
        return v

    @model_validator(mode="after")
    def _validate_webhook_settings(self) -> BotSettings:
        """Ensure webhook URL is set when mode is webhook."""
        if self.bot_mode == "webhook":
            if self.webhook.url is None:
                msg = "WEBHOOK_URL is required when BOT_MODE=webhook"
                raise ValueError(msg)
            if self.webhook.secret_token is None:
                msg = "WEBHOOK_SECRET_TOKEN is required when BOT_MODE=webhook"
                raise ValueError(msg)
        return self

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def is_admin(self, telegram_id: int) -> bool:
        """Check if a Telegram user ID is in the admin list."""
        return telegram_id in self.admin_ids

    @property
    def has_any_payment_gateway(self) -> bool:
        """Check if at least one payment gateway is enabled."""
        return self.cryptobot.enabled or self.yookassa.enabled or self.telegram_stars.enabled


@lru_cache(maxsize=1)
def get_settings() -> BotSettings:
    """Cached singleton accessor for bot settings.

    Returns the same BotSettings instance on every call.
    Settings are loaded once from environment / .env file.
    """
    return BotSettings()  # type: ignore[call-arg]
