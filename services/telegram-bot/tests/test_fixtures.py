"""Test that all conftest.py fixtures are working correctly.

This test file verifies that all pytest fixtures defined in conftest.py
can be imported, instantiated, and used properly.
"""

from __future__ import annotations

from datetime import datetime

import pytest
import respx
from aiogram import Bot, Dispatcher
from pydantic import SecretStr

from src.config import BotSettings
from src.middlewares.i18n import FluentTranslator
from src.models.subscription import PlanType, SubscriptionPlan
from src.models.user import UserDTO, UserStatus
from src.services.api_client import CyberVPNAPIClient


class TestMockBot:
    """Test the mock_bot fixture."""

    def test_mock_bot_fixture(self, mock_bot: Bot) -> None:
        """Verify mock_bot fixture provides a properly mocked Bot."""
        assert mock_bot is not None
        assert hasattr(mock_bot, "token")
        assert mock_bot.token == "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        assert hasattr(mock_bot, "send_message")
        assert hasattr(mock_bot, "edit_message_text")


class TestMockDispatcher:
    """Test the mock_dispatcher fixture."""

    def test_mock_dispatcher_fixture(self, mock_dispatcher: Dispatcher) -> None:
        """Verify mock_dispatcher provides a Dispatcher with MemoryStorage."""
        assert mock_dispatcher is not None
        assert hasattr(mock_dispatcher, "storage")
        assert mock_dispatcher.storage is not None


class TestFakeRedis:
    """Test the fake_redis fixture."""

    async def test_fake_redis_fixture(self, fake_redis) -> None:
        """Verify fake_redis provides a working Redis-like interface."""
        # Test basic set/get operations
        await fake_redis.set("test_key", "test_value")
        value = await fake_redis.get("test_key")
        assert value == "test_value"

        # Test deletion
        await fake_redis.delete("test_key")
        value = await fake_redis.get("test_key")
        assert value is None

    async def test_fake_redis_json_operations(self, fake_redis) -> None:
        """Verify fake_redis can handle JSON operations."""
        import orjson

        test_data = {"name": "test", "count": 42}
        await fake_redis.set("json_key", orjson.dumps(test_data))

        raw = await fake_redis.get("json_key")
        assert raw is not None
        parsed = orjson.loads(raw)
        assert parsed == test_data


class TestMockSettings:
    """Test the mock_settings fixture."""

    def test_mock_settings_fixture(self, mock_settings: BotSettings) -> None:
        """Verify mock_settings provides valid test configuration."""
        assert mock_settings is not None
        assert mock_settings.environment == "development"
        assert mock_settings.bot_mode == "polling"
        assert 123456789 in mock_settings.admin_ids

        # Check backend settings (AnyHttpUrl adds trailing slash)
        assert str(mock_settings.backend.api_url).rstrip("/") == "https://api.test.cybervpn.local"
        assert isinstance(mock_settings.backend.api_key, SecretStr)

        # Check payment gateways
        assert mock_settings.cryptobot.enabled is True
        assert mock_settings.telegram_stars.enabled is True


