from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.gifts import (
    CommitGiftPurchaseUseCase,
    ListGiftCodesUseCase,
    QuoteGiftPurchaseUseCase,
    RedeemGiftCodeUseCase,
)
from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.presentation.api.v1.payments.routes import _serialize_quote
from src.presentation.api.v1.payments.schemas import InvoiceResponse
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_crypto_client

from .schemas import (
    GiftCodeResponse,
    GiftPurchaseCommitRequest,
    GiftPurchaseCommitResponse,
    GiftPurchaseQuoteRequest,
    GiftPurchaseQuoteResponse,
    GiftRedeemRequest,
    GiftRedeemResponse,
)

router = APIRouter(prefix="/gifts", tags=["gifts"])


def _serialize_gift_code(
    code: GrowthCodeModel,
    policy: GiftCodePolicyModel | None,
    issuance: GrowthCodeIssuanceModel | None,
    redemption: GrowthCodeRedemptionModel | None,
) -> GiftCodeResponse:
    policy_snapshot = dict(policy.policy_snapshot or {}) if policy is not None else {}
    return GiftCodeResponse(
        id=code.id,
        masked_code=f"{code.code_prefix}••••",
        raw_code=issuance.raw_code_encrypted if issuance is not None else None,
        status=code.status,
        issuer_type=code.issuer_type,
        source_type=issuance.issuance_type if issuance is not None else None,
        plan_family=policy.plan_family if policy is not None else None,
        duration_days=policy.duration_days if policy is not None else None,
        recipient_hint=policy_snapshot.get("recipient_hint"),
        gift_message=policy_snapshot.get("gift_message"),
        expires_at=code.expires_at,
        created_at=code.created_at,
        redeemed_at=redemption.redeemed_at if redemption is not None else None,
        redeemed_by_user_id=redemption.redeemer_user_id if redemption is not None else None,
        source_order_id=issuance.source_order_id if issuance is not None else None,
        source_payment_id=issuance.source_payment_id if issuance is not None else None,
    )


@router.post("/purchase/quote", response_model=GiftPurchaseQuoteResponse)
async def quote_gift_purchase(
    payload: GiftPurchaseQuoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> GiftPurchaseQuoteResponse:
    use_case = QuoteGiftPurchaseUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            current_realm=current_realm,
            storefront_key=payload.storefront_key,
            host=request.headers.get("X-Forwarded-Host") or request.headers.get("Host"),
            plan_id=payload.plan_id,
            use_wallet=payload.use_wallet,
            currency=payload.currency,
            channel=payload.channel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    return GiftPurchaseQuoteResponse(quote=_serialize_quote(result.checkout_result))


@router.post("/purchase/commit", response_model=GiftPurchaseCommitResponse)
async def commit_gift_purchase(
    payload: GiftPurchaseCommitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    crypto_client=Depends(get_crypto_client),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> GiftPurchaseCommitResponse:
    quote_use_case = QuoteGiftPurchaseUseCase(db)
    try:
        quote_result = await quote_use_case.execute(
            user_id=user_id,
            current_realm=current_realm,
            storefront_key=payload.storefront_key,
            host=request.headers.get("X-Forwarded-Host") or request.headers.get("Host"),
            plan_id=payload.plan_id,
            use_wallet=payload.use_wallet,
            currency=payload.currency,
            channel=payload.channel,
        )
        commit_result = await CommitGiftPurchaseUseCase(db, crypto_client).execute(
            user_id=user_id,
            plan_id=payload.plan_id,
            quote_result=quote_result.checkout_result,
            currency=payload.currency,
            channel=payload.channel,
            recipient_hint=payload.recipient_hint,
            gift_message=payload.gift_message,
            storefront_id=quote_result.resolved_context.storefront.id,
            auth_realm_id=UUID(current_realm.realm_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    issued = commit_result.issued_gift
    return GiftPurchaseCommitResponse(
        quote=_serialize_quote(quote_result.checkout_result),
        payment_id=commit_result.commit_result.payment.id,
        status=commit_result.commit_result.status,
        invoice=(
            None
            if commit_result.commit_result.invoice is None
            else InvoiceResponse(**asdict(commit_result.commit_result.invoice))
        ),
        gift_code=(
            None
            if issued is None
            else _serialize_gift_code(
                issued.growth_code,
                issued.policy,
                issued.issuance,
                None,
            ).model_copy(update={"raw_code": issued.raw_code or issued.issuance.raw_code_encrypted})
        ),
    )


@router.get("/my", response_model=list[GiftCodeResponse])
async def list_my_gifts(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> list[GiftCodeResponse]:
    items = await ListGiftCodesUseCase(db).execute(owner_user_id=user_id)
    return [
        _serialize_gift_code(code, policy, issuance, redemption)
        for code, policy, issuance, redemption in items
    ]


@router.post("/redeem", response_model=GiftRedeemResponse)
async def redeem_gift(
    payload: GiftRedeemRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> GiftRedeemResponse:
    use_case = RedeemGiftCodeUseCase(db)
    try:
        result = await use_case.execute(
            code=payload.code,
            user_id=user_id,
            current_realm=current_realm,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from None
        if "already redeemed" in detail.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None
        if "expired" in detail.lower():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=detail) from None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from None

    issuance_items = await GrowthCodeRepository(db).list_issuances(result.growth_code.id)
    issuance = issuance_items[0] if issuance_items else None

    return GiftRedeemResponse(
        gift_code=_serialize_gift_code(
            result.growth_code,
            result.policy,
            issuance,
            result.redemption,
        ),
        entitlement_grant_id=result.entitlement_grant_id,
        entitlement_snapshot=result.entitlement_snapshot,
    )
