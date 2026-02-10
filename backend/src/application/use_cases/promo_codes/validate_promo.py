"""Use case for validating and calculating promo code discounts."""

from decimal import Decimal
from uuid import UUID

from src.domain.enums import DiscountType
from src.domain.exceptions import PromoCodeInvalidError, PromoCodeNotFoundError
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository


class ValidatePromoUseCase:
    def __init__(self, promo_repo: PromoCodeRepository) -> None:
        self._repo = promo_repo

    async def execute(
        self,
        code: str,
        user_id: UUID,
        plan_id: UUID | None = None,
        amount: Decimal | None = None,
    ) -> dict:
        promo = await self._repo.get_active_by_code(code)
        if promo is None:
            raise PromoCodeNotFoundError(code)

        if promo.is_single_use and await self._repo.has_user_used(promo.id, user_id):
            raise PromoCodeInvalidError("Already used by this user")

        if promo.plan_ids is not None and plan_id not in promo.plan_ids:
            raise PromoCodeInvalidError("Not valid for this plan")

        if promo.min_amount is not None and amount is not None and amount < Decimal(str(promo.min_amount)):
            raise PromoCodeInvalidError("Below minimum amount")

        discount = self._calculate_discount(
            discount_type=promo.discount_type,
            discount_value=Decimal(str(promo.discount_value)),
            amount=amount,
        )

        return {
            "promo_code_id": promo.id,
            "discount_type": promo.discount_type,
            "discount_value": float(promo.discount_value),
            "discount_amount": float(discount),
            "code": promo.code,
        }

    @staticmethod
    def _calculate_discount(
        discount_type: str,
        discount_value: Decimal,
        amount: Decimal | None,
    ) -> Decimal:
        if discount_type == DiscountType.PERCENT:
            if amount is None:
                return Decimal("0")
            calculated = amount * (discount_value / Decimal("100"))
            return min(calculated, amount)

        # DiscountType.FIXED
        if amount is not None:
            return min(discount_value, amount)
        return discount_value
