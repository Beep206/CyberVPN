"""OAuth routes with proper validation (CRIT-2).

Security improvements:
- Telegram: HMAC-SHA256 signature validation, auth_date check
- GitHub: Code-to-token exchange via GitHub API
- State parameter for CSRF protection (HIGH-5)
- Provider enum validation (HIGH-7)
"""

import logging

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.oauth_state_service import OAuthStateService
from src.application.use_cases.auth.account_linking import AccountLinkingUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.oauth.github import GitHubOAuthProvider
from src.infrastructure.oauth.telegram import TelegramOAuthProvider
from src.presentation.api.v1.oauth.schemas import (
    GitHubCallbackRequest,
    OAuthAuthorizeResponse,
    OAuthLinkResponse,
    OAuthProvider,
    TelegramCallbackRequest,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/telegram/authorize", response_model=OAuthAuthorizeResponse)
async def telegram_authorize(
    redirect_uri: str = Query(..., description="Redirect URI after authentication"),
    request: Request = None,
    redis_client: redis.Redis = Depends(get_redis),
    user: AdminUserModel = Depends(get_current_active_user),
) -> OAuthAuthorizeResponse:
    """Get Telegram OAuth authorization URL with CSRF state token.

    The state token must be included in the callback request.
    """
    state_service = OAuthStateService(redis_client)
    state = await state_service.generate(
        provider="telegram",
        user_id=str(user.id),
        ip_address=_get_client_ip(request) if request else None,
    )

    provider = TelegramOAuthProvider()
    authorize_url = provider.authorize_url(redirect_uri)

    # Append state to the URL
    if "?" in authorize_url:
        authorize_url += f"&state={state}"
    else:
        authorize_url += f"?state={state}"

    return OAuthAuthorizeResponse(authorize_url=authorize_url, state=state)


@router.get("/github/authorize", response_model=OAuthAuthorizeResponse)
async def github_authorize(
    redirect_uri: str = Query(..., description="Redirect URI after authentication"),
    request: Request = None,
    redis_client: redis.Redis = Depends(get_redis),
    user: AdminUserModel = Depends(get_current_active_user),
) -> OAuthAuthorizeResponse:
    """Get GitHub OAuth authorization URL with CSRF state token.

    The state token must be included in the callback request.
    """
    state_service = OAuthStateService(redis_client)
    state = await state_service.generate(
        provider="github",
        user_id=str(user.id),
        ip_address=_get_client_ip(request) if request else None,
    )

    provider = GitHubOAuthProvider()
    authorize_url = provider.authorize_url(redirect_uri, state=state)

    return OAuthAuthorizeResponse(authorize_url=authorize_url, state=state)


@router.post("/telegram/callback", response_model=OAuthLinkResponse)
async def telegram_callback(
    callback_data: TelegramCallbackRequest,
    request: Request,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthLinkResponse:
    """Process Telegram OAuth callback and link account.

    Validates:
    1. CSRF state token
    2. HMAC-SHA256 signature using bot token
    3. auth_date is within acceptable range (24 hours)
    """
    # Validate CSRF state token
    state_service = OAuthStateService(redis_client)
    if not await state_service.validate_and_consume(
        state=callback_data.state,
        provider="telegram",
        user_id=str(user.id),
        ip_address=_get_client_ip(request),
    ):
        logger.warning(
            "Telegram OAuth callback with invalid state",
            extra={"user_id": str(user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state.",
        )

    # Validate Telegram auth data
    provider = TelegramOAuthProvider()
    auth_data = {
        "id": callback_data.id,
        "first_name": callback_data.first_name,
        "auth_date": callback_data.auth_date,
        "hash": callback_data.hash,
    }
    if callback_data.last_name:
        auth_data["last_name"] = callback_data.last_name
    if callback_data.username:
        auth_data["username"] = callback_data.username
    if callback_data.photo_url:
        auth_data["photo_url"] = callback_data.photo_url

    user_info = await provider.exchange_code(auth_data)

    if not user_info:
        logger.warning(
            "Telegram OAuth validation failed",
            extra={"user_id": str(user.id)},
        )
        # Generic error to prevent information leakage
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth authentication failed.",
        )

    # Link the account
    uc = AccountLinkingUseCase(db)
    await uc.link_account(
        user_id=user.id,
        provider="telegram",
        provider_user_id=str(user_info["id"]),
    )

    logger.info(
        "Telegram account linked",
        extra={"user_id": str(user.id), "telegram_id": user_info["id"]},
    )

    return OAuthLinkResponse(
        status="linked",
        provider="telegram",
        provider_user_id=str(user_info["id"]),
    )


@router.post("/github/callback", response_model=OAuthLinkResponse)
async def github_callback(
    callback_data: GitHubCallbackRequest,
    request: Request,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthLinkResponse:
    """Process GitHub OAuth callback and link account.

    Validates:
    1. CSRF state token
    2. Exchanges code for access token via GitHub API
    3. Fetches user info from GitHub API
    """
    # Validate CSRF state token
    state_service = OAuthStateService(redis_client)
    if not await state_service.validate_and_consume(
        state=callback_data.state,
        provider="github",
        user_id=str(user.id),
        ip_address=_get_client_ip(request),
    ):
        logger.warning(
            "GitHub OAuth callback with invalid state",
            extra={"user_id": str(user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state.",
        )

    # Exchange code for user info
    provider = GitHubOAuthProvider()
    user_info = await provider.exchange_code(
        code=callback_data.code,
        redirect_uri=callback_data.redirect_uri,
    )

    if not user_info:
        logger.warning(
            "GitHub OAuth code exchange failed",
            extra={"user_id": str(user.id)},
        )
        # Generic error to prevent information leakage
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth authentication failed.",
        )

    # Link the account
    uc = AccountLinkingUseCase(db)
    await uc.link_account(
        user_id=user.id,
        provider="github",
        provider_user_id=str(user_info["id"]),
    )

    logger.info(
        "GitHub account linked",
        extra={"user_id": str(user.id), "github_id": user_info["id"]},
    )

    return OAuthLinkResponse(
        status="linked",
        provider="github",
        provider_user_id=str(user_info["id"]),
    )


@router.delete("/{provider}", response_model=OAuthLinkResponse)
async def unlink_provider(
    provider: OAuthProvider,  # HIGH-7: Enum validation
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OAuthLinkResponse:
    """Unlink a social account from the current user.

    Provider must be one of: telegram, github
    """
    uc = AccountLinkingUseCase(db)
    await uc.unlink_account(user.id, provider.value)

    logger.info(
        "OAuth provider unlinked",
        extra={"user_id": str(user.id), "provider": provider.value},
    )

    return OAuthLinkResponse(status="unlinked", provider=provider.value)
