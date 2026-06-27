"""Payment and checkout routes."""

import hmac
import logging
from dataclasses import asdict
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.stage1_growth_policy import Stage1GrowthPolicyError
from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.commerce_sessions.quote_serialization import _safe_code_label, _safe_code_ref
from src.application.use_cases.growth_code_sets.ledger import code_set_hash_for_applications
from src.application.use_cases.payments.checkout import (
    CheckoutAddonInput,
    CheckoutCodeBasketInput,
    CheckoutResult,
    CheckoutUseCase,
)
from src.application.use_cases.payments.crypto_payment import CreateCryptoInvoiceUseCase
from src.application.use_cases.payments.payment_completed_earnings import (
    RunPaymentCompletedEarningOutboxUseCase,
)
from src.application.use_cases.payments.payment_history import PaymentHistoryUseCase
from src.application.use_cases.payments.stage1_reconciliation import (
    DEFAULT_RECONCILIATION_LIMIT,
    MAX_RECONCILIATION_LIMIT,
    Stage1PaymentReconciliationUseCase,
    assert_stage1_payment_reconciliation_output_is_redacted,
)
from src.config.settings import settings
from src.domain.enums import PaymentProvider, PaymentStatus
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.instrumentation.routes import track_payment
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.presentation.api.shared.growth_customer_errors import growth_customer_error_from_value_error
from src.presentation.api.shared.stage1_payment_runtime import (
    require_stage1_payments_enabled,
    require_stage1_telegram_stars_enabled,
)
from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonResponse,
    CheckoutCodeRefResponse,
    CheckoutCodeResolutionResponse,
    CheckoutCodeSetResponse,
    CheckoutCommitResponse,
    CheckoutDiscountResponse,
    CheckoutQuoteRequest,
    CheckoutQuoteResponse,
    CreateInvoiceRequest,
    EntitlementsSnapshotResponse,
    InvoiceResponse,
    PaymentHistoryResponse,
    PaymentStatusResponse,
)
from src.presentation.api.v1.payments.telegram_stars import create_telegram_stars_checkout
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission
from src.presentation.dependencies.services import get_crypto_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


def _code_ref_response(value: str | None) -> CheckoutCodeRefResponse | None:
    code_ref = _safe_code_ref(value)
    if code_ref is None:
        return None
    return CheckoutCodeRefResponse.model_validate(code_ref)


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _is_valid_payment_settlement_worker_secret(secret: str | None) -> bool:
    configured = settings.payment_settlement_worker_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_payment_settlement_worker_secret(secret: str | None) -> None:
    if _is_valid_payment_settlement_worker_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _raise_checkout_value_error(exc: ValueError) -> NoReturn:
    mapped_error = growth_customer_error_from_value_error(exc)
    if mapped_error is not None:
        raise HTTPException(status_code=mapped_error.status_code, detail=mapped_error.detail()) from None
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


def _code_set_snapshot_for_response(result: CheckoutResult) -> dict | None:
    existing = getattr(result, "code_set_snapshot", None)
    if isinstance(existing, dict):
        return existing
    applications = [dict(item) for item in getattr(result, "code_set_applications", [])]
    if not applications:
        return None
    return {
        "id": getattr(result, "code_set_id", None),
        "hash": getattr(result, "code_set_hash", None) or code_set_hash_for_applications(applications),
        "acceptance_mode": getattr(result, "code_set_acceptance_mode", None) or "all_or_nothing",
        "applications": applications,
    }


