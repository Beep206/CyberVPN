"""Unit tests for subscription tasks."""

import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "telegramId": 111,
            "expiresAt": (now + timedelta(days=1)).isoformat(),
        },
        {
            "uuid": "user-2",
            "username": "user2",
            "telegramId": 222,
            "expiresAt": (now + timedelta(days=3)).isoformat(),
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as MockCache,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.check_expiring.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.exists = AsyncMock(return_value=False)  # Not sent yet
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 2
        assert mock_telegram.send_message.call_count == 2


@pytest.mark.asyncio
async def test_check_expiring_skips_already_sent(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring check skips reminders already sent."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "telegramId": 111,
            "expiresAt": (now + timedelta(days=1)).isoformat(),
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as MockCache,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.check_expiring.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.exists = AsyncMock(return_value=True)  # Already sent
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 0
        mock_telegram.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_expiring_correct_bracket(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring check uses correct bracket based on days left."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "telegramId": 111,
            "expiresAt": (now + timedelta(days=7)).isoformat(),  # 7 day bracket
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as MockCache,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.check_expiring.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.exists = AsyncMock(return_value=False)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 1
        # Verify cache key includes bracket 7
        cache_set_calls = mock_cache.set.call_args_list
        assert ":7" in str(cache_set_calls[0][0][0])  # Cache key ends with bracket number


@pytest.mark.asyncio
async def test_check_expiring_skips_no_telegram_id(mock_redis, mock_remnawave, mock_telegram):
    """Test expiring check skips users without telegram_id."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "telegramId": None,  # No telegram ID
            "expiresAt": (now + timedelta(days=1)).isoformat(),
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.check_expiring.get_redis_client", return_value=mock_redis),
        patch("src.tasks.subscriptions.check_expiring.CacheService") as MockCache,
        patch("src.tasks.subscriptions.check_expiring.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.check_expiring.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_expiring_subscriptions()

        assert result["reminders_sent"] == 0


@pytest.mark.asyncio
async def test_disable_expired_disables_users(mock_remnawave, mock_telegram):
    """Test disable expired disables expired users."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "expiresAt": (now - timedelta(days=1)).isoformat(),  # Expired
            "telegramId": 111,
        },
        {
            "uuid": "user-2",
            "username": "user2",
            "status": "active",
            "expiresAt": (now + timedelta(days=10)).isoformat(),  # Not expired
            "telegramId": 222,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.disable_expired.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.disable_expired.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await disable_expired_users()

        assert result["disabled"] == 1
        mock_remnawave.disable_user.assert_called_once_with("user-1")
        mock_telegram.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_disable_expired_sends_notification(mock_remnawave, mock_telegram):
    """Test disable expired sends notification to user."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "active",
            "expiresAt": (now - timedelta(days=1)).isoformat(),
            "telegramId": 12345,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.disable_expired.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.disable_expired.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        await disable_expired_users()

        mock_telegram.send_message.assert_called_once_with(
            chat_id=12345, text=unittest.mock.ANY
        )


@pytest.mark.asyncio
async def test_disable_expired_skips_already_disabled(mock_remnawave, mock_telegram):
    """Test disable expired skips already disabled users."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "status": "disabled",  # Already disabled
            "expiresAt": (now - timedelta(days=1)).isoformat(),
            "telegramId": 111,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.disable_expired.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.disable_expired.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await disable_expired_users()

        assert result["disabled"] == 0
        mock_remnawave.disable_user.assert_not_called()


@pytest.mark.asyncio
async def test_reset_traffic_resets_active_users(mock_remnawave, mock_telegram):
    """Test traffic reset resets active users."""
    users = [
        {"uuid": "user-1", "username": "user1", "status": "active", "telegramId": 111, "planName": "Pro"},
        {"uuid": "user-2", "username": "user2", "status": "disabled", "telegramId": 222, "planName": "Basic"},
        {"uuid": "user-3", "username": "user3", "status": "active", "telegramId": 333, "planName": "Premium"},
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.reset_traffic.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.reset_traffic.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await reset_monthly_traffic()

        assert result["reset"] == 2  # Only active users
        assert mock_remnawave.reset_user_traffic.call_count == 2
        assert mock_telegram.send_message.call_count == 2


@pytest.mark.asyncio
async def test_reset_traffic_sends_notification(mock_remnawave, mock_telegram):
    """Test traffic reset sends notification to users."""
    users = [
        {"uuid": "user-1", "username": "user1", "status": "active", "telegramId": 12345, "planName": "Pro"},
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.reset_traffic.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.reset_traffic.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        await reset_monthly_traffic()

        mock_telegram.send_message.assert_called_once_with(chat_id=12345, text=unittest.mock.ANY)


@pytest.mark.asyncio
async def test_auto_renew_creates_invoices(mock_settings, mock_remnawave, mock_cryptobot, mock_telegram):
    """Test auto-renew creates invoices for eligible users."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "autoRenew": True,
            "expiresAt": (now + timedelta(minutes=30)).isoformat(),  # Within 1 hour
            "telegramId": 111,
            "subscriptionPlan": "Pro",
            "planPrice": 10.0,
            "planCurrency": "USD",
        },
    ]
    mock_remnawave.get_users.return_value = users
    mock_cryptobot.create_invoice.return_value = {
        "invoice_id": 123,
        "pay_url": "https://pay.test/123",
    }

    with (
        patch("src.tasks.subscriptions.auto_renew.get_settings", return_value=mock_settings),
        patch("src.tasks.subscriptions.auto_renew.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.auto_renew.CryptoBotClient") as MockCB,
        patch("src.tasks.subscriptions.auto_renew.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockCB.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        MockCB.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await auto_renew_subscriptions()

        assert result["invoices_created"] == 1
        mock_cryptobot.create_invoice.assert_called_once()
        mock_telegram.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_auto_renew_skips_ineligible_users(mock_settings, mock_remnawave, mock_cryptobot, mock_telegram):
    """Test auto-renew skips users without auto_renew or not expiring soon."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "autoRenew": False,  # Not enabled
            "expiresAt": (now + timedelta(minutes=30)).isoformat(),
            "telegramId": 111,
        },
        {
            "uuid": "user-2",
            "username": "user2",
            "autoRenew": True,
            "expiresAt": (now + timedelta(days=5)).isoformat(),  # Too far in future
            "telegramId": 222,
        },
    ]
    mock_remnawave.get_users.return_value = users

    with (
        patch("src.tasks.subscriptions.auto_renew.get_settings", return_value=mock_settings),
        patch("src.tasks.subscriptions.auto_renew.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.auto_renew.CryptoBotClient") as MockCB,
        patch("src.tasks.subscriptions.auto_renew.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockCB.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        MockCB.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await auto_renew_subscriptions()

        assert result["invoices_created"] == 0
        mock_cryptobot.create_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_auto_renew_sends_payment_link(mock_settings, mock_remnawave, mock_cryptobot, mock_telegram):
    """Test auto-renew sends payment link to user."""
    now = datetime.now(timezone.utc)
    users = [
        {
            "uuid": "user-1",
            "username": "user1",
            "autoRenew": True,
            "expiresAt": (now + timedelta(minutes=30)).isoformat(),
            "telegramId": 12345,
            "subscriptionPlan": "Pro",
            "planPrice": 15.0,
            "planCurrency": "USD",
        },
    ]
    mock_remnawave.get_users.return_value = users
    mock_cryptobot.create_invoice.return_value = {
        "invoice_id": 999,
        "pay_url": "https://pay.test/999",
    }

    with (
        patch("src.tasks.subscriptions.auto_renew.get_settings", return_value=mock_settings),
        patch("src.tasks.subscriptions.auto_renew.RemnawaveClient") as MockRW,
        patch("src.tasks.subscriptions.auto_renew.CryptoBotClient") as MockCB,
        patch("src.tasks.subscriptions.auto_renew.TelegramClient") as MockTg,
    ):
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockCB.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        MockCB.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        await auto_renew_subscriptions()

        # Verify payment link was sent
        call_args = mock_telegram.send_message.call_args
        assert call_args[1]["chat_id"] == 12345
        assert "https://pay.test/999" in call_args[1]["text"]


# Import unittest.mock for ANY matcher
import unittest.mock
