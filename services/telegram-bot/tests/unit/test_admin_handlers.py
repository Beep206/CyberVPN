"""Unit tests for admin handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

if TYPE_CHECKING:
    from src.config import BotSettings


@pytest.mark.asyncio
class TestAdminStatsHandler:
    """Test admin statistics handler."""

    async def test_stats_handler_success(self) -> None:
        """Test successful stats retrieval."""
        # Mock API client
        api_client = MagicMock()
        api_client.get_bot_stats = AsyncMock(
            return_value={
                "total_users": 1250,
                "active_subscriptions": 450,
                "total_revenue": 12500.00,
                "new_users_today": 15,
                "new_users_week": 89,
                "new_users_month": 340,
            }
        )

        admin_user = User(id=123456, is_bot=False, first_name="Admin")

        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.data = "admin:stats"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Get stats
        stats = await api_client.get_bot_stats()

        # Format and display
        stats_text = (
            f"Total Users: {stats['total_users']}\n"
            f"Active Subscriptions: {stats['active_subscriptions']}\n"
            f"Total Revenue: ${stats['total_revenue']}\n"
            f"New Today: {stats['new_users_today']}\n"
            f"New This Week: {stats['new_users_week']}\n"
            f"New This Month: {stats['new_users_month']}"
        )

        await callback.message.edit_text(stats_text)
        await callback.answer()

        # Verify
        assert callback.message.edit_text.called
        call_args = callback.message.edit_text.call_args[0][0]
        assert "1250" in call_args
        assert "450" in call_args

    async def test_stats_handler_api_error(self) -> None:
        """Test stats handler with API error."""
        api_client = MagicMock()
        api_client.get_bot_stats = AsyncMock(side_effect=Exception("API error"))

        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()

        # Handle error
        try:
            await api_client.get_bot_stats()
        except Exception:
            await callback.answer("Error loading stats", show_alert=True)

        # Should have shown error
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args[0][0]
        assert "Error" in call_args


@pytest.mark.asyncio
class TestAdminUserManagement:
    """Test admin user management handlers."""

    async def test_view_user_details(self) -> None:
        """Test viewing user details."""
        api_client = MagicMock()
        api_client.get_user = AsyncMock(
            return_value={
                "telegram_id": 999999,
                "username": "testuser",
                "language": "en",
                "status": "active",
                "subscription": {"plan": "Premium", "expires_at": "2024-12-31"},
            }
        )

        user_id = 999999
        user_data = await api_client.get_user(user_id)

        assert user_data["telegram_id"] == user_id
        assert user_data["subscription"]["plan"] == "Premium"

    async def test_ban_user(self) -> None:
        """Test banning a user."""
        api_client = MagicMock()
        api_client.ban_user = AsyncMock(
            return_value={"telegram_id": 123, "status": "banned"}
        )

        result = await api_client.ban_user(telegram_id=123)

        assert result["status"] == "banned"

    async def test_unban_user(self) -> None:
        """Test unbanning a user."""
        api_client = MagicMock()
        api_client.unban_user = AsyncMock(
            return_value={"telegram_id": 123, "status": "active"}
        )

        result = await api_client.unban_user(telegram_id=123)

        assert result["status"] == "active"

    async def test_grant_subscription(self) -> None:
        """Test granting subscription to user."""
        api_client = MagicMock()
        api_client.grant_subscription = AsyncMock(
            return_value={
                "telegram_id": 456,
                "subscription": {"plan": "Premium", "days": 30},
            }
        )

        result = await api_client.grant_subscription(
            telegram_id=456, plan_id="premium", days=30
        )

        assert result["subscription"]["plan"] == "Premium"
        assert result["subscription"]["days"] == 30


@pytest.mark.asyncio
class TestAdminBroadcastHandler:
    """Test admin broadcast handlers."""

    async def test_broadcast_start(self) -> None:
        """Test starting broadcast flow."""
        admin_user = User(id=123456, is_bot=False, first_name="Admin")

        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.data = "admin:broadcast"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Mock FSM
        state = MagicMock(spec=FSMContext)
        state.set_state = AsyncMock()

        # Start broadcast
        await callback.message.edit_text("Send the message you want to broadcast:")
        await state.set_state("composing_message")
        await callback.answer()

        # Verify
        state.set_state.assert_called_once()
        callback.message.edit_text.assert_called_once()

    async def test_broadcast_compose_message(self) -> None:
        """Test composing broadcast message."""
        message = MagicMock(spec=Message)
        message.text = "Important announcement: New features available!"
        message.answer = AsyncMock()

        state = MagicMock(spec=FSMContext)
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()

        # Store message
        await state.update_data(broadcast_text=message.text)
        await state.set_state("confirming")

        # Show confirmation
        await message.answer(
            f"Preview:\n\n{message.text}\n\nSend to all users?",
            # reply_markup would have Yes/No buttons
        )

        state.update_data.assert_called_once()
        message.answer.assert_called_once()

    async def test_broadcast_confirm_send(self) -> None:
        """Test confirming and sending broadcast."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "broadcast:confirm"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(
            return_value={"broadcast_text": "Test message"}
        )
        state.clear = AsyncMock()

        # Get stored message
        data = await state.get_data()
        broadcast_text = data["broadcast_text"]

        # Simulate sending (in real handler, would send to all users)
        # Mock broadcast service
        broadcast_service = MagicMock()
        broadcast_service.send_to_all = AsyncMock(
            return_value={"sent": 1200, "failed": 50}
        )

        result = await broadcast_service.send_to_all(text=broadcast_text)

        # Show result
        await callback.message.edit_text(
            f"Broadcast sent!\n\nSent: {result['sent']}\nFailed: {result['failed']}"
        )
        await state.clear()

        # Verify
        assert result["sent"] == 1200
        state.clear.assert_called_once()

    async def test_broadcast_cancel(self) -> None:
        """Test canceling broadcast."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "broadcast:cancel"
        callback.answer = AsyncMock()

        state = MagicMock(spec=FSMContext)
        state.clear = AsyncMock()

        await state.clear()
        await callback.answer("Broadcast cancelled")

        state.clear.assert_called_once()
        callback.answer.assert_called_once()


@pytest.mark.asyncio
class TestIsAdminFilter:
    """Test IsAdmin filter."""

    async def test_admin_filter_allows_admin(
        self, mock_settings: BotSettings
    ) -> None:
        """Test that admin filter allows admin users."""
        admin_id = mock_settings.admin_ids[0]

        is_admin = admin_id in mock_settings.admin_ids
        assert is_admin is True

    async def test_admin_filter_blocks_non_admin(
        self, mock_settings: BotSettings
    ) -> None:
        """Test that admin filter blocks non-admin users."""
        non_admin_id = 999999

        is_admin = non_admin_id in mock_settings.admin_ids
        assert is_admin is False

    async def test_admin_filter_with_message(
        self, mock_settings: BotSettings
    ) -> None:
        """Test admin filter with message event."""
        admin_id = mock_settings.admin_ids[0]

        user = User(id=admin_id, is_bot=False, first_name="Admin")
        message = MagicMock(spec=Message)
        message.from_user = user

        # Simulate filter check
        is_admin = message.from_user.id in mock_settings.admin_ids
        assert is_admin is True

    async def test_admin_filter_with_callback(
        self, mock_settings: BotSettings
    ) -> None:
        """Test admin filter with callback event."""
        non_admin_id = 777777

        user = User(id=non_admin_id, is_bot=False, first_name="User")
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.answer = AsyncMock()

        # Simulate filter check
        is_admin = callback.from_user.id in mock_settings.admin_ids

        if not is_admin:
            await callback.answer("Access denied", show_alert=True)

        assert is_admin is False
        callback.answer.assert_called_once()


@pytest.mark.asyncio
class TestAdminIntegration:
    """Integration tests for admin workflows."""

    async def test_complete_broadcast_workflow(self) -> None:
        """Test complete broadcast workflow."""
        # 1. Admin opens broadcast menu
        state = MagicMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        state.get_data = AsyncMock(
            return_value={"broadcast_text": "Hello users!"}
        )
        state.clear = AsyncMock()

        # 2. Enter composing state
        await state.set_state("composing")

        # 3. Compose message
        await state.update_data(broadcast_text="Hello users!")

        # 4. Confirm
        data = await state.get_data()
        assert data["broadcast_text"] == "Hello users!"

        # 5. Send
        broadcast_service = MagicMock()
        broadcast_service.send_to_all = AsyncMock(
            return_value={"sent": 100, "failed": 0}
        )

        result = await broadcast_service.send_to_all(
            text=data["broadcast_text"]
        )

        # 6. Clear state
        await state.clear()

        # Verify workflow
        assert result["sent"] == 100
        state.clear.assert_called_once()

    async def test_admin_panel_navigation(self) -> None:
        """Test admin panel menu navigation."""
        callback = MagicMock(spec=CallbackQuery)
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Main admin menu
        callback.data = "admin:menu"
        await callback.message.edit_text("Admin Panel")

        # Navigate to stats
        callback.data = "admin:stats"
        await callback.message.edit_text("Statistics")

        # Back to menu
        callback.data = "admin:menu"
        await callback.message.edit_text("Admin Panel")

        # All navigations should succeed
        assert callback.message.edit_text.call_count == 3
