import logging
from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveGiftProvisioningAttemptService,
    remnawave_create_request_hash,
    remnawave_customer_create_key,
)
from src.application.services.remnawave_identity_access import (
    persist_runtime_mapped_mobile_identity,
    resolve_exact_mapped_mobile_user_ref,
)
from src.application.services.stage1_growth_policy import (
    Stage1GrowthPolicyError,
    assert_stage1_gift_codes_enabled,
)
from src.application.use_cases.gifts import (
    CommitGiftPurchaseUseCase,
    ListGiftCodesUseCase,
    QuoteGiftPurchaseUseCase,
    RedeemGiftCodeUseCase,
)
from src.application.use_cases.gifts.provisioning import (
    GiftProvisioningGateway,
    GiftProvisioningService,
    build_gift_provisioning_request,
)
from src.application.use_cases.service_access.service_identities import (
    BindProvisionedRemnawaveServiceIdentityUseCase,
)
from src.config.settings import settings
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.remnawave.client import RemnawaveClient, get_remnawave_client
from src.infrastructure.remnawave.stage1_gift_gateway import RemnawaveGiftProvisioningGateway
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
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
logger = logging.getLogger(__name__)


def _gift_provisioning_attempts(
    db: AsyncSession,
    *,
    is_create: bool,
) -> RemnawaveGiftProvisioningAttemptService:
    return RemnawaveGiftProvisioningAttemptService(
        db,
        customer_resource_type="remnawave_user_create" if is_create else "remnawave_user_update",
    )


async def get_gift_provisioning_gateway(
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> GiftProvisioningGateway | None:
    if not settings.stage1_paid_provisioning_enabled:
        return None
    return RemnawaveGiftProvisioningGateway(RemnawaveUserGateway(remnawave_client))


def require_gift_provisioning_gateway(
    provisioning_gateway: GiftProvisioningGateway | None,
) -> GiftProvisioningGateway:
    """Fail before a one-use gift can be consumed without data-plane access."""

    if provisioning_gateway is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gift VPN provisioning is unavailable",
        )
    return provisioning_gateway


