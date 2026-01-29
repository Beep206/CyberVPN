"""Unit tests for notification tasks."""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Set required environment variables before importing modules
os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.tasks.notifications.send_notification import send_notification
from src.tasks.notifications.process_queue import process_notification_queue
from src.tasks.notifications.broadcast import broadcast_message


@pytest.mark.asyncio
async def test_send_notification_success(mock_telegram):
    """Test successful notification send."""
    mock_telegram.send_message.return_value = {"message_id": 12345, "status": "sent"}

    with patch("src.tasks.notifications.send_notification.TelegramClient") as MockTg:
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await send_notification(chat_id=123456, text="Test message")

        assert result["message_id"] == 12345
        assert result["status"] == "sent"
        mock_telegram.send_message.assert_called_once_with(chat_id=123456, text="Test message", parse_mode="HTML")


@pytest.mark.asyncio
async def test_send_notification_telegram_failure(mock_telegram):
    """Test notification send handles Telegram API failure."""
    mock_telegram.send_message.side_effect = TelegramAPIError("API error")

    with patch("src.tasks.notifications.send_notification.TelegramClient") as MockTg:
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(TelegramAPIError):
            await send_notification(chat_id=123456, text="Test message")


@pytest.mark.asyncio
async def test_send_notification_custom_parse_mode(mock_telegram):
    """Test notification with custom parse mode."""
    mock_telegram.send_message.return_value = {"message_id": 789}

    with patch("src.tasks.notifications.send_notification.TelegramClient") as MockTg:
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

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
        patch("src.tasks.notifications.process_queue.TelegramClient") as MockTg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

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
        patch("src.tasks.notifications.process_queue.TelegramClient") as MockTg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

        assert result["sent"] == 2
        assert result["failed"] == 0
        assert notif1.status == "sent"
        assert notif2.status == "sent"
        assert notif1.sent_at is not None
        assert notif2.sent_at is not None


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
        patch("src.tasks.notifications.process_queue.TelegramClient") as MockTg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

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
        patch("src.tasks.notifications.process_queue.TelegramClient") as MockTg,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_notification_queue()

        assert result["failed"] == 1
        assert notif.status == "failed"  # Permanently failed
        assert notif.attempts == 5


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
