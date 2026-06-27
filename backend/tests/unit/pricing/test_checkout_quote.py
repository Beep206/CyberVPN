from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payments import checkout as checkout_module
from src.application.use_cases.payments.checkout import (
    CheckoutAddonInput,
    CheckoutUseCase,
)
from src.config.settings import settings


def _build_plan(**overrides):
    base = {
        "id": uuid4(),
        "name": "plus_365",
        "plan_code": "plus",
        "display_name": "Plus",
        "catalog_visibility": "public",
        "catalog_access_class": "public",
        "duration_days": 365,
        "device_limit": 5,
        "price_usd": Decimal("79.00"),
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "connection_modes": ["standard", "stealth"],
        "server_pool": ["shared_plus"],
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": True},
        "invite_bundle": {"count": 1, "friend_days": 14, "expiry_days": 60},
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "is_active": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_addon(**overrides):
    base = {
        "id": uuid4(),
        "code": "extra_device",
        "display_name": "+1 device",
        "price_usd": Decimal("5.00"),
        "delta_entitlements": {"device_limit": 1},
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "is_active": True,
        "quantity_step": 1,
        "is_stackable": True,
        "requires_location": False,
        "max_quantity_by_plan": {"plus": 3},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_partner_code(**overrides):
    base = {
        "id": uuid4(),
        "partner_account_id": uuid4(),
        "partner_user_id": uuid4(),
        "markup_pct": Decimal("20.00"),
        "is_active": True,
        "lifecycle_status": "active",
        "approval_status": "approved",
        "active_from": None,
        "expires_at": None,
        "owner_type": "affiliate",
        "code_kind": "starter_code",
        "lane_key": "creator_affiliate",
        "attribution_model": "last_eligible_touch",
        "attribution_window_seconds": 30 * 24 * 60 * 60,
        "policy_version_id": None,
        "commission_contract_id": None,
        "allowed_channels": ["web"],
        "allowed_storefront_ids": ["*"],
        "allowed_geographies": ["*"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_private_grant(**overrides):
    base = {
        "id": uuid4(),
        "policy_id": uuid4(),
        "policy_version_id": uuid4(),
        "growth_code_id": uuid4(),
        "code_set_hash": "8" * 64,
        "user_id": uuid4(),
        "anonymous_session_id": None,
        "storefront_id": uuid4(),
        "sale_channel": "web",
        "allowed_plan_ids": [],
        "status": "issued",
        "max_quote_conversions": 1,
        "quote_conversions_count": 0,
        "attached_quote_session_id": None,
        "expires_at": datetime.now(UTC) + timedelta(minutes=15),
        "revoked_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _allow_runtime_risk(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_evaluate_growth_runtime_risk(**_kwargs):
        return SimpleNamespace(decision=SimpleNamespace(decision_id=None))

    monkeypatch.setattr(checkout_module, "evaluate_growth_runtime_risk", fake_evaluate_growth_runtime_risk)


@pytest.mark.asyncio
async def test_checkout_quote_applies_addons_to_entitlements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stage1_addons_enabled", True)
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan()
    addon = _build_addon()

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[addon]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("25.00"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=uuid4(),
        plan_id=plan.id,
        addons=[CheckoutAddonInput(code="extra_device", qty=2)],
        use_wallet=Decimal("10.00"),
        sale_channel="web",
    )

    assert result.base_price == Decimal("79.00")
    assert result.addon_amount == Decimal("10.00")
    assert result.displayed_price == Decimal("89.00")
    assert result.wallet_amount == Decimal("10.00")
    assert result.gateway_amount == Decimal("79.00")
    assert result.entitlements_snapshot["effective_entitlements"]["device_limit"] == 7
    assert result.entitlements_snapshot["addons"] == [{"code": "extra_device", "qty": 2, "location_code": None}]


@pytest.mark.asyncio
async def test_checkout_quote_uses_effective_catalog_base_price() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan(price_usd=Decimal("90.00"))

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=uuid4(),
        plan_id=plan.id,
        catalog_base_price=Decimal("75.00"),
        sale_channel="web",
    )

    assert result.base_price == Decimal("75.00")
    assert result.displayed_price == Decimal("75.00")
    assert result.gateway_amount == Decimal("75.00")
    assert result.commission_base_amount == Decimal("75.00")


@pytest.mark.asyncio
async def test_checkout_quote_rejects_hidden_plan_on_public_channel() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    hidden_plan = _build_plan(catalog_visibility="hidden")

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=hidden_plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    with pytest.raises(ValueError, match="not available on this channel"):
        await use_case.execute(
            user_id=uuid4(),
            plan_id=hidden_plan.id,
            sale_channel="web",
        )


@pytest.mark.asyncio
async def test_checkout_quote_requires_private_catalog_grant_for_private_plan() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    private_plan = _build_plan(
        plan_code="ru_basic",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
    )
    wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = wallet

    with pytest.raises(ValueError, match="PRIVATE_CATALOG_GRANT_REQUIRED"):
        await use_case.execute(
            user_id=uuid4(),
            plan_id=private_plan.id,
            sale_channel="web",
            storefront_id=uuid4(),
        )

    wallet.get_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkout_quote_rejects_private_catalog_grant_for_public_plan() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan()
    grant_id = uuid4()

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock())

    with pytest.raises(ValueError, match="PRIVATE_CATALOG_GRANT_NOT_APPLICABLE"):
        await use_case.execute(
            user_id=uuid4(),
            plan_id=plan.id,
            sale_channel="web",
            storefront_id=uuid4(),
            private_catalog_grant_id=grant_id,
        )

    use_case._private_catalog_repo.get_access_grant_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkout_quote_rejects_private_catalog_grant_for_different_user() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    user_id = uuid4()
    storefront_id = uuid4()
    private_plan = _build_plan(
        plan_code="ru_basic",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
    )
    grant = _build_private_grant(
        user_id=uuid4(),
        storefront_id=storefront_id,
        allowed_plan_ids=[str(private_plan.id)],
    )
    wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock(return_value=grant))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = wallet

    with pytest.raises(ValueError, match="PRIVATE_CATALOG_GRANT_SUBJECT_MISMATCH"):
        await use_case.execute(
            user_id=user_id,
            plan_id=private_plan.id,
            sale_channel="web",
            storefront_id=storefront_id,
            private_catalog_grant_id=grant.id,
        )

    wallet.get_balance.assert_not_awaited()


@pytest.mark.parametrize(
    ("grant_overrides", "expected_error"),
    [
        ({"status": "consumed"}, "PRIVATE_CATALOG_GRANT_INVALID"),
        ({"revoked_at": datetime.now(UTC)}, "PRIVATE_CATALOG_GRANT_INVALID"),
        ({"expires_at": datetime.now(UTC) - timedelta(seconds=1)}, "PRIVATE_CATALOG_GRANT_INVALID"),
        ({"storefront_id": uuid4()}, "PRIVATE_CATALOG_GRANT_SCOPE_MISMATCH"),
        ({"sale_channel": "miniapp"}, "PRIVATE_CATALOG_GRANT_SCOPE_MISMATCH"),
        ({"allowed_plan_ids": [str(uuid4())]}, "PRIVATE_OFFER_UNAVAILABLE"),
        ({"max_quote_conversions": 1, "quote_conversions_count": 1}, "PRIVATE_CATALOG_GRANT_EXHAUSTED"),
    ],
)
@pytest.mark.asyncio
async def test_checkout_quote_rejects_invalid_private_catalog_grants_before_side_effects(
    grant_overrides,
    expected_error: str,
) -> None:
    user_id = uuid4()
    storefront_id = uuid4()
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    private_plan = _build_plan(
        plan_code="ru_basic",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
    )
    private_grant_overrides = {
        "user_id": user_id,
        "storefront_id": storefront_id,
        "allowed_plan_ids": [str(private_plan.id)],
        **grant_overrides,
    }
    grant = _build_private_grant(**private_grant_overrides)
    addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock(return_value=grant))
    use_case._addon_repo = addon_repo
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = wallet

    with pytest.raises(ValueError, match=expected_error):
        await use_case.execute(
            user_id=user_id,
            plan_id=private_plan.id,
            sale_channel="web",
            storefront_id=storefront_id,
            private_catalog_grant_id=grant.id,
        )

    addon_repo.get_by_codes.assert_not_awaited()
    wallet.get_balance.assert_not_awaited()
    session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkout_quote_accepts_valid_private_catalog_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_runtime_risk(monkeypatch)
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    user_id = uuid4()
    storefront_id = uuid4()
    private_plan = _build_plan(
        plan_code="ru_basic",
        display_name="RU Basic 90",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
        price_usd=Decimal("19.00"),
    )
    grant = _build_private_grant(
        user_id=user_id,
        storefront_id=storefront_id,
        allowed_plan_ids=[str(private_plan.id)],
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock(return_value=grant))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=user_id,
        plan_id=private_plan.id,
        sale_channel="web",
        storefront_id=storefront_id,
        private_catalog_grant_id=grant.id,
    )

    assert result.plan_id == private_plan.id
    assert result.private_catalog_grant_id == grant.id
    assert result.private_catalog_snapshot is not None
    assert result.private_catalog_snapshot["grant_id"] == str(grant.id)
    assert result.private_catalog_snapshot["allowed_plan_ids"] == [str(private_plan.id)]
    assert result.private_catalog_snapshot["subject_type"] == "user"
    assert result.gateway_amount == Decimal("19.00")


