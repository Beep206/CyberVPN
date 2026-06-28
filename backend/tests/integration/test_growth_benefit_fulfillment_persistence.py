from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_benefits.fulfill import (
    FulfillGrowthBenefitsUseCase,
    GrowthBenefitConfigurationError,
)
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.growth_benefit_model import GrowthCodeBenefitModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeIssuanceModel, GrowthCodeModel
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel, SubscriptionAddonModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.growth_benefit_fulfillment_repo import (
    GrowthBenefitFulfillmentRepository,
)

pytestmark = [pytest.mark.integration]

NOW = datetime(2026, 6, 27, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_growth_benefit_fulfillment_persists_bonus_gifts_and_addons_once(db: AsyncSession) -> None:
    context = await _seed_growth_benefit_context(db)
    snapshot = _growth_effects_snapshot(context)

    first = await FulfillGrowthBenefitsUseCase(GrowthBenefitFulfillmentRepository(db)).execute(
        order_id=context["order_id"],
        payment_id=context["payment_id"],
        user_id=context["user_id"],
        growth_effects_snapshot=snapshot,
        settlement_completed=True,
        occurred_at=NOW,
    )
    replay = await FulfillGrowthBenefitsUseCase(GrowthBenefitFulfillmentRepository(db)).execute(
        order_id=context["order_id"],
        payment_id=context["payment_id"],
        user_id=context["user_id"],
        growth_effects_snapshot=snapshot,
        settlement_completed=True,
        occurred_at=NOW + timedelta(minutes=1),
    )

    assert [result.status for result in first] == ["completed", "completed", "completed"]
    assert [result.duplicate for result in replay] == [True, True, True]

    bonus_count = await db.scalar(
        select(func.count())
        .select_from(GrowthRewardAllocationModel)
        .where(
            GrowthRewardAllocationModel.order_id == context["order_id"],
            GrowthRewardAllocationModel.reward_type == "bonus_days",
        )
    )
    gift_count = await db.scalar(
        select(func.count())
        .select_from(GrowthCodeModel)
        .join(GrowthCodeIssuanceModel, GrowthCodeIssuanceModel.growth_code_id == GrowthCodeModel.id)
        .where(
            GrowthCodeModel.code_type == "gift",
            GrowthCodeIssuanceModel.source_payment_id == context["payment_id"],
            GrowthCodeIssuanceModel.issuance_type == "growth_benefit",
        )
    )
    addon_count = await db.scalar(
        select(func.count())
        .select_from(SubscriptionAddonModel)
        .where(
            SubscriptionAddonModel.payment_id == context["payment_id"],
            SubscriptionAddonModel.plan_addon_id == context["addon_id"],
        )
    )
    grant_expires_at = await db.scalar(
        select(EntitlementGrantModel.expires_at).where(EntitlementGrantModel.id == context["entitlement_grant_id"])
    )

    assert bonus_count == 1
    assert gift_count == 2
    assert addon_count == 1
    assert grant_expires_at == context["original_expires_at"] + timedelta(days=5)


@pytest.mark.asyncio
async def test_grant_addon_benefit_fails_closed_without_plan_code_snapshot(db: AsyncSession) -> None:
    context = await _seed_growth_benefit_context(db)
    grant = await db.get(EntitlementGrantModel, context["entitlement_grant_id"])
    assert grant is not None
    grant.grant_snapshot = {"effective_entitlements": {"device_limit": 2}}
    await db.flush()

    with pytest.raises(GrowthBenefitConfigurationError, match="requires plan_code"):
        await FulfillGrowthBenefitsUseCase(GrowthBenefitFulfillmentRepository(db)).execute(
            order_id=context["order_id"],
            payment_id=context["payment_id"],
            user_id=context["user_id"],
            growth_effects_snapshot=_addon_only_growth_effects_snapshot(context),
            settlement_completed=True,
            occurred_at=NOW,
        )

    addon_count = await db.scalar(
        select(func.count())
        .select_from(SubscriptionAddonModel)
        .where(
            SubscriptionAddonModel.payment_id == context["payment_id"],
            SubscriptionAddonModel.plan_addon_id == context["addon_id"],
        )
    )
    assert addon_count == 0


@pytest.mark.asyncio
async def test_grant_addon_benefit_fails_closed_for_plan_not_allowed_by_addon(db: AsyncSession) -> None:
    context = await _seed_growth_benefit_context(db)
    grant = await db.get(EntitlementGrantModel, context["entitlement_grant_id"])
    assert grant is not None
    grant.grant_snapshot = {
        "plan_code": "unknown-plan",
        "effective_entitlements": {"device_limit": 2},
    }
    await db.flush()

    with pytest.raises(GrowthBenefitConfigurationError, match="not compatible"):
        await FulfillGrowthBenefitsUseCase(GrowthBenefitFulfillmentRepository(db)).execute(
            order_id=context["order_id"],
            payment_id=context["payment_id"],
            user_id=context["user_id"],
            growth_effects_snapshot=_addon_only_growth_effects_snapshot(context),
            settlement_completed=True,
            occurred_at=NOW,
        )

    addon_count = await db.scalar(
        select(func.count())
        .select_from(SubscriptionAddonModel)
        .where(
            SubscriptionAddonModel.payment_id == context["payment_id"],
            SubscriptionAddonModel.plan_addon_id == context["addon_id"],
        )
    )
    assert addon_count == 0


async def _seed_growth_benefit_context(db: AsyncSession) -> dict[str, uuid.UUID | datetime | str]:
    suffix = uuid.uuid4().hex[:10]
    realm_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    storefront_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    quote_session_id = uuid.uuid4()
    checkout_session_id = uuid.uuid4()
    order_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    growth_code_id = uuid.uuid4()
    bonus_benefit_id = uuid.uuid4()
    gift_benefit_id = uuid.uuid4()
    addon_benefit_id = uuid.uuid4()
    addon_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    entitlement_grant_id = uuid.uuid4()
    original_expires_at = NOW + timedelta(days=30)

    db.add_all(
        [
            AuthRealmModel(
                id=realm_id,
                realm_key=f"fulfill-{suffix}",
                realm_type="customer",
                display_name="Fulfillment Test Realm",
                audience=f"fulfill-{suffix}.example.test",
                cookie_namespace=f"fulfill-{suffix}",
                status="active",
                is_default=False,
            ),
            BrandModel(
                id=brand_id,
                brand_key=f"fulfill-{suffix}",
                display_name="Fulfillment Brand",
                status="active",
            ),
            MobileUserModel(
                id=user_id,
                public_uid=30_000_000 + int(suffix[:6], 16) % 50_000_000,
                auth_realm_id=realm_id,
                email=f"fulfill-{suffix}@example.test",
                password_hash="hash",
                notification_prefs={},
                totp_enabled=False,
                is_active=True,
                status="active",
            ),
            SubscriptionPlanModel(
                id=plan_id,
                name=f"Fulfillment Plan {suffix}",
                tier="pro",
                plan_code=f"ful-{suffix[:6]}",
                display_name="Fulfillment Plan",
                catalog_visibility="hidden",
                duration_days=30,
                traffic_limit_bytes=None,
                device_limit=2,
                price_usd=Decimal("10.00"),
                price_rub=None,
                sale_channels=["web"],
                traffic_policy={},
                connection_modes=["standard"],
                server_pool=["shared"],
                support_sla="standard",
                dedicated_ip={},
                invite_bundle={},
                trial_eligible=False,
                features={},
                is_active=True,
                sort_order=0,
            ),
        ]
    )
    await db.flush()
    db.add(
        StorefrontModel(
            id=storefront_id,
            storefront_key=f"fulfill-{suffix}",
            brand_id=brand_id,
            display_name="Fulfillment Storefront",
            host=f"fulfill-{suffix}.example.test",
            auth_realm_id=realm_id,
            status="active",
        )
    )
    await db.flush()
    db.add(
        GrowthCodeModel(
            id=growth_code_id,
            code_hash=f"hash-{suffix}",
            code_prefix="PR",
            code_type="promo",
            status="active",
            issuer_type="system",
            max_uses=100,
            storefront_id=storefront_id,
            auth_realm_id=realm_id,
        )
    )
    await db.flush()
    db.add_all(
        [
            GrowthCodeBenefitModel(
                id=bonus_benefit_id,
                growth_code_id=growth_code_id,
                benefit_type="bonus_days",
                trigger_type="payment_completed",
                merge_mode="append",
                config={},
                eligibility={},
                sort_order=0,
                is_active=True,
            ),
            GrowthCodeBenefitModel(
                id=gift_benefit_id,
                growth_code_id=growth_code_id,
                benefit_type="issue_gift",
                trigger_type="payment_completed",
                merge_mode="append",
                config={},
                eligibility={},
                sort_order=1,
                is_active=True,
            ),
            GrowthCodeBenefitModel(
                id=addon_benefit_id,
                growth_code_id=growth_code_id,
                benefit_type="grant_addon",
                trigger_type="payment_completed",
                merge_mode="append",
                config={},
                eligibility={},
                sort_order=2,
                is_active=True,
            ),
        ]
    )
    await db.flush()
    db.add(
        QuoteSessionModel(
            id=quote_session_id,
            user_id=user_id,
            auth_realm_id=realm_id,
            storefront_id=storefront_id,
            subscription_plan_id=plan_id,
            sale_channel="web",
            currency_code="USD",
            request_snapshot={},
            quote_snapshot={},
            context_snapshot={},
            expires_at=NOW + timedelta(hours=1),
        )
    )
    await db.flush()
    db.add_all(
        [
            CheckoutSessionModel(
                id=checkout_session_id,
                quote_session_id=quote_session_id,
                user_id=user_id,
                auth_realm_id=realm_id,
                storefront_id=storefront_id,
                subscription_plan_id=plan_id,
                sale_channel="web",
                currency_code="USD",
                checkout_status="committed",
                idempotency_key=f"fulfill-{suffix}",
                request_snapshot={},
                checkout_snapshot={},
                context_snapshot={},
                expires_at=NOW + timedelta(hours=1),
            ),
            PlanAddonModel(
                id=addon_id,
                code=f"extra-device-{suffix}",
                display_name="Extra Device",
                duration_mode="inherits_subscription",
                is_stackable=True,
                quantity_step=1,
                price_usd=Decimal("0.00"),
                price_rub=None,
                max_quantity_by_plan={f"ful-{suffix[:6]}": 3},
                delta_entitlements={"device_limit": 1},
                requires_location=False,
                sale_channels=["web"],
                is_active=True,
            ),
            PaymentModel(
                id=payment_id,
                external_id=f"fulfill-payment-{suffix}",
                user_uuid=user_id,
                amount=Decimal("10.00"),
                currency="USD",
                status="completed",
                provider="cryptobot",
                subscription_days=30,
                plan_id=plan_id,
                discount_amount=Decimal("0.00"),
                wallet_amount_used=Decimal("0.00"),
                final_amount=Decimal("10.00"),
                addons_snapshot=[],
                entitlements_snapshot={},
                metadata_={},
            ),
            ServiceIdentityModel(
                id=service_identity_id,
                service_key=f"fulfill-service-{suffix}",
                customer_account_id=user_id,
                auth_realm_id=realm_id,
                source_order_id=None,
                origin_storefront_id=storefront_id,
                provider_name="local",
                identity_scope="subscription",
                subscription_key=f"sub-{suffix}",
                identity_status="active",
                service_context={},
            ),
        ]
    )
    await db.flush()
    db.add(
        OrderModel(
            id=order_id,
            quote_session_id=quote_session_id,
            checkout_session_id=checkout_session_id,
            user_id=user_id,
            auth_realm_id=realm_id,
            storefront_id=storefront_id,
            subscription_plan_id=plan_id,
            sale_channel="web",
            currency_code="USD",
            order_status="committed",
            settlement_status="paid",
            base_price=Decimal("10.00"),
            addon_amount=Decimal("0.00"),
            displayed_price=Decimal("10.00"),
            discount_amount=Decimal("0.00"),
            wallet_amount=Decimal("0.00"),
            gateway_amount=Decimal("10.00"),
            partner_markup=Decimal("0.00"),
            commission_base_amount=Decimal("10.00"),
            merchant_snapshot={},
            pricing_snapshot={},
            policy_snapshot={},
            risk_snapshot={},
            fx_snapshot={},
            entitlements_snapshot={"plan_code": f"ful-{suffix[:6]}"},
        )
    )
    await db.flush()
    db.add(
        EntitlementGrantModel(
            id=entitlement_grant_id,
            grant_key=f"fulfill-grant-{suffix}",
            service_identity_id=service_identity_id,
            customer_account_id=user_id,
            auth_realm_id=realm_id,
            origin_storefront_id=storefront_id,
            source_type="order",
            source_order_id=order_id,
            grant_status="active",
            grant_snapshot={
                "plan_code": f"ful-{suffix[:6]}",
                "effective_entitlements": {"device_limit": 2},
            },
            source_snapshot={},
            effective_from=NOW - timedelta(days=1),
            expires_at=original_expires_at,
            activated_at=NOW - timedelta(days=1),
        )
    )
    await db.flush()
    return {
        "realm_id": realm_id,
        "storefront_id": storefront_id,
        "user_id": user_id,
        "plan_id": plan_id,
        "order_id": order_id,
        "payment_id": payment_id,
        "growth_code_id": growth_code_id,
        "bonus_benefit_id": bonus_benefit_id,
        "gift_benefit_id": gift_benefit_id,
        "addon_benefit_id": addon_benefit_id,
        "addon_id": addon_id,
        "addon_code": f"extra-device-{suffix}",
        "entitlement_grant_id": entitlement_grant_id,
        "original_expires_at": original_expires_at,
    }


def _growth_effects_snapshot(context: dict[str, uuid.UUID | datetime | str]) -> dict:
    return {
        "settlement": {
            "net_customer_paid_amount": "10.00",
            "gateway_amount": "10.00",
            "settlement_mode": "external_payment",
        },
        "code_set": {
            "applications": [
                {
                    "growth_code_id": str(context["growth_code_id"]),
                    "benefits": [
                        {
                            "benefit_id": str(context["bonus_benefit_id"]),
                            "type": "bonus_days",
                            "trigger_type": "payment_completed",
                            "config": {
                                "days": 5,
                                "grant_mode": "extend_current_subscription",
                                "entitlement_profile_key": "paid_access",
                                "allow_zero_net_payment": False,
                                "minimum_net_paid_amount": "1.00",
                                "reversal_mode": "shorten_entitlement",
                            },
                        },
                        {
                            "benefit_id": str(context["gift_benefit_id"]),
                            "type": "issue_gift",
                            "trigger_type": "payment_completed",
                            "config": {
                                "count": 2,
                                "friend_days": 30,
                                "expiry_mode": "relative",
                                "expiry_days": 30,
                                "absolute_expires_at": None,
                                "entitlement_mode": "plan_id",
                                "plan_id": str(context["plan_id"]),
                                "entitlement_profile_key": None,
                                "entitlement_snapshot": None,
                                "allow_zero_net_payment": False,
                                "minimum_net_paid_amount": "1.00",
                                "reversal_mode": "revoke_unredeemed",
                            },
                        },
                        {
                            "benefit_id": str(context["addon_benefit_id"]),
                            "type": "grant_addon",
                            "trigger_type": "payment_completed",
                            "config": {
                                "addon_code": str(context["addon_code"]),
                                "quantity": 1,
                                "duration_mode": "match_plan",
                                "duration_days": None,
                                "location_code": None,
                                "allow_zero_net_payment": False,
                                "minimum_net_paid_amount": "1.00",
                                "reversal_mode": "revoke_addon",
                            },
                        },
                    ],
                }
            ]
        },
    }


def _addon_only_growth_effects_snapshot(context: dict[str, uuid.UUID | datetime | str]) -> dict:
    snapshot = _growth_effects_snapshot(context)
    application = snapshot["code_set"]["applications"][0]
    application["benefits"] = [benefit for benefit in application["benefits"] if benefit["type"] == "grant_addon"]
    return snapshot
