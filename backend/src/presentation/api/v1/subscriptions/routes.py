import hmac
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.cache_service import CacheService
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.payments.checkout import CheckoutAddonInput
from src.application.use_cases.payments.commit_checkout import (
    CheckoutIdempotencyConflictError,
    CommitCheckoutUseCase,
)
from src.application.use_cases.subscriptions import (
    CancelSubscriptionUseCase,
    GenerateConfigUseCase,
    GetActiveSubscriptionUseCase,
    GetCurrentEntitlementsUseCase,
    PurchaseAddonsUseCase,
    Stage1ProvisioningRetryService,
    Stage1ProvisioningRetryWorker,
    Stage1ProvisioningRetryWorkerResult,
    UpgradeSubscriptionUseCase,
)
from src.application.use_cases.subscriptions.cancel_subscription import (
    SubscriptionCancellationIdentityConflictError,
    SubscriptionCancellationNotFoundError,
)
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.domain.exceptions import InsufficientWalletBalanceError, WalletNotFoundError
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.stage1_provisioning_retry_repo import Stage1ProvisioningRetryJobRepository
from src.infrastructure.monitoring.instrumentation.routes import track_subscription_activation
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionConfigResponse
from src.infrastructure.remnawave.control_plane_gateways import (
    RemnawaveSubscriptionTemplateControlPlaneGateway,
    RemnawaveSubscriptionTemplateCreateSafetyDisabled,
    RemnawaveSubscriptionTemplateMutationAcceptedPending,
)
from src.infrastructure.remnawave.stage1_paid_gateway import RemnawaveStage1PaidProvisioningGateway
from src.infrastructure.remnawave.stage1_trial_gateway import RemnawaveStage1TrialProvisioningGateway
from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient, RemnawaveSubscriptionClient
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending, RemnawaveUserGateway
from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonResponse,
    CheckoutCodeResolutionResponse,
    CheckoutCommitResponse,
    CheckoutDiscountResponse,
    CheckoutQuoteResponse,
    EntitlementsSnapshotResponse,
    InvoiceResponse,
)
from src.presentation.api.v1.remnawave_degraded import optional_remnawave_read
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.dependencies.auth import (
    CurrentPrincipalActor,
    get_current_mobile_user_id,
    get_current_principal_actor,
)
from src.presentation.dependencies.auth_realms import get_request_auth_realm, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_crypto_client

from .credential_access import (
    read_customer_vpn_credentials_as_admin,
)
from .credential_access import (
    require_customer_principal as _require_customer_principal,
)
from .credential_access import (
    resolve_exact_mobile_user_ref as _resolve_exact_mobile_user_ref,
)
from .schemas import (
    ActiveSubscriptionResponse,
    CancelSubscriptionResponse,
    CreateSubscriptionTemplateRequest,
    CurrentEntitlementsResponse,
    PurchaseSubscriptionAddonsRequest,
    SubscriptionTemplateListResponse,
    SubscriptionTemplateResponse,
    UpdateSubscriptionTemplateRequest,
    UpgradeSubscriptionRequest,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

_CANONICAL_LOCAL_USER_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def _parse_canonical_local_user_id(raw_user_id: str) -> UUID:
    try:
        parsed = UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid customer identifier"
        ) from exc
    if str(parsed) != raw_user_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid customer identifier")
    return parsed


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _is_valid_backend_internal_secret(secret: str | None) -> bool:
    configured = settings.backend_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_backend_internal_secret(secret: str | None) -> None:
    if _is_valid_backend_internal_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


@router.post("/internal/provisioning-retries/run")
async def run_stage1_provisioning_retries(
    limit: int = Query(25, ge=1, le=100),
    worker_id: str = Query("task-worker", min_length=1, max_length=120),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    backend_internal_secret: str | None = Header(default=None, alias="X-Backend-Internal-Secret"),
) -> dict:
    """Run a bounded durable S1 provisioning retry pass for the task worker."""

    _require_backend_internal_secret(backend_internal_secret)
    repository = Stage1ProvisioningRetryJobRepository(db)
    if not settings.stage1_provisioning_retry_claiming_enabled:
        metrics = await repository.metrics_snapshot(now=datetime.now(UTC))
        return Stage1ProvisioningRetryWorkerResult(
            skipped=True,
            skipped_reason="claiming_disabled",
            metrics=metrics,
        ).to_safe_dict()

    user_gateway = RemnawaveUserGateway(remnawave_client)
    retry_service = Stage1ProvisioningRetryService(queue=repository)
    runner = Stage1ProvisioningRetryWorker(
        repository=repository,
        retry_service=retry_service,
        paid_gateway=RemnawaveStage1PaidProvisioningGateway(user_gateway),
        trial_gateway=RemnawaveStage1TrialProvisioningGateway(user_gateway),
    )
    run_limit = max(1, min(limit, settings.stage1_provisioning_retry_batch_limit))
    return (await runner.run_due_jobs(limit=run_limit, worker_id=worker_id)).to_safe_dict()


