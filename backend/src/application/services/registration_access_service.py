"""Durable registration-access grants for invite-only registration."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.customer_onboarding_model import RegistrationAccessGrantModel

REGISTRATION_ACCESS_RESERVATION_PREFIX = "rag"
REGISTRATION_ACCESS_EXCHANGE_RESERVATION_PREFIX = "ragx"
REGISTRATION_ACCESS_EXCHANGE_SESSION_PREFIX = "ragx_v1"
REGISTRATION_ACCESS_EXCHANGE_SESSION_TTL_SECONDS = 15 * 60


@dataclass(frozen=True)
class RegistrationAccessGrantData:
    """Safe grant data returned to registration/auth callers."""

    role: str
    email_hint_hash: str | None
    created_by: str | None
    source: str = "registration_access_grants"

    def as_invite_data(self) -> dict[str, str | None]:
        return {
            "role": self.role,
            "email_hint_hash": self.email_hint_hash,
            "created_by": self.created_by,
            "source": self.source,
        }


@dataclass(frozen=True)
class RegistrationAccessExchangeResult:
    """Safe exchange result used to set a browser-only registration grant."""

    grant: RegistrationAccessGrantData
    session_token: str
    expires_at: datetime


class RegistrationAccessGrantService:
    """DB-backed registration token lifecycle.

    Raw access tokens are never persisted. New writes use this durable table;
    legacy Redis-only invite tokens can still be handled by callers when this
    service reports that no grant exists for a token hash.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(
        self,
        *,
        token: str,
        created_by_admin_user_id: UUID | None,
        role: str,
        email_hint: str | None,
        auth_realm_id: UUID | None,
        now: datetime | None = None,
    ) -> RegistrationAccessGrantModel:
        issued_at = _utc(now)
        grant = RegistrationAccessGrantModel(
            token_hash=hash_registration_access_token(token),
            status="issued",
            created_by_admin_user_id=created_by_admin_user_id,
            role_key=_normalize_role(role),
            email_hint_hash=hash_registration_access_email_hint(email_hint) if email_hint else None,
            auth_realm_id=auth_realm_id,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(hours=settings.invite_token_expiry_hours),
            metadata_={"issuer": "admin_invite"},
        )
        self._session.add(grant)
        await self._session.flush()
        return grant

    async def has_token(self, token: str) -> bool:
        grant = await self._get_by_token(token, lock=False)
        return grant is not None

    async def exchange_for_browser(
        self,
        *,
        token: str,
        idempotency_key: str,
        host: str,
        auth_realm_id: UUID | None,
        now: datetime | None = None,
    ) -> RegistrationAccessExchangeResult | None:
        exchanged_at = _utc(now)
        token_hash = hash_registration_access_token(token)
        normalized_idempotency_key = _normalize_idempotency_key(idempotency_key)
        normalized_host = _normalize_host(host)
        session_token = build_registration_access_exchange_session_token(
            token_hash=token_hash,
            idempotency_key=normalized_idempotency_key,
            host=normalized_host,
        )
        session_hash = hash_registration_access_exchange_session(session_token)
        grant = await self._get_by_token_hash(token_hash, lock=True)
        if grant is None:
            return None
        if self._is_expired(grant, exchanged_at):
            grant.status = "expired"
            await self._session.flush()
            return None
        if auth_realm_id is not None and grant.auth_realm_id is not None and grant.auth_realm_id != auth_realm_id:
            return None

        if grant.status == "exchanged":
            metadata = grant.metadata_ or {}
            if (
                grant.exchange_session_hash == session_hash
                and metadata.get("exchange_idempotency_key") == normalized_idempotency_key
                and metadata.get("exchange_host") == normalized_host
                and self._exchange_session_is_fresh(grant, exchanged_at)
            ):
                return RegistrationAccessExchangeResult(
                    grant=_grant_data(grant),
                    session_token=session_token,
                    expires_at=min(_utc(grant.expires_at), exchanged_at + _exchange_ttl()),
                )
            return None
        if grant.status not in {"issued", "released"}:
            return None

        grant.status = "exchanged"
        grant.exchanged_at = exchanged_at
        grant.exchange_session_hash = session_hash
        grant.reservation_key = None
        grant.reserved_at = None
        grant.registration_idempotency_key = None
        metadata = dict(grant.metadata_ or {})
        metadata.update(
            {
                "exchange_idempotency_key": normalized_idempotency_key,
                "exchange_host": normalized_host,
                "exchange_realm_id": str(auth_realm_id) if auth_realm_id is not None else None,
            }
        )
        grant.metadata_ = metadata
        await self._session.flush()
        return RegistrationAccessExchangeResult(
            grant=_grant_data(grant),
            session_token=session_token,
            expires_at=min(_utc(grant.expires_at), exchanged_at + _exchange_ttl()),
        )

    async def reserve_for_registration(
        self,
        *,
        token: str,
        reservation_id: str,
        registration_idempotency_key: str | None = None,
        now: datetime | None = None,
    ) -> RegistrationAccessGrantData | None:
        reserved_at = _utc(now)
        grant = await self._get_by_token(token, lock=True)
        if grant is None:
            return None
        if self._is_expired(grant, reserved_at):
            grant.status = "expired"
            await self._session.flush()
            return None
        reservation_key = build_registration_access_reservation_key(token, reservation_id)
        if grant.status == "reserved":
            if grant.reservation_key == reservation_key:
                return _grant_data(grant)
            return None
        if grant.status not in {"issued", "exchanged", "released"}:
            return None

        grant.status = "reserved"
        grant.reserved_at = reserved_at
        grant.reservation_key = reservation_key
        grant.registration_idempotency_key = registration_idempotency_key
        grant.released_at = None
        grant.release_reason = None
        await self._session.flush()
        return _grant_data(grant)

    async def reserve_exchange_session_for_registration(
        self,
        *,
        session_token: str,
        reservation_id: str,
        host: str,
        registration_idempotency_key: str | None = None,
        now: datetime | None = None,
    ) -> RegistrationAccessGrantData | None:
        reserved_at = _utc(now)
        normalized_host = _normalize_host(host)
        try:
            grant = await self._get_by_exchange_session(session_token, lock=True)
        except ValueError:
            return None
        if grant is None:
            return None
        if self._is_expired(grant, reserved_at) or not self._exchange_session_is_fresh(grant, reserved_at):
            grant.status = "expired"
            await self._session.flush()
            return None
        if (grant.metadata_ or {}).get("exchange_host") != normalized_host:
            return None

        reservation_key = build_registration_access_exchange_reservation_key(session_token, reservation_id)
        if grant.status == "reserved":
            if grant.reservation_key == reservation_key:
                return _grant_data(grant)
            return None
        if grant.status not in {"exchanged", "released"}:
            return None

        grant.status = "reserved"
        grant.reserved_at = reserved_at
        grant.reservation_key = reservation_key
        grant.registration_idempotency_key = registration_idempotency_key
        grant.released_at = None
        grant.release_reason = None
        await self._session.flush()
        return _grant_data(grant)

    async def consume_reserved_for_registration(
        self,
        *,
        token: str,
        reservation_id: str,
        consumed_user_id: UUID | None,
        now: datetime | None = None,
    ) -> RegistrationAccessGrantData | None:
        consumed_at = _utc(now)
        grant = await self._get_by_token(token, lock=True)
        if grant is None:
            return None
        if self._is_expired(grant, consumed_at):
            grant.status = "expired"
            await self._session.flush()
            return None
        if grant.status == "consumed" and grant.consumed_user_id == consumed_user_id:
            return _grant_data(grant)
        expected_reservation_key = build_registration_access_reservation_key(token, reservation_id)
        if grant.status != "reserved" or grant.reservation_key != expected_reservation_key:
            return None

        grant.status = "consumed"
        grant.consumed_at = consumed_at
        grant.consumed_user_id = consumed_user_id
        await self._session.flush()
        return _grant_data(grant)

    async def consume_reserved_exchange_session_for_registration(
        self,
        *,
        session_token: str,
        reservation_id: str,
        consumed_user_id: UUID | None,
        host: str,
        now: datetime | None = None,
    ) -> RegistrationAccessGrantData | None:
        consumed_at = _utc(now)
        normalized_host = _normalize_host(host)
        try:
            grant = await self._get_by_exchange_session(session_token, lock=True)
        except ValueError:
            return None
        if grant is None:
            return None
        if self._is_expired(grant, consumed_at) or not self._exchange_session_is_fresh(grant, consumed_at):
            grant.status = "expired"
            await self._session.flush()
            return None
        if (grant.metadata_ or {}).get("exchange_host") != normalized_host:
            return None
        if grant.status == "consumed" and grant.consumed_user_id == consumed_user_id:
            return _grant_data(grant)
        expected_reservation_key = build_registration_access_exchange_reservation_key(session_token, reservation_id)
        if grant.status != "reserved" or grant.reservation_key != expected_reservation_key:
            return None

        grant.status = "consumed"
        grant.consumed_at = consumed_at
        grant.consumed_user_id = consumed_user_id
        await self._session.flush()
        return _grant_data(grant)

    async def release_registration_reservation(
        self,
        *,
        token: str,
        reservation_id: str,
        reason: str,
        now: datetime | None = None,
    ) -> bool:
        released_at = _utc(now)
        grant = await self._get_by_token(token, lock=True)
        if grant is None:
            return False
        expected_reservation_key = build_registration_access_reservation_key(token, reservation_id)
        if grant.status != "reserved" or grant.reservation_key != expected_reservation_key:
            return False

        grant.status = "released"
        grant.released_at = released_at
        grant.release_reason = _bounded_reason(reason)
        grant.reservation_key = None
        grant.reserved_at = None
        grant.registration_idempotency_key = None
        await self._session.flush()
        return True

    async def release_exchange_session_registration_reservation(
        self,
        *,
        session_token: str,
        reservation_id: str,
        reason: str,
        host: str,
        now: datetime | None = None,
    ) -> bool:
        released_at = _utc(now)
        try:
            grant = await self._get_by_exchange_session(session_token, lock=True)
        except ValueError:
            return False
        if grant is None:
            return False
        if (grant.metadata_ or {}).get("exchange_host") != _normalize_host(host):
            return False
        expected_reservation_key = build_registration_access_exchange_reservation_key(session_token, reservation_id)
        if grant.status != "reserved" or grant.reservation_key != expected_reservation_key:
            return False

        grant.status = "released"
        grant.released_at = released_at
        grant.release_reason = _bounded_reason(reason)
        grant.reservation_key = None
        grant.reserved_at = None
        grant.registration_idempotency_key = None
        await self._session.flush()
        return True

    async def revoke(self, token: str, *, now: datetime | None = None) -> bool:
        grant = await self._get_by_token(token, lock=True)
        if grant is None:
            return False
        if grant.status == "consumed":
            return False
        grant.status = "revoked"
        grant.revoked_at = _utc(now)
        grant.reservation_key = None
        await self._session.flush()
        return True

    async def _get_by_token(self, token: str, *, lock: bool) -> RegistrationAccessGrantModel | None:
        return await self._get_by_token_hash(hash_registration_access_token(token), lock=lock)

    async def _get_by_token_hash(self, token_hash: str, *, lock: bool) -> RegistrationAccessGrantModel | None:
        stmt = select(RegistrationAccessGrantModel).where(RegistrationAccessGrantModel.token_hash == token_hash)
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_exchange_session(
        self,
        session_token: str,
        *,
        lock: bool,
    ) -> RegistrationAccessGrantModel | None:
        session_hash = hash_registration_access_exchange_session(session_token)
        stmt = select(RegistrationAccessGrantModel).where(
            RegistrationAccessGrantModel.exchange_session_hash == session_hash
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _is_expired(grant: RegistrationAccessGrantModel, now: datetime) -> bool:
        return _utc(grant.expires_at) <= now

    @staticmethod
    def _exchange_session_is_fresh(grant: RegistrationAccessGrantModel, now: datetime) -> bool:
        return grant.exchanged_at is not None and _utc(grant.exchanged_at) + _exchange_ttl() > now


def hash_registration_access_token(token: str) -> str:
    return hashlib.sha256(_normalize_token(token).encode("utf-8")).hexdigest()


def hash_registration_access_exchange_session(session_token: str) -> str:
    return hashlib.sha256(_normalize_exchange_session_token(session_token).encode("utf-8")).hexdigest()


def hash_registration_access_email_hint(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def registration_access_email_hint_matches(invite_data: dict, email: str | None) -> bool:
    email_hint = invite_data.get("email_hint")
    if email_hint:
        return bool(email and str(email_hint).strip().lower() == email.strip().lower())
    email_hint_hash = invite_data.get("email_hint_hash")
    if email_hint_hash:
        return bool(email and str(email_hint_hash) == hash_registration_access_email_hint(email))
    return True


def build_registration_access_reservation_key(token: str, reservation_id: str) -> str:
    token_hash = hash_registration_access_token(token)
    return f"{REGISTRATION_ACCESS_RESERVATION_PREFIX}:{token_hash[:32]}:{reservation_id}"


def build_registration_access_exchange_reservation_key(session_token: str, reservation_id: str) -> str:
    session_hash = hash_registration_access_exchange_session(session_token)
    return f"{REGISTRATION_ACCESS_EXCHANGE_RESERVATION_PREFIX}:{session_hash[:32]}:{reservation_id}"


def build_registration_access_exchange_session_token(
    *,
    token_hash: str,
    idempotency_key: str,
    host: str,
) -> str:
    message = ":".join(
        (
            "registration_access_exchange",
            "v1",
            token_hash,
            _normalize_idempotency_key(idempotency_key),
            _normalize_host(host),
        )
    )
    digest = hmac.new(_hmac_secret(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{REGISTRATION_ACCESS_EXCHANGE_SESSION_PREFIX}_{digest}"


def _grant_data(grant: RegistrationAccessGrantModel) -> RegistrationAccessGrantData:
    return RegistrationAccessGrantData(
        role=grant.role_key,
        email_hint_hash=grant.email_hint_hash,
        created_by=str(grant.created_by_admin_user_id) if grant.created_by_admin_user_id else None,
    )


def _normalize_token(token: str) -> str:
    normalized = token.strip()
    if not normalized:
        raise ValueError("Registration access token is required")
    return normalized


def _normalize_exchange_session_token(session_token: str) -> str:
    normalized = session_token.strip()
    if not normalized.startswith(f"{REGISTRATION_ACCESS_EXCHANGE_SESSION_PREFIX}_"):
        raise ValueError("Invalid registration access exchange session")
    if len(normalized) != len(REGISTRATION_ACCESS_EXCHANGE_SESSION_PREFIX) + 1 + 64:
        raise ValueError("Invalid registration access exchange session")
    return normalized


def _normalize_idempotency_key(idempotency_key: str) -> str:
    normalized = idempotency_key.strip()
    if not normalized or len(normalized) > 120:
        raise ValueError("Registration access exchange idempotency key is required")
    return normalized


def _normalize_host(host: str) -> str:
    return host.strip().lower()[:255] or "unknown"


def _normalize_role(role: str) -> str:
    return str(role).strip().lower() or "viewer"


def _bounded_reason(reason: str) -> str:
    return str(reason).strip()[:80] or "registration_released"


def _utc(value: datetime | None) -> datetime:
    resolved = value or datetime.now(UTC)
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=UTC)
    return resolved.astimezone(UTC)


def _exchange_ttl() -> timedelta:
    return timedelta(seconds=REGISTRATION_ACCESS_EXCHANGE_SESSION_TTL_SECONDS)


def _hmac_secret() -> bytes:
    return settings.jwt_secret.get_secret_value().encode("utf-8")
