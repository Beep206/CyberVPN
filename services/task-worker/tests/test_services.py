"""Tests for service client modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_remnawave_client_get_users():
    """Test RemnawaveClient get_users returns user list."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": [{"id": 1, "name": "User 1"}]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            users = await client.get_users()

            assert len(users) == 1
            assert users[0]["name"] == "User 1"


@pytest.mark.asyncio
async def test_remnawave_client_disable_user():
    """Test RemnawaveClient disable_user sends PATCH request."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "disabled"}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await client.disable_user("user-123")

            assert result["status"] == "disabled"
            mock_client.request.assert_called_with(
                "PATCH",
                "/api/users/user-123",
                json={"status": "disabled"}
            )


@pytest.mark.asyncio
async def test_remnawave_client_api_error():
    """Test RemnawaveClient raises error on non-2xx response."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "User not found"}
        mock_response.text = ""
        mock_response.reason_phrase = "Not Found"
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient, RemnawaveAPIError

        with pytest.raises(RemnawaveAPIError) as exc_info:
            async with RemnawaveClient() as client:
                await client.get_user("nonexistent")

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_remnawave_client_health_check():
    """Test RemnawaveClient health_check returns True when healthy."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await client.health_check()

            assert result is True


@pytest.mark.asyncio
async def test_telegram_client_send_message():
    """Test TelegramClient send_message sends request."""
    with patch("src.services.telegram_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.telegram_client import TelegramClient

        async with TelegramClient() as client:
            result = await client.send_message(123456, "Test message")

            assert result["message_id"] == 123
            assert "sent_at" in result


@pytest.mark.asyncio
async def test_telegram_client_send_admin_alert():
    """Test TelegramClient send_admin_alert broadcasts to admins."""
    with patch("src.services.telegram_client.httpx.AsyncClient") as mock_client_cls, \
         patch("src.services.telegram_client.get_settings") as mock_settings:

        mock_settings.return_value.admin_telegram_ids = [111, 222]

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.telegram_client import TelegramClient

        async with TelegramClient() as client:
            results = await client.send_admin_alert("Alert message", severity="warning")

            assert len(results) == 2


@pytest.mark.asyncio
async def test_telegram_client_rate_limit_retry():
    """Test TelegramClient retries on 429 error."""
    with patch("src.services.telegram_client.httpx.AsyncClient") as mock_client_cls, \
         patch("src.services.telegram_client.asyncio.sleep") as mock_sleep:

        mock_client = AsyncMock()
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        mock_error_response.json.return_value = {"ok": False, "parameters": {"retry_after": 1}}

        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {"ok": True, "result": {"message_id": 123}}

        mock_client.request.side_effect = [
            httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=mock_error_response),
            mock_success_response,
        ]
        mock_client_cls.return_value = mock_client

        from src.services.telegram_client import TelegramClient

        async with TelegramClient() as client:
            result = await client.send_message(123456, "Test")

            assert result["message_id"] == 123
            mock_sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_cryptobot_client_get_invoices():
    """Test CryptoBotClient get_invoices returns invoice list."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"items": [{"id": 1, "amount": 10.5}]}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.cryptobot_client import CryptoBotClient
        from pydantic import SecretStr

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            invoices = await client.get_invoices(status="active")

            assert len(invoices) == 1
            assert invoices[0]["amount"] == 10.5


@pytest.mark.asyncio
async def test_cryptobot_client_create_invoice():
    """Test CryptoBotClient create_invoice sends POST request."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"invoice_id": "inv-123"}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.cryptobot_client import CryptoBotClient
        from pydantic import SecretStr

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            invoice = await client.create_invoice(amount=50.0, currency="USDT", description="Test payment")

            assert invoice["invoice_id"] == "inv-123"


@pytest.mark.asyncio
async def test_cryptobot_client_health_check():
    """Test CryptoBotClient health_check returns True when healthy."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": [{"currency": "USDT", "amount": "100.0"}]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.cryptobot_client import CryptoBotClient
        from pydantic import SecretStr

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            result = await client.health_check()

            assert result is True


@pytest.mark.asyncio
async def test_cache_service_get_set():
    """Test CacheService get and set operations."""
    from src.services.cache_service import CacheService

    mock_redis = AsyncMock()
    mock_redis.get.return_value = b'{"key": "value"}'
    mock_redis.set.return_value = None

    cache = CacheService(mock_redis)

    # Test set
    await cache.set("test_key", {"key": "value"}, ttl=60)
    mock_redis.set.assert_called_once()

    # Test get
    result = await cache.get("test_key")
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_cache_service_delete():
    """Test CacheService delete operation."""
    from src.services.cache_service import CacheService

    mock_redis = AsyncMock()
    mock_redis.delete.return_value = 1

    cache = CacheService(mock_redis)

    result = await cache.delete("test_key")
    assert result is True


@pytest.mark.asyncio
async def test_redis_client_check():
    """Test redis_client check_redis returns True when healthy."""
    with patch("src.services.redis_client.Redis") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_cls.from_pool.return_value = mock_redis

        from src.services.redis_client import check_redis

        result = await check_redis()

        assert result is True
        mock_redis.ping.assert_called_once()
        mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_redis_client_check_failure():
    """Test redis_client check_redis returns False on failure."""
    with patch("src.services.redis_client.Redis") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis_cls.from_pool.return_value = mock_redis

        from src.services.redis_client import check_redis

        result = await check_redis()

        assert result is False