def _serialize_quote(result) -> CheckoutQuoteResponse:
    code_set_snapshot = _code_set_snapshot_for_response(result)
    code_set_response = CheckoutCodeSetResponse.model_validate(code_set_snapshot) if code_set_snapshot else None
    return CheckoutQuoteResponse(
        base_price=float(result.base_price),
        addon_amount=float(result.addon_amount),
        displayed_price=float(result.displayed_price),
        discount_amount=float(result.discount_amount),
        wallet_amount=float(result.wallet_amount),
        gateway_amount=float(result.gateway_amount),
        partner_markup=float(result.partner_markup),
        is_zero_gateway=result.is_zero_gateway,
        requires_external_payment=not result.is_zero_gateway,
        settlement_mode="internal_zero" if result.is_zero_gateway else "external_gateway",
        next_action="commit_and_activate" if result.is_zero_gateway else "create_payment_attempt",
        plan_id=result.plan_id,
        promo_code_id=result.promo_code_id,
        partner_code_id=result.partner_code_id,
        private_catalog_grant_id=result.private_catalog_grant_id,
        code_set_id=getattr(result, "code_set_id", None),
        code_set_hash=getattr(result, "code_set_hash", None)
        or (code_set_snapshot.get("hash") if code_set_snapshot else None),
        reservation_group_id=getattr(result, "reservation_group_id", None),
        code_set=code_set_response,
        code_input=_safe_code_label(result.code_input),
        code_input_ref=_code_ref_response(result.code_input),
        code_resolution=(
            CheckoutCodeResolutionResponse(
                accepted=result.code_resolution.accepted,
                code_type=result.code_resolution.code_type,
                action_context=result.code_resolution.action_context,
                result=result.code_resolution.result,
                reject_reason=result.code_resolution.reject_reason,
                conflict_code=result.code_resolution.conflict_code,
                wrong_context_target=result.code_resolution.wrong_context_target,
                issuer_type=result.code_resolution.issuer_type,
                owner_type=result.code_resolution.owner_type,
                resolved_code_id=result.code_resolution.resolved_code_id,
                growth_code_id=result.code_resolution.growth_code_id,
                promo_code_id=result.code_resolution.promo_code_id,
                partner_code_id=result.code_resolution.partner_code_id,
                user_message_key=result.code_resolution.user_message_key,
                reservation_id=result.reservation_id,
            )
            if result.code_resolution is not None
            else None
        ),
        discounts=[
            CheckoutDiscountResponse(
                type=discount.discount_type,
                code=_safe_code_label(discount.code) or "",
                code_ref=_code_ref_response(discount.code),
                amount=float(discount.amount),
                policy_version_id=discount.policy_version_id,
            )
            for discount in result.discounts
        ],
        growth_effects=(
            getattr(result, "growth_checkout_snapshot", {}).get("growth_effects")
            if isinstance(getattr(result, "growth_checkout_snapshot", None), dict)
            else None
        ),
        addons=[
            CheckoutAddonResponse(
                addon_id=line.addon_id,
                code=line.code,
                display_name=line.display_name,
                qty=line.qty,
                unit_price=float(line.unit_price),
                total_price=float(line.total_price),
                location_code=line.location_code,
            )
            for line in result.addons
        ],
        entitlements_snapshot=EntitlementsSnapshotResponse.model_validate(result.entitlements_snapshot),
    )


async def _build_quote(
    *,
    body: CheckoutQuoteRequest,
    db: AsyncSession,
    user_id: UUID,
) -> CheckoutResult:
    if body.private_catalog_grant_id is not None:
        _raise_checkout_value_error(ValueError("PRIVATE_CATALOG_GRANT_REQUIRES_QUOTE_SESSION"))
    use_case = CheckoutUseCase(db)
    try:
        return await use_case.execute(
            user_id=user_id,
            plan_id=body.plan_id,
            currency=body.currency,
            code_input=body.code_input,
            promo_code=body.promo_code,
            partner_code=body.partner_code,
            use_wallet=Decimal(str(body.use_wallet)),
            addons=[
                CheckoutAddonInput(
                    code=addon.code,
                    qty=addon.qty,
                    location_code=addon.location_code,
                )
                for addon in body.addons
            ],
            code_basket=[
                CheckoutCodeBasketInput(
                    code=item.code,
                    client_slot_id=item.client_slot_id,
                )
                for item in body.codes
            ],
            sale_channel=body.channel,
        )
    except Stage1GrowthPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from None
    except ValueError as exc:
        _raise_checkout_value_error(exc)


