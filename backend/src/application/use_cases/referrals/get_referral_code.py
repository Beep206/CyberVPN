"""Use case: get or generate a user's referral code."""

import secrets
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.mobile_user_model import MobileUserModel


class GetReferralCodeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, user_id: UUID) -> str:
        """Get or generate user's referral code.

        If the user already has a referral code, return it.
        Otherwise, generate a new 8-character uppercase code,
        persist it, and return it.
        """
        result = await self._session.execute(select(MobileUserModel.referral_code).where(MobileUserModel.id == user_id))
        code = result.scalar_one_or_none()
        if code:
            return code

        new_code = secrets.token_urlsafe(6)[:8].upper()
        await self._session.execute(
            update(MobileUserModel).where(MobileUserModel.id == user_id).values(referral_code=new_code)
        )
        await self._session.flush()
        return new_code
