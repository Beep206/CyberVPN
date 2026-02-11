"""Security management endpoints for anti-phishing codes.

Provides:
- ``POST   /api/v1/security/antiphishing`` -- set or update anti-phishing code
- ``GET    /api/v1/security/antiphishing`` -- get current anti-phishing code
- ``DELETE /api/v1/security/antiphishing`` -- remove anti-phishing code

All endpoints require authentication.
"""

import logging

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.anti_phishing import AntiPhishingUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

from .schemas import (
    AntiPhishingCodeResponse,
    DeleteAntiPhishingCodeResponse,
    SetAntiPhishingCodeRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


@router.post(
    "/antiphishing",
    response_model=AntiPhishingCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or update anti-phishing code",
    description="Set or update the authenticated user's anti-phishing code for email security.",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded (10 requests per hour)"},
    },
)
async def set_antiphishing_code(
    request: SetAntiPhishingCodeRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> AntiPhishingCodeResponse:
    """Set or update the user's anti-phishing code.

    The code will be displayed in emails from the platform to help users
    verify email authenticity and prevent phishing attacks.

    Rate limited to 10 requests per hour per user.
    """
    # Rate limiting: 10 requests per hour per user
    rate_limit_key = f"antiphishing_set:{current_user.id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 10

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    user_repo = AdminUserRepository(db)
    use_case = AntiPhishingUseCase(repo=user_repo)

    try:
        await use_case.set_code(user_id=current_user.id, code=request.code)
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

    logger.info(
        "Anti-phishing code set",
        extra={"user_id": str(current_user.id)},
    )

    return AntiPhishingCodeResponse(code=request.code)


@router.get(
    "/antiphishing",
    response_model=AntiPhishingCodeResponse,
    summary="Get current anti-phishing code",
    description="Retrieve the authenticated user's current anti-phishing code.",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_antiphishing_code(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AntiPhishingCodeResponse:
    """Get the user's current anti-phishing code.

    Returns null if no code has been set.
    """
    user_repo = AdminUserRepository(db)
    use_case = AntiPhishingUseCase(repo=user_repo)

    code = await use_case.get_code(user_id=current_user.id)

    logger.info(
        "Anti-phishing code retrieved",
        extra={"user_id": str(current_user.id), "code_set": code is not None},
    )

    return AntiPhishingCodeResponse(code=code)


@router.delete(
    "/antiphishing",
    response_model=DeleteAntiPhishingCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete anti-phishing code",
    description="Remove the authenticated user's anti-phishing code.",
    responses={
        401: {"description": "Not authenticated"},
        429: {"description": "Rate limit exceeded (5 requests per hour)"},
    },
)
async def delete_antiphishing_code(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> DeleteAntiPhishingCodeResponse:
    """Delete the user's anti-phishing code.

    After deletion, emails will no longer include the anti-phishing code.

    Rate limited to 5 requests per hour per user.
    """
    # Rate limiting: 5 requests per hour per user
    rate_limit_key = f"antiphishing_delete:{current_user.id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 5

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    user_repo = AdminUserRepository(db)
    use_case = AntiPhishingUseCase(repo=user_repo)

    await use_case.remove_code(user_id=current_user.id)

    # Increment rate limit counter
    pipe = redis_client.pipeline()
    await pipe.incr(rate_limit_key)
    await pipe.expire(rate_limit_key, rate_limit_window)
    await pipe.execute()

    logger.info(
        "Anti-phishing code deleted",
        extra={"user_id": str(current_user.id)},
    )

    return DeleteAntiPhishingCodeResponse()
