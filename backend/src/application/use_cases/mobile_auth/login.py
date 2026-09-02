"""Mobile user login use case.

Handles authentication of mobile app users with credential validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    LoginRequestDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
)
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.application.services.remnawave_identity_access import resolve_exact_mapped_mobile_user_ref
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)

if TYPE_CHECKING:
    from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient


@dataclass
class MobileLoginUseCase:
    """Use case for authenticating mobile app users.

    Validates credentials, updates device info, and returns authentication tokens.
    Supports extended refresh token TTL with remember_me option.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    subscription_client: CachedSubscriptionClient | None = None
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(self, request: LoginRequestDTO) -> AuthResponseDTO:
        """Authenticate a mobile user.

        Args:
            request: Login request with email, password, device info, and remember_me flag.

        Returns:
            AuthResponseDTO with tokens and user data.

        Raises:
            InvalidCredentialsError: If email not found or password incorrect.
        """
        # Find user by email
        user = await self.user_repo.get_by_email(request.email)
        if not user:
            raise InvalidCredentialsError()

        # Verify password
        is_valid = await self.auth_service.verify_password_async(request.password, user.password_hash)
        if not is_valid:
            raise InvalidCredentialsError()

        # Check account status
        if not user.is_active:
            raise InvalidCredentialsError()

        user_ref = await resolve_exact_mapped_mobile_user_ref(self.session, user)

        # Update last login timestamp
        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        tokens = await self._mobile_sessions().issue_session(
            user=user,
            device=request.device,
            remember_me=request.remember_me,
        )

        # Fetch an exact identity-bound subscription; dependency failures are
        # surfaced rather than converted into an empty entitlement.
        if self.subscription_client and user_ref is not None:
            subscription = await self.subscription_client.get_subscription(user_ref)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        user_response = build_mobile_user_response(user, subscription=subscription)

        return AuthResponseDTO(
            tokens=tokens,
            user=user_response,
            is_new_user=False,
        )

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileLoginUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
