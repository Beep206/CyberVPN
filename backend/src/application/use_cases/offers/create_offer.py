from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.offer_repo import OfferRepository


class CreateOfferUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OfferRepository(session)

    async def execute(
        self,
        *,
        offer_key: str,
        display_name: str,
        subscription_plan_id,
        included_addon_codes: list[str],
        sale_channels: list[str],
        visibility_rules: dict,
        invite_bundle: dict,
        trial_eligible: bool,
        gift_eligible: bool,
        referral_eligible: bool,
        renewal_incentives: dict,
        version_status: str,
        effective_from: datetime | None,
        effective_to: datetime | None,
        is_active: bool,
    ) -> OfferModel:
        plan = await self._session.get(SubscriptionPlanModel, subscription_plan_id)
        if plan is None:
            raise ValueError("Subscription plan not found")

        if included_addon_codes:
            addon_rows = (
                await self._session.execute(
                    select(PlanAddonModel.code).where(PlanAddonModel.code.in_(included_addon_codes))
                )
            ).scalars().all()
            if len(set(addon_rows)) != len(set(included_addon_codes)):
                raise ValueError("One or more included add-on codes do not exist")

        model = OfferModel(
            offer_key=offer_key.strip(),
            display_name=display_name.strip(),
            subscription_plan_id=subscription_plan_id,
            included_addon_codes=included_addon_codes,
            sale_channels=sale_channels,
            visibility_rules=visibility_rules,
            invite_bundle=invite_bundle,
            trial_eligible=trial_eligible,
            gift_eligible=gift_eligible,
            referral_eligible=referral_eligible,
            renewal_incentives=renewal_incentives,
            version_status=version_status,
            effective_from=effective_from or datetime.now(UTC),
            effective_to=effective_to,
            is_active=is_active,
        )
        return await self._repo.create(model)
