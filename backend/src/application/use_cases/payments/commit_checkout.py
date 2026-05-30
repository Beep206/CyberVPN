"""Persist checkout results as completed or pending payments."""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.application.services.wallet_service import WalletService
from src.application.use_cases.growth_codes.reservations import GrowthCodeReservationService
from src.application.use_cases.payments.complete_zero_gateway import (
    CompleteZeroGatewayUseCase,
)
from src.application.use_cases.payments.post_payment import (
    PostPaymentProcessingUseCase,
)
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient

logger = logging.getLogger(__name__)


class CheckoutIdempotencyConflictError(ValueError):
    """Raised when a retry key is reused for a different checkout payload."""


@dataclass(frozen=True)
class CommitCheckoutResult:
    payment: PaymentModel
    status: str
    invoice: InvoiceResponseDTO | None = None


class CommitCheckoutUseCase:
    """Turn a checkout quote into a payment record and optional invoice."""

    def __init__(self, session: AsyncSession, crypto_client: CryptoBotClient) -> None:
        self._session = session
        self._crypto_client = crypto_client
        self._payments = PaymentRepository(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(
        self,
        *,
        user_id: UUID,
        quote_result,
        currency: str,
        channel: str,
        description: str,
        payload: str,
        checkout_mode: str = "new_purchase",
        payment_plan_id: UUID | None = None,
        use_quote_plan_id_for_payment: bool = True,
        subscription_days_override: int | None = None,
        metadata_extra: dict | None = None,
        idempotency_key: str | None = None,
    ) -> CommitCheckoutResult:
        normalized_idempotency_key = _normalize_idempotency_key(idempotency_key)
        if normalized_idempotency_key is not None:
            await self._acquire_idempotency_lock(
                user_id=user_id,
                idempotency_key=normalized_idempotency_key,
            )

        addons_snapshot = [
            {
                "addon_id": str(line.addon_id),
                "code": line.code,
                "qty": line.qty,
                "unit_price": float(line.unit_price),
                "total_price": float(line.total_price),
                "location_code": line.location_code,
                "delta_entitlements": line.delta_entitlements,
            }
            for line in quote_result.addons
        ]
        checkout_fingerprint = _build_checkout_fingerprint(
            user_id=user_id,
            quote_result=quote_result,
            currency=currency,
            channel=channel,
            checkout_mode=checkout_mode,
            payment_plan_id=payment_plan_id,
            use_quote_plan_id_for_payment=use_quote_plan_id_for_payment,
            subscription_days_override=subscription_days_override,
            metadata_extra=metadata_extra,
            addons_snapshot=addons_snapshot,
        )
        if normalized_idempotency_key is not None:
            existing = await self._payments.get_by_checkout_idempotency_key(
                user_uuid=user_id,
                idempotency_key=normalized_idempotency_key,
                checkout_mode=checkout_mode,
            )
            if existing is not None:
                existing_metadata = dict(existing.metadata_ or {})
                if existing_metadata.get("checkout_fingerprint") != checkout_fingerprint:
                    raise CheckoutIdempotencyConflictError(
                        "Idempotency-Key was already used for a different checkout request"
                    )
                return CommitCheckoutResult(
                    payment=existing,
                    status=str(existing.status),
                    invoice=_invoice_from_metadata(existing_metadata),
                )

        reservation_id = getattr(quote_result, "reservation_id", None)
        if reservation_id is None and _should_reserve_direct_growth_code(quote_result):
            reservation = await GrowthCodeReservationService(self._session).reserve_for_direct_checkout(
                growth_code_id=quote_result.code_resolution.growth_code_id,
                user_id=user_id,
            )
            reservation_id = reservation.id
            quote_result.reservation_id = reservation.id

        metadata = {
            "commission_base_amount": str(quote_result.commission_base_amount),
            "addon_amount": str(quote_result.addon_amount),
            "channel": channel,
            "plan_name": quote_result.plan_name,
            "checkout_mode": checkout_mode,
        }
        if normalized_idempotency_key is not None:
            metadata["checkout_idempotency_key"] = normalized_idempotency_key
            metadata["checkout_fingerprint"] = checkout_fingerprint
        if reservation_id is not None:
            metadata["growth_code_reservation_id"] = str(reservation_id)
        if metadata_extra:
            metadata.update(metadata_extra)

        resolved_plan_id = quote_result.plan_id if use_quote_plan_id_for_payment else payment_plan_id
        if payment_plan_id is not None:
            resolved_plan_id = payment_plan_id

        if quote_result.is_zero_gateway:
            zero_gateway = CompleteZeroGatewayUseCase(self._session)
            payment = await zero_gateway.execute(
                user_id=user_id,
                plan_id=resolved_plan_id,
                displayed_price=quote_result.displayed_price,
                discount_amount=quote_result.discount_amount,
                wallet_amount=quote_result.wallet_amount,
                promo_code_id=quote_result.promo_code_id,
                partner_code_id=quote_result.partner_code_id,
                currency=currency,
                addons_snapshot=addons_snapshot,
                entitlements_snapshot=quote_result.entitlements_snapshot,
                commission_base_amount=quote_result.commission_base_amount,
                metadata_extra=metadata,
                subscription_days_override=subscription_days_override,
            )
            post_payment = PostPaymentProcessingUseCase(self._session)
            await post_payment.execute(payment.id)
            return CommitCheckoutResult(payment=payment, status="completed")

        if quote_result.wallet_amount > 0:
            await self._wallet.freeze(user_id, quote_result.wallet_amount)
            metadata["wallet_frozen"] = True

        invoice_data = await self._crypto_client.create_invoice(
            amount=str(quote_result.gateway_amount),
            currency=currency,
            description=description,
            payload=payload,
        )

        invoice = InvoiceResponseDTO(
            invoice_id=str(invoice_data.get("invoice_id", "")),
            payment_url=(
                invoice_data.get("mini_app_invoice_url")
                or invoice_data.get("bot_invoice_url")
                or invoice_data.get("web_app_invoice_url")
                or invoice_data.get("pay_url", "")
            ),
            amount=quote_result.gateway_amount,
            currency=currency,
            status=invoice_data.get("status", "pending"),
            expires_at=self._parse_invoice_expiration(invoice_data.get("expiration_date")),
        )
        metadata["invoice_snapshot"] = _invoice_to_metadata(invoice)

        payment = PaymentModel(
            external_id=invoice.invoice_id,
            user_uuid=user_id,
            amount=float(quote_result.displayed_price),
            currency=currency,
            status="pending",
            provider="cryptobot",
            subscription_days=subscription_days_override or quote_result.duration_days or 0,
            plan_id=resolved_plan_id,
            promo_code_id=quote_result.promo_code_id,
            partner_code_id=quote_result.partner_code_id,
            discount_amount=float(quote_result.discount_amount),
            wallet_amount_used=float(quote_result.wallet_amount),
            final_amount=float(quote_result.gateway_amount),
            addons_snapshot=addons_snapshot,
            entitlements_snapshot=quote_result.entitlements_snapshot,
            metadata_=metadata,
        )
        payment = await self._payments.create(payment)

        logger.info(
            "pending_checkout_payment_created",
            extra={
                "payment_id": str(payment.id),
                "external_id": invoice.invoice_id,
                "checkout_mode": checkout_mode,
            },
        )
        return CommitCheckoutResult(payment=payment, status="pending", invoice=invoice)

    async def _acquire_idempotency_lock(self, *, user_id: UUID, idempotency_key: str) -> None:
        bind = self._session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return
        lock_key = f"checkout:{user_id}:{idempotency_key}"
        await self._session.execute(
            text("select pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": lock_key},
        )

    @staticmethod
    def _parse_invoice_expiration(value: str | None):
        from datetime import UTC, datetime

        if not value:
            return datetime.now(UTC)

        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now(UTC)


def _normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError("Idempotency-Key must not be blank")
    if len(normalized) > 120:
        raise ValueError("Idempotency-Key must be 120 characters or fewer")
    return normalized


def _should_reserve_direct_growth_code(quote_result) -> bool:
    resolution = getattr(quote_result, "code_resolution", None)
    if resolution is None or not resolution.accepted:
        return False
    if getattr(resolution, "growth_code_id", None) is None:
        return False
    code_type = getattr(resolution, "code_type", None)
    return getattr(code_type, "value", code_type) == "promo"


def _build_checkout_fingerprint(
    *,
    user_id: UUID,
    quote_result,
    currency: str,
    channel: str,
    checkout_mode: str,
    payment_plan_id: UUID | None,
    use_quote_plan_id_for_payment: bool,
    subscription_days_override: int | None,
    metadata_extra: dict | None,
    addons_snapshot: list[dict],
) -> str:
    payload = {
        "user_id": str(user_id),
        "currency": currency.upper(),
        "channel": channel,
        "checkout_mode": checkout_mode,
        "payment_plan_id": str(payment_plan_id) if payment_plan_id else None,
        "use_quote_plan_id_for_payment": use_quote_plan_id_for_payment,
        "subscription_days_override": subscription_days_override,
        "plan_id": str(quote_result.plan_id) if quote_result.plan_id else None,
        "promo_code_id": str(quote_result.promo_code_id) if quote_result.promo_code_id else None,
        "partner_code_id": str(quote_result.partner_code_id) if quote_result.partner_code_id else None,
        "displayed_price": str(quote_result.displayed_price),
        "discount_amount": str(quote_result.discount_amount),
        "wallet_amount": str(quote_result.wallet_amount),
        "gateway_amount": str(quote_result.gateway_amount),
        "addons": addons_snapshot,
        "metadata_extra": metadata_extra or {},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _invoice_to_metadata(invoice: InvoiceResponseDTO) -> dict:
    return {
        "invoice_id": invoice.invoice_id,
        "payment_url": invoice.payment_url,
        "amount": str(invoice.amount),
        "currency": invoice.currency,
        "status": invoice.status,
        "expires_at": invoice.expires_at.isoformat(),
    }


def _invoice_from_metadata(metadata: dict) -> InvoiceResponseDTO | None:
    snapshot = metadata.get("invoice_snapshot")
    if not isinstance(snapshot, dict):
        return None
    raw_expires_at = snapshot.get("expires_at")
    expires_at = datetime.now(UTC) + timedelta(minutes=30)
    if raw_expires_at:
        try:
            expires_at = datetime.fromisoformat(str(raw_expires_at))
        except ValueError:
            expires_at = datetime.now(UTC) + timedelta(minutes=30)
    return InvoiceResponseDTO(
        invoice_id=str(snapshot.get("invoice_id", "")),
        payment_url=str(snapshot.get("payment_url", "")),
        amount=Decimal(str(snapshot.get("amount", "0"))),
        currency=str(snapshot.get("currency", "")),
        status=str(snapshot.get("status", "pending")),
        expires_at=expires_at,
    )
