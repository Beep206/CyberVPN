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

from src.application.services.auth_service import AuthService
from src.application.services.oauth_state_service import OAuthStateService
from src.application.use_cases.auth.account_linking import AccountLinkingUseCase
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.oauth_account_repo import OAuthAccountRepository
from src.infrastructure.oauth.apple import AppleOAuthProvider
from src.infrastructure.oauth.discord import DiscordOAuthProvider
from src.infrastructure.oauth.github import GitHubOAuthProvider
from src.infrastructure.oauth.google import GoogleOAuthProvider
from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider
from src.infrastructure.oauth.telegram import TelegramOAuthProvider
from src.infrastructure.oauth.twitter import TwitterOAuthProvider
from src.infrastructure.remnawave.adapters import RemnawaveUserAdapter, get_remnawave_adapter
from src.presentation.api.v1.oauth.schemas import (
    GitHubCallbackRequest,
    OAuthAuthorizeResponse,
    OAuthLinkResponse,
    OAuthLoginCallbackRequest,
    OAuthLoginResponse,
    OAuthLoginUserResponse,
    OAuthProvider,
    TelegramCallbackRequest,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service
from src.shared.security.fingerprint import generate_client_fingerprint

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])

# Provider class map: provider_name -> (ProviderClass, requires_pkce)
_OAUTH_PROVIDERS: dict[str, tuple[type, bool]] = {
    "google": (GoogleOAuthProvider, True),
    "discord": (DiscordOAuthProvider, False),
    "apple": (AppleOAuthProvider, True),
    "microsoft": (MicrosoftOAuthProvider, True),
    "twitter": (TwitterOAuthProvider, True),
    "github": (GitHubOAuthProvider, False),
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/telegram/authorize", response_model=OAuthAuthorizeResponse)
async def telegram_authorize(
    request: Request,
    redirect_uri: str = Query(..., description="Redirect URI after authentication"),
    redis_client: redis.Redis = Depends(get_redis),
    user: AdminUserModel = Depends(get_current_active_user),
) -> OAuthAuthorizeResponse:
    """Get Telegram OAuth authorization URL with CSRF state token.

    The state token must be included in the callback request.
    """
    state_service = OAuthStateService(redis_client)
    state, _ = await state_service.generate(
        provider="telegram",
        user_id=str(user.id),
        ip_address=_get_client_ip(request),
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
    request: Request,
    redirect_uri: str = Query(..., description="Redirect URI after authentication"),
    redis_client: redis.Redis = Depends(get_redis),
    user: AdminUserModel = Depends(get_current_active_user),
) -> OAuthAuthorizeResponse:
    """Get GitHub OAuth authorization URL with CSRF state token.

    The state token must be included in the callback request.
    """
    state_service = OAuthStateService(redis_client)
    state, _ = await state_service.generate(
        provider="github",
        user_id=str(user.id),
        ip_address=_get_client_ip(request),
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


@router.get("/{provider}/login", response_model=OAuthAuthorizeResponse)
async def oauth_login_authorize(
    request: Request,
    provider: OAuthProvider,
    redirect_uri: str = Query(..., description="Redirect URI after authentication"),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthAuthorizeResponse:
    """Get OAuth authorization URL for login (no authentication required).

    Generates state token and PKCE challenge (when supported).
    """
    if provider.value not in _OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider.value}' does not support login flow.",
        )

    provider_class, requires_pkce = _OAUTH_PROVIDERS[provider.value]
    state_service = OAuthStateService(redis_client)
    state, code_challenge = await state_service.generate(
        provider=provider.value,
        ip_address=_get_client_ip(request),
        pkce=requires_pkce,
    )

    oauth_provider = provider_class()
    if requires_pkce:
        authorize_url = oauth_provider.authorize_url(
            redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
    else:
        authorize_url = oauth_provider.authorize_url(redirect_uri, state=state)

    return OAuthAuthorizeResponse(authorize_url=authorize_url, state=state)


@router.post("/{provider}/login/callback", response_model=OAuthLoginResponse)
async def oauth_login_callback(
    provider: OAuthProvider,
    callback_data: OAuthLoginCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> OAuthLoginResponse:
    """Process OAuth login callback and return JWT tokens (no authentication required).

    Validates state, exchanges code with provider, finds or creates user.
    """
    if provider.value not in _OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider.value}' does not support login flow.",
        )

    # Validate and consume state token
    state_service = OAuthStateService(redis_client)
    state_data = await state_service.validate_and_consume(
        state=callback_data.state,
        provider=provider.value,
        ip_address=_get_client_ip(request),
    )

    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state.",
        )

    # Exchange code with provider
    provider_class, _ = _OAUTH_PROVIDERS[provider.value]
    oauth_provider = provider_class()

    # Include code_verifier if PKCE was used
    code_verifier = state_data.get("code_verifier") if isinstance(state_data, dict) else None
    exchange_kwargs: dict[str, str] = {
        "code": callback_data.code,
        "redirect_uri": callback_data.redirect_uri,
    }
    if code_verifier:
        exchange_kwargs["code_verifier"] = code_verifier

    user_info = await oauth_provider.exchange_code(**exchange_kwargs)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth authentication failed.",
        )

    # Find or create user via OAuthLoginUseCase
    user_repo = AdminUserRepository(db)
    oauth_repo = OAuthAccountRepository(db)
    use_case = OAuthLoginUseCase(
        user_repo=user_repo,
        oauth_repo=oauth_repo,
        auth_service=auth_service,
        session=db,
        remnawave_gateway=remnawave_adapter,
    )

    try:
        result = await use_case.execute(
            provider=provider.value,
            user_info=user_info,
            client_fingerprint=generate_client_fingerprint(request),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    logger.info(
        "OAuth login completed",
        extra={
            "provider": provider.value,
            "user_id": str(result.user.id) if hasattr(result, "user") else "unknown",
            "is_new_user": result.is_new_user,
        },
    )

    return OAuthLoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=OAuthLoginUserResponse.model_validate(result.user),
        is_new_user=result.is_new_user,
        requires_2fa=result.requires_2fa,
        tfa_token=result.tfa_token,
    )