def _serialize_subscription_quote(result) -> CheckoutQuoteResponse:
    return CheckoutQuoteResponse(
        base_price=float(result.base_price),
        addon_amount=float(result.addon_amount),
        displayed_price=float(result.displayed_price),
        discount_amount=float(result.discount_amount),
        wallet_amount=float(result.wallet_amount),
        gateway_amount=float(result.gateway_amount),
        partner_markup=float(result.partner_markup),
        is_zero_gateway=result.is_zero_gateway,
        plan_id=result.plan_id,
        promo_code_id=result.promo_code_id,
        partner_code_id=result.partner_code_id,
        code_input=result.code_input,
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
                code=discount.code,
                amount=float(discount.amount),
                policy_version_id=discount.policy_version_id,
            )
            for discount in result.discounts
        ],
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


@router.get(
    "/current/entitlements",
    response_model=CurrentEntitlementsResponse,
    summary="Get current effective entitlements",
    description="Return the canonical pricing entitlement snapshot for the authenticated mobile user.",
)
async def get_current_entitlements(
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm=Depends(get_request_customer_realm),
    db: AsyncSession = Depends(get_db),
) -> CurrentEntitlementsResponse:
    use_case = GetCurrentEntitlementsUseCase(db)
    snapshot = await use_case.execute(user_id, auth_realm_id=current_realm.auth_realm.id)
    return CurrentEntitlementsResponse(**snapshot)


@router.post("/current/upgrade/quote", response_model=CheckoutQuoteResponse)
async def quote_subscription_upgrade(
    body: UpgradeSubscriptionRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CheckoutQuoteResponse:
    use_case = UpgradeSubscriptionUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            target_plan_id=body.target_plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
            currency=body.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    return _serialize_subscription_quote(result)


@router.post("/current/upgrade", response_model=CheckoutCommitResponse)
async def commit_subscription_upgrade(
    body: UpgradeSubscriptionRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
) -> CheckoutCommitResponse:
    use_case = UpgradeSubscriptionUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            target_plan_id=body.target_plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
            currency=body.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    quote = _serialize_subscription_quote(result)
    commit_use_case = CommitCheckoutUseCase(db, crypto_client)
    try:
        commit_result = await commit_use_case.execute(
            user_id=user_id,
            quote_result=result,
            currency=body.currency,
            channel=body.channel,
            description=f"CyberVPN upgrade to {result.plan_name or 'plan'}",
            payload=f"{user_id}:{body.target_plan_id}:upgrade",
            checkout_mode="upgrade",
            payment_plan_id=result.plan_id,
            idempotency_key=idempotency_key,
        )
    except CheckoutIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except (InsufficientWalletBalanceError, WalletNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upgrade processing failed",
        ) from None

    invoice = InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
    return CheckoutCommitResponse(
        **quote.model_dump(),
        payment_id=commit_result.payment.id,
        status=commit_result.status,
        invoice=invoice,
    )


@router.post("/current/addons/quote", response_model=CheckoutQuoteResponse)
async def quote_subscription_addons(
    body: PurchaseSubscriptionAddonsRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CheckoutQuoteResponse:
    use_case = PurchaseAddonsUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            addons=[
                CheckoutAddonInput(
                    code=addon.code,
                    qty=addon.qty,
                    location_code=addon.location_code,
                )
                for addon in body.addons
            ],
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
            currency=body.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    return _serialize_subscription_quote(result)


@router.post("/current/addons", response_model=CheckoutCommitResponse)
async def purchase_subscription_addons(
    body: PurchaseSubscriptionAddonsRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
) -> CheckoutCommitResponse:
    use_case = PurchaseAddonsUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            addons=[
                CheckoutAddonInput(
                    code=addon.code,
                    qty=addon.qty,
                    location_code=addon.location_code,
                )
                for addon in body.addons
            ],
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
            currency=body.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    quote = _serialize_subscription_quote(result)
    commit_use_case = CommitCheckoutUseCase(db, crypto_client)
    try:
        commit_result = await commit_use_case.execute(
            user_id=user_id,
            quote_result=result,
            currency=body.currency,
            channel=body.channel,
            description=f"CyberVPN add-ons for {result.plan_name or 'plan'}",
            payload=f"{user_id}:{result.plan_id}:addons",
            checkout_mode="addon_only",
            payment_plan_id=None,
            use_quote_plan_id_for_payment=False,
            subscription_days_override=result.duration_days,
            metadata_extra={"base_plan_id": str(result.plan_id) if result.plan_id else None},
            idempotency_key=idempotency_key,
        )
    except CheckoutIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except (InsufficientWalletBalanceError, WalletNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Add-on purchase processing failed",
        ) from None

    invoice = InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
    return CheckoutCommitResponse(
        **quote.model_dump(),
        payment_id=commit_result.payment.id,
        status=commit_result.status,
        invoice=invoice,
    )


@router.get("/", response_model=SubscriptionTemplateListResponse)
async def list_subscription_templates(
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """List all subscription templates (admin only)"""
    empty_templates: list[SubscriptionTemplateResponse] = []
    templates: list[SubscriptionTemplateResponse] = await optional_remnawave_read(
        route="subscriptions",
        action="list_templates",
        fetch=lambda: client.get_collection_validated(
            "/subscription-templates",
            "templates",
            SubscriptionTemplateResponse,
        ),
        fallback=empty_templates,
    )
    return SubscriptionTemplateListResponse(total=len(templates), templates=templates)


@router.post(
    "/",
    response_model=SubscriptionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Template creation is safety-disabled pending durable settlement",
        }
    },
)
async def create_subscription_template(
    template_data: CreateSubscriptionTemplateRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> SubscriptionTemplateResponse:
    """Refuse duplicate-prone create until CyberVPN owns durable settlement."""
    try:
        return await RemnawaveSubscriptionTemplateControlPlaneGateway(client).create(
            template_data.to_upstream_payload()
        )
    except RemnawaveSubscriptionTemplateCreateSafetyDisabled as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.error_code},
        ) from exc


