"""Unit tests for MagicLinkService.

Tests token generation, validation/consumption, rate limiting,
and edge cases for the passwordless magic link flow.

Note on mocking redis.asyncio pipelines:
  - redis.pipeline() is a sync call returning a pipeline object
  - pipe.incr(), pipe.ttl(), pipe.get(), pipe.delete() are sync (queue commands)
  - pipe.execute() is async (sends queued commands to Redis)
  We use MagicMock for the pipeline and only AsyncMock for execute().
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.magic_link_service import MagicLinkService, RateLimitExceededError


def _make_pipeline(execute_return):
    """Create a mock Redis pipeline with sync queue methods and async execute."""
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=execute_return)
    # incr, ttl, get, delete are sync calls that just queue commands
    pipe.incr = MagicMock(return_value=pipe)
    pipe.ttl = MagicMock(return_value=pipe)
    pipe.get = MagicMock(return_value=pipe)
    pipe.delete = MagicMock(return_value=pipe)
    pipe.setex = MagicMock(return_value=pipe)
    return pipe


def _make_redis(pipe):
    """Create a mock Redis client that returns the given pipeline."""
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=pipe)
    redis.get = AsyncMock(return_value=None)
    redis.exists = AsyncMock(return_value=False)
    redis.expire = AsyncMock()
    redis.set = AsyncMock(return_value=False)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


class TestMagicLinkServiceGenerate:
    """Tests for MagicLinkService.generate()."""

    @pytest.fixture
    def mock_redis(self):
        """Redis mock with rate-limit pipeline returning first request."""
        pipe = _make_pipeline(execute_return=[1, -2])
        return _make_redis(pipe)

    @pytest.mark.unit
    async def test_generate_creates_token_with_sufficient_entropy(self, mock_redis):
        """Generated token has at least 64 characters (48 bytes -> 64 URL-safe chars)."""
        # Arrange
        service = MagicLinkService(mock_redis)

        # Act
        token, otp_code = await service.generate(email="test@example.com")

        # Assert - secrets.token_urlsafe(48) produces 64 chars
        assert len(token) >= 64
        assert len(otp_code) == 6
        assert otp_code.isdigit()

    @pytest.mark.unit
    async def test_generate_stores_token_in_redis_with_ttl(self, mock_redis):
        """Generated token, reverse lookup and OTP are stored in Redis with 1-hour TTL."""
        service = MagicLinkService(mock_redis)

        pipe = mock_redis.pipeline.return_value
        token, otp_code = await service.generate(email="test@example.com")

        assert pipe.setex.call_count == 3

        key, ttl, data_json = pipe.setex.call_args_list[0].args
        assert key == f"magic_link:{token}"
        assert ttl == 3600
        data = json.loads(data_json)
        assert data["email"] == "test@example.com"
        assert "created_at" in data

        email_key, email_ttl, stored_token = pipe.setex.call_args_list[1].args
        otp_key, otp_ttl, stored_otp = pipe.setex.call_args_list[2].args
        assert (email_key, email_ttl, stored_token) == ("magic_link_email:test@example.com", 3600, token)
        assert (otp_key, otp_ttl, stored_otp) == ("magic_link_otp:test@example.com", 3600, otp_code)

    @pytest.mark.unit
    async def test_generate_stores_ip_address_when_provided(self, mock_redis):
        """IP address is included in the stored payload when provided."""
        service = MagicLinkService(mock_redis)

        await service.generate(email="test@example.com", ip_address="192.168.1.100")

        pipe = mock_redis.pipeline.return_value
        data_json = pipe.setex.call_args_list[0].args[2]
        data = json.loads(data_json)
        assert data["ip_address"] == "192.168.1.100"

    @pytest.mark.unit
    async def test_generate_stores_none_ip_when_not_provided(self, mock_redis):
        """IP address is None in the stored payload when not provided."""
        service = MagicLinkService(mock_redis)

        await service.generate(email="test@example.com")

        pipe = mock_redis.pipeline.return_value
        data_json = pipe.setex.call_args_list[0].args[2]
        data = json.loads(data_json)
        assert data["ip_address"] is None

    @pytest.mark.unit
    async def test_generate_sets_rate_limit_ttl_on_first_request(self, mock_redis):
        """Rate limit key TTL is set on the first request (count == 1)."""
        service = MagicLinkService(mock_redis)

        await service.generate(email="test@example.com")

        # expire should be called to set TTL on the rate-limit key
        mock_redis.expire.assert_called_once()
        call_args = mock_redis.expire.call_args
        key = call_args.args[0] if call_args.args else call_args[0][0]
        ttl = call_args.args[1] if call_args.args else call_args[0][1]
        assert key == "magic_link_rate:test@example.com"
        assert ttl == 3600  # 1 hour window

    @pytest.mark.unit
    async def test_generate_does_not_reset_ttl_on_subsequent_request(self):
        """Rate limit key TTL is NOT reset on subsequent requests (count > 1)."""
        pipe = _make_pipeline(execute_return=[3, 2400])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        await service.generate(email="test@example.com")

        # expire should NOT be called since count != 1
        mock_redis.expire.assert_not_called()

    @pytest.mark.unit
    async def test_generate_unique_tokens(self, mock_redis):
        """Two consecutive generate calls produce different tokens."""
        service = MagicLinkService(mock_redis)

        token1, otp1 = await service.generate(email="test@example.com")
        token2, otp2 = await service.generate(email="test@example.com")

        assert token1 != token2
        assert otp1 != otp2


class TestMagicLinkServiceRateLimit:
    """Tests for rate limiting in MagicLinkService.generate()."""

    @pytest.mark.unit
    async def test_rate_limit_exceeded_raises_error(self):
        """Exceeding MAX_REQUESTS_PER_HOUR raises RateLimitExceededError."""
        # Arrange
        pipe = _make_pipeline(execute_return=[6, 1800])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        # Act & Assert
        with pytest.raises(RateLimitExceededError) as exc_info:
            await service.generate(email="spammer@example.com")

        assert exc_info.value.email == "spammer@example.com"
        assert exc_info.value.retry_after_seconds == 1800

    @pytest.mark.unit
    async def test_rate_limit_at_boundary_does_not_raise(self):
        """Exactly MAX_REQUESTS_PER_HOUR (5) does NOT raise -- only > 5 raises."""
        pipe = _make_pipeline(execute_return=[5, 2000])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        # Should succeed without error
        token, otp_code = await service.generate(email="borderline@example.com")
        assert len(token) >= 64
        assert len(otp_code) == 6

    @pytest.mark.unit
    async def test_rate_limit_retry_after_uses_window_when_ttl_negative(self):
        """retry_after_seconds falls back to RATE_LIMIT_WINDOW when TTL is negative."""
        pipe = _make_pipeline(execute_return=[10, -1])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await service.generate(email="test@example.com")

        assert exc_info.value.retry_after_seconds == 3600  # Full window


class TestMagicLinkServiceValidateAndConsume:
    """Tests for MagicLinkService.validate_and_consume()."""

    @pytest.mark.unit
    async def test_validate_valid_token_returns_payload(self):
        """Valid token returns the stored payload dict."""
        # Arrange
        payload = json.dumps(
            {
                "email": "test@example.com",
                "ip_address": "10.0.0.1",
                "created_at": "2026-01-15T10:00:00+00:00",
            }
        )
        pipe = _make_pipeline(execute_return=[payload.encode(), 1])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        # Act
        result = await service.validate_and_consume("valid_token_string")

        # Assert
        assert result is not None
        assert result["email"] == "test@example.com"
        assert result["ip_address"] == "10.0.0.1"
        assert result["created_at"] == "2026-01-15T10:00:00+00:00"

    @pytest.mark.unit
    async def test_validate_expired_token_returns_none(self):
        """Expired or non-existent token returns None."""
        pipe = _make_pipeline(execute_return=[None, 0])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        result = await service.validate_and_consume("expired_or_invalid_token")

        assert result is None

    @pytest.mark.unit
    async def test_validate_consumes_token_atomically(self):
        """Token is deleted from Redis during validation (single-use)."""
        payload = json.dumps(
            {"email": "test@example.com", "ip_address": None, "created_at": "2026-01-01T00:00:00+00:00"}
        )
        pipe = _make_pipeline(execute_return=[payload.encode(), 1])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        await service.validate_and_consume("token_to_consume")

        # Pipeline should have get + delete calls
        pipe.get.assert_called_once_with("magic_link:token_to_consume")
        assert pipe.delete.call_args_list[0].args == ("magic_link:token_to_consume",)

    @pytest.mark.unit
    async def test_validate_empty_token_string(self):
        """Empty token string returns None."""
        pipe = _make_pipeline(execute_return=[None, 0])
        mock_redis = _make_redis(pipe)

        service = MagicLinkService(mock_redis)

        result = await service.validate_and_consume("")

        assert result is None

    @pytest.mark.unit
    async def test_validate_allows_single_replay_then_blocks_further_reuse(self):
        """Second consumption may replay once; subsequent reuse is blocked."""
        payload = json.dumps(
            {"email": "test@example.com", "ip_address": None, "created_at": "2026-01-01T00:00:00+00:00"}
        )

        first_read = _make_pipeline(execute_return=[payload.encode(), 1])
        first_cleanup = _make_pipeline(execute_return=[1, 1, True, 1])
        second_read = _make_pipeline(execute_return=[None, 0])
        third_read = _make_pipeline(execute_return=[None, 0])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=[first_read, first_cleanup, second_read, third_read])
        mock_redis.get = AsyncMock(side_effect=[payload.encode(), payload.encode()])
        mock_redis.set = AsyncMock(side_effect=[True, False])

        service = MagicLinkService(mock_redis)

        result1 = await service.validate_and_consume("one_time_token")
        result2 = await service.validate_and_consume("one_time_token")
        result3 = await service.validate_and_consume("one_time_token")

        assert result1 is not None
        assert result2 is not None
        assert result3 is None


class TestRateLimitExceededError:
    """Tests for the RateLimitExceededError exception class."""

    @pytest.mark.unit
    def test_error_contains_email(self):
        """Error stores the offending email address."""
        error = RateLimitExceededError("bad@example.com", retry_after_seconds=600)

        assert error.email == "bad@example.com"
        assert error.retry_after_seconds == 600

    @pytest.mark.unit
    def test_error_message_includes_email(self):
        """Error message includes the email address."""
        error = RateLimitExceededError("test@example.com")

        assert "test@example.com" in str(error)

    @pytest.mark.unit
    def test_error_retry_after_defaults_to_none(self):
        """retry_after_seconds defaults to None when not provided."""
        error = RateLimitExceededError("test@example.com")

        assert error.retry_after_seconds is None