@router.post(
    "/crypto/invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid payment parameters"},
        422: {"description": "Validation error"},
    },
)
async def create_crypto_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_CREATE)),
) -> InvoiceResponse:
    """Create a direct cryptocurrency invoice."""
    require_stage1_payments_enabled()
    plan_repo = SubscriptionPlanRepository(db)
    use_case = CreateCryptoInvoiceUseCase(
        crypto_client=crypto_client,
        plan_repo=plan_repo,
    )

    try:
        invoice_data = await use_case.execute(
            user_uuid=request.user_uuid,
            plan_id=request.plan_id,
            currency=request.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    track_payment(status="created", currency=request.currency)
    return InvoiceResponse(**asdict(invoice_data))


@router.get(
    "/crypto/invoice/{invoice_id}",
    response_model=InvoiceResponse,
    responses={404: {"description": "Invoice not found"}},
)
async def get_crypto_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> InvoiceResponse:
    """Get a crypto invoice by ID."""
    plan_repo = SubscriptionPlanRepository(db)
    use_case = CreateCryptoInvoiceUseCase(
        crypto_client=crypto_client,
        plan_repo=plan_repo,
    )

    invoice_data = await use_case.get_invoice(invoice_id=invoice_id)
    if not invoice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    return InvoiceResponse(**asdict(invoice_data))


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
) -> PaymentHistoryResponse:
    """Return safe payment history for the authenticated customer."""
    payment_repo = PaymentRepository(db)
    use_case = PaymentHistoryUseCase(repo=payment_repo)

    payments = await use_case.get_by_user(
        user_uuid=user_id,
        offset=offset,
        limit=limit,
    )

    return PaymentHistoryResponse(payments=payments)


@router.post("/checkout/quote", response_model=CheckoutQuoteResponse)
async def quote_checkout(
    body: CheckoutQuoteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> CheckoutQuoteResponse:
    """Calculate checkout totals and effective entitlements without persisting payment."""
    result = await _build_quote(body=body, db=db, user_id=user_id)
    return _serialize_quote(result)


def _legacy_checkout_disabled_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "Legacy checkout commit is disabled. Use quote sessions, checkout sessions, orders, and payment attempts."
        ),
    )


@router.post(
    "/checkout/commit",
    response_model=CheckoutCommitResponse,
    deprecated=True,
    responses={410: {"description": "Legacy checkout commit is disabled"}},
)
async def commit_checkout(
    body: CheckoutQuoteRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> CheckoutCommitResponse:
    """Fail closed instead of committing payment from client-supplied quote inputs."""
    _ = body, idempotency_key, user_id
    raise _legacy_checkout_disabled_exception()


@router.post("/checkout/telegram-stars", response_model=CheckoutCommitResponse)
async def commit_telegram_stars_checkout(
    body: CheckoutQuoteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> CheckoutCommitResponse:
    """Create a Telegram Stars invoice link for Mini App base-plan checkout."""
    require_stage1_telegram_stars_enabled()
    if body.channel != "miniapp":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram Stars checkout is Mini App only")
    if body.currency.upper() != "XTR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram Stars checkout requires XTR")
    if body.use_wallet > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet is not supported for Telegram Stars",
        )
    if body.addons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram Stars checkout is currently available for base plans only",
        )

    result = await _build_quote(body=body, db=db, user_id=user_id)
    quote_response = _serialize_quote(result)
    mobile_user = await db.get(MobileUserModel, user_id)
    if mobile_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stars_result = await create_telegram_stars_checkout(
        db,
        user=mobile_user,
        quote_result=result,
        channel=body.channel,
        checkout_mode="new_purchase",
        description=f"CyberVPN {result.plan_name or 'plan'} - {result.duration_days or 0} days",
    )
    await db.commit()

    invoice = InvoiceResponse(
        invoice_id=str(stars_result.payment.id),
        payment_url=stars_result.invoice_url,
        amount=float(stars_result.stars_amount),
        currency="XTR",
        status="pending",
        expires_at=stars_result.expires_at,
    )
    return CheckoutCommitResponse(
        **quote_response.model_dump(),
        payment_id=stars_result.payment.id,
        status="pending",
        invoice=invoice,
    )


