from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import WalletTxReason
from src.infrastructure.database.models.growth_benefit_model import (
    GrowthBenefitFulfillmentModel,
    InviteBatchModel,
)
from src.infrastructure.database.models.growth_code_model import GrowthCodeReservationModel
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthCodeReservationGroupModel,
    GrowthReversalEventModel,
    OrderCodeApplicationModel,
    PrivateCatalogAccessGrantModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.wallet_model import WalletTransactionModel
from src.infrastructure.database.repositories.wallet_repo import WalletRepository

_REVERSAL_REFERENCE_TYPE = "growth_benefit_reversal"
_INVITE_REVERSAL_MODES = frozenset({"revoke_if_unused", "revoke_unredeemed", "reverse_always"})
_NOOP_REVERSAL_MODES = frozenset({"never", "none"})


@dataclass(frozen=True)
class ReversedOrderCodeApplicationsResult:
    reversed_count: int
    application_ids: list[UUID]
    fulfillment_reversal_count: int = 0
    invite_batches_revoked_count: int = 0
    invite_codes_revoked_count: int = 0
    private_grants_revoked_count: int = 0
    reservations_released_count: int = 0
    manual_review_count: int = 0
    wallet_debit_count: int = 0
    skipped_count: int = 0
    reversal_event_id: UUID | None = None
    reversal_event_idempotency_key: str | None = None

    @property
    def benefit_reversal_count(self) -> int:
        return self.fulfillment_reversal_count


