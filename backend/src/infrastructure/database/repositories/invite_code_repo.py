from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.invite_code_model import InviteCodeModel


class InviteCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> InviteCodeModel | None:
        return await self._session.get(InviteCodeModel, id)

    async def get_by_code(self, code: str) -> InviteCodeModel | None:
        result = await self._session.execute(select(InviteCodeModel).where(InviteCodeModel.code == code))
        return result.scalar_one_or_none()

    async def get_by_code_for_update(self, code: str) -> InviteCodeModel | None:
        result = await self._session.execute(
            select(InviteCodeModel).where(InviteCodeModel.code == code).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_user_id: UUID, offset: int = 0, limit: int = 50) -> list[InviteCodeModel]:
        now = datetime.now(UTC)
        revoked = (InviteCodeModel.revoked_at.is_not(None)) | (InviteCodeModel.status.in_(("revoked", "blocked")))
        expired_status = InviteCodeModel.status == "expired"
        expired_by_date = (InviteCodeModel.expires_at.is_not(None)) & (InviteCodeModel.expires_at <= now)
        expired = expired_status | expired_by_date
        multi_use_redeemable = (
            InviteCodeModel.usage_mode == "multi_use",
            ~revoked
            & ~expired
            & (InviteCodeModel.status != "exhausted")
            & InviteCodeModel.exhausted_at.is_(None)
            & (
                InviteCodeModel.max_redemptions.is_(None)
                | (InviteCodeModel.active_redemptions_count < InviteCodeModel.max_redemptions)
            ),
        )
        single_use_redeemable = (
            InviteCodeModel.usage_mode != "multi_use",
            ~revoked & ~expired & InviteCodeModel.is_used.is_(False),
        )
        status_sort_order = case(
            (multi_use_redeemable[0] & multi_use_redeemable[1], 0),
            (single_use_redeemable[0] & single_use_redeemable[1], 0),
            (revoked, 4),
            (expired_status, 3),
            (
                (InviteCodeModel.status.in_(("redeemed", "used", "exhausted"))) | (InviteCodeModel.is_used.is_(True)),
                2,
            ),
            (expired_by_date, 3),
            else_=5,
        )
        result = await self._session.execute(
            select(InviteCodeModel)
            .where(InviteCodeModel.owner_user_id == owner_user_id)
            .order_by(
                status_sort_order.asc(),
                InviteCodeModel.expires_at.asc().nulls_last(),
                InviteCodeModel.used_at.desc().nulls_last(),
                InviteCodeModel.created_at.desc(),
                InviteCodeModel.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_available_by_code(self, code: str) -> InviteCodeModel | None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(InviteCodeModel).where(
                InviteCodeModel.code == code,
                InviteCodeModel.is_used == False,  # noqa: E712
                (InviteCodeModel.expires_at.is_(None)) | (InviteCodeModel.expires_at > now),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, model: InviteCodeModel) -> InviteCodeModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def create_batch(self, models: list[InviteCodeModel]) -> list[InviteCodeModel]:
        self._session.add_all(models)
        await self._session.flush()
        return models

    async def mark_used(self, id: UUID, used_by_user_id: UUID) -> InviteCodeModel | None:
        invite_code = await self._session.get(InviteCodeModel, id)
        if invite_code is None:
            return None
        invite_code.is_used = True
        invite_code.used_by_user_id = used_by_user_id
        invite_code.used_at = datetime.now(UTC)
        invite_code.status = "redeemed"
        await self._session.flush()
        return invite_code
