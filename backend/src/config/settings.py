from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

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

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # GitHub OAuth (optional)
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")

    # Telegram OAuth
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_bot_username: str = ""  # Bot username without @
    telegram_auth_max_age_seconds: int = 86400  # 24 hours

    # Payment gateway
    cryptobot_token: SecretStr

    # Environment
    environment: str = "development"  # development, staging, production

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

    # Security Settings (MED-1, MED-5, MED-7)
    debug: bool = False  # Debug mode - should be False in production
    rate_limit_fail_open: bool = False  # MED-1: Fail-closed in production
    jwt_allowed_algorithms: list[str] = ["HS256", "HS384", "HS512"]  # MED-5: Allowlist
    swagger_enabled: bool = True  # MED-7: Disable in production via env

    # TOTP Encryption (MED-6)
    totp_encryption_key: SecretStr = SecretStr("")  # AES-256 key for TOTP secrets

    # Trusted Proxy (MED-8)
    trusted_proxy_ips: list[str] = []  # List of trusted proxy IPs for X-Forwarded-For

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


settings = Settings()
