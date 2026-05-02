"""Complete a mobile login paused behind TOTP verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    DeviceInfoDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TokenResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
from src.config.settings import settings
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.domain.exceptions import ValidationError
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
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

        await self._register_device(user.id, device)
        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        customer_realm = DEFAULT_AUTH_REALMS["customer"]
        access_token, _access_jti, _access_expire = self.auth_service.create_access_token(
            subject=str(user.id),
            role="mobile_user",
            extra={"device_id": device.device_id},
            audience=str(customer_realm["audience"]),
            principal_type="customer",
            realm_id=str(user.auth_realm_id or stable_auth_realm_id(str(customer_realm["realm_key"]))),
            realm_key=str(customer_realm["realm_key"]),
            scope_family="customer",
        )
        refresh_token, _refresh_jti, _refresh_expire = self.auth_service.create_refresh_token(
            subject=str(user.id),
            audience=str(customer_realm["audience"]),
            principal_type="customer",
            realm_id=str(user.auth_realm_id or stable_auth_realm_id(str(customer_realm["realm_key"]))),
            realm_key=str(customer_realm["realm_key"]),
            scope_family="customer",
        )

        if self.subscription_client and user.remnawave_uuid:
            subscription = await self.subscription_client.get_subscription(user.remnawave_uuid)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        return AuthResponseDTO(
            tokens=TokenResponseDTO(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="Bearer",  # noqa: S106 - auth scheme literal, not a secret
                expires_in=settings.access_token_expire_minutes * 60,
            ),
            user=build_mobile_user_response(user, subscription=subscription),
            is_new_user=False,
        )

    async def _register_device(self, user_id, device: DeviceInfoDTO) -> None:
        existing_device = await self.device_repo.get_by_device_id_and_user(
            device_id=device.device_id,
            user_id=user_id,
        )

        if existing_device:
            existing_device.platform = device.platform.value
            existing_device.platform_id = device.platform_id
            existing_device.os_version = device.os_version
            existing_device.app_version = device.app_version
            existing_device.device_model = device.device_model
            existing_device.push_token = device.push_token
            existing_device.last_active_at = datetime.now(UTC)
            await self.device_repo.update(existing_device)
            return

        await self.device_repo.create(
            MobileDeviceModel(
                device_id=device.device_id,
                platform=device.platform.value,
                platform_id=device.platform_id,
                os_version=device.os_version,
                app_version=device.app_version,
                device_model=device.device_model,
                push_token=device.push_token,
                user_id=user_id,
                last_active_at=datetime.now(UTC),
            )
        )
