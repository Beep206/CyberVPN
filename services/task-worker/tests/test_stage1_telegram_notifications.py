"""Tests for the Stage 1 Telegram notification contract."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.tasks.notifications.process_queue import process_notification_queue
from src.tasks.notifications.stage1_contract import (
    STAGE1_TELEGRAM_NOTIFICATION_TYPES,
    build_stage1_telegram_notification,
)
from src.utils.constants import (
    NOTIFICATION_TYPE_PAYMENT_FAILED,
    NOTIFICATION_TYPE_PAYMENT_RECEIVED,
    NOTIFICATION_TYPE_PROVISIONING_FAILED,
    NOTIFICATION_TYPE_PROVISIONING_READY,
    NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED,
    NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING,
    STATUS_PENDING,
    STATUS_SENT,
)


def test_stage1_notification_types_cover_expiry_payment_and_provisioning() -> None:
    expected_types = {
        NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING,
        NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED,
        NOTIFICATION_TYPE_PAYMENT_RECEIVED,
        NOTIFICATION_TYPE_PAYMENT_FAILED,
        NOTIFICATION_TYPE_PROVISIONING_READY,
        NOTIFICATION_TYPE_PROVISIONING_FAILED,
    }
    assert expected_types == STAGE1_TELEGRAM_NOTIFICATION_TYPES


def test_disabled_or_unlinked_telegram_notification_is_not_queued() -> None:
    assert (
        build_stage1_telegram_notification(
            telegram_id=123,
            notification_type=NOTIFICATION_TYPE_PAYMENT_RECEIVED,
            username="sasha",
            amount=9.99,
            plan_name="Plus",
            plan_days=30,
            enabled=False,
        )
        is None
    )
    assert (
        build_stage1_telegram_notification(
            telegram_id=None,
            notification_type=NOTIFICATION_TYPE_PAYMENT_RECEIVED,
            username="sasha",
            amount=9.99,
            plan_name="Plus",
            plan_days=30,
        )
        is None
    )


@pytest.mark.parametrize(
    ("notification_type", "kwargs", "expected_text"),
    [
        (
            NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING,
            {"days_left": 2, "expire_at": "2026-05-06 12:00 UTC", "renew_url": "https://cyber-vpn.net/pay"},
            "Subscription Expiring",
        ),
        (
            NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED,
            {"expire_at": "2026-05-04 12:00 UTC"},
            "Subscription Expired",
        ),
        (
            NOTIFICATION_TYPE_PAYMENT_RECEIVED,
            {"amount": 9.99, "currency": "USD", "plan_name": "Plus", "plan_days": 30},
            "Payment Received",
        ),
        (
            NOTIFICATION_TYPE_PAYMENT_FAILED,
            {"amount": 9.99, "currency": "USD", "reason": "provider declined"},
            "Payment Failed",
        ),
        (
            NOTIFICATION_TYPE_PROVISIONING_READY,
            {"plan_name": "Plus", "cabinet_url": "https://cyber-vpn.net/dashboard"},
            "VPN Access Ready",
        ),
        (
            NOTIFICATION_TYPE_PROVISIONING_FAILED,
            {"support_reference": "prov-123", "retry_hint": "retry queued"},
            "VPN Access Delayed",
        ),
    ],
)
def test_stage1_notifications_build_queue_models(notification_type: str, kwargs: dict, expected_text: str) -> None:
    scheduled_at = datetime(2026, 5, 4, 10, 0, tzinfo=UTC)

    notification = build_stage1_telegram_notification(
        telegram_id=777000111,
        notification_type=notification_type,
        username="sasha",
        scheduled_at=scheduled_at,
        **kwargs,
    )

    assert notification is not None
    assert notification.notification_type == notification_type
    assert expected_text in notification.message
    queue_model = notification.to_queue_model()
    assert queue_model.telegram_id == 777000111
    assert queue_model.notification_type == notification_type
    assert queue_model.status == STATUS_PENDING
    assert queue_model.scheduled_at == scheduled_at


def test_stage1_messages_escape_dynamic_html_values() -> None:
    notification = build_stage1_telegram_notification(
        telegram_id=777000111,
        notification_type=NOTIFICATION_TYPE_PROVISIONING_FAILED,
        username="<script>alert(1)</script>",
        support_reference='case-"42"',
        retry_hint="<retry>",
    )

    assert notification is not None
    assert "<script>" not in notification.message
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in notification.message
    assert "&lt;retry&gt;" in notification.message
    assert "case-&quot;42&quot;" in notification.message


def test_stage1_builder_rejects_invalid_required_fields() -> None:
    with pytest.raises(ValueError, match="telegram_id"):
        build_stage1_telegram_notification(
            telegram_id=0,
            notification_type=NOTIFICATION_TYPE_PROVISIONING_READY,
            username="sasha",
        )

    with pytest.raises(ValueError, match="payment_received"):
        build_stage1_telegram_notification(
            telegram_id=777000111,
            notification_type=NOTIFICATION_TYPE_PAYMENT_RECEIVED,
            username="sasha",
            amount=9.99,
            plan_name="Plus",
        )


@pytest.mark.asyncio
async def test_stage1_queued_notification_is_delivered_by_existing_processor(
    mock_settings,
    mock_db_session,
    mock_telegram,
) -> None:
    notification = build_stage1_telegram_notification(
        telegram_id=777000111,
        notification_type=NOTIFICATION_TYPE_PROVISIONING_READY,
        username="sasha",
        plan_name="Plus",
        cabinet_url="https://cyber-vpn.net/dashboard",
    )
    assert notification is not None
    queue_model = notification.to_queue_model()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [queue_model]
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_telegram.send_message.return_value = {"message_id": 999}

    with (
        patch("src.tasks.notifications.process_queue.get_settings", return_value=mock_settings),
        patch("src.tasks.notifications.process_queue.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.process_queue.TelegramClient") as mock_tg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

    assert result["sent"] == 1
    assert result["failed"] == 0
    assert queue_model.status == STATUS_SENT
    mock_telegram.send_message.assert_called_once_with(chat_id=777000111, text=queue_model.message)
