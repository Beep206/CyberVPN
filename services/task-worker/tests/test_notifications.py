"""Unit tests for notification tasks."""

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Set required environment variables before importing modules
os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.services.telegram_client import TelegramAPIError
from src.tasks.notifications.broadcast import broadcast_message
from src.tasks.notifications.process_queue import process_notification_queue
from src.tasks.notifications.send_notification import send_notification


@pytest.mark.asyncio
async def test_send_notification_success(mock_telegram):
    """Test successful notification send."""
    mock_telegram.send_message.return_value = {"message_id": 12345, "status": "sent"}

    with patch("src.tasks.notifications.send_notification.TelegramClient") as mock_tg:
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await send_notification(chat_id=123456, text="Test message")

        assert result["message_id"] == 12345
        assert result["status"] == "sent"
        mock_telegram.send_message.assert_called_once_with(chat_id=123456, text="Test message", parse_mode="HTML")


@pytest.mark.asyncio
async def test_send_notification_telegram_failure(mock_telegram):
    """Test notification send handles Telegram API failure."""
    mock_telegram.send_message.side_effect = TelegramAPIError("API error")

    with patch("src.tasks.notifications.send_notification.TelegramClient") as mock_tg:
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(TelegramAPIError):
            await send_notification(chat_id=123456, text="Test message")


@pytest.mark.asyncio
async def test_send_notification_custom_parse_mode(mock_telegram):
    """Test notification with custom parse mode."""
    mock_telegram.send_message.return_value = {"message_id": 789}

    with patch("src.tasks.notifications.send_notification.TelegramClient") as mock_tg:
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        await send_notification(chat_id=999, text="*Bold*", parse_mode="Markdown")

        mock_telegram.send_message.assert_called_once_with(chat_id=999, text="*Bold*", parse_mode="Markdown")


