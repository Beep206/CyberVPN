from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.settlement.commission_terms import (
    PartnerEarningSnapshotIncompleteError,
    calculate_partner_earning_amounts,
    extract_partner_commission_terms,
)
from src.domain.enums import EarningEventStatus, EarningHoldReasonType, EarningHoldStatus
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.earning_hold_model import EarningHoldModel
from src.infrastructure.database.models.partner_model import PartnerEarningModel
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.renewal_order_repo import RenewalOrderRepository
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
            earning_component="partner_cash",
            event_status=(EarningEventStatus.ON_HOLD.value if hold_days > 0 else EarningEventStatus.AVAILABLE.value),
            commission_base_amount=Decimal(str(legacy_partner_earning.base_price)),
            markup_amount=Decimal(str(legacy_partner_earning.markup_amount)),
            commission_pct=Decimal(str(legacy_partner_earning.commission_pct)),
            commission_amount=Decimal(str(legacy_partner_earning.commission_amount)),
            total_amount=Decimal(str(legacy_partner_earning.total_earning)),
            currency_code=legacy_partner_earning.currency or "USD",
            available_at=None if hold_days > 0 else created_at,
            created_at=created_at,
            updated_at=created_at,
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
                    created_at=created_at,
                    updated_at=created_at,
                )
            )

        if commit:
            await self._session.commit()
            await self._session.refresh(created_event)
            if created_hold is not None:
                await self._session.refresh(created_hold)
        return created_event, created_hold


class CreatePartnerEarningEventFromPaymentUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._attribution = OrderAttributionResultRepository(session)
        self._renewals = RenewalOrderRepository(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        payment_id: UUID,
        commission_base_amount: Decimal,
        source_event_id: str | None = None,
        commit: bool = True,
    ) -> tuple[EarningEventModel | None, EarningHoldModel | None]:
        event_id = source_event_id or str(payment_id)
        source_event_key = f"payment.completed:{event_id}"
        existing_by_key = await self._settlement.get_earning_event_by_source_event_key(source_event_key)
        if existing_by_key is not None:
            return existing_by_key, None
        existing_by_order = await self._settlement.get_earning_event_by_order_id(order_id)
        if existing_by_order is not None:
            return existing_by_order, None

        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        attribution_result = await self._attribution.get_by_order_id(order_id)
        renewal_order = None
        terms_source_result = attribution_result
        owner_type = attribution_result.owner_type if attribution_result is not None else "none"
        owner_source = attribution_result.owner_source if attribution_result is not None else None
        partner_account_id = attribution_result.partner_account_id if attribution_result is not None else None
        partner_code_id = attribution_result.partner_code_id if attribution_result is not None else None
        policy_snapshot = dict(attribution_result.policy_snapshot or {}) if attribution_result is not None else {}
        policy_version_id = attribution_result.policy_version_id if attribution_result is not None else None
        commission_contract_id = attribution_result.commission_contract_id if attribution_result is not None else None

        if attribution_result is None or attribution_result.owner_type == "none":
            renewal_order = await self._renewals.get_by_order_id(order_id)
            if (
                renewal_order is None
                or renewal_order.effective_owner_type == "none"
                or not renewal_order.payout_eligible
            ):
                return None, None
            if renewal_order.originating_attribution_result_id is None:
                raise PartnerEarningSnapshotIncompleteError(["renewal_originating_attribution_result"])
            terms_source_result = await self._attribution.get_by_id(renewal_order.originating_attribution_result_id)
            if terms_source_result is None:
                raise PartnerEarningSnapshotIncompleteError(["renewal_originating_attribution_result"])
            owner_type = renewal_order.effective_owner_type
            owner_source = renewal_order.effective_owner_source
            partner_account_id = renewal_order.effective_partner_account_id or terms_source_result.partner_account_id
            partner_code_id = renewal_order.effective_partner_code_id or terms_source_result.partner_code_id
            policy_snapshot = dict(terms_source_result.policy_snapshot or {})
            policy_version_id = terms_source_result.policy_version_id
            commission_contract_id = terms_source_result.commission_contract_id

        terms = extract_partner_commission_terms(
            policy_snapshot,
            expected_partner_account_id=partner_account_id,
            expected_partner_user_id=None,
            expected_partner_code_id=partner_code_id,
            expected_owner_type=owner_type,
            expected_commission_contract_id=commission_contract_id,
        )
        partner_account_id = partner_account_id or terms.partner_account_id
        partner_user_id = terms.partner_user_id
        if partner_account_id is None and partner_user_id is None:
            raise PartnerEarningSnapshotIncompleteError(["partner_owner"])
        payment_currency = str(payment.currency or order.currency_code or "USD").upper()
        if payment_currency != terms.currency_code:
            raise PartnerEarningSnapshotIncompleteError(["currency_code_mismatch"])

        commercial_snapshot = dict(policy_snapshot.get("commercial_policy_snapshot") or {})
        base_amount = Decimal(str(order.commission_base_amount))
        requested_commission_base_amount = Decimal(str(commission_base_amount))
        calculated = calculate_partner_earning_amounts(base_amount=base_amount, terms=terms)
        hold_days = terms.payout_hold_days
        created_at = _normalize_utc(payment.created_at)

        event = EarningEventModel(
            partner_account_id=partner_account_id,
            partner_user_id=partner_user_id,
            client_user_id=payment.user_uuid,
            order_id=order.id,
            payment_id=payment.id,
            source_event_id=event_id,
            source_event_key=source_event_key,
            partner_code_id=partner_code_id,
            legacy_partner_earning_id=None,
            order_attribution_result_id=terms_source_result.id if terms_source_result is not None else None,
            policy_version_id=policy_version_id,
            commission_contract_id=commission_contract_id,
            owner_type=owner_type,
            earning_component="partner_cash",
            event_status=(EarningEventStatus.ON_HOLD.value if hold_days > 0 else EarningEventStatus.AVAILABLE.value),
            commission_base_amount=calculated["commission_base_amount"],
            markup_amount=calculated["markup_amount"],
            commission_pct=terms.commission_pct,
            commission_amount=calculated["commission_amount"],
            total_amount=calculated["total_amount"],
            currency_code=terms.currency_code,
            available_at=None if hold_days > 0 else created_at,
            created_at=created_at,
            updated_at=created_at,
            calculation_snapshot={
                "calculator_version": "partner_earning_v3",
                "commission_contract_id": str(terms.commission_contract_id),
                "commission_model": terms.commission_model,
                "commission_base_amount": str(calculated["commission_base_amount"]),
                "markup_pct": str(terms.markup_pct),
                "markup_amount": str(calculated["markup_amount"]),
                "commission_pct": str(terms.commission_pct),
                "commission_amount": str(calculated["commission_amount"]),
                "total_amount": str(calculated["total_amount"]),
                "payout_hold_days": hold_days,
                "currency_code": terms.currency_code,
                "currency_policy": dict(terms.currency_policy),
                "rounding_mode": terms.rounding_mode,
                "renewal_policy": dict(terms.renewal_policy),
                "refund_policy": dict(terms.refund_policy),
                "commission_contract_snapshot": dict(terms.snapshot),
                "commercial_snapshot": commercial_snapshot,
                "policy_snapshot": dict(policy_snapshot or {}),
            },
            source_snapshot={
                "order_id": str(order.id),
                "payment_id": str(payment.id),
                "source_event_key": source_event_key,
                "requested_commission_base_amount": str(requested_commission_base_amount),
                "order_commission_base_amount": str(order.commission_base_amount),
                "owner_type": owner_type,
                "owner_source": owner_source,
                "partner_account_id": str(partner_account_id) if partner_account_id else None,
                "partner_code_id": str(partner_code_id) if partner_code_id else None,
                "attribution_session_id": (
                    str(terms_source_result.attribution_session_id)
                    if terms_source_result is not None and terms_source_result.attribution_session_id
                    else None
                ),
                "renewal_order_id": str(renewal_order.id) if renewal_order is not None else None,
                "renewal_sequence_number": (
                    renewal_order.renewal_sequence_number if renewal_order is not None else None
                ),
                "originating_attribution_result_id": (
                    str(renewal_order.originating_attribution_result_id) if renewal_order is not None else None
                ),
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
                    hold_payload={
                        "owner_type": owner_type,
                        "hold_days": hold_days,
                        "commission_contract_id": str(terms.commission_contract_id),
                    },
                    created_at=created_at,
                    updated_at=created_at,
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
