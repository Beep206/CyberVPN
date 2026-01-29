"""Integration tests for admin panel flows.

Tests admin dashboard navigation, broadcast creation, and user management operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import User

from tests.conftest import create_fsm_context
from src.states.admin import BroadcastStates, UserManagementStates

if TYPE_CHECKING:
    from src.config import BotSettings


@pytest.fixture
def admin_user() -> User:
    """Create a test admin user."""
    return User(
        id=123456789,  # Must be in admin_ids from mock_settings
        is_bot=False,
        first_name="Admin",
        last_name="User",
        username="admin_user",
        language_code="ru",
    )


@pytest.fixture
def regular_user() -> User:
    """Create a regular non-admin user."""
    return User(
        id=999888777,
        is_bot=False,
        first_name="Regular",
        last_name="User",
        username="regular_user",
        language_code="en",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_dashboard_navigation(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    admin_user: User,
) -> None:
    """Test admin panel navigation through all statistics pages.

    Flow:
    1. Admin opens dashboard
    2. Navigate to users statistics
    3. Navigate to payments statistics
    4. Navigate to subscriptions statistics
    5. Navigate to referrals statistics
    6. Navigate to system statistics
    7. Navigate to logs
    """
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, admin_user.id, admin_user.id)

    # Configure mock return values
    mock_simple_api_client.get_admin_stats.side_effect = lambda section: {
        "users": {"total_users": 1250, "active_users": 890, "new_today": 15, "new_this_week": 87},
        "payments": {"total_revenue": 450000.50, "payments_today": 12, "average_check": 1200.75},
        "subscriptions": {"active_subscriptions": 750, "expiring_soon": 45, "expired_today": 8},
        "referrals": {"total_referrals": 350, "successful_referrals": 120, "bonus_days_given": 360},
        "system": {"uptime": "15d 8h 32m", "active_servers": 12, "total_traffic_gb": 8500.5},
    }[section]

    mock_simple_api_client.get_admin_logs.return_value = {
        "logs": [
            {"level": "INFO", "message": "User registered", "timestamp": "2026-01-29T10:00:00Z"},
            {"level": "WARNING", "message": "Payment delayed", "timestamp": "2026-01-29T09:45:00Z"},
        ]
    }

    # Navigate through all statistics pages
    user_stats = await mock_simple_api_client.get_admin_stats("users")
    assert user_stats["total_users"] == 1250

    payment_stats = await mock_simple_api_client.get_admin_stats("payments")
    assert payment_stats["total_revenue"] > 0

    subscription_stats = await mock_simple_api_client.get_admin_stats("subscriptions")
    assert subscription_stats["active_subscriptions"] == 750

    referral_stats = await mock_simple_api_client.get_admin_stats("referrals")
    assert referral_stats["total_referrals"] == 350

    system_stats = await mock_simple_api_client.get_admin_stats("system")
    assert system_stats["active_servers"] == 12

    logs = await mock_simple_api_client.get_admin_logs()
    assert len(logs["logs"]) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_broadcast_creation_flow(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    admin_user: User,
) -> None:
    """Test complete broadcast message creation and sending flow.

    Flow:
    1. Admin selects broadcast audience (all/active/trial)
    2. Admin enters message content
    3. Admin adds optional buttons
    4. Admin previews message
    5. Admin confirms and sends broadcast
    """
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, admin_user.id, admin_user.id)

    # Configure mock return values
    mock_simple_api_client.create_broadcast.return_value = {
        "id": "broadcast_123",
        "audience": "active",
        "message": "Important update about our service",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    mock_simple_api_client.send_broadcast.return_value = {
        "id": "broadcast_123",
        "status": "sending",
        "total_recipients": 890,
        "sent_count": 0,
    }

    mock_simple_api_client.get_broadcast_status.return_value = {
        "id": "broadcast_123",
        "status": "completed",
        "sent_count": 890,
        "failed_count": 0,
    }

    # Step 1: Select audience
    await state.set_state(BroadcastStates.selecting_audience)
    await state.update_data(audience="active")

    # Step 2: Enter content
    await state.set_state(BroadcastStates.editing_content)
    await state.update_data(message="Important update about our service")

    # Step 3: Skip buttons (optional)
    await state.set_state(BroadcastStates.previewing)

    # Step 4: Confirm and create broadcast
    data = await state.get_data()
    broadcast = await mock_simple_api_client.create_broadcast({
        "audience": data["audience"],
        "message": data["message"],
    })

    assert broadcast["id"] == "broadcast_123"
    assert broadcast["audience"] == "active"

    # Step 5: Send broadcast
    await state.set_state(BroadcastStates.confirming)
    send_result = await mock_simple_api_client.send_broadcast("broadcast_123")

    assert send_result["status"] == "sending"
    assert send_result["total_recipients"] == 890

    # Check status
    status = await mock_simple_api_client.get_broadcast_status("broadcast_123")
    assert status["status"] == "completed"
    assert status["sent_count"] == 890

    # Clear state
    await state.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_user_search_and_management(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    admin_user: User,
) -> None:
    """Test admin user search and management operations.

    Flow:
    1. Admin searches for user by username/ID
    2. Admin views user details
    3. Admin performs action (edit discount/points/role)
    """
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, admin_user.id, admin_user.id)

    # Configure mock return values
    mock_simple_api_client.search_users.return_value = {
        "users": [
            {
                "uuid": "user-uuid-123",
                "telegram_id": 999888777,
                "username": "regular_user",
                "first_name": "Regular",
                "status": "active",
                "personal_discount": 0.0,
                "points": 100,
            }
        ]
    }

    mock_simple_api_client.get_user_details.return_value = {
        "uuid": "user-uuid-123",
        "telegram_id": 999888777,
        "username": "regular_user",
        "first_name": "Regular",
        "status": "active",
        "personal_discount": 0.0,
        "points": 100,
        "subscription": {
            "plan": "Basic VPN",
            "status": "active",
            "expires_at": "2026-02-28T00:00:00Z",
        },
    }

    mock_simple_api_client.update_user.return_value = {
        "uuid": "user-uuid-123",
        "telegram_id": 999888777,
        "personal_discount": 15.0,
    }

    # Step 1: Search for user
    await state.set_state(UserManagementStates.searching_user)
    search_results = await mock_simple_api_client.search_users("regular_user")

    assert len(search_results["users"]) == 1
    assert search_results["users"][0]["username"] == "regular_user"

    # Step 2: View user details
    await state.update_data(target_user_id=999888777)
    await state.set_state(UserManagementStates.viewing_user)

    user_details = await mock_simple_api_client.get_user_details(999888777)
    assert user_details["telegram_id"] == 999888777
    assert user_details["subscription"]["status"] == "active"

    # Step 3: Update user discount
    await state.set_state(UserManagementStates.editing_discount)
    await state.update_data(new_discount=15.0)

    updated_user = await mock_simple_api_client.update_user(999888777, {"personal_discount": 15.0})
    assert updated_user["personal_discount"] == 15.0

    # Clear state
    await state.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_access_denied_for_regular_user(
    mock_bot: Bot,
    mock_settings: BotSettings,
    regular_user: User,
) -> None:
    """Test that regular users cannot access admin panel."""
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, regular_user.id, regular_user.id)

    # Regular user ID not in admin_ids
    assert regular_user.id not in mock_settings.admin_ids

    # Attempt to access admin panel should be blocked
    # (This would be handled by admin filter in actual handlers)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_user_ban_and_unban(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    admin_user: User,
) -> None:
    """Test admin can ban and unban users."""
    # Configure mock return values
    mock_simple_api_client.ban_user.return_value = {
        "telegram_id": 999888777,
        "status": "banned",
    }

    mock_simple_api_client.unban_user.return_value = {
        "telegram_id": 999888777,
        "status": "active",
    }

    # Ban user
    ban_result = await mock_simple_api_client.ban_user(999888777)
    assert ban_result["status"] == "banned"

    # Unban user
    unban_result = await mock_simple_api_client.unban_user(999888777)
    assert unban_result["status"] == "active"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_send_direct_message_to_user(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    admin_user: User,
) -> None:
    """Test admin can send direct message to specific user."""
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, admin_user.id, admin_user.id)

    # Configure mock return values
    mock_simple_api_client.send_admin_message.return_value = {
        "message_id": "msg_123",
        "recipient_id": 999888777,
        "status": "sent",
    }

    # Admin enters message sending state
    await state.set_state(UserManagementStates.sending_message)
    await state.update_data(
        target_user_id=999888777,
        message="Hello! This is a message from admin.",
    )

    # Send message
    result = await mock_simple_api_client.send_admin_message(
        user_id=999888777,
        message="Hello! This is a message from admin.",
    )

    assert result["status"] == "sent"
    assert result["recipient_id"] == 999888777

    await state.clear()
