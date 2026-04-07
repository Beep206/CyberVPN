"""OAuth routes with proper validation (CRIT-2).

Security improvements:
- Telegram: HMAC-SHA256 signature validation, auth_date check
- GitHub: Code-to-token exchange via GitHub API
- State parameter for CSRF protection (HIGH-5)
- Provider enum validation (HIGH-7)
"""

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlparse

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.oauth_state_service import OAuthStateService
from src.application.use_cases.auth.account_linking import AccountLinkingUseCase
from src.application.use_cases.auth.oauth_login import OAuthLoginUseCase
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.oauth_account_repo import OAuthAccountRepository
from src.infrastructure.monitoring.client_context import resolve_web_client_context
from src.infrastructure.monitoring.instrumentation.routes import (
    observe_auth_activation_duration,
    observe_auth_request_duration,
    sync_active_sessions,
    sync_auth_security_posture,
    track_auth_attempt,
    track_auth_error,
    track_auth_flow_event,
    track_auth_security_event,
    track_first_login_after_activation,
    track_oauth_attempt,
    track_oauth_callback_failure,
    track_registration,
)
from src.infrastructure.oauth.apple import AppleOAuthProvider
from src.infrastructure.oauth.discord import DiscordOAuthProvider
from src.infrastructure.oauth.errors import OAuthProviderUnavailableError
from src.infrastructure.oauth.facebook import FacebookOAuthProvider
from src.infrastructure.oauth.github import GitHubOAuthProvider
from src.infrastructure.oauth.google import GoogleOAuthProvider
from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider
from src.infrastructure.oauth.telegram import TelegramOAuthProvider
from src.infrastructure.oauth.twitter import TwitterOAuthProvider
from src.infrastructure.remnawave.adapters import RemnawaveUserAdapter, get_remnawave_adapter
from src.presentation.api.v1.auth.cookies import set_auth_cookies
from src.presentation.api.v1.auth.session_tokens import store_refresh_token
from src.presentation.api.v1.oauth.schemas import (
    FacebookCallbackRequest,
    GitHubCallbackRequest,
    OAuthAuthorizeResponse,
    OAuthLinkResponse,
    OAuthLoginCallbackRequest,
    OAuthLoginResponse,
    OAuthLoginUserResponse,
    OAuthProvider,
    TelegramCallbackRequest,
    TelegramMagicLinkCompleteRequest,
    TelegramMagicLinkCompleteResponse,
    TelegramMagicLinkResponse,
    TelegramMagicLinkStatusResponse,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service
from src.shared.security.fingerprint import generate_client_fingerprint

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])

_OAUTH_CALLBACK_PATH_RE = re.compile(r"^/(?:[a-z]{2,3}-[A-Z]{2}/)?oauth/callback/?$")
_OAUTH_WEB_CALLBACK_PREFIX = "/api/oauth/callback"

# Provider class map: provider_name -> (ProviderClass, requires_pkce)
_OAUTH_PROVIDERS: dict[str, tuple[type, bool]] = {
    "google": (GoogleOAuthProvider, True),
    "discord": (DiscordOAuthProvider, False),
    "facebook": (FacebookOAuthProvider, False),
    "apple": (AppleOAuthProvider, True),
    "microsoft": (MicrosoftOAuthProvider, True),
    "twitter": (TwitterOAuthProvider, True),
    "github": (GitHubOAuthProvider, True),
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _resolve_locale(user: AdminUserModel | None = None, fallback: str | None = None) -> str:
    if fallback:
        return fallback
    if user and user.language:
        return user.language
    return "unknown"


def _get_magic_link_key(token: str) -> str:
    return f"auth_magic_link:{token}"


def _is_allowed_oauth_redirect_uri(redirect_uri: str) -> bool:
    if redirect_uri in settings.oauth_allowed_redirect_uris:
        return True

    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    if parsed.params or parsed.query or parsed.fragment:
        return False

    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in settings.cors_origins:
        return False

    return _OAUTH_CALLBACK_PATH_RE.fullmatch(parsed.path) is not None


def _validate_oauth_redirect_uri(redirect_uri: str) -> None:
    if _is_allowed_oauth_redirect_uri(redirect_uri):
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OAuth redirect URI.",
    )


