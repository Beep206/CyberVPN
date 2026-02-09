from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.oauth_account_model import OAuthAccount


class OAuthAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_provider_and_user_id(self, provider: str, provider_user_id: str) -> OAuthAccount | None:
        result = await self._session.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_provider(self, user_id: UUID, provider: str) -> OAuthAccount | None:
        result = await self._session.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, model: OAuthAccount) -> OAuthAccount:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: OAuthAccount) -> OAuthAccount:
        await self._session.merge(model)
        await self._session.flush()
        return model
