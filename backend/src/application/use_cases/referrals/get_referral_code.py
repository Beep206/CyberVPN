"""Use case: get or generate a user's referral code."""

import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import DomainError
from src.infrastructure.database.models.mobile_user_model import MobileUserModel

REFERRAL_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
REFERRAL_CODE_LENGTH = 8
REFERRAL_CODE_MAX_ATTEMPTS = 10


class GetReferralCodeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, user_id: UUID) -> str:
        """Get or generate user's referral code.

        If the user already has a referral code, return it.
        Otherwise, generate a new 8-character uppercase code,
        persist it, and return it.
        """
        result = await self._session.execute(
            select(MobileUserModel)
            .where(MobileUserModel.id == user_id)
            .with_for_update()
        )
        user = result.scalars().one_or_none()
        if user is None:
            raise DomainError("User not found")
        if user.referral_code:
            return user.referral_code

        for _attempt in range(REFERRAL_CODE_MAX_ATTEMPTS):
            candidate = _generate_referral_code()
            existing = await self._session.execute(
                select(MobileUserModel.id).where(MobileUserModel.referral_code == candidate).limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            user.referral_code = candidate
            try:
                await self._session.flush()
                return candidate
            except IntegrityError as exc:
                await self._session.rollback()
                result = await self._session.execute(
                    select(MobileUserModel)
                    .where(MobileUserModel.id == user_id)
                    .with_for_update()
                )
                user = result.scalars().one_or_none()
                if user is None:
                    raise DomainError("User not found") from exc
                if user.referral_code:
                    return user.referral_code

        raise DomainError("Unable to allocate referral code")


def _generate_referral_code() -> str:
    return "".join(secrets.choice(REFERRAL_CODE_ALPHABET) for _ in range(REFERRAL_CODE_LENGTH))