# ── Backward Compatibility Aliases ───────────────────────────────────────────


@router.get("/telegram/callback", response_model=OAuthLinkResponse, deprecated=True)
async def telegram_callback_get_alias(
    request: Request,
    id: int = Query(...),
    first_name: str = Query(...),
    auth_date: int = Query(...),
    hash: str = Query(...),
    state: str = Query(...),
    last_name: str | None = Query(None),
    username: str | None = Query(None),
    photo_url: str | None = Query(None),
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthLinkResponse:
    """Telegram OAuth callback (GET alias for mobile compatibility).

    **DEPRECATED**: Use POST /oauth/telegram/callback instead.

    This is an alias route for backward compatibility with mobile clients
    that use GET redirects. New implementations should use POST.
    """
    callback_data = TelegramCallbackRequest(
        id=str(id),
        first_name=first_name,
        auth_date=str(auth_date),
        hash=hash,
        state=state,
        last_name=last_name,
        username=username,
        photo_url=photo_url,
    )
    return await telegram_callback(callback_data, request, user, db, redis_client)


@router.get("/github/callback", response_model=OAuthLinkResponse, deprecated=True)
async def github_callback_get_alias(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthLinkResponse:
    """GitHub OAuth callback (GET alias for mobile compatibility).

    **DEPRECATED**: Use POST /oauth/github/callback instead.

    This is an alias route for backward compatibility with mobile clients
    that use GET redirects. New implementations should use POST.
    """
    callback_data = GitHubCallbackRequest(code=code, state=state, redirect_uri=redirect_uri)
    return await github_callback(callback_data, request, user, db, redis_client)
