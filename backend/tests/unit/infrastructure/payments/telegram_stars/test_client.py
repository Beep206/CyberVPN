from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.payments.telegram_stars.client import (
    TelegramStarsClient,
    TelegramStarsRefundError,
)


@pytest.mark.asyncio
async def test_refund_payment_returns_success_snapshot() -> None:
    client = TelegramStarsClient(bot_token="token")
    fake_http = MagicMock()
    fake_http.post = AsyncMock()
    fake_http.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"ok": True, "result": True}),
    )
    client._get_client = AsyncMock(return_value=fake_http)

    result = await client.refund_payment(
        user_id=123456789,
        telegram_payment_charge_id="tg-charge-1",
        provider_payment_charge_id="provider-charge-1",
    )

    fake_http.post.assert_awaited_once()
    assert result.external_reference == "tg-charge-1"
    assert result.already_refunded is False
    assert result.provider_snapshot["provider_result"] == "refunded"


@pytest.mark.asyncio
async def test_refund_payment_treats_already_refunded_as_idempotent_success() -> None:
    client = TelegramStarsClient(bot_token="token")
    fake_http = MagicMock()
    fake_http.post = AsyncMock()
    fake_http.post.return_value = MagicMock(
        status_code=400,
        json=MagicMock(return_value={"ok": False, "description": "Bad Request: CHARGE_ALREADY_REFUNDED"}),
    )
    client._get_client = AsyncMock(return_value=fake_http)

    result = await client.refund_payment(
        user_id=123456789,
        telegram_payment_charge_id="tg-charge-1",
    )

    assert result.already_refunded is True
    assert result.provider_snapshot["provider_result"] == "already_refunded"


@pytest.mark.asyncio
async def test_refund_payment_raises_for_provider_failure() -> None:
    client = TelegramStarsClient(bot_token="token")
    fake_http = MagicMock()
    fake_http.post = AsyncMock()
    fake_http.post.return_value = MagicMock(
        status_code=400,
        json=MagicMock(return_value={"ok": False, "description": "Bad Request: CHARGE_NOT_FOUND"}),
    )
    client._get_client = AsyncMock(return_value=fake_http)

    with pytest.raises(TelegramStarsRefundError, match="CHARGE_NOT_FOUND"):
        await client.refund_payment(
            user_id=123456789,
            telegram_payment_charge_id="tg-charge-1",
        )
