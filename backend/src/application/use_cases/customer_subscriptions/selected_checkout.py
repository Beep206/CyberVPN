from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.services.stage1_growth_policy import assert_stage1_checkout_codes_enabled
from src.application.services.stage1_plan_policy import assert_stage1_addons_enabled
from src.application.services.wallet_service import WalletService
from src.application.use_cases.payments.checkout import (
    CheckoutAddonInput,
    CheckoutResult,
    CheckoutUseCase,
)
from src.config.settings import settings
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository


class SelectedSubscriptionCheckoutUseCase:
    """Quote selected-subscription upgrade and add-on purchases."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._plans = SubscriptionPlanRepository(session)
        self._addons = PlanAddonRepository(session)
        self._promo_repo = PromoCodeRepository(session)
        self._checkout = CheckoutUseCase(session)
        self._wallet = WalletService(WalletRepository(session))

    async def quote_upgrade(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
        target_plan_id: UUID,
        promo_code: str | None,
        use_wallet: Decimal,
        sale_channel: str,
    ) -> CheckoutResult:
        grant = await self._get_active_grant(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            subscription_key=subscription_key,
        )
        current_snapshot = self._normalize_snapshot(grant)
        if current_snapshot.get("plan_uuid") == str(target_plan_id):
            raise ValueError("Target plan matches the selected subscription")

        quote = await self._checkout.execute(
            user_id=customer_account_id,
            plan_id=target_plan_id,
            promo_code=promo_code,
            use_wallet=use_wallet,
            sale_channel=sale_channel,
        )
        target_plan = await self._plans.get_by_id(target_plan_id)
        if target_plan is not None:
            quote.entitlements_snapshot = EntitlementsService.build_snapshot(
                plan=target_plan,
                addon_lines=await self._addon_lines_from_snapshot(current_snapshot),
            )
        return quote

    async def quote_addons(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
        addons: list[CheckoutAddonInput],
        promo_code: str | None,
        use_wallet: Decimal,
        sale_channel: str,
    ) -> CheckoutResult:
        assert_stage1_addons_enabled(
            addon_count=max(1, len(addons)),
            enabled=settings.stage1_addons_enabled,
        )
        assert_stage1_checkout_codes_enabled(
            code_input=None,
            promo_code=promo_code,
            enabled=settings.checkout_code_discounts_enabled,
        )

        grant = await self._get_active_grant(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            subscription_key=subscription_key,
        )
        snapshot = self._normalize_snapshot(grant)
        plan_uuid = snapshot.get("plan_uuid")
        if not plan_uuid:
            raise ValueError("Selected subscription has no plan to attach add-ons to")
        plan = await self._plans.get_by_id(UUID(str(plan_uuid)))
        if plan is None:
            raise ValueError("Selected subscription plan not found")

        active_addon_lines = await self._addon_lines_from_snapshot(snapshot)
        existing_quantities = {
            str(line["code"]): int(line.get("qty", 1))
            for line in active_addon_lines
            if line.get("code")
        }
        addon_lines = await self._checkout._resolve_addons(
            plan=plan,
            addon_inputs=addons,
            sale_channel=sale_channel,
            existing_quantities_by_code=existing_quantities,
        )

        addon_amount = sum((line.total_price for line in addon_lines), Decimal("0"))
        discount_amount = Decimal("0")
        promo_code_id = None
        if promo_code:
            promo = await self._promo_repo.get_active_by_code(promo_code)
            if promo:
                promo_code_id = promo.id
                if promo.discount_type == "percent":
                    discount_amount = addon_amount * (Decimal(str(promo.discount_value)) / Decimal("100"))
                else:
                    discount_amount = min(Decimal(str(promo.discount_value)), addon_amount)

        after_promo = addon_amount - discount_amount
        wallet_amount = Decimal("0")
        if use_wallet > 0:
            wallet = await self._wallet.get_balance(customer_account_id)
            available = Decimal(str(wallet.balance)) - Decimal(str(wallet.frozen))
            wallet_amount = min(use_wallet, available, after_promo)

        gateway_amount = after_promo - wallet_amount
        if gateway_amount < 0:
            gateway_amount = Decimal("0")

        entitlements_snapshot = EntitlementsService.build_snapshot(
            plan=plan,
            addon_lines=active_addon_lines
            + [
                {
                    "code": line.code,
                    "qty": line.qty,
                    "location_code": line.location_code,
                    "delta_entitlements": line.delta_entitlements,
                }
                for line in addon_lines
            ],
            expires_at=EntitlementsService._to_utc_datetime(grant.expires_at),
        )

        return CheckoutResult(
            base_price=Decimal("0"),
            addon_amount=addon_amount,
            displayed_price=addon_amount,
            discount_amount=discount_amount,
            wallet_amount=wallet_amount,
            gateway_amount=gateway_amount,
            partner_markup=Decimal("0"),
            is_zero_gateway=gateway_amount <= 0,
            plan_id=plan.id,
            promo_code_id=promo_code_id,
            partner_code_id=None,
            plan_name=plan.name,
            duration_days=self._remaining_days(grant.expires_at),
            addons=addon_lines,
            entitlements_snapshot=entitlements_snapshot,
            commission_base_amount=Decimal("0"),
        )

    async def _get_active_grant(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
    ) -> EntitlementGrantModel:
        prefix, _, raw_id = subscription_key.partition(":")
        if prefix != "grant" or not raw_id:
            raise ValueError("Selected subscription writes are only supported for entitlement grants")
        grant = await self._repo.get_entitlement_grant_by_id(UUID(raw_id))
        if grant is None:
            raise ValueError("Selected subscription not found")
        if grant.customer_account_id != customer_account_id or grant.auth_realm_id != auth_realm_id:
            raise ValueError("Selected subscription not found")
        if grant.grant_status != "active":
            raise ValueError("Selected subscription is not active")
        expires_at = EntitlementsService._to_utc_datetime(grant.expires_at)
        if expires_at is not None and expires_at <= datetime.now(UTC):
            raise ValueError("Selected subscription is expired")
        return grant

    def _normalize_snapshot(self, grant: EntitlementGrantModel) -> dict:
        return EntitlementsService(self._session).normalize_grant_snapshot(
            grant_snapshot=dict(grant.grant_snapshot or {}),
            expires_at=grant.expires_at,
        )

    async def _addon_lines_from_snapshot(self, snapshot: dict) -> list[dict]:
        raw_addons = [dict(item) for item in snapshot.get("addons") or [] if item.get("code")]
        if not raw_addons:
            return []
        catalog = {
            addon.code: addon
            for addon in await self._addons.get_by_codes([str(item["code"]) for item in raw_addons])
        }
        lines: list[dict] = []
        for item in raw_addons:
            code = str(item["code"])
            addon = catalog.get(code)
            lines.append(
                {
                    "code": code,
                    "qty": int(item.get("qty", 1)),
                    "location_code": item.get("location_code"),
                    "delta_entitlements": dict(addon.delta_entitlements or {}) if addon is not None else {},
                }
            )
        return lines

    @staticmethod
    def _remaining_days(expires_at: datetime | None) -> int:
        resolved = EntitlementsService._to_utc_datetime(expires_at)
        if resolved is None:
            return 0
        seconds = max(0.0, (resolved - datetime.now(UTC)).total_seconds())
        return max(1, math.ceil(seconds / 86400))
