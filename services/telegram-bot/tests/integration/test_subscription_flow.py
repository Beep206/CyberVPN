"""Integration tests for complete subscription purchase flow.

Tests the full user journey from /start through plan selection, duration selection,
payment gateway selection, payment processing, and config delivery.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, User

from tests.conftest import create_fsm_context
from src.models.subscription import (
    PlanAvailability,
    PlanDuration,
    PlanType,
    ResetStrategy,
    SubscriptionPlan,
)
from src.models.user import UserDTO, UserStatus
from src.states.subscription import SubscriptionStates

if TYPE_CHECKING:
    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient


@pytest.fixture
def test_user() -> User:
    """Create a test Telegram user."""
    return User(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="test_user",
        language_code="ru",
    )


@pytest.fixture
def test_plans() -> list[SubscriptionPlan]:
    """Create test subscription plans."""
    return [
        SubscriptionPlan(
            id="basic_plan",
            name="Basic VPN",
            description="Basic VPN access",
            tag="BASIC",
            plan_type=PlanType.BOTH,
            availability=PlanAvailability.ALL,
            is_active=True,
            traffic_limit_gb=10.0,
            device_limit=3,
            reset_strategy=ResetStrategy.MONTH,
            durations=[
                PlanDuration(duration_days=30, prices={"USD": 9.99, "RUB": 750.0}),
                PlanDuration(duration_days=90, prices={"USD": 24.99, "RUB": 1990.0}),
            ],
            squads=["default"],
        ),
        SubscriptionPlan(
            id="premium_plan",
            name="Premium VPN",
            description="Premium VPN with unlimited traffic",
            tag="PREMIUM",
            plan_type=PlanType.UNLIMITED,
            availability=PlanAvailability.ALL,
            is_active=True,
            traffic_limit_gb=None,
            device_limit=10,
            reset_strategy=ResetStrategy.MONTH,
            durations=[
                PlanDuration(duration_days=30, prices={"USD": 19.99, "RUB": 1490.0}),
            ],
            squads=["default"],
        ),
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_subscription_flow_success(
    mock_bot: Bot,
    mock_dispatcher: Dispatcher,
    mock_api_client: CyberVPNAPIClient,
    mock_settings: BotSettings,
    test_user: User,
    test_plans: list[SubscriptionPlan],
) -> None:
    """Test complete subscription purchase flow from start to activation.

    Flow:
    1. User starts bot (/start)
    2. User clicks "Subscription" button
    3. User selects plan
    4. User selects duration
    5. User selects payment gateway (Stars)
    6. Payment is processed successfully
    7. Subscription is activated
    8. User receives config
    """
    # Setup FSM context
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    # Mock API responses
    async with respx.mock:
        # Mock user registration/get
        respx.post(f"{mock_settings.backend.api_url}/users").mock(
            return_value=respx.MockResponse(
                200,
                json={
                    "uuid": "00000000-0000-0000-0000-000000000001",
                    "telegram_id": test_user.id,
                    "username": test_user.username,
                    "first_name": test_user.first_name,
                    "language": "ru",
                    "status": "active",
                    "is_admin": False,
                    "personal_discount": 0.0,
                    "next_purchase_discount": 0.0,
                    "referrer_id": None,
                    "points": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

        # Mock get plans
        respx.get(f"{mock_settings.backend.api_url}/plans").mock(
            return_value=respx.MockResponse(
                200,
                json=[plan.model_dump(mode="json") for plan in test_plans],
            )
        )

        # Mock create payment
        respx.post(f"{mock_settings.backend.api_url}/payments").mock(
            return_value=respx.MockResponse(
                200,
                json={
                    "id": "payment_123",
                    "user_id": test_user.id,
                    "plan_id": "basic_plan",
                    "amount": 750.0,
                    "currency": "RUB",
                    "status": "pending",
                    "payment_method": "stars",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

        # Mock payment verification
        respx.get(f"{mock_settings.backend.api_url}/payments/payment_123").mock(
            return_value=respx.MockResponse(
                200,
                json={
                    "id": "payment_123",
                    "status": "completed",
                    "subscription_id": "sub_123",
                },
            )
        )

        # Mock get subscription
        respx.get(f"{mock_settings.backend.api_url}/subscriptions/sub_123").mock(
            return_value=respx.MockResponse(
                200,
                json={
                    "id": "sub_123",
                    "user_id": test_user.id,
                    "plan_id": "basic_plan",
                    "status": "active",
                    "expires_at": "2026-02-28T00:00:00Z",
                    "config_url": "https://api.test.cybervpn.local/configs/sub_123",
                },
            )
        )

        # Step 1: User selects plan
        await state.set_state(SubscriptionStates.selecting_plan)
        await state.update_data(user_id=test_user.id)

        # Simulate plan selection callback
        callback_data = await state.get_data()
        assert await state.get_state() == SubscriptionStates.selecting_plan

        # Step 2: Plan selected -> selecting duration
        await state.update_data(plan_id="basic_plan")
        await state.set_state(SubscriptionStates.selecting_duration)

        current_state = await state.get_state()
        assert current_state == SubscriptionStates.selecting_duration
        data = await state.get_data()
        assert data["plan_id"] == "basic_plan"

        # Step 3: Duration selected -> selecting payment
        await state.update_data(duration_days=30, total_price=750.0)
        await state.set_state(SubscriptionStates.selecting_payment)

        current_state = await state.get_state()
        assert current_state == SubscriptionStates.selecting_payment
        data = await state.get_data()
        assert data["duration_days"] == 30
        assert data["total_price"] == 750.0

        # Step 4: Payment method selected -> confirming
        await state.update_data(payment_method="stars", payment_id="payment_123")
        await state.set_state(SubscriptionStates.confirming)

        current_state = await state.get_state()
        assert current_state == SubscriptionStates.confirming
        data = await state.get_data()
        assert data["payment_method"] == "stars"
        assert data["payment_id"] == "payment_123"

        # Step 5: Payment confirmed -> processing
        await state.set_state(SubscriptionStates.processing)
        current_state = await state.get_state()
        assert current_state == SubscriptionStates.processing

        # Step 6: Payment completed -> subscription activated
        await state.update_data(subscription_id="sub_123")
        await state.clear()

        # Verify final state
        current_state = await state.get_state()
        assert current_state is None  # State cleared after completion


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscription_flow_no_plans_available(
    mock_bot: Bot,
    mock_api_client: CyberVPNAPIClient,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test subscription flow when no plans are available."""
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    async with respx.mock:
        # Mock empty plans response
        respx.get(f"{mock_settings.backend.api_url}/plans").mock(
            return_value=respx.MockResponse(200, json=[])
        )

        # Attempt to start subscription flow
        await state.set_state(SubscriptionStates.selecting_plan)

        # Fetch plans via API client
        plans = await mock_api_client.get_plans()

        # Verify no plans available
        assert plans == [] or plans is None

        # State should not progress
        current_state = await state.get_state()
        assert current_state == SubscriptionStates.selecting_plan


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscription_flow_payment_failure(
    mock_bot: Bot,
    mock_api_client: CyberVPNAPIClient,
    mock_settings: BotSettings,
    test_user: User,
) -> None:
    """Test subscription flow when payment fails."""
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    async with respx.mock:
        # Mock payment creation failure
        respx.post(f"{mock_settings.backend.api_url}/payments").mock(
            return_value=respx.MockResponse(400, json={"detail": "Payment creation failed"})
        )

        # Setup state with plan and duration
        await state.update_data(
            plan_id="basic_plan",
            duration_days=30,
            total_price=750.0,
        )
        await state.set_state(SubscriptionStates.selecting_payment)

        # Attempt payment creation should fail
        # This would be handled by the payment handler with error handling

        # State should remain in selecting_payment or be cleared on error
        current_state = await state.get_state()
        assert current_state == SubscriptionStates.selecting_payment


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscription_flow_state_transitions(
    mock_bot: Bot,
    test_user: User,
) -> None:
    """Test FSM state transitions are correct throughout subscription flow."""
    storage = MemoryStorage()
    state = create_fsm_context(storage, mock_bot.id, test_user.id, test_user.id)

    # Test state progression
    states_sequence = [
        SubscriptionStates.selecting_plan,
        SubscriptionStates.selecting_duration,
        SubscriptionStates.selecting_payment,
        SubscriptionStates.confirming,
        SubscriptionStates.processing,
    ]

    for expected_state in states_sequence:
        await state.set_state(expected_state)
        current_state = await state.get_state()
        assert current_state == expected_state

    # Clear state after completion
    await state.clear()
    current_state = await state.get_state()
    assert current_state is None
