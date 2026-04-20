"""Infrastructure repository for auth realms and principal sessions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel


class AuthRealmRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_realms(self) -> list[AuthRealmModel]:
        result = await self._session.execute(
            select(AuthRealmModel).order_by(AuthRealmModel.realm_type, AuthRealmModel.realm_key)
        )
        return list(result.scalars().all())

    async def get_realm_by_id(self, id: UUID) -> AuthRealmModel | None:
        return await self._session.get(AuthRealmModel, id)

    async def get_realm_by_key(self, realm_key: str) -> AuthRealmModel | None:
        result = await self._session.execute(
            select(AuthRealmModel).where(func.lower(AuthRealmModel.realm_key) == realm_key.lower())
        )
        return result.scalar_one_or_none()

    async def get_realm_by_storefront_host(self, host: str) -> AuthRealmModel | None:
        normalized_host = host.split(":", 1)[0].strip().lower()
        result = await self._session.execute(
            select(AuthRealmModel)
            .join(StorefrontModel, StorefrontModel.auth_realm_id == AuthRealmModel.id)
            .where(func.lower(StorefrontModel.host) == normalized_host)
        )
        return result.scalar_one_or_none()

    async def get_default_realm(self, realm_type: str) -> AuthRealmModel | None:
        result = await self._session.execute(
            select(AuthRealmModel)
            .where(AuthRealmModel.realm_type == realm_type, AuthRealmModel.is_default.is_(True))
            .order_by(AuthRealmModel.created_at.asc())
        )
        return result.scalar_one_or_none()

    async def get_or_create_default_realm(self, realm_type: str) -> AuthRealmModel:
        existing = await self.get_default_realm(realm_type)
        if existing:
            return existing

        if realm_type not in DEFAULT_AUTH_REALMS:
            raise ValueError(f"Unsupported default realm type: {realm_type}")

        definition = DEFAULT_AUTH_REALMS[realm_type]
        model = AuthRealmModel(
            id=stable_auth_realm_id(str(definition["realm_key"])),
            realm_key=str(definition["realm_key"]),
            realm_type=str(definition["realm_type"]),
            display_name=str(definition["display_name"]),
            audience=str(definition["audience"]),
            cookie_namespace=str(definition["cookie_namespace"]),
            is_default=bool(definition["is_default"]),
            status="active",
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_realm(self, model: AuthRealmModel) -> AuthRealmModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_principal_session(self, model: PrincipalSessionModel) -> PrincipalSessionModel:
        self._session.add(model)
        await self._session.flush()
        return model
