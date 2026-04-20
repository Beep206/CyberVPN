from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel


class CommerceSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_quote_session(self, model: QuoteSessionModel) -> QuoteSessionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_quote_session_by_id(self, quote_session_id: UUID) -> QuoteSessionModel | None:
        return await self._session.get(QuoteSessionModel, quote_session_id)

    async def create_checkout_session(self, model: CheckoutSessionModel) -> CheckoutSessionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_checkout_session_by_id(self, checkout_session_id: UUID) -> CheckoutSessionModel | None:
        return await self._session.get(CheckoutSessionModel, checkout_session_id)

    async def get_checkout_session_by_quote_session_id(
        self,
        quote_session_id: UUID,
    ) -> CheckoutSessionModel | None:
        result = await self._session.execute(
            select(CheckoutSessionModel).where(CheckoutSessionModel.quote_session_id == quote_session_id)
        )
        return result.scalar_one_or_none()
