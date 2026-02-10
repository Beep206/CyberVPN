"""Unified checkout use case combining plan + promo + wallet + partner resolution.

Price calculation order:
1. Base price (from subscription plan)
2. + Partner markup: base * (1 + markup_pct/100) = displayed price
3. - Promo discount: displayed * discount% = after_promo
4. - Wallet balance (user-chosen amount, capped at after_promo)
5. = Gateway charge (CryptoBot invoice amount)

Commissions always use BASE price (not discounted).
If promo+wallet fully cover payment, complete immediately without gateway.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.services.wallet_service import WalletService
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository

logger = logging.getLogger(__name__)


@dataclass
class CheckoutResult:
    """Result of checkout price calculation."""

    base_price: Decimal
    displayed_price: Decimal  # base + partner markup
    discount_amount: Decimal
    wallet_amount: Decimal
    gateway_amount: Decimal  # what to charge via CryptoBot
    partner_markup: Decimal
    is_zero_gateway: bool  # True if no gateway payment needed

    # IDs for tracking
    plan_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None


class CheckoutUseCase:
    """Calculate final payment amounts for subscription purchase."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plan_repo = SubscriptionPlanRepository(session)
        config_repo = SystemConfigRepository(session)
        self._config = ConfigService(config_repo)
        self._promo_repo = PromoCodeRepository(session)
        self._partner_repo = PartnerRepository(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(
        self,
        user_id: UUID,
        plan_id: UUID,
        promo_code: str | None = None,
        use_wallet: Decimal = Decimal("0"),
    ) -> CheckoutResult:
        # 1. Resolve plan
        plan = await self._plan_repo.get_by_id(plan_id)
        if plan is None:
            msg = f"Plan not found: {plan_id}"
            raise ValueError(msg)

        base_price = Decimal(str(plan.price_usd))

        # 2. Resolve partner markup
        partner_markup = Decimal("0")
        partner_code_id = None

        user = await self._session.get(MobileUserModel, user_id)
        if user and user.partner_user_id:
            # Find the active partner code for this partner
            codes = await self._partner_repo.get_codes_by_partner(user.partner_user_id)
            active_code = next((c for c in codes if c.is_active), None)
            if active_code:
                partner_markup = base_price * (Decimal(str(active_code.markup_pct)) / Decimal("100"))
                partner_code_id = active_code.id

        displayed_price = base_price + partner_markup

        # 3. Apply promo discount
        discount_amount = Decimal("0")
        promo_code_id = None

        if promo_code:
            promo = await self._promo_repo.get_active_by_code(promo_code)
            if promo:
                promo_code_id = promo.id
                if promo.discount_type == "percent":
                    discount_amount = displayed_price * (Decimal(str(promo.discount_value)) / Decimal("100"))
                else:  # fixed
                    discount_amount = min(Decimal(str(promo.discount_value)), displayed_price)

        after_promo = displayed_price - discount_amount

        # 4. Apply wallet balance
        wallet_amount = Decimal("0")
        if use_wallet > 0:
            wallet = await self._wallet.get_balance(user_id)
            available = Decimal(str(wallet.balance)) - Decimal(str(wallet.frozen))
            wallet_amount = min(use_wallet, available, after_promo)

        # 5. Calculate gateway amount
        gateway_amount = after_promo - wallet_amount
        is_zero_gateway = gateway_amount <= 0

        if gateway_amount < 0:
            gateway_amount = Decimal("0")

        logger.info(
            "Checkout calculated",
            extra={
                "user_id": str(user_id),
                "base": str(base_price),
                "markup": str(partner_markup),
                "discount": str(discount_amount),
                "wallet": str(wallet_amount),
                "gateway": str(gateway_amount),
                "zero_gateway": is_zero_gateway,
            },
        )

        return CheckoutResult(
            base_price=base_price,
            displayed_price=displayed_price,
            discount_amount=discount_amount,
            wallet_amount=wallet_amount,
            gateway_amount=gateway_amount,
            partner_markup=partner_markup,
            is_zero_gateway=is_zero_gateway,
            plan_id=plan_id,
            promo_code_id=promo_code_id,
            partner_code_id=partner_code_id,
        )
