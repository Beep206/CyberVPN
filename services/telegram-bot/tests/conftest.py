"""Pytest configuration and fixtures for CyberVPN Telegram Bot tests.

This module provides comprehensive test fixtures for:
- Mock aiogram Bot and Dispatcher
- Fake Redis (fakeredis)
- Mock CyberVPN API client with respx
- Mock settings
- Factory fixtures for DTOs (user, subscription plans, etc.)
- Pre-loaded i18n translator
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import respx
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from fluent.runtime import FluentBundle, FluentResource
from pydantic import SecretStr

from src.config import (
    BackendSettings,
    BotSettings,
    CryptoBotSettings,
    LoggingSettings,
    PrometheusSettings,
    RedisSettings,
    ReferralSettings,
    TelegramStarsSettings,
    TrialSettings,
    WebhookSettings,
    YooKassaSettings,
)
from src.middlewares.i18n import FluentTranslator
from src.models.subscription import (
    PlanAvailability,
    PlanDuration,
    PlanType,
    ResetStrategy,
    SubscriptionPlan,
)
from src.models.user import UserDTO, UserStatus
from src.services.api_client import CyberVPNAPIClient

if TYPE_CHECKING:
    from pathlib import Path

# ── Pytest configuration ─────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio backend for pytest-asyncio."""
    return "asyncio"


# ── Mock Bot and Dispatcher ──────────────────────────────────────────────────


@pytest.fixture
def mock_bot() -> Bot:
    """Create a mocked aiogram Bot instance.

    The bot has all methods mocked with AsyncMock to prevent actual API calls.
    Useful for testing handlers and business logic without hitting Telegram API.

    Returns:
        Mocked Bot instance with token from test settings.
    """
    bot = MagicMock(spec=Bot)
    bot.token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    bot.session = MagicMock()

    # Mock common bot methods as AsyncMock
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_document = AsyncMock()
    bot.get_me = AsyncMock(return_value=MagicMock(id=123456789, username="test_bot", first_name="TestBot"))

    return bot


@pytest.fixture
def mock_dispatcher(mock_bot: Bot) -> Dispatcher:
    """Create a Dispatcher with MemoryStorage for testing.

    Args:
        mock_bot: Mocked Bot fixture.

    Returns:
        Dispatcher configured with MemoryStorage for FSM state testing.
    """
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)
    return dispatcher


@pytest.fixture
def fsm_storage() -> MemoryStorage:
    """Create a MemoryStorage instance for FSM testing.

    Returns:
        MemoryStorage instance.
    """
    return MemoryStorage()


def create_fsm_context(storage: MemoryStorage, bot_id: int, user_id: int, chat_id: int) -> FSMContext:
    """Helper to create FSMContext with proper StorageKey.

    Args:
        storage: MemoryStorage instance.
        bot_id: Bot ID.
        user_id: User ID.
        chat_id: Chat ID.

    Returns:
        FSMContext instance.
    """
    return FSMContext(
        storage=storage,
        key=StorageKey(bot_id=bot_id, user_id=user_id, chat_id=chat_id)
    )


# ── Fake Redis ───────────────────────────────────────────────────────────────


