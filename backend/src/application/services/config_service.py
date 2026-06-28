"""Application service for reading/writing system configuration."""

import os
from dataclasses import dataclass
from typing import Any, Literal, cast
from uuid import UUID

from src.config.settings import settings
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository

MiniAppRuntimeMode = Literal["live", "canary", "maintenance", "rollback"]
CustomerSiteMode = Literal["full_site", "cabinet_only", "maintenance"]
CustomerSiteCabinetMarketingRouteAction = Literal["redirect_public", "allow", "not_found"]
OnboardingCodeType = Literal["promo", "invite", "gift"]
PASSKEY_ADMIN_POLICY_CONFIG_KEY = "passkeys.admin_policy"
CUSTOMER_SITE_RUNTIME_CONFIG_KEY = "customer_site.runtime"
CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY = "customer_onboarding.runtime"


def _normalize_customer_site_mode(value: object, *, fallback: CustomerSiteMode = "full_site") -> CustomerSiteMode:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"full_site", "cabinet_only", "maintenance"}:
            return normalized  # type: ignore[return-value]
    return fallback


def _normalize_string_tuple(value: object, *, default: tuple[str, ...] = (), max_items: int = 50) -> tuple[str, ...]:
    if not isinstance(value, list | tuple | set):
        return default

    normalized: list[str] = []
    for item in value:
        candidate = str(item).strip()
        if not candidate or candidate in normalized:
            continue
        normalized.append(candidate)
        if len(normalized) >= max_items:
            break
    return tuple(normalized)


def _normalize_path(value: object, *, default: str) -> str:
    candidate = str(value or "").strip()
    if not _is_safe_path(candidate):
        return default
    return candidate


def _normalize_path_tuple(value: object, *, default: tuple[str, ...] = (), max_items: int = 100) -> tuple[str, ...]:
    if not isinstance(value, list | tuple | set):
        return default

    normalized: list[str] = []
    for item in value:
        candidate = str(item).strip()
        if not _is_safe_path(candidate) or candidate in normalized:
            continue
        normalized.append(candidate)
        if len(normalized) >= max_items:
            break
    return tuple(normalized)


def _is_safe_path(value: str) -> bool:
    return bool(value) and value.startswith("/") and not value.startswith("//")


def _normalize_positive_int(value: object, *, default: int = 1, maximum: int = 1000) -> int:
    try:
        candidate = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if candidate < 1 or candidate > maximum:
        return default
    return candidate


def _normalize_miniapp_runtime_mode(value: object) -> MiniAppRuntimeMode:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"live", "canary", "maintenance", "rollback"}:
            return normalized  # type: ignore[return-value]
    return "live"


def _normalize_customer_site_cabinet_marketing_action(
    value: object,
) -> CustomerSiteCabinetMarketingRouteAction:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"redirect_public", "allow", "not_found"}:
            return normalized  # type: ignore[return-value]
    return "redirect_public"


def _normalize_telegram_user_id_list(value: object) -> tuple[int, ...]:
    if not isinstance(value, list | tuple | set):
        return ()

    normalized: set[int] = set()
    for item in value:
        try:
            candidate = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if candidate > 0:
            normalized.add(candidate)
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class MiniAppRuntimeConfig:
    enabled: bool = True
    mode: MiniAppRuntimeMode = "live"
    trial_enabled: bool = True
    checkout_enabled: bool = True
    config_enabled: bool = True
    maintenance_message: str | None = None
    canary_telegram_user_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class MiniAppLaunchReadinessConfig:
    observability_acknowledged: bool = False
    incident_runbook_acknowledged: bool = False
    checkout_canary_passed: bool = False
    config_delivery_canary_passed: bool = False
    rollback_drill_acknowledged: bool = False
    support_window_confirmed: bool = False
    customer_comms_ready: bool = False
    status_page_template_ready: bool = False
    incident_channel: str | None = None
    rollback_commander: str | None = None
    primary_oncall_contact: str | None = None
    release_window_note: str | None = None

    @property
    def is_ready(self) -> bool:
        return all(
            (
                self.observability_acknowledged,
                self.incident_runbook_acknowledged,
                self.checkout_canary_passed,
                self.config_delivery_canary_passed,
                self.rollback_drill_acknowledged,
                self.support_window_confirmed,
                self.customer_comms_ready,
                self.status_page_template_ready,
                bool(self.incident_channel),
                bool(self.rollback_commander),
                bool(self.primary_oncall_contact),
            )
        )


