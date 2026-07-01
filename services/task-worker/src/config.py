"""Configuration management for task-worker microservice.

Uses Pydantic Settings for type-safe configuration loading from environment variables.
Settings are cached as a singleton using lru_cache for performance.
"""

from functools import lru_cache
from typing import Annotated, ClassVar, Literal
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator, model_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic_settings import NoDecode as _NoDecode
except ImportError:  # pragma: no cover - compatibility with older local pydantic-settings builds
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class _NoDecode:  # type: ignore[no-redef]
        """Compatibility shim for pydantic-settings versions without NoDecode."""

        pass


NoDecode = _NoDecode


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    PROVIDER_SECRET_PLACEHOLDER_PATTERNS: ClassVar[frozenset[str]] = frozenset(
        {
            "<",
            "changeme",
            "dev",
            "dummy",
            "example",
            "local",
            "placeholder",
            "redacted",
            "replace",
            "test",
            "your_",
        }
    )

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
    backend_api_url: str | None = None
    backend_internal_secret: SecretStr | None = None
    telegram_bot_internal_secret: SecretStr | None = None
    payment_settlement_worker_secret: SecretStr | None = None
    helix_enabled: bool = False
    helix_adapter_url: str = "http://localhost:8090"
    helix_adapter_token: SecretStr = SecretStr("")

    # Bot Tokens
    telegram_bot_token: SecretStr
    cryptobot_token: SecretStr
    cryptobot_network: Literal["mainnet", "testnet"] = "mainnet"

    # Admin Configuration — env var is comma-separated string, parsed to list[int]
    admin_telegram_ids: Annotated[list[int], NoDecode] = []

    # Worker Configuration
    worker_concurrency: int = 2
    result_ttl_seconds: int = 3600
    stage1_provisioning_retry_claiming_enabled: bool = False
    stage1_provisioning_retry_batch_limit: int = 25
    payment_completed_partner_earnings_enabled: bool = True
    payment_completed_partner_earnings_batch_limit: int = 25
    vpn_tester_enabled: bool = False
    vpn_tester_runtime_enabled: bool = False
    vpn_tester_synthetic_users_enabled: bool = False
    vpn_tester_scheduled_enabled: bool = False
    vpn_tester_balancer_recommendations_enabled: bool = False
    vpn_tester_queue_batch_limit: int = 5
    vpn_tester_lock_ttl_seconds: int = 600

    # Notification Settings
    notification_max_retries: int = 5
    notification_batch_size: int = 50
    messaging_outbox_batch_size: int = 50
    messaging_outbox_lease_seconds: int = 30
    messaging_outbox_retry_after_seconds: int = 30
    messaging_outbox_dead_letter_after_attempts: int = 5

    # Health Check Configuration
    health_check_interval_seconds: int = 120
    helix_stale_heartbeat_seconds: int = 180
    helix_rollback_alert_threshold: int = 1
    helix_rollout_min_connect_success_rate: float = 0.95
    helix_rollout_max_fallback_rate: float = 0.05
    helix_rollout_min_continuity_success_rate: float = 0.80
    helix_rollout_min_cross_route_recovery_rate: float = 0.20
    helix_alert_state_ttl_seconds: int = 3600
    helix_actuation_escalation_seconds: int = 900
    helix_canary_min_connect_success_rate: float = 0.98
    helix_canary_max_fallback_rate: float = 0.03
    helix_canary_min_continuity_observations: int = 5
    helix_canary_require_throughput_evidence: bool = True
    helix_canary_min_relative_throughput_ratio: float = 0.90
    helix_canary_max_relative_open_to_first_byte_gap_ratio: float = 1.15

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
    sentry_release: str = ""  # Canonical Sentry release name (optional, empty = auto/disabled)

    # Email Provider Configuration (OTP)
    # Optional fallback: Resend.com
    resend_api_key: SecretStr | None = None
    resend_from_email: str = "CyberVPN <verify@email.cyber-vpn.net>"

    # Optional legacy API provider configuration
    brevo_api_key: SecretStr | None = None
    brevo_from_email: str = "CyberVPN <noreply@email.cyber-vpn.net>"

    # Magic Link
    magic_link_base_url: str = "http://localhost:9001"  # Frontend URL for magic link emails

    # Dev/Test environment: Use Mailpit cluster for email testing
    # Set EMAIL_DEV_MODE=true to use SMTP instead of API providers
    email_dev_mode: bool = False
    email_resend_fallback_enabled: bool = False
    email_task_payload_ttl_seconds: int = 14400
    email_verified_sender_domains: Annotated[list[str], NoDecode] = []

    # Production SMTP primary route. Credentials must be supplied by runtime
    # secret storage; never commit mailbox passwords to source.
    smtp_host: str = "mail.cyber-vpn.net"
    smtp_port: int = 587
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_auth_username: str = ""
    smtp_auth_password: SecretStr | None = None
    smtp_system_from_email: str = "CyberVPN <noreply@cyber-vpn.net>"
    smtp_billing_from_email: str = "CyberVPN Billing <billing@cyber-vpn.net>"
    smtp_support_from_email: str = "CyberVPN Support <support@cyber-vpn.net>"

    # Mailpit SMTP servers (round-robin for provider rotation testing)
    # Format: host:port,host:port,host:port
    smtp_servers: Annotated[list[str], NoDecode] = [
        "localhost:1025",
        "localhost:1026",
        "localhost:1027",
    ]
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

    @field_validator("email_verified_sender_domains", mode="before")
    @classmethod
    def parse_email_verified_sender_domains(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        if not isinstance(v, str) or not v.strip():
            return []
        return [domain.strip().lower().lstrip(".") for domain in v.split(",") if domain.strip()]

    @field_validator("email_task_payload_ttl_seconds", mode="after")
    @classmethod
    def validate_email_task_payload_ttl_seconds(cls, v: int) -> int:
        if v < 300 or v > 86400:
            msg = "EMAIL_TASK_PAYLOAD_TTL_SECONDS must be between 300 and 86400 seconds"
            raise ValueError(msg)
        return v

    @staticmethod
    def _secret_value(secret: SecretStr | None) -> str:
        if secret is None:
            return ""
        return secret.get_secret_value().strip()

    @staticmethod
    def _sender_domain(from_email: str) -> str:
        value = from_email.strip()
        if "<" in value and ">" in value:
            value = value.split("<", 1)[1].split(">", 1)[0].strip()
        if "@" not in value:
            return ""
        return value.rsplit("@", 1)[1].lower().lstrip(".")

    @classmethod
    def _reject_placeholder_provider_secret(cls, *, field_name: str, secret: str) -> None:
        if len(secret) < 16:
            msg = f"{field_name} must be a real provider token in production"
            raise ValueError(msg)
        lowered = secret.lower()
        if any(marker in lowered for marker in cls.PROVIDER_SECRET_PLACEHOLDER_PATTERNS):
            msg = f"{field_name} must not be a placeholder/test value in production"
            raise ValueError(msg)

    @classmethod
    def _reject_placeholder_config_value(cls, *, field_name: str, value: str) -> None:
        lowered = value.strip().lower()
        if any(marker in lowered for marker in cls.PROVIDER_SECRET_PLACEHOLDER_PATTERNS):
            msg = f"{field_name} must not be a placeholder/test value in production"
            raise ValueError(msg)

    @model_validator(mode="after")
    def validate_metrics_settings(self) -> "Settings":
        has_backend_url = self.backend_api_url is not None and bool(str(self.backend_api_url).strip())
        has_backend_secret = self.backend_internal_secret is not None and bool(
            self.backend_internal_secret.get_secret_value().strip()
        )
        has_telegram_bot_internal_secret = self.telegram_bot_internal_secret is not None and bool(
            self.telegram_bot_internal_secret.get_secret_value().strip()
        )
        has_payment_settlement_worker_secret = self.payment_settlement_worker_secret is not None and bool(
            self.payment_settlement_worker_secret.get_secret_value().strip()
        )
        if self.environment.lower() == "production" and self.cryptobot_network != "mainnet":
            msg = "CRYPTOBOT_NETWORK=testnet is not allowed in production"
            raise ValueError(msg)
        if self.environment.lower() == "production":
            cryptobot_token = self.cryptobot_token.get_secret_value().strip()
            if len(cryptobot_token) < 16:
                msg = "CRYPTOBOT_TOKEN must be a real provider token in production"
                raise ValueError(msg)
            token_lower = cryptobot_token.lower()
            if any(marker in token_lower for marker in self.PROVIDER_SECRET_PLACEHOLDER_PATTERNS):
                msg = "CRYPTOBOT_TOKEN must not be a placeholder/test value in production"
                raise ValueError(msg)
        if self.environment.lower() == "production":
            if self.email_dev_mode:
                msg = "EMAIL_DEV_MODE=true is not allowed in production"
                raise ValueError(msg)

            parsed_magic_base = urlparse(self.magic_link_base_url.strip())
            if parsed_magic_base.scheme != "https" or not parsed_magic_base.netloc:
                msg = "MAGIC_LINK_BASE_URL must be a canonical https origin in production"
                raise ValueError(msg)
            if parsed_magic_base.path not in {"", "/"} or parsed_magic_base.params or parsed_magic_base.query:
                msg = "MAGIC_LINK_BASE_URL must not include path, params, or query in production"
                raise ValueError(msg)
            if parsed_magic_base.fragment:
                msg = "MAGIC_LINK_BASE_URL must not include a fragment in production"
                raise ValueError(msg)

            resend_secret = self._secret_value(self.resend_api_key)
            if self.email_resend_fallback_enabled:
                if not resend_secret:
                    msg = "RESEND_API_KEY is required when EMAIL_RESEND_FALLBACK_ENABLED=true in production"
                    raise ValueError(msg)
                self._reject_placeholder_provider_secret(field_name="RESEND_API_KEY", secret=resend_secret)
            elif resend_secret:
                self._reject_placeholder_provider_secret(field_name="RESEND_API_KEY", secret=resend_secret)

            brevo_secret = self._secret_value(self.brevo_api_key)
            if brevo_secret:
                self._reject_placeholder_provider_secret(field_name="BREVO_API_KEY", secret=brevo_secret)

            if not self.smtp_host.strip() or "://" in self.smtp_host or "/" in self.smtp_host:
                msg = "SMTP_HOST must be a bare SMTP hostname in production"
                raise ValueError(msg)
            self._reject_placeholder_config_value(field_name="SMTP_HOST", value=self.smtp_host)
            if not 1 <= int(self.smtp_port) <= 65535:
                msg = "SMTP_PORT must be between 1 and 65535"
                raise ValueError(msg)
            if self.smtp_starttls and self.smtp_use_ssl:
                msg = "SMTP_STARTTLS and SMTP_USE_SSL cannot both be true"
                raise ValueError(msg)
            if not self.smtp_starttls and not self.smtp_use_ssl:
                msg = "SMTP_STARTTLS or SMTP_USE_SSL must be enabled in production"
                raise ValueError(msg)
            if not self.smtp_auth_username.strip():
                msg = "SMTP_AUTH_USERNAME is required for production SMTP delivery"
                raise ValueError(msg)
            self._reject_placeholder_config_value(field_name="SMTP_AUTH_USERNAME", value=self.smtp_auth_username)
            smtp_password = self._secret_value(self.smtp_auth_password)
            if not smtp_password:
                msg = "SMTP_AUTH_PASSWORD is required for production SMTP delivery"
                raise ValueError(msg)
            self._reject_placeholder_config_value(field_name="SMTP_AUTH_PASSWORD", value=smtp_password)

            verified_domains = set(self.email_verified_sender_domains)
            required_domains = {
                self._sender_domain(self.smtp_system_from_email),
                self._sender_domain(self.smtp_billing_from_email),
                self._sender_domain(self.smtp_support_from_email),
            }
            if resend_secret:
                required_domains.add(self._sender_domain(self.resend_from_email))
            if brevo_secret:
                required_domains.add(self._sender_domain(self.brevo_from_email))
            missing_domains = sorted(domain for domain in required_domains if domain and domain not in verified_domains)
            if missing_domains:
                msg = "EMAIL_VERIFIED_SENDER_DOMAINS must include configured sender domains: " + ", ".join(
                    missing_domains
                )
                raise ValueError(msg)
        if has_backend_url != has_backend_secret:
            msg = "BACKEND_API_URL and BACKEND_INTERNAL_SECRET must be configured together"
            raise ValueError(msg)
        if self.environment.lower() == "production" and has_backend_url:
            backend_internal_secret = self.backend_internal_secret
            if backend_internal_secret is None:
                msg = "BACKEND_INTERNAL_SECRET is required when BACKEND_API_URL is configured in production"
                raise ValueError(msg)
            self._reject_placeholder_provider_secret(
                field_name="BACKEND_INTERNAL_SECRET",
                secret=backend_internal_secret.get_secret_value().strip(),
            )
            if not has_telegram_bot_internal_secret:
                msg = "TELEGRAM_BOT_INTERNAL_SECRET is required when BACKEND_API_URL is configured in production"
                raise ValueError(msg)
            telegram_bot_internal_secret = self.telegram_bot_internal_secret
            if telegram_bot_internal_secret is None:
                msg = "TELEGRAM_BOT_INTERNAL_SECRET is required when BACKEND_API_URL is configured in production"
                raise ValueError(msg)
            self._reject_placeholder_provider_secret(
                field_name="TELEGRAM_BOT_INTERNAL_SECRET",
                secret=telegram_bot_internal_secret.get_secret_value().strip(),
            )
            backend_secret = backend_internal_secret.get_secret_value().strip()
            telegram_secret = telegram_bot_internal_secret.get_secret_value().strip()
            if backend_secret and telegram_secret and backend_secret == telegram_secret:
                msg = "TELEGRAM_BOT_INTERNAL_SECRET must differ from BACKEND_INTERNAL_SECRET"
                raise ValueError(msg)
        if self.payment_completed_partner_earnings_enabled and self.environment.lower() == "production":
            if not has_backend_url:
                msg = "BACKEND_API_URL is required when payment completed partner earnings worker is enabled"
                raise ValueError(msg)
            if not has_payment_settlement_worker_secret:
                msg = (
                    "PAYMENT_SETTLEMENT_WORKER_SECRET is required when payment completed partner earnings worker "
                    "is enabled"
                )
                raise ValueError(msg)
            backend_internal_secret = self.backend_internal_secret
            if backend_internal_secret is None:
                msg = "BACKEND_INTERNAL_SECRET is required when payment completed partner earnings worker is enabled"
                raise ValueError(msg)
            payment_settlement_worker_secret = self.payment_settlement_worker_secret
            if payment_settlement_worker_secret is None:
                msg = (
                    "PAYMENT_SETTLEMENT_WORKER_SECRET is required when payment completed partner earnings worker "
                    "is enabled"
                )
                raise ValueError(msg)
            self._reject_placeholder_provider_secret(
                field_name="PAYMENT_SETTLEMENT_WORKER_SECRET",
                secret=payment_settlement_worker_secret.get_secret_value().strip(),
            )
            backend_secret = backend_internal_secret.get_secret_value().strip()
            worker_secret = payment_settlement_worker_secret.get_secret_value().strip()
            if backend_secret and worker_secret and backend_secret == worker_secret:
                msg = "PAYMENT_SETTLEMENT_WORKER_SECRET must differ from BACKEND_INTERNAL_SECRET"
                raise ValueError(msg)
            telegram_secret = (
                self.telegram_bot_internal_secret.get_secret_value().strip()
                if self.telegram_bot_internal_secret is not None
                else ""
            )
            if telegram_secret and worker_secret and telegram_secret == worker_secret:
                msg = "PAYMENT_SETTLEMENT_WORKER_SECRET must differ from TELEGRAM_BOT_INTERNAL_SECRET"
                raise ValueError(msg)
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
    return Settings()  # type: ignore[call-arg]
