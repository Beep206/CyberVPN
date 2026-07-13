import hmac
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
        "https://partner.cyber-vpn.net",
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
VPN_TEST_AGENT_LOCAL_HTTP_HOSTS = frozenset({"cybervpn-vpn-test-agent"})
S1_PRODUCTION_PASSKEY_ORIGINS = frozenset(
    {
        "https://cyber-vpn.net",
        "https://my.cyber-vpn.net",
        "https://admin.cyber-vpn.net",
        "https://partner.cyber-vpn.net",
    }
)
S1_LOCAL_STAGE_BROWSER_ORIGINS = frozenset(
    {
        "http://localhost:13000",
        "http://localhost:13001",
        "http://127.0.0.1:13000",
        "http://127.0.0.1:13001",
    }
)
S1_LOCAL_STAGE_ENVIRONMENTS = frozenset({"local-stage"})


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
    remnawave_webhook_max_body_bytes: int = 65536
    remnawave_default_user_expire_days: int = 7
    remnawave_lifetime_expiry_mode: Literal["sentinel", "none"] = "sentinel"
    remnawave_lifetime_expire_at: str = "2099-12-31T23:59:59Z"
    remnawave_default_internal_squad_uuid: str = ""
    remnawave_default_internal_squad_name: str = "CYBERVPN_PREMIUM_SMART_RU_NODES"
    remnawave_subscription_public_base_url: str = "https://cyber-vpn.org/api/sub"
    remnawave_ru_bundle_external_squad_uuid: str = ""
    remnawave_ru_bundle_plan_codes: str = "ru_start,ru_basic"
    remnawave_ru_bundle_subscription_template_name: str = "Mihomo (RU bundle)"
    remnawave_smart_ru_external_squad_uuid: str = ""
    remnawave_smart_ru_internal_squad_uuid: str = ""
    remnawave_smart_ru_plan_codes: str = "premium_smart_ru"
    remnawave_smart_ru_subscription_template_name: str = "CyberVPN Premium Smart RU"
    remnawave_spb_de_exceptions_external_squad_uuid: str = ""
    remnawave_spb_de_exceptions_internal_squad_uuid: str = ""
    remnawave_spb_de_exceptions_bridge_squad_uuid: str = ""
    remnawave_spb_de_exceptions_plan_codes: str = "premium_spb_de_exceptions"
    remnawave_spb_de_exceptions_profile_name: str = "S1 SPB DE Exceptions"
    remnawave_spb_de_exceptions_policy_version: str = "premium_spb_de_exceptions.v1"
    remnawave_spb_de_exceptions_data_plane_ready: bool = False
    remnawave_spb_de_exceptions_readiness_attestation: str = ""
    remnawave_spb_de_exceptions_readiness_attestation_path: str = ""
    remnawave_spb_de_exceptions_readiness_public_key: str = ""
    remnawave_spb_de_exceptions_readiness_public_key_path: str = ""
    remnawave_spb_de_exceptions_readiness_active_pointer: str = ""
    remnawave_spb_de_exceptions_readiness_active_pointer_path: str = ""
    remnawave_spb_de_exceptions_readiness_lkg_pointer: str = ""
    remnawave_spb_de_exceptions_readiness_lkg_pointer_path: str = ""
    remnawave_spb_de_exceptions_readiness_manifest: str = ""
    remnawave_spb_de_exceptions_readiness_store_path: str = ""
    remnawave_spb_de_exceptions_readiness_revoked_attestation_ids: str = ""
    remnawave_request_retries: int = 1
    remnawave_retry_backoff_seconds: float = 0.25
    remnawave_token_expires_at: str = ""
    remnawave_token_scope_label: str = ""
    remnawave_token_rotation_warning_days: int = 14
    remnawave_feature_xhttp_enabled: bool = False
    remnawave_feature_xhttp_mihomo_enabled: bool = False
    remnawave_feature_xhttp_rollout_mode: Literal["disabled", "internal", "canary", "premium_smart_ru", "stable"] = (
        "disabled"
    )
    remnawave_feature_xhttp_allowed_plan_codes: str = "premium_smart_ru"
    remnawave_feature_xhttp_allowed_user_segments: str = "internal,beta,premium_smart_ru_canary"
    remnawave_feature_xhttp_force_disabled: bool = False
    remnawave_feature_hysteria2_enabled: bool = False
    remnawave_feature_ech_enabled: bool = False
    remnawave_feature_tun_enabled: bool = False
    remnawave_feature_v2plus_enabled: bool = False
    remnawave_abuse_auto_disable_enabled: bool = False
    remnawave_abuse_torrent_disable_after: int = 2
    remnawave_abuse_torrent_window_hours: int = 24
    vpn_tester_enabled: bool = False
    vpn_tester_runtime_enabled: bool = False
    vpn_tester_synthetic_users_enabled: bool = False
    vpn_tester_scheduled_enabled: bool = False
    vpn_tester_balancer_recommendations_enabled: bool = False
    vpn_tester_retention_days: int = 30
    vpn_test_agent_url: str = ""
    vpn_test_agent_secret: SecretStr | None = None
    vpn_test_agent_moscow_url: str = ""
    vpn_test_agent_moscow_secret: SecretStr | None = None
    vpn_test_agent_spb_url: str = ""
    vpn_test_agent_spb_secret: SecretStr | None = None
    vpn_test_agent_timeout_seconds: int = 20
    vpn_test_agent_signature_max_skew_seconds: int = 60
    stage1_trial_provisioning_enabled: bool = False
    stage1_paid_provisioning_enabled: bool = False
    stage1_provisioning_retry_claiming_enabled: bool = False
    stage1_provisioning_retry_batch_limit: int = 25
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
    backend_internal_secret: SecretStr = SecretStr("")
    frontend_observability_internal_secret: SecretStr = SecretStr("")
    payment_settlement_worker_enabled: bool = True
    payment_settlement_worker_secret: SecretStr = SecretStr("")

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
    # Container ingress/firewall controls exposure for deployed API bind addresses.
    api_host: str = "0.0.0.0"  # nosec B104
    api_port: int = 8000
    uvicorn_access_log: bool = False
    uvicorn_server_header: bool = False
    uvicorn_date_header: bool = True
    uvicorn_backlog: int = 2048
    uvicorn_timeout_keep_alive: int = 5
    uvicorn_timeout_graceful_shutdown: int = 30
    uvicorn_limit_concurrency: int | None = None
    uvicorn_limit_max_requests: int | None = None
    request_body_limit_enabled: bool = True
    max_request_body_bytes: int = 1_048_576

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    helix_admin_read_rate_limit_requests: int = 1500
    rate_limit_auth_sensitive_requests: int = 20
    rate_limit_payment_write_requests: int = 30
    rate_limit_trial_activate_requests: int = 10
    rate_limit_growth_sensitive_requests: int = 60
    rate_limit_private_catalog_preflight_requests: int = 20
    rate_limit_support_write_requests: int = 30
    rate_limit_messaging_write_requests: int = 30
    rate_limit_messaging_realtime_requests: int = 60
    rate_limit_messaging_admin_read_requests: int = 120
    rate_limit_messaging_broadcast_requests: int = 10
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
    telegram_bot_registration_mode: Literal[
        "disabled",
        "allow_existing_only",
        "allow_with_invite_code",
        "allow_pending_onboarding",
        "allow_all_bot_users",
    ] = "allow_pending_onboarding"
    telegram_bot_allow_registration_when_public_closed: bool = True
    telegram_miniapp_url: str = "https://cyber-vpn.net/ru-RU/miniapp"
    telegram_miniapp_onboarding_url: str = "https://cyber-vpn.net/ru-RU/miniapp/onboarding/code"

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
    web_device_cookie_name: str = "__Host-cvpn_device_id"
    device_cookie_pepper_secret_name: str = "CYBERVPN_DEVICE_COOKIE_PEPPER"  # noqa: S105 - env var name only.

    # Passkey/WebAuthn 2.0
    passkey_enabled: bool = False
    passkey_customer_enabled: bool = False
    passkey_admin_enabled: bool = False
    passkey_partner_enabled: bool = False
    passkey_conditional_ui_enabled: bool = False
    passkey_customer_registration_prompt_enabled: bool = False
    passkey_admin_security_dashboard_enabled: bool = False
    passkey_partner_workspace_policy_enabled: bool = False
    passkey_admin_counts_as_mfa: bool = False
    passkey_dev_enabled: bool = False
    passkey_rp_id: str = "cyber-vpn.net"
    passkey_rp_name: str = "CyberVPN"
    passkey_allowed_origins: Annotated[list[str], NoDecode] = [
        "https://cyber-vpn.net",
        "https://my.cyber-vpn.net",
        "https://admin.cyber-vpn.net",
        "https://partner.cyber-vpn.net",
    ]
    passkey_dev_rp_id: str = "localhost"
    passkey_dev_allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3004",
        "http://admin.localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:9464",
    ]
    passkey_challenge_ttl_seconds: int = 300
    passkey_browser_timeout_ms: int = 60000
    passkey_fresh_auth_ttl_seconds: int = 300

    # Metrics (SEC-02)
    enable_metrics: bool = True  # Enable HTTP Prometheus middleware metrics
    # Deployment network policy controls metrics endpoint exposure.
    metrics_host: str = "0.0.0.0"  # nosec B104
    metrics_port: int = 9091  # Separate port for /metrics, not exposed publicly

    # Partner event backbone / realtime
    partner_portal_enabled: bool = False
    partner_applications_enabled: bool = False
    partner_codes_enabled: bool = False
    partner_attribution_enabled: bool = False
    partner_legacy_code_public_slug_enabled: bool = True
    partner_legacy_code_public_slug_sunset_date: str = "2026-09-30"  # noqa: S105 - date, not a secret.
    partner_deterministic_public_token_fallback_enabled: bool = True
    partner_deterministic_public_token_sunset_date: str = "2026-09-30"  # noqa: S105 - date, not a secret.
    partner_legacy_partner_earning_enabled: bool = True
    partner_legacy_partner_earning_sunset_date: str = "2026-09-30"  # noqa: S105 - date, not a secret.
    partner_storefronts_enabled: bool = False
    partner_reporting_enabled: bool = False
    partner_settlement_sandbox_enabled: bool = False
    partner_webhooks_enabled: bool = False
    partner_payouts_enabled: bool = False
    partner_event_backbone_enabled: bool = False
    messaging_event_backbone_enabled: bool = False
    nats_url: str = "nats://localhost:4222"
    nats_partner_stream_name: str = "PARTNER_EVENTS"
    nats_partner_subject_prefix: str = "partner"
    nats_messaging_stream_name: str = "MESSAGING_EVENTS"
    nats_messaging_subject_prefix: str = "messaging"
    outbox_dispatch_batch_size: int = 100
    outbox_dispatch_interval_seconds: float = 1.0
    outbox_dispatch_lease_seconds: int = 30
    outbox_dispatch_retry_after_seconds: int = 5
    outbox_dispatch_dead_letter_after_attempts: int = 5
    nats_consumer_fetch_batch_size: int = 25
    nats_consumer_fetch_timeout_seconds: float = 1.0
    partner_realtime_backlog_limit: int = 100
    messaging_presence_ttl_seconds: int = 45
    messaging_realtime_heartbeat_seconds: float = 15.0
    messaging_realtime_queue_size: int = 100

    # PostHog product intelligence
    posthog_enabled: bool = False
    posthog_host: str = ""
    posthog_project_api_key: SecretStr = SecretStr("")
    posthog_timeout_seconds: float = 5.0

    # Sentry (Observability)
    sentry_dsn: str = ""  # Sentry DSN for error tracking (optional, empty = disabled)
    sentry_release: str = ""  # Canonical Sentry release name (optional, empty = auto/disabled)
    runtime_origin_marker: str = "stage1-prod-a"
    runtime_container_image: str = ""
    runtime_git_sha: str = ""

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
        "passkey_allowed_origins",
        "passkey_dev_allowed_origins",
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
                raise ValueError("ADMIN_ALLOWED_HOSTS must not include public or redirect-only hosts in S1 production.")
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

        if environment in S1_LOCAL_STAGE_ENVIRONMENTS:
            if "*" in normalized_origins:
                raise ValueError("CORS_ORIGINS='*' is not allowed in local-stage.")
            missing_origins = S1_LOCAL_STAGE_BROWSER_ORIGINS - set(normalized_origins)
            if missing_origins:
                raise ValueError(
                    "Local-stage CORS_ORIGINS must include approved browser origins: "
                    + ", ".join(sorted(missing_origins))
                )
            invalid_origins = set(normalized_origins) - S1_LOCAL_STAGE_BROWSER_ORIGINS
            if invalid_origins:
                raise ValueError(
                    "Local-stage CORS origin is not approved for S1 synthetic QA: " + ", ".join(sorted(invalid_origins))
                )

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

    @field_validator("max_request_body_bytes", mode="after")
    @classmethod
    def validate_max_request_body_bytes(cls, v: int) -> int:
        if v < 1024:
            raise ValueError("MAX_REQUEST_BODY_BYTES must be at least 1024 bytes.")
        if v > 10 * 1024 * 1024:
            raise ValueError("MAX_REQUEST_BODY_BYTES must be at most 10485760 bytes.")
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
            raise ValueError("OAUTH_WEB_BASE_URL is required in production when OAuth login providers are enabled.")
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

    @model_validator(mode="after")
    def validate_payment_settlement_worker_secret(self) -> Self:
        if not self.payment_settlement_worker_enabled:
            return self
        if self.environment.lower() != "production":
            return self

        worker_secret = self.payment_settlement_worker_secret.get_secret_value().strip()
        if len(worker_secret) < 16:
            raise ValueError("PAYMENT_SETTLEMENT_WORKER_SECRET is required in production.")

        worker_secret_lower = worker_secret.lower()
        for marker in self.PROVIDER_SECRET_PLACEHOLDER_PATTERNS:
            if marker in worker_secret_lower:
                raise ValueError("PAYMENT_SETTLEMENT_WORKER_SECRET must not be a placeholder/test value in production.")

        telegram_secret = self.telegram_bot_internal_secret.get_secret_value().strip()
        if telegram_secret and hmac.compare_digest(worker_secret, telegram_secret):
            raise ValueError("PAYMENT_SETTLEMENT_WORKER_SECRET must differ from TELEGRAM_BOT_INTERNAL_SECRET.")

        backend_secret = self.backend_internal_secret.get_secret_value().strip()
        if backend_secret and hmac.compare_digest(worker_secret, backend_secret):
            raise ValueError("PAYMENT_SETTLEMENT_WORKER_SECRET must differ from BACKEND_INTERNAL_SECRET.")

        return self

    @model_validator(mode="after")
    def validate_telegram_bot_internal_secret(self) -> Self:
        if self.environment.lower() != "production":
            return self

        telegram_secret = self.telegram_bot_internal_secret.get_secret_value().strip()
        if not telegram_secret:
            return self
        if len(telegram_secret) < 16:
            raise ValueError("TELEGRAM_BOT_INTERNAL_SECRET must be a real internal credential in production.")

        telegram_secret_lower = telegram_secret.lower()
        for marker in self.PROVIDER_SECRET_PLACEHOLDER_PATTERNS:
            if marker in telegram_secret_lower:
                raise ValueError("TELEGRAM_BOT_INTERNAL_SECRET must not be a placeholder/test value in production.")

        return self

    @model_validator(mode="after")
    def validate_backend_internal_secret(self) -> Self:
        if self.environment.lower() != "production":
            return self

        backend_secret = self.backend_internal_secret.get_secret_value().strip()
        if not backend_secret:
            return self
        if len(backend_secret) < 16:
            raise ValueError("BACKEND_INTERNAL_SECRET must be a real internal credential in production.")

        backend_secret_lower = backend_secret.lower()
        for marker in self.PROVIDER_SECRET_PLACEHOLDER_PATTERNS:
            if marker in backend_secret_lower:
                raise ValueError("BACKEND_INTERNAL_SECRET must not be a placeholder/test value in production.")

        telegram_secret = self.telegram_bot_internal_secret.get_secret_value().strip()
        if telegram_secret and hmac.compare_digest(backend_secret, telegram_secret):
            raise ValueError("BACKEND_INTERNAL_SECRET must differ from TELEGRAM_BOT_INTERNAL_SECRET.")

        worker_secret = self.payment_settlement_worker_secret.get_secret_value().strip()
        if worker_secret and hmac.compare_digest(backend_secret, worker_secret):
            raise ValueError("BACKEND_INTERNAL_SECRET must differ from PAYMENT_SETTLEMENT_WORKER_SECRET.")

        return self

    @model_validator(mode="after")
    def validate_vpn_test_agent_secrets(self) -> Self:
        if self.environment.lower() != "production" or not self.vpn_tester_runtime_enabled:
            return self

        targets = (
            ("VPN_TEST_AGENT", self.vpn_test_agent_url, self.vpn_test_agent_secret),
            ("VPN_TEST_AGENT_MOSCOW", self.vpn_test_agent_moscow_url, self.vpn_test_agent_moscow_secret),
            ("VPN_TEST_AGENT_SPB", self.vpn_test_agent_spb_url, self.vpn_test_agent_spb_secret),
        )
        for label, url, secret_value in targets:
            secret = secret_value.get_secret_value().strip() if secret_value is not None else ""
            if bool(url.strip()) != bool(secret):
                raise ValueError(f"{label}_URL and {label}_SECRET must be configured together in production.")
            if not url.strip():
                continue
            parsed_url = urlparse(url.strip())
            local_plaintext = (
                label == "VPN_TEST_AGENT"
                and parsed_url.scheme == "http"
                and parsed_url.hostname in VPN_TEST_AGENT_LOCAL_HTTP_HOSTS
            )
            if parsed_url.hostname is None or (parsed_url.scheme != "https" and not local_plaintext):
                raise ValueError(f"{label}_URL must use HTTPS outside the local compose network.")
            if (
                parsed_url.username is not None
                or parsed_url.password is not None
                or parsed_url.query
                or parsed_url.fragment
                or parsed_url.path not in {"", "/"}
            ):
                raise ValueError(f"{label}_URL must be an origin URL without credentials, path, query or fragment.")
            if len(secret) < 16:
                raise ValueError(f"{label}_SECRET must be a real internal credential in production.")
            secret_lower = secret.lower()
            if any(marker in secret_lower for marker in self.PROVIDER_SECRET_PLACEHOLDER_PATTERNS):
                raise ValueError(f"{label}_SECRET must not be a placeholder/test value in production.")
        if not self.vpn_test_agent_url.strip():
            raise ValueError("VPN_TEST_AGENT_URL is required when production runtime VPN testing is enabled.")
        return self

    @field_validator("vpn_test_agent_signature_max_skew_seconds", mode="after")
    @classmethod
    def validate_vpn_test_agent_signature_max_skew_seconds(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("VPN_TEST_AGENT_SIGNATURE_MAX_SKEW_SECONDS must be between 1 and 300 seconds.")
        return v

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

    @field_validator("web_device_cookie_name", mode="before")
    @classmethod
    def normalize_web_device_cookie_name(cls, v: str | None) -> str:
        return (v or "").strip()

    @field_validator("web_device_cookie_name", mode="after")
    @classmethod
    def validate_web_device_cookie_name(cls, v: str) -> str:
        if not v:
            raise ValueError("WEB_DEVICE_COOKIE_NAME must not be empty.")
        if not v.startswith("__Host-"):
            raise ValueError("WEB_DEVICE_COOKIE_NAME must use the __Host- prefix.")
        if any(char in v for char in ("=", ";", " ", "\t", "\n", "\r")):
            raise ValueError("WEB_DEVICE_COOKIE_NAME must be a bare cookie name.")
        return v

    @field_validator("device_cookie_pepper_secret_name", mode="before")
    @classmethod
    def normalize_device_cookie_pepper_secret_name(cls, v: str | None) -> str:
        return (v or "").strip()

    @field_validator("device_cookie_pepper_secret_name", mode="after")
    @classmethod
    def validate_device_cookie_pepper_secret_name(cls, v: str) -> str:
        if not v:
            raise ValueError("DEVICE_COOKIE_PEPPER_SECRET_NAME must name an environment secret.")
        if len(v) > 128:
            raise ValueError("DEVICE_COOKIE_PEPPER_SECRET_NAME must be at most 128 characters.")
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        if any(char not in allowed for char in v) or v[0].isdigit():
            raise ValueError("DEVICE_COOKIE_PEPPER_SECRET_NAME must be an uppercase env-var style name.")
        return v

    @field_validator("csrf_protection_enabled", mode="after")
    @classmethod
    def validate_csrf_protection_enabled(cls, v: bool, info) -> bool:
        environment = str(info.data.get("environment", "development")).lower()
        if environment == "production" and not v:
            raise ValueError("CSRF_PROTECTION_ENABLED=false is not allowed in production.")
        return v

    @field_validator("passkey_rp_id", "passkey_dev_rp_id", mode="before")
    @classmethod
    def normalize_passkey_rp_id(cls, v: str | None) -> str:
        return (v or "").strip().lower().lstrip(".")

    @field_validator("passkey_rp_id", "passkey_dev_rp_id", mode="after")
    @classmethod
    def validate_passkey_rp_id(cls, v: str, info) -> str:
        field_name = info.field_name
        if not v:
            raise ValueError(f"{field_name.upper()} must not be empty.")
        if "://" in v or "/" in v or ":" in v or "?" in v or "#" in v or "*" in v:
            raise ValueError(f"{field_name.upper()} must be a bare domain without protocol, path, port, or wildcard.")
        return v

    @field_validator("passkey_allowed_origins", "passkey_dev_allowed_origins", mode="after")
    @classmethod
    def validate_passkey_origins(cls, v: list[str], info) -> list[str]:
        environment = str(info.data.get("environment", "development")).lower()
        field_name = info.field_name
        normalized_origins: list[str] = []

        for origin in v:
            normalized = origin.strip().rstrip("/")
            if not normalized:
                continue
            if "*" in normalized:
                raise ValueError(f"{field_name.upper()} must not include wildcard origins.")

            parsed = urlparse(normalized)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"{field_name.upper()} entries must be absolute http(s) origins.")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError(f"{field_name.upper()} entries must not include path, query, or fragment.")

            origin_value = f"{parsed.scheme}://{parsed.netloc}"
            if field_name == "passkey_allowed_origins":
                if environment == "production" and parsed.scheme != "https":
                    raise ValueError("Production PASSKEY_ALLOWED_ORIGINS must use https origins.")
                if environment == "production" and origin_value not in S1_PRODUCTION_PASSKEY_ORIGINS:
                    raise ValueError(f"Production passkey origin is not approved for S1: {origin_value}")
            normalized_origins.append(origin_value)

        return normalized_origins

    @field_validator("passkey_challenge_ttl_seconds", mode="after")
    @classmethod
    def validate_passkey_challenge_ttl_seconds(cls, v: int) -> int:
        if v < 30 or v > 300:
            raise ValueError("PASSKEY_CHALLENGE_TTL_SECONDS must be between 30 and 300 seconds.")
        return v

    @field_validator("passkey_browser_timeout_ms", mode="after")
    @classmethod
    def validate_passkey_browser_timeout_ms(cls, v: int) -> int:
        if v < 15000 or v > 120000:
            raise ValueError("PASSKEY_BROWSER_TIMEOUT_MS must be between 15000 and 120000 milliseconds.")
        return v

    @field_validator("passkey_fresh_auth_ttl_seconds", mode="after")
    @classmethod
    def validate_passkey_fresh_auth_ttl_seconds(cls, v: int) -> int:
        if v < 60 or v > 900:
            raise ValueError("PASSKEY_FRESH_AUTH_TTL_SECONDS must be between 60 and 900 seconds.")
        return v

    @model_validator(mode="after")
    def validate_passkey_runtime_policy(self) -> Self:
        environment = self.environment.lower()
        if not self.passkey_enabled:
            return self

        if not self.passkey_allowed_origins:
            raise ValueError("PASSKEY_ALLOWED_ORIGINS is required when PASSKEY_ENABLED=true.")
        if environment == "production":
            if self.passkey_dev_enabled:
                raise ValueError("PASSKEY_DEV_ENABLED=true is not allowed in production.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE=true is required when passkeys are enabled in production.")
            if self.passkey_rp_id != "cyber-vpn.net":
                raise ValueError("Production PASSKEY_RP_ID must be cyber-vpn.net for S1.")
        return self

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


settings = Settings()  # type: ignore[call-arg]
