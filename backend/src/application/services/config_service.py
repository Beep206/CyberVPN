"""Application service for reading/writing system configuration."""

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository

MiniAppRuntimeMode = Literal["live", "canary", "maintenance", "rollback"]


def _normalize_miniapp_runtime_mode(value: object) -> MiniAppRuntimeMode:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"live", "canary", "maintenance", "rollback"}:
            return normalized  # type: ignore[return-value]
    return "live"


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
        val = await self._repo.get_value("referral.enabled", {"enabled": True})
        return bool(val.get("enabled", True))

    async def get_referral_commission_rate(self) -> float:
        val = await self._repo.get_value("referral.commission_rate", {"rate": 0.10})
        return float(val.get("rate", 0.10))

    async def get_referral_duration_mode(self) -> dict[str, Any]:
        return await self._repo.get_value(
            "referral.duration_mode", {"mode": "indefinite"}
        )

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

    # --- Wallet config ---

    async def get_wallet_min_withdrawal(self) -> dict[str, Any]:
        return await self._repo.get_value(
            "wallet.min_withdrawal", {"amount": 5.0, "currency": "USD"}
        )

    async def is_withdrawal_enabled(self) -> bool:
        val = await self._repo.get_value("wallet.withdrawal_enabled", {"enabled": True})
        return bool(val.get("enabled", True))

    async def get_withdrawal_fee_pct(self) -> float:
        val = await self._repo.get_value("wallet.withdrawal_fee_pct", {"pct": 0})
        return float(val.get("pct", 0))

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
            maintenance_message=(
                str(val["maintenance_message"]).strip()
                if val.get("maintenance_message")
                else None
            ),
            canary_telegram_user_ids=_normalize_telegram_user_id_list(
                val.get("canary_telegram_user_ids", [])
            ),
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
            incident_channel=(
                str(val["incident_channel"]).strip()
                if val.get("incident_channel")
                else None
            ),
            rollback_commander=(
                str(val["rollback_commander"]).strip()
                if val.get("rollback_commander")
                else None
            ),
            primary_oncall_contact=(
                str(val["primary_oncall_contact"]).strip()
                if val.get("primary_oncall_contact")
                else None
            ),
            release_window_note=(
                str(val["release_window_note"]).strip()
                if val.get("release_window_note")
                else None
            ),
        )
