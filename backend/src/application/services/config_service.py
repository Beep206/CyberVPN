"""Application service for reading/writing system configuration."""

from typing import Any
from uuid import UUID

from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository


class ConfigService:
    """Typed access to system_config key-value store."""

    def __init__(self, config_repo: SystemConfigRepository) -> None:
        self._repo = config_repo

    # --- Generic ---

    async def get(self, key: str, default: Any = None) -> Any:
        return await self._repo.get_value(key, default)

    async def set(self, key: str, value: dict[str, Any], updated_by: UUID | None = None) -> None:
        await self._repo.set(key, value, updated_by=updated_by)

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
