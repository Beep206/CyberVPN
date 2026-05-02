"""Telegram OIDC authentication use case for mobile native login."""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    DeviceInfoDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TelegramOIDCAuthRequestDTO,
    TokenResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.application.services.telegram_oidc_auth import TelegramOIDCAuthService, TelegramOIDCUserInfo
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
from src.config.settings import settings
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)
from src.infrastructure.monitoring.instrumentation.routes import (
    track_telegram_oidc_device_registered,
    track_telegram_oidc_user_created,
    track_telegram_oidc_user_resolved,
)

if TYPE_CHECKING:
    from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient


logger = logging.getLogger(__name__)


@dataclass
class MobileTelegramOIDCAuthUseCase:
    """Authenticate a mobile user via Telegram OIDC ID token."""

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    telegram_oidc_service: TelegramOIDCAuthService
    subscription_client: CachedSubscriptionClient | None = None

    async def execute(self, request: TelegramOIDCAuthRequestDTO) -> tuple[AuthResponseDTO, bool]:
        """Validate Telegram OIDC token, resolve user, and issue mobile tokens."""
        telegram_user = await self.telegram_oidc_service.validate_id_token(request.id_token)

        user = await self.user_repo.get_by_telegram_subject(telegram_user.subject)
        resolution_path = "subject"
        is_new_user = False

        if not user and telegram_user.telegram_id is not None:
            user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)
            if user:
                resolution_path = "legacy_telegram_id"

        if not user:
            user = await self._create_user_from_telegram(telegram_user)
            resolution_path = "new_user"
            is_new_user = True
        else:
            await self._update_telegram_data(user, telegram_user)

        track_telegram_oidc_user_resolved(path=resolution_path)
        logger.info(
            "telegram_oidc_user_resolved",
            extra={
                "path": resolution_path,
                "user_id": str(user.id),
                "telegram_subject_hash": self._hash_subject(telegram_user.subject),
            },
        )

        if user.totp_enabled and user.totp_secret:
            customer_realm = DEFAULT_AUTH_REALMS["customer"]
            tfa_token, _pending_jti, _pending_expire = self.auth_service.create_access_token(
                subject=str(user.id),
                role="2fa_pending",
                extra={
                    "type": "2fa_pending",
                    "auth_method": "telegram_oidc",
                    "device_id": request.device.device_id,
                    "platform": request.device.platform.value,
                    "platform_id": request.device.platform_id,
                    "os_version": request.device.os_version,
                    "app_version": request.device.app_version,
                    "device_model": request.device.device_model,
                    "push_token": request.device.push_token,
                },
                audience=str(customer_realm["audience"]),
                principal_type="customer",
                realm_id=str(user.auth_realm_id or stable_auth_realm_id(str(customer_realm["realm_key"]))),
                realm_key=str(customer_realm["realm_key"]),
                scope_family="customer",
            )
            return (
                AuthResponseDTO(
                    is_new_user=False,
                    requires_2fa=True,
                    tfa_token=tfa_token,
                    method="totp",
                ),
                is_new_user,
            )

        await self._register_device(user.id, request.device)
        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        customer_realm = DEFAULT_AUTH_REALMS["customer"]
        access_token, _access_jti, _access_expire = self.auth_service.create_access_token(
            subject=str(user.id),
            role="mobile_user",
            extra={"device_id": request.device.device_id},
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

        tokens = TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

        if self.subscription_client and user.remnawave_uuid:
            subscription = await self.subscription_client.get_subscription(user.remnawave_uuid)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        user_response = build_mobile_user_response(user, subscription=subscription)

        return (
            AuthResponseDTO(
                tokens=tokens,
                user=user_response,
                is_new_user=is_new_user,
            ),
            is_new_user,
        )

    async def _create_user_from_telegram(self, telegram_user: TelegramOIDCUserInfo) -> MobileUserModel:
        placeholder_key = telegram_user.telegram_id if telegram_user.telegram_id is not None else telegram_user.subject
        placeholder_email = f"tg{placeholder_key}@telegram.local"
        password_hash = await self.auth_service.hash_password(secrets.token_urlsafe(32))
        username = self._generate_username(telegram_user)

        user = MobileUserModel(
            auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
            email=placeholder_email,
            password_hash=password_hash,
            username=username,
            telegram_subject=telegram_user.subject,
            telegram_id=telegram_user.telegram_id,
            telegram_username=telegram_user.preferred_username,
            is_active=True,
            status="active",
        )
        created_user = await self.user_repo.create(user)
        track_telegram_oidc_user_created()
        return created_user

    async def _update_telegram_data(self, user: MobileUserModel, telegram_user: TelegramOIDCUserInfo) -> None:
        changed = False

        if user.telegram_subject != telegram_user.subject:
            user.telegram_subject = telegram_user.subject
            changed = True

        if user.telegram_id != telegram_user.telegram_id:
            user.telegram_id = telegram_user.telegram_id
            changed = True

        if user.telegram_username != telegram_user.preferred_username:
            user.telegram_username = telegram_user.preferred_username
            changed = True

        generated_username = self._generate_username(telegram_user)
        if (
            generated_username
            and generated_username != user.username
            and self._should_refresh_username(user)
        ):
            existing_username = await self.user_repo.get_by_username(generated_username)
            if existing_username is None or existing_username.id == user.id:
                user.username = generated_username
                changed = True

        if changed:
            await self.user_repo.update(user)

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
            track_telegram_oidc_device_registered(platform=device.platform.value, action="updated")
            logger.info(
                "telegram_oidc_device_registered",
                extra={
                    "platform": device.platform.value,
                    "action": "updated",
                    "user_id": str(user_id),
                    "app_version": device.app_version,
                },
            )
            return

        new_device = MobileDeviceModel(
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
        await self.device_repo.create(new_device)
        track_telegram_oidc_device_registered(platform=device.platform.value, action="created")
        logger.info(
            "telegram_oidc_device_registered",
            extra={
                "platform": device.platform.value,
                "action": "created",
                "user_id": str(user_id),
                "app_version": device.app_version,
            },
        )

    @staticmethod
    def _generate_username(telegram_user: TelegramOIDCUserInfo) -> str:
        if telegram_user.preferred_username:
            username = re.sub(r"[^a-zA-Z0-9_]", "", telegram_user.preferred_username)
            if len(username) >= 3:
                return username[:50]

        if telegram_user.name:
            username = re.sub(r"[^a-zA-Z0-9_]", "", telegram_user.name.replace(" ", "_"))
            if len(username) >= 3:
                return username[:50]

        if telegram_user.telegram_id is not None:
            return f"tg_{telegram_user.telegram_id}"

        return f"tg_{telegram_user.subject[:20]}"

    @staticmethod
    def _should_refresh_username(user: MobileUserModel) -> bool:
        if not user.username:
            return True
        return user.username.startswith("tg_")

    @staticmethod
    def _hash_subject(subject: str) -> str:
        return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:12]
