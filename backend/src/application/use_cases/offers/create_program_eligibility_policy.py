from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.program_eligibility_policy_repo import ProgramEligibilityPolicyRepository


class CreateProgramEligibilityPolicyUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProgramEligibilityPolicyRepository(session)

    async def execute(
        self,
        *,
        policy_key: str,
        subject_type: str,
        subscription_plan_id,
        plan_addon_id,
        offer_id,
        invite_allowed: bool,
        referral_credit_allowed: bool,
        creator_affiliate_allowed: bool,
        performance_allowed: bool,
        reseller_allowed: bool,
        renewal_commissionable: bool,
        addon_commissionable: bool,
        version_status: str,
        effective_from: datetime | None,
        effective_to: datetime | None,
        is_active: bool,
    ) -> ProgramEligibilityPolicyModel:
        if subject_type not in {"plan", "addon", "offer"}:
            raise ValueError("Unsupported subject_type")

        if subject_type == "plan":
            if (
                subscription_plan_id is None
                or await self._session.get(SubscriptionPlanModel, subscription_plan_id) is None
            ):
                raise ValueError("Referenced subscription plan does not exist")
        if subject_type == "addon":
            if plan_addon_id is None or await self._session.get(PlanAddonModel, plan_addon_id) is None:
                raise ValueError("Referenced plan add-on does not exist")
        if subject_type == "offer":
            if offer_id is None or await self._session.get(OfferModel, offer_id) is None:
                raise ValueError("Referenced offer does not exist")

        model = ProgramEligibilityPolicyModel(
            policy_key=policy_key.strip(),
            subject_type=subject_type,
            subscription_plan_id=subscription_plan_id,
            plan_addon_id=plan_addon_id,
            offer_id=offer_id,
            invite_allowed=invite_allowed,
            referral_credit_allowed=referral_credit_allowed,
            creator_affiliate_allowed=creator_affiliate_allowed,
            performance_allowed=performance_allowed,
            reseller_allowed=reseller_allowed,
            renewal_commissionable=renewal_commissionable,
            addon_commissionable=addon_commissionable,
            version_status=version_status,
            effective_from=effective_from or datetime.now(UTC),
            effective_to=effective_to,
            is_active=is_active,
        )
        return await self._repo.create(model)
