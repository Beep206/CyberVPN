from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.application.use_cases.payment_attempts.snapshot_adapter import build_checkout_result_from_order
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
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
        if order.settlement_status == "paid":
            raise ValueError("Order is already settled")

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

        active_attempt = await self._attempts.get_active_for_order(order_id)
        if active_attempt is not None:
            raise ValueError("An active payment attempt already exists for this order")

        latest_attempt = await self._attempts.get_latest_for_order(order_id)
        if latest_attempt and latest_attempt.status == PaymentAttemptStatus.SUCCEEDED.value:
            raise ValueError("Order already has a succeeded payment attempt")

        attempt_number = latest_attempt.attempt_number + 1 if latest_attempt else 1
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
        )

        status = (
            PaymentAttemptStatus.SUCCEEDED.value
            if commit_result.status == "completed"
            else PaymentAttemptStatus.PENDING.value
        )
        attempt = PaymentAttemptModel(
            order_id=order.id,
            payment_id=commit_result.payment.id,
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
                commit_result.invoice.invoice_id
                if commit_result.invoice
                else commit_result.payment.external_id
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

        await self._session.commit()
        refreshed_attempt = await self._attempts.get_by_id(created_attempt.id)
        if refreshed_attempt is None:
            raise ValueError("Payment attempt was created but could not be reloaded")
        return CreatePaymentAttemptResult(
            payment_attempt=refreshed_attempt,
            invoice=commit_result.invoice,
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
        datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if isinstance(expires_at, str)
        else datetime.now(UTC)
    )
    return InvoiceResponseDTO(
        invoice_id=str(snapshot["invoice_id"]),
        payment_url=str(snapshot.get("payment_url", "")),
        amount=snapshot.get("amount", 0),
        currency=str(snapshot.get("currency", "USD")),
        status=str(snapshot.get("status", "pending")),
        expires_at=expires_at_value,
    )
