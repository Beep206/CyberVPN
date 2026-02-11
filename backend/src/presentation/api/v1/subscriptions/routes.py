from datetime import UTC, datetime

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status

from src.application.services.cache_service import CacheService
from src.application.use_cases.subscriptions import CancelSubscriptionUseCase, GetActiveSubscriptionUseCase
from src.domain.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.monitoring.instrumentation.routes import track_subscription_activation
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient, RemnawaveSubscriptionClient
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies import get_current_active_user, get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import (
    RemnawaveSubscriptionConfigResponse,
    RemnawaveSubscriptionResponse,
    StatusMessageResponse,
)

from .schemas import (
    ActiveSubscriptionResponse,
    CancelSubscriptionResponse,
    CreateSubscriptionTemplateRequest,
    UpdateSubscriptionTemplateRequest,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=list[RemnawaveSubscriptionResponse])
async def list_subscription_templates(
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """List all subscription templates (admin only)"""
    return await client.get("/subscriptions")


@router.post("/", response_model=RemnawaveSubscriptionResponse)
async def create_subscription_template(
    template_data: CreateSubscriptionTemplateRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new subscription template (admin only)"""
    return await client.post("/subscriptions", json=template_data.model_dump())


@router.get("/{uuid}", response_model=RemnawaveSubscriptionResponse)
async def get_subscription_template(
    uuid: str,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Get subscription template details"""
    return await client.get(f"/subscriptions/{uuid}")


@router.put("/{uuid}", response_model=RemnawaveSubscriptionResponse)
async def update_subscription_template(
    uuid: str,
    template_data: UpdateSubscriptionTemplateRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Update subscription template (admin only)"""
    return await client.put(f"/subscriptions/{uuid}", json=template_data.model_dump(exclude_none=True))


@router.delete("/{uuid}", response_model=StatusMessageResponse)
async def delete_subscription_template(
    uuid: str,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Delete subscription template (admin only)"""
    return await client.delete(f"/subscriptions/{uuid}")


@router.get("/config/{user_uuid}", response_model=RemnawaveSubscriptionConfigResponse)
async def generate_config(
    user_uuid: str,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Generate VPN configuration for a user"""
    return await client.get(f"/subscriptions/config/{user_uuid}")


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