class ReverseOrderCodeApplicationsForRefundUseCase:
    """Reverse growth effects for an order after refund/cancellation events.

    The historical order-code application ledger is always processed per
    application. Refunds keep reservation usage consumed by default, while
    cancellation can release not-yet-consumed reservation rows.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        order_id: UUID,
        refund_id: UUID,
        reversal_reason: str,
        commit: bool = False,
    ) -> ReversedOrderCodeApplicationsResult:
        return await self._execute(
            order_id=order_id,
            reversal_event_type="refund",
            reversal_event_id=refund_id,
            reversal_reason=reversal_reason,
            release_unconsumed_reservations=False,
            commit=commit,
        )

    async def execute_cancellation(
        self,
        *,
        order_id: UUID,
        reversal_event_id: UUID,
        reversal_reason: str,
        commit: bool = False,
    ) -> ReversedOrderCodeApplicationsResult:
        return await self._execute(
            order_id=order_id,
            reversal_event_type="zero_payment_cancellation",
            reversal_event_id=reversal_event_id,
            reversal_reason=reversal_reason,
            release_unconsumed_reservations=True,
            commit=commit,
        )

    async def _execute(
        self,
        *,
        order_id: UUID,
        reversal_event_type: str,
        reversal_event_id: UUID,
        reversal_reason: str,
        release_unconsumed_reservations: bool,
        commit: bool,
    ) -> ReversedOrderCodeApplicationsResult:
        now = datetime.now(UTC)
        reversal_event = await self._get_or_create_reversal_event(
            order_id=order_id,
            event_type=reversal_event_type,
            event_id=reversal_event_id,
            reversal_reason=reversal_reason,
        )
        result = await self._session.execute(
            select(OrderCodeApplicationModel)
            .where(OrderCodeApplicationModel.order_id == order_id)
            .with_for_update()
            .order_by(OrderCodeApplicationModel.created_at.asc(), OrderCodeApplicationModel.id.asc())
        )
        applications = list(result.scalars().all())
        changed_ids: list[UUID] = []
        for application in applications:
            snapshot = dict(application.application_snapshot or {})
            reversals = list(snapshot.get("reversals") or [])
            if _has_reversal(reversals, event_type=reversal_event_type, event_id=reversal_event_id):
                continue

            reversal_entry = {
                "event_type": reversal_event_type,
                "event_id": str(reversal_event_id),
                "idempotency_key": _application_reversal_idempotency_key(
                    application_id=application.id,
                    event_type=reversal_event_type,
                    event_id=reversal_event_id,
                ),
                "reversal_reason": reversal_reason,
                "reversed_at": now.isoformat(),
                "applied_target_amount": str(application.discount_amount),
                "target_currency_code": application.currency_code,
                "source_amount": str(application.source_amount) if application.source_amount is not None else None,
                "source_currency_code": application.source_currency_code,
                "fx_conversion_id": str(application.fx_conversion_id) if application.fx_conversion_id else None,
            }
            if reversal_event_type == "refund":
                reversal_entry["refund_id"] = str(reversal_event_id)
            reversals.append(reversal_entry)
            snapshot["reversals"] = reversals
            snapshot["last_reversal"] = reversal_entry
            snapshot["reversal_state"] = f"{reversal_event_type}_reversed"
            application.application_snapshot = snapshot
            application.application_status = "reversed"
            changed_ids.append(application.id)

        reservations_released_count = 0
        if release_unconsumed_reservations:
            reservations_released_count = await self._release_unconsumed_reservations(
                applications=applications,
                reversal_reason=reversal_reason,
                now=now,
            )

        fulfillment_result = await self._reverse_benefit_fulfillments(
            order_id=order_id,
            event_type=reversal_event_type,
            event_id=reversal_event_id,
            reversal_reason=reversal_reason,
            now=now,
        )
        private_grants_revoked_count = await self._revoke_private_catalog_grants(
            order_id=order_id,
            event_type=reversal_event_type,
            event_id=reversal_event_id,
            reversal_reason=reversal_reason,
            now=now,
        )

        reversal_result = ReversedOrderCodeApplicationsResult(
            reversed_count=len(changed_ids),
            application_ids=changed_ids,
            fulfillment_reversal_count=fulfillment_result.fulfillment_reversal_count,
            invite_batches_revoked_count=fulfillment_result.invite_batches_revoked_count,
            invite_codes_revoked_count=fulfillment_result.invite_codes_revoked_count,
            private_grants_revoked_count=private_grants_revoked_count,
            reservations_released_count=reservations_released_count,
            manual_review_count=fulfillment_result.manual_review_count,
            wallet_debit_count=fulfillment_result.wallet_debit_count,
            skipped_count=fulfillment_result.skipped_count,
            reversal_event_id=reversal_event.id,
            reversal_event_idempotency_key=reversal_event.idempotency_key,
        )
        if not reversal_event.event_payload or _result_has_work(reversal_result):
            reversal_event.event_status = "applied"
            reversal_event.event_payload = _reversal_event_payload(reversal_result)
        if commit:
            await self._session.commit()
        return reversal_result

    async def _get_or_create_reversal_event(
        self,
        *,
        order_id: UUID,
        event_type: str,
        event_id: UUID,
        reversal_reason: str,
    ) -> GrowthReversalEventModel:
        idempotency_key = _reversal_event_idempotency_key(
            order_id=order_id,
            event_type=event_type,
            event_id=event_id,
        )
        existing = await self._get_reversal_event_for_update(idempotency_key)
        if existing is not None:
            return existing
        event = GrowthReversalEventModel(
            id=uuid4(),
            event_type=event_type,
            event_id=event_id,
            order_id=order_id,
            refund_id=event_id if event_type == "refund" else None,
            campaign_id=event_id if event_type == "campaign_revoke" else None,
            idempotency_key=idempotency_key,
            reason_code=reversal_reason,
            event_status="applying",
            event_payload={},
        )
        try:
            async with self._session.begin_nested():
                self._session.add(event)
                await self._session.flush()
        except IntegrityError:
            existing = await self._get_reversal_event_for_update(idempotency_key)
            if existing is None:
                raise
            return existing
        return event

    async def _get_reversal_event_for_update(self, idempotency_key: str) -> GrowthReversalEventModel | None:
        result = await self._session.execute(
            select(GrowthReversalEventModel)
            .where(GrowthReversalEventModel.idempotency_key == idempotency_key)
            .with_for_update()
        )
        return result.scalars().first()

    async def _release_unconsumed_reservations(
        self,
        *,
        applications: list[OrderCodeApplicationModel],
        reversal_reason: str,
        now: datetime,
    ) -> int:
        reservation_ids = sorted(
            {application.reservation_id for application in applications if application.reservation_id is not None},
            key=str,
        )
        if not reservation_ids:
            return 0
        result = await self._session.execute(
            select(GrowthCodeReservationModel)
            .where(GrowthCodeReservationModel.id.in_(reservation_ids))
            .with_for_update()
            .order_by(GrowthCodeReservationModel.id.asc())
        )
        reservations = list(result.scalars().all())
        released_group_ids: set[UUID] = set()
        released_count = 0
        for reservation in reservations:
            if reservation.status not in {"reserved", "committed"}:
                continue
            reservation.status = "released"
            reservation.released_at = now
            reservation.release_reason = reversal_reason
            released_count += 1
            if reservation.reservation_group_id is not None:
                released_group_ids.add(reservation.reservation_group_id)

        if released_group_ids:
            groups_result = await self._session.execute(
                select(GrowthCodeReservationGroupModel)
                .where(GrowthCodeReservationGroupModel.id.in_(sorted(released_group_ids, key=str)))
                .with_for_update()
            )
            for group in groups_result.scalars().all():
                if group.status in {"reserved", "committed"}:
                    group.status = "released"
                    group.released_at = now
                    group.release_reason = reversal_reason
        return released_count

    async def _reverse_benefit_fulfillments(
        self,
        *,
        order_id: UUID,
        event_type: str,
        event_id: UUID,
        reversal_reason: str,
        now: datetime,
    ) -> _BenefitReversalStats:
        result = await self._session.execute(
            select(GrowthBenefitFulfillmentModel)
            .where(GrowthBenefitFulfillmentModel.order_id == order_id)
            .with_for_update()
            .order_by(GrowthBenefitFulfillmentModel.created_at.asc(), GrowthBenefitFulfillmentModel.id.asc())
        )
        fulfillments = list(result.scalars().all())
        stats = _BenefitReversalStats()
        for fulfillment in fulfillments:
            payload = dict(fulfillment.result_payload or {})
            reversals = list(payload.get("reversals") or [])
            if _has_reversal(reversals, event_type=event_type, event_id=event_id):
                continue

            reversal_mode = _reversal_mode(fulfillment=fulfillment)
            reversal_entry = {
                "event_type": event_type,
                "event_id": str(event_id),
                "idempotency_key": _benefit_reversal_idempotency_key(
                    fulfillment_id=fulfillment.id,
                    event_id=event_id,
                ),
                "reversal_reason": reversal_reason,
                "reversal_mode": reversal_mode,
                "reversed_at": now.isoformat(),
            }
            if reversal_mode in _NOOP_REVERSAL_MODES:
                reversal_entry["status"] = "skipped"
                stats.skipped_count += 1
            elif _is_invite_fulfillment(fulfillment=fulfillment, payload=payload):
                invite_stats = await self._reverse_invite_fulfillment(
                    fulfillment=fulfillment,
                    payload=payload,
                    reversal_mode=reversal_mode,
                    reversal_reason=reversal_reason,
                    now=now,
                )
                reversal_entry.update(invite_stats.payload)
                stats.invite_batches_revoked_count += invite_stats.invite_batches_revoked_count
                stats.invite_codes_revoked_count += invite_stats.invite_codes_revoked_count
                stats.manual_review_count += invite_stats.manual_review_count
            elif _is_wallet_credit_fulfillment(payload):
                wallet_stats = await self._reverse_wallet_credit_fulfillment(
                    fulfillment=fulfillment,
                    payload=payload,
                    reversal_mode=reversal_mode,
                )
                reversal_entry.update(wallet_stats.payload)
                stats.wallet_debit_count += wallet_stats.wallet_debit_count
                stats.manual_review_count += wallet_stats.manual_review_count
            elif reversal_mode in {"manual_review", "proportional"}:
                reversal_entry["status"] = "manual_review_required"
                stats.manual_review_count += 1
            elif reversal_mode in {"reverse_always", "revoke_addon", "revoke_unapplied", "shorten_entitlement"}:
                reversal_entry["status"] = "queued_domain_worker"
                stats.manual_review_count += 1
            else:
                reversal_entry["status"] = "manual_review_required"
                stats.manual_review_count += 1

            reversals.append(reversal_entry)
            payload["reversals"] = reversals
            payload["last_reversal"] = reversal_entry
            payload["reversal_state"] = reversal_entry["status"]
            fulfillment.result_payload = payload
            stats.fulfillment_reversal_count += 1
        return stats

    async def _reverse_invite_fulfillment(
        self,
        *,
        fulfillment: GrowthBenefitFulfillmentModel,
        payload: dict[str, Any],
        reversal_mode: str,
        reversal_reason: str,
        now: datetime,
    ) -> _InviteReversalStats:
        if reversal_mode not in _INVITE_REVERSAL_MODES:
            return _InviteReversalStats(payload={"status": "manual_review_required"}, manual_review_count=1)

        batch_id = _optional_uuid(payload.get("invite_batch_id"))
        if batch_id is None:
            return _InviteReversalStats(payload={"status": "manual_review_required"}, manual_review_count=1)

        batch = await self._session.get(InviteBatchModel, batch_id, with_for_update=True)
        if batch is None or batch.source_order_id != fulfillment.order_id:
            return _InviteReversalStats(payload={"status": "manual_review_required"}, manual_review_count=1)

        codes_result = await self._session.execute(
            select(InviteCodeModel)
            .where(InviteCodeModel.batch_id == batch.id)
            .with_for_update()
            .order_by(InviteCodeModel.id.asc())
        )
        codes = list(codes_result.scalars().all())
        revoked_code_ids: list[str] = []
        used_code_ids: list[str] = []
        for code in codes:
            if code.is_used or code.used_at is not None or code.status == "used":
                used_code_ids.append(str(code.id))
                continue
            if code.revoked_at is not None or code.status == "revoked":
                continue
            code.status = "revoked"
            code.revoked_at = now
            code.revoked_reason = reversal_reason
            revoked_code_ids.append(str(code.id))

        if revoked_code_ids:
            batch.revoked_at = batch.revoked_at or now
            batch.revoked_reason = batch.revoked_reason or reversal_reason
        if (
            codes
            and len(used_code_ids) == 0
            and all(code.revoked_at is not None or code.status == "revoked" for code in codes)
        ):
            batch.status = "revoked"
        elif revoked_code_ids:
            batch.status = "partially_revoked"

        return _InviteReversalStats(
            payload={
                "status": "reversed",
                "invite_batch_id": str(batch.id),
                "revoked_invite_code_ids": revoked_code_ids,
                "preserved_redeemed_invite_code_ids": used_code_ids,
            },
            invite_batches_revoked_count=1 if revoked_code_ids else 0,
            invite_codes_revoked_count=len(revoked_code_ids),
        )

    async def _reverse_wallet_credit_fulfillment(
        self,
        *,
        fulfillment: GrowthBenefitFulfillmentModel,
        payload: dict[str, Any],
        reversal_mode: str,
    ) -> _WalletReversalStats:
        if reversal_mode not in {"wallet_debit", "reverse_always"}:
            return _WalletReversalStats(payload={"status": "manual_review_required"}, manual_review_count=1)

        wallet_credit = payload.get("wallet_credit")
        if not isinstance(wallet_credit, dict):
            return _WalletReversalStats(payload={"status": "manual_review_required"}, manual_review_count=1)
        amount = _optional_decimal(wallet_credit.get("amount"))
        if amount is None or amount <= Decimal("0"):
            return _WalletReversalStats(payload={"status": "manual_review_required"}, manual_review_count=1)

        existing = await self._session.execute(
            select(WalletTransactionModel).where(
                WalletTransactionModel.reference_type == _REVERSAL_REFERENCE_TYPE,
                WalletTransactionModel.reference_id == fulfillment.id,
            )
        )
        existing_tx = existing.scalars().first()
        if existing_tx is not None:
            return _WalletReversalStats(
                payload={
                    "status": "reversed",
                    "wallet_debit_transaction_id": str(existing_tx.id),
                    "duplicate": True,
                },
                wallet_debit_count=0,
            )

        try:
            tx = await WalletRepository(self._session).debit(
                user_id=fulfillment.user_id,
                amount=amount,
                reason=WalletTxReason.REFUND,
                description="growth.benefit.walletCredit.reversal",
                reference_type=_REVERSAL_REFERENCE_TYPE,
                reference_id=fulfillment.id,
            )
        except ValueError as exc:
            return _WalletReversalStats(
                payload={"status": "manual_review_required", "manual_review_reason": str(exc)},
                manual_review_count=1,
            )
        return _WalletReversalStats(
            payload={
                "status": "reversed",
                "wallet_debit_transaction_id": str(tx.id),
                "amount": str(tx.amount),
                "currency": tx.currency,
                "balance_after": str(tx.balance_after),
                "duplicate": False,
            },
            wallet_debit_count=1,
        )

    async def _revoke_private_catalog_grants(
        self,
        *,
        order_id: UUID,
        event_type: str,
        event_id: UUID,
        reversal_reason: str,
        now: datetime,
    ) -> int:
        result = await self._session.execute(
            select(PrivateCatalogAccessGrantModel)
            .where(PrivateCatalogAccessGrantModel.consumed_order_id == order_id)
            .with_for_update()
            .order_by(PrivateCatalogAccessGrantModel.created_at.asc(), PrivateCatalogAccessGrantModel.id.asc())
        )
        changed = 0
        for grant in result.scalars().all():
            metadata = dict(grant.metadata_ or {})
            reversals = list(metadata.get("reversals") or [])
            if _has_reversal(reversals, event_type=event_type, event_id=event_id):
                continue
            reversal_entry = {
                "event_type": event_type,
                "event_id": str(event_id),
                "idempotency_key": _private_grant_reversal_idempotency_key(
                    grant_id=grant.id,
                    event_id=event_id,
                ),
                "reversal_reason": reversal_reason,
                "reversed_at": now.isoformat(),
                "status": "revoked",
            }
            reversals.append(reversal_entry)
            metadata["reversals"] = reversals
            metadata["last_reversal"] = reversal_entry
            grant.metadata_ = metadata
            if grant.revoked_at is None:
                grant.revoked_at = now
                grant.revoked_reason = reversal_reason
                grant.status = "revoked"
                changed += 1
        return changed


class ReverseZeroPaymentOrderCancellationUseCase:
    """Cancel an internal-zero order without executing a provider refund."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._reversal = ReverseOrderCodeApplicationsForRefundUseCase(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        reason_code: str,
        commit: bool = False,
    ) -> ReversedOrderCodeApplicationsResult:
        result = await self._session.execute(select(OrderModel).where(OrderModel.id == order_id).with_for_update())
        order = result.scalars().first()
        if order is None:
            raise ValueError("order_not_found")
        if order.gateway_amount > 0 and order.settlement_status != "pending_internal_settlement":
            raise ValueError("zero_payment_cancellation_requires_internal_zero_order")
        order.order_status = "cancelled"
        order.settlement_status = "cancelled"
        reversal = await self._reversal.execute_cancellation(
            order_id=order.id,
            reversal_event_id=order.id,
            reversal_reason=reason_code,
            commit=False,
        )
        if commit:
            await self._session.commit()
        return reversal


