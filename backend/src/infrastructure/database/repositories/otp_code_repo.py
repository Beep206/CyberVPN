"""OTP Code Repository for database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.otp_code_model import OtpCodeModel


class OtpCodeRepository:
    """Repository for OTP code database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, otp: OtpCodeModel) -> OtpCodeModel:
        """Create a new OTP code record."""
        self._session.add(otp)
        await self._session.flush()
        return otp

    async def get_by_id(self, otp_id: UUID) -> OtpCodeModel | None:
        """Get OTP code by ID."""
        return await self._session.get(OtpCodeModel, otp_id)

    async def get_active_by_user_id(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
    ) -> OtpCodeModel | None:
        """
        Get the most recent active (non-verified, non-expired) OTP for a user.

        Args:
            user_id: The user's UUID
            purpose: The OTP purpose (email_verification, password_reset, login_2fa)

        Returns:
            The active OTP code or None if no active code exists
        """
        now = datetime.now().astimezone()
        result = await self._session.execute(
            select(OtpCodeModel)
            .where(
                and_(
                    OtpCodeModel.user_id == user_id,
                    OtpCodeModel.purpose == purpose,
                    OtpCodeModel.verified_at.is_(None),
                    OtpCodeModel.expires_at > now,
                    OtpCodeModel.attempts_used < OtpCodeModel.max_attempts,
                )
            )
            .order_by(OtpCodeModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id_and_code(
        self,
        user_id: UUID,
        code: str,
        purpose: str = "email_verification",
    ) -> OtpCodeModel | None:
        """
        Get OTP by user ID and code value for verification.

        Only returns non-verified codes (verified_at is None).

        Args:
            user_id: The user's UUID
            code: The 6-digit OTP code
            purpose: The OTP purpose

        Returns:
            The OTP code record or None
        """
        result = await self._session.execute(
            select(OtpCodeModel)
            .where(
                and_(
                    OtpCodeModel.user_id == user_id,
                    OtpCodeModel.code == code,
                    OtpCodeModel.purpose == purpose,
                    OtpCodeModel.verified_at.is_(None),
                )
            )
            .order_by(OtpCodeModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, otp: OtpCodeModel) -> OtpCodeModel:
        """Update an existing OTP code record."""
        await self._session.merge(otp)
        await self._session.flush()
        return otp

    async def invalidate_all_for_user(
        self,
        user_id: UUID,
        purpose: str = "email_verification",
    ) -> int:
        """
        Invalidate all active OTP codes for a user by setting them as expired.

        Used when creating a new OTP to ensure only one active code exists.

        Args:
            user_id: The user's UUID
            purpose: The OTP purpose

        Returns:
            Number of codes invalidated
        """
        now = datetime.now().astimezone()
        result = await self._session.execute(
            select(OtpCodeModel)
            .where(
                and_(
                    OtpCodeModel.user_id == user_id,
                    OtpCodeModel.purpose == purpose,
                    OtpCodeModel.verified_at.is_(None),
                    OtpCodeModel.expires_at > now,
                )
            )
        )
        codes = result.scalars().all()

        count = 0
        for code in codes:
            code.expires_at = now
            count += 1

        if count > 0:
            await self._session.flush()

        return count

    async def count_resends_in_window(
        self,
        user_id: UUID,
        window_start: datetime,
        purpose: str = "email_verification",
    ) -> int:
        """
        Count the number of OTP resends for a user within a time window.

        Used for rate limiting resend requests.

        Args:
            user_id: The user's UUID
            window_start: Start of the time window
            purpose: The OTP purpose

        Returns:
            Number of OTP codes created in the window
        """
        result = await self._session.execute(
            select(OtpCodeModel)
            .where(
                and_(
                    OtpCodeModel.user_id == user_id,
                    OtpCodeModel.purpose == purpose,
                    OtpCodeModel.created_at >= window_start,
                )
            )
        )
        return len(result.scalars().all())

    async def delete_expired(self, before_date: datetime | None = None) -> int:
        """
        Delete expired OTP codes for cleanup.

        Args:
            before_date: Delete codes that expired before this date.
                         Defaults to current time.

        Returns:
            Number of codes deleted
        """
        if before_date is None:
            before_date = datetime.now().astimezone()

        result = await self._session.execute(
            select(OtpCodeModel).where(
                and_(
                    OtpCodeModel.expires_at < before_date,
                    OtpCodeModel.verified_at.is_(None),
                )
            )
        )
        codes = result.scalars().all()

        count = 0
        for code in codes:
            await self._session.delete(code)
            count += 1

        if count > 0:
            await self._session.flush()

        return count
