from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.pricebook import Pricebook


class PricebookRepository(ABC):
    @abstractmethod
    async def create(self, pricebook: Pricebook) -> Pricebook: ...

    @abstractmethod
    async def list_active(
        self,
        *,
        storefront_id: UUID | None = None,
        at: datetime | None = None,
        currency_code: str | None = None,
        region_code: str | None = None,
    ) -> list[Pricebook]: ...

    @abstractmethod
    async def get_current_by_key(
        self,
        pricebook_key: str,
        *,
        at: datetime | None = None,
    ) -> Pricebook | None: ...
