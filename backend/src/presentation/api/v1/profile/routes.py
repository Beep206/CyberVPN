"""Authenticated user profile routes.

Provides GET and PATCH endpoints for authenticated user profile management.
All profile updates are persisted to the database.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.monitoring.instrumentation.routes import track_profile_update
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

from .schemas import ProfileResponse, ProfileUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me", tags=["profile"])


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
async def get_profile(
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> ProfileResponse:
    """Return the profile for the authenticated user."""
    logger.info(
        "Profile read requested",
        extra={"user_id": str(current_user.id)},
    )

    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email or "",
        display_name=current_user.display_name or current_user.login,
        avatar_url=None,
        language=current_user.language,
        timezone=current_user.timezone,
        updated_at=current_user.updated_at,
    )


@router.patch(
    "/profile",
    response_model=ProfileResponse,
    summary="Update current user profile",
    description=(
        "Partially update the profile of the currently authenticated user. "
        "Only the fields present in the request body are applied."
    ),
)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Apply a partial update to the authenticated user's profile.

    Persists changes to the database and returns the updated profile.
    """
    # Extract only the fields explicitly provided in the request
    updates = request.model_dump(exclude_unset=True)

    logger.info(
        "Profile update requested",
        extra={
            "user_id": str(current_user.id),
            "updated_fields": list(updates.keys()),
        },
    )

    # Update the user model with provided fields
    user_repo = AdminUserRepository(db)

    # Apply updates to the current user instance
    for field, value in updates.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
            track_profile_update(field=field)

    # Persist to database
    updated_user = await user_repo.update(current_user)
    await db.commit()
    await db.refresh(updated_user)

    logger.info(
        "Profile updated successfully",
        extra={"user_id": str(updated_user.id)},
    )

    return ProfileResponse(
        id=str(updated_user.id),
        email=updated_user.email or "",
        display_name=updated_user.display_name or updated_user.login,
        avatar_url=None,
        language=updated_user.language,
        timezone=updated_user.timezone,
        updated_at=updated_user.updated_at,
    )
