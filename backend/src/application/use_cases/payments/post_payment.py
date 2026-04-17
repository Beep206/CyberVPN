"""Post-payment processing: invites, commissions, wallet debit, promo tracking."""

import logging
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.services.wallet_service import WalletService
from src.application.use_cases.invites.generate_invites import (
    GenerateInvitesForPaymentUseCase,
)
from src.application.use_cases.partners.process_partner_earning import (
    ProcessPartnerEarningUseCase,
)
from src.application.use_cases.referrals.process_referral_commission import (
    ProcessReferralCommissionUseCase,
)
from src.domain.enums import WalletTxReason
from src.infrastructure.database.models.plan_addon_model import SubscriptionAddonModel
from src.infrastructure.database.models.promo_code_model import PromoCodeUsageModel
from src.infrastructure.database.repositories.invite_code_repo import (
    InviteCodeRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileUserRepository,
)
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.plan_addon_repo import (
    SubscriptionAddonRepository,
)
from src.infrastructure.database.repositories.promo_code_repo import (
    PromoCodeRepository,
)
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)
from src.infrastructure.database.repositories.subscription_plan_repo import (
    SubscriptionPlanRepository,
)
from src.infrastructure.database.repositories.system_config_repo import (
    SystemConfigRepository,
)
from src.infrastructure.database.repositories.wallet_repo import WalletRepository

logger = logging.getLogger(__name__)