@pytest.fixture
async def fake_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Create a fakeredis instance for testing cache operations.

    Provides an in-memory Redis-compatible store that resets between tests.

    Yields:
        FakeRedis instance with aioredis compatibility.
    """
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


# ── Mock Settings ────────────────────────────────────────────────────────────


@pytest.fixture
def mock_settings() -> BotSettings:
    """Create BotSettings with test values.

    Returns:
        BotSettings configured for testing with safe defaults.
    """
    return BotSettings(
        bot_token=SecretStr("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"),
        bot_mode="polling",
        environment="development",
        admin_ids=[123456789, 987654321],
        support_username="TestSupport",
        default_language="ru",
        available_languages=["ru", "en"],
        webhook=WebhookSettings(
            url=None,
            path="/webhook/telegram",
            port=8080,
            secret_token=None,
        ),
        backend=BackendSettings(
            api_url="https://api.test.cybervpn.local",
            api_key=SecretStr("test_api_key_12345"),
            timeout=30,
            max_retries=3,
            retry_backoff=0.5,
        ),
        redis=RedisSettings(
            url="redis://localhost:6379",
            db=1,
            password=None,
            key_prefix="cybervpn:test:",
            ttl_seconds=3600,
        ),
        cryptobot=CryptoBotSettings(
            enabled=True,
            token=SecretStr("test_cryptobot_token"),
            network="testnet",
        ),
        yookassa=YooKassaSettings(
            enabled=False,
            shop_id=None,
            secret_key=None,
            test_mode=True,
        ),
        telegram_stars=TelegramStarsSettings(enabled=True),
        trial=TrialSettings(enabled=True, days=2, traffic_gb=2),
        referral=ReferralSettings(enabled=True, bonus_days=3, max_referrals=100),
        logging=LoggingSettings(level="DEBUG", json_format=False, show_locals=True),
        prometheus=PrometheusSettings(enabled=False, port=9090, path="/metrics"),
    )


# ── Mock API Client ──────────────────────────────────────────────────────────


class MockCyberVPNAPIClient:
    """Mock API client for testing that doesn't require respx.

    This provides all the methods needed by integration tests with
    AsyncMock implementations that return proper dict/list structures.
    """

    def __init__(self, settings: BackendSettings) -> None:
        self.settings = settings
        # User operations
        self.get_user = AsyncMock(return_value={})
        self.register_user = AsyncMock(return_value={})
        self.update_user_language = AsyncMock(return_value={})

        # Subscription operations
        self.get_user_config = AsyncMock(return_value={})
        self.get_available_plans = AsyncMock(return_value=[])
        self.create_subscription = AsyncMock(return_value={})

        # Payment operations
        self.create_crypto_invoice = AsyncMock(return_value={})
        self.create_yookassa_payment = AsyncMock(return_value={})
        self.create_stars_invoice = AsyncMock(return_value={})
        self.get_invoice_status = AsyncMock(return_value={})

        # Referral operations
        self.get_referral_stats = AsyncMock(return_value={})
        self.withdraw_referral_points = AsyncMock(return_value={})

        # Promocode operations
        self.activate_promocode = AsyncMock(return_value={})

        # Admin operations (real API)
        self.get_statistics = AsyncMock(return_value={})
        self.get_users = AsyncMock(return_value={})
        self.manage_user = AsyncMock(return_value={})
        self.get_admin_plans = AsyncMock(return_value=[])
        self.get_admin_promocodes = AsyncMock(return_value={})
        self.create_broadcast = AsyncMock(return_value={})
        self.get_access_settings = AsyncMock(return_value={})
        self.get_gateway_settings = AsyncMock(return_value={})
        self.get_remnawave_stats = AsyncMock(return_value={})

        # Admin operations (legacy/test-specific methods)
        self.get_admin_stats = AsyncMock(return_value={})
        self.get_admin_logs = AsyncMock(return_value={"logs": []})
        self.send_broadcast = AsyncMock(return_value={})
        self.get_broadcast_status = AsyncMock(return_value={})
        self.search_users = AsyncMock(return_value={})
        self.get_user_details = AsyncMock(return_value={})
        self.update_user = AsyncMock(return_value={})
        self.ban_user = AsyncMock(return_value={})
        self.unban_user = AsyncMock(return_value={})
        self.send_admin_message = AsyncMock(return_value={})

        # Payment operations (legacy/test-specific methods)
        self.create_payment = AsyncMock(return_value={})
        self.get_payment = AsyncMock(return_value={})
        self.verify_payment = AsyncMock(return_value={})
        self.process_webhook = AsyncMock(return_value={})
        self.get_subscription = AsyncMock(return_value={})

        # Health check
        self.health_check = AsyncMock(return_value=True)

    async def close(self) -> None:
        """Close client (no-op for mock)."""
        pass


@pytest.fixture
async def mock_api_client(
    mock_settings: BotSettings,
) -> AsyncGenerator[CyberVPNAPIClient, None]:
    """Create a real CyberVPNAPIClient for testing with respx.

    Args:
        mock_settings: Test settings fixture.

    Yields:
        CyberVPNAPIClient instance (use respx to mock HTTP responses).
    """
    client = CyberVPNAPIClient(settings=mock_settings.backend)
    yield client
    await client.close()


@pytest.fixture
async def mock_simple_api_client(
    mock_settings: BotSettings,
) -> AsyncGenerator[MockCyberVPNAPIClient, None]:
    """Create a MockCyberVPNAPIClient for integration tests.

    This fixture is useful for integration tests that need a simple
    mock without complex HTTP mocking via respx.

    Args:
        mock_settings: Test settings fixture.

    Yields:
        MockCyberVPNAPIClient instance with AsyncMock methods.
    """
    client = MockCyberVPNAPIClient(settings=mock_settings.backend)
    yield client
    await client.close()


# ── Factory Fixtures for DTOs ────────────────────────────────────────────────


@pytest.fixture
def sample_user() -> UserDTO:
    """Factory fixture for creating sample UserDTO instances.

    Returns:
        Callable that creates UserDTO with customizable parameters.
    """

    def _create_user(
        telegram_id: int = 123456789,
        username: str | None = "test_user",
        language: str = "ru",
        status: UserStatus = UserStatus.ACTIVE,
        is_admin: bool = False,
        **kwargs: Any,
    ) -> UserDTO:
        """Create a UserDTO instance with test defaults.

        Args:
            telegram_id: User's Telegram ID.
            username: Telegram username.
            language: Language preference.
            status: User status.
            is_admin: Admin flag.
            **kwargs: Additional UserDTO fields to override.

        Returns:
            UserDTO instance.
        """
        defaults: dict[str, Any] = {
            "uuid": "00000000-0000-0000-0000-000000000001",
            "telegram_id": telegram_id,
            "username": username,
            "first_name": "Test",
            "language": language,
            "status": status,
            "is_admin": is_admin,
            "personal_discount": 0.0,
            "next_purchase_discount": 0.0,
            "referrer_id": None,
            "points": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return UserDTO(**defaults)

    return _create_user


@pytest.fixture
def sample_plan() -> SubscriptionPlan:
    """Factory fixture for creating sample SubscriptionPlan instances.

    Returns:
        Callable that creates SubscriptionPlan with customizable parameters.
    """

    def _create_plan(
        plan_id: str = "basic_plan",
        name: str = "Basic VPN",
        plan_type: PlanType = PlanType.BOTH,
        availability: PlanAvailability = PlanAvailability.ALL,
        traffic_limit_gb: float | None = 10.0,
        device_limit: int | None = 3,
        **kwargs: Any,
    ) -> SubscriptionPlan:
        """Create a SubscriptionPlan instance with test defaults.

        Args:
            plan_id: Unique plan identifier.
            name: Plan display name.
            plan_type: Type of plan (traffic/devices/both/unlimited).
            availability: Plan availability setting.
            traffic_limit_gb: Traffic limit in GB.
            device_limit: Device limit.
            **kwargs: Additional SubscriptionPlan fields to override.

        Returns:
            SubscriptionPlan instance.
        """
        defaults: dict[str, Any] = {
            "id": plan_id,
            "name": name,
            "description": f"Test subscription plan: {name}",
            "tag": "TEST",
            "plan_type": plan_type,
            "availability": availability,
            "is_active": True,
            "traffic_limit_gb": traffic_limit_gb,
            "device_limit": device_limit,
            "reset_strategy": ResetStrategy.MONTH,
            "durations": [
                PlanDuration(
                    duration_days=30,
                    prices={"USD": 9.99, "EUR": 8.99, "RUB": 750.0},
                ),
                PlanDuration(
                    duration_days=90,
                    prices={"USD": 24.99, "EUR": 22.99, "RUB": 1990.0},
                ),
            ],
            "squads": ["default"],
        }
        defaults.update(kwargs)
        return SubscriptionPlan(**defaults)

    return _create_plan


# ── i18n Fixture ─────────────────────────────────────────────────────────────


@pytest.fixture
def i18n_fixture(tmp_path: Path) -> FluentTranslator:
    """Create a pre-loaded FluentTranslator for 'ru' locale.

    Creates minimal .ftl files in a temporary directory and loads them
    into a FluentBundle for testing localized message formatting.

    Args:
        tmp_path: pytest's temporary directory fixture.

    Returns:
        FluentTranslator instance with Russian locale loaded.
    """
    # Create temporary locales directory structure
    locales_dir = tmp_path / "locales"
    ru_dir = locales_dir / "ru"
    ru_dir.mkdir(parents=True)

    # Create minimal Russian .ftl file for testing
    ftl_content = """
