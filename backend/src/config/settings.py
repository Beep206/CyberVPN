import logging
from typing import ClassVar

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Environment (must be first for validators to access it)
    environment: str = "development"  # development, staging, production

    # Database
    database_url: str = "postgresql+asyncpg://cybervpn:cybervpn@localhost:6767/cybervpn"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Remnawave API
    remnawave_url: str = "http://localhost:3000"
    remnawave_token: SecretStr

    # JWT
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # CORS (SEC-013: Default to empty list, require explicit config)
    cors_origins: list[str] = []

    # GitHub OAuth (optional)
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")

    # Telegram OAuth
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_bot_username: str = ""  # Bot username without @
    telegram_auth_max_age_seconds: int = 86400  # 24 hours

    # Payment gateway
    cryptobot_token: SecretStr

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
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

    # Security Settings (MED-1, MED-4, MED-5, MED-7)
    debug: bool = False  # Debug mode - should be False in production
    rate_limit_fail_open: bool = False  # MED-1: Fail-closed in production
    mobile_rate_limit_fail_open: bool = False  # MED-4: Mobile rate limit fail-closed
    jwt_allowed_algorithms: list[str] = ["HS256", "HS384", "HS512"]  # MED-5: Allowlist
    swagger_enabled: bool = False  # SEC-008: Disabled by default, enable via env for dev

    # TOTP Encryption (MED-6)
    totp_encryption_key: SecretStr = SecretStr("")  # AES-256 key for TOTP secrets

    # Log Sanitization (LOW-4)
    log_sanitization_enabled: bool = True  # Sanitize sensitive data in logs

    # Trusted Proxy (MED-8)
    trusted_proxy_ips: list[str] = []  # List of trusted proxy IPs for X-Forwarded-For

    # Token Device Binding (MED-2)
    enforce_token_binding: bool = False  # Strict fingerprint validation on token refresh

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("jwt_issuer", "jwt_audience", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    # SEC-004 + MED-005: Known weak/test secrets to reject in production
    WEAK_SECRET_PATTERNS: ClassVar[frozenset[str]] = frozenset({
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
    })

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
                f"Generate with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )

        # SEC-004: Reject weak secrets in production
        environment = info.data.get("environment", "development")
        if environment == "production":
            secret_lower = secret.lower()
            for weak in cls.WEAK_SECRET_PATTERNS:
                if weak in secret_lower:
                    raise ValueError(
                        f"JWT_SECRET appears to be a weak/test secret (contains '{weak}'). "
                        f"Generate a strong secret: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
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
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v


settings = Settings()
