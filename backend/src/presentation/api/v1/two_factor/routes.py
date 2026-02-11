"""Two-factor authentication routes with security improvements (CRIT-3).

Security improvements:
- Password re-authentication required for setup and disable
- TOTP secret stored only after successful verification
- Disable requires both password AND current TOTP code
- Rate limiting on verification attempts
"""

import logging
import secrets

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.pending_totp_service import PendingTOTPService
from src.application.services.reauth_service import ReauthenticationRequired, ReauthService
from src.application.use_cases.auth.two_factor import TwoFactorUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.monitoring.instrumentation.routes import track_2fa_operation
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.totp.totp_service import TOTPService
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service

from .schemas import (
    ReauthRequest,
    ReauthResponse,
    TwoFactorDisableRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorValidateResponse,
    TwoFactorVerifyRequest,
    VerifyCodeRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/2fa", tags=["two-factor"])


# Rate limiting constants for 2FA verification
VERIFY_RATE_LIMIT_KEY = "2fa_verify_attempts:"
VERIFY_MAX_ATTEMPTS = 5
VERIFY_WINDOW_SECONDS = 900  # 15 minutes


async def _check_verify_rate_limit(user_id: str, redis_client: redis.Redis) -> None:
    """Check and increment verification attempt rate limit."""
    key = f"{VERIFY_RATE_LIMIT_KEY}{user_id}"
    attempts = await redis_client.get(key)
    attempts = int(attempts) if attempts else 0

    if attempts >= VERIFY_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification attempts. Try again in {VERIFY_WINDOW_SECONDS // 60} minutes.",
        )

    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, VERIFY_WINDOW_SECONDS)
    await pipe.execute()


async def _reset_verify_rate_limit(user_id: str, redis_client: redis.Redis) -> None:
    """Reset verification attempt counter on success."""
    key = f"{VERIFY_RATE_LIMIT_KEY}{user_id}"
    await redis_client.delete(key)


@router.post(
    "/reauth",
    response_model=ReauthResponse,
    responses={401: {"description": "Invalid password"}},
)
async def reauthenticate(
    body: ReauthRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReauthResponse:
    """Re-authenticate with password for sensitive 2FA operations.

    Required before:
    - Setting up 2FA
    - Disabling 2FA

    Valid for 5 minutes.
    """
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password authentication not available for this account.",
        )

    reauth_service = ReauthService(redis_client, auth_service)
    if not await reauth_service.verify_password(
        user_id=str(user.id),
        password=body.password.get_secret_value(),
        password_hash=user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    return ReauthResponse(valid_for_minutes=5)


@router.post(
    "/setup",
    response_model=TwoFactorSetupResponse,
    responses={
        400: {"description": "2FA already enabled"},
        401: {"description": "Re-authentication required"},
    },
)
async def setup_2fa(
    user: AdminUserModel = Depends(get_current_active_user),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> TwoFactorSetupResponse:
    """Begin 2FA setup process.

    Requires recent password re-authentication (call /2fa/reauth first).

    Returns a TOTP secret and QR URI. The secret is NOT stored in the database
    until verified with /2fa/verify.
    """
    # Check re-authentication
    reauth_service = ReauthService(redis_client, auth_service)
    try:
        await reauth_service.require_reauth(str(user.id))
    except ReauthenticationRequired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password re-authentication required. Call POST /2fa/reauth first.",
        )

    # Check if 2FA already enabled
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled. Disable it first to set up a new secret.",
        )

    # Generate pending secret (stored in Redis, not DB)
    pending_service = PendingTOTPService(redis_client)
    result = await pending_service.generate_pending_secret(
        user_id=str(user.id),
        account_name=user.email or user.login,
    )

    logger.info(
        "2FA setup initiated",
        extra={"user_id": str(user.id)},
    )

    track_2fa_operation(operation="setup", success=True)
    return TwoFactorSetupResponse(
        secret=result["secret"],
        qr_uri=result["qr_uri"],
    )


