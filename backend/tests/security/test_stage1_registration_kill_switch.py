"""S1-AUTH-001 public registration kill-switch coverage."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response

from src.application.dto.mobile_auth import DeviceInfoDTO, Platform, RegisterRequestDTO
from src.application.services.public_registration_policy import (
    REGISTRATION_DISABLED_CODE,
    PublicRegistrationDisabledError,
    ensure_public_registration_enabled,
    get_public_registration_state,
)
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.application.use_cases.auth.telegram_miniapp import TelegramMiniAppUseCase
from src.application.use_cases.mobile_auth.register import MobileRegisterUseCase
from src.application.use_cases.mobile_auth.telegram_auth import MobileTelegramAuthUseCase
from src.application.use_cases.mobile_auth.telegram_oidc_auth import MobileTelegramOIDCAuthUseCase


def _device() -> DeviceInfoDTO:
    return DeviceInfoDTO(
        device_id="123e4567-e89b-12d3-a456-426614174000",
        platform=Platform.IOS,
        platform_id="ios-vendor-id",
        os_version="17.4",
        app_version="1.2.3",
        device_model="iPhone 15 Pro",
    )


def _auth_service() -> MagicMock:
    service = MagicMock()
    access_exp = datetime.now(UTC) + timedelta(minutes=15)
    refresh_exp = datetime.now(UTC) + timedelta(days=7)
    service.create_access_token.return_value = ("access_token", "access_jti", access_exp)
    service.create_refresh_token.return_value = ("refresh_token", "refresh_jti", refresh_exp)
    service.hash_password = AsyncMock(return_value="$argon2id$synthetic")
    return service


def _mobile_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.email = "existing@example.com"
    user.username = "existing"
    user.status = "active"
    user.telegram_id = 424242
    user.telegram_username = "existing_tg"
    user.telegram_subject = "telegram-subject"
    user.auth_realm_id = None
    user.remnawave_uuid = None
    user.totp_enabled = False
    user.totp_secret = None
    user.is_email_verified = True
    user.linked_providers = []
    user.created_at = datetime.now(UTC)
    user.last_login_at = None
    return user


def test_default_public_registration_state_is_paused(monkeypatch):
    monkeypatch.setattr(
        "src.application.services.public_registration_policy.settings.registration_enabled",
        False,
    )
    monkeypatch.setattr(
        "src.application.services.public_registration_policy.settings.registration_invite_required",
        True,
    )

    state = get_public_registration_state()

    assert state.enabled is False
    assert state.invite_required is True
    assert state.paused is True


def test_public_registration_guard_fails_closed():
    with pytest.raises(PublicRegistrationDisabledError) as exc_info:
        ensure_public_registration_enabled(channel="web_password", registration_enabled=False)

    assert exc_info.value.public_detail() == {
        "code": REGISTRATION_DISABLED_CODE,
        "message": "Public registration is currently paused.",
        "channel": "web_password",
    }


@pytest.mark.asyncio
async def test_oauth_new_account_creation_blocked_when_registration_paused():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    user_repo.get_by_login.return_value = None
    oauth_repo = AsyncMock()
    oauth_repo.get_by_provider_and_user_id.return_value = None
    auth_service = _auth_service()
    remnawave = AsyncMock()
    use_case = OAuthLoginUseCase(
        user_repo=user_repo,
        oauth_repo=oauth_repo,
        auth_service=auth_service,
        session=AsyncMock(),
        remnawave_gateway=remnawave,
        allow_new_users=False,
    )

    with pytest.raises(PublicRegistrationDisabledError):
        await use_case.execute(
            provider="google",
            user_info={
                "id": "google-user-1",
                "email": "new@example.com",
                "email_verified": True,
                "email_trusted": True,
                "username": "newuser",
                "access_token": "provider-token",
            },
        )

    user_repo.create.assert_not_called()
    oauth_repo.create.assert_not_called()
    auth_service.hash_password.assert_not_awaited()
    remnawave.create_user.assert_not_called()


@pytest.mark.asyncio
async def test_oauth_existing_linked_account_still_logs_in_when_registration_paused():
    user = MagicMock()
    user.id = uuid4()
    user.role = "viewer"
    user.totp_enabled = False
    oauth_account = MagicMock(user_id=user.id)
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user
    oauth_repo = AsyncMock()
    oauth_repo.get_by_provider_and_user_id.return_value = oauth_account
    use_case = OAuthLoginUseCase(
        user_repo=user_repo,
        oauth_repo=oauth_repo,
        auth_service=_auth_service(),
        session=AsyncMock(),
        allow_new_users=False,
    )

    result = await use_case.execute(
        provider="google",
        user_info={"id": "google-user-1", "email": "existing@example.com", "access_token": "provider-token"},
    )

    assert result.is_new_user is False
    assert result.user is user
    user_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_miniapp_new_account_creation_blocked_when_paused():
    user_repo = AsyncMock()
    user_repo.get_by_telegram_id.return_value = None
    telegram_provider = MagicMock()
    telegram_provider.validate_init_data.return_value = {
        "id": "424242",
        "username": "new_tg",
        "first_name": "New",
    }
    use_case = TelegramMiniAppUseCase(
        user_repo=user_repo,
        auth_service=_auth_service(),
        session=AsyncMock(),
        telegram_provider=telegram_provider,
        remnawave_gateway=AsyncMock(),
        allow_new_users=False,
    )

    with pytest.raises(PublicRegistrationDisabledError):
        await use_case.execute("valid-init-data")

    user_repo.create.assert_not_called()
    user_repo.get_by_login.assert_not_called()


@pytest.mark.asyncio
async def test_mobile_password_registration_blocked_before_repository_side_effects():
    user_repo = AsyncMock()
    device_repo = AsyncMock()
    use_case = MobileRegisterUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=_auth_service(),
        allow_new_users=False,
    )

    with pytest.raises(PublicRegistrationDisabledError):
        await use_case.execute(
            RegisterRequestDTO(
                email="new-mobile@example.com",
                password="SecurePassword123!",
                device=_device(),
            )
        )

    user_repo.get_by_email.assert_not_called()
    user_repo.create.assert_not_called()
    device_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_mobile_telegram_new_account_creation_blocked_when_paused():
    user_repo = AsyncMock()
    user_repo.get_by_telegram_id.return_value = None
    device_repo = AsyncMock()
    telegram_service = MagicMock()
    telegram_service.validate_auth_data.return_value = SimpleNamespace(
        telegram_id=424242,
        username="new_tg",
        first_name="New",
        last_name=None,
    )
    use_case = MobileTelegramAuthUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=_auth_service(),
        telegram_auth_service=telegram_service,
        allow_new_users=False,
    )
    request = SimpleNamespace(auth_data="auth-data", device=_device())

    with pytest.raises(PublicRegistrationDisabledError):
        await use_case.execute(request)

    user_repo.create.assert_not_called()
    device_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_mobile_telegram_oidc_existing_user_login_allowed_when_paused():
    user = _mobile_user()
    user_repo = AsyncMock()
    user_repo.get_by_telegram_subject.return_value = user
    device_repo = AsyncMock()
    device_repo.get_by_device_id_and_user.return_value = None
    telegram_oidc_service = AsyncMock()
    telegram_oidc_service.validate_id_token.return_value = SimpleNamespace(
        subject="telegram-subject",
        telegram_id=424242,
        preferred_username="existing_tg",
        name="Existing Telegram",
    )
    use_case = MobileTelegramOIDCAuthUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=_auth_service(),
        telegram_oidc_service=telegram_oidc_service,
        allow_new_users=False,
    )
    request = SimpleNamespace(id_token="id-token", device=_device())

    result, is_new_user = await use_case.execute(request)

    assert is_new_user is False
    assert result.user.id == user.id
    user_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_magic_link_new_account_creation_returns_403_when_registration_paused(monkeypatch):
    from src.presentation.api.v1.auth.routes import verify_magic_link
    from src.presentation.api.v1.auth.schemas import MagicLinkVerifyRequest

    monkeypatch.setattr("src.presentation.api.v1.auth.routes.settings.registration_enabled", False)
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    auth_service = _auth_service()
    http_request = MagicMock(spec=Request)
    http_request.headers = {}

    with (
        patch(
            "src.presentation.api.v1.auth.routes.MagicLinkService.validate_and_consume",
            new=AsyncMock(
                return_value={
                    "email": "new-magic@example.com",
                    "locale": "en-EN",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ),
        ),
        patch("src.presentation.api.v1.auth.routes.AdminUserRepository", return_value=user_repo),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await verify_magic_link(
                request=MagicLinkVerifyRequest(token="magic-token"),
                http_request=http_request,
                response=Response(),
                db=AsyncMock(),
                redis_client=AsyncMock(),
                auth_service=auth_service,
            )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == REGISTRATION_DISABLED_CODE
    assert exc_info.value.detail["channel"] == "magic_link"
    user_repo.create.assert_not_called()
    auth_service.hash_password.assert_not_awaited()
