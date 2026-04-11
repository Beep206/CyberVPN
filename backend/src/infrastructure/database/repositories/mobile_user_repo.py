"""Repository for mobile user database operations."""

from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel


class MobileUserRepository:
    """Repository for mobile user CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _apply_admin_filters(
        stmt,
        *,
        search: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        is_partner: bool | None = None,
        has_referral_code: bool | None = None,
    ):
        normalized_search = (search or "").strip()
        if normalized_search:
            like_pattern = f"%{normalized_search}%"
            stmt = stmt.where(
                or_(
                    MobileUserModel.email.ilike(like_pattern),
                    MobileUserModel.username.ilike(like_pattern),
                    MobileUserModel.telegram_username.ilike(like_pattern),
                    MobileUserModel.remnawave_uuid.ilike(like_pattern),
                    MobileUserModel.referral_code.ilike(like_pattern),
                    cast(MobileUserModel.id, String).ilike(like_pattern),
                    cast(MobileUserModel.telegram_id, String).ilike(like_pattern),
                )
            )

        if status:
            stmt = stmt.where(MobileUserModel.status == status)

        if is_active is not None:
            stmt = stmt.where(MobileUserModel.is_active == is_active)  # noqa: E712

        if is_partner is not None:
            stmt = stmt.where(MobileUserModel.is_partner == is_partner)  # noqa: E712

        if has_referral_code is not None:
            if has_referral_code:
                stmt = stmt.where(MobileUserModel.referral_code.is_not(None))
            else:
                stmt = stmt.where(MobileUserModel.referral_code.is_(None))

        return stmt

    async def get_by_id(self, id: UUID) -> MobileUserModel | None:
        """Get mobile user by UUID."""
        return await self._session.get(MobileUserModel, id)

    async def get_by_id_with_devices(self, id: UUID) -> MobileUserModel | None:
        """Get mobile user by UUID with devices eagerly loaded."""
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.id == id).options(selectinload(MobileUserModel.devices))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> MobileUserModel | None:
        """Get mobile user by email address."""
        result = await self._session.execute(select(MobileUserModel).where(MobileUserModel.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> MobileUserModel | None:
        """Get mobile user by username."""
        result = await self._session.execute(select(MobileUserModel).where(MobileUserModel.username == username))
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> MobileUserModel | None:
        """Get mobile user by Telegram ID."""
        result = await self._session.execute(select(MobileUserModel).where(MobileUserModel.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_remnawave_uuid(self, remnawave_uuid: str) -> MobileUserModel | None:
        """Get mobile user by Remnawave VPN user UUID."""
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.remnawave_uuid == remnawave_uuid)
        )
        return result.scalar_one_or_none()

    async def get_by_referral_code(self, referral_code: str) -> MobileUserModel | None:
        """Get mobile user by referral code."""
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.referral_code == referral_code)
        )
        return result.scalar_one_or_none()

    async def list_admin(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        is_partner: bool | None = None,
        has_referral_code: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[MobileUserModel]:
        stmt = select(MobileUserModel)
        stmt = self._apply_admin_filters(
            stmt,
            search=search,
            status=status,
            is_active=is_active,
            is_partner=is_partner,
            has_referral_code=has_referral_code,
        )
        stmt = stmt.order_by(MobileUserModel.created_at.desc()).offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_admin(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        is_partner: bool | None = None,
        has_referral_code: bool | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(MobileUserModel)
        stmt = self._apply_admin_filters(
            stmt,
            search=search,
            status=status,
            is_active=is_active,
            is_partner=is_partner,
            has_referral_code=has_referral_code,
        )

        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_by_ids(self, ids: list[UUID]) -> list[MobileUserModel]:
        if not ids:
            return []

        result = await self._session.execute(select(MobileUserModel).where(MobileUserModel.id.in_(ids)))
        return list(result.scalars().all())

    async def get_device_counts(self, user_ids: list[UUID]) -> dict[UUID, int]:
        if not user_ids:
            return {}

        result = await self._session.execute(
            select(MobileDeviceModel.user_id, func.count(MobileDeviceModel.id))
            .where(MobileDeviceModel.user_id.in_(user_ids))
            .group_by(MobileDeviceModel.user_id)
        )
        return {user_id: int(count) for user_id, count in result.all()}

    async def create(self, model: MobileUserModel) -> MobileUserModel:
        """Create new mobile user."""
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: MobileUserModel) -> MobileUserModel:
        """Update existing mobile user."""
        await self._session.merge(model)
        await self._session.flush()
        return model


class MobileDeviceRepository:
    """Repository for mobile device CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_device_id_and_user(self, device_id: str, user_id: UUID) -> MobileDeviceModel | None:
        """Get device by device_id and user_id combination."""
        result = await self._session.execute(
            select(MobileDeviceModel).where(
                MobileDeviceModel.device_id == device_id,
                MobileDeviceModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_devices(self, user_id: UUID) -> list[MobileDeviceModel]:
        """Get all devices for a user."""
        result = await self._session.execute(select(MobileDeviceModel).where(MobileDeviceModel.user_id == user_id))
        return list(result.scalars().all())

    async def create(self, model: MobileDeviceModel) -> MobileDeviceModel:
        """Create new device registration."""
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: MobileDeviceModel) -> MobileDeviceModel:
        """Update device information."""
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def delete(self, model: MobileDeviceModel) -> None:
        """Delete device registration."""
        await self._session.delete(model)
        await self._session.flush()

    async def get_by_id_for_user(self, id: UUID, user_id: UUID) -> MobileDeviceModel | None:
        result = await self._session.execute(
            select(MobileDeviceModel).where(
                MobileDeviceModel.id == id,
                MobileDeviceModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
