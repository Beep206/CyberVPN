from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.infrastructure.database.models.growth_code_model import GrowthCodeReservationModel
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
    pass


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
    ) -> GrowthCodeReservationModel:
        existing = await self._codes.find_quote_reservation(
            growth_code_id=growth_code_id,
            quote_session_id=quote_session_id,
            user_id=user_id,
        )
        if existing is not None:
            code = await self._codes.get_code_by_id(growth_code_id)
            existing.expires_at = _normalize_utc(expires_at)
            existing.status = "reserved"
            await self._session.flush()
            if code is not None:
                log_growth_code_event(
                    "growth_code.reserved",
                    surface=CUSTOMER_COMMERCE_SURFACE,
                    code_type=code.code_type,
                    action_context="checkout",
                    result="success",
                    growth_code_id=str(code.id),
                    reservation_id=str(existing.id),
                )
            return existing

        reservation = await self._codes.create_reservation(
            GrowthCodeReservationModel(
                growth_code_id=growth_code_id,
                quote_session_id=quote_session_id,
                user_id=user_id,
                reserved_at=datetime.now(UTC),
                expires_at=_normalize_utc(expires_at),
                status="reserved",
            )
        )
        code = await self._codes.get_code_by_id(growth_code_id)
        if code is not None:
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
                    "quote_session_id": str(quote_session_id),
                    "user_id": str(user_id),
                    "expires_at": reservation.expires_at.isoformat(),
                },
                actor_context=OutboxActorContext(principal_type="customer", principal_id=str(user_id)),
                source_context={"source_use_case": "GrowthCodeReservationService.reserve_for_quote"},
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
        return reservation

    async def consume_for_order(
        self,
        *,
        reservation_id: UUID,
        order_id: UUID,
    ) -> GrowthCodeReservationModel:
        reservation = await self._codes.get_reservation_by_id(reservation_id)
        if reservation is None:
            raise GrowthCodeReservationError("Growth code reservation not found")
        code = await self._codes.get_code_by_id(reservation.growth_code_id)

        if reservation.status == "consumed":
            if reservation.consumed_order_id == order_id:
                return reservation
            raise GrowthCodeReservationError("Growth code reservation already consumed")

        if reservation.status != "reserved":
            raise GrowthCodeReservationError("Growth code reservation is not active")

        if _normalize_utc(reservation.expires_at) <= datetime.now(UTC):
            reservation.status = "expired"
            await self._session.flush()
            if code is not None:
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

        reservation.status = "consumed"
        reservation.consumed_order_id = order_id
        reservation.released_at = datetime.now(UTC)
        reservation.release_reason = "order_commit"
        await self._session.flush()
        if code is not None:
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

    async def release_for_quote(
        self,
        *,
        quote_session_id: UUID,
        reason: str,
        status: str = "released",
    ) -> None:
        reservations = await self._codes.list_reservations_for_quote_session(quote_session_id)
        released_at = datetime.now(UTC)
        for reservation in reservations:
            if reservation.status != "reserved":
                continue
            code = await self._codes.get_code_by_id(reservation.growth_code_id)
            reservation.status = status
            reservation.released_at = released_at
            reservation.release_reason = reason
            if code is None:
                continue
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
        await self._session.flush()


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
