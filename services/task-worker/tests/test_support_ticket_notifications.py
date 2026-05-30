"""Tests for support ticket Telegram notifications."""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.tasks.notifications.support_ticket_contract import (
    SUPPORT_TICKET_IDEMPOTENCY_TTL_SECONDS,
    SUPPORT_TICKET_NOTIFICATION_EVENT_TYPES,
    build_support_ticket_telegram_notification,
)
from src.tasks.notifications.support_tickets import queue_support_ticket_notification
from src.utils.constants import NOTIFICATION_TYPE_SUPPORT_TICKET_UPDATE, STATUS_PENDING


def test_support_ticket_notification_contract_allows_public_update_events_only() -> None:
    assert SUPPORT_TICKET_NOTIFICATION_EVENT_TYPES == frozenset(
        {
            "public_reply_added",
            "status_changed",
            "closed",
            "reopened",
        }
    )

    with pytest.raises(ValueError, match="Unsupported support ticket notification event type"):
        build_support_ticket_telegram_notification(
            telegram_id=777000111,
            ticket_event_id="evt_internal_note",
            ticket_public_id="sup_123",
            event_type="internal_note_added",
            status="pending_customer",
            category="billing",
        )


def test_support_ticket_notification_builds_queue_model_without_body_preview() -> None:
    scheduled_at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)

    notification = build_support_ticket_telegram_notification(
        telegram_id=777000111,
        ticket_event_id="evt_admin_reply_1",
        ticket_public_id="sup_abc123",
        event_type="public_reply_added",
        status="pending_customer",
        category="billing",
        support_url="https://cyber-vpn.net/en-EN/miniapp/support",
        scheduled_at=scheduled_at,
    )

    assert notification is not None
    assert notification.idempotency_key == "cybervpn:support-ticket-notification:evt_admin_reply_1"
    assert "Support replied to your ticket" in notification.message
    assert "sup_abc123" in notification.message
    assert "pending_customer" in notification.message
    assert "internal" not in notification.message.lower()
    assert "latest public conversation" in notification.message

    queue_model = notification.to_queue_model()
    assert queue_model.telegram_id == 777000111
    assert queue_model.notification_type == NOTIFICATION_TYPE_SUPPORT_TICKET_UPDATE
    assert queue_model.status == STATUS_PENDING
    assert queue_model.scheduled_at == scheduled_at


def test_support_ticket_notification_is_not_queued_without_linked_telegram() -> None:
    assert (
        build_support_ticket_telegram_notification(
            telegram_id=None,
            ticket_event_id="evt_admin_reply_1",
            ticket_public_id="sup_abc123",
            event_type="public_reply_added",
            status="pending_customer",
            category="billing",
        )
        is None
    )


@pytest.mark.asyncio
async def test_queue_support_ticket_notification_persists_once(mock_db_session, mock_redis) -> None:
    mock_factory = MagicMock(return_value=mock_db_session)

    with (
        patch("src.tasks.notifications.support_tickets.get_session_factory", return_value=mock_factory),
        patch("src.tasks.notifications.support_tickets.get_redis_client", return_value=mock_redis),
    ):
        result = await queue_support_ticket_notification(
            telegram_id=777000111,
            ticket_event_id="evt_admin_reply_1",
            ticket_public_id="sup_abc123",
            event_type="public_reply_added",
            status="pending_customer",
            category="billing",
            support_url="https://cyber-vpn.net/en-EN/miniapp/support",
        )

    assert result["queued"] == 1
    assert result["skipped"] is False
    mock_redis.set.assert_awaited_once_with(
        "cybervpn:support-ticket-notification:evt_admin_reply_1",
        "1",
        nx=True,
        ex=SUPPORT_TICKET_IDEMPOTENCY_TTL_SECONDS,
    )
    mock_db_session.add.assert_called_once()
    queued_model = mock_db_session.add.call_args.args[0]
    assert queued_model.notification_type == NOTIFICATION_TYPE_SUPPORT_TICKET_UPDATE
    assert queued_model.telegram_id == 777000111
    assert "latest public conversation" in queued_model.message
    mock_db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_queue_support_ticket_notification_skips_duplicate_event(mock_db_session, mock_redis) -> None:
    mock_redis.set.return_value = False

    with (
        patch("src.tasks.notifications.support_tickets.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.support_tickets.get_redis_client", return_value=mock_redis),
    ):
        result = await queue_support_ticket_notification(
            telegram_id=777000111,
            ticket_event_id="evt_admin_reply_1",
            ticket_public_id="sup_abc123",
            event_type="public_reply_added",
            status="pending_customer",
            category="billing",
        )

    assert result == {"queued": 0, "skipped": True, "reason": "idempotent_duplicate"}
    mock_factory.assert_not_called()
    mock_db_session.add.assert_not_called()