@dataclass(frozen=True)
class CustomerSiteRuntimeConfig:
    mode: CustomerSiteMode = "full_site"
    version: int = 1
    public_hosts: tuple[str, ...] = ("cyber-vpn.net", "www.cyber-vpn.net")
    cabinet_hosts: tuple[str, ...] = ("my.cyber-vpn.net",)
    cabinet_destination_path: str = "/dashboard"
    allowed_path_prefixes: tuple[str, ...] = (
        "/login",
        "/register",
        "/verify",
        "/verify-email",
        "/forgot-password",
        "/reset-password",
        "/magic-link",
        "/oauth",
        "/legal",
        "/r/",
        "/p/",
    )
    cabinet_allowed_prefixes: tuple[str, ...] = (
        "/dashboard",
        "/subscriptions",
        "/payment-history",
        "/referral",
        "/rewards",
        "/wallet",
        "/settings",
        "/support",
        "/messages",
        "/servers",
        "/monitoring",
        "/analytics",
        "/users",
        "/partner",
        "/login",
        "/register",
        "/verify",
        "/verify-email",
        "/forgot-password",
        "/reset-password",
        "/magic-link",
        "/oauth",
        "/telegram-link",
        "/onboarding",
    )
    cabinet_marketing_route_action: CustomerSiteCabinetMarketingRouteAction = "redirect_public"
    public_marketing_destination_path: str = "/"
    legal_path_prefixes: tuple[str, ...] = (
        "/acceptable-use",
        "/cookie-policy",
        "/privacy",
        "/privacy-policy",
        "/refund-policy",
        "/terms",
    )
    operational_path_prefixes: tuple[str, ...] = (
        "/status",
        "/telegram-widget",
        "/.well-known",
    )
    preserve_query_keys: tuple[str, ...] = (
        "ref",
        "referral",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    )

    @property
    def cabinet_only(self) -> bool:
        return self.mode == "cabinet_only"


@dataclass(frozen=True)
class CustomerOnboardingRuntimeConfig:
    post_registration_code_prompt_enabled: bool = False
    web_otp_enabled: bool = False
    telegram_miniapp_enabled: bool = False
    state_store_ready: bool = False
    flow_key: str = "post_registration_growth_code_v1"
    version: int = 1
    allowed_code_types: tuple[OnboardingCodeType, ...] = ("promo", "invite", "gift")
    allow_referral_input: bool = False
    allow_partner_input: bool = False

    @property
    def available(self) -> bool:
        return (
            self.post_registration_code_prompt_enabled
            and self.state_store_ready
            and (self.web_otp_enabled or self.telegram_miniapp_enabled)
        )


@dataclass(frozen=True)
class PasskeyAdminPolicyConfig:
    enabled: bool = True
    registration_enabled: bool = True
    authentication_enabled: bool = True
    reauthentication_enabled: bool = True
    conditional_ui_enabled: bool = True
    security_dashboard_enabled: bool = True
    admin_counts_as_mfa: bool = False
    challenge_ttl_seconds: int = 300
    browser_timeout_ms: int = 60000
    fresh_auth_ttl_seconds: int = 300


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return default
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return default
    if candidate < minimum or candidate > maximum:
        return default
    return candidate


