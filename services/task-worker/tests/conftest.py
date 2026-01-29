"""Pytest fixtures for task-worker tests.

Provides mock fixtures for:
- Settings configuration
- Redis client
- Database session
- External API clients (Remnawave, Telegram, CryptoBot)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest.fixture(scope="session", autouse=True)
def mock_settings_for_imports():
    """Mock settings at import time to prevent validation errors."""
    settings = MagicMock()

    # Database Configuration
    settings.database_url = "sqlite+aiosqlite:///:memory:"

    # Cache Configuration
    settings.redis_url = "redis://localhost:6379/0"

    # External Services
    settings.remnawave_url = "http://localhost:3000"
    settings.remnawave_api_token.get_secret_value.return_value = "test-token"

    # Bot Tokens
    settings.telegram_bot_token.get_secret_value.return_value = "123:test-bot"
    settings.cryptobot_token.get_secret_value.return_value = "test-crypto"

    # Admin Configuration
    settings.admin_telegram_ids = [12345]

    # Worker Configuration
    settings.worker_concurrency = 2
    settings.result_ttl_seconds = 3600

    # Notification Settings
    settings.notification_max_retries = 5
    settings.notification_batch_size = 50

    # Health Check Configuration
    settings.health_check_interval_seconds = 120

    # Cleanup Configuration
    settings.cleanup_audit_retention_days = 90
    settings.cleanup_webhook_retention_days = 30

    # Bulk Operations
    settings.bulk_batch_size = 50

    # Monitoring
    settings.metrics_port = 9091

    # Application Environment
    settings.log_level = "DEBUG"
    settings.environment = "test"

    with patch("src.config.get_settings", return_value=settings):
        yield settings


@pytest.fixture
def mock_settings():
    """Provide test settings with all required configuration."""
    settings = MagicMock()

    # Database Configuration
    settings.database_url = "sqlite+aiosqlite:///:memory:"

    # Cache Configuration
    settings.redis_url = "redis://localhost:6379/0"

    # External Services
    settings.remnawave_url = "http://localhost:3000"
    settings.remnawave_api_token.get_secret_value.return_value = "test-token"

    # Bot Tokens
    settings.telegram_bot_token.get_secret_value.return_value = "123:test-bot"
    settings.cryptobot_token.get_secret_value.return_value = "test-crypto"

    # Admin Configuration
    settings.admin_telegram_ids = [12345]

    # Worker Configuration
    settings.worker_concurrency = 2
    settings.result_ttl_seconds = 3600

    # Notification Settings
    settings.notification_max_retries = 5
    settings.notification_batch_size = 50

    # Health Check Configuration
    settings.health_check_interval_seconds = 120

    # Cleanup Configuration
    settings.cleanup_audit_retention_days = 90
    settings.cleanup_webhook_retention_days = 30

    # Bulk Operations
    settings.bulk_batch_size = 50

    # Monitoring
    settings.metrics_port = 9091

    # Application Environment
    settings.log_level = "DEBUG"
    settings.environment = "test"

    return settings


@pytest_asyncio.fixture
async def mock_redis():
    """Provide mock Redis client with common operations."""
    redis = AsyncMock()

    # Basic operations
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)

    # Connection management
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    redis.close = AsyncMock()

    # Pub/Sub
    redis.publish = AsyncMock(return_value=1)

    # Hash operations
    redis.hget = AsyncMock(return_value=None)
    redis.hset = AsyncMock(return_value=1)
    redis.hgetall = AsyncMock(return_value={})

    # List operations
    redis.lpush = AsyncMock(return_value=1)
    redis.rpush = AsyncMock(return_value=1)
    redis.lpop = AsyncMock(return_value=None)
    redis.rpop = AsyncMock(return_value=None)
    redis.llen = AsyncMock(return_value=0)

    # Set operations
    redis.sadd = AsyncMock(return_value=1)
    redis.srem = AsyncMock(return_value=1)
    redis.smembers = AsyncMock(return_value=set())

    # Info
    redis.info = AsyncMock(return_value={"clients": {"connected_clients": 5}})

    return redis


@pytest_asyncio.fixture
async def mock_db_session():
    """Provide mock database session."""
    session = AsyncMock()

    # Basic operations
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()

    # Context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    # Query results
    result = AsyncMock()
    result.scalars = MagicMock(return_value=result)
    result.all = MagicMock(return_value=[])
    result.first = MagicMock(return_value=None)
    result.one = MagicMock(return_value=None)
    result.one_or_none = MagicMock(return_value=None)
    session.execute.return_value = result

    return session


@pytest_asyncio.fixture
async def mock_remnawave():
    """Provide mock RemnawaveClient."""
    client = AsyncMock()

    # Context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    # API methods
    client.get_users = AsyncMock(return_value=[])
    client.get_nodes = AsyncMock(return_value=[])
    client.create_user = AsyncMock(return_value={"uuid": "test-uuid"})
    client.update_user = AsyncMock(return_value={"uuid": "test-uuid"})
    client.delete_user = AsyncMock(return_value=True)
    client.reset_user_traffic = AsyncMock(return_value=True)
    client.get_user = AsyncMock(return_value={"uuid": "test-uuid"})

    return client


@pytest_asyncio.fixture
async def mock_telegram():
    """Provide mock TelegramClient."""
    client = AsyncMock()

    # Context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    # API methods
    client.send_message = AsyncMock(return_value=True)
    client.send_bulk_messages = AsyncMock(return_value={"sent": 10, "failed": 0})
    client.edit_message = AsyncMock(return_value=True)
    client.delete_message = AsyncMock(return_value=True)

    return client


@pytest_asyncio.fixture
async def mock_cryptobot():
    """Provide mock CryptoBotClient."""
    client = AsyncMock()

    # Context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    # API methods
    client.create_invoice = AsyncMock(return_value={
        "invoice_id": 1,
        "pay_url": "https://pay.test/1",
        "status": "active",
    })
    client.get_invoices = AsyncMock(return_value=[])
    client.get_invoice = AsyncMock(return_value={
        "invoice_id": 1,
        "status": "paid",
    })

    return client


@pytest.fixture
def mock_broker():
    """Provide mock TaskIQ broker."""
    broker = MagicMock()
    broker.task = MagicMock(return_value=lambda f: f)
    return broker
