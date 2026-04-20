from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.repositories.offer_repo import OfferRepository
from src.infrastructure.database.repositories.pricebook_repo import PricebookRepository


class CreatePricebookUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PricebookRepository(session)
        self._offer_repo = OfferRepository(session)

    async def execute(
        self,
        *,
        pricebook_key: str,
        display_name: str,
        storefront_id,
        merchant_profile_id,
        currency_code: str,
        region_code: str | None,
        discount_rules: dict,
        renewal_pricing_policy: dict,
        version_status: str,
        effective_from: datetime | None,
        effective_to: datetime | None,
        is_active: bool,
        entries: list[dict],
    ) -> PricebookModel:
        storefront = await self._session.get(StorefrontModel, storefront_id)
        if storefront is None:
            raise ValueError("Storefront not found")
        if merchant_profile_id is not None:
            merchant = await self._session.get(MerchantProfileModel, merchant_profile_id)
            if merchant is None:
                raise ValueError("Merchant profile not found")

        offer_ids = [entry["offer_id"] for entry in entries]
        if len(set(offer_ids)) != len(offer_ids):
            raise ValueError("Pricebook cannot contain duplicate offer entries")
        offers = await self._offer_repo.get_by_ids(offer_ids)
        if len(offers) != len(set(offer_ids)):
            raise ValueError("One or more pricebook offers do not exist")

        model = PricebookModel(
            pricebook_key=pricebook_key.strip(),
            display_name=display_name.strip(),
            storefront_id=storefront_id,
            merchant_profile_id=merchant_profile_id,
            currency_code=currency_code.upper(),
            region_code=region_code.upper() if region_code else None,
            discount_rules=discount_rules,
            renewal_pricing_policy=renewal_pricing_policy,
            version_status=version_status,
            effective_from=effective_from or datetime.now(UTC),
            effective_to=effective_to,
            is_active=is_active,
            entries=[
                PricebookEntryModel(
                    offer_id=entry["offer_id"],
                    visible_price=entry["visible_price"],
                    compare_at_price=entry.get("compare_at_price"),
                    included_addon_codes=entry.get("included_addon_codes", []),
                    display_order=entry.get("display_order", 0),
                )
                for entry in entries
            ],
        )
        return await self._repo.create(model)