@dataclass(slots=True)
class _BenefitReversalStats:
    fulfillment_reversal_count: int = 0
    invite_batches_revoked_count: int = 0
    invite_codes_revoked_count: int = 0
    manual_review_count: int = 0
    wallet_debit_count: int = 0
    skipped_count: int = 0


@dataclass(frozen=True, slots=True)
class _InviteReversalStats:
    payload: dict[str, Any]
    invite_batches_revoked_count: int = 0
    invite_codes_revoked_count: int = 0
    manual_review_count: int = 0


@dataclass(frozen=True, slots=True)
class _WalletReversalStats:
    payload: dict[str, Any]
    wallet_debit_count: int = 0
    manual_review_count: int = 0


def _has_reversal(reversals: list[object], *, event_type: str, event_id: UUID) -> bool:
    expected_event_id = str(event_id)
    for reversal in reversals:
        if not isinstance(reversal, dict):
            continue
        legacy_refund_id = str(reversal.get("refund_id") or "")
        if event_type == "refund" and legacy_refund_id == expected_event_id:
            return True
        if (
            str(reversal.get("event_type") or "") == event_type
            and str(reversal.get("event_id") or "") == expected_event_id
        ):
            return True
    return False


def _application_reversal_idempotency_key(*, application_id: UUID, event_type: str, event_id: UUID) -> str:
    return f"order-code-application-reversal:{application_id}:{event_type}:{event_id}"


