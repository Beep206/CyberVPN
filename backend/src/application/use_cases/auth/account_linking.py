from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.oauth_account_model import OAuthAccount


class AccountLinkingUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def link_account(
        self,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        provider_username: str | None = None,
        provider_email: str | None = None,
        access_token: str = "",
        refresh_token: str | None = None,
    ) -> OAuthAccount:
        account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_username=provider_username,
            provider_email=provider_email,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        self._session.add(account)
        await self._session.flush()
        return account

    async def unlink_account(self, user_id: UUID, provider: str) -> None:
        result = await self._session.execute(
            select(OAuthAccount).where(OAuthAccount.user_id == user_id, OAuthAccount.provider == provider)
        )
        account = result.scalar_one_or_none()
        if account:
            await self._session.delete(account)
            await self._session.flush()

    async def get_linked_accounts(self, user_id: UUID) -> list[OAuthAccount]:
        result = await self._session.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))
        return list(result.scalars().all())
