"""Infrastructure repository for promo_codes and promo_code_usages tables."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.promo_code_model import (
    PromoCodeModel,
    PromoCodeUsageModel,
)


class PromoCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> PromoCodeModel | None:
        return await self._session.get(PromoCodeModel, id)

    async def get_by_code(self, code: str) -> PromoCodeModel | None:
        result = await self._session.execute(select(PromoCodeModel).where(PromoCodeModel.code == code))
        return result.scalar_one_or_none()

    async def get_active_by_code(self, code: str) -> PromoCodeModel | None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(PromoCodeModel).where(
                PromoCodeModel.code == code,
                PromoCodeModel.is_active.is_(True),
                (PromoCodeModel.expires_at.is_(None)) | (PromoCodeModel.expires_at > now),
                (PromoCodeModel.max_uses.is_(None)) | (PromoCodeModel.current_uses < PromoCodeModel.max_uses),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, offset: int = 0, limit: int = 50) -> list[PromoCodeModel]:
        result = await self._session.execute(
            select(PromoCodeModel).order_by(PromoCodeModel.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, model: PromoCodeModel) -> PromoCodeModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: PromoCodeModel) -> PromoCodeModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def increment_usage(self, id: UUID) -> None:
        await self._session.execute(
            update(PromoCodeModel).where(PromoCodeModel.id == id).values(current_uses=PromoCodeModel.current_uses + 1)
        )
        await self._session.flush()

    async def record_usage(self, usage: PromoCodeUsageModel) -> PromoCodeUsageModel:
        self._session.add(usage)
        await self._session.flush()
        return usage

    async def get_usages_by_promo(
        self, promo_code_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[PromoCodeUsageModel]:
        result = await self._session.execute(
            select(PromoCodeUsageModel)
            .where(PromoCodeUsageModel.promo_code_id == promo_code_id)
            .order_by(PromoCodeUsageModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def has_user_used(self, promo_code_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            select(PromoCodeUsageModel.id)
            .where(
                PromoCodeUsageModel.promo_code_id == promo_code_id,
                PromoCodeUsageModel.user_id == user_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