@pytest.mark.asyncio
async def test_checkout_quote_rejects_stolen_anonymous_private_catalog_grant() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    user_id = uuid4()
    storefront_id = uuid4()
    private_plan = _build_plan(
        plan_code="ru_basic",
        display_name="RU Basic 90",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
        price_usd=Decimal("19.00"),
    )
    grant = _build_private_grant(
        user_id=None,
        anonymous_session_id="server-session-ref-victim",
        storefront_id=storefront_id,
        allowed_plan_ids=[str(private_plan.id)],
    )
    wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock(return_value=grant))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = wallet

    with pytest.raises(ValueError, match="PRIVATE_CATALOG_GRANT_SUBJECT_MISMATCH"):
        await use_case.execute(
            user_id=user_id,
            plan_id=private_plan.id,
            sale_channel="web",
            storefront_id=storefront_id,
            private_catalog_grant_id=grant.id,
            private_catalog_anonymous_session_id="server-session-ref-attacker",
        )

    wallet.get_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkout_quote_accepts_anonymous_grant_with_matching_server_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _allow_runtime_risk(monkeypatch)
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    storefront_id = uuid4()
    anonymous_session_id = "server-session-ref-victim"
    private_plan = _build_plan(
        plan_code="ru_basic",
        display_name="RU Basic 90",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
        price_usd=Decimal("19.00"),
    )
    grant = _build_private_grant(
        user_id=None,
        anonymous_session_id=anonymous_session_id,
        storefront_id=storefront_id,
        allowed_plan_ids=[str(private_plan.id)],
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock(return_value=grant))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=uuid4(),
        plan_id=private_plan.id,
        sale_channel="web",
        storefront_id=storefront_id,
        private_catalog_grant_id=grant.id,
        private_catalog_anonymous_session_id=anonymous_session_id,
    )

    assert result.private_catalog_snapshot is not None
    assert result.private_catalog_snapshot["subject_type"] == "anonymous_session"
    assert result.private_catalog_snapshot["anonymous_session_bound"] is True
    assert result.gateway_amount == Decimal("19.00")


