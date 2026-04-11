"""Repository for persistent customer staff notes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.customer_staff_note_model import CustomerStaffNoteModel


class CustomerStaffNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: CustomerStaffNoteModel) -> CustomerStaffNoteModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[CustomerStaffNoteModel]:
        result = await self._session.execute(
            select(CustomerStaffNoteModel)
            .where(CustomerStaffNoteModel.user_id == user_id)
            .order_by(CustomerStaffNoteModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
