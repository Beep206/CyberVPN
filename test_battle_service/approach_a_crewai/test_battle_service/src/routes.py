"""Auth API router — 5 endpoints covering the full JWT auth lifecycle."""

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

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# 1. POST /auth/register
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error (invalid email or password < 8 chars)"},
    },
)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account with email and password."""
    # Check for existing user
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
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


# ---------------------------------------------------------------------------
# 2. POST /auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Authenticate and receive tokens",
    responses={401: {"description": "Invalid email or password"}},
)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password, receive access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenPairResponse(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


# ---------------------------------------------------------------------------
# 3. GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    responses={401: {"description": "Missing, invalid, or expired token"}},
)
async def me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user


# ---------------------------------------------------------------------------
# 4. POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh an access token",
    responses={401: {"description": "Invalid or expired refresh token"}},
)
async def refresh(body: RefreshTokenRequest):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(body.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    email: str | None = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    return AccessTokenResponse(access_token=create_access_token(email))


# ---------------------------------------------------------------------------
# 5. POST /auth/token/verify
# ---------------------------------------------------------------------------
@router.post(
    "/token/verify",
    response_model=TokenVerifyResponse,
    summary="Verify a token's validity",
)
async def token_verify(body: TokenVerifyRequest):
    """Check whether a JWT is valid and return its claims if so."""
    payload = decode_token(body.token)

    if payload is None:
        return TokenVerifyResponse(valid=False, email=None, exp=None)

    return TokenVerifyResponse(
        valid=True,
        email=payload.get("sub"),
        exp=payload.get("exp"),
    )
