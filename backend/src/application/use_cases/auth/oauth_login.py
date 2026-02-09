"""OAuth login use case - find or create user from OAuth provider data."""

import logging
import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.oauth_account_model import OAuthAccount
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.oauth_account_repo import OAuthAccountRepository

logger = logging.getLogger(__name__)


class OAuthLoginResult:
    """Result of OAuth login."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        token_type: str,
        expires_in: int,
        user: AdminUserModel,
        is_new_user: bool,
        requires_2fa: bool = False,
        tfa_token: str | None = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.user = user
        self.is_new_user = is_new_user
        self.requires_2fa = requires_2fa
        self.tfa_token = tfa_token


class OAuthLoginUseCase:
    """Handles OAuth login: find or create user, link provider, issue tokens."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        oauth_repo: OAuthAccountRepository,
        auth_service: AuthService,
        session: AsyncSession,
    ) -> None:
        self._user_repo = user_repo
        self._oauth_repo = oauth_repo
        self._auth_service = auth_service
        self._session = session

    async def execute(
        self,
        provider: str,
        user_info: dict,
        client_fingerprint: str | None = None,
    ) -> OAuthLoginResult:
        """Execute OAuth login flow.

        Args:
            provider: OAuth provider name (google, discord, apple, etc.)
            user_info: Normalized dict from OAuth provider with keys:
                id, email, username, name, avatar_url, access_token, refresh_token
            client_fingerprint: Optional device fingerprint for token binding

        Returns:
            OAuthLoginResult with tokens and user

        Raises:
            ValueError: If email conflict detected
        """
        provider_user_id = str(user_info["id"])
        email = user_info.get("email")
        username = user_info.get("username")
        avatar_url = user_info.get("avatar_url")
        provider_access_token = user_info.get("access_token", "")
        provider_refresh_token = user_info.get("refresh_token")

        is_new_user = False

        # Step 1: Check if OAuth account already exists (provider + provider_user_id)
        oauth_account = await self._oauth_repo.get_by_provider_and_user_id(provider, provider_user_id)

        if oauth_account:
            # Existing linked account - login as that user
            user = await self._user_repo.get_by_id(oauth_account.user_id)
            if not user:
                raise ValueError("Linked user account not found")

            # Update provider tokens
            oauth_account.access_token = provider_access_token
            if provider_refresh_token:
                oauth_account.refresh_token = provider_refresh_token
            if username:
                oauth_account.provider_username = username
            if avatar_url:
                oauth_account.provider_avatar_url = avatar_url
            await self._oauth_repo.update(oauth_account)

            logger.info(
                "OAuth login via existing linked account",
                extra={"provider": provider, "user_id": str(user.id)},
            )
        else:
            # Step 2: Check if user exists by email (auto-link)
            user = None
            if email:
                user = await self._user_repo.get_by_email(email)

            if user:
                # Auto-link OAuth to existing user
                logger.info(
                    "Auto-linking OAuth to existing user by email",
                    extra={"provider": provider, "email": email, "user_id": str(user.id)},
                )
            else:
                # Step 3: Create new user
                login = username or (email.split("@")[0] if email else f"user_{secrets.token_hex(4)}")

                # Ensure login is unique
                existing = await self._user_repo.get_by_login(login)
                if existing:
                    login = f"{login}_{secrets.token_hex(3)}"

                password_hash = await self._auth_service.hash_password(secrets.token_urlsafe(32))
                user = AdminUserModel(
                    login=login,
                    email=email,
                    password_hash=password_hash,
                    role="viewer",
                    is_active=True,
                    is_email_verified=email is not None,
                )
                user = await self._user_repo.create(user)
                is_new_user = True

                logger.info(
                    "Created new user from OAuth login",
                    extra={"provider": provider, "user_id": str(user.id), "login": login},
                )

            # Create OAuth account link
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_username=username,
                provider_email=email,
                provider_avatar_url=avatar_url,
                access_token=provider_access_token,
                refresh_token=provider_refresh_token,
            )
            await self._oauth_repo.create(oauth_account)

        # Commit the transaction
        await self._session.commit()

        # 2FA gate: if user has TOTP enabled, return partial response
        if user.totp_enabled:
            tfa_token, _, _ = self._auth_service.create_access_token(
                subject=str(user.id),
                role="2fa_pending",
                extra={"type": "2fa_pending"},
            )
            logger.info(
                "OAuth login requires 2FA verification",
                extra={"provider": provider, "user_id": str(user.id)},
            )
            return OAuthLoginResult(
                access_token="",
                refresh_token="",
                token_type="bearer",
                expires_in=0,
                user=user,
                is_new_user=is_new_user,
                requires_2fa=True,
                tfa_token=tfa_token,
            )

        # Issue JWT tokens
        access_token, _, access_exp = self._auth_service.create_access_token(
            subject=str(user.id),
            role=user.role if isinstance(user.role, str) else user.role.value,
        )
        refresh_token, _, _ = self._auth_service.create_refresh_token(
            subject=str(user.id),
            fingerprint=client_fingerprint,
        )
        expires_in = int((access_exp - datetime.now(UTC)).total_seconds())

        return OAuthLoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
            is_new_user=is_new_user,
        )