def _benefit_reversal_idempotency_key(*, fulfillment_id: UUID, event_id: UUID) -> str:
    return f"benefit-reversal:{fulfillment_id}:{event_id}"


def _private_grant_reversal_idempotency_key(*, grant_id: UUID, event_id: UUID) -> str:
    return f"private-grant-reversal:{grant_id}:{event_id}"


def _reversal_event_idempotency_key(*, order_id: UUID, event_type: str, event_id: UUID) -> str:
    return f"growth-reversal:{event_type}:{event_id}:order:{order_id}"


def _result_has_work(result: ReversedOrderCodeApplicationsResult) -> bool:
    return any(
        (
            result.reversed_count,
            result.fulfillment_reversal_count,
            result.invite_batches_revoked_count,
            result.invite_codes_revoked_count,
            result.private_grants_revoked_count,
            result.reservations_released_count,
            result.manual_review_count,
            result.wallet_debit_count,
            result.skipped_count,
        )
    )


def _reversal_event_payload(result: ReversedOrderCodeApplicationsResult) -> dict[str, Any]:
    return {
        "order_code_application_count": result.reversed_count,
        "order_code_application_ids": [str(application_id) for application_id in result.application_ids],
        "benefit_fulfillment_reversal_count": result.fulfillment_reversal_count,
        "invite_batches_revoked_count": result.invite_batches_revoked_count,
        "invite_codes_revoked_count": result.invite_codes_revoked_count,
        "private_grants_revoked_count": result.private_grants_revoked_count,
        "reservations_released_count": result.reservations_released_count,
        "manual_review_count": result.manual_review_count,
        "wallet_debit_count": result.wallet_debit_count,
        "skipped_count": result.skipped_count,
        "reversal_event_id": str(result.reversal_event_id) if result.reversal_event_id is not None else None,
        "reversal_event_idempotency_key": result.reversal_event_idempotency_key,
    }