@pytest.mark.asyncio
async def test_checkout_quote_accepts_grant_already_attached_to_current_quote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _allow_runtime_risk(monkeypatch)
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    user_id = uuid4()
    storefront_id = uuid4()
    quote_session_id = uuid4()
    private_plan = _build_plan(
        plan_code="ru_basic",
        display_name="RU Basic 90",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
        price_usd=Decimal("19.00"),
    )
    grant = _build_private_grant(
        user_id=user_id,
        storefront_id=storefront_id,
        allowed_plan_ids=[str(private_plan.id)],
        max_quote_conversions=1,
        quote_conversions_count=1,
        attached_quote_session_id=quote_session_id,
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_plan))
    use_case._private_catalog_repo = SimpleNamespace(get_access_grant_by_id=AsyncMock(return_value=grant))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=user_id,
        plan_id=private_plan.id,
        sale_channel="web",
        storefront_id=storefront_id,
        private_catalog_grant_id=grant.id,
        private_catalog_quote_session_id=quote_session_id,
    )

    assert result.private_catalog_grant_id == grant.id
    assert result.gateway_amount == Decimal("19.00")


@pytest.mark.asyncio
async def test_checkout_quote_prefers_explicit_partner_code_over_legacy_bound_partner() -> None:
    partner_user_id = uuid4()
    user = SimpleNamespace(id=uuid4(), partner_user_id=partner_user_id)
    account = SimpleNamespace(status="active", legacy_owner_user_id=uuid4())
    session = SimpleNamespace(get=AsyncMock(side_effect=[user, account]))
    use_case = CheckoutUseCase(session)
    plan = _build_plan(price_usd=Decimal("100.00"))
    explicit_code = _build_partner_code(markup_pct=Decimal("20.00"))
    legacy_code = _build_partner_code(markup_pct=Decimal("5.00"))

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(
        get_code_by_code=AsyncMock(return_value=explicit_code),
        get_account_by_id=AsyncMock(return_value=account),
        get_codes_by_partner=AsyncMock(return_value=[legacy_code]),
    )
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=uuid4(),
        plan_id=plan.id,
        partner_code="NEBULA20",
        sale_channel="web",
    )

    assert result.partner_code_id == explicit_code.id
    assert result.partner_markup == Decimal("20.00")
    assert result.displayed_price == Decimal("120.00")