def _build_oauth_web_callback_uri(provider: str) -> str:
    base_url = settings.oauth_web_base_url
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth web callback base URL is not configured.",
        )

    return f"{base_url}{_OAUTH_WEB_CALLBACK_PREFIX}/{provider}"


def _resolve_oauth_login_redirect_uri(provider: str, redirect_uri: str | None) -> str:
    if redirect_uri is None:
        return _build_oauth_web_callback_uri(provider)

    if redirect_uri in settings.oauth_allowed_redirect_uris:
        return redirect_uri

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OAuth redirect URI.",
    )


def _is_oauth_login_provider_enabled(provider: str) -> bool:
    return provider in settings.oauth_enabled_login_providers


def _validate_oauth_login_provider(provider: OAuthProvider) -> None:
    if provider.value not in _OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider.value}' does not support login flow.",
        )

    if _is_oauth_login_provider_enabled(provider.value):
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Provider '{provider.value}' is currently disabled.",
    )


def _build_magic_link_user_info(payload: TelegramMagicLinkCompleteRequest) -> dict[str, str | None]:
    return {
        "id": payload.id,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "username": payload.username,
        "language_code": payload.language_code,
    }


async def _build_code_oauth_authorize_response(
    *,
    provider_name: str,
    provider_class: type,
    requires_pkce: bool,
    redirect_uri: str,
    request: Request,
    redis_client: redis.Redis,
    user: AdminUserModel,
) -> OAuthAuthorizeResponse:
    state_service = OAuthStateService(redis_client)
    state, code_challenge = await state_service.generate(
        provider=provider_name,
        user_id=str(user.id),
        ip_address=_get_client_ip(request),
        pkce=requires_pkce,
    )

    provider = provider_class()
    if requires_pkce:
        authorize_url = provider.authorize_url(
            redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
    else:
        authorize_url = provider.authorize_url(redirect_uri, state=state)
    return OAuthAuthorizeResponse(authorize_url=authorize_url, state=state)


async def _complete_code_oauth_link(
    *,
    provider_name: str,
    provider_class: type,
    requires_pkce: bool,
    callback_data: GitHubCallbackRequest | FacebookCallbackRequest,
    request: Request,
    user: AdminUserModel,
    db: AsyncSession,
    redis_client: redis.Redis,
) -> OAuthLinkResponse:
    state_service = OAuthStateService(redis_client)
    state_data = await state_service.validate_and_consume(
        state=callback_data.state,
        provider=provider_name,
        user_id=str(user.id),
        ip_address=_get_client_ip(request),
    )
    if not state_data:
        logger.warning(
            "%s OAuth callback with invalid state",
            provider_name.capitalize(),
            extra={"user_id": str(user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state.",
        )

    provider = provider_class()
    exchange_kwargs: dict[str, str] = {
        "code": callback_data.code,
        "redirect_uri": callback_data.redirect_uri,
    }
    code_verifier = state_data.get("code_verifier") if requires_pkce and isinstance(state_data, dict) else None
    if code_verifier:
        exchange_kwargs["code_verifier"] = code_verifier

    user_info = await provider.exchange_code(**exchange_kwargs)

    if not user_info:
        logger.warning(
            "%s OAuth code exchange failed",
            provider_name.capitalize(),
            extra={"user_id": str(user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth authentication failed.",
        )

    uc = AccountLinkingUseCase(db)
    await uc.link_account(
        user_id=user.id,
        provider=provider_name,
        provider_user_id=str(user_info["id"]),
        provider_username=user_info.get("username"),
        provider_email=user_info.get("email"),
        access_token=user_info.get("access_token", ""),
        refresh_token=user_info.get("refresh_token"),
    )

    logger.info(
        "%s account linked",
        provider_name.capitalize(),
        extra={"user_id": str(user.id), f"{provider_name}_id": user_info["id"]},
    )

    return OAuthLinkResponse(
        status="linked",
        provider=provider_name,
        provider_user_id=str(user_info["id"]),
    )


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
    return await _build_code_oauth_authorize_response(
        provider_name="github",
        provider_class=GitHubOAuthProvider,
        requires_pkce=True,
        redirect_uri=redirect_uri,
        request=request,
        redis_client=redis_client,
        user=user,
    )


@router.get("/facebook/authorize", response_model=OAuthAuthorizeResponse)
async def facebook_authorize(
    request: Request,
    redirect_uri: str = Query(..., description="Redirect URI after authentication"),
    redis_client: redis.Redis = Depends(get_redis),
    user: AdminUserModel = Depends(get_current_active_user),
) -> OAuthAuthorizeResponse:
    """Get Facebook OAuth authorization URL with CSRF state token.

    The state token must be included in the callback request.
    """
    return await _build_code_oauth_authorize_response(
        provider_name="facebook",
        provider_class=FacebookOAuthProvider,
        requires_pkce=False,
        redirect_uri=redirect_uri,
        request=request,
        redis_client=redis_client,
        user=user,
    )


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


@router.get("/telegram/magic-link", response_model=TelegramMagicLinkResponse)
async def create_telegram_magic_link(
    redis_client: redis.Redis = Depends(get_redis),
) -> TelegramMagicLinkResponse:
    """Create a new Deep Link (Magic Link) session for seamless Telegram login."""
    token = str(uuid.uuid4())

    provider = TelegramOAuthProvider()
    bot_username = provider.bot_username
    if not bot_username:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot is not configured.",
        )

    await redis_client.setex(_get_magic_link_key(token), 300, "pending")

    bot_url = f"https://t.me/{bot_username}?start=auth_{token}"
    deep_link_url = f"tg://resolve?domain={bot_username}&start=auth_{token}"

    return TelegramMagicLinkResponse(
        token=token,
        bot_url=bot_url,
        deep_link_url=deep_link_url,
    )


@router.post("/telegram/magic-link/complete", response_model=TelegramMagicLinkCompleteResponse)
async def complete_telegram_magic_link(
    payload: TelegramMagicLinkCompleteRequest,
    redis_client: redis.Redis = Depends(get_redis),
    _current_user: AdminUserModel = Depends(get_current_active_user),
) -> TelegramMagicLinkCompleteResponse:
    """Accept trusted Telegram bot data for a pending magic-link session."""
    redis_key = _get_magic_link_key(payload.token)
    current_status = await redis_client.get(redis_key)

    if current_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Magic link session expired or not found.",
        )

    if current_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Magic link session has already been completed.",
        )

    ttl_seconds = await redis_client.ttl(redis_key)
    if ttl_seconds <= 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Magic link session expired or not found.",
        )

    stored = await redis_client.set(
        redis_key,
        json.dumps(_build_magic_link_user_info(payload)),
        ex=ttl_seconds,
        xx=True,
    )
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Magic link session expired or not found.",
        )

    logger.info(
        "Telegram Magic Link session confirmed",
        extra={"telegram_id": payload.id},
    )

    return TelegramMagicLinkCompleteResponse(status="accepted")


