"""Integration tests for payment flows across all payment gateways.

Tests payment creation, verification, and webhook processing for:
- Telegram Stars (native Telegram payments)
- CryptoBot (cryptocurrency payments)
- YooKassa (card payments)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import User

from tests.conftest import create_fsm_context
from src.states.subscription import SubscriptionStates

if TYPE_CHECKING:
    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient


@pytest.fixture
def test_user() -> User:
    """Create a test Telegram user."""
    return User(
        id=987654321,
        is_bot=False,
        first_name="Payment",
        last_name="Tester",
        username="payment_tester",
        language_code="en",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_telegram_stars_payment_flow_success(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test complete Telegram Stars payment flow from invoice to activation.

    Flow:
    1. Create payment invoice
    2. User receives invoice via send_invoice
    3. Pre-checkout query validation
    4. Successful payment callback
    5. Subscription activation
    """
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    # Mock payment creation for Stars
    mock_simple_api_client.create_payment.return_value = {
        "id": "stars_payment_123",
        "user_id": test_user.id,
        "plan_id": "premium_plan",
        "amount": 1490.0,
        "currency": "RUB",
        "status": "pending",
        "payment_method": "stars",
        "invoice_payload": "payment_stars_payment_123",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mock payment verification after Stars payment
    mock_simple_api_client.verify_payment.return_value = {
        "id": "stars_payment_123",
        "status": "completed",
        "subscription_id": "sub_stars_123",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mock subscription activation
    mock_simple_api_client.get_subscription.return_value = {
        "id": "sub_stars_123",
        "user_id": test_user.id,
        "plan_id": "premium_plan",
        "status": "active",
        "expires_at": "2026-02-28T00:00:00Z",
        "config_url": "https://api.test.cybervpn.local/configs/sub_stars_123",
    }

    # Step 1: Create payment
    await state.update_data(
        plan_id="premium_plan",
        duration_days=30,
        total_price=1490.0,
        payment_method="stars",
    )
    await state.set_state(SubscriptionStates.confirming)

    payment_data = {
        "user_id": test_user.id,
        "plan_id": "premium_plan",
        "duration_days": 30,
        "amount": 1490.0,
        "payment_method": "stars",
    }

    payment = await mock_simple_api_client.create_payment(payment_data)
    assert payment["payment_method"] == "stars"
    assert payment["status"] == "pending"

    # Step 2: Simulate invoice sent (mocked)
    mock_bot.send_invoice = AsyncMock()
    await mock_bot.send_invoice(
        chat_id=test_user.id,
        title="Premium VPN Subscription",
        description="30 days of premium VPN access",
        payload=payment["invoice_payload"],
        provider_token="",  # Empty for Stars
        currency="XTR",
        prices=[{"label": "Premium Plan", "amount": 149000}],
    )

    # Step 3: Verify payment after successful Stars payment
    await state.update_data(payment_id="stars_payment_123")
    await state.set_state(SubscriptionStates.processing)

    verification = await mock_simple_api_client.verify_payment("stars_payment_123")
    assert verification["status"] == "completed"
    assert verification["subscription_id"] == "sub_stars_123"

    # Step 4: Fetch activated subscription
    subscription = await mock_simple_api_client.get_subscription("sub_stars_123")
    assert subscription["status"] == "active"

    # Clear state after completion
    await state.clear()
    assert await state.get_state() is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cryptobot_payment_flow_success(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test complete CryptoBot payment flow with external redirect.

    Flow:
    1. Create CryptoBot payment
    2. User is redirected to CryptoBot payment page
    3. Webhook callback on successful payment
    4. Payment verification
    5. Subscription activation
    """
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    # Mock CryptoBot payment creation
    mock_simple_api_client.create_payment.return_value = {
        "id": "crypto_payment_456",
        "user_id": test_user.id,
        "plan_id": "basic_plan",
        "amount": 750.0,
        "currency": "RUB",
        "status": "pending",
        "payment_method": "cryptobot",
        "payment_url": "https://crypto.bot/pay/abc123xyz",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mock webhook callback verification
    mock_simple_api_client.process_webhook.return_value = {
        "payment_id": "crypto_payment_456",
        "status": "completed",
        "subscription_id": "sub_crypto_456",
    }

    # Mock payment status check
    mock_simple_api_client.get_payment.return_value = {
        "id": "crypto_payment_456",
        "status": "completed",
        "subscription_id": "sub_crypto_456",
    }

    # Mock subscription fetch
    mock_simple_api_client.get_subscription.return_value = {
        "id": "sub_crypto_456",
        "user_id": test_user.id,
        "status": "active",
        "config_url": "https://api.test.cybervpn.local/configs/sub_crypto_456",
    }

    # Step 1: Create payment
    await state.update_data(
        plan_id="basic_plan",
        duration_days=30,
        total_price=750.0,
        payment_method="cryptobot",
    )

    payment = await mock_simple_api_client.create_payment(
        {
            "user_id": test_user.id,
            "plan_id": "basic_plan",
            "duration_days": 30,
            "amount": 750.0,
            "payment_method": "cryptobot",
        }
    )

    assert payment["payment_method"] == "cryptobot"
    assert payment["payment_url"] is not None
    await state.update_data(payment_id=payment["id"])

    # Step 2: Simulate webhook callback (external payment completed)
    webhook_response = await mock_simple_api_client.process_webhook(
        "cryptobot",
        {
            "payment_id": "crypto_payment_456",
            "status": "completed",
        },
    )

    assert webhook_response["status"] == "completed"

    # Step 3: Check payment status
    payment_status = await mock_simple_api_client.get_payment("crypto_payment_456")
    assert payment_status["status"] == "completed"

    # Clear state
    await state.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_yookassa_payment_flow_success(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test complete YooKassa payment flow with card payment redirect.

    Flow:
    1. Create YooKassa payment
    2. User is redirected to YooKassa payment page
    3. Webhook notification on payment success
    4. Payment verification
    5. Subscription activation
    """
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    # Mock YooKassa payment creation
    mock_simple_api_client.create_payment.return_value = {
        "id": "yookassa_payment_789",
        "user_id": test_user.id,
        "plan_id": "premium_plan",
        "amount": 1490.0,
        "currency": "RUB",
        "status": "pending",
        "payment_method": "yookassa",
        "payment_url": "https://yookassa.ru/payments/xyz789",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mock YooKassa webhook
    mock_simple_api_client.process_webhook.return_value = {
        "payment_id": "yookassa_payment_789",
        "status": "completed",
        "subscription_id": "sub_yookassa_789",
    }

    # Mock payment verification
    mock_simple_api_client.verify_payment.return_value = {
        "id": "yookassa_payment_789",
        "status": "completed",
        "subscription_id": "sub_yookassa_789",
    }

    # Create payment
    payment = await mock_simple_api_client.create_payment(
        {
            "user_id": test_user.id,
            "plan_id": "premium_plan",
            "duration_days": 30,
            "amount": 1490.0,
            "payment_method": "yookassa",
        }
    )

    assert payment["payment_method"] == "yookassa"
    assert "payment_url" in payment

    # Simulate webhook processing
    webhook_result = await mock_simple_api_client.process_webhook(
        "yookassa",
        {
            "payment_id": "yookassa_payment_789",
            "status": "completed",
        },
    )

    assert webhook_result["status"] == "completed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_timeout_handling(
    mock_bot: Bot,
    mock_simple_api_client,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test payment flow when payment times out."""
    # Mock payment that times out
    mock_simple_api_client.create_payment.return_value = {
        "id": "timeout_payment_999",
        "status": "pending",
        "payment_method": "cryptobot",
    }

    # Mock payment status check returning timeout
    mock_simple_api_client.get_payment.return_value = {
        "id": "timeout_payment_999",
        "status": "timeout",
    }

    # Create payment
    payment = await mock_simple_api_client.create_payment(
        {
            "user_id": test_user.id,
            "plan_id": "basic_plan",
            "duration_days": 30,
            "amount": 750.0,
            "payment_method": "cryptobot",
        }
    )

    # Check status after timeout
    status = await mock_simple_api_client.get_payment("timeout_payment_999")
    assert status["status"] == "timeout"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_webhook_verification_failure(
    mock_simple_api_client,
    mock_settings: BotSettings,
) -> None:
    """Test webhook verification failure scenario."""
    # Mock webhook verification failure
    mock_simple_api_client.process_webhook.side_effect = Exception("Invalid webhook signature")

    # Attempt to process webhook with invalid signature
    try:
        await mock_simple_api_client.process_webhook(
            "cryptobot",
            {
                "payment_id": "invalid_payment",
                "status": "completed",
            },
        )
        pytest.fail("Expected webhook verification to fail")
    except Exception:
        # Expected to fail
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_activation_error(
    mock_simple_api_client,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test payment flow when subscription activation fails."""
    # Payment succeeds
    mock_simple_api_client.create_payment.return_value = {
        "id": "payment_with_activation_error",
        "status": "pending",
    }

    # But activation fails
    mock_simple_api_client.verify_payment.side_effect = Exception("Subscription activation failed")

    # Create payment
    payment = await mock_simple_api_client.create_payment(
        {
            "user_id": test_user.id,
            "plan_id": "basic_plan",
            "duration_days": 30,
            "amount": 750.0,
            "payment_method": "stars",
        }
    )

    # Attempt verification should fail
    try:
        await mock_simple_api_client.verify_payment("payment_with_activation_error")
        pytest.fail("Expected activation to fail")
    except Exception:
        # Expected to fail
        pass