class ConfigService:
    """Typed access to system_config key-value store."""

    def __init__(self, config_repo: SystemConfigRepository) -> None:
        self._repo = config_repo

    # --- Generic ---

    async def get(self, key: str, default: Any = None) -> Any:
        return await self._repo.get_value(key, default)

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        updated_by: UUID | None = None,
        description: str | None = None,
    ) -> None:
        await self._repo.set(key, value, updated_by=updated_by, description=description)

    # --- Invite config ---

    async def get_invite_plan_rules(self) -> list[dict[str, Any]]:
        val = await self._repo.get_value("invite.plan_rules", {"rules": []})
        return val.get("rules", [])

    async def get_invite_default_expiry_days(self) -> int:
        val = await self._repo.get_value("invite.default_expiry_days", {"days": 30})
        return int(val.get("days", 30))

    # --- Referral config ---

    async def is_referral_enabled(self) -> bool:
        if not settings.referral_enabled:
            return False
        val = await self._repo.get_value("referral.enabled", {"enabled": False})
        return bool(val.get("enabled", False))

    async def get_referral_commission_rate(self) -> float:
        val = await self._repo.get_value("referral.commission_rate", {"rate": 0.10})
        return float(val.get("rate", 0.10))

    async def get_referral_duration_mode(self) -> dict[str, Any]:
        return await self._repo.get_value("referral.duration_mode", {"mode": "indefinite"})

    # --- Partner config ---

    async def get_partner_max_markup_pct(self) -> int:
        val = await self._repo.get_value("partner.max_markup_pct", {"max_pct": 300})
        return int(val.get("max_pct", 300))

    async def get_partner_base_commission_pct(self) -> int:
        val = await self._repo.get_value("partner.base_commission_pct", {"pct": 10})
        return int(val.get("pct", 10))

    async def get_partner_tiers(self) -> list[dict[str, Any]]:
        val = await self._repo.get_value(
            "partner.tiers",
            {"tiers": [{"min_clients": 0, "commission_pct": 20}]},
        )
        return val.get("tiers", [])

    async def get_partner_payout_hold_days(self, *, owner_type: str | None = None) -> int:
        if owner_type == "performance":
            val = await self._repo.get_value("performance.payout_hold_days", {"days": 45})
            return int(val.get("days", 45))
        val = await self._repo.get_value("affiliate.payout_hold_days", {"days": 30})
        return int(val.get("days", 30))

    # --- Passkey/WebAuthn config ---

    async def get_passkey_admin_policy_config(self) -> PasskeyAdminPolicyConfig:
        val = await self._repo.get_value(PASSKEY_ADMIN_POLICY_CONFIG_KEY, {})
        if not isinstance(val, dict):
            val = {}

        return PasskeyAdminPolicyConfig(
            enabled=bool(val.get("enabled", True)),
            registration_enabled=bool(val.get("registration_enabled", True)),
            authentication_enabled=bool(val.get("authentication_enabled", True)),
            reauthentication_enabled=bool(val.get("reauthentication_enabled", True)),
            conditional_ui_enabled=bool(val.get("conditional_ui_enabled", True)),
            security_dashboard_enabled=bool(val.get("security_dashboard_enabled", True)),
            admin_counts_as_mfa=bool(val.get("admin_counts_as_mfa", settings.passkey_admin_counts_as_mfa)),
            challenge_ttl_seconds=_bounded_int(
                val.get("challenge_ttl_seconds"),
                default=settings.passkey_challenge_ttl_seconds,
                minimum=30,
                maximum=300,
            ),
            browser_timeout_ms=_bounded_int(
                val.get("browser_timeout_ms"),
                default=settings.passkey_browser_timeout_ms,
                minimum=15000,
                maximum=120000,
            ),
            fresh_auth_ttl_seconds=_bounded_int(
                val.get("fresh_auth_ttl_seconds"),
                default=settings.passkey_fresh_auth_ttl_seconds,
                minimum=60,
                maximum=900,
            ),
        )

    # --- Wallet config ---

    async def get_wallet_min_withdrawal(self) -> dict[str, Any]:
        return await self._repo.get_value("wallet.min_withdrawal", {"amount": 5.0, "currency": "USD"})

    async def is_withdrawal_enabled(self) -> bool:
        val = await self._repo.get_value("wallet.withdrawal_enabled", {"enabled": False})
        return bool(val.get("enabled", False))

    async def get_withdrawal_fee_pct(self) -> float:
        val = await self._repo.get_value("wallet.withdrawal_fee_pct", {"pct": 0})
        return float(val.get("pct", 0))

    # --- Customer site and onboarding runtime config ---

    async def get_customer_site_runtime_config(self) -> CustomerSiteRuntimeConfig:
        fallback_mode = _normalize_customer_site_mode(os.getenv("CUSTOMER_SITE_MODE_FALLBACK"))
        val = await self._repo.get_value(
            CUSTOMER_SITE_RUNTIME_CONFIG_KEY,
            {
                "mode": fallback_mode,
                "version": 1,
                "public_hosts": ["cyber-vpn.net", "www.cyber-vpn.net"],
                "cabinet_hosts": ["my.cyber-vpn.net"],
                "cabinet_destination_path": "/dashboard",
                "allowed_path_prefixes": [
                    "/login",
                    "/register",
                    "/verify",
                    "/verify-email",
                    "/forgot-password",
                    "/reset-password",
                    "/magic-link",
                    "/oauth",
                    "/legal",
                    "/r/",
                    "/p/",
                ],
                "cabinet_allowed_prefixes": list(CustomerSiteRuntimeConfig.cabinet_allowed_prefixes),
                "cabinet_marketing_route_action": "redirect_public",
                "public_marketing_destination_path": "/",
                "legal_path_prefixes": list(CustomerSiteRuntimeConfig.legal_path_prefixes),
                "operational_path_prefixes": list(CustomerSiteRuntimeConfig.operational_path_prefixes),
                "preserve_query_keys": [
                    "ref",
                    "referral",
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_content",
                    "utm_term",
                ],
            },
        )
        if not isinstance(val, dict):
            val = {}
        return CustomerSiteRuntimeConfig(
            mode=_normalize_customer_site_mode(val.get("mode", val.get("customer_site_mode")), fallback=fallback_mode),
            version=_normalize_positive_int(val.get("version")),
            public_hosts=_normalize_string_tuple(
                val.get("public_hosts"),
                default=("cyber-vpn.net", "www.cyber-vpn.net"),
            ),
            cabinet_hosts=_normalize_string_tuple(val.get("cabinet_hosts"), default=("my.cyber-vpn.net",)),
            cabinet_destination_path=_normalize_path(
                val.get("cabinet_destination_path"),
                default=CustomerSiteRuntimeConfig.cabinet_destination_path,
            ),
            allowed_path_prefixes=_normalize_path_tuple(
                val.get("allowed_path_prefixes"),
                default=CustomerSiteRuntimeConfig.allowed_path_prefixes,
                max_items=100,
            ),
            cabinet_allowed_prefixes=_normalize_path_tuple(
                val.get("cabinet_allowed_prefixes"),
                default=CustomerSiteRuntimeConfig.cabinet_allowed_prefixes,
                max_items=100,
            ),
            cabinet_marketing_route_action=_normalize_customer_site_cabinet_marketing_action(
                val.get("cabinet_marketing_route_action")
            ),
            public_marketing_destination_path=_normalize_path(
                val.get("public_marketing_destination_path"),
                default=CustomerSiteRuntimeConfig.public_marketing_destination_path,
            ),
            legal_path_prefixes=_normalize_path_tuple(
                val.get("legal_path_prefixes"),
                default=CustomerSiteRuntimeConfig.legal_path_prefixes,
                max_items=100,
            ),
            operational_path_prefixes=_normalize_path_tuple(
                val.get("operational_path_prefixes"),
                default=CustomerSiteRuntimeConfig.operational_path_prefixes,
                max_items=100,
            ),
            preserve_query_keys=_normalize_string_tuple(
                val.get("preserve_query_keys"),
                default=CustomerSiteRuntimeConfig.preserve_query_keys,
            ),
        )

    async def get_customer_onboarding_runtime_config(self) -> CustomerOnboardingRuntimeConfig:
        val = await self._repo.get_value(
            CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
            {
                "post_registration_code_prompt_enabled": False,
                "web_otp_enabled": False,
                "telegram_miniapp_enabled": False,
                "state_store_ready": False,
                "flow_key": "post_registration_growth_code_v1",
                "version": 1,
                "allowed_code_types": ["promo", "invite", "gift"],
                "allow_referral_input": False,
                "allow_partner_input": False,
            },
        )
        if not isinstance(val, dict):
            val = {}
        flow_key = str(val.get("flow_key") or "post_registration_growth_code_v1").strip()
        allowed_code_types = _normalize_string_tuple(
            val.get("allowed_code_types"),
            default=("promo", "invite", "gift"),
            max_items=8,
        )
        filtered_code_types = tuple(
            cast(OnboardingCodeType, code_type)
            for code_type in allowed_code_types
            if code_type in {"promo", "invite", "gift"}
        )
        return CustomerOnboardingRuntimeConfig(
            post_registration_code_prompt_enabled=bool(val.get("post_registration_code_prompt_enabled", False)),
            web_otp_enabled=bool(val.get("web_otp_enabled", False)),
            telegram_miniapp_enabled=bool(val.get("telegram_miniapp_enabled", False)),
            state_store_ready=bool(val.get("state_store_ready", False)),
            flow_key=flow_key or "post_registration_growth_code_v1",
            version=_normalize_positive_int(val.get("version")),
            allowed_code_types=filtered_code_types or ("promo", "invite", "gift"),
            allow_referral_input=bool(val.get("allow_referral_input", False)),
            allow_partner_input=bool(val.get("allow_partner_input", False)),
        )

    # --- Mini App runtime config ---

    async def get_miniapp_runtime_config(self) -> MiniAppRuntimeConfig:
        val = await self._repo.get_value(
            "miniapp.runtime",
            {
                "enabled": True,
                "mode": "live",
                "trial_enabled": True,
                "checkout_enabled": True,
                "config_enabled": True,
                "maintenance_message": None,
                "canary_telegram_user_ids": [],
            },
        )
        return MiniAppRuntimeConfig(
            enabled=bool(val.get("enabled", True)),
            mode=_normalize_miniapp_runtime_mode(val.get("mode")),
            trial_enabled=bool(val.get("trial_enabled", True)),
            checkout_enabled=bool(val.get("checkout_enabled", True)),
            config_enabled=bool(val.get("config_enabled", True)),
            maintenance_message=(str(val["maintenance_message"]).strip() if val.get("maintenance_message") else None),
            canary_telegram_user_ids=_normalize_telegram_user_id_list(val.get("canary_telegram_user_ids", [])),
        )

    async def get_miniapp_launch_readiness_config(self) -> MiniAppLaunchReadinessConfig:
        val = await self._repo.get_value(
            "miniapp.launch_readiness",
            {
                "observability_acknowledged": False,
                "incident_runbook_acknowledged": False,
                "checkout_canary_passed": False,
                "config_delivery_canary_passed": False,
                "rollback_drill_acknowledged": False,
                "support_window_confirmed": False,
                "customer_comms_ready": False,
                "status_page_template_ready": False,
                "incident_channel": None,
                "rollback_commander": None,
                "primary_oncall_contact": None,
                "release_window_note": None,
            },
        )
        return MiniAppLaunchReadinessConfig(
            observability_acknowledged=bool(val.get("observability_acknowledged", False)),
            incident_runbook_acknowledged=bool(val.get("incident_runbook_acknowledged", False)),
            checkout_canary_passed=bool(val.get("checkout_canary_passed", False)),
            config_delivery_canary_passed=bool(val.get("config_delivery_canary_passed", False)),
            rollback_drill_acknowledged=bool(val.get("rollback_drill_acknowledged", False)),
            support_window_confirmed=bool(val.get("support_window_confirmed", False)),
            customer_comms_ready=bool(val.get("customer_comms_ready", False)),
            status_page_template_ready=bool(val.get("status_page_template_ready", False)),
            incident_channel=(str(val["incident_channel"]).strip() if val.get("incident_channel") else None),
            rollback_commander=(str(val["rollback_commander"]).strip() if val.get("rollback_commander") else None),
            primary_oncall_contact=(
                str(val["primary_oncall_contact"]).strip() if val.get("primary_oncall_contact") else None
            ),
            release_window_note=(str(val["release_window_note"]).strip() if val.get("release_window_note") else None),
        )
