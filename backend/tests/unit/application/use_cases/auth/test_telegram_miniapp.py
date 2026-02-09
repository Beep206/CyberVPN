"""Unit tests for TelegramMiniAppUseCase."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.use_cases.auth.telegram_miniapp import (
    TelegramMiniAppResult,
    TelegramMiniAppUseCase,
)


class TestTelegramMiniAppUseCase:
    """Tests for TelegramMiniAppUseCase.execute()."""

    @pytest.fixture
    def mock_user_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_auth_service(self):
        service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        refresh_exp = datetime.now(UTC) + timedelta(days=7)
        service.create_access_token.return_value = ("access_tok", "jti_a", access_exp)
        service.create_refresh_token.return_value = ("refresh_tok", "jti_r", refresh_exp)
        service.hash_password = AsyncMock(return_value="$argon2id$hashed")
        return service

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def mock_telegram_provider(self):
        provider = MagicMock()
        provider.validate_init_data.return_value = {
            "id": "123456789",
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "photo_url": None,
            "language_code": "en",
        }
        return provider

    @pytest.fixture
    def make_user(self):
        def _make(user_id=None, login="testuser", telegram_id=123456789, is_active=True, role="viewer"):
            user = MagicMock()
            user.id = user_id or uuid4()
            user.login = login
            user.email = None
            user.telegram_id = telegram_id
            user.role = role
            user.is_active = is_active
            user.is_email_verified = True
            user.created_at = datetime.now(UTC)
            user.totp_enabled = False
            return user
        return _make

    @pytest.fixture
    def use_case(self, mock_user_repo, mock_auth_service, mock_session, mock_telegram_provider):
        return TelegramMiniAppUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            session=mock_session,
            telegram_provider=mock_telegram_provider,
        )

    @pytest.mark.unit
    async def test_existing_user_login(self, use_case, mock_user_repo, make_user):
        existing = make_user()
        mock_user_repo.get_by_telegram_id.return_value = existing

        result = await use_case.execute("valid_init_data")

        assert isinstance(result, TelegramMiniAppResult)
        assert result.is_new_user is False
        assert result.access_token == "access_tok"
        assert result.user == existing
        mock_user_repo.create.assert_not_called()

    @pytest.mark.unit
    async def test_new_user_auto_register(self, use_case, mock_user_repo, make_user):
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.get_by_login.return_value = None
        new_user = make_user()
        mock_user_repo.create.return_value = new_user

        result = await use_case.execute("valid_init_data")

        assert result.is_new_user is True
        assert result.access_token == "access_tok"
        mock_user_repo.create.assert_called_once()

    @pytest.mark.unit
    async def test_new_user_gets_unique_login(self, use_case, mock_user_repo, make_user):
        mock_user_repo.get_by_telegram_id.return_value = None
        # First login check returns existing user (collision)
        mock_user_repo.get_by_login.return_value = make_user()
        new_user = make_user()
        mock_user_repo.create.return_value = new_user

        result = await use_case.execute("valid_init_data")

        assert result.is_new_user is True
        # The created user's login should have been modified with hex suffix
        created_model = mock_user_repo.create.call_args[0][0]
        assert "_" in created_model.login and len(created_model.login) > len("testuser")

    @pytest.mark.unit
    async def test_invalid_init_data_raises(self, use_case, mock_telegram_provider):
        mock_telegram_provider.validate_init_data.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired"):
            await use_case.execute("bad_data")

    @pytest.mark.unit
    async def test_missing_telegram_id_raises(self, use_case, mock_telegram_provider):
        mock_telegram_provider.validate_init_data.return_value = {
            "id": "",
            "first_name": "Test",
            "username": None,
            "last_name": None,
            "photo_url": None,
            "language_code": None,
        }

        with pytest.raises(ValueError, match="user ID missing"):
            await use_case.execute("some_data")

    @pytest.mark.unit
    async def test_new_user_is_active_and_verified(self, use_case, mock_user_repo, make_user):
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = make_user()

        await use_case.execute("valid_init_data")

        created_model = mock_user_repo.create.call_args[0][0]
        assert created_model.is_active is True
        assert created_model.is_email_verified is True

    @pytest.mark.unit
    async def test_remnawave_called_for_new_user(
        self, mock_user_repo, mock_auth_service, mock_session, mock_telegram_provider, make_user
    ):
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = make_user()

        remnawave = AsyncMock()
        uc = TelegramMiniAppUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            session=mock_session,
            telegram_provider=mock_telegram_provider,
            remnawave_gateway=remnawave,
        )

        await uc.execute("valid_init_data")

        remnawave.create_user.assert_called_once()

    @pytest.mark.unit
    async def test_remnawave_failure_non_fatal(
        self, mock_user_repo, mock_auth_service, mock_session, mock_telegram_provider, make_user
    ):
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = make_user()

        remnawave = AsyncMock()
        remnawave.create_user.side_effect = RuntimeError("API down")
        uc = TelegramMiniAppUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            session=mock_session,
            telegram_provider=mock_telegram_provider,
            remnawave_gateway=remnawave,
        )

        # Should not raise
        result = await uc.execute("valid_init_data")
        assert result.is_new_user is True

    @pytest.mark.unit
    async def test_remnawave_not_called_for_existing_user(
        self, mock_user_repo, mock_auth_service, mock_session, mock_telegram_provider, make_user
    ):
        mock_user_repo.get_by_telegram_id.return_value = make_user()

        remnawave = AsyncMock()
        uc = TelegramMiniAppUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            session=mock_session,
            telegram_provider=mock_telegram_provider,
            remnawave_gateway=remnawave,
        )

        await uc.execute("valid_init_data")
        remnawave.create_user.assert_not_called()

    @pytest.mark.unit
    async def test_session_committed(self, use_case, mock_user_repo, mock_session, make_user):
        mock_user_repo.get_by_telegram_id.return_value = make_user()

        await use_case.execute("valid_init_data")

        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    async def test_new_user_sets_telegram_id(self, use_case, mock_user_repo, make_user):
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = make_user()

        await use_case.execute("valid_init_data")

        created_model = mock_user_repo.create.call_args[0][0]
        assert created_model.telegram_id == 123456789