@pytest.mark.asyncio
async def test_process_queue_empty(mock_settings, mock_db_session, mock_telegram):
    """Test processing empty notification queue."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch("src.tasks.notifications.process_queue.get_settings", return_value=mock_settings),
        patch("src.tasks.notifications.process_queue.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.process_queue.TelegramClient") as mock_tg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

        assert result["sent"] == 0
        assert result["failed"] == 0
        assert "No pending notifications" in result["message"]


@pytest.mark.asyncio
async def test_process_queue_processes_batch(mock_settings, mock_db_session, mock_telegram):
    """Test processing batch of notifications successfully."""
    # Create mock notifications
    notif1 = MagicMock()
    notif1.id = uuid4()
    notif1.telegram_id = 123
    notif1.message = "Message 1"
    notif1.attempts = 0
    notif1.status = "pending"

    notif2 = MagicMock()
    notif2.id = uuid4()
    notif2.telegram_id = 456
    notif2.message = "Message 2"
    notif2.attempts = 0
    notif2.status = "pending"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif1, notif2]
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

        assert result["sent"] == 2
        assert result["failed"] == 0
        assert notif1.status == "sent"
        assert notif2.status == "sent"
        assert notif1.sent_at is not None
        assert notif2.sent_at is not None


@pytest.mark.asyncio
async def test_process_queue_auto_renew_rejects_reassigned_recipient(
    mock_settings,
    mock_db_session,
    mock_telegram,
) -> None:
    """A stale queued payment link is never sent after Telegram reassignment."""

    customer_id = uuid4()
    notification = MagicMock()
    notification.id = uuid4()
    notification.telegram_id = 123
    notification.message = "Sensitive payment link"
    notification.notification_type = f"auto_renew:{customer_id}"
    notification.attempts = 0
    notification.status = "pending"

    queue_result = MagicMock()
    queue_result.scalars.return_value.all.return_value = [notification]
    current_recipient_result = MagicMock()
    current_recipient_result.mappings.return_value.one_or_none.return_value = {
        "telegram_id": 456,
        "is_active": True,
    }
    mock_db_session.execute = AsyncMock(side_effect=[queue_result, MagicMock(), current_recipient_result])

    with (
        patch("src.tasks.notifications.process_queue.get_settings", return_value=mock_settings),
        patch("src.tasks.notifications.process_queue.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.process_queue.TelegramClient") as mock_tg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

    assert result == {"sent": 0, "failed": 1}
    assert notification.status == "failed"
    assert notification.error_message == "canonical_recipient_mismatch"
    assert notification.attempts == mock_settings.notification_max_retries
    mock_telegram.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_queue_rejects_legacy_unbound_auto_renew_notification(
    mock_settings,
    mock_db_session,
    mock_telegram,
) -> None:
    """Pre-upgrade auto-renew rows cannot bypass canonical recipient binding."""

    notification = MagicMock()
    notification.id = uuid4()
    notification.telegram_id = 123
    notification.message = "Sensitive payment link"
    notification.notification_type = "subscription:auto_renew_invoice"
    notification.attempts = 0
    notification.status = "pending"

    queue_result = MagicMock()
    queue_result.scalars.return_value.all.return_value = [notification]
    mock_db_session.execute = AsyncMock(side_effect=[queue_result, MagicMock()])

    with (
        patch("src.tasks.notifications.process_queue.get_settings", return_value=mock_settings),
        patch("src.tasks.notifications.process_queue.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.process_queue.TelegramClient") as mock_tg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

    assert result == {"sent": 0, "failed": 1}
    assert notification.error_message == "canonical_recipient_mismatch"
    mock_telegram.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_queue_auto_renew_sends_only_to_current_canonical_recipient(
    mock_settings,
    mock_db_session,
    mock_telegram,
) -> None:
    """The payment link is sent only while the local subject binding matches."""

    customer_id = uuid4()
    notification = MagicMock()
    notification.id = uuid4()
    notification.telegram_id = 123
    notification.message = "Sensitive payment link"
    notification.notification_type = f"auto_renew:{customer_id}"
    notification.attempts = 0
    notification.status = "pending"

    queue_result = MagicMock()
    queue_result.scalars.return_value.all.return_value = [notification]
    current_recipient_result = MagicMock()
    current_recipient_result.mappings.return_value.one_or_none.return_value = {
        "telegram_id": 123,
        "is_active": True,
    }
    delivery_result = MagicMock()
    delivery_result.scalars.return_value.first.return_value = None
    mock_db_session.execute = AsyncMock(
        side_effect=[queue_result, MagicMock(), current_recipient_result, delivery_result, MagicMock()]
    )

    with (
        patch("src.tasks.notifications.process_queue.get_settings", return_value=mock_settings),
        patch("src.tasks.notifications.process_queue.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.process_queue.TelegramClient") as mock_tg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

    assert result == {"sent": 1, "failed": 0}
    mock_telegram.send_message.assert_awaited_once_with(
        chat_id=123,
        text="Sensitive payment link",
    )


@pytest.mark.asyncio
async def test_process_queue_syncs_growth_delivery_status(mock_settings, mock_db_session, mock_telegram):
    """Telegram delivery processor should update canonical growth delivery status."""
    notif = MagicMock()
    notif.id = uuid4()
    notif.telegram_id = 123
    notif.message = "Growth message"
    notif.attempts = 0
    notif.status = "pending"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif]
    executed_statements = []

    async def _execute(statement, *args, **kwargs):
        executed_statements.append(str(statement))
        return mock_result

    mock_db_session.execute = AsyncMock(side_effect=_execute)
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
        assert any("customer_growth_notification_deliveries" in stmt for stmt in executed_statements)
        assert any("delivery_status" in stmt for stmt in executed_statements)


@pytest.mark.asyncio
async def test_process_queue_handles_individual_failures(mock_settings, mock_db_session, mock_telegram):
    """Test processing batch with some failures."""
    notif1 = MagicMock()
    notif1.id = uuid4()
    notif1.telegram_id = 123
    notif1.message = "Message 1"
    notif1.attempts = 0
    notif1.status = "pending"

    notif2 = MagicMock()
    notif2.id = uuid4()
    notif2.telegram_id = 456
    notif2.message = "Message 2"
    notif2.attempts = 0
    notif2.status = "pending"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif1, notif2]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # First call succeeds, second fails
    mock_telegram.send_message.side_effect = [
        {"message_id": 999},
        TelegramAPIError("User blocked bot"),
    ]

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
        assert result["failed"] == 1
        assert notif1.status == "sent"
        assert notif2.status == "pending"  # Retryable
        assert notif2.attempts == 1


@pytest.mark.asyncio
async def test_process_queue_max_retries_reached(mock_settings, mock_db_session, mock_telegram):
    """Test notification marked as failed after max retries."""
    notif = MagicMock()
    notif.id = uuid4()
    notif.telegram_id = 123
    notif.message = "Message"
    notif.attempts = 4  # One away from max (5)
    notif.status = "pending"

    mock_settings.notification_max_retries = 5

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif]
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_telegram.send_message.side_effect = TelegramAPIError("Failed")

    with (
        patch("src.tasks.notifications.process_queue.get_settings", return_value=mock_settings),
        patch("src.tasks.notifications.process_queue.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.process_queue.TelegramClient") as mock_tg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

        assert result["failed"] == 1
        assert notif.status == "failed"  # Permanently failed
        assert notif.attempts == 5
        assert notif.error_message == "telegram_delivery_failed"
        alert_text = mock_telegram.send_admin_alert.await_args.args[0]
        assert "Telegram ID:" not in alert_text
        assert "Error:" not in alert_text


@pytest.mark.asyncio
async def test_broadcast_queues_notifications(mock_db_session, mock_redis):
    """Test broadcast queues notifications via DB and tracks progress."""
    telegram_ids = [111, 222, 333]
    mock_db_session.add_all = MagicMock()

    with (
        patch("src.tasks.notifications.broadcast.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.broadcast.get_redis_client") as mock_redis_fn,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_redis_fn.return_value = mock_redis

        result = await broadcast_message(telegram_ids=telegram_ids, text="Broadcast test")

        assert result["queued"] == 3
        assert result["job_id"]
        mock_db_session.add_all.assert_called()
        mock_db_session.commit.assert_called()
        mock_redis.set.assert_called()


@pytest.mark.asyncio
async def test_broadcast_empty_list(mock_db_session, mock_redis):
    """Test broadcast handles empty recipient list."""
    with (
        patch("src.tasks.notifications.broadcast.get_session_factory") as mock_factory,
        patch("src.tasks.notifications.broadcast.get_redis_client") as mock_redis_fn,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_redis_fn.return_value = mock_redis

        result = await broadcast_message(telegram_ids=[], text="Test")

        assert result["queued"] == 0