class PostPaymentProcessingUseCase:
    """Orchestrate all post-payment side effects after a successful payment.

    Designed to run in the backend (not the task-worker) within a single
    ``AsyncSession`` that is committed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

        # Repositories
        self._payment_repo = PaymentRepository(session)
        self._promo_repo = PromoCodeRepository(session)
        self._user_repo = MobileUserRepository(session)
        self._subscription_addons = SubscriptionAddonRepository(session)

        # Services
        config_repo = SystemConfigRepository(session)
        self._config = ConfigService(config_repo)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

        # Sub-use-cases
        invite_repo = InviteCodeRepository(session)
        plan_repo = SubscriptionPlanRepository(session)
        self._generate_invites = GenerateInvitesForPaymentUseCase(
            invite_repo=invite_repo,
            plan_repo=plan_repo,
        )

        commission_repo = ReferralCommissionRepository(session)
        self._process_referral = ProcessReferralCommissionUseCase(
            commission_repo=commission_repo,
            wallet_service=self._wallet,
            config_service=self._config,
        )

        partner_repo = PartnerRepository(session)
        self._process_partner = ProcessPartnerEarningUseCase(
            partner_repo=partner_repo,
            wallet_service=self._wallet,
            config_service=self._config,
        )

    async def execute(self, payment_id: UUID) -> dict:
        """Run all post-payment processing for a completed payment.

        Returns a dict summarising the outcome of each step for
        logging and debugging purposes.
        """
        payment = await self._payment_repo.get_by_id(payment_id)
        if payment is None:
            logger.error(
                "post_payment_not_found",
                extra={"payment_id": str(payment_id)},
            )
            return {"error": "payment_not_found"}

        results: dict = {"payment_id": str(payment_id)}
        commission_base_amount = Decimal(str((payment.metadata_ or {}).get("commission_base_amount", payment.amount)))
        checkout_mode = str((payment.metadata_ or {}).get("checkout_mode", "new_purchase"))

        # Look up the paying user once for referral/partner resolution.
        user = await self._user_repo.get_by_id(payment.user_uuid)

        # ------------------------------------------------------------------
        # 1. Activate purchased add-ons
        # ------------------------------------------------------------------
        addon_lines = payment.addons_snapshot or []
        if addon_lines:
            try:
                expires_at = (
                    payment.created_at + timedelta(days=payment.subscription_days)
                    if payment.subscription_days > 0
                    else None
                )
                addon_models = [
                    SubscriptionAddonModel(
                        user_id=payment.user_uuid,
                        plan_addon_id=UUID(str(line["addon_id"])),
                        payment_id=payment.id,
                        quantity=int(line.get("qty", 1)),
                        location_code=line.get("location_code"),
                        status="active",
                        starts_at=payment.created_at,
                        expires_at=expires_at,
                        metadata_={
                            "code": line.get("code"),
                            "unit_price": line.get("unit_price"),
                        },
                    )
                    for line in addon_lines
                    if line.get("addon_id")
                ]
                if addon_models:
                    await self._subscription_addons.create_batch(addon_models)
                results["addons_activated"] = len(addon_models)
            except Exception:
                logger.exception(
                    "post_payment_addon_activation_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["addons_activated"] = 0
        else:
            results["addons_activated"] = 0

        # ------------------------------------------------------------------
        # 1b. Extend existing add-ons for subscription upgrades
        # ------------------------------------------------------------------
        if checkout_mode == "upgrade" and payment.subscription_days > 0:
            try:
                upgrade_expires_at = payment.created_at + timedelta(days=payment.subscription_days)
                active_addons = await self._subscription_addons.list_active_for_user(
                    payment.user_uuid,
                    at=payment.created_at,
                )
                extended_count = 0
                for active_addon in active_addons:
                    if active_addon.expires_at is None or active_addon.expires_at < upgrade_expires_at:
                        active_addon.expires_at = upgrade_expires_at
                        extended_count += 1
                await self._session.flush()
                results["addons_extended"] = extended_count
            except Exception:
                logger.exception(
                    "post_payment_addon_extension_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["addons_extended"] = 0
        else:
            results["addons_extended"] = 0

        # ------------------------------------------------------------------
        # 2. Generate invite codes
        # ------------------------------------------------------------------
        if payment.plan_id:
            try:
                invites = await self._generate_invites.execute(
                    owner_user_id=payment.user_uuid,
                    plan_id=payment.plan_id,
                    payment_id=payment.id,
                )
                results["invites_generated"] = len(invites)
            except Exception:
                logger.exception(
                    "post_payment_invite_generation_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["invites_generated"] = 0

        # ------------------------------------------------------------------
        # 3. Process referral commission
        # ------------------------------------------------------------------
        referrer_id = user.referred_by_user_id if user else None
        if referrer_id is not None and commission_base_amount > 0:
            try:
                commission = await self._process_referral.execute(
                    referrer_user_id=referrer_id,
                    referred_user_id=payment.user_uuid,
                    payment_id=payment.id,
                    base_amount=commission_base_amount,
                )
                results["referral_commission"] = float(commission.commission_amount) if commission else None
            except Exception:
                logger.exception(
                    "post_payment_referral_commission_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["referral_commission"] = None
        else:
            results["referral_commission"] = None

        # ------------------------------------------------------------------
        # 4. Process partner earning
        # ------------------------------------------------------------------
        if payment.partner_code_id and user and user.partner_user_id and commission_base_amount > 0:
            try:
                earning = await self._process_partner.execute(
                    partner_user_id=user.partner_user_id,
                    client_user_id=payment.user_uuid,
                    payment_id=payment.id,
                    partner_code_id=payment.partner_code_id,
                    base_price=commission_base_amount,
                )
                results["partner_earning"] = float(earning.total_earning)
            except Exception:
                logger.exception(
                    "post_payment_partner_earning_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["partner_earning"] = None
        else:
            results["partner_earning"] = None

        # ------------------------------------------------------------------
        # 5. Debit wallet amount
        # ------------------------------------------------------------------
        wallet_used = Decimal(str(payment.wallet_amount_used or 0))
        if wallet_used > 0:
            try:
                wallet = await self._wallet.get_balance(payment.user_uuid)
                await self._wallet.debit(
                    user_id=payment.user_uuid,
                    amount=wallet_used,
                    reason=WalletTxReason.SUBSCRIPTION_PAYMENT,
                    description=f"Payment {payment_id}",
                    reference_type="payment",
                    reference_id=payment_id,
                )
                frozen_amount = Decimal(str(wallet.frozen or 0))
                if frozen_amount >= wallet_used:
                    await self._wallet.unfreeze(payment.user_uuid, wallet_used)
                results["wallet_debited"] = float(wallet_used)
            except Exception:
                logger.exception(
                    "post_payment_wallet_debit_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["wallet_debited"] = None

        # ------------------------------------------------------------------
        # 6. Increment promo code usage
        # ------------------------------------------------------------------
        if payment.promo_code_id:
            try:
                await self._promo_repo.increment_usage(payment.promo_code_id)
                usage = PromoCodeUsageModel(
                    promo_code_id=payment.promo_code_id,
                    user_id=payment.user_uuid,
                    payment_id=payment.id,
                    discount_applied=Decimal(str(payment.discount_amount or 0)),
                )
                await self._promo_repo.record_usage(usage)
                results["promo_usage_recorded"] = True
            except Exception:
                logger.exception(
                    "post_payment_promo_usage_failed",
                    extra={"payment_id": str(payment_id)},
                )
                results["promo_usage_recorded"] = False

        logger.info("post_payment_processing_completed", extra=results)
        return results