@router.post(
    "/checkout",
    response_model=CheckoutCommitResponse,
    deprecated=True,
    responses={410: {"description": "Legacy checkout commit is disabled"}},
)
async def checkout_alias(
    body: CheckoutQuoteRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> CheckoutCommitResponse:
    """Backward-compatible alias for the disabled legacy checkout commit."""
    _ = body, idempotency_key, user_id
    raise _legacy_checkout_disabled_exception()


@router.post("/internal/reconciliation/run")
async def run_stage1_payment_reconciliation(
    limit: int = Query(DEFAULT_RECONCILIATION_LIMIT, ge=1, le=MAX_RECONCILIATION_LIMIT),
    db: AsyncSession = Depends(get_db),
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
) -> dict:
    """Run the internal S1 payment reconciliation scan.

    The response is intentionally redacted so it can be stored as launch
    evidence without raw provider ids, payment ids, order ids or idempotency
    keys.
    """

    _require_telegram_bot_secret(telegram_bot_secret)
    report = await Stage1PaymentReconciliationUseCase(db).execute(limit=limit)
    payload = report.to_api_dict()
    assert_stage1_payment_reconciliation_output_is_redacted(payload)
    logger.info(
        "stage1_payment_reconciliation_completed",
        extra={
            "total_items": payload["summary"]["total_items"],
            "p0_blocker_items": payload["summary"]["p0_blocker_items"],
            "launch_blocked": payload["summary"]["launch_blocked"],
        },
    )
    return payload


@router.post("/internal/partner-earnings/run", include_in_schema=False)
async def run_payment_completed_partner_earnings(
    limit: int = Query(25, ge=1, le=100),
    worker_id: str = Query("task-worker", min_length=1, max_length=120),
    db: AsyncSession = Depends(get_db),
    payment_settlement_worker_secret: str | None = Header(
        default=None,
        alias="X-Payment-Settlement-Worker-Secret",
    ),
) -> dict:
    """Claim and process durable payment.completed partner earning publications."""

    _require_payment_settlement_worker_secret(payment_settlement_worker_secret)
    report = await RunPaymentCompletedEarningOutboxUseCase(db).execute(limit=limit, worker_id=worker_id)
    logger.info(
        "payment_completed_partner_earning_outbox_run_completed",
        extra={
            "claimed": report["claimed"],
            "succeeded": report["succeeded"],
            "retrying": report["retrying"],
            "dead_letter": report["dead_letter"],
        },
    )
    return report


@router.get("/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> PaymentStatusResponse:
    """Get the authenticated user's payment status."""
    payment = await PaymentRepository(db).get_by_id(payment_id)
    if payment is None or payment.user_uuid != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    return PaymentStatusResponse(
        payment_id=payment.id,
        status=PaymentStatus(payment.status),
        provider=PaymentProvider(payment.provider),
        external_id=payment.external_id,
        amount=float(payment.amount),
        currency=payment.currency,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


# ── Backward Compatibility Aliases ───────────────────────────────────────────


@router.post(
    "/create",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def create_payment_alias(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_CREATE)),
) -> InvoiceResponse:
    """Create a payment (POST /create alias for mobile compatibility)."""
    return await create_crypto_invoice(request, db, crypto_client, _)


@router.get(
    "/{invoice_id}/status",
    response_model=InvoiceResponse,
    deprecated=True,
)
async def get_payment_status_alias(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> InvoiceResponse:
    """Get payment status (GET /:id/status alias for mobile compatibility)."""
    return await get_crypto_invoice(invoice_id, db, crypto_client, _)