@router.get("/telegram/magic-link/{token}/status", response_model=TelegramMagicLinkStatusResponse)
async def check_telegram_magic_link_status(
    request: Request,
    response: Response,
    token: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> TelegramMagicLinkStatusResponse:
    """Poll the status of the Magic Link login session."""
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        request.headers.get("User-Agent"),
        request.headers.get("sec-ch-ua-mobile"),
    )
    redis_key = _get_magic_link_key(token)
    raw_status = await redis_client.get(redis_key)
    if not raw_status:
        return TelegramMagicLinkStatusResponse(status="expired")

    status_str = raw_status.decode("utf-8") if isinstance(raw_status, bytes) else raw_status
    if status_str == "pending":
        return TelegramMagicLinkStatusResponse(status="pending")

    consumed_status = await redis_client.getdel(redis_key)
    if not consumed_status:
        return TelegramMagicLinkStatusResponse(status="expired")

    consumed_status_str = consumed_status.decode("utf-8") if isinstance(consumed_status, bytes) else consumed_status
    if consumed_status_str == "pending":
        return TelegramMagicLinkStatusResponse(status="pending")

    try:
        user_info = json.loads(consumed_status_str)
    except json.JSONDecodeError:
        logger.exception("Failed to parse Telegram Magic Link payload")
        return TelegramMagicLinkStatusResponse(status="expired")

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
            provider="telegram",
            user_info=user_info,
            client_fingerprint=generate_client_fingerprint(request),
            client_ip=_get_client_ip(request),
        )
    except ValueError as e:
        track_auth_attempt(method="telegram", success=False)
        track_auth_error("invalid_credentials")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        observe_auth_request_duration("telegram", started_at)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    logger.info(
        "Telegram Magic Link login completed",
        extra={
            "user_id": str(result.user.id),
            "is_new_user": result.is_new_user,
        },
    )

    login_result = OAuthLoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        user=OAuthLoginUserResponse.model_validate(result.user),
        is_new_user=result.is_new_user,
        requires_2fa=result.requires_2fa,
        tfa_token=result.tfa_token,
    )

    if result.access_token and result.refresh_token:
        refresh_payload = auth_service.decode_token(result.refresh_token)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], UTC)
        await store_refresh_token(
            db,
            user_id=result.user.id,
            refresh_token=result.refresh_token,
            expires_at=refresh_exp,
            device_id=generate_client_fingerprint(request),
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        set_auth_cookies(response, result.access_token, result.refresh_token)
        await sync_active_sessions(db)
        await sync_auth_security_posture(db, redis_client)

    track_auth_attempt(method="telegram", success=True)
    locale = _resolve_locale(result.user, user_info.get("language_code") if isinstance(user_info, dict) else None)
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="telegram",
        provider="telegram",
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )
    if result.is_new_user:
        track_registration(method="telegram")
        track_first_login_after_activation("telegram")
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="registered",
        )
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="telegram",
            provider="telegram",
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
        )
    await sync_auth_security_posture(db, redis_client)
    observe_auth_request_duration("telegram", started_at)

    return TelegramMagicLinkStatusResponse(status="completed", login_result=login_result)


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
    return await _complete_code_oauth_link(
        provider_name="github",
        provider_class=GitHubOAuthProvider,
        requires_pkce=True,
        callback_data=callback_data,
        request=request,
        user=user,
        db=db,
        redis_client=redis_client,
    )


