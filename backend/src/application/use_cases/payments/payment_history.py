from uuid import UUID

from src.infrastructure.database.repositories.payment_repo import PaymentRepository


class PaymentHistoryUseCase:
    def __init__(self, repo: PaymentRepository) -> None:
        self._repo = repo

    async def get_by_user(self, user_uuid: UUID, offset: int = 0, limit: int = 20) -> list:
        return await self._repo.get_by_user_uuid(user_uuid, offset=offset, limit=limit)

    async def get_by_id(self, payment_id: UUID):
        return await self._repo.get_by_id(payment_id)
