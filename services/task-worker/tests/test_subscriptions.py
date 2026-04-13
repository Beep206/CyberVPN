"""Unit tests for subscription tasks."""

from datetime import UTC, datetime, timedelta
import os
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

# Set required environment variables before importing modules
os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.tasks.subscriptions.check_expiring import check_expiring_subscriptions
from src.tasks.subscriptions.disable_expired import disable_expired_users
from src.tasks.subscriptions.reset_traffic import reset_monthly_traffic
from src.tasks.subscriptions.auto_renew import auto_renew_subscriptions


@pytest.mark.asyncio
async def test_check_expiring_sends_reminders(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring subscriptions sends reminders at correct brackets."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "telegram_id": 111,
            "expire_at": (now + timedelta(days=1)).isoformat(),
        },
        {
            "uuid": "user-2",
            "username": "user2",
            "status": "active",
            "telegram_id": 222,
            "expire_at": (now + timedelta(days=3)).isoformat(),
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as mock_cache_cls,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.check_expiring.get_session_factory") as mock_session_factory,
    ):
        mock_cache = MagicMock()
        mock_cache.exists = AsyncMock(return_value=False)  # Not sent yet
        mock_cache.set = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 2
        mock_session.add_all.assert_called_once()


@pytest.mark.asyncio
async def test_check_expiring_skips_already_sent(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring check skips reminders already sent."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "telegram_id": 111,
            "expire_at": (now + timedelta(days=1)).isoformat(),
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as mock_cache_cls,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.check_expiring.get_session_factory") as mock_session_factory,
    ):
        mock_cache = MagicMock()
        mock_cache.exists = AsyncMock(return_value=True)  # Already sent
        mock_cache.set = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 0
        mock_session.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_check_expiring_correct_bracket(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring check uses correct bracket based on days left."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "telegram_id": 111,
            "expire_at": (now + timedelta(days=7)).isoformat(),  # 7 day bracket
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as mock_cache_cls,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.check_expiring.get_session_factory") as mock_session_factory,
    ):
        mock_cache = MagicMock()
        mock_cache.exists = AsyncMock(return_value=False)
        mock_cache.set = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 1
        # Verify cache key includes bracket 7
        cache_set_calls = mock_cache.set.call_args_list
        assert ":7" in str(cache_set_calls[0][0][0])  # Cache key ends with bracket number


@pytest.mark.asyncio
async def test_check_expiring_skips_no_telegram_id(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring check skips users without telegram_id."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "telegram_id": None,  # No telegram ID
            "expire_at": (now + timedelta(days=1)).isoformat(),
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as mock_cache_cls,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.check_expiring.get_session_factory") as mock_session_factory,
    ):
        mock_cache = MagicMock()
        mock_cache_cls.return_value = mock_cache

        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 0


@pytest.mark.asyncio
async def test_disable_expired_disables_users(mock_remnawave, mock_telegram):
    """Test disable expired disables expired users."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "expire_at": (now - timedelta(days=1)).isoformat(),  # Expired
            "telegram_id": 111,
        },
        {
            "uuid": "user-2",
            "username": "user2",
            "status": "active",
            "expire_at": (now + timedelta(days=10)).isoformat(),  # Not expired
            "telegram_id": 222,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.disable_expired.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.disable_expired.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await disable_expired_users()

        assert result["disabled"] == 1
        mock_remnawave.disable_user.assert_called_once_with("user-1")
        mock_telegram.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_disable_expired_sends_notification(mock_remnawave, mock_telegram):
    """Test disable expired sends notification to user."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "expire_at": (now - timedelta(days=1)).isoformat(),
            "telegram_id": 12345,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.disable_expired.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.disable_expired.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await disable_expired_users()

        mock_telegram.send_message.assert_called_once_with(chat_id=12345, text=ANY)


