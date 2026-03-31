"""Unit tests for pending-2FA login completion route."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response

from src.presentation.api.v1.two_factor.routes import complete_2fa_login
from src.presentation.api.v1.two_factor.schemas import VerifyCodeRequest


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/2fa/complete",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )


class TestComplete2FALoginRoute:
    @pytest.mark.unit
    async def test_complete_2fa_login_issues_tokens_and_sets_cookies(self):
        user = MagicMock()
        user.id = uuid4()
        user.role = "viewer"
        user.is_active = True

        redis_client = MagicMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.delete = AsyncMock()
        pipeline = MagicMock()
        pipeline.execute = AsyncMock(return_value=[1, True])
        redis_client.pipeline.return_value = pipeline
        db = MagicMock()
        db.flush = AsyncMock()
        response = Response()
        auth_service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        refresh_exp = datetime.now(UTC) + timedelta(days=7)
        auth_service.create_access_token.return_value = ("access_tok", "jti_a", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti_r", refresh_exp)

        with (
            patch("src.presentation.api.v1.two_factor.routes.TwoFactorUseCase") as mock_use_case_cls,
            patch("src.presentation.api.v1.two_factor.routes.generate_client_fingerprint", return_value="fp_123"),
        ):
            mock_use_case = AsyncMock()
            mock_use_case.verify_code.return_value = True
            mock_use_case_cls.return_value = mock_use_case

            result = await complete_2fa_login(
                body=VerifyCodeRequest(code="123456"),
                http_request=_build_request(),
                response=response,
                user=user,
                db=db,
                redis_client=redis_client,
                auth_service=auth_service,
            )

        assert result.access_token == "access_tok"
        assert result.refresh_token == "refresh_tok"
        assert db.add.call_count == 1
        set_cookie_headers = response.headers.getlist("set-cookie")
        assert any("access_token=access_tok" in header for header in set_cookie_headers)
        assert any("refresh_token=refresh_tok" in header for header in set_cookie_headers)

    @pytest.mark.unit
    async def test_complete_2fa_login_rejects_invalid_code(self):
        user = MagicMock()
        user.id = uuid4()
        user.role = "viewer"
        user.is_active = True

        redis_client = MagicMock()
        redis_client.get = AsyncMock(return_value=None)
        pipeline = MagicMock()
        pipeline.execute = AsyncMock(return_value=[1, True])
        redis_client.pipeline.return_value = pipeline
        db = MagicMock()
        db.flush = AsyncMock()
        response = Response()
        auth_service = MagicMock()

        with patch("src.presentation.api.v1.two_factor.routes.TwoFactorUseCase") as mock_use_case_cls:
            mock_use_case = AsyncMock()
            mock_use_case.verify_code.return_value = False
            mock_use_case_cls.return_value = mock_use_case

            with pytest.raises(HTTPException) as exc_info:
                await complete_2fa_login(
                    body=VerifyCodeRequest(code="123456"),
                    http_request=_build_request(),
                    response=response,
                    user=user,
                    db=db,
                    redis_client=redis_client,
                    auth_service=auth_service,
                )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid verification code."
