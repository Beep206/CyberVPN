from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, exists, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService
from src.application.services.config_service import ConfigService
from src.application.use_cases.attribution.qualifying_events.evaluate_order_policy import EvaluateOrderPolicyUseCase
from src.application.use_cases.referrals.process_referral_reward import ProcessReferralRewardUseCase
from src.application.use_cases.settlement.commission_terms import (
    PartnerEarningSnapshotIncompleteError,
)
from src.application.use_cases.settlement.earning_events import CreatePartnerEarningEventFromPaymentUseCase
from src.domain.enums import OutboxPublicationStatus
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.outbox_consumer_receipt_model import OutboxConsumerReceiptModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.outbox_consumer_receipt_repo import OutboxConsumerReceiptRepository
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository

logger = logging.getLogger(__name__)

PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER = "partner_earning_worker"
PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS = (60, 300, 900, 3600, 21600)
PAYMENT_COMPLETED_LEASE_SECONDS = 60


async def append_payment_completed_partner_earning_publication(
    outbox: EventOutboxService,
    *,
    payment,
    payment_attempt,
    source: str,
) -> Any:
    payment_metadata = dict(payment.metadata_ or {})
    order_id = (
        str(payment_attempt.order_id)
        if payment_attempt is not None and payment_attempt.order_id is not None
        else _optional_payload_uuid(payment_metadata.get("order_id"))
    )
    return await outbox.append_event(
        event_name="payment.completed",
        aggregate_type="payment",
        aggregate_id=str(payment.id),
        partition_key=str(payment.user_uuid),
        consumer_keys=(PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,),
        event_key=f"payment.completed:{payment.id}",
        event_payload={
            "payment_id": str(payment.id),
            "payment_attempt_id": str(payment_attempt.id) if payment_attempt is not None else None,
            "order_id": order_id,
            "payment_status": payment.status,
            "payment_attempt_status": payment_attempt.status if payment_attempt is not None else None,
            "provider": payment.provider,
            "currency": payment.currency,
            "amount": str(payment.amount),
        },
        source_context={"source": source, "provider": str(payment.provider or "")},
    )


