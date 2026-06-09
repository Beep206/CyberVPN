"""Shared auth session issuance for realm-aware web login flows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel


class DeviceLimitExceededError(ValueError):
    """Raised when a new active device would exceed the backend policy."""


@dataclass(frozen=True)
class AuthSessionIssueRequest:
    user_id: UUID
    role: str
    device_key: str | None
    refresh_fingerprint: str | None = None
    ip_address: str | None = None
    ip_source: str | None = None
    proxy_peer: str | None = None
    user_agent: str | None = None
    auth_realm_id: UUID | None = None
    auth_realm_key: str | None = None
    audience: str | None = None
    principal_class: str = "admin"
    principal_subject: str | None = None
    scope_family: str = "admin"
    token_type: str = "bearer"  # noqa: S105 - token type label, not a secret.
    remember_me: bool = False
    access_extra: dict | None = None
    device_label: str | None = None
    platform: str | None = "web"
    device_limit: int | None = None
    replace_existing_device_sessions: bool = True


@dataclass(frozen=True)
class AuthSessionIssueResult:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    access_token_jti: str
    refresh_token_jti: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    auth_realm_id: str | None
    auth_realm_key: str | None
    audience: str | None
    principal_type: str
    scope_family: str
    user_device_id: UUID | None = None
    principal_session_id: UUID | None = None

    def as_token_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "auth_realm_id": self.auth_realm_id,
            "auth_realm_key": self.auth_realm_key,
            "audience": self.audience,
            "principal_type": self.principal_type,
            "scope_family": self.scope_family,
        }


class AuthSessionIssuer:
    """Issue JWTs and persist their device/session/refresh-token records."""

    def __init__(self, *, auth_service: AuthService, session: AsyncSession) -> None:
        self._auth_service = auth_service
        self._session = session

    async def issue_auth_session(self, request: AuthSessionIssueRequest) -> AuthSessionIssueResult:
        principal_subject = request.principal_subject or str(request.user_id)
        realm_id = str(request.auth_realm_id) if request.auth_realm_id else None

        access_token, access_jti, access_expires_at = self._auth_service.create_access_token(
            subject=str(request.user_id),
            role=request.role,
            extra=request.access_extra,
            audience=request.audience,
            principal_type=request.principal_class,
            realm_id=realm_id,
            realm_key=request.auth_realm_key,
            scope_family=request.scope_family,
        )
        refresh_token, refresh_jti, refresh_expires_at = self._auth_service.create_refresh_token(
            subject=str(request.user_id),
            remember_me=request.remember_me,
            fingerprint=request.refresh_fingerprint,
            audience=request.audience,
            principal_type=request.principal_class,
            realm_id=realm_id,
            realm_key=request.auth_realm_key,
            scope_family=request.scope_family,
        )

        if request.auth_realm_id is None or request.audience is None:
            return AuthSessionIssueResult(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type=request.token_type,
                expires_in=settings.access_token_expire_minutes * 60,
                access_token_jti=access_jti,
                refresh_token_jti=refresh_jti,
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                auth_realm_id=realm_id,
                auth_realm_key=request.auth_realm_key,
                audience=request.audience,
                principal_type=request.principal_class,
                scope_family=request.scope_family,
            )

        user_device = None
        principal_session = None
        if request.device_key:
            user_device = await self._get_or_create_user_device(
                request=request,
                principal_subject=principal_subject,
            )
            if request.replace_existing_device_sessions:
                await self._revoke_existing_device_sessions(
                    auth_realm_id=request.auth_realm_id,
                    principal_subject=principal_subject,
                    principal_class=request.principal_class,
                    user_device_id=user_device.id,
                )

        refresh_record = RefreshToken(
            user_id=request.user_id,
            auth_realm_id=request.auth_realm_id,
            principal_class=request.principal_class,
            principal_subject=principal_subject,
            audience=request.audience,
            scope_family=request.scope_family,
            token_hash=sha256(refresh_token.encode()).hexdigest(),
            expires_at=refresh_expires_at,
            device_id=str(user_device.id) if user_device else request.device_key,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            jti=refresh_jti,
            family_id=uuid4(),
        )
        self._session.add(refresh_record)
        await self._session.flush()

        if request.auth_realm_id and request.audience:
            principal_session = PrincipalSessionModel(
                auth_realm_id=request.auth_realm_id,
                principal_subject=principal_subject,
                principal_class=request.principal_class,
                audience=request.audience,
                scope_family=request.scope_family,
                access_token_jti=access_jti,
                refresh_token_id=refresh_record.id,
                user_device_id=user_device.id if user_device else None,
                current_refresh_token_id=refresh_record.id,
                expires_at=refresh_expires_at,
            )
            self._session.add(principal_session)
            await self._session.flush()
            refresh_record.principal_session_id = principal_session.id
            await self._session.flush()

        return AuthSessionIssueResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=request.token_type,
            expires_in=settings.access_token_expire_minutes * 60,
            access_token_jti=access_jti,
            refresh_token_jti=refresh_jti,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            auth_realm_id=realm_id,
            auth_realm_key=request.auth_realm_key,
            audience=request.audience,
            principal_type=request.principal_class,
            scope_family=request.scope_family,
            user_device_id=user_device.id if user_device else None,
            principal_session_id=principal_session.id if principal_session else None,
        )

    async def _get_or_create_user_device(
        self,
        *,
        request: AuthSessionIssueRequest,
        principal_subject: str,
    ) -> UserDeviceModel:
        if request.auth_realm_id is None or request.audience is None or not request.device_key:
            raise ValueError("auth_realm_id, audience and device_key are required for user device issuance")

        now = datetime.now(UTC)
        device_key_hash = hash_device_key(request.device_key)
        result = await self._session.execute(
            select(UserDeviceModel)
            .where(
                UserDeviceModel.auth_realm_id == request.auth_realm_id,
                UserDeviceModel.principal_class == request.principal_class,
                UserDeviceModel.principal_subject == principal_subject,
                UserDeviceModel.device_key_hash == device_key_hash,
                UserDeviceModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        user_device = result.scalar_one_or_none()
        if user_device:
            previous_user_agent = user_device.user_agent
            user_device.audience = request.audience
            user_device.device_label = request.device_label or user_device.device_label
            user_device.platform = request.platform or user_device.platform
            user_device.ip_address = request.ip_address
            user_device.user_agent = request.user_agent
            user_device.first_user_agent = user_device.first_user_agent or previous_user_agent or request.user_agent
            user_device.last_user_agent = request.user_agent
            user_device.last_ip_address = request.ip_address
            user_device.last_ip_source = request.ip_source
            user_device.last_proxy_peer = request.proxy_peer
            user_device.last_seen_at = now
            await self._session.flush()
            return user_device

        await self._enforce_device_limit(
            auth_realm_id=request.auth_realm_id,
            principal_class=request.principal_class,
            principal_subject=principal_subject,
            device_limit=request.device_limit,
        )
        user_device = UserDeviceModel(
            auth_realm_id=request.auth_realm_id,
            principal_subject=principal_subject,
            principal_class=request.principal_class,
            audience=request.audience,
            device_key_hash=device_key_hash,
            device_label=request.device_label,
            platform=request.platform,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            first_user_agent=request.user_agent,
            last_user_agent=request.user_agent,
            last_ip_address=request.ip_address,
            last_ip_source=request.ip_source,
            last_proxy_peer=request.proxy_peer,
            first_seen_at=now,
            last_seen_at=now,
        )
        self._session.add(user_device)
        await self._session.flush()
        return user_device

    async def _enforce_device_limit(
        self,
        *,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subject: str,
        device_limit: int | None,
    ) -> None:
        if device_limit is None or device_limit <= 0:
            return

        active_devices = await self._session.scalar(
            select(func.count())
            .select_from(UserDeviceModel)
            .where(
                UserDeviceModel.auth_realm_id == auth_realm_id,
                UserDeviceModel.principal_class == principal_class,
                UserDeviceModel.principal_subject == principal_subject,
                UserDeviceModel.revoked_at.is_(None),
            )
        )
        if int(active_devices or 0) >= device_limit:
            raise DeviceLimitExceededError("Device limit exceeded")

    async def _revoke_existing_device_sessions(
        self,
        *,
        auth_realm_id: UUID,
        principal_subject: str,
        principal_class: str,
        user_device_id: UUID,
    ) -> None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(PrincipalSessionModel)
            .where(
                PrincipalSessionModel.auth_realm_id == auth_realm_id,
                PrincipalSessionModel.principal_class == principal_class,
                PrincipalSessionModel.principal_subject == principal_subject,
                PrincipalSessionModel.user_device_id == user_device_id,
                PrincipalSessionModel.status == "active",
                PrincipalSessionModel.revoked_at.is_(None),
            )
            .with_for_update()
        )
        active_sessions = list(result.scalars().all())
        if not active_sessions:
            return

        session_ids = [session.id for session in active_sessions]
        current_refresh_ids = [
            session.current_refresh_token_id for session in active_sessions if session.current_refresh_token_id
        ]
        for session in active_sessions:
            session.status = "revoked"
            session.revoked_at = now
            session.last_seen_at = now

        if session_ids:
            await self._session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.principal_session_id.in_(session_ids),
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now, revoked_reason="replaced_by_new_login")
            )
        if current_refresh_ids:
            await self._session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.id.in_(current_refresh_ids),
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now, revoked_reason="replaced_by_new_login")
            )
        await self._session.flush()


def hash_device_key(device_key: str) -> str:
    return sha256((device_key + _device_cookie_pepper()).encode("utf-8")).hexdigest()


def _hash_device_key(device_key: str) -> str:
    return hash_device_key(device_key)


def _device_cookie_pepper() -> str:
    pepper = os.environ.get(settings.device_cookie_pepper_secret_name, "").strip()
    if pepper:
        return pepper
    if settings.environment.lower() == "production":
        raise RuntimeError(f"{settings.device_cookie_pepper_secret_name} is required for web device cookie hashing")
    return settings.jwt_secret.get_secret_value()
