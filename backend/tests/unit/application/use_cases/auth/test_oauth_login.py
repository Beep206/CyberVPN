"""Unit tests for OAuthLoginUseCase.

Tests the three login paths (existing linked account, auto-link by email,
new user creation), 2FA gating, token issuance, and error handling.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.use_cases.auth.oauth_login import OAuthLoginResult, OAuthLoginUseCase


class TestOAuthLoginUseCase:
    """Tests for OAuthLoginUseCase.execute()."""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock AdminUserRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_oauth_repo(self):
        """Mock OAuthAccountRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_auth_service(self):
        """Mock AuthService with token creation methods."""
        service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        refresh_exp = datetime.now(UTC) + timedelta(days=7)
        service.create_access_token.return_value = ("access_token_value", "jti_a", access_exp)
        service.create_refresh_token.return_value = ("refresh_token_value", "jti_r", refresh_exp)
        service.hash_password = AsyncMock(return_value="$argon2id$hashed_random_password")
        return service

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        return AsyncMock()

    @pytest.fixture
    def make_user(self):
        """Factory for creating mock user objects."""

        def _make(
            user_id=None,
            role="viewer",
            totp_enabled=False,
            login="testuser",
            email="test@example.com",
        ):
            user = MagicMock()
            user.id = user_id or uuid4()
            user.role = role
            user.totp_enabled = totp_enabled
            user.login = login
            user.email = email
            return user

        return _make

    # ------------------------------------------------------------------
    # Path 1: Existing OAuth account login
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_existing_oauth_account_login_returns_tokens(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Login via existing linked OAuth account returns JWT tokens."""
        # Arrange
        user = make_user()
        oauth_account = MagicMock()
        oauth_account.user_id = user.id

        mock_oauth_repo.get_by_provider_and_user_id.return_value = oauth_account
        mock_user_repo.get_by_id.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        # Act
        result = await use_case.execute(
            provider="google",
            user_info={"id": "g123", "email": "test@gmail.com", "username": "test", "access_token": "provider_tok"},
        )

        # Assert
        assert result.access_token == "access_token_value"
        assert result.refresh_token == "refresh_token_value"
        assert result.token_type == "bearer"
        assert result.is_new_user is False
        assert result.requires_2fa is False
        assert result.user is user

    @pytest.mark.unit
    async def test_existing_oauth_account_updates_provider_tokens(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Existing linked account updates stored provider tokens on login."""
        user = make_user()
        oauth_account = MagicMock()
        oauth_account.user_id = user.id

        mock_oauth_repo.get_by_provider_and_user_id.return_value = oauth_account
        mock_user_repo.get_by_id.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={
                "id": "g123",
                "email": "test@gmail.com",
                "username": "newname",
                "avatar_url": "https://new-avatar.jpg",
                "access_token": "new_provider_token",
                "refresh_token": "new_provider_refresh",
            },
        )

        assert oauth_account.access_token == "new_provider_token"
        assert oauth_account.refresh_token == "new_provider_refresh"
        assert oauth_account.provider_username == "newname"
        assert oauth_account.provider_avatar_url == "https://new-avatar.jpg"
        mock_oauth_repo.update.assert_called_once_with(oauth_account)

    @pytest.mark.unit
    async def test_existing_oauth_account_missing_user_raises_error(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session
    ):
        """Linked OAuth account whose user was deleted raises ValueError."""
        oauth_account = MagicMock()
        oauth_account.user_id = uuid4()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = oauth_account
        mock_user_repo.get_by_id.return_value = None  # User deleted

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        with pytest.raises(ValueError, match="Linked user account not found"):
            await use_case.execute(
                provider="google",
                user_info={"id": "g123", "email": "gone@gmail.com", "access_token": "tok"},
            )

    # ------------------------------------------------------------------
    # Path 2: Auto-link by email
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_auto_link_by_email_creates_oauth_account(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """User found by email gets a new OAuth account link created."""
        user = make_user(email="existing@example.com")

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None  # No existing link
        mock_user_repo.get_by_email.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(
            provider="discord",
            user_info={
                "id": "d456",
                "email": "existing@example.com",
                "username": "discorduser",
                "access_token": "tok",
            },
        )

        assert result.is_new_user is False
        assert result.user is user
        mock_oauth_repo.create.assert_called_once()

        # Verify the OAuth account was created with correct provider info
        created_account = mock_oauth_repo.create.call_args.args[0]
        assert created_account.provider == "discord"
        assert created_account.provider_user_id == "d456"
        assert created_account.user_id == user.id

    @pytest.mark.unit
    async def test_auto_link_commits_session(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Auto-link flow commits the database session."""
        user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "123", "email": user.email, "access_token": "tok"},
        )

        mock_session.commit.assert_called_once()

    # ------------------------------------------------------------------
    # Path 3: Create new user
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_create_new_user_when_no_existing_account(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """New user is created when no OAuth link and no email match."""
        new_user = make_user(role="viewer")

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None  # No email match
        mock_user_repo.get_by_login.return_value = None  # Login is available
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(
            provider="discord",
            user_info={
                "id": "d789",
                "email": "brand_new@discord.com",
                "username": "newguy",
                "access_token": "tok",
            },
        )

        assert result.is_new_user is True
        assert result.user is new_user
        mock_user_repo.create.assert_called_once()
        mock_oauth_repo.create.assert_called_once()

    @pytest.mark.unit
    async def test_create_new_user_uses_username_as_login(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """New user login is derived from the provider username."""
        new_user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="discord",
            user_info={
                "id": "d789",
                "email": "new@discord.com",
                "username": "coolname",
                "access_token": "tok",
            },
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "coolname"

    @pytest.mark.unit
    async def test_create_new_user_deduplicates_login(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Login gets a random suffix appended when username already exists."""
        new_user = make_user()
        existing_user = make_user(login="taken_name")

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = existing_user  # Login is taken
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={
                "id": "g999",
                "email": "new@gmail.com",
                "username": "taken_name",
                "access_token": "tok",
            },
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login.startswith("taken_name_")
        assert len(created_user.login) > len("taken_name_")

    @pytest.mark.unit
    async def test_create_new_user_without_email_generates_login(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """User with no email and no username gets a generated login (user_xxxx)."""
        new_user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="twitter",
            user_info={
                "id": "tw111",
                "email": None,
                "username": None,
                "access_token": "tok",
            },
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login.startswith("user_")

    @pytest.mark.unit
    async def test_create_new_user_falls_back_to_email_prefix_for_login(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """When no username but email is present, login is the email prefix."""
        new_user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={
                "id": "g555",
                "email": "alice@gmail.com",
                "username": None,
                "access_token": "tok",
            },
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "alice"

    @pytest.mark.unit
    async def test_create_new_user_sets_email_verified_when_email_present(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """New user with email from OAuth has is_email_verified=True."""
        new_user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "g1", "email": "verified@gmail.com", "access_token": "tok"},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.is_email_verified is True
        assert created_user.is_active is True

    @pytest.mark.unit
    async def test_create_new_user_unverified_when_no_email(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """New user without email has is_email_verified=False."""
        new_user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="twitter",
            user_info={"id": "tw1", "email": None, "access_token": "tok"},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.is_email_verified is False

    @pytest.mark.unit
    async def test_create_new_user_hashes_random_password(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """New user gets a hashed random password (not usable for password login)."""
        new_user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "g1", "email": "new@gmail.com", "access_token": "tok"},
        )

        mock_auth_service.hash_password.assert_called_once()
        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.password_hash == "$argon2id$hashed_random_password"

    # ------------------------------------------------------------------
    # 2FA gate
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_totp_enabled_returns_2fa_pending_result(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """User with TOTP enabled gets requires_2fa=True and empty tokens."""
        user = make_user(totp_enabled=True)

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = user

        # Override create_access_token for 2FA pending token
        tfa_access_exp = datetime.now(UTC) + timedelta(minutes=5)
        mock_auth_service.create_access_token.return_value = ("2fa_pending_tok", "jti_2fa", tfa_access_exp)

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(
            provider="google",
            user_info={"id": "g2fa", "email": user.email, "access_token": "tok"},
        )

        assert result.requires_2fa is True
        assert result.tfa_token == "2fa_pending_tok"
        assert result.access_token == ""
        assert result.refresh_token == ""
        assert result.expires_in == 0

    @pytest.mark.unit
    async def test_totp_enabled_calls_create_token_with_2fa_pending_role(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """2FA pending token is created with role='2fa_pending'."""
        user = make_user(totp_enabled=True)

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = user

        tfa_exp = datetime.now(UTC) + timedelta(minutes=5)
        mock_auth_service.create_access_token.return_value = ("tfa_tok", "jti", tfa_exp)

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "g2fa", "email": user.email, "access_token": "tok"},
        )

        mock_auth_service.create_access_token.assert_called_once_with(
            subject=str(user.id),
            role="2fa_pending",
            extra={"type": "2fa_pending"},
        )

    # ------------------------------------------------------------------
    # Token issuance
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_jwt_tokens_issued_with_correct_subject_and_role(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """JWT tokens are created with the user's ID as subject and role."""
        user = make_user(role="admin")

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "g_admin", "email": user.email, "access_token": "tok"},
        )

        mock_auth_service.create_access_token.assert_called_once_with(
            subject=str(user.id),
            role="admin",
        )
        mock_auth_service.create_refresh_token.assert_called_once_with(
            subject=str(user.id),
            fingerprint=None,
        )

    @pytest.mark.unit
    async def test_client_fingerprint_passed_to_refresh_token(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Client fingerprint is forwarded to refresh token creation."""
        user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "g1", "email": user.email, "access_token": "tok"},
            client_fingerprint="device_fp_abc123",
        )

        mock_auth_service.create_refresh_token.assert_called_once_with(
            subject=str(user.id),
            fingerprint="device_fp_abc123",
        )

    @pytest.mark.unit
    async def test_expires_in_calculated_from_access_token_expiry(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """expires_in is calculated as seconds until access token expiry."""
        user = make_user()

        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = user

        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        mock_auth_service.create_access_token.return_value = ("tok", "jti", access_exp)
        mock_auth_service.create_refresh_token.return_value = (
            "rtok",
            "rjti",
            datetime.now(UTC) + timedelta(days=7),
        )

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(
            provider="google",
            user_info={"id": "g1", "email": user.email, "access_token": "tok"},
        )

        # expires_in should be approximately 900 seconds (15 min), allow some tolerance
        assert 850 < result.expires_in <= 900

    # ------------------------------------------------------------------
    # Email conflict / auto-link for different provider
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_email_conflict_auto_links_different_provider(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Email already linked to a different OAuth provider auto-links successfully.

        When a user already has a GitHub OAuth account and logs in via Google
        with the same email, the auto-link path creates a new OAuth record
        for the existing user rather than raising a conflict.
        """
        existing_user = make_user(email="conflict@example.com")
        existing_oauth = MagicMock()
        existing_oauth.provider = "github"
        existing_oauth.user_id = existing_user.id

        # No existing link for THIS provider+user combination
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        # User found by email (auto-link path)
        mock_user_repo.get_by_email.return_value = existing_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(
            provider="google",
            user_info={"id": "g_conflict", "email": "conflict@example.com", "access_token": "tok"},
        )

        # The auto-link path should succeed, not raise a conflict
        assert result.is_new_user is False
        assert result.user is existing_user
        mock_oauth_repo.create.assert_called_once()


class TestTelegramOAuthLogin:
    """Tests for Telegram-specific OAuth login behavior."""

    @pytest.fixture
    def mock_user_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_oauth_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_auth_service(self):
        service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        refresh_exp = datetime.now(UTC) + timedelta(days=7)
        service.create_access_token.return_value = ("access_token_value", "jti_a", access_exp)
        service.create_refresh_token.return_value = ("refresh_token_value", "jti_r", refresh_exp)
        service.hash_password = AsyncMock(return_value="$argon2id$hashed")
        return service

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def make_user(self):
        def _make(user_id=None, role="viewer", totp_enabled=False, login="testuser", email="test@example.com"):
            user = MagicMock()
            user.id = user_id or uuid4()
            user.role = role
            user.totp_enabled = totp_enabled
            user.login = login
            user.email = email
            return user
        return _make

    @pytest.fixture
    def telegram_user_info(self):
        """Standard Telegram user_info dict."""
        return {
            "id": "123456789",
            "username": "johndoe",
            "first_name": "John",
            "access_token": "",
        }

    # ------------------------------------------------------------------
    # kpn9.7.1: Telegram creates user with is_email_verified=True, is_active=True
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_telegram_creates_user_with_email_verified_true(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user, telegram_user_info
    ):
        """Telegram OAuth creates user with is_email_verified=True (no email needed)."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(provider="telegram", user_info=telegram_user_info)

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.is_email_verified is True

    @pytest.mark.unit
    async def test_telegram_creates_user_with_is_active_true(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user, telegram_user_info
    ):
        """Telegram OAuth creates user with is_active=True."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(provider="telegram", user_info=telegram_user_info)

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.is_active is True

    @pytest.mark.unit
    async def test_telegram_without_email_still_sets_verified_true(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Telegram user without email still gets is_email_verified=True (unlike other providers)."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="telegram",
            user_info={"id": "999", "first_name": "NoEmail", "access_token": ""},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.is_email_verified is True

    # ------------------------------------------------------------------
    # kpn9.7.2: Telegram OAuth skips OTP dispatch
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_telegram_does_not_dispatch_otp(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user, telegram_user_info
    ):
        """Telegram OAuth flow never dispatches OTP — tokens are issued directly."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(provider="telegram", user_info=telegram_user_info)

        # OAuthLoginUseCase never calls OTP — it issues tokens directly
        assert result.access_token == "access_token_value"
        assert result.refresh_token == "refresh_token_value"
        assert result.is_new_user is True

    # ------------------------------------------------------------------
    # kpn9.7.3: Username generation from @tg_username / first_name / fallback
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_telegram_username_from_tg_username(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Telegram login uses @telegram_username when available."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="telegram",
            user_info={"id": "111", "username": "alice_bot", "first_name": "Alice", "access_token": ""},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "alice_bot"

    @pytest.mark.unit
    async def test_telegram_username_fallback_to_first_name(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Telegram login falls back to first_name when username is absent."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="telegram",
            user_info={"id": "222", "username": None, "first_name": "Dmitry", "access_token": ""},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "Dmitry"

    @pytest.mark.unit
    async def test_telegram_username_fallback_to_tg_id(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Telegram login falls back to tg_{id} when both username and first_name are absent."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="telegram",
            user_info={"id": "333444555", "access_token": ""},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "tg_333444555"

    @pytest.mark.unit
    async def test_telegram_username_sanitizes_special_chars(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Telegram username with special chars is sanitized to alphanumeric+underscore."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="telegram",
            user_info={"id": "444", "username": "cool.user-name!", "first_name": "Cool", "access_token": ""},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "coolusername"

    @pytest.mark.unit
    async def test_telegram_short_username_falls_back_to_first_name(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Telegram username shorter than 3 chars falls back to first_name."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="telegram",
            user_info={"id": "555", "username": "ab", "first_name": "Alexander", "access_token": ""},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "Alexander"

    # ------------------------------------------------------------------
    # kpn9.7.4: is_new_user=true for new, false for existing
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_telegram_new_user_returns_is_new_user_true(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user, telegram_user_info
    ):
        """Telegram OAuth returns is_new_user=True for new registrations."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(provider="telegram", user_info=telegram_user_info)

        assert result.is_new_user is True

    @pytest.mark.unit
    async def test_telegram_existing_user_returns_is_new_user_false(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user, telegram_user_info
    ):
        """Telegram OAuth returns is_new_user=False for existing linked accounts."""
        user = make_user()
        oauth_account = MagicMock()
        oauth_account.user_id = user.id

        mock_oauth_repo.get_by_provider_and_user_id.return_value = oauth_account
        mock_user_repo.get_by_id.return_value = user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(provider="telegram", user_info=telegram_user_info)

        assert result.is_new_user is False

    # ------------------------------------------------------------------
    # kpn9.7.5: Non-Telegram providers still follow standard flow (regression)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_google_oauth_no_email_sets_verified_false(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Non-Telegram provider without email sets is_email_verified=False (unlike Telegram)."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="twitter",
            user_info={"id": "tw1", "email": None, "access_token": "tok"},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.is_email_verified is False

    @pytest.mark.unit
    async def test_google_oauth_uses_username_not_telegram_logic(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Non-Telegram provider uses username directly (not _generate_telegram_login)."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        await use_case.execute(
            provider="google",
            user_info={"id": "g1", "email": "test@gmail.com", "username": "googleuser", "access_token": "tok"},
        )

        created_user = mock_user_repo.create.call_args.args[0]
        assert created_user.login == "googleuser"

    @pytest.mark.unit
    async def test_discord_new_user_still_returns_is_new_user_true(
        self, mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session, make_user
    ):
        """Non-Telegram provider still returns is_new_user=True for new registrations."""
        new_user = make_user()
        mock_oauth_repo.get_by_provider_and_user_id.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_login.return_value = None
        mock_user_repo.create.return_value = new_user

        use_case = OAuthLoginUseCase(mock_user_repo, mock_oauth_repo, mock_auth_service, mock_session)

        result = await use_case.execute(
            provider="discord",
            user_info={"id": "d1", "email": "disc@test.com", "username": "discuser", "access_token": "tok"},
        )

        assert result.is_new_user is True


class TestGenerateTelegramLogin:
    """Tests for OAuthLoginUseCase._generate_telegram_login static method."""

    def test_prefers_username(self):
        login = OAuthLoginUseCase._generate_telegram_login(username="alice", first_name="Alice", telegram_id="123")
        assert login == "alice"

    def test_sanitizes_username(self):
        login = OAuthLoginUseCase._generate_telegram_login(username="cool.user!", first_name=None, telegram_id="123")
        assert login == "cooluser"

    def test_rejects_short_username(self):
        login = OAuthLoginUseCase._generate_telegram_login(username="ab", first_name="Alexander", telegram_id="123")
        assert login == "Alexander"

    def test_falls_back_to_first_name(self):
        login = OAuthLoginUseCase._generate_telegram_login(username=None, first_name="Dmitry", telegram_id="123")
        assert login == "Dmitry"

    def test_first_name_with_spaces(self):
        login = OAuthLoginUseCase._generate_telegram_login(username=None, first_name="John Doe", telegram_id="123")
        assert login == "John_Doe"

    def test_falls_back_to_tg_id(self):
        login = OAuthLoginUseCase._generate_telegram_login(username=None, first_name=None, telegram_id="999")
        assert login == "tg_999"

    def test_truncates_long_first_name(self):
        login = OAuthLoginUseCase._generate_telegram_login(username=None, first_name="A" * 50, telegram_id="123")
        assert len(login) == 32

    def test_short_first_name_falls_back_to_tg_id(self):
        login = OAuthLoginUseCase._generate_telegram_login(username=None, first_name="AB", telegram_id="456")
        assert login == "tg_456"


class TestOAuthLoginResult:
    """Tests for the OAuthLoginResult dataclass."""

    @pytest.mark.unit
    def test_result_stores_all_fields(self):
        """OAuthLoginResult stores all provided fields correctly."""
        user = MagicMock()
        result = OAuthLoginResult(
            access_token="at",
            refresh_token="rt",
            token_type="bearer",
            expires_in=900,
            user=user,
            is_new_user=True,
            requires_2fa=False,
            tfa_token=None,
        )

        assert result.access_token == "at"
        assert result.refresh_token == "rt"
        assert result.token_type == "bearer"
        assert result.expires_in == 900
        assert result.user is user
        assert result.is_new_user is True
        assert result.requires_2fa is False
        assert result.tfa_token is None

    @pytest.mark.unit
    def test_result_defaults(self):
        """OAuthLoginResult defaults requires_2fa=False and tfa_token=None."""
        user = MagicMock()
        result = OAuthLoginResult(
            access_token="at",
            refresh_token="rt",
            token_type="bearer",
            expires_in=900,
            user=user,
            is_new_user=False,
        )

        assert result.requires_2fa is False
        assert result.tfa_token is None
