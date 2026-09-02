"""Complete a mobile login paused behind TOTP verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    DeviceInfoDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
)
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.application.services.remnawave_identity_access import resolve_exact_mapped_mobile_user_ref
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
from src.domain.exceptions import ValidationError
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)
from src.infrastructure.totp.totp_service import TOTPService

if TYPE_CHECKING:
    from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient


@dataclass
class MobileCompleteTwoFactorUseCase:
    """Verify a pending mobile TOTP challenge and issue a first-party session."""

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    totp_service: TOTPService
    subscription_client: CachedSubscriptionClient | None = None
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(
        self,
        *,
        user: MobileUserModel,
        code: str,
        device: DeviceInfoDTO,
    ) -> AuthResponseDTO:
        if not user.totp_enabled or not user.totp_secret:
            raise ValidationError("Two-factor authentication is not enabled for this account")

        if not self.totp_service.verify_code(user.totp_secret, code):
            raise ValidationError("Invalid verification code")

        user_ref = await resolve_exact_mapped_mobile_user_ref(self.session, user)

        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        tokens = await self._mobile_sessions().issue_session(user=user, device=device)

        if self.subscription_client and user_ref is not None:
            subscription = await self.subscription_client.get_subscription(user_ref)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        return AuthResponseDTO(
            tokens=tokens,
            user=build_mobile_user_response(user, subscription=subscription),
            is_new_user=False,
        )

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileCompleteTwoFactorUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
