from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.phase7_reporting_marts import build_phase7_reporting_marts_pack
from src.application.use_cases.settlement import (
    ListPartnerPayoutAccountsUseCase,
    ListPartnerStatementsUseCase,
)
from src.infrastructure.database.models.commissionability_evaluation_model import (
    CommissionabilityEvaluationModel,
)
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.order_attribution_result_model import (
    OrderAttributionResultModel,
)
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
from src.infrastructure.database.models.refund_model import RefundModel
from src.infrastructure.database.models.renewal_order_model import RenewalOrderModel
from src.infrastructure.database.repositories.payment_dispute_repo import (
    PaymentDisputeRepository,
)
from src.infrastructure.database.repositories.refund_repo import RefundRepository


@dataclass(frozen=True)
class PartnerWorkspaceReportingContext:
    order_items: list[dict[str, Any]]
    statements: list[Any]
    payout_accounts: list[Any]
    report_pack: dict[str, Any]


class BuildPartnerWorkspaceReportingUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._refunds = RefundRepository(session)
        self._disputes = PaymentDisputeRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        order_limit: int = 100,
        order_offset: int = 0,
        statement_limit: int = 100,
        statement_offset: int = 0,
        payout_limit: int = 100,
        payout_offset: int = 0,
    ) -> PartnerWorkspaceReportingContext:
        order_items = await self._load_workspace_order_items(
            partner_account_id=partner_account_id,
            limit=order_limit,
            offset=order_offset,
        )
        statements = await ListPartnerStatementsUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            settlement_period_id=None,
            statement_status=None,
            limit=statement_limit,
            offset=statement_offset,
        )
        payout_accounts = await ListPartnerPayoutAccountsUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            limit=payout_limit,
            offset=payout_offset,
        )
        report_pack = await self._build_report_pack(
            partner_account_id=partner_account_id,
            order_items=order_items,
            statements=statements,
        )
        order_reporting_rows = {
            str(item["order_id"]): item for item in report_pack.get("order_reporting_mart", [])
        }
        for item in order_items:
            item["report_row"] = order_reporting_rows.get(str(item["order"].id), {})
        return PartnerWorkspaceReportingContext(
            order_items=order_items,
            statements=statements,
            payout_accounts=payout_accounts,
            report_pack=report_pack,
        )

    async def is_order_visible_to_workspace(
        self,
        *,
        partner_account_id: UUID,
        order_id: UUID,
    ) -> bool:
        query = (
            select(OrderModel.id)
            .outerjoin(
                OrderAttributionResultModel,
                OrderAttributionResultModel.order_id == OrderModel.id,
            )
            .outerjoin(
                RenewalOrderModel,
                RenewalOrderModel.order_id == OrderModel.id,
            )
            .where(
                OrderModel.id == order_id,
                or_(
                    OrderAttributionResultModel.partner_account_id == partner_account_id,
                    RenewalOrderModel.effective_partner_account_id == partner_account_id,
                ),
            )
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none() is not None

    async def _load_workspace_order_items(
        self,
        *,
        partner_account_id: UUID,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        rows = await self._session.execute(
            select(
                OrderModel,
                OrderAttributionResultModel,
                CommissionabilityEvaluationModel,
                RenewalOrderModel,
            )
            .outerjoin(
                OrderAttributionResultModel,
                OrderAttributionResultModel.order_id == OrderModel.id,
            )
            .outerjoin(
                CommissionabilityEvaluationModel,
                CommissionabilityEvaluationModel.order_id == OrderModel.id,
            )
            .outerjoin(
                RenewalOrderModel,
                RenewalOrderModel.order_id == OrderModel.id,
            )
            .where(
                or_(
                    OrderAttributionResultModel.partner_account_id == partner_account_id,
                    RenewalOrderModel.effective_partner_account_id == partner_account_id,
                )
            )
            .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        order_rows = list(rows.all())
        if not order_rows:
            return []

        order_ids = [order.id for order, *_rest in order_rows]
        refund_map = await self._load_refunds_by_order(order_ids)
        dispute_map = await self._load_disputes_by_order(order_ids)

        partner_code_ids = {
            renewal_order.effective_partner_code_id
            if renewal_order is not None and renewal_order.effective_partner_code_id is not None
            else attribution_result.partner_code_id
            if attribution_result is not None and attribution_result.partner_code_id is not None
            else None
            for _order, attribution_result, _evaluation, renewal_order in order_rows
        }
        partner_code_ids.discard(None)
        code_by_id = await self._load_partner_codes_by_id(list(partner_code_ids))

        items: list[dict[str, Any]] = []
        for order, attribution_result, evaluation, renewal_order in order_rows:
            effective_partner_code_id = (
                renewal_order.effective_partner_code_id
                if renewal_order is not None and renewal_order.effective_partner_code_id is not None
                else attribution_result.partner_code_id
                if attribution_result is not None
                else None
            )
            items.append(
                {
                    "order": order,
                    "attribution_result": attribution_result,
                    "evaluation": evaluation,
                    "renewal_order": renewal_order,
                    "partner_code": code_by_id.get(effective_partner_code_id),
                    "disputes": dispute_map.get(order.id, []),
                    "refunds": refund_map.get(order.id, []),
                }
            )
        return items

    async def _build_report_pack(
        self,
        *,
        partner_account_id: UUID,
        order_items: list[dict[str, Any]],
        statements: list[Any],
    ) -> dict[str, Any]:
        earning_events = await self._load_earning_events(partner_account_id=partner_account_id)
        outbox_events = await self._load_workspace_outbox_events(
            order_items=order_items,
            statements=statements,
            earning_events=earning_events,
        )

        snapshot = {
            "metadata": {
                "source": f"workspace_reporting:{partner_account_id}",
                "snapshot_id": str(partner_account_id),
            },
            "orders": [self._serialize_order(order_item["order"]) for order_item in order_items],
            "order_attribution_results": [
                self._serialize_attribution_result(order_item["attribution_result"])
                for order_item in order_items
                if order_item["attribution_result"] is not None
            ],
            "commissionability_evaluations": [
                self._serialize_evaluation(order_item["evaluation"])
                for order_item in order_items
                if order_item["evaluation"] is not None
            ],
            "renewal_orders": [
                self._serialize_renewal_order(order_item["renewal_order"])
                for order_item in order_items
                if order_item["renewal_order"] is not None
            ],
            "refunds": [
                self._serialize_refund(refund)
                for order_item in order_items
                for refund in order_item["refunds"]
            ],
            "payment_disputes": [
                self._serialize_dispute(dispute)
                for order_item in order_items
                for dispute in order_item["disputes"]
            ],
            "earning_events": [self._serialize_earning_event(item) for item in earning_events],
            "partner_statements": [self._serialize_partner_statement(item) for item in statements],
            "outbox_events": [self._serialize_outbox_event(item) for item in outbox_events],
            "outbox_publications": [
                self._serialize_outbox_publication(publication)
                for event in outbox_events
                for publication in event.publications
            ],
        }
        return build_phase7_reporting_marts_pack(snapshot)

    async def _load_refunds_by_order(self, order_ids: list[UUID]) -> dict[UUID, list[RefundModel]]:
        result: dict[UUID, list[RefundModel]] = defaultdict(list)
        for order_id in order_ids:
            result[order_id] = await self._refunds.list_for_order(order_id)
        return result

    async def _load_disputes_by_order(
        self,
        order_ids: list[UUID],
    ) -> dict[UUID, list[PaymentDisputeModel]]:
        result: dict[UUID, list[PaymentDisputeModel]] = defaultdict(list)
        for order_id in order_ids:
            result[order_id] = await self._disputes.list_for_order(order_id)
        return result

    async def _load_partner_codes_by_id(
        self,
        partner_code_ids: list[UUID],
    ) -> dict[UUID, PartnerCodeModel]:
        if not partner_code_ids:
            return {}
        rows = await self._session.execute(
            select(PartnerCodeModel).where(PartnerCodeModel.id.in_(partner_code_ids))
        )
        return {item.id: item for item in rows.scalars().all()}

    async def _load_earning_events(
        self,
        *,
        partner_account_id: UUID,
    ) -> list[EarningEventModel]:
        rows = await self._session.execute(
            select(EarningEventModel)
            .where(EarningEventModel.partner_account_id == partner_account_id)
            .order_by(EarningEventModel.created_at.desc(), EarningEventModel.id.desc())
        )
        return list(rows.scalars().all())

    async def _load_workspace_outbox_events(
        self,
        *,
        order_items: list[dict[str, Any]],
        statements: list[Any],
        earning_events: list[EarningEventModel],
    ) -> list[OutboxEventModel]:
        conditions = []
        order_ids = [str(order_item["order"].id) for order_item in order_items]
        statement_ids = [str(statement.id) for statement in statements]
        earning_event_ids = [str(event.id) for event in earning_events]

        if order_ids:
            conditions.append(
                and_(
                    OutboxEventModel.aggregate_type == "order",
                    OutboxEventModel.aggregate_id.in_(order_ids),
                )
            )
        if statement_ids:
            conditions.append(
                and_(
                    OutboxEventModel.aggregate_type == "partner_statement",
                    OutboxEventModel.aggregate_id.in_(statement_ids),
                )
            )
        if earning_event_ids:
            conditions.append(
                and_(
                    OutboxEventModel.aggregate_type == "earning_event",
                    OutboxEventModel.aggregate_id.in_(earning_event_ids),
                )
            )

        if not conditions:
            return []

        rows = await self._session.execute(
            select(OutboxEventModel)
            .options(selectinload(OutboxEventModel.publications))
            .where(or_(*conditions))
            .order_by(OutboxEventModel.occurred_at.desc(), OutboxEventModel.id.desc())
        )
        return list(rows.scalars().unique().all())

    @staticmethod
    def _serialize_order(model: OrderModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "user_id": str(model.user_id),
            "sale_channel": model.sale_channel,
            "currency_code": model.currency_code,
            "order_status": model.order_status,
            "settlement_status": model.settlement_status,
            "commission_base_amount": float(model.commission_base_amount or 0),
            "displayed_price": float(model.displayed_price or 0),
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_attribution_result(model: OrderAttributionResultModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "order_id": str(model.order_id),
            "owner_type": model.owner_type,
            "owner_source": model.owner_source,
            "partner_account_id": str(model.partner_account_id) if model.partner_account_id else None,
            "partner_code_id": str(model.partner_code_id) if model.partner_code_id else None,
            "created_at": model.created_at,
            "updated_at": model.resolved_at,
        }

    @staticmethod
    def _serialize_evaluation(model: CommissionabilityEvaluationModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "order_id": str(model.order_id),
            "commissionability_status": model.commissionability_status,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_renewal_order(model: RenewalOrderModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "order_id": str(model.order_id),
            "effective_partner_account_id": (
                str(model.effective_partner_account_id) if model.effective_partner_account_id else None
            ),
            "effective_partner_code_id": (
                str(model.effective_partner_code_id) if model.effective_partner_code_id else None
            ),
            "effective_owner_type": model.effective_owner_type,
            "effective_owner_source": model.effective_owner_source,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_refund(model: RefundModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "order_id": str(model.order_id),
            "refund_status": model.refund_status,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_dispute(model: PaymentDisputeModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "order_id": str(model.order_id),
            "outcome_class": model.outcome_class,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_earning_event(model: EarningEventModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "partner_account_id": str(model.partner_account_id) if model.partner_account_id else None,
            "available_amount": float(model.total_amount or 0),
            "currency_code": model.currency_code,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_partner_statement(model) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "partner_account_id": str(model.partner_account_id),
            "superseded_by_statement_id": (
                str(model.superseded_by_statement_id) if model.superseded_by_statement_id else None
            ),
            "available_amount": float(model.available_amount or 0),
            "currency_code": model.currency_code,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_outbox_event(model: OutboxEventModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "event_family": model.event_family,
            "aggregate_type": model.aggregate_type,
            "aggregate_id": model.aggregate_id,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def _serialize_outbox_publication(model) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "outbox_event_id": str(model.outbox_event_id),
            "consumer_key": model.consumer_key,
            "publication_status": model.publication_status,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
