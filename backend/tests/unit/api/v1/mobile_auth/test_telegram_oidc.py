"""Unit tests for mobile Telegram OIDC route."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TokenResponseDTO,
    UserResponseDTO,
)
from src.application.services.telegram_oidc_auth import InvalidTelegramOIDCTokenError
from src.presentation.api.v1.mobile_auth.routes import telegram_oidc
from src.presentation.api.v1.mobile_auth.schemas import TelegramOIDCAuthRequest


def _request_model() -> TelegramOIDCAuthRequest:
    return TelegramOIDCAuthRequest.model_validate(
        {
            "id_token": "telegram-id-token",
            "device": {
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "platform": "ios",
                "platform_id": "ios-vendor-id",
                "os_version": "17.4",
                "app_version": "1.2.3",
                "device_model": "iPhone 15 Pro",
                "push_token": None,
            },
        }
    )


def _auth_result(*, is_new_user: bool) -> AuthResponseDTO:
    return AuthResponseDTO(
        tokens=TokenResponseDTO(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="Bearer",
            expires_in=900,
        ),
        user=UserResponseDTO(
            id=uuid4(),
            email="tg123456789@telegram.local",
            username="telegram_route_user",
            status="active",
            telegram_id=123456789,
            telegram_username="telegram_route_user",
            created_at=datetime.now(UTC),
            subscription=SubscriptionInfoDTO(status=SubscriptionStatus.NONE),
        ),
        is_new_user=is_new_user,
    )


class TestTelegramOIDCRoute:
    @pytest.mark.unit
    async def test_success_returns_auth_response(self) -> None:
        db = AsyncMock()
        use_case = MagicMock()
        use_case.execute = AsyncMock(return_value=(_auth_result(is_new_user=True), True))

        with (
            patch("src.presentation.api.v1.mobile_auth.routes.MobileUserRepository"),
            patch("src.presentation.api.v1.mobile_auth.routes.MobileDeviceRepository"),
            patch("src.presentation.api.v1.mobile_auth.routes.AuthService"),
            patch("src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService"),
            patch("src.presentation.api.v1.mobile_auth.routes.MobileTelegramOIDCAuthUseCase", return_value=use_case),
            patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", AsyncMock()),
        ):
            response = await telegram_oidc(
                request=_request_model(),
                _rate_limit=None,
                db=db,
                sub_client=None,
            )

        assert response.is_new_user is True
        assert response.user.telegram_id == 123456789
        assert response.tokens.access_token == "access-token"
        db.commit.assert_awaited_once()

    @pytest.mark.unit
    async def test_invalid_token_maps_to_401(self) -> None:
        db = AsyncMock()
        use_case = MagicMock()
        use_case.execute = AsyncMock(
            side_effect=InvalidTelegramOIDCTokenError(
                "Telegram ID token signature is invalid",
                reason="signature_invalid",
            )
        )

        with (
            patch("src.presentation.api.v1.mobile_auth.routes.MobileUserRepository"),
            patch("src.presentation.api.v1.mobile_auth.routes.MobileDeviceRepository"),
            patch("src.presentation.api.v1.mobile_auth.routes.AuthService"),
            patch("src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService"),
            patch("src.presentation.api.v1.mobile_auth.routes.MobileTelegramOIDCAuthUseCase", return_value=use_case),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await telegram_oidc(
                    request=_request_model(),
                    _rate_limit=None,
                    db=db,
                    sub_client=None,
                )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "INVALID_TELEGRAM_ID_TOKEN"
        assert exc_info.value.detail["details"]["reason"] == "signature_invalid"

    @pytest.mark.unit
    async def test_pending_2fa_response_is_returned_without_tokens(self) -> None:
        db = AsyncMock()
        use_case = MagicMock()
        use_case.execute = AsyncMock(
            return_value=(
                AuthResponseDTO(
                    is_new_user=False,
                    requires_2fa=True,
                    tfa_token="pending-2fa-token",
                    method="totp",
                ),
                False,
            )
        )

        with (
            patch("src.presentation.api.v1.mobile_auth.routes.MobileUserRepository"),
            patch("src.presentation.api.v1.mobile_auth.routes.MobileDeviceRepository"),
            patch("src.presentation.api.v1.mobile_auth.routes.AuthService"),
            patch("src.presentation.api.v1.mobile_auth.routes.TelegramOIDCAuthService"),
            patch("src.presentation.api.v1.mobile_auth.routes.MobileTelegramOIDCAuthUseCase", return_value=use_case),
            patch("src.presentation.api.v1.mobile_auth.routes.sync_auth_security_posture", AsyncMock()),
        ):
            response = await telegram_oidc(
                request=_request_model(),
                _rate_limit=None,
                db=db,
                sub_client=None,
            )

        assert response.requires_2fa is True
        assert response.tfa_token == "pending-2fa-token"
        assert response.method == "totp"
        assert response.tokens is None
        assert response.user is None