async def provision_redeemed_gift_access(
    *,
    db: AsyncSession,
    user_id: UUID,
    result,
    provisioning_gateway: GiftProvisioningGateway | None,
) -> None:
    provisioning_gateway = require_gift_provisioning_gateway(provisioning_gateway)

    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    grant = await db.get(EntitlementGrantModel, result.entitlement_grant_id)
    if grant is None or grant.expires_at is None:
        raise RuntimeError("Gift entitlement grant is incomplete before provisioning")
    if grant.customer_account_id != user_id or grant.auth_realm_id != user.auth_realm_id:
        raise RuntimeError("Gift entitlement grant does not belong to the redeeming customer")

    identity_binding = BindProvisionedRemnawaveServiceIdentityUseCase(db)
    await identity_binding.validate_target(
        service_identity_id=grant.service_identity_id,
        customer_account_id=user_id,
        auth_realm_id=grant.auth_realm_id,
    )

    snapshot = dict(result.entitlement_snapshot or {})
    effective_entitlements = dict(snapshot.get("effective_entitlements") or {})
    device_limit = effective_entitlements.get("device_limit")
    if isinstance(device_limit, bool) or not isinstance(device_limit, int) or device_limit <= 0:
        raise RuntimeError("Gift entitlement snapshot has no valid device limit")
    existing_ref = await resolve_exact_mapped_mobile_user_ref(db, user)
    request = build_gift_provisioning_request(
        customer_account_id=user_id,
        gift_code_id=result.growth_code.id,
        email=user.email,
        username=user.username,
        telegram_id=user.telegram_id,
        plan_code=result.policy.plan_family or snapshot.get("plan_code"),
        access_expires_at=grant.expires_at,
        traffic_limit_bytes=effective_entitlements.get("traffic_limit_bytes"),
        device_limit=device_limit,
        existing_remnawave_uuid=(
            str(existing_ref.legacy_uuid) if existing_ref is not None and existing_ref.legacy_uuid is not None else None
        ),
        existing_remnawave_user_id=(existing_ref.require_numeric_id() if existing_ref is not None else None),
    )

    is_create = existing_ref is None
    attempt_scope = "remnawave-customer:create" if is_create else "remnawave-customer:update"
    attempt_key = (
        remnawave_customer_create_key(user_id)
        if is_create
        else remnawave_create_request_hash(
            {
                "operation": "gift_redemption_update",
                "customer_account_id": str(user_id),
                "gift_code_id": str(result.growth_code.id),
            }
        )
    )
    request_hash = remnawave_create_request_hash(
        {
            "customer_account_id": str(user_id),
            "gift_code_id": str(result.growth_code.id),
            "entitlement_grant_id": str(result.entitlement_grant_id),
            "access_expires_at": request.access_expires_at,
            "plan_code": request.plan_code,
            "traffic_limit_bytes": request.traffic_limit_bytes,
            "device_limit": request.device_limit,
            "provider_numeric_subject_id": request.existing_remnawave_user_id,
        }
    )
    try:
        async with AsyncSessionLocal() as marker_db:
            decision = await _gift_provisioning_attempts(marker_db, is_create=is_create).begin(
                gift_code_id=result.growth_code.id,
                customer_account_id=user_id,
                customer_scope=attempt_scope,
                customer_idempotency_key=attempt_key,
                request_hash=request_hash,
            )
    except RemnawaveCreateAttemptConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gift Remnawave mutation requires reconciliation",
        ) from exc
    if not decision.should_mutate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gift Remnawave mutation requires reconciliation",
        )

    try:
        provisioning = await GiftProvisioningService(provisioning_gateway).provision(request)
    except Exception as exc:
        async with AsyncSessionLocal() as marker_db:
            marker_attempts = _gift_provisioning_attempts(marker_db, is_create=is_create)
            marker_decision = await marker_attempts.begin(
                gift_code_id=result.growth_code.id,
                customer_account_id=user_id,
                customer_scope=attempt_scope,
                customer_idempotency_key=attempt_key,
                request_hash=request_hash,
            )
            await marker_attempts.mark_reconciliation_required(marker_decision)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gift Remnawave mutation requires reconciliation",
        ) from exc

    remnawave_user_id = provisioning.require_remnawave_user_id()
    await persist_runtime_mapped_mobile_identity(
        db,
        customer=user,
        remnawave_user_id=remnawave_user_id,
        remnawave_uuid=provisioning.remnawave_uuid,
        source="gift_redemption",
    )
    await identity_binding.execute(
        service_identity_id=grant.service_identity_id,
        customer_account_id=user_id,
        auth_realm_id=grant.auth_realm_id,
        remnawave_user_id=remnawave_user_id,
        remnawave_uuid=provisioning.remnawave_uuid,
        mapping_source="gift_redemption",
    )
    user.subscription_url = provisioning.subscription_url
    await user_repo.update(user)

    attempts = _gift_provisioning_attempts(db, is_create=is_create)
    completion_decision = await attempts.begin(
        gift_code_id=result.growth_code.id,
        customer_account_id=user_id,
        customer_scope=attempt_scope,
        customer_idempotency_key=attempt_key,
        request_hash=request_hash,
    )
    if completion_decision.should_mutate:
        raise RuntimeError("Gift Remnawave mutation marker disappeared before local commit")
    await attempts.mark_completed(
        completion_decision,
        user_ref=RemnawaveUserRef(
            id=remnawave_user_id,
            legacy_uuid=(UUID(provisioning.remnawave_uuid) if provisioning.remnawave_uuid is not None else None),
        ),
    )


def _assert_gift_public_flow_enabled() -> None:
    try:
        assert_stage1_gift_codes_enabled(enabled=settings.gift_codes_enabled)
    except Stage1GrowthPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


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
    _assert_gift_public_flow_enabled()
    use_case = QuoteGiftPurchaseUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            current_realm=current_realm,
            storefront_key=payload.storefront_key,
            host=request.headers.get("X-Forwarded-Host") or request.headers.get("Host"),
            plan_id=payload.plan_id,
            use_wallet=Decimal(str(payload.use_wallet)),
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
    _assert_gift_public_flow_enabled()
    quote_use_case = QuoteGiftPurchaseUseCase(db)
    try:
        quote_result = await quote_use_case.execute(
            user_id=user_id,
            current_realm=current_realm,
            storefront_key=payload.storefront_key,
            host=request.headers.get("X-Forwarded-Host") or request.headers.get("Host"),
            plan_id=payload.plan_id,
            use_wallet=Decimal(str(payload.use_wallet)),
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
    _assert_gift_public_flow_enabled()
    items = await ListGiftCodesUseCase(db).execute(owner_user_id=user_id)
    return [_serialize_gift_code(code, policy, issuance, redemption) for code, policy, issuance, redemption in items]


@router.post("/redeem", response_model=GiftRedeemResponse)
async def redeem_gift(
    payload: GiftRedeemRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    provisioning_gateway: GiftProvisioningGateway | None = Depends(get_gift_provisioning_gateway),
) -> GiftRedeemResponse:
    _assert_gift_public_flow_enabled()
    provisioning_gateway = require_gift_provisioning_gateway(provisioning_gateway)
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

    try:
        await provision_redeemed_gift_access(
            db=db,
            user_id=user_id,
            result=result,
            provisioning_gateway=provisioning_gateway,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "gift_vpn_provisioning_failed",
            extra={
                "user_id": str(user_id),
                "gift_code_id": str(result.growth_code.id),
                "entitlement_grant_id": str(result.entitlement_grant_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="VPN access provisioning failed",
        ) from exc

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
