"""Test that pytest fixtures are properly configured."""

import pytest


def test_mock_settings(mock_settings):
    """Test mock settings fixture."""
    assert mock_settings.environment == "test"
    assert mock_settings.log_level == "DEBUG"
    assert mock_settings.worker_concurrency == 2
    assert mock_settings.remnawave_api_token.get_secret_value() == "test-token"


@pytest.mark.asyncio
async def test_mock_redis(mock_redis):
    """Test mock Redis client fixture."""
    await mock_redis.set("test_key", "test_value")
    assert await mock_redis.ping() is True
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_mock_remnawave(mock_remnawave):
    """Test mock Remnawave client fixture."""
    async with mock_remnawave as client:
        users = await client.get_users()
        assert users == []


@pytest.mark.asyncio
async def test_mock_telegram(mock_telegram):
    """Test mock Telegram client fixture."""
    async with mock_telegram as client:
        result = await client.send_message(12345, "Test message")
        assert result is True


@pytest.mark.asyncio
async def test_mock_cryptobot(mock_cryptobot):
    """Test mock CryptoBot client fixture."""
    async with mock_cryptobot as client:
        invoice = await client.create_invoice(amount=10, currency="USD")
        assert invoice["invoice_id"] == 1
        assert "pay_url" in invoice
