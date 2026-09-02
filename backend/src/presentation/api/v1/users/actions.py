"""User action routes (enable/disable) for VPN users."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from src.application.use_cases.auth.permissions import Permission
from src.domain.enums import UserStatus
from src.domain.exceptions import UserNotFoundError
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.users.schemas import UserResponse
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: Annotated[int, Path(ge=1)],
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserResponse:
    """Disable a VPN user account."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        user = await gateway.update(RemnawaveUserRef(id=user_id), status=UserStatus.DISABLED)
        if user is None:
            raise UserNotFoundError(f"Remnawave user id {user_id} not found")

        return UserResponse(
            id=user.ref.require_numeric_id(),
            uuid=user.uuid,
            username=user.username,
            status=user.status,
            short_uuid=user.short_uuid,
            created_at=user.created_at,
            updated_at=user.updated_at,
            subscription_uuid=user.subscription_uuid,
            expire_at=user.expire_at,
            traffic_limit_bytes=user.traffic_limit_bytes,
            used_traffic_bytes=user.used_traffic_bytes,
            email=user.email,
            telegram_id=user.telegram_id,
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable user: {str(e)}",
        )


@router.post("/{user_id}/enable", response_model=UserResponse)
async def enable_user(
    user_id: Annotated[int, Path(ge=1)],
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserResponse:
    """Enable a VPN user account."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        user = await gateway.update(RemnawaveUserRef(id=user_id), status=UserStatus.ACTIVE)
        if user is None:
            raise UserNotFoundError(f"Remnawave user id {user_id} not found")

        return UserResponse(
            id=user.ref.require_numeric_id(),
            uuid=user.uuid,
            username=user.username,
            status=user.status,
            short_uuid=user.short_uuid,
            created_at=user.created_at,
            updated_at=user.updated_at,
            subscription_uuid=user.subscription_uuid,
            expire_at=user.expire_at,
            traffic_limit_bytes=user.traffic_limit_bytes,
            used_traffic_bytes=user.used_traffic_bytes,
            email=user.email,
            telegram_id=user.telegram_id,
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable user: {str(e)}",
        )
