"""Authenticated user profile routes.

Provides ``PATCH /api/v1/users/me/profile`` so that the currently
authenticated admin user can update their own profile settings.

This is a **placeholder implementation** -- no database writes are
performed.  The endpoint validates input, merges provided fields with
mock defaults, and returns a synthetic ``ProfileResponse``.
"""

import logging

from fastapi import APIRouter, Depends

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user

from .schemas import ProfileResponse, ProfileUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me", tags=["profile"])


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Get current user profile",
    description=(
        "Returns the profile of the currently authenticated user. Placeholder implementation returning mock data."
    ),
)
async def get_profile(
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> ProfileResponse:
    """Return the profile for the authenticated user.

    This is a placeholder that constructs a response from the existing
    ``AdminUserModel`` fields plus hard-coded defaults for fields that
    do not yet exist in the database schema.
    """
    logger.info(
        "Profile read requested",
        extra={"user_id": str(current_user.id)},
    )

    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email or "",
        display_name=current_user.login,
        avatar_url=None,
        language="en",
        timezone="UTC",
        updated_at=current_user.updated_at,
    )


@router.patch(
    "/profile",
    response_model=ProfileResponse,
    summary="Update current user profile",
    description=(
        "Partially update the profile of the currently authenticated user. "
        "Only the fields present in the request body are applied. "
        "Placeholder implementation -- changes are NOT persisted."
    ),
)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> ProfileResponse:
    """Apply a partial update to the authenticated user's profile.

    This is a placeholder that validates the inbound payload and
    returns a mock response reflecting the requested changes.  No
    database or cache writes are performed.
    """
    # Merge provided fields over the current defaults.
    # ``model_fields_set`` contains only the keys the client explicitly sent.
    base = {
        "display_name": current_user.login,
        "avatar_url": None,
        "language": "en",
        "timezone": "UTC",
    }

    updates = request.model_dump(exclude_unset=True)
    merged = {**base, **updates}

    logger.info(
        "Profile update requested (placeholder -- not persisted)",
        extra={
            "user_id": str(current_user.id),
            "updated_fields": list(updates.keys()),
        },
    )

    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email or "",
        display_name=merged["display_name"],
        avatar_url=merged["avatar_url"],
        language=merged["language"],
        timezone=merged["timezone"],
        updated_at=current_user.updated_at,
    )