@pytest.mark.asyncio
async def test_checkout_quote_rejects_self_attribution_before_checkout_side_effects() -> None:
    partner_user_id = uuid4()
    user = SimpleNamespace(id=partner_user_id, partner_account_id=None)
    account = SimpleNamespace(status="active", legacy_owner_user_id=uuid4())
    session = SimpleNamespace(get=AsyncMock(return_value=user))
    use_case = CheckoutUseCase(session)
    plan = _build_plan(price_usd=Decimal("100.00"))
    explicit_code = _build_partner_code(partner_user_id=partner_user_id)
    wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(
        get_code_by_code=AsyncMock(return_value=explicit_code),
        get_account_by_id=AsyncMock(return_value=account),
        get_codes_by_partner=AsyncMock(return_value=[]),
    )
    use_case._wallet = wallet

    with pytest.raises(ValueError, match="Partner code self-referral is blocked"):
        await use_case.execute(
            user_id=partner_user_id,
            plan_id=plan.id,
            partner_code="NEBULA20",
            sale_channel="web",
        )

    wallet.get_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkout_quote_rejects_explicit_partner_code_when_policy_disallows_channel() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(id=uuid4())))
    use_case = CheckoutUseCase(session)
    plan = _build_plan(price_usd=Decimal("100.00"))
    explicit_code = _build_partner_code(allowed_channels=["partner_blog"])

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(
        get_code_by_code=AsyncMock(return_value=explicit_code),
        get_account_by_id=AsyncMock(return_value=SimpleNamespace(status="active", legacy_owner_user_id=uuid4())),
        get_codes_by_partner=AsyncMock(return_value=[]),
    )
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    with pytest.raises(ValueError, match="not eligible for this checkout surface"):
        await use_case.execute(
            user_id=uuid4(),
            plan_id=plan.id,
            partner_code="NEBULA20",
            sale_channel="web",
        )