@router.get("/config/{user_uuid}", response_model=RemnawaveSubscriptionConfigResponse)
async def generate_config(
    user_uuid: Annotated[
        str,
        Path(
            min_length=36,
            max_length=36,
            pattern=_CANONICAL_LOCAL_USER_UUID_PATTERN,
            description="Canonical CyberVPN MobileUser UUID; never a Remnawave identifier.",
        ),
    ],
    request: Request,
    current_actor: CurrentPrincipalActor = Depends(get_current_principal_actor),
    current_realm: RealmResolution = Depends(get_request_auth_realm),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Return a customer's live VPN credential through an object-authorized path."""

    customer_id = _parse_canonical_local_user_id(user_uuid)
    if current_realm.realm_type == "customer":
        _require_customer_principal(current_actor, current_realm)
        if current_actor.principal_id != customer_id:
            # Do not turn this credential endpoint into a customer enumeration oracle.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        _customer, user_ref = await _resolve_exact_mobile_user_ref(
            db,
            customer_id=customer_id,
            expected_auth_realm_id=current_actor.auth_realm_id,
        )
        return await GenerateConfigUseCase(client).execute(user_ref)

    return await read_customer_vpn_credentials_as_admin(
        customer_id=customer_id,
        request=request,
        actor=current_actor,
        current_realm=current_realm,
        db=db,
        client=client,
        redis_client=redis_client,
    )