@router.post(
    "/verify",
    response_model=TwoFactorStatusResponse,
    responses={
        400: {"description": "Invalid verification code or no pending setup"},
        429: {"description": "Too many verification attempts"},
    },
)
async def verify_2fa(
    body: TwoFactorVerifyRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> TwoFactorStatusResponse:
    """Verify TOTP code and enable 2FA.

    This persists the TOTP secret to the database after successful verification.
    """
    # Rate limit verification attempts
    await _check_verify_rate_limit(str(user.id), redis_client)

    # Verify code against pending secret
    pending_service = PendingTOTPService(redis_client)
    secret = await pending_service.verify_and_consume(str(user.id), body.code)

    if not secret:
        track_2fa_operation(operation="verify", success=False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or no pending 2FA setup.",
        )

    # Persist to database
    repo = AdminUserRepository(db)
    user.totp_secret = secret
    user.totp_enabled = True
    await repo.update(user)

    # Reset rate limit on success
    await _reset_verify_rate_limit(str(user.id), redis_client)

    logger.info(
        "2FA enabled",
        extra={"user_id": str(user.id)},
    )

    track_2fa_operation(operation="enable", success=True)
    return TwoFactorStatusResponse(status="enabled")


@router.post(
    "/validate",
    response_model=TwoFactorValidateResponse,
    responses={
        400: {"description": "2FA not enabled"},
        429: {"description": "Too many verification attempts"},
    },
)
async def validate_2fa(
    body: VerifyCodeRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> TwoFactorValidateResponse:
    """Validate a 2FA code without changing state.

    Rate limited to prevent brute force attacks.
    """
    # Rate limit verification attempts
    await _check_verify_rate_limit(str(user.id), redis_client)

    uc = TwoFactorUseCase(db)
    valid = await uc.verify_code(user.id, body.code)

    if valid:
        await _reset_verify_rate_limit(str(user.id), redis_client)

    track_2fa_operation(operation="validate", success=valid)
    return TwoFactorValidateResponse(valid=valid)


@router.delete(
    "/disable",
    response_model=TwoFactorStatusResponse,
    responses={
        400: {"description": "2FA not enabled"},
        401: {"description": "Invalid password or TOTP code"},
    },
)
async def disable_2fa(
    body: TwoFactorDisableRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> TwoFactorStatusResponse:
    """Disable two-factor authentication.

    Requires:
    1. Current password
    2. Current TOTP code

    Returns one-time recovery codes (for emergency access if needed later).
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled.",
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password authentication not available for this account.",
        )

    # Verify password
    if not auth_service.verify_password(body.password.get_secret_value(), user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    # Verify TOTP code
    totp_service = TOTPService()
    if not user.totp_secret or not totp_service.verify_code(user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code.",
        )

    # Generate recovery codes before disabling
    recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]

    # Disable 2FA
    repo = AdminUserRepository(db)
    user.totp_enabled = False
    user.totp_secret = None
    await repo.update(user)

    logger.info(
        "2FA disabled",
        extra={"user_id": str(user.id)},
    )

    track_2fa_operation(operation="disable", success=True)
    return TwoFactorStatusResponse(status="disabled", recovery_codes=recovery_codes)


@router.get(
    "/status",
    response_model=TwoFactorStatusResponse,
)
async def get_2fa_status(
    user: AdminUserModel = Depends(get_current_active_user),
) -> TwoFactorStatusResponse:
    """Get current 2FA status for the user."""
    return TwoFactorStatusResponse(status="enabled" if user.totp_enabled else "disabled")


# ── Backward Compatibility Aliases ───────────────────────────────────────────


@router.post(
    "/disable",
    response_model=TwoFactorStatusResponse,
    responses={
        400: {"description": "2FA not enabled"},
        401: {"description": "Invalid password or TOTP code"},
    },
    deprecated=True,
)
async def disable_2fa_post_alias(
    body: TwoFactorDisableRequest,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> TwoFactorStatusResponse:
    """Disable 2FA (POST alias for mobile compatibility).

    **DEPRECATED**: Use DELETE /2fa/disable instead.

    This is an alias route for backward compatibility with mobile clients
    that expect POST method. New implementations should use DELETE.
    """
    return await disable_2fa(body, user, db, redis_client, auth_service)
