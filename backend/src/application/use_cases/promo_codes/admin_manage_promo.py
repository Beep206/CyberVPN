"""Use case for admin CRUD operations on promo codes."""

from datetime import datetime
from uuid import UUID

from src.domain.exceptions import PromoCodeNotFoundError
from src.infrastructure.database.models.promo_code_model import (
    PromoCodeModel,
    PromoCodeUsageModel,
)
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository


class AdminManagePromoUseCase:
    def __init__(self, promo_repo: PromoCodeRepository) -> None:
        self._repo = promo_repo

    async def create(
        self,
        code: str,
        discount_type: str,
        discount_value: float,
        created_by: UUID | None = None,
        *,
        max_uses: int | None = None,
        is_single_use: bool = False,
        plan_ids: list[UUID] | None = None,
        min_amount: float | None = None,
        expires_at: datetime | None = None,
        description: str | None = None,
        currency: str = "USD",
    ) -> PromoCodeModel:
        model = PromoCodeModel(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            created_by=created_by,
            max_uses=max_uses,
            is_single_use=is_single_use,
            plan_ids=plan_ids,
            min_amount=min_amount,
            expires_at=expires_at,
            description=description,
            currency=currency,
        )
        return await self._repo.create(model)

    async def update(self, promo_id: UUID, **kwargs) -> PromoCodeModel:
        promo = await self._repo.get_by_id(promo_id)
        if promo is None:
            raise PromoCodeNotFoundError(str(promo_id))

        allowed_fields = {
            "is_active",
            "max_uses",
            "expires_at",
            "description",
            "discount_value",
        }
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(promo, field, value)

        return await self._repo.update(promo)

    async def deactivate(self, promo_id: UUID) -> PromoCodeModel:
        promo = await self._repo.get_by_id(promo_id)
        if promo is None:
            raise PromoCodeNotFoundError(str(promo_id))

        promo.is_active = False
        return await self._repo.update(promo)

    async def list_all(self, offset: int = 0, limit: int = 50) -> list[PromoCodeModel]:
        return await self._repo.get_all(offset=offset, limit=limit)

    async def get_detail(self, promo_id: UUID) -> PromoCodeModel:
        promo = await self._repo.get_by_id(promo_id)
        if promo is None:
            raise PromoCodeNotFoundError(str(promo_id))
        return promo

    async def get_usages(self, promo_id: UUID, offset: int = 0, limit: int = 50) -> list[PromoCodeUsageModel]:
        return await self._repo.get_usages_by_promo(promo_code_id=promo_id, offset=offset, limit=limit)
