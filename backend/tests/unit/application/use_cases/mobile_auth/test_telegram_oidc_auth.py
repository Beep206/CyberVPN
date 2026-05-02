"""Unit tests for MobileTelegramOIDCAuthUseCase."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.telegram_oidc_auth import TelegramOIDCUserInfo
from src.application.use_cases.mobile_auth.telegram_oidc_auth import MobileTelegramOIDCAuthUseCase


class TestMobileTelegramOIDCAuthUseCase:
    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        repo.get_by_telegram_subject.return_value = None
        repo.get_by_telegram_id.return_value = None
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_device_repo(self):
        repo = AsyncMock()
        repo.get_by_device_id_and_user.return_value = None
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_auth_service(self):
        service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        refresh_exp = datetime.now(UTC) + timedelta(days=7)
        service.create_access_token.return_value = ("access_token_value", "jti_a", access_exp)
        service.create_refresh_token.return_value = ("refresh_token_value", "jti_r", refresh_exp)
        service.hash_password = AsyncMock(return_value="$argon2id$synthetic_hash")
        return service

    @pytest.fixture
    def mock_telegram_service(self):
        service = AsyncMock()
        service.validate_id_token.return_value = TelegramOIDCUserInfo(
            subject="telegram-subject",
            telegram_id=123456789,
            name="Telegram User",
            preferred_username="telegram_user",
            picture=None,
            phone_number=None,
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        return service

    @pytest.fixture
    def device_request(self):
        device = MagicMock()
        device.device_id = "123e4567-e89b-12d3-a456-426614174000"
        device.platform.value = "ios"
        device.platform_id = "ios-vendor-id"
        device.os_version = "17.4"
        device.app_version = "1.2.3"
        device.device_model = "iPhone 15 Pro"
        device.push_token = None
        return device

    @pytest.fixture
    def request_dto(self, device_request):
        dto = MagicMock()
        dto.id_token = "id-token"
        dto.device = device_request
        return dto

    @pytest.fixture
    def make_user(self):
        def _make():
            user = MagicMock()
            user.id = uuid4()
            user.email = "existing@example.com"
            user.username = "existing_user"
            user.status = "active"
            user.telegram_subject = "telegram-subject"
            user.telegram_id = 123456789
            user.telegram_username = "telegram_user"
            user.created_at = datetime.now(UTC)
            user.last_login_at = None
            user.auth_realm_id = None
            user.remnawave_uuid = None
            user.totp_enabled = False
            user.totp_secret = None
            return user

        return _make

    @pytest.mark.unit
    async def test_existing_user_by_subject_reuses_account(
        self,
        mock_user_repo,
        mock_device_repo,
        mock_auth_service,
        mock_telegram_service,
        request_dto,
        make_user,
    ):
        user = make_user()
        mock_user_repo.get_by_telegram_subject.return_value = user

        use_case = MobileTelegramOIDCAuthUseCase(
            user_repo=mock_user_repo,
            device_repo=mock_device_repo,
            auth_service=mock_auth_service,
            telegram_oidc_service=mock_telegram_service,
        )

        result, is_new_user = await use_case.execute(request_dto)

        assert is_new_user is False
        assert result.user.id == user.id
        mock_user_repo.get_by_telegram_id.assert_not_awaited()
        mock_user_repo.create.assert_not_awaited()

    @pytest.mark.unit
    async def test_existing_user_by_telegram_id_backfills_subject(
        self,
        mock_user_repo,
        mock_device_repo,
        mock_auth_service,
        mock_telegram_service,
        request_dto,
        make_user,
    ):
        user = make_user()
        user.telegram_subject = None
        mock_user_repo.get_by_telegram_subject.return_value = None
        mock_user_repo.get_by_telegram_id.return_value = user

        use_case = MobileTelegramOIDCAuthUseCase(
            user_repo=mock_user_repo,
            device_repo=mock_device_repo,
            auth_service=mock_auth_service,
            telegram_oidc_service=mock_telegram_service,
        )

        await use_case.execute(request_dto)

        assert user.telegram_subject == "telegram-subject"
        mock_user_repo.update.assert_awaited()

    @pytest.mark.unit
    async def test_new_user_creation_uses_synthetic_password_hash(
        self,
        mock_user_repo,
        mock_device_repo,
        mock_auth_service,
        mock_telegram_service,
        request_dto,
        make_user,
    ):
        created_user = make_user()
        created_user.email = "tg123456789@telegram.local"
        mock_user_repo.create.return_value = created_user

        use_case = MobileTelegramOIDCAuthUseCase(
            user_repo=mock_user_repo,
            device_repo=mock_device_repo,
            auth_service=mock_auth_service,
            telegram_oidc_service=mock_telegram_service,
        )

        result, is_new_user = await use_case.execute(request_dto)

        assert is_new_user is True
        created_model = mock_user_repo.create.await_args.args[0]
        assert created_model.password_hash == "$argon2id$synthetic_hash"
        assert created_model.telegram_subject == "telegram-subject"
        assert created_model.email == "tg123456789@telegram.local"
        assert result.is_new_user is True

    @pytest.mark.unit
    async def test_existing_user_with_totp_returns_pending_2fa_response(
        self,
        mock_user_repo,
        mock_device_repo,
        mock_auth_service,
        mock_telegram_service,
        request_dto,
        make_user,
    ):
        user = make_user()
        user.totp_enabled = True
        user.totp_secret = "encrypted-secret"
        mock_user_repo.get_by_telegram_subject.return_value = user
        pending_exp = datetime.now(UTC) + timedelta(minutes=15)
        mock_auth_service.create_access_token.return_value = ("pending-2fa-token", "jti_pending", pending_exp)

        use_case = MobileTelegramOIDCAuthUseCase(
            user_repo=mock_user_repo,
            device_repo=mock_device_repo,
            auth_service=mock_auth_service,
            telegram_oidc_service=mock_telegram_service,
        )

        result, is_new_user = await use_case.execute(request_dto)

        assert is_new_user is False
        assert result.requires_2fa is True
        assert result.tfa_token == "pending-2fa-token"
        assert result.method == "totp"
        assert result.tokens is None
        assert result.user is None
        mock_device_repo.create.assert_not_awaited()
