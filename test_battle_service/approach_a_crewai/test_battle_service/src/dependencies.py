"""FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import decode_token
from src.database import get_db
from src.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Bearer access token.

    Raises 401 if the token is missing, invalid, expired, not an access
    token, or references a non-existent / inactive user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Only access tokens are accepted here
    if payload.get("type") != "access":
        raise credentials_exception

    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user
