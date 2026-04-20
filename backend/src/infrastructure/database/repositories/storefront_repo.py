"""Infrastructure repository for brand and storefront core objects."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.communication_profile_model import CommunicationProfileModel
from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.support_profile_model import SupportProfileModel


class StorefrontRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_brand_by_id(self, id: UUID) -> BrandModel | None:
        return await self._session.get(BrandModel, id)

    async def get_brand_by_key(self, brand_key: str) -> BrandModel | None:
        result = await self._session.execute(select(BrandModel).where(BrandModel.brand_key == brand_key))
        return result.scalar_one_or_none()

    async def create_brand(self, model: BrandModel) -> BrandModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_brand(self, model: BrandModel) -> BrandModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def get_storefront_by_id(self, id: UUID) -> StorefrontModel | None:
        return await self._session.get(StorefrontModel, id)

    async def get_storefront_by_key(self, storefront_key: str) -> StorefrontModel | None:
        result = await self._session.execute(
            select(StorefrontModel).where(StorefrontModel.storefront_key == storefront_key)
        )
        return result.scalar_one_or_none()

    async def get_storefront_by_host(self, host: str) -> StorefrontModel | None:
        result = await self._session.execute(select(StorefrontModel).where(StorefrontModel.host == host))
        return result.scalar_one_or_none()

    async def get_storefronts_by_brand(self, brand_id: UUID) -> list[StorefrontModel]:
        result = await self._session.execute(select(StorefrontModel).where(StorefrontModel.brand_id == brand_id))
        return list(result.scalars().all())

    async def create_storefront(self, model: StorefrontModel) -> StorefrontModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_storefront(self, model: StorefrontModel) -> StorefrontModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def get_merchant_profile_by_id(self, id: UUID) -> MerchantProfileModel | None:
        return await self._session.get(MerchantProfileModel, id)

    async def create_merchant_profile(self, model: MerchantProfileModel) -> MerchantProfileModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_invoice_profile_by_id(self, id: UUID) -> InvoiceProfileModel | None:
        return await self._session.get(InvoiceProfileModel, id)

    async def create_invoice_profile(self, model: InvoiceProfileModel) -> InvoiceProfileModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_billing_descriptor_by_id(self, id: UUID) -> BillingDescriptorModel | None:
        return await self._session.get(BillingDescriptorModel, id)

    async def create_billing_descriptor(self, model: BillingDescriptorModel) -> BillingDescriptorModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_support_profile_by_id(self, id: UUID) -> SupportProfileModel | None:
        return await self._session.get(SupportProfileModel, id)

    async def create_support_profile(self, model: SupportProfileModel) -> SupportProfileModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_communication_profile_by_id(self, id: UUID) -> CommunicationProfileModel | None:
        return await self._session.get(CommunicationProfileModel, id)

    async def create_communication_profile(
        self, model: CommunicationProfileModel
    ) -> CommunicationProfileModel:
        self._session.add(model)
        await self._session.flush()
        return model
