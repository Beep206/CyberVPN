from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.application.events import EventOutboxService
from src.application.use_cases.growth_code_sets.snapshots import read_growth_checkout_v3_snapshot
from src.application.use_cases.payment_attempts.finalize_completed_payment import FinalizeCompletedPaymentUseCase
from src.application.use_cases.payment_attempts.snapshot_adapter import build_checkout_result_from_order
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.application.use_cases.payments.payment_completed_earnings import (
    append_payment_completed_partner_earning_publication,
)
from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_attempt_repo import PaymentAttemptRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.presentation.dependencies.auth_realms import RealmResolution

TERMINAL_PAYMENT_ATTEMPT_STATUSES = {
    PaymentAttemptStatus.SUCCEEDED.value,
    PaymentAttemptStatus.FAILED.value,
    PaymentAttemptStatus.EXPIRED.value,
    PaymentAttemptStatus.CANCELLED.value,
}


@dataclass(frozen=True)
class CreatePaymentAttemptResult:
    payment_attempt: PaymentAttemptModel
    invoice: InvoiceResponseDTO | None
    created: bool


class CreatePaymentAttemptUseCase:
    def __init__(self, session: AsyncSession, crypto_client: CryptoBotClient) -> None:
        self._session = session
        self._crypto_client = crypto_client
        self._orders = OrderRepository(session)
        self._attempts = PaymentAttemptRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        user_id: UUID,
        current_realm: RealmResolution,
        idempotency_key: str,
    ) -> CreatePaymentAttemptResult:
        order = await self._orders.get_by_id(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("Order not found")
        if str(order.auth_realm_id) != current_realm.realm_id:
            raise ValueError("Order does not belong to the current auth realm")

        await self._acquire_order_attempt_lock(order_id=order_id)
        refresh = getattr(self._session, "refresh", None)
        if callable(refresh):
            await refresh(order)

        existing = await self._attempts.get_by_order_and_idempotency_key(
            order_id=order_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return CreatePaymentAttemptResult(
                payment_attempt=existing,
                invoice=_invoice_from_snapshot(existing.provider_snapshot or {}),
                created=False,
            )
        if order.settlement_status == "paid":
            raise ValueError("Order is already settled")

        active_attempt = await self._attempts.get_active_for_order(order_id)
        if active_attempt is not None:
            raise ValueError("An active payment attempt already exists for this order")

        latest_attempt = await self._attempts.get_latest_for_order(order_id)
        if latest_attempt and latest_attempt.status == PaymentAttemptStatus.SUCCEEDED.value:
            raise ValueError("Order already has a succeeded payment attempt")

        attempt_number = latest_attempt.attempt_number + 1 if latest_attempt else 1
        if _decimal(order.gateway_amount) <= Decimal("0"):
            return await self._create_internal_zero_attempt(
                order=order,
                idempotency_key=idempotency_key,
                attempt_number=attempt_number,
                latest_attempt=latest_attempt,
            )

        quote_result = build_checkout_result_from_order(order)
        commit_result = await CommitCheckoutUseCase(self._session, self._crypto_client).execute(
            user_id=user_id,
            quote_result=quote_result,
            currency=order.currency_code,
            channel=order.sale_channel,
            description=_build_description(order),
            payload=f"{user_id}:{order.id}:attempt:{attempt_number}",
            checkout_mode="order_payment_attempt",
            payment_plan_id=order.subscription_plan_id,
            metadata_extra={
                "order_id": str(order.id),
                "idempotency_key": idempotency_key,
                "origin_checkout_session_id": str(order.checkout_session_id),
                "attempt_number": attempt_number,
            },
            idempotency_key=idempotency_key,
            publish_completed_payment_event=False,
        )

        status = (
            PaymentAttemptStatus.SUCCEEDED.value
            if commit_result.status == "completed"
            else PaymentAttemptStatus.PENDING.value
        )
        attempt = PaymentAttemptModel(
            order_id=order.id,
            payment_id=commit_result.payment.id,
            code_set_id=getattr(order, "code_set_id", None),
            supersedes_attempt_id=latest_attempt.id if latest_attempt else None,
            attempt_number=attempt_number,
            provider=commit_result.payment.provider,
            sale_channel=order.sale_channel,
            currency_code=order.currency_code,
            status=status,
            displayed_amount=float(order.displayed_price),
            wallet_amount=float(order.wallet_amount),
            gateway_amount=float(order.gateway_amount),
            external_reference=(
                commit_result.invoice.invoice_id if commit_result.invoice else commit_result.payment.external_id
            ),
            idempotency_key=idempotency_key,
            provider_snapshot=_snapshot_from_invoice(commit_result.invoice),
            request_snapshot={
                "order_id": str(order.id),
                "checkout_session_id": str(order.checkout_session_id),
                "sale_channel": order.sale_channel,
                "currency_code": order.currency_code,
                "attempt_number": attempt_number,
                "gateway_amount": float(order.gateway_amount),
                "wallet_amount": float(order.wallet_amount),
            },
            terminal_at=datetime.now(UTC) if status in TERMINAL_PAYMENT_ATTEMPT_STATUSES else None,
        )
        created_attempt = await self._attempts.create(attempt)
        order.settlement_status = "paid" if status == PaymentAttemptStatus.SUCCEEDED.value else "pending_payment"
        if status == PaymentAttemptStatus.SUCCEEDED.value:
            await append_payment_completed_partner_earning_publication(
                self._outbox,
                payment=commit_result.payment,
                payment_attempt=created_attempt,
                source="zero_gateway_order_payment_attempt",
            )

        await self._session.commit()
        refreshed_attempt = await self._attempts.get_by_id(created_attempt.id)
        if refreshed_attempt is None:
            raise ValueError("Payment attempt was created but could not be reloaded")
        return CreatePaymentAttemptResult(
            payment_attempt=refreshed_attempt,
            invoice=commit_result.invoice,
            created=True,
        )

    async def _acquire_order_attempt_lock(self, *, order_id: UUID) -> None:
        if self._session_dialect_name() != "postgresql":
            return
        await self._session.execute(
            text("select pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"payment_attempt:{order_id}"},
        )

    def _session_dialect_name(self) -> str | None:
        candidates = (
            self._session,
            getattr(self._session, "sync_session", None),
            getattr(self._session, "_session", None),
        )
        for candidate in candidates:
            if candidate is None:
                continue
            get_bind = getattr(candidate, "get_bind", None)
            if not callable(get_bind):
                continue
            bind = get_bind()
            dialect = getattr(bind, "dialect", None)
            dialect_name = getattr(dialect, "name", None)
            if isinstance(dialect_name, str):
                return dialect_name
        return None

    async def _create_internal_zero_attempt(
        self,
        *,
        order,
        idempotency_key: str,
        attempt_number: int,
        latest_attempt: PaymentAttemptModel | None,
    ) -> CreatePaymentAttemptResult:
        now = datetime.now(UTC)
        quote_snapshot = _quote_snapshot_from_order(order)
        reason_code, funding_source = _zero_payment_reason_and_funding_source(quote_snapshot)
        growth_checkout_snapshot = read_growth_checkout_v3_snapshot(dict(order.pricing_snapshot or {}))
        payment = PaymentModel(
            external_id=f"internal_zero:{order.id}",
            user_uuid=order.user_id,
            amount=float(order.displayed_price),
            currency=order.currency_code,
            status="completed",
            provider="internal_zero",
            subscription_days=int(quote_snapshot.get("duration_days") or 0),
            plan_id=order.subscription_plan_id,
            promo_code_id=order.promo_code_id,
            partner_code_id=order.partner_code_id,
            code_set_id=order.code_set_id,
            discount_amount=float(order.discount_amount),
            wallet_amount_used=float(order.wallet_amount),
            final_amount=0.0,
            addons_snapshot=list(quote_snapshot.get("addons") or []),
            entitlements_snapshot=dict(quote_snapshot.get("entitlements_snapshot") or {}),
            growth_snapshot={
                "code_set_id": str(order.code_set_id) if order.code_set_id else None,
                "code_resolution": _safe_code_resolution_snapshot(dict(quote_snapshot.get("code_resolution") or {})),
                "discounts": list(quote_snapshot.get("discounts") or []),
                "growth_checkout_snapshot": growth_checkout_snapshot,
                "growth_effects_snapshot": (
                    dict(growth_checkout_snapshot.get("growth_effects") or {}) if growth_checkout_snapshot else {}
                ),
            },
            metadata_={
                "checkout_mode": "zero_gateway_order_payment_attempt",
                "order_id": str(order.id),
                "checkout_session_id": str(order.checkout_session_id),
                "quote_session_id": str(order.quote_session_id) if order.quote_session_id else None,
                "no_external_invoice": True,
                "provider": "internal_zero",
                "reason_code": reason_code,
                "funding_source": funding_source,
                "settlement_mode": "internal_zero",
                "commission_base_amount": str(_decimal(order.commission_base_amount).quantize(Decimal("0.01"))),
            },
        )
        self._session.add(payment)
        await self._session.flush()
        attempt = PaymentAttemptModel(
            order_id=order.id,
            payment_id=payment.id,
            code_set_id=order.code_set_id,
            supersedes_attempt_id=latest_attempt.id if latest_attempt else None,
            attempt_number=attempt_number,
            provider="internal_zero",
            sale_channel=order.sale_channel,
            currency_code=order.currency_code,
            status=PaymentAttemptStatus.SUCCEEDED.value,
            displayed_amount=float(order.displayed_price),
            wallet_amount=float(order.wallet_amount),
            gateway_amount=0.0,
            external_reference=payment.external_id,
            idempotency_key=idempotency_key,
            provider_snapshot={
                "provider": "internal_zero",
                "status": PaymentAttemptStatus.SUCCEEDED.value,
                "invoice_created": False,
                "reason_code": reason_code,
                "funding_source": funding_source,
                "completed_at": now.isoformat(),
            },
            request_snapshot={
                "order_id": str(order.id),
                "checkout_session_id": str(order.checkout_session_id),
                "sale_channel": order.sale_channel,
                "currency_code": order.currency_code,
                "attempt_number": attempt_number,
                "gateway_amount": 0.0,
                "wallet_amount": float(order.wallet_amount),
                "source": "zero_gateway_order_payment_attempt",
            },
            terminal_at=now,
        )
        created_attempt = await self._attempts.create(attempt)
        await FinalizeCompletedPaymentUseCase(self._session).execute(
            order=order,
            payment=payment,
            payment_attempt=created_attempt,
            quote_snapshot=quote_snapshot,
            source="zero_gateway_order_payment_attempt",
        )
        await self._session.commit()
        refreshed_attempt = await self._attempts.get_by_id(created_attempt.id)
        if refreshed_attempt is None:
            raise ValueError("Payment attempt was created but could not be reloaded")
        return CreatePaymentAttemptResult(
            payment_attempt=refreshed_attempt,
            invoice=None,
            created=True,
        )


def _build_description(order) -> str:
    pricing_snapshot = order.pricing_snapshot or {}
    quote_snapshot = pricing_snapshot.get("quote") or {}
    plan_name = quote_snapshot.get("plan_name") or "plan"
    duration_days = quote_snapshot.get("duration_days") or 0
    return f"CyberVPN {plan_name} - {duration_days} days"


def _snapshot_from_invoice(invoice: InvoiceResponseDTO | None) -> dict:
    if invoice is None:
        return {}
    return {
        "invoice_id": invoice.invoice_id,
        "payment_url": invoice.payment_url,
        "amount": float(invoice.amount),
        "currency": invoice.currency,
        "status": invoice.status,
        "expires_at": invoice.expires_at.isoformat(),
    }


def _invoice_from_snapshot(snapshot: dict | None) -> InvoiceResponseDTO | None:
    if not snapshot or not snapshot.get("invoice_id"):
        return None
    expires_at = snapshot.get("expires_at")
    expires_at_value = (
        datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if isinstance(expires_at, str) else datetime.now(UTC)
    )
    return InvoiceResponseDTO(
        invoice_id=str(snapshot["invoice_id"]),
        payment_url=str(snapshot.get("payment_url", "")),
        amount=snapshot.get("amount", 0),
        currency=str(snapshot.get("currency", "USD")),
        status=str(snapshot.get("status", "pending")),
        expires_at=expires_at_value,
    )


def _quote_snapshot_from_order(order) -> dict:
    pricing_snapshot = dict(order.pricing_snapshot or {})
    return dict(pricing_snapshot.get("quote") or pricing_snapshot)


def _safe_code_resolution_snapshot(code_resolution: dict) -> dict:
    allowed_keys = {
        "accepted",
        "code_type",
        "action_context",
        "result",
        "reject_reason",
        "wrong_context_target",
        "issuer_type",
        "owner_type",
        "growth_code_id",
        "promo_code_id",
        "partner_code_id",
        "reservation_id",
        "user_message_key",
        "policy_snapshot",
    }
    return {key: code_resolution.get(key) for key in allowed_keys if key in code_resolution}


def _decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def _zero_payment_reason_and_funding_source(quote_snapshot: dict) -> tuple[str, str]:
    discount_amount = _decimal(quote_snapshot.get("discount_amount"))
    wallet_amount = _decimal(quote_snapshot.get("wallet_amount"))
    if discount_amount > 0 and wallet_amount > 0:
        return "mixed_fully_funded", "promotion_and_wallet"
    if wallet_amount > 0:
        return "wallet_fully_funded", "wallet"
    return "promotion_fully_funded", "promotion"