# Test Fluent Translation File
welcome = Добро пожаловать, { $name }!
start-message = Привет! Выберите действие:
error-occurred = Произошла ошибка
subscription-active = Ваша подписка активна до { $date }
"""
    (ru_dir / "main.ftl").write_text(ftl_content, encoding="utf-8")

    # Load into FluentBundle using the correct API
    bundle = FluentBundle(["ru"])
    resource = FluentResource(ftl_content)
    bundle.add_resource(resource)

    # Monkey-patch the format method to use the correct API
    def format_method(key: str, args: dict[str, Any] | None = None) -> tuple[str, list[Any]]:
        """Format a message using the Fluent API."""
        args = args or {}
        msg = bundle.get_message(key)
        if msg and msg.value:
            return bundle.format_pattern(msg.value, args)
        return (key, [])

    bundle.format = format_method  # type: ignore[method-assign]

    # Return wrapped translator
    return FluentTranslator(bundle=bundle, fallback_bundle=None)


# ── Respx Global Mock for Backend API ───────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_respx_base_url() -> None:
    """Configure respx to mock the Backend API base URL globally.

    This fixture runs automatically for all tests and sets up
    the base URL for API mocking.
    """
    # Note: Individual tests should use the respx_mock fixture
    # to define specific endpoint behaviors
    pass


# ── Cleanup and Teardown ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
async def cleanup_between_tests() -> AsyncGenerator[None, None]:
    """Automatic cleanup between test runs.

    Ensures each test starts with a clean state.
    """
    # Setup (before test)
    yield
    # Teardown (after test)
    # Add any global cleanup logic here if needed
