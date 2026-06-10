"""Mobile user registration use case.

Handles registration of new mobile app users with device tracking.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    RegisterRequestDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
)
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.application.services.public_registration_policy import ensure_public_registration_enabled
from src.application.services.public_uid_allocator import allocate_public_uid
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
from src.domain.exceptions import DuplicateUsernameError
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileRegisterUseCase:
    """Use case for registering new mobile app users.

    Creates a new mobile user account, registers the device,
    and returns authentication tokens.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    allow_new_users: bool = True
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(self, request: RegisterRequestDTO) -> AuthResponseDTO:
        """Register a new mobile user.

        Args:
            request: Registration request with email, password, and device info.

        Returns:
            AuthResponseDTO with tokens and user data.

        Raises:
            DuplicateUsernameError: If email already exists.
        """
        ensure_public_registration_enabled(
            channel="mobile_password",
            registration_enabled=self.allow_new_users,
        )

        # Check email uniqueness
        existing_user = await self.user_repo.get_by_email(request.email)
        if existing_user:
            raise DuplicateUsernameError(username=request.email)

        # Hash password
        password_hash = await self.auth_service.hash_password(request.password)

        user = MobileUserModel(
            public_uid=await allocate_public_uid(self.user_repo),
            email=request.email,
            password_hash=password_hash,
            is_active=True,
            status="active",
        )
        created_user = await self.user_repo.create(user)

        tokens = await self._mobile_sessions().issue_session(user=created_user, device=request.device)

        subscription = SubscriptionInfoDTO(
            status=SubscriptionStatus.NONE,
        )

        user_response = build_mobile_user_response(created_user, subscription=subscription)

        return AuthResponseDTO(
            tokens=tokens,
            user=user_response,
            is_new_user=True,
        )

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileRegisterUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
