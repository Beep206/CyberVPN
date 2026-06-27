from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel, GrowthCodeReservationModel
from src.infrastructure.database.models.growth_code_set_model import GrowthCodeReservationGroupModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_COMMERCE_SURFACE,
    adjust_growth_code_reservations_active,
    log_growth_code_event,
    observe_growth_code_redemption,
    observe_growth_code_reservation_expiration,
    observe_promo_applied,
)


class GrowthCodeReservationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "GROWTH_CODE_RESERVATION_ERROR",
        message_key: str = "growth.errors.reservation_failed",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message_key = message_key
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class ReservationCapacityContext:
    risk_subject_id: UUID | None = None
    risk_decision_id: UUID | None = None
    device_key_hash: str | None = None
    velocity_bucket: str | None = None


@dataclass(frozen=True, slots=True)
class _CapacityDimension:
    dimension: str
    key_hash: str
    limit: int


@dataclass(frozen=True, slots=True)
class _ReservationPolicyCaps:
    global_cap: int | None
    per_user_cap: int | None
    dimensions: tuple[_CapacityDimension, ...]


_CAPACITY_CONTEXT_VERSION = "growth.reservation.capacity.v1"


class GrowthCodeReservationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._codes = GrowthCodeRepository(session)
        self._outbox = EventOutboxService(session)

    async def reserve_for_quote(
        self,
        *,
        growth_code_id: UUID,
        quote_session_id: UUID,
        user_id: UUID,
        expires_at: datetime,
        capacity_context: ReservationCapacityContext | None = None,
    ) -> GrowthCodeReservationModel:
        reservations = await self.reserve_many_for_quote(
            growth_code_ids=[growth_code_id],
            quote_session_id=quote_session_id,
            user_id=user_id,
            expires_at=expires_at,
            capacity_contexts={growth_code_id: capacity_context or ReservationCapacityContext()},
        )
        return reservations[growth_code_id]

    async def reserve_many_for_quote(
        self,
        *,
        growth_code_ids: list[UUID],
        quote_session_id: UUID | None,
        user_id: UUID,
        expires_at: datetime,
        capacity_contexts: dict[UUID, ReservationCapacityContext] | None = None,
    ) -> dict[UUID, GrowthCodeReservationModel]:
        ordered_code_ids = sorted(dict.fromkeys(growth_code_ids), key=str)
        if not ordered_code_ids:
            return {}

        locked_codes = await self._codes.lock_codes_sorted_for_update(ordered_code_ids)
        reservations: dict[UUID, GrowthCodeReservationModel] = {}
        for code in locked_codes:
            context = (capacity_contexts or {}).get(code.id) or ReservationCapacityContext()
            existing = None
            if quote_session_id is not None:
                existing = await self._codes.find_quote_reservation(
                    growth_code_id=code.id,
                    quote_session_id=quote_session_id,
                    user_id=user_id,
                )
            if existing is not None:
                existing.expires_at = _normalize_utc(expires_at)
                existing.status = "reserved"
                await self._session.flush()
                log_growth_code_event(
                    "growth_code.reserved",
                    surface=CUSTOMER_COMMERCE_SURFACE,
                    code_type=code.code_type,
                    action_context="checkout",
                    result="success",
                    growth_code_id=str(code.id),
                    reservation_id=str(existing.id),
                )
                reservations[code.id] = existing
                continue

            caps = await self._policy_caps_for_code(code, context)
            await self._reserve_capacity(code=code, user_id=user_id, caps=caps)
            reservation = await self._codes.create_reservation(
                GrowthCodeReservationModel(
                    growth_code_id=code.id,
                    quote_session_id=quote_session_id,
                    user_id=user_id,
                    risk_subject_id=context.risk_subject_id,
                    risk_decision_id=context.risk_decision_id,
                    device_key_hash=context.device_key_hash,
                    velocity_bucket=context.velocity_bucket,
                    capacity_context=_capacity_context_payload(caps),
                    reserved_at=datetime.now(UTC),
                    expires_at=_normalize_utc(expires_at),
                    status="reserved",
                )
            )
            await self._emit_reserved_event(
                code=code,
                reservation=reservation,
                quote_session_id=quote_session_id,
                user_id=user_id,
                source="quote" if quote_session_id is not None else "direct_checkout",
            )
            reservations[code.id] = reservation

        return reservations

    async def create_group_for_quote(
        self,
        *,
        code_set_id: UUID,
        reservations: list[GrowthCodeReservationModel],
        user_id: UUID,
        quote_session_id: UUID | None,
        expires_at: datetime,
        idempotency_key: str,
    ) -> GrowthCodeReservationGroupModel:
        existing = await self._get_group_by_idempotency_key(idempotency_key, for_update=True)
        ordered_reservations = sorted(reservations, key=lambda item: (str(item.growth_code_id), str(item.id)))
        if existing is not None:
            for reservation in ordered_reservations:
                reservation.reservation_group_id = existing.id
            await self._session.flush()
            return existing

        reserved_at = min((reservation.reserved_at for reservation in ordered_reservations), default=datetime.now(UTC))
        try:
            async with self._session.begin_nested():
                group = GrowthCodeReservationGroupModel(
                    code_set_id=code_set_id,
                    status="reserved",
                    user_id=user_id,
                    quote_session_id=quote_session_id,
                    reserved_at=_normalize_utc(reserved_at),
                    expires_at=_normalize_utc(expires_at),
                    idempotency_key=idempotency_key,
                )
                self._session.add(group)
                await self._session.flush()
        except IntegrityError:
            existing = await self._get_group_by_idempotency_key(idempotency_key, for_update=True)
            if existing is None:
                raise
            for reservation in ordered_reservations:
                reservation.reservation_group_id = existing.id
            await self._session.flush()
            return existing
        for reservation in ordered_reservations:
            reservation.reservation_group_id = group.id
        await self._outbox.append_event(
            event_name="growth_code.reserved",
            aggregate_type="growth_code_reservation_group",
            aggregate_id=str(group.id),
            partition_key=str(user_id),
            event_payload={
                "reservation_group_id": str(group.id),
                "code_set_id": str(code_set_id),
                "quote_session_id": str(quote_session_id) if quote_session_id else None,
                "reservation_ids": [str(reservation.id) for reservation in ordered_reservations],
                "expires_at": group.expires_at.isoformat(),
            },
            actor_context=OutboxActorContext(principal_type="customer", principal_id=str(user_id)),
            source_context={"source_use_case": "GrowthCodeReservationService.create_group_for_quote"},
        )
        await self._session.flush()
        return group

    async def reserve_for_direct_checkout(
        self,
        *,
        growth_code_id: UUID,
        user_id: UUID,
        expires_at: datetime | None = None,
    ) -> GrowthCodeReservationModel:
        """Reserve a promo for direct commit paths that do not create quote sessions."""
        reservations = await self.reserve_many_for_quote(
            growth_code_ids=[growth_code_id],
            quote_session_id=None,
            user_id=user_id,
            expires_at=expires_at or (datetime.now(UTC) + timedelta(minutes=30)),
        )
        return reservations[growth_code_id]

    async def consume_for_order(
        self,
        *,
        reservation_id: UUID,
        order_id: UUID,
    ) -> GrowthCodeReservationModel:
        reservation, code = await self._lock_transition_rows(reservation_id)

        if reservation.status == "consumed":
            if reservation.consumed_order_id == order_id:
                return reservation
            raise GrowthCodeReservationError("Growth code reservation already consumed")

        if reservation.status != "reserved":
            raise GrowthCodeReservationError("Growth code reservation is not active")

        if _normalize_utc(reservation.expires_at) <= datetime.now(UTC):
            await self._release_reserved_capacity(reservation=reservation, code=code)
            reservation.status = "expired"
            await self._session.flush()
            adjust_growth_code_reservations_active(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                delta=-1,
            )
            observe_growth_code_reservation_expiration(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                reason_code="expired_before_commit",
            )
            raise GrowthCodeReservationError("Growth code reservation has expired")

        await self._consume_reserved_capacity(reservation=reservation, code=code)
        reservation.status = "consumed"
        reservation.consumed_order_id = order_id
        reservation.released_at = datetime.now(UTC)
        reservation.release_reason = "order_commit"
        await self._session.flush()
        adjust_growth_code_reservations_active(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            delta=-1,
        )
        await self._outbox.append_event(
            event_name="growth_code.redeemed",
            aggregate_type="growth_code",
            aggregate_id=str(code.id),
            partition_key=str(code.id),
            event_payload={
                "growth_code_id": str(code.id),
                "reservation_id": str(reservation.id),
                "order_id": str(order_id),
                "code_type": code.code_type,
            },
            actor_context=OutboxActorContext(
                principal_type="customer" if reservation.user_id else "system",
                principal_id=str(reservation.user_id) if reservation.user_id else None,
            ),
            source_context={"source_use_case": "GrowthCodeReservationService.consume_for_order"},
        )
        observe_growth_code_redemption(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            result="success",
        )
        if code.code_type == "promo":
            await self._outbox.append_event(
                event_name="promo.applied_to_order",
                aggregate_type="growth_code",
                aggregate_id=str(code.id),
                partition_key=str(code.id),
                event_payload={
                    "growth_code_id": str(code.id),
                    "reservation_id": str(reservation.id),
                    "order_id": str(order_id),
                },
                actor_context=OutboxActorContext(
                    principal_type="customer" if reservation.user_id else "system",
                    principal_id=str(reservation.user_id) if reservation.user_id else None,
                ),
                source_context={"source_use_case": "GrowthCodeReservationService.consume_for_order"},
            )
            observe_promo_applied(surface=CUSTOMER_COMMERCE_SURFACE, result="success")
        log_growth_code_event(
            "growth_code.redeemed",
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=code.code_type,
            action_context="checkout",
            result="success",
            growth_code_id=str(code.id),
            reservation_id=str(reservation.id),
            order_id=str(order_id),
        )
        return reservation

    async def commit_for_order(
        self,
        *,
        reservation_id: UUID,
        order_id: UUID,
    ) -> GrowthCodeReservationModel:
        reservation, code = await self._lock_transition_rows(reservation_id)

        if reservation.status == "committed":
            if reservation.consumed_order_id == order_id:
                return reservation
            raise GrowthCodeReservationError("Growth code reservation already committed")

        if reservation.status == "consumed":
            if reservation.consumed_order_id == order_id:
                return reservation
            raise GrowthCodeReservationError("Growth code reservation already consumed")

        if reservation.status != "reserved":
            raise GrowthCodeReservationError("Growth code reservation is not active")

        if _normalize_utc(reservation.expires_at) <= datetime.now(UTC):
            await self._release_reserved_capacity(reservation=reservation, code=code)
            reservation.status = "expired"
            await self._session.flush()
            adjust_growth_code_reservations_active(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                delta=-1,
            )
            observe_growth_code_reservation_expiration(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                reason_code="expired_before_order_commit",
            )
            raise GrowthCodeReservationError("Growth code reservation has expired")

        reservation.status = "committed"
        reservation.consumed_order_id = order_id
        reservation.committed_at = datetime.now(UTC)
        await self._session.flush()
        adjust_growth_code_reservations_active(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            delta=-1,
        )
        await self._outbox.append_event(
            event_name="growth_code.reservation_committed",
            aggregate_type="growth_code",
            aggregate_id=str(code.id),
            partition_key=str(code.id),
            event_payload={
                "growth_code_id": str(code.id),
                "reservation_id": str(reservation.id),
                "order_id": str(order_id),
                "code_type": code.code_type,
            },
            actor_context=OutboxActorContext(
                principal_type="customer" if reservation.user_id else "system",
                principal_id=str(reservation.user_id) if reservation.user_id else None,
            ),
            source_context={"source_use_case": "GrowthCodeReservationService.commit_for_order"},
        )
        return reservation

    async def consume_for_settlement(
        self,
        *,
        reservation_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        user_id: UUID,
    ) -> GrowthCodeReservationModel:
        reservation, code = await self._lock_transition_rows(reservation_id)

        if reservation.status == "consumed":
            if reservation.consumed_order_id != order_id:
                raise GrowthCodeReservationError("Growth code reservation already consumed")
            if reservation.consumed_payment_id is None:
                reservation.consumed_payment_id = payment_id
                reservation.consumed_at = reservation.consumed_at or datetime.now(UTC)
                reservation.release_reason = reservation.release_reason or "payment_settlement"
                await self._session.flush()
                return reservation
            if reservation.consumed_payment_id == payment_id:
                return reservation
            raise GrowthCodeReservationError("Growth code reservation already consumed")

        was_reserved = reservation.status == "reserved"
        if reservation.status not in {"reserved", "committed"}:
            raise GrowthCodeReservationError("Growth code reservation is not committed")

        if _normalize_utc(reservation.expires_at) <= datetime.now(UTC):
            await self._release_reserved_capacity(reservation=reservation, code=code)
            reservation.status = "expired"
            await self._session.flush()
            if was_reserved:
                adjust_growth_code_reservations_active(
                    code_type=code.code_type,
                    surface=CUSTOMER_COMMERCE_SURFACE,
                    delta=-1,
                )
            observe_growth_code_reservation_expiration(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                reason_code="expired_before_payment_settlement",
            )
            raise GrowthCodeReservationError("Growth code reservation has expired")

        if reservation.consumed_order_id is not None and reservation.consumed_order_id != order_id:
            raise GrowthCodeReservationError("Growth code reservation belongs to a different order")

        await self._consume_reserved_capacity(reservation=reservation, code=code)
        reservation.status = "consumed"
        reservation.consumed_order_id = order_id
        reservation.consumed_payment_id = payment_id
        reservation.consumed_at = datetime.now(UTC)
        reservation.released_at = reservation.consumed_at
        reservation.release_reason = "payment_settlement"
        await self._session.flush()
        if was_reserved:
            adjust_growth_code_reservations_active(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                delta=-1,
            )
        await self._outbox.append_event(
            event_name="growth_code.redeemed",
            aggregate_type="growth_code",
            aggregate_id=str(code.id),
            partition_key=str(code.id),
            event_payload={
                "growth_code_id": str(code.id),
                "reservation_id": str(reservation.id),
                "order_id": str(order_id),
                "payment_id": str(payment_id),
                "code_type": code.code_type,
            },
            actor_context=OutboxActorContext(principal_type="customer", principal_id=str(user_id)),
            source_context={"source_use_case": "GrowthCodeReservationService.consume_for_settlement"},
        )
        observe_growth_code_redemption(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            result="success",
        )
        if code.code_type == "promo":
            await self._outbox.append_event(
                event_name="promo.applied_to_order",
                aggregate_type="growth_code",
                aggregate_id=str(code.id),
                partition_key=str(code.id),
                event_payload={
                    "growth_code_id": str(code.id),
                    "reservation_id": str(reservation.id),
                    "order_id": str(order_id),
                    "payment_id": str(payment_id),
                },
                actor_context=OutboxActorContext(principal_type="customer", principal_id=str(user_id)),
                source_context={"source_use_case": "GrowthCodeReservationService.consume_for_settlement"},
            )
            observe_promo_applied(surface=CUSTOMER_COMMERCE_SURFACE, result="success")
        log_growth_code_event(
            "growth_code.redeemed",
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=code.code_type,
            action_context="checkout",
            result="success",
            growth_code_id=str(code.id),
            reservation_id=str(reservation.id),
            order_id=str(order_id),
            payment_id=str(payment_id),
        )
        return reservation

    async def bind_groups_to_checkout_session(
        self,
        *,
        quote_session_id: UUID,
        checkout_session_id: UUID,
    ) -> None:
        reservations = await self._codes.list_reservations_for_quote_session(quote_session_id)
        group_ids = {
            reservation.reservation_group_id for reservation in reservations if reservation.reservation_group_id
        }
        for group_id in sorted(group_ids, key=str):
            group = await self._session.get(GrowthCodeReservationGroupModel, group_id)
            if group is None:
                continue
            group.checkout_session_id = checkout_session_id
        await self._session.flush()

    async def commit_group_for_order(
        self,
        *,
        reservation_ids: list[UUID],
        order_id: UUID,
    ) -> list[GrowthCodeReservationModel]:
        reservations = await self._load_reservations_sorted(reservation_ids)
        committed: list[GrowthCodeReservationModel] = []
        for reservation in reservations:
            committed.append(await self.commit_for_order(reservation_id=reservation.id, order_id=order_id))
        await self._sync_groups(
            reservations=committed,
            status="committed",
            order_id=order_id,
            payment_id=None,
            release_reason=None,
        )
        return committed

    async def consume_group_for_order(
        self,
        *,
        reservation_ids: list[UUID],
        order_id: UUID,
    ) -> list[GrowthCodeReservationModel]:
        reservations = await self._load_reservations_sorted(reservation_ids)
        consumed: list[GrowthCodeReservationModel] = []
        for reservation in reservations:
            consumed.append(await self.consume_for_order(reservation_id=reservation.id, order_id=order_id))
        await self._sync_groups(
            reservations=consumed,
            status="consumed",
            order_id=order_id,
            payment_id=None,
            release_reason="order_commit",
        )
        return consumed

    async def consume_group_for_settlement(
        self,
        *,
        reservation_ids: list[UUID],
        order_id: UUID,
        payment_id: UUID,
        user_id: UUID,
    ) -> list[GrowthCodeReservationModel]:
        reservations = await self._load_reservations_sorted(reservation_ids)
        consumed: list[GrowthCodeReservationModel] = []
        for reservation in reservations:
            consumed.append(
                await self.consume_for_settlement(
                    reservation_id=reservation.id,
                    order_id=order_id,
                    payment_id=payment_id,
                    user_id=user_id,
                )
            )
        await self._sync_groups(
            reservations=consumed,
            status="consumed",
            order_id=order_id,
            payment_id=payment_id,
            release_reason="payment_settlement",
        )
        return consumed

    async def consume_for_payment(
        self,
        *,
        reservation_id: UUID,
        payment_id: UUID,
        user_id: UUID,
    ) -> GrowthCodeReservationModel:
        """Consume a direct-checkout reservation after the payment is completed."""
        reservation, code = await self._lock_transition_rows(reservation_id)

        if reservation.status == "consumed":
            return reservation

        if reservation.status != "reserved":
            raise GrowthCodeReservationError("Growth code reservation is not active")

        if _normalize_utc(reservation.expires_at) <= datetime.now(UTC):
            await self._release_reserved_capacity(reservation=reservation, code=code)
            reservation.status = "expired"
            await self._session.flush()
            adjust_growth_code_reservations_active(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                delta=-1,
            )
            observe_growth_code_reservation_expiration(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                reason_code="expired_before_payment_completion",
            )
            raise GrowthCodeReservationError("Growth code reservation has expired")

        await self._consume_reserved_capacity(reservation=reservation, code=code)
        reservation.status = "consumed"
        reservation.consumed_payment_id = payment_id
        reservation.consumed_at = datetime.now(UTC)
        reservation.released_at = reservation.consumed_at
        reservation.release_reason = "payment_commit"
        await self._session.flush()
        adjust_growth_code_reservations_active(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            delta=-1,
        )
        await self._outbox.append_event(
            event_name="growth_code.redeemed",
            aggregate_type="growth_code",
            aggregate_id=str(code.id),
            partition_key=str(code.id),
            event_payload={
                "growth_code_id": str(code.id),
                "reservation_id": str(reservation.id),
                "payment_id": str(payment_id),
                "code_type": code.code_type,
            },
            actor_context=OutboxActorContext(principal_type="customer", principal_id=str(user_id)),
            source_context={"source_use_case": "GrowthCodeReservationService.consume_for_payment"},
        )
        observe_growth_code_redemption(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            result="success",
        )
        if code.code_type == "promo":
            observe_promo_applied(surface=CUSTOMER_COMMERCE_SURFACE, result="success")
        log_growth_code_event(
            "growth_code.redeemed",
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=code.code_type,
            action_context="checkout",
            result="success",
            growth_code_id=str(code.id),
            reservation_id=str(reservation.id),
            payment_id=str(payment_id),
        )
        return reservation

    async def release_reservation(
        self,
        *,
        reservation_id: UUID,
        reason: str,
        status: str = "released",
    ) -> GrowthCodeReservationModel:
        reservation, code = await self._lock_transition_rows(reservation_id)
        if reservation.status != "reserved":
            raise GrowthCodeReservationError("Growth code reservation is not active")
        await self._release_reserved_capacity(reservation=reservation, code=code)
        reservation.status = status
        reservation.released_at = datetime.now(UTC)
        reservation.release_reason = reason
        await self._session.flush()
        adjust_growth_code_reservations_active(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            delta=-1,
        )
        event_name = "growth_code.reservation_expired" if status == "expired" else "growth_code.released"
        await self._outbox.append_event(
            event_name=event_name,
            aggregate_type="growth_code",
            aggregate_id=str(code.id),
            partition_key=str(code.id),
            event_payload={
                "growth_code_id": str(code.id),
                "reservation_id": str(reservation.id),
                "quote_session_id": str(reservation.quote_session_id) if reservation.quote_session_id else None,
                "reason_code": reason,
                "status": status,
            },
            actor_context=OutboxActorContext(
                principal_type="customer" if reservation.user_id else "system",
                principal_id=str(reservation.user_id) if reservation.user_id else None,
            ),
            source_context={"source_use_case": "GrowthCodeReservationService.release_reservation"},
        )
        if status == "expired":
            observe_growth_code_reservation_expiration(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                reason_code=reason,
            )
        log_growth_code_event(
            event_name,
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=code.code_type,
            action_context="checkout",
            result=status,
            growth_code_id=str(code.id),
            reservation_id=str(reservation.id),
            reason_code=reason,
        )
        return reservation

    async def release_for_quote(
        self,
        *,
        quote_session_id: UUID,
        reason: str,
        status: str = "released",
    ) -> None:
        reservations = sorted(
            await self._codes.list_reservations_for_quote_session(quote_session_id),
            key=lambda item: (str(item.growth_code_id), str(item.id)),
        )
        group_ids: set[UUID] = set()
        released_at = datetime.now(UTC)
        for initial_reservation in reservations:
            reservation, code = await self._lock_transition_rows(initial_reservation.id)
            if reservation.status != "reserved":
                continue
            if reservation.reservation_group_id is not None:
                group_ids.add(reservation.reservation_group_id)
            await self._release_reserved_capacity(reservation=reservation, code=code)
            reservation.status = status
            reservation.released_at = released_at
            reservation.release_reason = reason
            adjust_growth_code_reservations_active(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                delta=-1,
            )
            event_name = "growth_code.reservation_expired" if status == "expired" else "growth_code.released"
            await self._outbox.append_event(
                event_name=event_name,
                aggregate_type="growth_code",
                aggregate_id=str(code.id),
                partition_key=str(code.id),
                event_payload={
                    "growth_code_id": str(code.id),
                    "reservation_id": str(reservation.id),
                    "quote_session_id": str(quote_session_id),
                    "reason_code": reason,
                    "status": status,
                },
                actor_context=OutboxActorContext(
                    principal_type="customer" if reservation.user_id else "system",
                    principal_id=str(reservation.user_id) if reservation.user_id else None,
                ),
                source_context={"source_use_case": "GrowthCodeReservationService.release_for_quote"},
            )
            if status == "expired":
                observe_growth_code_reservation_expiration(
                    code_type=code.code_type,
                    surface=CUSTOMER_COMMERCE_SURFACE,
                    reason_code=reason,
                )
            log_growth_code_event(
                event_name,
                surface=CUSTOMER_COMMERCE_SURFACE,
                code_type=code.code_type,
                action_context="checkout",
                result=status,
                growth_code_id=str(code.id),
                reservation_id=str(reservation.id),
                reason_code=reason,
            )
        for group_id in sorted(group_ids, key=str):
            group = await self._session.get(GrowthCodeReservationGroupModel, group_id)
            if group is None:
                continue
            group.status = status
            group.released_at = released_at
            group.release_reason = reason
        await self._session.flush()

    async def replace_group_for_quote(
        self,
        *,
        old_group_id: UUID,
        code_set_id: UUID,
        reservations: list[GrowthCodeReservationModel],
        user_id: UUID,
        quote_session_id: UUID | None,
        expires_at: datetime,
        idempotency_key: str,
        reason: str = "code_set_replaced",
    ) -> GrowthCodeReservationGroupModel:
        new_group = await self.create_group_for_quote(
            code_set_id=code_set_id,
            reservations=reservations,
            user_id=user_id,
            quote_session_id=quote_session_id,
            expires_at=expires_at,
            idempotency_key=idempotency_key,
        )
        old_group = await self._session.get(GrowthCodeReservationGroupModel, old_group_id, with_for_update=True)
        if old_group is None:
            raise GrowthCodeReservationError("Growth code reservation group not found")
        if old_group.status == "released" and old_group.release_reason == reason:
            return new_group
        result = await self._session.execute(
            select(GrowthCodeReservationModel).where(GrowthCodeReservationModel.reservation_group_id == old_group_id)
        )
        released_at = datetime.now(UTC)
        for initial_reservation in sorted(
            result.scalars().all(),
            key=lambda item: (str(item.growth_code_id), str(item.id)),
        ):
            reservation, code = await self._lock_transition_rows(initial_reservation.id)
            if reservation.status != "reserved":
                if reservation.status == "released" and reservation.release_reason == reason:
                    continue
                raise GrowthCodeReservationError("Growth code reservation group cannot be replaced")
            await self._release_reserved_capacity(reservation=reservation, code=code)
            reservation.status = "released"
            reservation.released_at = released_at
            reservation.release_reason = reason
            adjust_growth_code_reservations_active(
                code_type=code.code_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                delta=-1,
            )
        old_group.status = "released"
        old_group.released_at = released_at
        old_group.release_reason = reason
        await self._session.flush()
        return new_group

    async def _emit_reserved_event(
        self,
        *,
        code: GrowthCodeModel,
        reservation: GrowthCodeReservationModel,
        quote_session_id: UUID | None,
        user_id: UUID,
        source: str,
    ) -> None:
        adjust_growth_code_reservations_active(
            code_type=code.code_type,
            surface=CUSTOMER_COMMERCE_SURFACE,
            delta=1,
        )
        await self._outbox.append_event(
            event_name="growth_code.reserved",
            aggregate_type="growth_code",
            aggregate_id=str(code.id),
            partition_key=str(code.id),
            event_payload={
                "growth_code_id": str(code.id),
                "reservation_id": str(reservation.id),
                "quote_session_id": str(quote_session_id) if quote_session_id else None,
                "user_id": str(user_id),
                "expires_at": reservation.expires_at.isoformat(),
                "source": source,
            },
            actor_context=OutboxActorContext(principal_type="customer", principal_id=str(user_id)),
            source_context={"source_use_case": "GrowthCodeReservationService.reserve_many_for_quote"},
        )
        log_growth_code_event(
            "growth_code.reserved",
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=code.code_type,
            action_context="checkout",
            result="success",
            growth_code_id=str(code.id),
            reservation_id=str(reservation.id),
        )

    async def _policy_caps_for_code(
        self,
        code: GrowthCodeModel,
        context: ReservationCapacityContext,
    ) -> _ReservationPolicyCaps:
        promo_policy = await self._codes.get_promo_policy(code.id) if code.code_type == "promo" else None
        policy_snapshot = dict(promo_policy.policy_snapshot or {}) if promo_policy is not None else {}
        return _ReservationPolicyCaps(
            global_cap=_min_positive_cap(
                code.max_uses,
                promo_policy.global_usage_cap if promo_policy is not None else None,
            ),
            per_user_cap=_positive_int(promo_policy.usage_cap_per_user if promo_policy is not None else None),
            dimensions=tuple(_capacity_dimensions_from_context(policy_snapshot, context)),
        )

    async def _reserve_capacity(
        self,
        *,
        code: GrowthCodeModel,
        user_id: UUID,
        caps: _ReservationPolicyCaps,
    ) -> None:
        self._ensure_code_reservable(code)
        if caps.global_cap is not None and int(code.uses_count or 0) + int(code.reserved_uses or 0) >= caps.global_cap:
            raise GrowthCodeReservationError(
                "Growth code capacity is exhausted",
                code="RESERVATION_GROUP_EXHAUSTED",
                message_key="growth.errors.code_exhausted",
                status_code=409,
            )

        user_counter = await self._codes.get_or_create_user_counter_for_update(
            growth_code_id=code.id,
            user_id=user_id,
        )
        if (
            caps.per_user_cap is not None
            and int(user_counter.consumed_uses or 0) + int(user_counter.reserved_uses or 0) >= caps.per_user_cap
        ):
            raise GrowthCodeReservationError(
                "Growth code user usage cap reached",
                code="PROMO_USER_USAGE_CAP_REACHED",
                message_key="growth.errors.user_usage_cap_reached",
                status_code=409,
            )

        capacity_counters = []
        for dimension in sorted(caps.dimensions, key=lambda item: (item.dimension, item.key_hash)):
            counter = await self._codes.get_or_create_capacity_counter_for_update(
                growth_code_id=code.id,
                capacity_dimension=dimension.dimension,
                capacity_key_hash=dimension.key_hash,
            )
            if int(counter.consumed_uses or 0) + int(counter.reserved_uses or 0) >= dimension.limit:
                raise GrowthCodeReservationError(
                    "Growth code capacity dimension cap reached",
                    code=f"{dimension.dimension.upper()}_USAGE_CAP_REACHED",
                    message_key=f"growth.errors.{dimension.dimension}_usage_cap_reached",
                    status_code=409,
                )
            capacity_counters.append(counter)

        code.reserved_uses = int(code.reserved_uses or 0) + 1
        user_counter.reserved_uses = int(user_counter.reserved_uses or 0) + 1
        for counter in capacity_counters:
            counter.reserved_uses = int(counter.reserved_uses or 0) + 1
        await self._session.flush()

    async def _lock_transition_rows(
        self,
        reservation_id: UUID,
    ) -> tuple[GrowthCodeReservationModel, GrowthCodeModel]:
        initial = await self._codes.get_reservation_by_id(reservation_id)
        if initial is None:
            raise GrowthCodeReservationError("Growth code reservation not found")
        locked_codes = await self._codes.lock_codes_sorted_for_update([initial.growth_code_id])
        code = locked_codes[0]
        if initial.user_id is not None:
            await self._codes.get_or_create_user_counter_for_update(
                growth_code_id=initial.growth_code_id,
                user_id=initial.user_id,
            )
        for dimension in _capacity_dimensions_from_reservation(initial):
            await self._codes.get_or_create_capacity_counter_for_update(
                growth_code_id=initial.growth_code_id,
                capacity_dimension=dimension.dimension,
                capacity_key_hash=dimension.key_hash,
            )
        reservation = await self._codes.lock_reservation_for_update(reservation_id)
        if reservation is None:
            raise GrowthCodeReservationError("Growth code reservation not found")
        if reservation.growth_code_id != code.id:
            raise GrowthCodeReservationError("Growth code reservation changed during transition")
        return reservation, code

    async def _release_reserved_capacity(
        self,
        *,
        reservation: GrowthCodeReservationModel,
        code: GrowthCodeModel,
    ) -> None:
        if not _capacity_accounted(reservation):
            return
        if int(code.reserved_uses or 0) <= 0:
            raise GrowthCodeReservationError("Growth code reserved capacity is inconsistent")
        code.reserved_uses = int(code.reserved_uses or 0) - 1
        if reservation.user_id is not None:
            user_counter = await self._codes.get_or_create_user_counter_for_update(
                growth_code_id=reservation.growth_code_id,
                user_id=reservation.user_id,
            )
            if int(user_counter.reserved_uses or 0) <= 0:
                raise GrowthCodeReservationError("Growth code user reserved capacity is inconsistent")
            user_counter.reserved_uses = int(user_counter.reserved_uses or 0) - 1
        for dimension in _capacity_dimensions_from_reservation(reservation):
            counter = await self._codes.get_or_create_capacity_counter_for_update(
                growth_code_id=reservation.growth_code_id,
                capacity_dimension=dimension.dimension,
                capacity_key_hash=dimension.key_hash,
            )
            if int(counter.reserved_uses or 0) <= 0:
                raise GrowthCodeReservationError("Growth code dimension reserved capacity is inconsistent")
            counter.reserved_uses = int(counter.reserved_uses or 0) - 1

    async def _consume_reserved_capacity(
        self,
        *,
        reservation: GrowthCodeReservationModel,
        code: GrowthCodeModel,
    ) -> None:
        if not _capacity_accounted(reservation):
            return
        await self._release_reserved_capacity(reservation=reservation, code=code)
        code.uses_count = int(code.uses_count or 0) + 1
        code.last_used_at = datetime.now(UTC)
        if reservation.user_id is not None:
            user_counter = await self._codes.get_or_create_user_counter_for_update(
                growth_code_id=reservation.growth_code_id,
                user_id=reservation.user_id,
            )
            user_counter.consumed_uses = int(user_counter.consumed_uses or 0) + 1
        for dimension in _capacity_dimensions_from_reservation(reservation):
            counter = await self._codes.get_or_create_capacity_counter_for_update(
                growth_code_id=reservation.growth_code_id,
                capacity_dimension=dimension.dimension,
                capacity_key_hash=dimension.key_hash,
            )
            counter.consumed_uses = int(counter.consumed_uses or 0) + 1

    @staticmethod
    def _ensure_code_reservable(code: GrowthCodeModel) -> None:
        if code.status != "active":
            raise GrowthCodeReservationError(
                "Growth code is not active",
                code="CODE_NOT_ACTIVE",
                message_key="growth.errors.code_not_active",
                status_code=409,
            )
        if code.expires_at is not None and _normalize_utc(code.expires_at) <= datetime.now(UTC):
            raise GrowthCodeReservationError(
                "Growth code has expired",
                code="CODE_EXPIRED",
                message_key="growth.errors.code_expired",
                status_code=409,
            )

    async def _get_group_by_idempotency_key(
        self,
        idempotency_key: str,
        *,
        for_update: bool = False,
    ) -> GrowthCodeReservationGroupModel | None:
        stmt = select(GrowthCodeReservationGroupModel).where(
            GrowthCodeReservationGroupModel.idempotency_key == idempotency_key
        )
        if for_update:
            stmt = stmt.with_for_update(of=GrowthCodeReservationGroupModel)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def _load_reservations_sorted(self, reservation_ids: list[UUID]) -> list[GrowthCodeReservationModel]:
        unique_ids = list(dict.fromkeys(reservation_ids))
        if not unique_ids:
            return []
        result = await self._session.execute(
            select(GrowthCodeReservationModel).where(GrowthCodeReservationModel.id.in_(unique_ids))
        )
        reservations = list(result.scalars().all())
        if len(reservations) != len(unique_ids):
            raise GrowthCodeReservationError("Growth code reservation not found")
        return sorted(reservations, key=lambda item: (str(item.growth_code_id), str(item.id)))

    async def _sync_groups(
        self,
        *,
        reservations: list[GrowthCodeReservationModel],
        status: str,
        order_id: UUID,
        payment_id: UUID | None,
        release_reason: str | None,
    ) -> None:
        now = datetime.now(UTC)
        group_ids = {
            reservation.reservation_group_id for reservation in reservations if reservation.reservation_group_id
        }
        for group_id in sorted(group_ids, key=str):
            group = await self._session.get(GrowthCodeReservationGroupModel, group_id)
            if group is None:
                continue
            group.status = status
            group.order_id = order_id
            if status == "committed":
                group.committed_at = group.committed_at or now
            if status == "consumed":
                group.consumed_at = group.consumed_at or now
            if payment_id is not None:
                group.payment_id = payment_id
            if release_reason is not None:
                group.release_reason = release_reason
        await self._session.flush()


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _capacity_context_payload(caps: _ReservationPolicyCaps) -> dict[str, Any]:
    dimensions = [
        {
            "dimension": dimension.dimension,
            "key_hash": dimension.key_hash,
            "limit": dimension.limit,
        }
        for dimension in caps.dimensions
    ]
    payload: dict[str, Any] = {
        "schema_version": _CAPACITY_CONTEXT_VERSION,
        "global_accounted": True,
        "user_counter_accounted": True,
        "dimensions": dimensions,
    }
    for dimension in caps.dimensions:
        if dimension.dimension == "risk_subject":
            payload["risk_subject_key_hash"] = dimension.key_hash
        if dimension.dimension == "velocity":
            payload["velocity_key_hash"] = dimension.key_hash
    return {
        **payload,
    }