class ProcessPaymentCompletedEarningsUseCase:
    """Create referral and partner cash payout artifacts from a durable payment.completed event."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payments = PaymentRepository(session)
        self._payment_attempts = PaymentAttemptRepository(session)
        self._orders = OrderRepository(session)
        self._users = MobileUserRepository(session)
        self._policy_evaluator = EvaluateOrderPolicyUseCase(session)
        self._config = ConfigService(SystemConfigRepository(session))
        self._process_referral = ProcessReferralRewardUseCase(session, config_service=self._config)
        self._create_partner_earning_event = CreatePartnerEarningEventFromPaymentUseCase(session)
        self._outbox = EventOutboxService(session)

    async def execute(self, *, payment_id: UUID, source_event_id: str | None = None) -> dict[str, Any]:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            return {"status": "skipped", "reason": "payment_not_found", "cash_payout_created": False}
        if payment.status != "completed":
            return {"status": "skipped", "reason": "payment_not_completed", "cash_payout_created": False}

        payment_attempt = await self._payment_attempts.get_by_payment_id(payment.id)
        if payment_attempt is None or payment_attempt.order_id is None:
            return {"status": "skipped", "reason": "payment_attempt_order_not_found", "cash_payout_created": False}
        if payment_attempt.status != "succeeded":
            return {"status": "skipped", "reason": "payment_attempt_not_succeeded", "cash_payout_created": False}

        order = await self._orders.get_by_id(payment_attempt.order_id)
        if order is None:
            raise ValueError("Order not found")

        policy_evaluation = await self._policy_evaluator.execute(order_id=order.id)
        user = await self._users.get_by_id(payment.user_uuid)
        payment_metadata = dict(payment.metadata_ or {})
        gift_flow = str(payment_metadata.get("checkout_mode") or "").strip().lower() == "gift_purchase"
        commission_base_amount = Decimal(str(order.commission_base_amount))

        results: dict[str, Any] = {
            "status": "processed",
            "payment_id": str(payment.id),
            "order_id": str(order.id),
            "cash_payout_created": False,
            "policy_evaluation": {
                "qualifying_first_payment": policy_evaluation.qualifying_event.qualifying_first_payment,
                "referral_cash_payout_allowed": policy_evaluation.payout_rules.referral_cash_payout_allowed,
                "partner_cash_payout_allowed": policy_evaluation.payout_rules.partner_cash_payout_allowed,
                "no_double_payout": policy_evaluation.payout_rules.no_double_payout,
            },
        }

        await self._process_referral_reward(
            payment=payment,
            user=user,
            order=order,
            gift_flow=gift_flow,
            commission_base_amount=commission_base_amount,
            policy_evaluation=policy_evaluation,
            results=results,
        )
        await self._process_partner_earning(
            payment=payment,
            order=order,
            gift_flow=gift_flow,
            commission_base_amount=commission_base_amount,
            policy_evaluation=policy_evaluation,
            source_event_id=source_event_id or str(payment.id),
            results=results,
        )
        await self._session.flush()
        return results

    async def _process_referral_reward(
        self,
        *,
        payment,
        user,
        order,
        gift_flow: bool,
        commission_base_amount: Decimal,
        policy_evaluation,
        results: dict[str, Any],
    ) -> None:
        referrer_id = user.referred_by_user_id if user else None
        if gift_flow or referrer_id is None or commission_base_amount <= 0:
            results["referral_reward_amount"] = None
            results["referral_reward_status"] = None
            return
        if not policy_evaluation.payout_rules.referral_cash_payout_allowed:
            results["referral_reward_amount"] = None
            results["referral_reward_status"] = None
            results["referral_policy_block_reasons"] = policy_evaluation.payout_rules.referral_reason_codes
            return

        reward = await self._process_referral.execute(
            referrer_user_id=referrer_id,
            referred_user_id=payment.user_uuid,
            payment_id=payment.id,
            base_amount=commission_base_amount,
            duration_days=payment.subscription_days,
            order_id=order.id,
            storefront_id=order.storefront_id,
        )
        results["referral_reward_amount"] = str(reward.quantity) if reward else None
        results["referral_reward_status"] = reward.allocation_status if reward else None
        if reward is not None:
            results["cash_payout_created"] = True

    async def _process_partner_earning(
        self,
        *,
        payment,
        order,
        gift_flow: bool,
        commission_base_amount: Decimal,
        policy_evaluation,
        source_event_id: str,
        results: dict[str, Any],
    ) -> None:
        results["settlement_earning_event_id"] = None
        results["settlement_earning_event_status"] = None
        order_commission_base_amount = Decimal(str(order.commission_base_amount))
        if gift_flow or order_commission_base_amount <= 0:
            results["partner_earning"] = None
            return
        if not policy_evaluation.payout_rules.partner_cash_payout_allowed:
            results["partner_earning"] = None
            results["partner_policy_block_reasons"] = policy_evaluation.payout_rules.partner_reason_codes
            return

        try:
            earning_event, _earning_hold = await self._create_partner_earning_event.execute(
                order_id=order.id,
                payment_id=payment.id,
                commission_base_amount=commission_base_amount,
                source_event_id=source_event_id,
                commit=False,
            )
        except PartnerEarningSnapshotIncompleteError as exc:
            manual_review_event = await self._record_partner_snapshot_incomplete(
                payment=payment,
                order_id=order.id,
                missing_terms=exc.missing_terms,
                reason_code=exc.code,
            )
            results["partner_earning"] = None
            results["partner_policy_block_reasons"] = [exc.code]
            results["partner_earning_snapshot_missing_terms"] = exc.missing_terms
            results["partner_earning_manual_review_event_id"] = str(manual_review_event.id)
            return

        if earning_event is None:
            results["partner_earning"] = None
            results["partner_earning_source"] = "canonical_no_owner"
            return

        await self._outbox.append_event(
            event_name="settlement.earning.created",
            aggregate_type="earning_event",
            aggregate_id=str(earning_event.id),
            partition_key=str(earning_event.partner_account_id or earning_event.partner_user_id or order.id),
            event_key=f"settlement.earning.created:{earning_event.id}",
            event_payload={
                "earning_event_id": str(earning_event.id),
                "payment_id": str(payment.id),
                "order_id": str(order.id),
                "partner_account_id": (
                    str(earning_event.partner_account_id) if earning_event.partner_account_id else None
                ),
                "partner_user_id": str(earning_event.partner_user_id) if earning_event.partner_user_id else None,
                "total_amount": str(earning_event.total_amount),
                "currency_code": earning_event.currency_code,
                "event_status": earning_event.event_status,
            },
            source_context={"source": "payment_completed_partner_earning_worker"},
        )
        results["partner_earning"] = str(earning_event.total_amount)
        results["settlement_earning_event_id"] = str(earning_event.id)
        results["settlement_earning_event_status"] = earning_event.event_status
        results["cash_payout_created"] = True

    async def _record_partner_snapshot_incomplete(
        self,
        *,
        payment,
        order_id: UUID,
        missing_terms: list[str],
        reason_code: str,
    ):
        return await self._outbox.append_event(
            event_name="settlement.earning.snapshot_incomplete",
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            partition_key=str(order_id),
            event_key=f"settlement.earning.snapshot_incomplete:{payment.id}:{order_id}",
            event_payload={
                "payment_id": str(payment.id),
                "order_id": str(order_id),
                "reason_code": reason_code,
                "missing_terms": sorted(set(missing_terms)),
                "manual_review_required": True,
                "retryable": True,
                "cash_payout_created": False,
            },
            source_context={
                "source": "payment_completed_partner_earning_worker",
                "provider": str(payment.provider or ""),
                "currency": str(payment.currency or "").upper(),
            },
        )


class EnsurePaymentCompletedPartnerEarningPublicationUseCase:
    """Recover completed canonical payments that predate the durable worker publication."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = EventOutboxService(session)
        self._outbox_repo = OutboxRepository(session)
        self._receipt_repo = OutboxConsumerReceiptRepository(session)

    async def execute(self, *, limit: int) -> dict[str, Any]:
        event_key_expr = literal("payment.completed:") + cast(PaymentModel.id, String)
        worker_receipt_exists = exists().where(
            OutboxConsumerReceiptModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
            OutboxConsumerReceiptModel.event_key == event_key_expr,
        )
        worker_publication_exists = exists().where(
            OutboxEventModel.event_key == event_key_expr,
            OutboxPublicationModel.outbox_event_id == OutboxEventModel.id,
            OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
        )
        statement = (
            select(PaymentModel, PaymentAttemptModel, OrderModel)
            .join(PaymentAttemptModel, PaymentAttemptModel.payment_id == PaymentModel.id)
            .join(OrderModel, OrderModel.id == PaymentAttemptModel.order_id)
            .where(
                PaymentModel.status == "completed",
                PaymentAttemptModel.status == "succeeded",
                OrderModel.settlement_status == "paid",
                ~worker_receipt_exists,
                ~worker_publication_exists,
            )
            .order_by(PaymentModel.created_at.asc(), PaymentModel.id.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        report: dict[str, Any] = {
            "scanned": len(rows),
            "ensured_publications": 0,
            "created_events": 0,
            "already_queued": 0,
            "already_receipted": 0,
        }
        for payment, payment_attempt, _order in rows:
            event_key = f"payment.completed:{payment.id}"
            receipt = await self._receipt_repo.get_receipt(
                consumer_key=PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                event_key=event_key,
            )
            if receipt is not None:
                report["already_receipted"] += 1
                continue

            existing_event = await self._outbox_repo.get_event_by_key(event_key)
            has_worker_publication = existing_event is not None and any(
                publication.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER
                for publication in existing_event.publications
            )
            if has_worker_publication:
                report["already_queued"] += 1
                continue

            await append_payment_completed_partner_earning_publication(
                self._outbox,
                payment=payment,
                payment_attempt=payment_attempt,
                source="payment_completed_partner_earning_backfill",
            )
            report["ensured_publications"] += 1
            if existing_event is None:
                report["created_events"] += 1

        if report["ensured_publications"]:
            await self._session.flush()
        return report


class RunPaymentCompletedEarningOutboxUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox_repo = OutboxRepository(session)
        self._receipt_repo = OutboxConsumerReceiptRepository(session)
        self._processor = ProcessPaymentCompletedEarningsUseCase(session)
        self._outbox = EventOutboxService(session)
        self._publication_recovery = EnsurePaymentCompletedPartnerEarningPublicationUseCase(session)

    async def execute(self, *, limit: int, worker_id: str) -> dict[str, Any]:
        recovery_report = await self._publication_recovery.execute(limit=limit)
        if int(recovery_report["ensured_publications"] or 0) > 0:
            await self._session.commit()

        now = datetime.now(UTC)
        publications = await self._outbox_repo.claim_publications(
            consumer_key=PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
            batch_size=limit,
            lease_owner=worker_id,
            leased_until=now + timedelta(seconds=PAYMENT_COMPLETED_LEASE_SECONDS),
            now=now,
        )
        report: dict[str, Any] = {
            "claimed": len(publications),
            "succeeded": 0,
            "retrying": 0,
            "dead_letter": 0,
            "skipped": 0,
            "backfilled": recovery_report,
            "reconciliation_required": 0,
            "alerts": 0,
            "failures": [],
        }
        for publication in publications:
            await self._process_publication(publication=publication, report=report)
        return report

    async def _process_publication(self, *, publication: OutboxPublicationModel, report: dict[str, Any]) -> None:
        event = publication.outbox_event
        if event.event_name != "payment.completed":
            await self._outbox_repo.mark_publication_published(
                publication=publication,
                lease_owner=str(publication.lease_owner),
                published_at=datetime.now(UTC),
                publication_payload={"skipped": True, "reason": "unsupported_event_name"},
            )
            await self._session.commit()
            report["skipped"] += 1
            return

        try:
            existing_receipt = await self._receipt_repo.get_receipt(
                consumer_key=PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                event_key=event.event_key,
            )
            if existing_receipt is not None:
                await self._outbox_repo.mark_publication_published(
                    publication=publication,
                    lease_owner=str(publication.lease_owner),
                    published_at=datetime.now(UTC),
                    publication_payload={"receipt_id": str(existing_receipt.id), "already_processed": True},
                )
                await self._session.commit()
                report["succeeded"] += 1
                return
            payment_id = UUID(str(dict(event.event_payload or {}).get("payment_id") or event.aggregate_id))
            async with self._session.begin_nested():
                result = await self._processor.execute(payment_id=payment_id, source_event_id=str(payment_id))
                receipt = await self._receipt_repo.create_receipt(
                    consumer_key=PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                    event_key=event.event_key,
                    event_name=event.event_name,
                    subject=f"payment:{payment_id}",
                    metadata_payload={
                        "payment_id": str(payment_id),
                        "cash_payout_created": bool(result.get("cash_payout_created")),
                        "settlement_earning_event_id": result.get("settlement_earning_event_id"),
                    },
                )
            await self._outbox_repo.mark_publication_published(
                publication=publication,
                lease_owner=str(publication.lease_owner),
                published_at=datetime.now(UTC),
                publication_payload={"result": result, "receipt_id": str(receipt.id)},
            )
            await self._session.commit()
            report["succeeded"] += 1
        except Exception as exc:
            logger.exception(
                "payment_completed_partner_earning_publication_failed",
                extra={"publication_id": str(publication.id), "event_key": event.event_key},
            )
            await self._mark_publication_retry_or_dead_letter(publication=publication, exc=exc, report=report)

    async def _mark_publication_retry_or_dead_letter(
        self,
        *,
        publication: OutboxPublicationModel,
        exc: Exception,
        report: dict[str, Any],
    ) -> None:
        failed_at = datetime.now(UTC)
        error_message = _safe_error_message(exc)
        attempts = int(publication.attempts or 0)
        if attempts > len(PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS):
            await self._outbox_repo.mark_publication_dead_letter(
                publication=publication,
                lease_owner=str(publication.lease_owner),
                failed_at=failed_at,
                error_message=error_message,
            )
            reconciliation_event = await self._record_dead_letter_reconciliation_event(
                publication=publication,
                exc=exc,
                failed_at=failed_at,
                error_message=error_message,
            )
            await self._session.commit()
            report["dead_letter"] += 1
            report["reconciliation_required"] += 1
            report["alerts"] += 1
            report["failures"].append(
                {
                    "publication_id": str(publication.id),
                    "status": "dead_letter",
                    "reconciliation_event_id": str(reconciliation_event.id),
                }
            )
            return

        retry_delay = PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS[attempts - 1]
        await self._outbox_repo.mark_publication_failed(
            publication=publication,
            lease_owner=str(publication.lease_owner),
            failed_at=failed_at,
            retry_at=failed_at + timedelta(seconds=retry_delay),
            error_message=error_message,
        )
        await self._session.commit()
        report["retrying"] += 1
        report["failures"].append(
            {
                "publication_id": str(publication.id),
                "status": OutboxPublicationStatus.FAILED.value,
                "retry_after_seconds": retry_delay,
            }
        )

    async def _record_dead_letter_reconciliation_event(
        self,
        *,
        publication: OutboxPublicationModel,
        exc: Exception,
        failed_at: datetime,
        error_message: str,
    ):
        event = await self._outbox_repo.get_event_by_id(publication.outbox_event_id)
        if event is None:
            raise ValueError("Outbox event not found for dead-letter publication")
        payload = dict(event.event_payload or {})
        return await self._outbox.append_event(
            event_name="payment.completed.partner_earning.reconciliation_required",
            aggregate_type="outbox_publication",
            aggregate_id=str(publication.id),
            partition_key=str(payload.get("payment_id") or event.aggregate_id),
            event_key=f"payment.completed.partner_earning.reconciliation_required:{publication.id}",
            event_payload={
                "payment_id": str(payload.get("payment_id") or event.aggregate_id),
                "order_id": payload.get("order_id"),
                "source_event_id": str(event.id),
                "source_event_key": event.event_key,
                "outbox_publication_id": str(publication.id),
                "consumer_key": publication.consumer_key,
                "attempts": int(publication.attempts or 0),
                "failed_at": failed_at.isoformat(),
                "error_type": _safe_error_type(exc),
                "error_fingerprint": _safe_value_fingerprint(error_message),
                "manual_reconciliation_required": True,
                "alert_required": True,
                "next_action": "review_policy_or_data_failure_and_requeue_payment_completed_publication",
            },
            source_context={
                "source": "payment_completed_partner_earning_worker",
                "alert": "payment_completed_partner_earning_dead_letter",
            },
        )


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    fingerprint = _safe_value_fingerprint(message)[:16]
    return f"{_safe_error_type(exc)}:{fingerprint}"


def _safe_error_type(exc: Exception) -> str:
    return type(exc).__name__[:120]


def _safe_value_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_payload_uuid(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None
