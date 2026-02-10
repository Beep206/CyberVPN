"""Bulk user action routes for VPN users."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.users.bulk_operations import BulkUserOperationsUseCase
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.users.schemas import BulkUserActionRequest, UserResponse
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/users/bulk", tags=["users"])


@router.post("/disable", response_model=list[UserResponse])
async def bulk_disable_users(
    request: BulkUserActionRequest,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> list[UserResponse]:
    """Disable multiple VPN user accounts."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        use_case = BulkUserOperationsUseCase(gateway=gateway)

        users = await use_case.disable_users(uuids=request.user_ids)

        return [
            UserResponse(
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
            for user in users
        ]
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable users: {str(e)}",
        )


@router.post("/enable", response_model=list[UserResponse])
async def bulk_enable_users(
    request: BulkUserActionRequest,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> list[UserResponse]:
    """Enable multiple VPN user accounts."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        use_case = BulkUserOperationsUseCase(gateway=gateway)

        users = await use_case.enable_users(uuids=request.user_ids)

        return [
            UserResponse(
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
            for user in users
        ]
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable users: {str(e)}",
        )
