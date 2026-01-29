from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.payment import Payment


class PaymentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Payment | None: ...

    @abstractmethod
    async def get_by_external_id(self, external_id: str) -> Payment | None: ...

    @abstractmethod
    async def get_by_user(self, user_uuid: UUID, offset: int = 0, limit: int = 100) -> list[Payment]: ...

    @abstractmethod
    async def create(self, payment: Payment) -> Payment: ...

    @abstractmethod
    async def update(self, payment: Payment) -> Payment: ...