def _capacity_accounted(reservation: GrowthCodeReservationModel) -> bool:
    context = dict(reservation.capacity_context or {})
    return context.get("schema_version") == _CAPACITY_CONTEXT_VERSION and context.get("global_accounted") is True


def _capacity_dimensions_from_reservation(reservation: GrowthCodeReservationModel) -> tuple[_CapacityDimension, ...]:
    context = dict(reservation.capacity_context or {})
    raw_dimensions = context.get("dimensions")
    if not isinstance(raw_dimensions, list):
        return ()
    dimensions: list[_CapacityDimension] = []
    for raw_dimension in raw_dimensions:
        if not isinstance(raw_dimension, dict):
            continue
        dimension = str(raw_dimension.get("dimension") or "")
        key_hash = str(raw_dimension.get("key_hash") or "")
        limit = _positive_int(raw_dimension.get("limit"))
        if dimension in {"risk_subject", "device", "velocity"} and key_hash and limit is not None:
            dimensions.append(_CapacityDimension(dimension=dimension, key_hash=key_hash, limit=limit))
    return tuple(sorted(dimensions, key=lambda item: (item.dimension, item.key_hash)))


def _capacity_dimensions_from_context(
    policy_snapshot: dict[str, Any],
    context: ReservationCapacityContext,
) -> tuple[_CapacityDimension, ...]:
    risk_limit = _capacity_limit(
        policy_snapshot,
        (
            "risk_subject",
            "risk_subject_cap",
            "risk_cluster_cap",
            "usage_cap_per_risk_subject",
            "usage_cap_per_risk_cluster",
        ),
    )
    device_limit = _capacity_limit(
        policy_snapshot,
        ("device", "device_cap", "usage_cap_per_device", "per_device_cap"),
    )
    velocity_limit = _capacity_limit(
        policy_snapshot,
        ("velocity", "velocity_cap", "usage_cap_per_velocity_bucket", "per_velocity_bucket_cap"),
    )

    dimensions: list[_CapacityDimension] = []
    if risk_limit is not None:
        if context.risk_subject_id is None:
            raise GrowthCodeReservationError(
                "Risk subject capacity context is required",
                code="CAPACITY_CONTEXT_REQUIRED",
                message_key="growth.errors.capacity_context_required",
                status_code=409,
            )
        dimensions.append(
            _CapacityDimension(
                dimension="risk_subject",
                key_hash=_hash_capacity_key("risk_subject", str(context.risk_subject_id)),
                limit=risk_limit,
            )
        )
    if device_limit is not None:
        if not context.device_key_hash:
            raise GrowthCodeReservationError(
                "Device capacity context is required",
                code="CAPACITY_CONTEXT_REQUIRED",
                message_key="growth.errors.capacity_context_required",
                status_code=409,
            )
        dimensions.append(
            _CapacityDimension(
                dimension="device",
                key_hash=str(context.device_key_hash),
                limit=device_limit,
            )
        )
    if velocity_limit is not None:
        if not context.velocity_bucket:
            raise GrowthCodeReservationError(
                "Velocity capacity context is required",
                code="CAPACITY_CONTEXT_REQUIRED",
                message_key="growth.errors.capacity_context_required",
                status_code=409,
            )
        dimensions.append(
            _CapacityDimension(
                dimension="velocity",
                key_hash=_hash_capacity_key("velocity", context.velocity_bucket),
                limit=velocity_limit,
            )
        )
    return tuple(sorted(dimensions, key=lambda item: (item.dimension, item.key_hash)))


def _capacity_limit(policy_snapshot: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    roots: list[dict[str, Any]] = []
    for raw_root in (
        policy_snapshot.get("reservation_caps"),
        policy_snapshot.get("caps"),
        policy_snapshot,
    ):
        if isinstance(raw_root, dict):
            roots.append(raw_root)
    for root in roots:
        for key in keys:
            value = root.get(key)
            if isinstance(value, dict):
                value = value.get("limit") or value.get("max_uses") or value.get("cap")
            cap = _positive_int(value)
            if cap is not None:
                return cap
    return None


def _positive_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int | float | str | bytes | bytearray):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _min_positive_cap(*values: object) -> int | None:
    caps = [cap for cap in (_positive_int(value) for value in values) if cap is not None]
    if not caps:
        return None
    return min(caps)


def _hash_capacity_key(dimension: str, value: str) -> str:
    encoded = f"{dimension}:{value}".encode()
    return hashlib.sha256(encoded).hexdigest()