@router.post("/facebook/callback", response_model=OAuthLinkResponse)
async def facebook_callback(
    callback_data: FacebookCallbackRequest,
    request: Request,
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthLinkResponse:
    """Process Facebook OAuth callback and link account."""
    return await _complete_code_oauth_link(
        provider_name="facebook",
        provider_class=FacebookOAuthProvider,
        requires_pkce=False,
        callback_data=callback_data,
        request=request,
        user=user,
        db=db,
        redis_client=redis_client,
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
    redirect_uri: str | None = Query(
        default=None,
        description="Exact native/universal callback URI. Omit for canonical web flow.",
    ),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthAuthorizeResponse:
    """Get OAuth authorization URL for login (no authentication required).

    Generates state token and PKCE challenge (when supported).
    """
    _validate_oauth_login_provider(provider)
    resolved_redirect_uri = _resolve_oauth_login_redirect_uri(provider.value, redirect_uri)

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
            resolved_redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
    else:
        authorize_url = oauth_provider.authorize_url(resolved_redirect_uri, state=state)

    return OAuthAuthorizeResponse(authorize_url=authorize_url, state=state)


@router.post("/{provider}/login/callback", response_model=OAuthLoginResponse)
async def oauth_login_callback(
    provider: OAuthProvider,
    callback_data: OAuthLoginCallbackRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
    remnawave_adapter: RemnawaveUserAdapter = Depends(get_remnawave_adapter),
) -> OAuthLoginResponse:
    """Process OAuth login callback and return JWT tokens (no authentication required).

    Validates state, exchanges code with provider, finds or creates user.
    """
    started_at = perf_counter()
    client_context = resolve_web_client_context(
        request.headers.get("User-Agent"),
        request.headers.get("sec-ch-ua-mobile"),
    )
    _validate_oauth_login_provider(provider)
    resolved_redirect_uri = _resolve_oauth_login_redirect_uri(provider.value, callback_data.redirect_uri)

    # Validate and consume state token
    state_service = OAuthStateService(redis_client)
    state_data = await state_service.validate_and_consume(
        state=callback_data.state,
        provider=provider.value,
        ip_address=_get_client_ip(request),
    )

    if not state_data:
        track_oauth_attempt(provider=provider.value, success=False)
        track_auth_attempt(method="oauth", success=False)
        track_auth_error("expired_token")
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            error_type="expired_token",
        )
        track_oauth_callback_failure(channel="web", provider=provider.value, reason="invalid_state")
        observe_auth_request_duration("oauth", started_at)
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
        "redirect_uri": resolved_redirect_uri,
    }
    if code_verifier:
        exchange_kwargs["code_verifier"] = code_verifier

    try:
        user_info = await oauth_provider.exchange_code(**exchange_kwargs)
    except OAuthProviderUnavailableError as exc:
        track_oauth_attempt(provider=provider.value, success=False)
        track_auth_attempt(method="oauth", success=False)
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_oauth_callback_failure(channel="web", provider=provider.value, reason="provider_unavailable")
        observe_auth_request_duration("oauth", started_at)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if not user_info:
        track_oauth_attempt(provider=provider.value, success=False)
        track_auth_attempt(method="oauth", success=False)
        track_auth_error("invalid_credentials")
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            error_type="invalid_credentials",
        )
        track_oauth_callback_failure(channel="web", provider=provider.value, reason="exchange_failed")
        observe_auth_request_duration("oauth", started_at)
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
            client_ip=_get_client_ip(request),
        )
    except ValueError as e:
        track_oauth_attempt(provider=provider.value, success=False)
        track_auth_attempt(method="oauth", success=False)
        track_auth_error("invalid_credentials")
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            client_context=client_context,
            step="login",
            status="failure",
        )
        track_auth_security_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale="unknown",
            error_type="invalid_credentials",
        )
        track_oauth_callback_failure(channel="web", provider=provider.value, reason="account_conflict")
        observe_auth_request_duration("oauth", started_at)
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

    if result.access_token and result.refresh_token:
        refresh_payload = auth_service.decode_token(result.refresh_token)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], UTC)
        await store_refresh_token(
            db,
            user_id=result.user.id,
            refresh_token=result.refresh_token,
            expires_at=refresh_exp,
            device_id=generate_client_fingerprint(request),
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        set_auth_cookies(response, result.access_token, result.refresh_token)
        await sync_active_sessions(db)
        await sync_auth_security_posture(db, redis_client)

    track_oauth_attempt(provider=provider.value, success=True)
    track_auth_attempt(method="oauth", success=True)
    locale = _resolve_locale(result.user, user_info.get("language_code") if isinstance(user_info, dict) else None)
    track_auth_flow_event(
        channel="web",
        method="oauth",
        provider=provider.value,
        locale=locale,
        client_context=client_context,
        step="login",
        status="success",
    )
    track_auth_flow_event(
        channel="web",
        method="oauth",
        provider=provider.value,
        locale=locale,
        client_context=client_context,
        step="session_started",
        status="success",
    )
    if result.is_new_user:
        track_registration(method="oauth")
        track_first_login_after_activation("oauth")
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale=locale,
            client_context=client_context,
            step="registered",
        )
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale=locale,
            client_context=client_context,
            step="activated",
        )
        track_auth_flow_event(
            channel="web",
            method="oauth",
            provider=provider.value,
            locale=locale,
            client_context=client_context,
            step="first_successful_login",
        )
        observe_auth_activation_duration(
            channel="web",
            method="oauth",
            locale=locale,
            stage="first_login",
            started_at=result.user.created_at,
        )
    await sync_auth_security_posture(db, redis_client)
    observe_auth_request_duration("oauth", started_at)

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


@router.get("/facebook/callback", response_model=OAuthLinkResponse, deprecated=True)
async def facebook_callback_get_alias(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
    user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthLinkResponse:
    """Facebook OAuth callback (GET alias for mobile compatibility).

    **DEPRECATED**: Use POST /oauth/facebook/callback instead.
    """
    callback_data = FacebookCallbackRequest(code=code, state=state, redirect_uri=redirect_uri)
    return await facebook_callback(callback_data, request, user, db, redis_client)
