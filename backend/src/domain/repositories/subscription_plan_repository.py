from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.subscription_plan import SubscriptionPlan


class SubscriptionPlanRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[SubscriptionPlan]: ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> SubscriptionPlan | None: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> SubscriptionPlan | None: ...

    @abstractmethod
    async def create(self, plan: SubscriptionPlan) -> SubscriptionPlan: ...

    @abstractmethod
    async def update(self, plan: SubscriptionPlan) -> SubscriptionPlan: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
