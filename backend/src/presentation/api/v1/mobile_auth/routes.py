"""Mobile authentication API routes.

Endpoints for mobile app authentication: register, login, refresh, logout, device.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    DeviceInfoDTO,
    LoginRequestDTO,
    Platform,
    RegisterRequestDTO,
)
from src.application.services.auth_service import AuthService
from src.application.use_cases.mobile_auth.login import MobileLoginUseCase
from src.application.use_cases.mobile_auth.register import MobileRegisterUseCase
from src.domain.exceptions import DuplicateUsernameError, InvalidCredentialsError
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)
from src.presentation.api.v1.mobile_auth.schemas import (
    AuthResponse,
    LoginRequest,
    MobileAuthError,
    RegisterRequest,
    SubscriptionInfo,
    SubscriptionStatus,
    TokenResponse,
    UserResponse,
)
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/mobile/auth", tags=["mobile-auth"])


def _register_dto_from_request(request: RegisterRequest) -> RegisterRequestDTO:
    """Convert Pydantic register request to application DTO."""
    return RegisterRequestDTO(
        email=request.email,
        password=request.password,
        device=DeviceInfoDTO(
            device_id=request.device.device_id,
            platform=Platform(request.device.platform.value),
            platform_id=request.device.platform_id,
            os_version=request.device.os_version,
            app_version=request.device.app_version,
            device_model=request.device.device_model,
            push_token=request.device.push_token,
        ),
    )


def _login_dto_from_request(request: LoginRequest) -> LoginRequestDTO:
    """Convert Pydantic login request to application DTO."""
    return LoginRequestDTO(
        email=request.email,
        password=request.password,
        device=DeviceInfoDTO(
            device_id=request.device.device_id,
            platform=Platform(request.device.platform.value),
            platform_id=request.device.platform_id,
            os_version=request.device.os_version,
            app_version=request.device.app_version,
            device_model=request.device.device_model,
            push_token=request.device.push_token,
        ),
        remember_me=request.remember_me,
    )


def _response_from_dto(dto) -> AuthResponse:
    """Convert application DTO to Pydantic response schema."""
    subscription = None
    if dto.user.subscription:
        subscription = SubscriptionInfo(
            status=SubscriptionStatus(dto.user.subscription.status.value),
            plan_name=dto.user.subscription.plan_name,
            expires_at=dto.user.subscription.expires_at,
            traffic_limit_bytes=dto.user.subscription.traffic_limit_bytes,
            used_traffic_bytes=dto.user.subscription.used_traffic_bytes,
            auto_renew=dto.user.subscription.auto_renew,
        )

    return AuthResponse(
        tokens=TokenResponse(
            access_token=dto.tokens.access_token,
            refresh_token=dto.tokens.refresh_token,
            token_type=dto.tokens.token_type,
            expires_in=dto.tokens.expires_in,
        ),
        user=UserResponse(
            id=dto.user.id,
            email=dto.user.email,
            username=dto.user.username,
            status=dto.user.status,
            telegram_id=dto.user.telegram_id,
            telegram_username=dto.user.telegram_username,
            created_at=dto.user.created_at,
            subscription=subscription,
        ),
        is_new_user=dto.is_new_user,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": MobileAuthError,
            "description": "Email already registered",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": MobileAuthError,
            "description": "Validation error",
        },
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new mobile app user.

    Creates a new user account with the provided email and password,
    registers the device, and returns authentication tokens.

    **Request Body:**
    - `email`: Valid email address (unique)
    - `password`: 8+ chars with at least one letter and one digit
    - `device`: Device information (device_id, platform, os_version, etc.)

    **Response:**
    - `tokens`: Access and refresh JWT tokens
    - `user`: User profile with subscription info
    - `is_new_user`: Always true for registration

    **Error Codes:**
    - `EMAIL_EXISTS`: Email already registered (409)
    - `VALIDATION_ERROR`: Invalid request data (422)
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
        return _response_from_dto(result)

    except DuplicateUsernameError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_EXISTS",
                "message": "Email already registered",
            },
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": MobileAuthError,
            "description": "Invalid credentials or account disabled",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": MobileAuthError,
            "description": "Rate limit exceeded",
        },
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate a mobile app user.

    Validates credentials, updates device registration, and returns authentication tokens.

    **Request Body:**
    - `email`: User email address
    - `password`: User password
    - `device`: Device information
    - `remember_me`: If true, extends refresh token TTL to 30 days

    **Response:**
    - `tokens`: Access and refresh JWT tokens
    - `user`: User profile with subscription info
    - `is_new_user`: Always false for login

    **Error Codes:**
    - `INVALID_CREDENTIALS`: Wrong email/password or account disabled (401)
    - `RATE_LIMITED`: Too many login attempts (429)
    """
    user_repo = MobileUserRepository(db)
    device_repo = MobileDeviceRepository(db)
    auth_service = AuthService()

    use_case = MobileLoginUseCase(
        user_repo=user_repo,
        device_repo=device_repo,
        auth_service=auth_service,
    )

    try:
        dto_request = _login_dto_from_request(request)
        result = await use_case.execute(dto_request)
        await db.commit()
        return _response_from_dto(result)

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password",
            },
        )