class TestMockAPIClient:
    """Test the mock_api_client fixture."""

    @pytest.mark.respx(base_url="https://api.test.cybervpn.local")
    async def test_mock_api_client_fixture(
        self,
        mock_api_client: CyberVPNAPIClient,
        respx_mock,
    ) -> None:
        """Verify mock_api_client provides a working API client."""
        assert mock_api_client is not None

        # Mock health check endpoint
        respx_mock.get("/health").mock(return_value=respx.MockResponse(200, json={"status": "ok"}))

        # Test health check
        is_healthy = await mock_api_client.health_check()
        assert is_healthy is True

    @pytest.mark.respx(base_url="https://api.test.cybervpn.local")
    async def test_mock_api_client_custom_endpoint(
        self,
        mock_api_client: CyberVPNAPIClient,
        respx_mock,
    ) -> None:
        """Verify we can add custom endpoint mocks."""
        # Setup custom endpoint mock
        respx_mock.get("/telegram/users/123").mock(
            return_value=respx.MockResponse(
                200,
                json={
                    "uuid": "test-uuid",
                    "telegram_id": 123,
                    "username": "test_user",
                    "language": "en",
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            ),
        )

        # Call the mocked endpoint
        result = await mock_api_client.get_user(123)
        assert result["telegram_id"] == 123
        assert result["username"] == "test_user"


class TestSampleUserFactory:
    """Test the sample_user factory fixture."""

    def test_sample_user_default(self, sample_user) -> None:
        """Verify sample_user factory creates valid UserDTO with defaults."""
        user = sample_user()

        assert isinstance(user, UserDTO)
        assert user.telegram_id == 123456789
        assert user.username == "test_user"
        assert user.language == "ru"
        assert user.status == UserStatus.ACTIVE
        assert user.is_admin is False

    def test_sample_user_custom(self, sample_user) -> None:
        """Verify sample_user factory accepts custom parameters."""
        user = sample_user(
            telegram_id=999,
            username="custom_user",
            language="en",
            status=UserStatus.EXPIRED,
            is_admin=True,
            points=100,
        )

        assert user.telegram_id == 999
        assert user.username == "custom_user"
        assert user.language == "en"
        assert user.status == UserStatus.EXPIRED
        assert user.is_admin is True
        assert user.points == 100


class TestSamplePlanFactory:
    """Test the sample_plan factory fixture."""

    def test_sample_plan_default(self, sample_plan) -> None:
        """Verify sample_plan factory creates valid SubscriptionPlan with defaults."""
        plan = sample_plan()

        assert isinstance(plan, SubscriptionPlan)
        assert plan.id == "basic_plan"
        assert plan.name == "Basic VPN"
        assert plan.plan_type == PlanType.BOTH
        assert plan.traffic_limit_gb == 10.0
        assert plan.device_limit == 3
        assert len(plan.durations) == 2

    def test_sample_plan_custom(self, sample_plan) -> None:
        """Verify sample_plan factory accepts custom parameters."""
        plan = sample_plan(
            plan_id="premium_plan",
            name="Premium VPN",
            plan_type=PlanType.UNLIMITED,
            traffic_limit_gb=None,
            device_limit=None,
        )

        assert plan.id == "premium_plan"
        assert plan.name == "Premium VPN"
        assert plan.plan_type == PlanType.UNLIMITED
        assert plan.traffic_limit_gb is None
        assert plan.device_limit is None


class TestI18nFixture:
    """Test the i18n_fixture."""

    def test_i18n_fixture_translation(self, i18n_fixture: FluentTranslator) -> None:
        """Verify i18n_fixture provides working translator."""
        # Test basic translation
        result = i18n_fixture("welcome", name="Alice")
        assert "Alice" in result
        assert "Добро пожаловать" in result

    def test_i18n_fixture_missing_key(self, i18n_fixture: FluentTranslator) -> None:
        """Verify i18n_fixture returns key name for missing translations."""
        result = i18n_fixture("non_existent_key")
        assert result == "non_existent_key"

    def test_i18n_fixture_no_variables(self, i18n_fixture: FluentTranslator) -> None:
        """Verify i18n_fixture works without variables."""
        result = i18n_fixture("start-message")
        assert "Привет" in result


class TestFixtureIntegration:
    """Test integration between multiple fixtures."""

    @pytest.mark.respx(base_url="https://api.test.cybervpn.local")
    async def test_settings_with_api_client(
        self,
        mock_settings: BotSettings,
        mock_api_client: CyberVPNAPIClient,
        respx_mock,
    ) -> None:
        """Verify settings and API client work together."""
        # Settings should be used by API client (AnyHttpUrl adds trailing slash)
        assert str(mock_settings.backend.api_url).rstrip("/") == "https://api.test.cybervpn.local"

        # Mock health check endpoint
        respx_mock.get("/health").mock(return_value=respx.MockResponse(200, json={"status": "ok"}))

        # API client should be functional
        assert await mock_api_client.health_check()

    async def test_user_and_plan_factories(
        self,
        sample_user,
        sample_plan,
    ) -> None:
        """Verify user and plan factories can be used together."""
        user = sample_user()
        plan = sample_plan()

        assert isinstance(user, UserDTO)
        assert isinstance(plan, SubscriptionPlan)

        # Simulate a subscription scenario
        assert user.telegram_id > 0
        assert plan.id is not None
