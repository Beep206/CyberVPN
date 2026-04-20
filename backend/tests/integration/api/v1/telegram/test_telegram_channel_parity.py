from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from src.config.settings import settings


def _bot_headers() -> dict[str, str]:
    return {"X-Telegram-Bot-Secret": "telegram-test-secret"}


def _entitlement_snapshot() -> dict:
    return {
        "status": "active",
        "plan_uuid": "plan-pro-001",
        "plan_code": "pro",
        "display_name": "Pro Plan",
        "period_days": 30,
        "expires_at": "2026-05-01T12:00:00Z",
        "effective_entitlements": {
            "device_limit": 5,
        },
        "invite_bundle": {"count": 1, "friend_days": 7, "expiry_days": 30},
        "is_trial": False,
        "addons": [],
    }


def _fake_order():
    order_id = uuid4()
    item = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        item_type="plan",
        subject_id=uuid4(),
        subject_code="pro",
        display_name="Pro Plan",
        quantity=1,
        unit_price=29.99,
        total_price=29.99,
        currency_code="USD",
        item_snapshot={},
        created_at=datetime(2026, 4, 18, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 18, 10, 0, tzinfo=UTC),
    )
    return SimpleNamespace(
        id=order_id,
        quote_session_id=uuid4(),
        checkout_session_id=uuid4(),
        user_id=uuid4(),
        auth_realm_id=uuid4(),
        storefront_id=uuid4(),
        merchant_profile_id=None,
        invoice_profile_id=None,
        billing_descriptor_id=None,
        pricebook_id=None,
        pricebook_entry_id=None,
        offer_id=None,
        legal_document_set_id=None,
        program_eligibility_policy_id=None,
        subscription_plan_id=uuid4(),
        promo_code_id=None,
        partner_code_id=None,
        sale_channel="telegram_bot",
        currency_code="USD",
        order_status="committed",
        settlement_status="paid",
        base_price=29.99,
        addon_amount=0,
        displayed_price=29.99,
        discount_amount=0,
        wallet_amount=0,
        gateway_amount=29.99,
        partner_markup=0,
        commission_base_amount=29.99,
        merchant_snapshot={},
        pricing_snapshot={"display_name": "Pro Plan"},
        policy_snapshot={},
        entitlements_snapshot=_entitlement_snapshot(),
        items=[item],
        created_at=datetime(2026, 4, 18, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 18, 10, 0, tzinfo=UTC),
    )


class TestTelegramChannelParity:
    @pytest.mark.integration
    async def test_bot_subscription_summary_uses_canonical_entitlements(
        self,
        async_client: AsyncClient,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
        mobile_user = SimpleNamespace(id=uuid4(), auth_realm_id=None)

        with patch(
            "src.presentation.api.v1.telegram.routes._get_mobile_user_or_404",
            AsyncMock(return_value=mobile_user),
        ), patch(
            "src.presentation.api.v1.telegram.routes.GetCurrentEntitlementsUseCase.execute",
            AsyncMock(return_value=_entitlement_snapshot()),
        ):
            response = await async_client.get(
                "/api/v1/telegram/bot/user/123456/subscriptions",
                headers=_bot_headers(),
            )

        assert response.status_code == 200
        assert response.json() == [
            {
                "status": "active",
                "plan_name": "Pro Plan",
                "expires_at": "2026-05-01T12:00:00Z",
                "traffic_limit_bytes": None,
                "used_traffic_bytes": None,
                "auto_renew": False,
            }
        ]

    @pytest.mark.integration
    async def test_bot_orders_endpoint_returns_canonical_order_history(
        self,
        async_client: AsyncClient,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
        mobile_user = SimpleNamespace(id=uuid4(), auth_realm_id=None)
        fake_order = _fake_order()

        with patch(
            "src.presentation.api.v1.telegram.routes._get_mobile_user_or_404",
            AsyncMock(return_value=mobile_user),
        ), patch(
            "src.presentation.api.v1.telegram.routes.ListOrdersUseCase.execute",
            AsyncMock(return_value=[fake_order]),
        ):
            response = await async_client.get(
                "/api/v1/telegram/bot/user/123456/orders?limit=10&offset=0",
                headers=_bot_headers(),
            )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["sale_channel"] == "telegram_bot"
        assert payload[0]["settlement_status"] == "paid"
        assert payload[0]["items"][0]["display_name"] == "Pro Plan"

    @pytest.mark.integration
    async def test_bot_service_state_endpoint_returns_canonical_service_state(
        self,
        async_client: AsyncClient,
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
        mobile_user = SimpleNamespace(id=uuid4(), auth_realm_id=None)
        service_state = SimpleNamespace(
            entitlement_snapshot=_entitlement_snapshot(),
            service_identity=None,
            provisioning_profile=None,
            device_credential=None,
            access_delivery_channel=None,
            active_entitlement_grant=None,
            resolved_channel_subject_ref=None,
            resolved_provisioning_profile_key=None,
        )

        with patch(
            "src.presentation.api.v1.telegram.routes._get_mobile_user_or_404",
            AsyncMock(return_value=mobile_user),
        ), patch(
            "src.presentation.api.v1.telegram.routes._resolve_bot_customer_realm",
            AsyncMock(return_value=SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4()))),
        ), patch(
            "src.presentation.api.v1.telegram.routes.GetCurrentServiceStateUseCase.execute",
            AsyncMock(return_value=service_state),
        ):
            response = await async_client.get(
                "/api/v1/telegram/bot/user/123456/service-state",
                headers=_bot_headers(),
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["provider_name"] == "remnawave"
        assert payload["entitlement_snapshot"]["status"] == "active"
        assert payload["consumption_context"]["channel_type"] == "telegram_bot"
        assert payload["consumption_context"]["credential_type"] == "telegram_bot"
        assert payload["consumption_context"]["credential_subject_key"] == "telegram-bot:123456"
