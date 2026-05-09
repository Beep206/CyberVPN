"""S1-PAY-011 Telegram Stars readiness contract checks."""

from __future__ import annotations

from uuid import UUID

import pytest

from src.infrastructure.payments.telegram_stars.client import TelegramStarsClient
from src.presentation.api.shared.stage1_payment_mapping import (
    Stage1PaymentProvider,
    Stage1PaymentState,
    resolve_stage1_provider_payment_status,
)
from src.presentation.api.v1.payments import telegram_stars as miniapp_stars
from src.presentation.api.v1.telegram.routes import (
    _build_telegram_stars_invoice_payload,
    _parse_telegram_stars_invoice_payload,
)


def test_stage1_telegram_stars_pre_checkout_never_unlocks_access() -> None:
    decision = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.TELEGRAM_STARS,
        "pre_checkout_query",
    )

    assert decision.payment_state == Stage1PaymentState.PROCESSING
    assert decision.automatic_paid_access_allowed is False
    assert decision.final is False


def test_stage1_telegram_stars_successful_payment_is_only_paid_state() -> None:
    decision = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.TELEGRAM_STARS,
        "successful_payment",
    )

    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.automatic_paid_access_allowed is True
    assert decision.final is True


def test_stage1_telegram_stars_invoice_payload_binds_payment_to_user() -> None:
    payment_id = "4b6b5fa1-6f12-4cfd-8fb8-72e5c2d3e701"
    payload = _build_telegram_stars_invoice_payload(payment_id=payment_id, telegram_id=123456789)

    assert payload == f"stars:{payment_id}:123456789"
    assert _parse_telegram_stars_invoice_payload(payload) == (UUID(payment_id), 123456789)
    assert _parse_telegram_stars_invoice_payload("stars:not-a-uuid:123456789") is None
    assert _parse_telegram_stars_invoice_payload(f"stars:{payment_id}:not-a-user") is None


@pytest.mark.asyncio
async def test_stage1_miniapp_invoice_link_uses_stars_only_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeSecret:
        def get_secret_value(self) -> str:
            return "redacted-bot-token"

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"ok": True, "result": "https://t.me/invoice/redacted"}

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(miniapp_stars.settings, "telegram_bot_token", FakeSecret())
    monkeypatch.setattr(miniapp_stars.httpx, "AsyncClient", FakeAsyncClient)

    result = await miniapp_stars._create_telegram_invoice_link(
        title="CyberVPN Pro",
        description="CyberVPN access for 30 days",
        invoice_payload="stars:4b6b5fa1-6f12-4cfd-8fb8-72e5c2d3e701:123456789",
        stars_amount=500,
    )

    assert result == "https://t.me/invoice/redacted"
    assert captured["url"] == "https://api.telegram.org/botredacted-bot-token/createInvoiceLink"
    request_payload = captured["json"]
    assert isinstance(request_payload, dict)
    assert request_payload["provider_token"] == ""
    assert request_payload["currency"] == "XTR"
    assert request_payload["prices"] == [{"label": "CyberVPN Pro", "amount": 500}]
    assert "need_email" not in request_payload
    assert "need_phone_number" not in request_payload
    assert "need_shipping_address" not in request_payload


@pytest.mark.asyncio
async def test_stage1_telegram_stars_refund_client_uses_refund_star_payment() -> None:
    captured: dict[str, object] = {}
    client = TelegramStarsClient("redacted-bot-token")

    class FakeHttp:
        async def post(self, url: str, *, json: dict[str, object]) -> object:
            captured["url"] = url
            captured["json"] = json

            class FakeResponse:
                status_code = 200

                def json(self) -> dict[str, object]:
                    return {"ok": True, "result": True}

            return FakeResponse()

    async def fake_get_client() -> FakeHttp:
        return FakeHttp()

    client._get_client = fake_get_client  # type: ignore[method-assign]

    result = await client.refund_payment(
        user_id=123456789,
        telegram_payment_charge_id="tg-stars-charge-1",
        provider_payment_charge_id="provider-charge-1",
    )

    assert captured["url"] == "/botredacted-bot-token/refundStarPayment"
    assert captured["json"] == {
        "user_id": 123456789,
        "telegram_payment_charge_id": "tg-stars-charge-1",
    }
    assert result.provider_snapshot["refund_method"] == "refundStarPayment"
