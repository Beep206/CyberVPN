"""Security tests for registration endpoint (CRIT-1).

Tests that:
1. Registration is blocked when REGISTRATION_ENABLED=false
2. Registration requires invite token when enabled with invite-only mode
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Request, Response


def _fake_customer_realm() -> SimpleNamespace:
    return SimpleNamespace(
        auth_realm=SimpleNamespace(id=uuid4()),
        realm_key="customer",
    )


class TestRegistrationDisabled:
    """Test registration when REGISTRATION_ENABLED=false (default)."""

    @pytest.mark.asyncio
    async def test_registration_blocked_when_disabled(self):
        """Registration returns 403 when disabled."""
        from fastapi import HTTPException

        from src.presentation.api.v1.auth.registration import register
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        # Mock settings with registration disabled
        with patch("src.presentation.api.v1.auth.registration.settings") as mock_settings:
            mock_settings.registration_enabled = False
            mock_settings.registration_invite_required = True

            request = RegisterRequest(
                login="testuser",
                email="test@example.com",
                password="SecurePass123!",
                locale="en-EN",
                tos_accepted=True,
            )

            mock_db = MagicMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()
            mock_dispatcher = AsyncMock()
            mock_redis = AsyncMock()
            mock_http_request = MagicMock(spec=Request)
            mock_http_request.headers = {}
            mock_http_request.cookies = {}
            mock_http_request.url = SimpleNamespace(hostname="testserver")

            with pytest.raises(HTTPException) as exc_info:
                await register(
                    request=request,
                    http_request=mock_http_request,
                    response=MagicMock(spec=Response),
                    invite_token=None,
                    db=mock_db,
                    email_dispatcher=mock_dispatcher,
                    redis_client=mock_redis,
                )

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["code"] == "REGISTRATION_DISABLED"
            assert "paused" in exc_info.value.detail["message"].lower()


class TestInviteTokenValidation:
    """Test invite token validation."""

    @pytest.mark.asyncio
    async def test_registration_requires_invite_token(self):
        """Registration fails without invite token when required."""
        from fastapi import HTTPException

        from src.presentation.api.v1.auth.registration import register
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        with patch("src.presentation.api.v1.auth.registration.settings") as mock_settings:
            mock_settings.registration_enabled = True
            mock_settings.registration_invite_required = True

            request = RegisterRequest(
                login="testuser",
                email="test@example.com",
                password="SecurePass123!",
                locale="en-EN",
                tos_accepted=True,
            )

            mock_db = MagicMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()
            mock_dispatcher = AsyncMock()
            mock_redis = AsyncMock()
            mock_http_request = MagicMock(spec=Request)
            mock_http_request.headers = {}
            mock_http_request.cookies = {}
            mock_http_request.url = SimpleNamespace(hostname="testserver")

            with pytest.raises(HTTPException) as exc_info:
                await register(
                    request=request,
                    http_request=mock_http_request,
                    response=MagicMock(spec=Response),
                    invite_token=None,  # No invite token
                    db=mock_db,
                    email_dispatcher=mock_dispatcher,
                    redis_client=mock_redis,
                )

            assert exc_info.value.status_code == 403
            assert "invite" in exc_info.value.detail.lower()


class TestRegistrationAccessExchange:
    """Registration access raw tokens are exchanged once for cookie-backed grants."""

    @pytest.mark.asyncio
    async def test_exchange_sets_http_only_cookie_and_returns_no_secret_material(self, monkeypatch):
        from src.presentation.api.v1.auth import registration
        from src.presentation.api.v1.auth.schemas import RegistrationAccessExchangeRequest

        idempotency_key = uuid4()
        calls: list[str] = []

        class FakeRegistrationAccessGrantService:
            def __init__(self, _db):
                pass

            async def exchange_for_browser(self, *, token: str, idempotency_key: str, host: str, auth_realm_id):
                assert token == "raw-registration-access-token"
                assert idempotency_key
                assert host == "public.example"
                assert auth_realm_id
                calls.append("exchange")
                return SimpleNamespace(
                    grant=SimpleNamespace(email_hint_hash="email-hash"),
                    session_token=f"{registration.REGISTRATION_ACCESS_COOKIE_NAME.strip('_')}_session",
                    expires_at=datetime.now(UTC) + timedelta(minutes=10),
                )

            async def has_token(self, _token: str):
                calls.append("has_token")
                return True

        monkeypatch.setattr(registration, "RegistrationAccessGrantService", FakeRegistrationAccessGrantService)
        monkeypatch.setattr(registration.settings, "registration_invite_required", True)
        monkeypatch.setattr(registration.settings, "cookie_secure", True)

        http_request = MagicMock(spec=Request)
        http_request.headers = {"host": "public.example"}
        http_request.url = SimpleNamespace(hostname="public.example")
        response = Response()

        result = await registration.exchange_registration_access(
            request=RegistrationAccessExchangeRequest.model_validate(
                {"registration_access_token": "raw-registration-access-token"}
            ),
            http_request=http_request,
            response=response,
            idempotency_key=idempotency_key,
            db=MagicMock(),
            current_realm=_fake_customer_realm(),
        )

        set_cookie = response.headers["set-cookie"]
        assert result.status == "exchanged"
        assert result.email_hint_present is True
        assert result.email_hint_masked is None
        assert registration.REGISTRATION_ACCESS_COOKIE_NAME in set_cookie
        assert "httponly" in set_cookie.lower()
        assert "raw-registration-access-token" not in result.model_dump_json()
        assert "raw-registration-access-token" not in set_cookie
        assert "email-hash" not in result.model_dump_json()
        assert calls == ["exchange"]


class TestRegistrationInviteReservation:
    """Registration consumes invite tokens only after durable registration work succeeds."""

    @pytest.mark.asyncio
    async def test_registration_reserves_exchange_cookie_grant_and_consumes_after_success(self, monkeypatch):
        from src.presentation.api.v1.auth import registration
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        calls: list[str] = []

        class FakeInviteTokenService:
            def __init__(self, _redis_client):
                pass

            async def reserve_for_registration(self, _token: str, _reservation_id: str):
                calls.append("legacy_reserve")
                return None

            async def consume_reserved_for_registration(self, token: str, reservation_id: str):
                assert token == "invite-token-42"
                assert reservation_id
                calls.append("legacy_consume")
                return {"created_by": "admin", "role": "VIEWER", "email_hint": "test@example.com"}

            async def release_registration_reservation(self, _token: str, _reservation_id: str):
                calls.append("legacy_release")
                return True

        class FakeGrantData:
            def as_invite_data(self):
                return {"created_by": "admin", "role": "viewer", "email_hint_hash": None}

        class FakeRegistrationAccessGrantService:
            def __init__(self, _db):
                pass

            async def reserve_exchange_session_for_registration(
                self,
                *,
                session_token: str,
                reservation_id: str,
                host: str,
                registration_idempotency_key: str | None,
            ):
                assert session_token == "exchange-session-42"
                assert reservation_id
                assert host == "testserver"
                assert registration_idempotency_key is None
                calls.append("db_exchange_reserve")
                return FakeGrantData()

            async def has_token(self, _token: str):
                calls.append("db_has_token")
                return True

            async def consume_reserved_exchange_session_for_registration(
                self,
                *,
                session_token: str,
                reservation_id: str,
                consumed_user_id,
                host: str,
            ):
                assert session_token == "exchange-session-42"
                assert reservation_id
                assert consumed_user_id
                assert host == "testserver"
                calls.append("db_exchange_consume")
                return FakeGrantData()

            async def release_exchange_session_registration_reservation(self, **_kwargs):
                calls.append("db_exchange_release")
                return True

        class FakeRegisterUseCase:
            def __init__(self, **_kwargs):
                pass

            async def execute(self, **kwargs):
                calls.append("execute")
                assert kwargs["role"].value == "viewer"
                return SimpleNamespace(
                    user=SimpleNamespace(
                        id=uuid4(),
                        login="testuser",
                        email="test@example.com",
                        is_active=False,
                        is_email_verified=False,
                    ),
                    otp_sent=True,
                    resumed_unverified_registration=False,
                )

        monkeypatch.setattr(registration.settings, "registration_enabled", True)
        monkeypatch.setattr(registration.settings, "registration_invite_required", True)
        monkeypatch.setattr(registration, "InviteTokenService", FakeInviteTokenService)
        monkeypatch.setattr(registration, "RegistrationAccessGrantService", FakeRegistrationAccessGrantService)
        monkeypatch.setattr(registration, "RegisterUseCase", FakeRegisterUseCase)
        monkeypatch.setattr(registration, "_log_registration_attempt", AsyncMock())
        monkeypatch.setattr(registration, "sync_auth_security_posture", AsyncMock())

        request = RegisterRequest(
            login="testuser",
            email="test@example.com",
            password="SecurePass123!",
            locale="en-EN",
            tos_accepted=True,
        )
        mock_http_request = MagicMock(spec=Request)
        mock_http_request.headers = {}
        mock_http_request.cookies = {registration.REGISTRATION_ACCESS_COOKIE_NAME: "exchange-session-42"}
        mock_http_request.url = SimpleNamespace(hostname="testserver")
        mock_response = MagicMock(spec=Response)

        response = await registration.register(
            request=request,
            http_request=mock_http_request,
            response=mock_response,
            invite_token=None,
            db=MagicMock(),
            current_realm=_fake_customer_realm(),
            email_dispatcher=AsyncMock(),
            redis_client=AsyncMock(),
        )

        assert response.login == "testuser"
        assert calls == ["db_exchange_reserve", "execute", "db_exchange_consume"]
        assert mock_response.set_cookie.called

    @pytest.mark.asyncio
    async def test_registration_releases_exchange_cookie_grant_when_use_case_fails(self, monkeypatch):
        from src.presentation.api.v1.auth import registration
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        calls: list[str] = []

        class FakeInviteTokenService:
            def __init__(self, _redis_client):
                pass

            async def reserve_for_registration(self, _token: str, _reservation_id: str):
                calls.append("legacy_reserve")
                return {"created_by": "admin", "role": "VIEWER", "email_hint": "test@example.com"}

            async def consume_reserved_for_registration(self, _token: str, _reservation_id: str):
                calls.append("legacy_consume")
                return {"created_by": "admin", "role": "VIEWER", "email_hint": "test@example.com"}

            async def release_registration_reservation(self, _token: str, _reservation_id: str):
                calls.append("legacy_release")
                return True

        class FakeGrantData:
            def as_invite_data(self):
                return {"created_by": "admin", "role": "viewer", "email_hint_hash": None}

        class FakeRegistrationAccessGrantService:
            def __init__(self, _db):
                pass

            async def reserve_exchange_session_for_registration(self, **_kwargs):
                calls.append("db_exchange_reserve")
                return FakeGrantData()

            async def has_token(self, _token: str):
                calls.append("db_has_token")
                return True

            async def consume_reserved_exchange_session_for_registration(self, **_kwargs):
                calls.append("db_exchange_consume")
                return FakeGrantData()

            async def release_exchange_session_registration_reservation(self, *, reason: str, **_kwargs):
                assert reason == "registration_failed"
                calls.append("db_exchange_release")
                return True

        class FakeRegisterUseCase:
            def __init__(self, **_kwargs):
                pass

            async def execute(self, **_kwargs):
                calls.append("execute")
                raise RuntimeError("registration failed after invite reservation")

        monkeypatch.setattr(registration.settings, "registration_enabled", True)
        monkeypatch.setattr(registration.settings, "registration_invite_required", True)
        monkeypatch.setattr(registration, "InviteTokenService", FakeInviteTokenService)
        monkeypatch.setattr(registration, "RegistrationAccessGrantService", FakeRegistrationAccessGrantService)
        monkeypatch.setattr(registration, "RegisterUseCase", FakeRegisterUseCase)
        monkeypatch.setattr(registration, "_log_registration_attempt", AsyncMock())

        request = RegisterRequest(
            login="testuser",
            email="test@example.com",
            password="SecurePass123!",
            locale="en-EN",
            tos_accepted=True,
        )
        mock_http_request = MagicMock(spec=Request)
        mock_http_request.headers = {}
        mock_http_request.cookies = {registration.REGISTRATION_ACCESS_COOKIE_NAME: "exchange-session-42"}
        mock_http_request.url = SimpleNamespace(hostname="testserver")

        with pytest.raises(RuntimeError, match="registration failed"):
            await registration.register(
                request=request,
                http_request=mock_http_request,
                response=MagicMock(spec=Response),
                invite_token=None,
                db=MagicMock(),
                current_realm=_fake_customer_realm(),
                email_dispatcher=AsyncMock(),
                redis_client=AsyncMock(),
            )

        assert calls == ["db_exchange_reserve", "execute", "db_exchange_release"]

    @pytest.mark.asyncio
    async def test_registration_blocks_raw_durable_grant_without_redis_fallback(self, monkeypatch):
        from fastapi import HTTPException

        from src.presentation.api.v1.auth import registration
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        calls: list[str] = []

        class FakeInviteTokenService:
            def __init__(self, _redis_client):
                pass

            async def reserve_for_registration(self, _token: str, _reservation_id: str):
                calls.append("legacy_reserve")
                return {"created_by": "admin", "role": "viewer", "email_hint": None}

        class FakeRegistrationAccessGrantService:
            def __init__(self, _db):
                pass

            async def has_token(self, _token: str):
                calls.append("db_has_token")
                return True

        monkeypatch.setattr(registration.settings, "registration_enabled", True)
        monkeypatch.setattr(registration.settings, "registration_invite_required", True)
        monkeypatch.setattr(registration, "InviteTokenService", FakeInviteTokenService)
        monkeypatch.setattr(registration, "RegistrationAccessGrantService", FakeRegistrationAccessGrantService)
        monkeypatch.setattr(registration, "_log_registration_attempt", AsyncMock())

        request = RegisterRequest(
            login="testuser",
            email="test@example.com",
            password="SecurePass123!",
            locale="en-EN",
            tos_accepted=True,
        )
        mock_http_request = MagicMock(spec=Request)
        mock_http_request.headers = {}
        mock_http_request.cookies = {}
        mock_http_request.url = SimpleNamespace(hostname="testserver")

        with pytest.raises(HTTPException) as exc_info:
            await registration.register(
                request=request,
                http_request=mock_http_request,
                response=MagicMock(spec=Response),
                invite_token="invite-token-42",
                db=MagicMock(),
                current_realm=_fake_customer_realm(),
                email_dispatcher=AsyncMock(),
                redis_client=AsyncMock(),
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "REGISTRATION_ACCESS_EXCHANGE_REQUIRED"
        assert calls == ["db_has_token"]


class TestInviteTokenService:
    """Test InviteTokenService functionality."""

    @pytest.mark.asyncio
    async def test_generate_token_stores_in_redis(self):
        """Token generation stores data in Redis."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        service = InviteTokenService(mock_redis)

        token = await service.generate(
            created_by="admin-id",
            role="VIEWER",
            email_hint="test@example.com",
        )

        # Verify token was stored
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert f"invite_token:{token}" == call_args[0][0]

    @pytest.mark.asyncio
    async def test_validate_returns_data_for_valid_token(self):
        """Validating valid token returns data."""
        import json

        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        token_data = {"created_by": "admin", "role": "VIEWER", "created_at": "2026-01-01"}
        mock_redis.get = AsyncMock(return_value=json.dumps(token_data))

        service = InviteTokenService(mock_redis)
        result = await service.validate("test-token")

        assert result is not None
        assert result["role"] == "VIEWER"

    @pytest.mark.asyncio
    async def test_validate_returns_none_for_missing_token(self):
        """Validating non-existent token returns None."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        service = InviteTokenService(mock_redis)
        result = await service.validate("nonexistent-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_reserve_for_registration_sets_short_lived_reservation_without_consuming_token(self):
        """Reservation validates an invite token but does not delete it."""
        import hashlib
        import json

        from src.application.services.invite_service import InviteTokenService

        token_data = {"created_by": "admin", "role": "VIEWER", "created_at": "2026-01-01"}
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(token_data))
        mock_redis.set = AsyncMock(return_value=True)

        service = InviteTokenService(mock_redis)
        result = await service.reserve_for_registration("test-token", "reservation-1")

        assert result == token_data
        expected_reservation_key = "invite_token_registration_reservation:" + hashlib.sha256(b"test-token").hexdigest()
        mock_redis.set.assert_awaited_once_with(
            expected_reservation_key,
            "reservation-1",
            ex=600,
            nx=True,
        )
        assert "test-token" not in expected_reservation_key
        mock_redis.pipeline.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_reserved_for_registration_requires_matching_reservation(self):
        """A mismatched reservation cannot consume another request's invite token."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="other-reservation")

        service = InviteTokenService(mock_redis)
        service.validate_and_consume = AsyncMock()  # type: ignore[method-assign]

        result = await service.consume_reserved_for_registration("test-token", "reservation-1")

        assert result is None
        service.validate_and_consume.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_consume_reserved_for_registration_consumes_and_releases_owned_reservation(self):
        """The owning registration request consumes the token and clears its reservation."""
        from src.application.services.invite_service import InviteTokenService

        token_data = {"created_by": "admin", "role": "VIEWER", "created_at": "2026-01-01"}
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"reservation-1")
        mock_redis.eval = AsyncMock(return_value=1)

        service = InviteTokenService(mock_redis)
        service.validate_and_consume = AsyncMock(return_value=token_data)  # type: ignore[method-assign]

        result = await service.consume_reserved_for_registration("test-token", "reservation-1")

        assert result == token_data
        service.validate_and_consume.assert_awaited_once_with("test-token")
        mock_redis.eval.assert_awaited_once()
        assert mock_redis.eval.await_args.args[2] != "invite_token_registration_reservation:test-token"

    @pytest.mark.asyncio
    async def test_consume_reserved_for_registration_accepts_legacy_raw_reservation_key(self):
        """Legacy raw-token reservation keys remain consumable during the compatibility window."""
        from src.application.services.invite_service import InviteTokenService

        token_data = {"created_by": "admin", "role": "VIEWER", "created_at": "2026-01-01"}
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=[None, b"reservation-1"])
        mock_redis.eval = AsyncMock(return_value=1)

        service = InviteTokenService(mock_redis)
        service.validate_and_consume = AsyncMock(return_value=token_data)  # type: ignore[method-assign]

        result = await service.consume_reserved_for_registration("test-token", "reservation-1")

        assert result == token_data
        service.validate_and_consume.assert_awaited_once_with("test-token")
        mock_redis.eval.assert_awaited_once()
        assert mock_redis.eval.await_args.args[2] == "invite_token_registration_reservation:test-token"

    @pytest.mark.asyncio
    async def test_revoke_token_deletes_from_redis(self):
        """Revoking token deletes it from Redis."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)

        service = InviteTokenService(mock_redis)
        result = await service.revoke("test-token")

        assert result is True
        mock_redis.delete.assert_called_once_with("invite_token:test-token")

    @pytest.mark.asyncio
    async def test_revoke_returns_false_for_missing_token(self):
        """Revoking non-existent token returns False."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=0)

        service = InviteTokenService(mock_redis)
        result = await service.revoke("nonexistent-token")

        assert result is False
