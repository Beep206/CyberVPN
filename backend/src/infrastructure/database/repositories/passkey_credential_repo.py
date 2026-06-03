"""Repository for WebAuthn passkey credentials."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.passkey_credential_model import PasskeyCredentialModel


class PasskeyCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_statement(self) -> Select[tuple[PasskeyCredentialModel]]:
        return select(PasskeyCredentialModel).where(
            PasskeyCredentialModel.status == "active",
            PasskeyCredentialModel.revoked_at.is_(None),
            PasskeyCredentialModel.deleted_at.is_(None),
        )

    async def add(self, credential: PasskeyCredentialModel) -> PasskeyCredentialModel:
        self._session.add(credential)
        await self._session.flush()
        return credential

    async def get_by_id(self, credential_id: UUID) -> PasskeyCredentialModel | None:
        return await self._session.get(PasskeyCredentialModel, credential_id)

    async def get_active_by_hash(self, credential_id_hash: str) -> PasskeyCredentialModel | None:
        result = await self._session.execute(
            self._active_statement().where(PasskeyCredentialModel.credential_id_hash == credential_id_hash)
        )
        return result.scalar_one_or_none()

    async def list_active_for_principal(
        self,
        *,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subject: str,
    ) -> list[PasskeyCredentialModel]:
        result = await self._session.execute(
            self._active_statement()
            .where(
                PasskeyCredentialModel.auth_realm_id == auth_realm_id,
                PasskeyCredentialModel.principal_class == principal_class,
                PasskeyCredentialModel.principal_subject == principal_subject,
            )
            .order_by(PasskeyCredentialModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_for_realm(
        self,
        *,
        auth_realm_id: UUID,
        principal_class: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PasskeyCredentialModel]:
        statement = select(PasskeyCredentialModel).where(PasskeyCredentialModel.auth_realm_id == auth_realm_id)
        if principal_class is not None:
            statement = statement.where(PasskeyCredentialModel.principal_class == principal_class)

        result = await self._session.execute(
            statement
            .order_by(PasskeyCredentialModel.created_at.desc(), PasskeyCredentialModel.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_for_principal_subjects(
        self,
        *,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subjects: Iterable[str],
    ) -> list[PasskeyCredentialModel]:
        subjects = tuple(principal_subjects)
        if not subjects:
            return []

        result = await self._session.execute(
            select(PasskeyCredentialModel)
            .where(
                PasskeyCredentialModel.auth_realm_id == auth_realm_id,
                PasskeyCredentialModel.principal_class == principal_class,
                PasskeyCredentialModel.principal_subject.in_(subjects),
            )
            .order_by(PasskeyCredentialModel.created_at.desc(), PasskeyCredentialModel.id.asc())
        )
        return list(result.scalars().all())

    async def count_active_for_principal(
        self,
        *,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subject: str,
    ) -> int:
        result = await self._session.execute(
            select(func.count(PasskeyCredentialModel.id)).where(
                PasskeyCredentialModel.auth_realm_id == auth_realm_id,
                PasskeyCredentialModel.principal_class == principal_class,
                PasskeyCredentialModel.principal_subject == principal_subject,
                PasskeyCredentialModel.status == "active",
                PasskeyCredentialModel.revoked_at.is_(None),
                PasskeyCredentialModel.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def rename_for_principal(
        self,
        *,
        credential_id: UUID,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subject: str,
        label: str,
    ) -> PasskeyCredentialModel | None:
        credential = await self.get_by_id(credential_id)
        if not credential or not self._matches_principal(
            credential,
            auth_realm_id=auth_realm_id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        ):
            return None
        credential.label = label
        await self._session.flush()
        return credential

    async def revoke_for_principal(
        self,
        *,
        credential_id: UUID,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subject: str,
    ) -> PasskeyCredentialModel | None:
        credential = await self.get_by_id(credential_id)
        if not credential or not self._matches_principal(
            credential,
            auth_realm_id=auth_realm_id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        ):
            return None
        credential.status = "revoked"
        credential.revoked_at = datetime.now(UTC)
        await self._session.flush()
        return credential

    async def mark_used(
        self,
        credential: PasskeyCredentialModel,
        *,
        sign_count: int,
        user_verified: bool,
        backed_up: bool,
        device_type: str | None,
    ) -> PasskeyCredentialModel:
        credential.sign_count = sign_count
        credential.user_verified = user_verified
        credential.backed_up = backed_up
        credential.device_type = device_type
        credential.last_used_at = datetime.now(UTC)
        await self._session.flush()
        return credential

    async def mark_clone_suspected(self, credential: PasskeyCredentialModel) -> PasskeyCredentialModel:
        credential.clone_suspected_at = datetime.now(UTC)
        await self._session.flush()
        return credential

    def _matches_principal(
        self,
        credential: PasskeyCredentialModel,
        *,
        auth_realm_id: UUID,
        principal_class: str,
        principal_subject: str,
    ) -> bool:
        return (
            credential.auth_realm_id == auth_realm_id
            and credential.principal_class == principal_class
            and credential.principal_subject == principal_subject
            and credential.deleted_at is None
            and credential.revoked_at is None
            and credential.status == "active"
        )
