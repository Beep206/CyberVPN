import json
import logging
from typing import Annotated, ClassVar, Literal, Self
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode

_logger = logging.getLogger(__name__)

S1_PRODUCTION_CORS_ORIGINS = frozenset(
    {
        "https://cyber-vpn.net",
        "https://my.cyber-vpn.net",
        "https://admin.cyber-vpn.net",
    }
)
S1_REDIRECT_ONLY_ORIGINS = frozenset(
    {
        "https://cyber-vpn.org",
        "https://admin.cyber-vpn.org",
    }
)
S1_PRODUCTION_COOKIE_DOMAINS = frozenset({"", "cyber-vpn.net"})
S1_PRODUCTION_ADMIN_ALLOWED_HOSTS = frozenset({"admin.cyber-vpn.net"})
S1_REDIRECT_ONLY_ADMIN_HOSTS = frozenset({"admin.cyber-vpn.org"})
S1_PUBLIC_NON_ADMIN_HOSTS = frozenset({"cyber-vpn.net", "my.cyber-vpn.net", "cyber-vpn.org"})


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Environment (must be first for validators to access it)
    environment: str = "development"  # development, staging, production

    # Database
    database_url: str = "postgresql+asyncpg://cybervpn:cybervpn@localhost:6767/cybervpn"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 100
    redis_pool_wait_seconds: float = 5.0

    # Remnawave API
    remnawave_url: str = "http://localhost:3000"
    remnawave_token: SecretStr
    remnawave_webhook_secret: SecretStr = SecretStr("")
    remnawave_webhook_max_age_seconds: int = 300
    remnawave_webhook_future_skew_seconds: int = 60
    remnawave_default_user_expire_days: int = 7
    remnawave_default_internal_squad_uuid: str = ""
    remnawave_default_internal_squad_name: str = "Default-Squad"
    remnawave_subscription_public_base_url: str = "https://cyber-vpn.org/api/sub"
    remnawave_ru_bundle_external_squad_uuid: str = ""
    remnawave_ru_bundle_plan_codes: str = "ru_start,ru_basic"
    remnawave_ru_bundle_subscription_template_name: str = "Mihomo (RU bundle)"
    remnawave_request_retries: int = 1
    remnawave_retry_backoff_seconds: float = 0.25
    stage1_trial_provisioning_enabled: bool = False
    stage1_paid_provisioning_enabled: bool = False
    stage1_addons_enabled: bool = False
    referral_enabled: bool = False
    promo_codes_enabled: bool = False
    gift_codes_enabled: bool = False
    checkout_code_discounts_enabled: bool = False

    # Helix adapter
    helix_enabled: bool = False
    helix_admin_enabled: bool = False
    helix_adapter_url: str = "http://localhost:8090"
    helix_adapter_token: SecretStr = SecretStr("")
    helix_default_channel: str = "lab"

    # JWT
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # CORS (SEC-013: Default to empty list, require explicit config)
    cors_origins: Annotated[list[str], NoDecode] = []

    # Canonical frontend origin for server-owned web OAuth callbacks
    oauth_web_base_url: str = ""

    # OAuth redirect allowlist for explicit native/universal callbacks (exact URI match)
    oauth_allowed_redirect_uris: Annotated[list[str], NoDecode] = ["cybervpn://oauth/callback"]

    # Active OAuth login providers (rollout gate)
    oauth_enabled_login_providers: Annotated[list[str], NoDecode] = [
        "google",
        "github",
    ]

    # Only these providers may auto-link to an existing account by email
    oauth_trusted_email_link_providers: Annotated[list[str], NoDecode] = [
        "google",
        "github",
    ]

    # OAuth provider token encryption (prefer dedicated key, fallback to TOTP key)
    oauth_token_encryption_key: SecretStr = SecretStr("")
    oauth_token_plaintext_fallback_enabled: bool = True
    oauth_retained_access_token_providers: Annotated[list[str], NoDecode] = []
    oauth_retained_refresh_token_providers: Annotated[list[str], NoDecode] = []

    # GitHub OAuth (optional)
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")

    # Telegram OAuth
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_bot_username: str = ""  # Bot username without @
    telegram_auth_max_age_seconds: int = 86400  # 24 hours
    telegram_oidc_client_id: str = ""
    telegram_oidc_client_secret: SecretStr = SecretStr("")
    telegram_oidc_issuer: str = "https://oauth.telegram.org"
    telegram_oidc_discovery_url: str = "https://oauth.telegram.org/.well-known/openid-configuration"
    telegram_oidc_jwks_url: str = "https://oauth.telegram.org/.well-known/jwks.json"
    telegram_oidc_allowed_audience: str = ""
    telegram_oidc_clock_skew_seconds: int = 60
    telegram_bot_internal_secret: SecretStr = SecretStr("")
    frontend_observability_internal_secret: SecretStr = SecretStr("")

    # Google OAuth (optional)
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")

    # Discord OAuth (optional)
    discord_client_id: str = ""
    discord_client_secret: SecretStr = SecretStr("")

    # Facebook OAuth (optional)
    facebook_client_id: str = ""
    facebook_client_secret: SecretStr = SecretStr("")

    # Apple Sign In (optional)
    apple_client_id: str = ""
    apple_team_id: str = ""
    apple_key_id: str = ""
    apple_private_key: SecretStr = SecretStr("")

    # Microsoft OAuth (optional)
    microsoft_client_id: str = ""
    microsoft_client_secret: SecretStr = SecretStr("")
    microsoft_tenant_id: str = "common"

    # X/Twitter OAuth (optional)
    twitter_client_id: str = ""
    twitter_client_secret: SecretStr = SecretStr("")

    # Magic Link
    magic_link_ttl_seconds: int = 900  # 15 minutes
    magic_link_rate_limit: int = 5  # Max requests per hour per email
    magic_link_base_url: str = ""  # Base URL for magic link emails

    # Payment gateway
    cryptobot_token: SecretStr
    cryptobot_network: Literal["mainnet", "testnet"] = "mainnet"
    payments_enabled: bool = True
    telegram_stars_enabled: bool = True
    payment_reconciliation_enabled: bool = True
    payment_autorenewal_enabled: bool = False
    payment_orphan_max_age_hours: int = 24
    growth_code_hash_secret: SecretStr = SecretStr("")
    growth_reporting_rollup_retention_days: int = 180
    growth_reporting_refresh_run_retention_days: int = 180
    growth_reporting_delivery_retention_days: int = 90

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    json_logs: bool = True  # Enable JSON structured logging (False = human-readable console)

    # API server runtime
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    uvicorn_access_log: bool = False
    uvicorn_server_header: bool = False
    uvicorn_date_header: bool = True
    uvicorn_backlog: int = 2048
    uvicorn_timeout_keep_alive: int = 5
    uvicorn_timeout_graceful_shutdown: int = 30
    uvicorn_limit_concurrency: int | None = None
    uvicorn_limit_max_requests: int | None = None

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    helix_admin_read_rate_limit_requests: int = 1500
    rate_limit_auth_sensitive_requests: int = 20
    rate_limit_payment_write_requests: int = 30
    rate_limit_trial_activate_requests: int = 10
    rate_limit_growth_sensitive_requests: int = 60
    rate_limit_support_write_requests: int = 30
    trust_proxy_headers: bool = False

    # OTP Configuration
    otp_expiration_hours: int = 3
    otp_max_attempts: int = 5
    otp_max_resends: int = 3
    otp_resend_window_hours: int = 1
    otp_resend_cooldown_seconds: int = 30

    # Registration Security (CRIT-1)
    registration_enabled: bool = False  # Disabled by default for security
    registration_invite_required: bool = True  # Require invite token when enabled
    invite_token_expiry_hours: int = 24  # Invite tokens expire after 24 hours
    telegram_miniapp_bootstrap_usernames: str = ""  # Comma-separated one-time owner bootstrap allowlist
    telegram_bot_bootstrap_usernames: str = ""  # Comma-separated Telegram Bot closed-beta bootstrap allowlist

    # Security Settings (MED-1, MED-4, MED-5, MED-7)
    debug: bool = False  # Debug mode - should be False in production
    rate_limit_fail_open: bool = False  # MED-1: Fail-closed in production
    mobile_rate_limit_fail_open: bool = False  # MED-4: Mobile rate limit fail-closed
    jwt_allowed_algorithms: Annotated[list[str], NoDecode] = ["HS256", "HS384", "HS512"]  # MED-5: Allowlist
    swagger_enabled: bool = False  # SEC-008: Disabled by default, enable via env for dev
    csrf_protection_enabled: bool = True  # S1-BE-006: Origin/Referer guard for cookie-auth unsafe methods

    # TOTP Encryption (MED-6)
    totp_encryption_key: SecretStr = SecretStr("")  # AES-256 key for TOTP secrets

    # Log Sanitization (LOW-4)
    log_sanitization_enabled: bool = True  # Sanitize sensitive data in logs

    # Trusted Proxy (MED-8)
    trusted_proxy_ips: Annotated[list[str], NoDecode] = []  # List of trusted proxy IPs for X-Forwarded-For

    # Admin access boundary (S1-ADM-001)
    admin_host_protection_enabled: bool = True
    admin_allowed_hosts: Annotated[list[str], NoDecode] = ["admin.cyber-vpn.net"]
    admin_2fa_required: bool = False

    # Token Device Binding (MED-2)
    enforce_token_binding: bool = False  # Strict fingerprint validation on token refresh

    # Cookie settings (SEC-01)
    cookie_domain: str = ""  # Leave empty for current domain
    cookie_secure: bool = True  # Set to False for local HTTP development

    # Metrics (SEC-02)
    enable_metrics: bool = True  # Enable HTTP Prometheus middleware metrics
    metrics_host: str = "0.0.0.0"
    metrics_port: int = 9091  # Separate port for /metrics, not exposed publicly

    # Partner event backbone / realtime
    partner_portal_enabled: bool = False
    partner_applications_enabled: bool = False
    partner_codes_enabled: bool = False
    partner_attribution_enabled: bool = False
    partner_storefronts_enabled: bool = False
    partner_reporting_enabled: bool = False
    partner_settlement_sandbox_enabled: bool = False
    partner_webhooks_enabled: bool = False
    partner_payouts_enabled: bool = False
    partner_event_backbone_enabled: bool = False
    nats_url: str = "nats://localhost:4222"
    nats_partner_stream_name: str = "PARTNER_EVENTS"
    nats_partner_subject_prefix: str = "partner"
    outbox_dispatch_batch_size: int = 100
    outbox_dispatch_interval_seconds: float = 1.0
    outbox_dispatch_lease_seconds: int = 30
    outbox_dispatch_retry_after_seconds: int = 5
    outbox_dispatch_dead_letter_after_attempts: int = 5
    nats_consumer_fetch_batch_size: int = 25
    nats_consumer_fetch_timeout_seconds: float = 1.0
    partner_realtime_backlog_limit: int = 100

    # PostHog product intelligence
    posthog_enabled: bool = False
    posthog_host: str = ""
    posthog_project_api_key: SecretStr = SecretStr("")
    posthog_timeout_seconds: float = 5.0

    # Sentry (Observability)
    sentry_dsn: str = ""  # Sentry DSN for error tracking (optional, empty = disabled)
    sentry_release: str = ""  # Canonical Sentry release name (optional, empty = auto/disabled)

    # OpenTelemetry (Distributed Tracing)
    otel_exporter_endpoint: str = "http://otel-collector:4317"  # OTLP gRPC endpoint
    otel_service_name: str = "cybervpn-backend"  # Service name in traces
    otel_enabled: bool = True  # Enable OpenTelemetry tracing

    @field_validator(
        "cors_origins",
        "oauth_allowed_redirect_uris",
        "oauth_enabled_login_providers",
        "oauth_trusted_email_link_providers",
        "oauth_retained_access_token_providers",
        "oauth_retained_refresh_token_providers",
        "jwt_allowed_algorithms",
        "trusted_proxy_ips",
        "admin_allowed_hosts",
        mode="before",
    )
    @classmethod
    def parse_str_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            normalized = v.strip()
            if not normalized:
                return []

            if normalized.startswith("["):
                parsed = json.loads(normalized)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]

            return [origin.strip() for origin in normalized.split(",") if origin.strip()]
        return v

    @field_validator("admin_host_protection_enabled", mode="after")
    @classmethod
    def validate_admin_host_protection_enabled(cls, v: bool, info) -> bool:
        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and not v:
            raise ValueError("ADMIN_HOST_PROTECTION_ENABLED=false is not allowed in production.")
        return v

    @field_validator("admin_2fa_required", mode="after")
    @classmethod
    def validate_admin_2fa_required(cls, v: bool, info) -> bool:
        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and not v:
            raise ValueError("ADMIN_2FA_REQUIRED=false is not allowed in production.")
        return v

    @field_validator("admin_allowed_hosts", mode="after")
    @classmethod
    def validate_admin_allowed_hosts(cls, v: list[str], info) -> list[str]:
        environment = str(info.data.get("environment", "development")).lower()
        normalized_hosts: list[str] = []

        for host in v:
            normalized = host.strip().lower().lstrip(".")
            if not normalized:
                continue
            if "://" in normalized or "/" in normalized or "?" in normalized or "#" in normalized:
                raise ValueError("ADMIN_ALLOWED_HOSTS entries must be bare hostnames, not URLs.")
            if ":" in normalized and not normalized.startswith("["):
                raise ValueError("ADMIN_ALLOWED_HOSTS entries must not include ports.")
            normalized_hosts.append(normalized.strip("[]"))

        if environment == "production":
            if not normalized_hosts:
                raise ValueError("ADMIN_ALLOWED_HOSTS must include the approved S1 admin host in production.")
            if S1_PRODUCTION_ADMIN_ALLOWED_HOSTS - set(normalized_hosts):
                raise ValueError("ADMIN_ALLOWED_HOSTS must include admin.cyber-vpn.net in S1 production.")
            invalid_hosts = set(normalized_hosts) & (S1_REDIRECT_ONLY_ADMIN_HOSTS | S1_PUBLIC_NON_ADMIN_HOSTS)
            if invalid_hosts:
                raise ValueError(
                    "ADMIN_ALLOWED_HOSTS must not include public or redirect-only hosts in S1 production."
                )
            if set(normalized_hosts) - S1_PRODUCTION_ADMIN_ALLOWED_HOSTS:
                raise ValueError("ADMIN_ALLOWED_HOSTS contains hostnames not approved for S1 production.")

        return normalized_hosts

    @field_validator("cors_origins", mode="after")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info) -> list[str]:
        """Validate browser origins before wiring CORS middleware."""
        environment = str(info.data.get("environment", "development")).lower()
        normalized_origins: list[str] = []

        for origin in v:
            normalized = origin.strip().rstrip("/")
            if normalized == "*":
                normalized_origins.append(normalized)
                continue

            parsed = urlparse(normalized)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS_ORIGINS entries must be absolute http(s) origins.")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError("CORS_ORIGINS entries must not include path, query, or fragment.")

            origin_value = f"{parsed.scheme}://{parsed.netloc}"
            normalized_origins.append(origin_value)

        if environment == "production":
            if not normalized_origins:
                raise ValueError("CORS_ORIGINS must include approved S1 browser origins in production.")
            if "*" in normalized_origins:
                raise ValueError("CORS_ORIGINS='*' is not allowed in production.")

            for origin in normalized_origins:
                if not origin.startswith("https://"):
                    raise ValueError("Production CORS_ORIGINS must use https origins.")
                if origin in S1_REDIRECT_ONLY_ORIGINS:
                    raise ValueError("cyber-vpn.org origins are redirect-only in S1 and must not call the API.")
                if origin not in S1_PRODUCTION_CORS_ORIGINS:
                    raise ValueError(f"Production CORS origin is not approved for S1: {origin}")

        return normalized_origins

    @field_validator("jwt_issuer", "jwt_audience", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, v: bool | str | None) -> bool | str | None:
        """Accept common host-environment variants instead of crashing startup."""
        if not isinstance(v, str):
            return v

        normalized = v.strip().lower()
        if normalized in {"release", "prod", "production"}:
            return False
        if normalized in {"debug", "dev", "development"}:
            return True

        return v

    @field_validator("oauth_web_base_url", mode="before")
    @classmethod
    def normalize_oauth_web_base_url(cls, v: str | None) -> str:
        if v is None:
            return ""
        return v.strip()

    @field_validator("oauth_web_base_url", mode="after")
    @classmethod
    def validate_oauth_web_base_url(cls, v: str | None) -> str:
        """Normalize the canonical frontend origin used for web OAuth callbacks."""
        if not v:
            return ""

        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OAUTH_WEB_BASE_URL must be an absolute http(s) origin.")

        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            raise ValueError("OAUTH_WEB_BASE_URL must not include a path, query, or fragment.")

        return f"{parsed.scheme}://{parsed.netloc}"

    @model_validator(mode="after")
    def validate_s2_oauth_login_provider_credentials(self) -> Self:
        """Fail fast if a production OAuth login provider is enabled without credentials."""
        enabled = {provider.strip().lower() for provider in self.oauth_enabled_login_providers if provider.strip()}
        unsupported = enabled - {"google", "github"}
        if unsupported:
            raise ValueError("OAUTH_ENABLED_LOGIN_PROVIDERS only supports google and github in S2.")

        if self.environment.lower() != "production" or not enabled:
            return self

        if not self.oauth_web_base_url:
            raise ValueError(
                "OAUTH_WEB_BASE_URL is required in production when OAuth login providers are enabled."
            )
        if "google" in enabled and (
            not self.google_client_id.strip() or not self.google_client_secret.get_secret_value().strip()
        ):
            raise ValueError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required in production "
                "when google OAuth login is enabled."
            )
        if "github" in enabled and (
            not self.github_client_id.strip() or not self.github_client_secret.get_secret_value().strip()
        ):
            raise ValueError(
                "GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are required in production "
                "when github OAuth login is enabled."
            )

        return self

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, v: str | None) -> str:
        if v is None:
            return ""
        return v.strip().lower().lstrip(".")

    @field_validator("cookie_domain", mode="after")
    @classmethod
    def validate_cookie_domain(cls, v: str, info) -> str:
        if not v:
            return ""

        if "://" in v or "/" in v or ":" in v or "?" in v or "#" in v:
            raise ValueError("COOKIE_DOMAIN must be a bare hostname, not a URL.")

        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and v not in S1_PRODUCTION_COOKIE_DOMAINS:
            raise ValueError("COOKIE_DOMAIN must be empty for host-only cookies or 'cyber-vpn.net' in S1 production.")

        return v

    @field_validator("cookie_secure", mode="after")
    @classmethod
    def validate_cookie_secure(cls, v: bool, info) -> bool:
        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and not v:
            raise ValueError("COOKIE_SECURE=false is not allowed in production.")
        return v

    @field_validator("csrf_protection_enabled", mode="after")
    @classmethod
    def validate_csrf_protection_enabled(cls, v: bool, info) -> bool:
        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and not v:
            raise ValueError("CSRF_PROTECTION_ENABLED=false is not allowed in production.")
        return v

    @field_validator("cryptobot_network", mode="after")
    @classmethod
    def validate_cryptobot_network(cls, v: str, info) -> str:
        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and v != "mainnet":
            raise ValueError("CRYPTOBOT_NETWORK=testnet is not allowed in production.")
        return v

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

    @field_validator("cryptobot_token", mode="after")
    @classmethod
    def validate_cryptobot_token(cls, v: SecretStr, info) -> SecretStr:
        environment = str(info.data.get("environment", "development")).lower()
        token = v.get_secret_value().strip()

        if environment != "production":
            return SecretStr(token)

        if len(token) < 16:
            raise ValueError("CRYPTOBOT_TOKEN must be a real provider token in production.")

        token_lower = token.lower()
        for marker in cls.PROVIDER_SECRET_PLACEHOLDER_PATTERNS:
            if marker in token_lower:
                raise ValueError("CRYPTOBOT_TOKEN must not be a placeholder/test value in production.")

        return SecretStr(token)

    # SEC-004 + MED-005: Known weak/test secrets to reject in production
    WEAK_SECRET_PATTERNS: ClassVar[frozenset[str]] = frozenset(
        {
            "test_token",
            "test_secret",
            "dev_secret",
            "local_secret",
            "dummy_secret",
            "changeme",
            "password",
            "secret",
            "development",
            "example",
            "placeholder",
        }
    )

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: SecretStr, info) -> SecretStr:
        """SEC-014 + SEC-004: Validate JWT secret length and reject weak secrets.

        HS256 requires 256-bit (32 bytes) key minimum per RFC 7518.
        In production, also reject known weak/test secrets.
        """
        secret = v.get_secret_value()
        min_length = 32

        if len(secret) < min_length:
            raise ValueError(
                f"JWT_SECRET must be at least {min_length} characters for security. "
                f"Current length: {len(secret)}. "
                f'Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )

        # SEC-004: Reject weak secrets in production
        environment = info.data.get("environment", "development")
        if environment == "production":
            secret_lower = secret.lower()
            for weak in cls.WEAK_SECRET_PATTERNS:
                if weak in secret_lower:
                    raise ValueError(
                        f"JWT_SECRET appears to be a weak/test secret (contains '{weak}'). "
                        f'Generate a strong secret: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                    )

        return v

    @field_validator("totp_encryption_key", mode="after")
    @classmethod
    def warn_missing_totp_key(cls, v: SecretStr) -> SecretStr:
        """Warn if TOTP encryption key is not set (HIGH-001 remediation)."""
        if not v.get_secret_value():
            _logger.warning(
                "TOTP_ENCRYPTION_KEY not set - TOTP secrets will be unencrypted. "
                "This is acceptable for development only. "
                'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return v

    @field_validator("oauth_token_encryption_key", mode="after")
    @classmethod
    def warn_missing_oauth_token_key(cls, v: SecretStr, info) -> SecretStr:
        """Warn or fail closed when provider-token encryption is not configured."""
        if v.get_secret_value():
            return v

        environment = info.data.get("environment", "development")
        totp_key = info.data.get("totp_encryption_key")
        has_totp_key = isinstance(totp_key, SecretStr) and bool(totp_key.get_secret_value())

        if environment == "production" and not has_totp_key:
            raise ValueError(
                "OAUTH_TOKEN_ENCRYPTION_KEY (or TOTP_ENCRYPTION_KEY fallback) must be configured in production."
            )

        _logger.warning(
            "OAUTH_TOKEN_ENCRYPTION_KEY not set - provider tokens will use TOTP_ENCRYPTION_KEY if available, "
            "otherwise plaintext fallback remains enabled."
        )
        return v


settings = Settings()
