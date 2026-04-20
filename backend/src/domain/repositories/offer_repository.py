from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.offer import Offer


class OfferRepository(ABC):
    @abstractmethod
    async def create(self, offer: Offer) -> Offer: ...

    @abstractmethod
    async def list_active(
        self,
        *,
        at: datetime | None = None,
        sale_channel: str | None = None,
        subscription_plan_id: UUID | None = None,
    ) -> list[Offer]: ...

    @abstractmethod
    async def get_current_by_key(
        self,
        offer_key: str,
        *,
        at: datetime | None = None,
    ) -> Offer | None: ...
