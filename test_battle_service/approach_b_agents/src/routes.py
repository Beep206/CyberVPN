from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.database import get_db
from src.dependencies import get_current_user
from src.models import User
from src.schemas import (
    AccessTokenResponse,
    RefreshTokenRequest,
    TokenPairResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user. Returns 409 if email already exists."""
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenPairResponse,
)
async def login(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPairResponse:
    """Authenticate a user and return access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    return TokenPairResponse(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return current_user


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
)
async def refresh(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """Issue a new access token given a valid refresh token."""
    payload = decode_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    email: str | None = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    return AccessTokenResponse(
        access_token=create_access_token(user.email),
    )


@router.post(
    "/token/verify",
    response_model=TokenVerifyResponse,
)
async def verify_token(
    body: TokenVerifyRequest,
) -> TokenVerifyResponse:
    """Verify whether a JWT token is valid. Always returns 200 with a validity flag."""
    payload = decode_token(body.token)
    if payload is None:
        return TokenVerifyResponse(valid=False)

    return TokenVerifyResponse(
        valid=True,
        email=payload.get("sub"),
        exp=payload.get("exp"),
    )
