"""FCM token registration and removal endpoints.

Mobile clients call these endpoints to register or unregister Firebase
Cloud Messaging tokens so the backend can send push notifications.

Both endpoints require authentication -- the token is associated with
the currently authenticated user.

NOTE: This is a **placeholder** implementation.  The endpoints accept
valid schemas and return appropriate responses, but token persistence
will be added once the FCM infrastructure layer is in place.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from src.presentation.dependencies.auth import get_current_active_user

from .schemas import FCMTokenDeleteRequest, FCMTokenRequest, FCMTokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me/fcm-token", tags=["fcm"])


@router.post(
    "",
    response_model=FCMTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register FCM token",
    description=(
        "Register (or refresh) a Firebase Cloud Messaging token for the "
        "authenticated user's device.  If a token already exists for the "
        "given device_id it will be replaced."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "User account is inactive"},
        422: {"description": "Validation error"},
    },
)
async def register_fcm_token(
    body: FCMTokenRequest,
    _user=Depends(get_current_active_user),
) -> FCMTokenResponse:
    """Register an FCM push-notification token for the current user.

    Placeholder implementation -- logs the registration and returns the
    token data without persisting it.  Real storage will be wired once
    the infrastructure repository is ready.
    """
    logger.info(
        "FCM token registered (placeholder)",
        extra={
            "user_id": str(_user.id),
            "device_id": body.device_id,
            "platform": body.platform,
        },
    )
    return FCMTokenResponse(
        token=body.token,
        device_id=body.device_id,
        platform=body.platform,
        created_at=datetime.now(UTC),
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister FCM token",
    description=(
        "Remove the FCM token for the authenticated user's device.  "
        "Called on logout or when push notifications are disabled."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "User account is inactive"},
        422: {"description": "Validation error"},
    },
)
async def unregister_fcm_token(
    body: FCMTokenDeleteRequest,
    _user=Depends(get_current_active_user),
) -> None:
    """Unregister an FCM push-notification token for the current user.

    Placeholder implementation -- logs the removal without touching
    any persistent store.
    """
    logger.info(
        "FCM token unregistered (placeholder)",
        extra={
            "user_id": str(_user.id),
            "device_id": body.device_id,
        },
    )
    return None