@router.get(
    "/active",
    response_model=ActiveSubscriptionResponse,
    summary="Get active subscription",
    description="Retrieve the authenticated user's current subscription status.",
    responses={
        401: {"description": "Not authenticated"},
        202: {"description": "Revocation accepted; authoritative state reconciliation is pending"},
    },
)
async def get_active_subscription(
    current_actor: CurrentPrincipalActor = Depends(get_current_principal_actor),
    current_realm: RealmResolution = Depends(get_request_auth_realm),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client: redis.Redis = Depends(get_redis),
) -> ActiveSubscriptionResponse:
    """Get the user's active subscription.

    Returns subscription status, plan details, expiration, and traffic usage.
    Data is cached for 5 minutes for performance.
    """
    _require_customer_principal(current_actor, current_realm)
    _customer, user_ref = await _resolve_exact_mobile_user_ref(
        db,
        customer_id=current_actor.principal_id,
        expected_auth_realm_id=current_actor.auth_realm_id,
    )

    # Build subscription client with caching
    cache_service = CacheService(redis_client)
    base_client = RemnawaveSubscriptionClient(remnawave_client)
    cached_client = CachedSubscriptionClient(base_client, cache_service)

    # Execute use case
    use_case = GetActiveSubscriptionUseCase(cached_client)
    subscription = await use_case.execute(user_ref)

    # Track subscription activation metric
    if subscription.status == "active" and subscription.plan_name:
        track_subscription_activation(plan_type=subscription.plan_name)

    return ActiveSubscriptionResponse(
        status=subscription.status,
        plan_name=subscription.plan_name,
        expires_at=subscription.expires_at,
        traffic_limit_bytes=subscription.traffic_limit_bytes,
        used_traffic_bytes=subscription.used_traffic_bytes,
        auto_renew=subscription.auto_renew,
    )


@router.post(
    "/cancel",
    response_model=CancelSubscriptionResponse,
    summary="Cancel subscription",
    description="Cancel the authenticated user's active subscription.",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found in VPN backend"},
        429: {"description": "Rate limit exceeded (3 requests per hour)"},
    },
)
async def cancel_subscription(
    current_actor: CurrentPrincipalActor = Depends(get_current_principal_actor),
    current_realm: RealmResolution = Depends(get_request_auth_realm),
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client: redis.Redis = Depends(get_redis),
) -> CancelSubscriptionResponse | Response:
    """Cancel the user's active subscription.

    Sets the subscription revocation timestamp and invalidates cached data.
    Does not throw an error if the subscription is already canceled.

    Rate limited to 3 requests per hour per user.
    """
    _require_customer_principal(current_actor, current_realm)
    _customer, user_ref = await _resolve_exact_mobile_user_ref(
        db,
        customer_id=current_actor.principal_id,
        expected_auth_realm_id=current_actor.auth_realm_id,
    )

    # Rate limiting is scoped to the immutable local customer id, not an
    # attacker-controlled upstream identifier.
    rate_limit_key = f"subscription_cancel:{current_actor.principal_id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 3

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    # Build dependencies
    cache_service = CacheService(redis_client)
    user_gateway = RemnawaveUserGateway(remnawave_client)
    base_client = RemnawaveSubscriptionClient(remnawave_client)
    cached_client = CachedSubscriptionClient(base_client, cache_service)

    # Execute use case
    use_case = CancelSubscriptionUseCase(user_gateway, cached_client)

    try:
        canceled_at = await use_case.execute(user_ref)
    except SubscriptionCancellationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SubscriptionCancellationIdentityConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RemnawaveMutationAcceptedPending:
        return Response(status_code=status.HTTP_202_ACCEPTED, headers={"Retry-After": "30"})

    # Increment rate limit counter
    pipe = redis_client.pipeline()
    pipe.incr(rate_limit_key)
    pipe.expire(rate_limit_key, rate_limit_window)
    await pipe.execute()

    return CancelSubscriptionResponse(canceled_at=canceled_at)


@router.get("/{uuid}", response_model=SubscriptionTemplateResponse)
async def get_subscription_template(
    uuid: UUID,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Get subscription template details"""
    return await client.get_validated(f"/subscription-templates/{uuid}", SubscriptionTemplateResponse)


@router.put(
    "/{uuid}",
    response_model=SubscriptionTemplateResponse,
    responses={
        status.HTTP_202_ACCEPTED: {
            "description": "Remnawave accepted the template update without a response body.",
        }
    },
)
async def update_subscription_template(
    uuid: UUID,
    template_data: UpdateSubscriptionTemplateRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> SubscriptionTemplateResponse | Response:
    """Update subscription template (admin only)"""
    try:
        result = await RemnawaveSubscriptionTemplateControlPlaneGateway(client).update(
            uuid,
            template_data.to_upstream_payload(),
        )
    except RemnawaveSubscriptionTemplateMutationAcceptedPending:
        return Response(status_code=status.HTTP_202_ACCEPTED, headers={"Retry-After": "30"})
    return SubscriptionTemplateResponse.model_validate(result.model_dump(by_alias=True, mode="json"))


@router.delete(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_subscription_template(
    uuid: UUID,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Response:
    """Delete subscription template (admin only)"""
    await client.delete_validated(f"/subscription-templates/{uuid}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
