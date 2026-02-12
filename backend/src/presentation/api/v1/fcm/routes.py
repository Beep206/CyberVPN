"""FCM token registration and removal endpoints.

Mobile clients call these endpoints to register or unregister Firebase
Cloud Messaging tokens so the backend can send push notifications.

Both endpoints require authentication -- the token is associated with
the currently authenticated user.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.fcm_token_repo import FCMTokenRepositoryImpl
from src.infrastructure.monitoring.metrics import fcm_operations_total
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

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
    db: AsyncSession = Depends(get_db),
) -> FCMTokenResponse:
    """Register an FCM push-notification token for the current user.

    Persists the token to the database using upsert (INSERT ... ON CONFLICT DO UPDATE).
    If a token already exists for this (user_id, device_id), it will be updated.
    """
    repo = FCMTokenRepositoryImpl(db)

    fcm_token = await repo.upsert(
        user_id=_user.id,
        token=body.token,
        device_id=body.device_id,
        platform=body.platform,
    )

    logger.info(
        "FCM token registered",
        extra={
            "user_id": str(_user.id),
            "device_id": body.device_id,
            "platform": body.platform,
        },
    )

    fcm_operations_total.labels(operation="register").inc()
    return FCMTokenResponse(
        token=fcm_token.token,
        device_id=fcm_token.device_id,
        platform=fcm_token.platform,
        created_at=fcm_token.created_at,
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
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unregister an FCM push-notification token for the current user.

    Deletes the token from the database. If the token doesn't exist, this
    operation is idempotent and returns successfully.
    """
    repo = FCMTokenRepositoryImpl(db)

    await repo.delete(
        user_id=_user.id,
        device_id=body.device_id,
    )

    fcm_operations_total.labels(operation="unregister").inc()
    logger.info(
        "FCM token unregistered",
        extra={
            "user_id": str(_user.id),
            "device_id": body.device_id,
        },
    )
    return None
