from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class ListMerchantProfilesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, include_inactive: bool = False) -> list[MerchantProfileModel]:
        stmt = select(MerchantProfileModel).order_by(MerchantProfileModel.profile_key)
        if not include_inactive:
            stmt = stmt.where(MerchantProfileModel.status == "active")
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ResolveMerchantProfileUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = StorefrontRepository(session)

    async def execute(
        self,
        *,
        storefront_id=None,
        storefront_key: str | None = None,
    ) -> MerchantProfileModel | None:
        storefront = None
        if storefront_id is not None:
            storefront = await self._repo.get_storefront_by_id(storefront_id)
        elif storefront_key is not None:
            storefront = await self._repo.get_storefront_by_key(storefront_key)
        else:
            raise ValueError("storefront_id or storefront_key is required")
        if storefront is None or storefront.merchant_profile_id is None:
            return None
        return await self._repo.get_merchant_profile_by_id(storefront.merchant_profile_id)


class CreateMerchantProfileUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StorefrontRepository(session)

    async def execute(
        self,
        *,
        profile_key: str,
        legal_entity_name: str,
        billing_descriptor: str,
        invoice_profile_id,
        settlement_reference: str | None,
        supported_currencies: list[str],
        tax_behavior: dict,
        refund_responsibility_model: str,
        chargeback_liability_model: str,
        status: str,
    ) -> MerchantProfileModel:
        if invoice_profile_id is not None:
            invoice_profile = await self._repo.get_invoice_profile_by_id(invoice_profile_id)
            if invoice_profile is None:
                raise ValueError("Invoice profile not found")

        normalized_currencies = sorted({code.strip().upper() for code in supported_currencies if code.strip()})
        model = MerchantProfileModel(
            profile_key=profile_key.strip(),
            legal_entity_name=legal_entity_name.strip(),
            billing_descriptor=billing_descriptor.strip(),
            invoice_profile_id=invoice_profile_id,
            settlement_reference=settlement_reference.strip() if settlement_reference else None,
            supported_currencies=normalized_currencies,
            tax_behavior=tax_behavior,
            refund_responsibility_model=refund_responsibility_model,
            chargeback_liability_model=chargeback_liability_model,
            status=status,
        )
        created = await self._repo.create_merchant_profile(model)
        await self._session.commit()
        await self._session.refresh(created)
        return created
