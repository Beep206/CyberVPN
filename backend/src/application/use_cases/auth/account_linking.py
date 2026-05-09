from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.oauth_account_model import OAuthAccount
from src.shared.security.oauth_token_store import build_stored_oauth_tokens


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
        stored_tokens = build_stored_oauth_tokens(
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        result = await self._session.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        existing_identity = result.scalar_one_or_none()
        if existing_identity:
            if existing_identity.user_id != user_id:
                raise ValueError("Provider account is already linked to another user.")
            existing_identity.provider_username = provider_username
            existing_identity.provider_email = provider_email
            existing_identity.access_token = stored_tokens.access_token
            existing_identity.refresh_token = stored_tokens.refresh_token
            await self._session.flush()
            return existing_identity

        result = await self._session.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
            )
        )
        existing_provider = result.scalar_one_or_none()
        if existing_provider:
            if existing_provider.provider_user_id != provider_user_id:
                raise ValueError("User already has a different account linked for this provider.")
            existing_provider.provider_username = provider_username
            existing_provider.provider_email = provider_email
            existing_provider.access_token = stored_tokens.access_token
            existing_provider.refresh_token = stored_tokens.refresh_token
            await self._session.flush()
            return existing_provider

        account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_username=provider_username,
            provider_email=provider_email,
            access_token=stored_tokens.access_token,
            refresh_token=stored_tokens.refresh_token,
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
