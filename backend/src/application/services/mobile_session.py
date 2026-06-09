"""Shared session-backed mobile authentication helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import DeviceInfoDTO, DeviceSessionDTO, TokenResponseDTO
from src.application.services.auth_service import AuthService
from src.application.services.auth_session_issuer import (
    AuthSessionIssuer,
    AuthSessionIssueRequest,
    hash_device_key,
)
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenReplayError, RefreshTokenUseCase
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS
from src.domain.exceptions import InvalidCredentialsError, InvalidTokenError, UserNotFoundError, ValidationError
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileDeviceRepository, MobileUserRepository

MOBILE_PRINCIPAL_CLASS = "customer"
MOBILE_ROLE = "mobile_user"
MOBILE_TOKEN_TYPE = "Bearer"  # noqa: S105 - auth scheme literal, not a secret.


@dataclass(frozen=True)
class MobileRefreshSessionContext:
    token_record: RefreshToken
    principal_session: PrincipalSessionModel
    user_device: UserDeviceModel
    realm: AuthRealmModel


class MobileSessionService:
    """Bridge mobile auth endpoints to the shared principal-session model."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        auth_service: AuthService,
        user_repo: MobileUserRepository,
        device_repo: MobileDeviceRepository,
    ) -> None:
        self._session = session
        self._auth_service = auth_service
        self._user_repo = user_repo
        self._device_repo = device_repo
        self._session_issuer = AuthSessionIssuer(auth_service=auth_service, session=session)

    async def issue_session(
        self,
        *,
        user: MobileUserModel,
        device: DeviceInfoDTO,
        remember_me: bool = False,
    ) -> TokenResponseDTO:
        realm = await self._resolve_customer_realm(user)
        await self._upsert_legacy_device(user_id=user.id, device=device)

        issued_session = await self._session_issuer.issue_auth_session(
            AuthSessionIssueRequest(
                user_id=user.id,
                role=MOBILE_ROLE,
                device_key=device.device_id,
                auth_realm_id=realm.id,
                auth_realm_key=realm.realm_key,
                audience=realm.audience,
                principal_class=MOBILE_PRINCIPAL_CLASS,
                principal_subject=str(user.id),
                scope_family=realm.realm_type,
                token_type=MOBILE_TOKEN_TYPE,
                remember_me=remember_me,
                access_extra={"device_id": device.device_id},
                device_label=device.device_model,
                platform=device.platform.value,
            )
        )

        return TokenResponseDTO(
            access_token=issued_session.access_token,
            refresh_token=issued_session.refresh_token,
            token_type=issued_session.token_type,
            expires_in=issued_session.expires_in,
        )

    async def refresh(self, *, refresh_token: str, device_id: str) -> TokenResponseDTO:
        context = await self._validate_refresh_token_device(refresh_token=refresh_token, device_id=device_id)
        try:
            result = await RefreshTokenUseCase(auth_service=self._auth_service, session=self._session).execute(
                refresh_token,
                auth_realm_id=context.principal_session.auth_realm_id,
                auth_realm_key=context.realm.realm_key,
                audience=context.principal_session.audience,
                principal_type=MOBILE_PRINCIPAL_CLASS,
                scope_family=context.principal_session.scope_family,
                access_extra={"device_id": device_id},
            )
        except RefreshTokenReplayError:
            raise
        except InvalidCredentialsError as exc:
            raise InvalidTokenError() from exc

        await self._touch_legacy_device(user_id=context.token_record.user_id, device_id=device_id)
        return TokenResponseDTO(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=MOBILE_TOKEN_TYPE,
            expires_in=int(result["expires_in"]),
        )

    async def logout(self, *, refresh_token: str, device_id: str) -> None:
        context = await self._validate_refresh_token_device(refresh_token=refresh_token, device_id=device_id)
        result = await LogoutUseCase(session=self._session).execute(refresh_token)
        if not result.refresh_token_revoked:
            raise InvalidTokenError()
        await self._touch_legacy_device(user_id=context.token_record.user_id, device_id=device_id, clear_push=True)

    async def list_devices(self, *, user_id: UUID) -> list[DeviceSessionDTO]:
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UserNotFoundError(identifier=str(user_id))

        realm = await self._resolve_customer_realm(user)
        result = await self._session.execute(
            select(UserDeviceModel).where(
                UserDeviceModel.auth_realm_id == realm.id,
                UserDeviceModel.principal_class == MOBILE_PRINCIPAL_CLASS,
                UserDeviceModel.principal_subject == str(user_id),
                UserDeviceModel.revoked_at.is_(None),
            )
        )
        active_device_hashes = {device.device_key_hash for device in result.scalars().all()}
        if not active_device_hashes:
            return []

        legacy_devices = await self._device_repo.get_user_devices(user_id)
        return [
            DeviceSessionDTO(
                id=device.device_id,
                name=device.device_model,
                platform=device.platform,
                ip_address=None,
                last_active_at=device.last_active_at,
                created_at=device.registered_at,
                is_current=False,
            )
            for device in legacy_devices
            if hash_device_key(device.device_id) in active_device_hashes
        ]

    async def revoke_device(self, *, user_id: UUID, device_id: str) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UserNotFoundError(identifier=str(user_id))

        realm = await self._resolve_customer_realm(user)
        user_device = await self._get_active_user_device(
            auth_realm_id=realm.id,
            principal_subject=str(user_id),
            device_id=device_id,
        )
        if user_device is None:
            raise ValidationError("Device not found")

        await LogoutUseCase(session=self._session).execute_device(
            auth_realm_id=realm.id,
            principal_subject=str(user_id),
            principal_class=MOBILE_PRINCIPAL_CLASS,
            user_device_id=user_device.id,
            reason="mobile_device_removed",
        )

        legacy_device = await self._device_repo.get_by_device_id_and_user(device_id=device_id, user_id=user_id)
        if legacy_device is not None:
            await self._device_repo.delete(legacy_device)

    async def _resolve_customer_realm(self, user: MobileUserModel) -> AuthRealmModel:
        repo = AuthRealmRepository(self._session)
        if user.auth_realm_id is not None:
            realm = await repo.get_realm_by_id(user.auth_realm_id)
            if realm is not None and realm.realm_type == str(DEFAULT_AUTH_REALMS["customer"]["realm_type"]):
                return realm

        realm = await repo.get_or_create_default_realm("customer")
        if user.auth_realm_id != realm.id:
            user.auth_realm_id = realm.id
            await self._session.flush()
        return realm

    async def _upsert_legacy_device(self, *, user_id: UUID, device: DeviceInfoDTO) -> MobileDeviceModel:
        existing_device = await self._device_repo.get_by_device_id_and_user(
            device_id=device.device_id,
            user_id=user_id,
        )
        now = datetime.now(UTC)
        if existing_device:
            existing_device.platform = device.platform.value
            existing_device.platform_id = device.platform_id
            existing_device.os_version = device.os_version
            existing_device.app_version = device.app_version
            existing_device.device_model = device.device_model
            existing_device.push_token = device.push_token
            existing_device.last_active_at = now
            return await self._device_repo.update(existing_device)

        return await self._device_repo.create(
            MobileDeviceModel(
                device_id=device.device_id,
                platform=device.platform.value,
                platform_id=device.platform_id,
                os_version=device.os_version,
                app_version=device.app_version,
                device_model=device.device_model,
                push_token=device.push_token,
                user_id=user_id,
                last_active_at=now,
            )
        )

    async def _touch_legacy_device(self, *, user_id: UUID, device_id: str, clear_push: bool = False) -> None:
        device = await self._device_repo.get_by_device_id_and_user(device_id=device_id, user_id=user_id)
        if device is None:
            return
        if clear_push:
            device.push_token = None
        device.last_active_at = datetime.now(UTC)
        await self._device_repo.update(device)

    async def _validate_refresh_token_device(
        self,
        *,
        refresh_token: str,
        device_id: str,
    ) -> MobileRefreshSessionContext:
        token_hash = sha256(refresh_token.encode()).hexdigest()
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
        token_record = result.scalar_one_or_none()
        if token_record is None:
            raise InvalidTokenError("legacy_unpersisted_refresh_token")

        principal_session = await self._load_token_session(token_record)
        if principal_session is None or principal_session.user_device_id is None:
            raise InvalidTokenError("missing_principal_session")
        if (
            token_record.principal_class != MOBILE_PRINCIPAL_CLASS
            or token_record.principal_subject != str(token_record.user_id)
            or token_record.audience != principal_session.audience
            or token_record.scope_family != principal_session.scope_family
            or token_record.auth_realm_id != principal_session.auth_realm_id
        ):
            raise InvalidTokenError("invalid_refresh_token_owner")
        if (
            principal_session.status != "active"
            or principal_session.revoked_at is not None
            or principal_session.principal_class != MOBILE_PRINCIPAL_CLASS
            or principal_session.principal_subject != str(token_record.user_id)
        ):
            raise InvalidTokenError("invalid_principal_session")

        realm = await AuthRealmRepository(self._session).get_realm_by_id(principal_session.auth_realm_id)
        if realm is None or realm.realm_type != str(DEFAULT_AUTH_REALMS["customer"]["realm_type"]):
            raise InvalidTokenError("invalid_realm")

        user_device = await self._session.get(UserDeviceModel, principal_session.user_device_id)
        if (
            user_device is None
            or user_device.revoked_at is not None
            or user_device.auth_realm_id != principal_session.auth_realm_id
            or user_device.principal_class != MOBILE_PRINCIPAL_CLASS
            or user_device.principal_subject != str(token_record.user_id)
            or user_device.device_key_hash != hash_device_key(device_id)
        ):
            raise InvalidTokenError("device_mismatch")

        return MobileRefreshSessionContext(
            token_record=token_record,
            principal_session=principal_session,
            user_device=user_device,
            realm=realm,
        )

    async def _load_token_session(self, token_record: RefreshToken) -> PrincipalSessionModel | None:
        if token_record.principal_session_id is not None:
            result = await self._session.execute(
                select(PrincipalSessionModel)
                .where(PrincipalSessionModel.id == token_record.principal_session_id)
                .with_for_update()
            )
            return result.scalar_one_or_none()

        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                or_(
                    PrincipalSessionModel.refresh_token_id == token_record.id,
                    PrincipalSessionModel.current_refresh_token_id == token_record.id,
                )
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _get_active_user_device(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: str,
        device_id: str,
    ) -> UserDeviceModel | None:
        result = await self._session.execute(
            select(UserDeviceModel)
            .where(
                UserDeviceModel.auth_realm_id == auth_realm_id,
                UserDeviceModel.principal_class == MOBILE_PRINCIPAL_CLASS,
                UserDeviceModel.principal_subject == principal_subject,
                UserDeviceModel.device_key_hash == hash_device_key(device_id),
                UserDeviceModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()
