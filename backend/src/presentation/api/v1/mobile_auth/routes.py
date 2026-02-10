"""Mobile authentication API routes.

Endpoints for mobile app authentication: register, login, refresh, logout, me, device.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    DeviceInfoDTO,
    LoginRequestDTO,
    LogoutRequestDTO,
    Platform,
    RefreshTokenRequestDTO,
    RegisterRequestDTO,
    TelegramAuthRequestDTO,
)
from src.application.services.auth_service import AuthService
from src.application.services.cache_service import CacheService
from src.application.services.telegram_auth import (
    InvalidTelegramAuthError,
    TelegramAuthExpiredError,
    TelegramAuthService,
)
from src.application.use_cases.mobile_auth.device import MobileDeviceRegistrationUseCase
from src.application.use_cases.mobile_auth.login import MobileLoginUseCase
from src.application.use_cases.mobile_auth.logout import MobileLogoutUseCase
from src.application.use_cases.mobile_auth.me import MobileGetProfileUseCase
from src.application.use_cases.mobile_auth.refresh import MobileRefreshUseCase
from src.application.use_cases.mobile_auth.register import MobileRegisterUseCase
from src.application.use_cases.mobile_auth.telegram_auth import MobileTelegramAuthUseCase
from src.domain.exceptions import (
    DuplicateUsernameError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)
from src.infrastructure.remnawave.client import remnawave_client
from src.infrastructure.remnawave.subscription_client import (
    CachedSubscriptionClient,
    RemnawaveSubscriptionClient,
)
from src.presentation.api.v1.mobile_auth.schemas import (
    AuthResponse,
    DeviceRegistrationRequest,
    DeviceResponse,
    LoginRequest,
    LogoutRequest,
    MobileAuthError,
    RefreshTokenRequest,
    RegisterRequest,
    SubscriptionInfo,
    SubscriptionStatus,
    TelegramAuthRequest,
    TokenResponse,
    UserResponse,
)
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.mobile_rate_limit import (
    LoginRateLimit,
    RegisterRateLimit,
)


async def _get_subscription_client(
    redis_client=Depends(get_redis),
) -> CachedSubscriptionClient:
    """Dependency for CachedSubscriptionClient."""
    inner = RemnawaveSubscriptionClient(remnawave_client)
    cache = CacheService(redis_client)
    return CachedSubscriptionClient(inner=inner, cache=cache)


router = APIRouter(prefix="/mobile/auth", tags=["mobile-auth"])


# ============================================================================
# Helper functions for DTO conversion
# ============================================================================


def _device_dto(device) -> DeviceInfoDTO:
    """Convert Pydantic DeviceInfo to DTO."""
    return DeviceInfoDTO(
        device_id=device.device_id,
        platform=Platform(device.platform.value),
        platform_id=device.platform_id,
        os_version=device.os_version,
        app_version=device.app_version,
        device_model=device.device_model,
        push_token=device.push_token,
    )


def _register_dto_from_request(request: RegisterRequest) -> RegisterRequestDTO:
    """Convert Pydantic register request to application DTO."""
    return RegisterRequestDTO(
        email=request.email,
        password=request.password,
        device=_device_dto(request.device),
    )


def _login_dto_from_request(request: LoginRequest) -> LoginRequestDTO:
    """Convert Pydantic login request to application DTO."""
    return LoginRequestDTO(
        email=request.email,
        password=request.password,
        device=_device_dto(request.device),
        remember_me=request.remember_me,
    )


def _user_response_from_dto(dto) -> UserResponse:
    """Convert user DTO to Pydantic response."""
    subscription = None
    if dto.subscription:
        subscription = SubscriptionInfo(
            status=SubscriptionStatus(dto.subscription.status.value),
            plan_name=dto.subscription.plan_name,
            expires_at=dto.subscription.expires_at,
            traffic_limit_bytes=dto.subscription.traffic_limit_bytes,
            used_traffic_bytes=dto.subscription.used_traffic_bytes,
            auto_renew=dto.subscription.auto_renew,
        )

    return UserResponse(
        id=dto.id,
        email=dto.email,
        username=dto.username,
        status=dto.status,
        telegram_id=dto.telegram_id,
        telegram_username=dto.telegram_username,
        created_at=dto.created_at,
        subscription=subscription,
    )


def _auth_response_from_dto(dto) -> AuthResponse:
    """Convert auth DTO to Pydantic response schema."""
    return AuthResponse(
        tokens=TokenResponse(
            access_token=dto.tokens.access_token,
            refresh_token=dto.tokens.refresh_token,
            token_type=dto.tokens.token_type,
            expires_in=dto.tokens.expires_in,
        ),
        user=_user_response_from_dto(dto.user),
        is_new_user=dto.is_new_user,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": MobileAuthError,
            "description": "Email already registered",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": MobileAuthError,
            "description": "Too many registration attempts (limit: 3/min per IP)",
        },
    },
)
async def register(
    request: RegisterRequest,
    _rate_limit: RegisterRateLimit,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new mobile app user.

    Creates a new user account with the provided email and password,
    registers the device, and returns authentication tokens.

    **Error Codes:**
    - `EMAIL_EXISTS`: Email already registered (409)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)
    auth_service = AuthService()

    use_case = MobileRegisterUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=auth_service,
    )

    try:
        dto_request = _register_dto_from_request(request)
        result = await use_case.execute(dto_request)
        await db.commit()
        return _auth_response_from_dto(result)

    except DuplicateUsernameError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": "Email already registered"},
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Invalid credentials",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": MobileAuthError,
            "description": "Too many login attempts (limit: 5/min per device)",
        },
    },
)
async def login(
    request: LoginRequest,
    _rate_limit: LoginRateLimit,
    db: AsyncSession = Depends(get_db),
    sub_client: CachedSubscriptionClient = Depends(_get_subscription_client),
) -> AuthResponse:
    """Authenticate a mobile app user.

    Validates credentials, updates device registration, and returns tokens.

    **Error Codes:**
    - `INVALID_CREDENTIALS`: Wrong email/password or account disabled (401)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)
    auth_service = AuthService()

    use_case = MobileLoginUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=auth_service,
        subscription_client=sub_client,
    )

    try:
        dto_request = _login_dto_from_request(request)
        result = await use_case.execute(dto_request)
        await db.commit()
        return _auth_response_from_dto(result)

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Invalid or expired refresh token",
        },
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh authentication tokens.

    Exchanges a valid refresh token for new access and refresh tokens.

    **Error Codes:**
    - `INVALID_TOKEN`: Refresh token is invalid, expired, or device mismatch (401)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)
    auth_service = AuthService()

    use_case = MobileRefreshUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=auth_service,
    )

    try:
        dto_request = RefreshTokenRequestDTO(
            refresh_token=request.refresh_token,
            device_id=request.device_id,
        )
        result = await use_case.execute(dto_request)
        return TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
        )

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired refresh token"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Invalid token",
        },
    },
)
async def logout(
    request: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout a mobile app user.

    Revokes the refresh token and optionally removes device registration.

    **Error Codes:**
    - `INVALID_TOKEN`: Token is invalid or device mismatch (401)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)
    auth_service = AuthService()

    use_case = MobileLogoutUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=auth_service,
    )

    try:
        dto_request = LogoutRequestDTO(
            refresh_token=request.refresh_token,
            device_id=request.device_id,
        )
        await use_case.execute(dto_request)
        await db.commit()

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token"},
        )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Not authenticated",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": MobileAuthError,
            "description": "User not found",
        },
    },
)
async def get_me(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    sub_client: CachedSubscriptionClient = Depends(_get_subscription_client),
) -> UserResponse:
    """Get current user profile.

    Returns the authenticated user's profile with subscription information.

    **Error Codes:**
    - `UNAUTHORIZED`: Not authenticated (401)
    - `USER_NOT_FOUND`: User account not found (404)
    """
    user_repo = MobileUserRepository(db)

    use_case = MobileGetProfileUseCase(user_repo=user_repo, subscription_client=sub_client)

    try:
        result = await use_case.execute(user_id)
        return _user_response_from_dto(result)

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )


@router.post(
    "/device",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Not authenticated",
        },
    },
)
async def register_device(
    request: DeviceRegistrationRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """Register or update a mobile device.

    Registers a new device or updates existing device information.
    Used for push notifications and session management.

    **Error Codes:**
    - `UNAUTHORIZED`: Not authenticated (401)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)

    use_case = MobileDeviceRegistrationUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
    )

    try:
        result = await use_case.execute(user_id, _device_dto(request.device))
        await db.commit()
        return DeviceResponse(
            device_id=result.device_id,
            registered_at=result.registered_at,
            last_active_at=result.last_active_at,
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )


@router.post(
    "/telegram/callback",
    response_model=AuthResponse,
    responses={
        status.HTTP_200_OK: {
            "model": AuthResponse,
            "description": "Existing user authenticated via Telegram",
        },
        status.HTTP_201_CREATED: {
            "model": AuthResponse,
            "description": "New user created and authenticated via Telegram",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": MobileAuthError,
            "description": "Invalid Telegram authentication data",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Telegram authentication expired or invalid signature",
        },
    },
)
async def telegram_callback(
    request: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
    sub_client: CachedSubscriptionClient = Depends(_get_subscription_client),
) -> AuthResponse:
    """Authenticate via Telegram Login Widget.

    Validates Telegram OAuth callback data and creates or links user account.
    New users are auto-created from Telegram profile data.

    **Error Codes:**
    - `INVALID_TELEGRAM_AUTH`: Invalid signature or malformed data (400)
    - `TELEGRAM_AUTH_EXPIRED`: auth_date is older than 24 hours (401)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)
    auth_service = AuthService()
    telegram_auth_service = TelegramAuthService()

    use_case = MobileTelegramAuthUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=auth_service,
        telegram_auth_service=telegram_auth_service,
        subscription_client=sub_client,
    )

    try:
        dto_request = TelegramAuthRequestDTO(
            auth_data=request.auth_data,
            device=_device_dto(request.device),
        )
        result, _ = await use_case.execute(dto_request)
        await db.commit()

        # Note: Clients should check is_new_user flag in response
        # to determine if this was a new registration.
        return _auth_response_from_dto(result)

    except InvalidTelegramAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TELEGRAM_AUTH", "message": str(e.message)},
        )
    except TelegramAuthExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TELEGRAM_AUTH_EXPIRED", "message": str(e.message)},
        )
