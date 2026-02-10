"""Unit tests for bot link token Redis helpers."""

import json
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.cache.bot_link_tokens import (
    consume_bot_link_token,
    generate_bot_link_token,
)


class TestGenerateBotLinkToken:
    """Tests for generate_bot_link_token()."""

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.mark.unit
    async def test_returns_token_string(self, mock_redis):
        token = await generate_bot_link_token(mock_redis, telegram_id=123456789)
        assert isinstance(token, str)
        assert len(token) > 20  # 32 bytes base64 = ~43 chars

    @pytest.mark.unit
    async def test_stores_in_redis_with_ttl(self, mock_redis):
        await generate_bot_link_token(mock_redis, telegram_id=42, ip="1.2.3.4")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        key = call_args[0][0]
        value = call_args[0][1]
        ttl = call_args[1]["ex"]

        assert key.startswith("tg_login_link:")
        assert ttl == 300

        data = json.loads(value)
        assert data["telegram_id"] == 42
        assert data["ip"] == "1.2.3.4"
        assert "created_at" in data

    @pytest.mark.unit
    async def test_unique_tokens(self, mock_redis):
        t1 = await generate_bot_link_token(mock_redis, telegram_id=1)
        t2 = await generate_bot_link_token(mock_redis, telegram_id=1)
        assert t1 != t2


class TestConsumeBotLinkToken:
    """Tests for consume_bot_link_token()."""

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.mark.unit
    async def test_returns_telegram_id_on_valid_token(self, mock_redis):
        mock_redis.getdel.return_value = json.dumps({"telegram_id": 999})

        result = await consume_bot_link_token(mock_redis, "valid_token")

        assert result == 999
        mock_redis.getdel.assert_called_once_with("tg_login_link:valid_token")

    @pytest.mark.unit
    async def test_returns_none_on_missing_token(self, mock_redis):
        mock_redis.getdel.return_value = None

        result = await consume_bot_link_token(mock_redis, "missing_token")

        assert result is None

    @pytest.mark.unit
    async def test_returns_none_on_invalid_json(self, mock_redis):
        mock_redis.getdel.return_value = "not-json"

        result = await consume_bot_link_token(mock_redis, "bad_token")

        assert result is None

    @pytest.mark.unit
    async def test_returns_none_on_missing_telegram_id(self, mock_redis):
        mock_redis.getdel.return_value = json.dumps({"ip": "1.2.3.4"})

        result = await consume_bot_link_token(mock_redis, "no_tg_id")

        assert result is None