@pytest.mark.asyncio
async def test_disable_expired_skips_already_disabled(mock_remnawave, mock_telegram):
    """Test disable expired skips already disabled users."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "disabled",  # Already disabled
            "expire_at": (now - timedelta(days=1)).isoformat(),
            "telegram_id": 111,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.disable_expired.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.disable_expired.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await disable_expired_users()

        assert result["disabled"] == 0
        mock_remnawave.disable_user.assert_not_called()


@pytest.mark.asyncio
async def test_reset_traffic_resets_active_users(mock_remnawave, mock_telegram):
    """Test traffic reset resets active users."""
    users = [
        {"uuid": "user-1", "username": "user1", "status": "active", "telegram_id": 111, "plan_name": "Pro"},
        {"uuid": "user-2", "username": "user2", "status": "disabled", "telegram_id": 222, "plan_name": "Basic"},
        {"uuid": "user-3", "username": "user3", "status": "active", "telegram_id": 333, "plan_name": "Premium"},
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.reset_traffic.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.reset_traffic.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await reset_monthly_traffic()

        assert result["reset"] == 2  # Only active users
        assert mock_remnawave.reset_user_traffic.call_count == 2
        assert mock_telegram.send_message.call_count == 2


@pytest.mark.asyncio
async def test_reset_traffic_sends_notification(mock_remnawave, mock_telegram):
    """Test traffic reset sends notification to users."""
    users = [
        {"uuid": "user-1", "username": "user1", "status": "active", "telegram_id": 12345, "plan_name": "Pro"},
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.reset_traffic.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.reset_traffic.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await reset_monthly_traffic()

        mock_telegram.send_message.assert_called_once_with(chat_id=12345, text=ANY)


@pytest.mark.asyncio
async def test_auto_renew_creates_invoices(mock_settings, mock_remnawave, mock_cryptobot, mock_telegram):
    """Test auto-renew creates invoices for eligible users."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "auto_renew": True,
            "expire_at": (now + timedelta(minutes=30)).isoformat(),  # Within 1 hour
            "telegram_id": 111,
            "plan_name": "Pro",
            "plan_price": 10.0,
            "plan_currency": "USD",
        },
    ]
    mock_remnawave.get_users.return_value = users
    mock_cryptobot.create_invoice.return_value = {
        "invoice_id": 123,
        "pay_url": "https://pay.test/123",
    }

    with (
        patch("src.tasks.subscriptions.auto_renew.get_settings", return_value=mock_settings),
        patch("src.tasks.subscriptions.auto_renew.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.auto_renew.CryptoBotClient") as mock_cb_cls,
        patch("src.tasks.subscriptions.auto_renew.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_cb_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await auto_renew_subscriptions()

        assert result["invoices_created"] == 1
        mock_cryptobot.create_invoice.assert_called_once()
        mock_telegram.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_auto_renew_skips_ineligible_users(mock_settings, mock_remnawave, mock_cryptobot, mock_telegram):
    """Test auto-renew skips users without auto_renew or not expiring soon."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "auto_renew": False,  # Not enabled
            "expire_at": (now + timedelta(minutes=30)).isoformat(),
            "telegram_id": 111,
        },
        {
            "uuid": "user-2",
            "username": "user2",
            "auto_renew": True,
            "expire_at": (now + timedelta(days=5)).isoformat(),  # Too far in future
            "telegram_id": 222,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.auto_renew.get_settings", return_value=mock_settings),
        patch("src.tasks.subscriptions.auto_renew.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.auto_renew.CryptoBotClient") as mock_cb_cls,
        patch("src.tasks.subscriptions.auto_renew.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_cb_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await auto_renew_subscriptions()

        assert result["invoices_created"] == 0
        mock_cryptobot.create_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_auto_renew_sends_payment_link(mock_settings, mock_remnawave, mock_cryptobot, mock_telegram):
    """Test auto-renew sends payment link to user."""
    now = datetime.now(UTC)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "auto_renew": True,
            "expire_at": (now + timedelta(minutes=30)).isoformat(),
            "telegram_id": 12345,
            "plan_name": "Pro",
            "plan_price": 15.0,
            "plan_currency": "USD",
        },
    ]
    mock_remnawave.get_users.return_value = users
    mock_cryptobot.create_invoice.return_value = {
        "invoice_id": 999,
        "pay_url": "https://pay.test/999",
    }

    with (
        patch("src.tasks.subscriptions.auto_renew.get_settings", return_value=mock_settings),
        patch("src.tasks.subscriptions.auto_renew.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.subscriptions.auto_renew.CryptoBotClient") as mock_cb_cls,
        patch("src.tasks.subscriptions.auto_renew.TelegramClient") as mock_tg_cls,
    ):
        mock_rw_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_cb_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg_cls.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await auto_renew_subscriptions()

        # Verify payment link was sent
        call_args = mock_telegram.send_message.call_args
        assert call_args[1]["chat_id"] == 12345
        assert "https://pay.test/999" in call_args[1]["text"]
