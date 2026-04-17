from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.cache_service import CacheService
from src.application.use_cases.payments.checkout import CheckoutAddonInput
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.application.use_cases.subscriptions import (
    CancelSubscriptionUseCase,
    GenerateConfigUseCase,
    GetActiveSubscriptionUseCase,
    GetCurrentEntitlementsUseCase,
    PurchaseAddonsUseCase,
    UpgradeSubscriptionUseCase,
)
from src.domain.enums import AdminRole
from src.domain.exceptions import InsufficientWalletBalanceError, WalletNotFoundError
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.monitoring.instrumentation.routes import track_subscription_activation
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import (
    RemnawaveSubscriptionConfigResponse,
    RemnawaveSubscriptionResponse,
    StatusMessageResponse,
)
from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient, RemnawaveSubscriptionClient
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.payments.schemas import (
    CheckoutAddonResponse,
    CheckoutCommitResponse,
    CheckoutQuoteResponse,
    EntitlementsSnapshotResponse,
    InvoiceResponse,
)
from src.presentation.dependencies import get_current_active_user, get_remnawave_client, require_role
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_crypto_client

from .schemas import (
    ActiveSubscriptionResponse,
    CancelSubscriptionResponse,
    CreateSubscriptionTemplateRequest,
    CurrentEntitlementsResponse,
    PurchaseSubscriptionAddonsRequest,
    SubscriptionTemplateListResponse,
    UpdateSubscriptionTemplateRequest,
    UpgradeSubscriptionRequest,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


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
    db: AsyncSession = Depends(get_db),
) -> CurrentEntitlementsResponse:
    use_case = GetCurrentEntitlementsUseCase(db)
    snapshot = await use_case.execute(user_id)
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
) -> CheckoutCommitResponse:
    use_case = UpgradeSubscriptionUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            target_plan_id=body.target_plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
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
        )
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
        )
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
    templates = await client.get_collection_validated(
        "/subscription-templates",
        "templates",
        RemnawaveSubscriptionResponse,
    )
    return SubscriptionTemplateListResponse(total=len(templates), templates=templates)


@router.post("/", response_model=RemnawaveSubscriptionResponse)
async def create_subscription_template(
    template_data: CreateSubscriptionTemplateRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new subscription template (admin only)"""
    return await client.post_validated(
        "/subscription-templates",
        RemnawaveSubscriptionResponse,
        json=template_data.model_dump(),
    )


@router.get("/config/{user_uuid}", response_model=RemnawaveSubscriptionConfigResponse)
async def generate_config(
    user_uuid: str,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Generate VPN configuration for a user"""
    use_case = GenerateConfigUseCase(client)
    return await use_case.execute(user_uuid)


@router.get(
    "/active",
    response_model=ActiveSubscriptionResponse,
    summary="Get active subscription",
    description="Retrieve the authenticated user's current subscription status.",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_active_subscription(
    current_user: AdminUserModel = Depends(get_current_active_user),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client: redis.Redis = Depends(get_redis),
) -> ActiveSubscriptionResponse:
    """Get the user's active subscription.

    Returns subscription status, plan details, expiration, and traffic usage.
    Data is cached for 5 minutes for performance.
    """
    # Build subscription client with caching
    cache_service = CacheService(redis_client)
    base_client = RemnawaveSubscriptionClient(remnawave_client)
    cached_client = CachedSubscriptionClient(base_client, cache_service)

    # Execute use case
    use_case = GetActiveSubscriptionUseCase(cached_client)
    subscription = await use_case.execute(current_user.id)

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
    current_user: AdminUserModel = Depends(get_current_active_user),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client: redis.Redis = Depends(get_redis),
) -> CancelSubscriptionResponse:
    """Cancel the user's active subscription.

    Sets the subscription revocation timestamp and invalidates cached data.
    Does not throw an error if the subscription is already canceled.

    Rate limited to 3 requests per hour per user.
    """
    # Rate limiting: 3 requests per hour per user
    rate_limit_key = f"subscription_cancel:{current_user.id}"
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
        await use_case.execute(current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # Increment rate limit counter
    pipe = redis_client.pipeline()
    await pipe.incr(rate_limit_key)
    await pipe.expire(rate_limit_key, rate_limit_window)
    await pipe.execute()

    return CancelSubscriptionResponse(canceled_at=datetime.now(UTC))


@router.get("/{uuid}", response_model=RemnawaveSubscriptionResponse)
async def get_subscription_template(
    uuid: str,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Get subscription template details"""
    return await client.get_validated(f"/subscription-templates/{uuid}", RemnawaveSubscriptionResponse)


@router.put("/{uuid}", response_model=RemnawaveSubscriptionResponse)
async def update_subscription_template(
    uuid: str,
    template_data: UpdateSubscriptionTemplateRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update subscription template (admin only)"""
    return await client.put_validated(
        f"/subscription-templates/{uuid}",
        RemnawaveSubscriptionResponse,
        json=template_data.model_dump(exclude_none=True),
    )


@router.delete("/{uuid}", response_model=StatusMessageResponse)
async def delete_subscription_template(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Delete subscription template (admin only)"""
    return await client.delete_validated(f"/subscription-templates/{uuid}", StatusMessageResponse)
