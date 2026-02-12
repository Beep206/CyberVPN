"""Notification preferences routes for authenticated users (BF2-5)."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.monitoring.metrics import notification_operations_total
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

from .schemas import NotificationPreferencesResponse, NotificationPreferencesUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me", tags=["notifications"])

# Default notification preferences
DEFAULT_PREFS = {
    "email_security": True,
    "email_marketing": False,
    "push_connection": True,
    "push_payment": True,
    "push_subscription": True,
}


@router.get(
    "/notifications",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
    description="Returns the current user's notification preferences.",
)
async def get_notification_preferences(
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> NotificationPreferencesResponse:
    """Return the notification preferences for the authenticated user."""
    logger.info(
        "Notification preferences read requested",
        extra={"user_id": str(current_user.id)},
    )

    # Merge user prefs with defaults
    prefs = {**DEFAULT_PREFS, **(current_user.notification_prefs or {})}

    notification_operations_total.labels(operation="get_preferences").inc()
    return NotificationPreferencesResponse(
        email_security=prefs.get("email_security", True),
        email_marketing=prefs.get("email_marketing", False),
        push_connection=prefs.get("push_connection", True),
        push_payment=prefs.get("push_payment", True),
        push_subscription=prefs.get("push_subscription", True),
    )


@router.patch(
    "/notifications",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
    description=(
        "Partially update the current user's notification preferences. "
        "Only the fields present in the request body are applied."
    ),
)
async def update_notification_preferences(
    request: NotificationPreferencesUpdateRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    """Apply a partial update to the authenticated user's notification preferences."""
    # Extract only the fields explicitly provided in the request
    updates = request.model_dump(exclude_unset=True)

    logger.info(
        "Notification preferences update requested",
        extra={
            "user_id": str(current_user.id),
            "updated_fields": list(updates.keys()),
        },
    )

    # Merge with existing preferences
    current_prefs = current_user.notification_prefs or {}
    merged_prefs = {**DEFAULT_PREFS, **current_prefs, **updates}

    # Update the user model
    user_repo = AdminUserRepository(db)
    current_user.notification_prefs = merged_prefs

    # Persist to database
    updated_user = await user_repo.update(current_user)
    await db.commit()
    await db.refresh(updated_user)

    logger.info(
        "Notification preferences updated successfully",
        extra={"user_id": str(updated_user.id)},
    )

    notification_operations_total.labels(operation="update_preferences").inc()
    return NotificationPreferencesResponse(
        email_security=merged_prefs.get("email_security", True),
        email_marketing=merged_prefs.get("email_marketing", False),
        push_connection=merged_prefs.get("push_connection", True),
        push_payment=merged_prefs.get("push_payment", True),
        push_subscription=merged_prefs.get("push_subscription", True),
    )
