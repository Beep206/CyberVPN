from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.domain.enums import EarningEventStatus, EarningHoldReasonType, EarningHoldStatus
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.earning_hold_model import EarningHoldModel
from src.infrastructure.database.models.partner_model import PartnerEarningModel
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository


class RecordEarningEventUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._attribution = OrderAttributionResultRepository(session)
        self._config = ConfigService(SystemConfigRepository(session))

    async def execute(
        self,
        *,
        order_id: UUID,
        legacy_partner_earning: PartnerEarningModel,
        payment_id: UUID | None = None,
        commit: bool = True,
    ) -> tuple[EarningEventModel, EarningHoldModel | None]:
        existing = await self._settlement.get_earning_event_by_order_id(order_id)
        if existing is not None:
            return existing, None

        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        payment = await self._payments.get_by_id(payment_id) if payment_id is not None else None
        attribution_result = await self._attribution.get_by_order_id(order_id)
        owner_type = attribution_result.owner_type if attribution_result is not None else "affiliate"
        hold_days = await self._config.get_partner_payout_hold_days(owner_type=owner_type)
        created_at = _normalize_utc(payment.created_at if payment is not None else None)

        event = EarningEventModel(
            partner_account_id=legacy_partner_earning.partner_account_id,
            partner_user_id=legacy_partner_earning.partner_user_id,
            client_user_id=legacy_partner_earning.client_user_id,
            order_id=order.id,
            payment_id=payment_id,
            partner_code_id=legacy_partner_earning.partner_code_id,
            legacy_partner_earning_id=legacy_partner_earning.id,
            order_attribution_result_id=(attribution_result.id if attribution_result is not None else None),
            owner_type=owner_type,
            event_status=(
                EarningEventStatus.ON_HOLD.value if hold_days > 0 else EarningEventStatus.AVAILABLE.value
            ),
            commission_base_amount=float(legacy_partner_earning.base_price),
            markup_amount=float(legacy_partner_earning.markup_amount),
            commission_pct=float(legacy_partner_earning.commission_pct),
            commission_amount=float(legacy_partner_earning.commission_amount),
            total_amount=float(legacy_partner_earning.total_earning),
            currency_code=legacy_partner_earning.currency or "USD",
            available_at=None if hold_days > 0 else created_at,
            source_snapshot={
                "order_settlement_status": order.settlement_status,
                "order_currency_code": order.currency_code,
                "legacy_partner_earning_id": str(legacy_partner_earning.id),
                "payment_id": str(payment_id) if payment_id else None,
                "owner_type": owner_type,
            },
        )
        created_event = await self._settlement.create_earning_event(event)

        created_hold = None
        if hold_days > 0:
            created_hold = await self._settlement.create_earning_hold(
                EarningHoldModel(
                    earning_event_id=created_event.id,
                    partner_account_id=created_event.partner_account_id,
                    hold_reason_type=EarningHoldReasonType.PAYOUT_HOLD.value,
                    hold_status=EarningHoldStatus.ACTIVE.value,
                    reason_code="partner_payout_hold_policy",
                    hold_until=created_at + timedelta(days=hold_days),
                    hold_payload={"owner_type": owner_type, "hold_days": hold_days},
                )
            )

        if commit:
            await self._session.commit()
            await self._session.refresh(created_event)
            if created_hold is not None:
                await self._session.refresh(created_hold)
        return created_event, created_hold


class ListEarningEventsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        order_id: UUID | None = None,
        event_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EarningEventModel]:
        return await self._settlement.list_earning_events(
            partner_account_id=partner_account_id,
            order_id=order_id,
            event_status=event_status,
            limit=limit,
            offset=offset,
        )


class GetEarningEventUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, event_id: UUID) -> EarningEventModel | None:
        return await self._settlement.get_earning_event_by_id(event_id)


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
