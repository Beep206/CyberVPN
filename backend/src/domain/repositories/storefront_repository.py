from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.storefront import (
    BillingDescriptor,
    Brand,
    CommunicationProfile,
    InvoiceProfile,
    MerchantProfile,
    Storefront,
    SupportProfile,
)


class StorefrontRepository(ABC):
    @abstractmethod
    async def get_brand_by_id(self, id: UUID) -> Brand | None: ...

    @abstractmethod
    async def get_brand_by_key(self, brand_key: str) -> Brand | None: ...

    @abstractmethod
    async def create_brand(self, brand: Brand) -> Brand: ...

    @abstractmethod
    async def update_brand(self, brand: Brand) -> Brand: ...

    @abstractmethod
    async def get_storefront_by_id(self, id: UUID) -> Storefront | None: ...

    @abstractmethod
    async def get_storefront_by_key(self, storefront_key: str) -> Storefront | None: ...

    @abstractmethod
    async def get_storefront_by_host(self, host: str) -> Storefront | None: ...

    @abstractmethod
    async def create_storefront(self, storefront: Storefront) -> Storefront: ...

    @abstractmethod
    async def update_storefront(self, storefront: Storefront) -> Storefront: ...

    @abstractmethod
    async def get_merchant_profile_by_id(self, id: UUID) -> MerchantProfile | None: ...

    @abstractmethod
    async def create_merchant_profile(self, profile: MerchantProfile) -> MerchantProfile: ...

    @abstractmethod
    async def get_invoice_profile_by_id(self, id: UUID) -> InvoiceProfile | None: ...

    @abstractmethod
    async def create_invoice_profile(self, profile: InvoiceProfile) -> InvoiceProfile: ...

    @abstractmethod
    async def get_billing_descriptor_by_id(self, id: UUID) -> BillingDescriptor | None: ...

    @abstractmethod
    async def create_billing_descriptor(self, descriptor: BillingDescriptor) -> BillingDescriptor: ...

    @abstractmethod
    async def get_support_profile_by_id(self, id: UUID) -> SupportProfile | None: ...

    @abstractmethod
    async def create_support_profile(self, profile: SupportProfile) -> SupportProfile: ...

    @abstractmethod
    async def get_communication_profile_by_id(self, id: UUID) -> CommunicationProfile | None: ...

    @abstractmethod
    async def create_communication_profile(
        self, profile: CommunicationProfile
    ) -> CommunicationProfile: ...