def _reversal_mode(*, fulfillment: GrowthBenefitFulfillmentModel) -> str:
    payload = dict(fulfillment.result_payload or {})
    config = dict(fulfillment.config_snapshot or {})
    policy = payload.get("reversal_policy") or config.get("reversal_policy")
    if isinstance(policy, str) and policy:
        return policy
    mode = payload.get("reversal_mode")
    if isinstance(mode, str) and mode:
        return _canonical_reversal_mode(mode)
    mode = config.get("reversal_mode")
    if isinstance(mode, str) and mode:
        return _canonical_reversal_mode(mode)
    return "manual_review"


def _canonical_reversal_mode(mode: str) -> str:
    return {
        "none": "never",
        "revoke_unredeemed": "revoke_if_unused",
    }.get(mode, mode)


def _is_invite_fulfillment(*, fulfillment: GrowthBenefitFulfillmentModel, payload: dict[str, Any]) -> bool:
    if isinstance(payload.get("invite_batch_id"), str):
        return True
    benefit_type = payload.get("benefit_type") or dict(fulfillment.config_snapshot or {}).get("benefit_type")
    return benefit_type in {"issue_invites", "issue_gift"}


def _is_wallet_credit_fulfillment(payload: dict[str, Any]) -> bool:
    return payload.get("benefit_type") == "wallet_credit" or isinstance(payload.get("wallet_credit"), dict)


def _optional_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _has_refund_reversal(reversals: list[object], *, refund_id: UUID) -> bool:
    return _has_reversal(reversals, event_type="refund", event_id=refund_id)
