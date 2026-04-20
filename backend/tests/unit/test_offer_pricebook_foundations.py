from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.entities.offer import Offer, Pricebook, PricebookEntry
from src.domain.entities.plan_addon import PlanAddon
from src.domain.entities.program_eligibility_policy import ProgramEligibilityPolicy
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.enums import CatalogVisibility, PlanCode, PolicyVersionStatus


def test_subscription_plan_and_addon_expose_product_catalog_identity_separately_from_overlays() -> None:
    plan = SubscriptionPlan(
        uuid=uuid4(),
        name="plus_365",
        plan_code=PlanCode.PLUS,
        display_name="Plus",
        catalog_visibility=CatalogVisibility.PUBLIC,
        duration_days=365,
        traffic_limit_bytes=None,
        device_limit=5,
        price_usd=Decimal("79.00"),
        price_rub=None,
        traffic_policy={"mode": "fair_use"},
        connection_modes=["standard", "stealth"],
        server_pool=["shared_plus"],
        support_sla="standard",
        dedicated_ip={"eligible": True},
        sale_channels=["web"],
        invite_bundle={"count": 2},
        trial_eligible=False,
        features={"audience": "mass_market"},
        is_active=True,
        sort_order=20,
    )
    addon = PlanAddon(
        uuid=uuid4(),
        code="extra_device",
        display_name="Extra Device",
        duration_mode="inherits_subscription",
        is_stackable=True,
        quantity_step=1,
        price_usd=Decimal("5.00"),
        price_rub=None,
        max_quantity_by_plan={"plus": 5},
        delta_entitlements={"device_limit_delta": 1},
        requires_location=False,
        sale_channels=["web"],
        is_active=True,
    )

    assert plan.product_family_key == "plus"
    assert plan.legacy_offer_overlay["invite_bundle"] == {"count": 2}
    assert addon.product_family_key == "extra_device"
    assert addon.legacy_eligibility_overlay["sale_channels"] == ["web"]


def test_multiple_offers_and_pricebooks_can_reference_same_product_family() -> None:
    plan_id = uuid4()
    now = datetime.now(UTC)
    margin_offer = Offer(
        uuid=uuid4(),
        offer_key="plus-margin",
        display_name="Plus Margin",
        subscription_plan_id=plan_id,
        included_addon_codes=[],
        sale_channels=["web"],
        visibility_rules={"surface": "official"},
        invite_bundle={"count": 0},
        trial_eligible=False,
        gift_eligible=False,
        referral_eligible=False,
        renewal_incentives={"renewal_discount_pct": 10},
        version_status=PolicyVersionStatus.ACTIVE,
        effective_from=now,
        effective_to=None,
        is_active=True,
    )
    conversion_offer = Offer(
        uuid=uuid4(),
        offer_key="plus-conversion",
        display_name="Plus Conversion",
        subscription_plan_id=plan_id,
        included_addon_codes=[],
        sale_channels=["web"],
        visibility_rules={"surface": "partner"},
        invite_bundle={"count": 0},
        trial_eligible=False,
        gift_eligible=False,
        referral_eligible=True,
        renewal_incentives={"renewal_discount_pct": 20},
        version_status=PolicyVersionStatus.ACTIVE,
        effective_from=now,
        effective_to=None,
        is_active=True,
    )

    official_pricebook = Pricebook(
        uuid=uuid4(),
        pricebook_key="official-usd",
        display_name="Official USD",
        storefront_id=uuid4(),
        merchant_profile_id=None,
        currency_code="USD",
        region_code=None,
        discount_rules={"promo_stacking": False},
        renewal_pricing_policy={"renewal_source": "current_active_pricebook"},
        entries=[
            PricebookEntry(
                uuid=uuid4(),
                offer_id=margin_offer.uuid,
                visible_price=79.0,
                compare_at_price=99.0,
                included_addon_codes=[],
                display_order=0,
            )
        ],
        version_status=PolicyVersionStatus.ACTIVE,
        effective_from=now,
        effective_to=None,
        is_active=True,
    )
    partner_pricebook = Pricebook(
        uuid=uuid4(),
        pricebook_key="partner-usd",
        display_name="Partner USD",
        storefront_id=uuid4(),
        merchant_profile_id=None,
        currency_code="USD",
        region_code=None,
        discount_rules={"promo_stacking": False},
        renewal_pricing_policy={"renewal_source": "current_active_pricebook"},
        entries=[
            PricebookEntry(
                uuid=uuid4(),
                offer_id=conversion_offer.uuid,
                visible_price=69.0,
                compare_at_price=89.0,
                included_addon_codes=["extra_device"],
                display_order=0,
            )
        ],
        version_status=PolicyVersionStatus.ACTIVE,
        effective_from=now,
        effective_to=None,
        is_active=True,
    )

    assert margin_offer.subscription_plan_id == conversion_offer.subscription_plan_id
    assert official_pricebook.entries[0].visible_price != partner_pricebook.entries[0].visible_price


def test_program_eligibility_requires_one_subject_and_valid_effective_window() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="exactly one subject"):
        ProgramEligibilityPolicy(
            uuid=uuid4(),
            policy_key="invalid",
            subject_type="plan",
            subscription_plan_id=uuid4(),
            plan_addon_id=uuid4(),
            offer_id=None,
            invite_allowed=False,
            referral_credit_allowed=False,
            creator_affiliate_allowed=False,
            performance_allowed=False,
            reseller_allowed=False,
            renewal_commissionable=False,
            addon_commissionable=False,
            version_status=PolicyVersionStatus.ACTIVE,
            effective_from=now,
            effective_to=None,
            is_active=True,
        )

    with pytest.raises(ValueError, match="effective_to"):
        Offer(
            uuid=uuid4(),
            offer_key="expired",
            display_name="Expired",
            subscription_plan_id=uuid4(),
            included_addon_codes=[],
            sale_channels=["web"],
            visibility_rules={},
            invite_bundle={},
            trial_eligible=False,
            gift_eligible=False,
            referral_eligible=False,
            renewal_incentives={},
            version_status=PolicyVersionStatus.ACTIVE,
            effective_from=now,
            effective_to=now - timedelta(days=1),
            is_active=True,
        )
