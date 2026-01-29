"""User management routes for Remnawave VPN users."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dto.user_dto import CreateUserDTO
from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.users.create_user import CreateUserUseCase
from src.application.use_cases.users.delete_user import DeleteUserUseCase
from src.application.use_cases.users.get_user import GetUserUseCase
from src.application.use_cases.users.list_users import ListUsersUseCase
from src.application.use_cases.users.update_user import UpdateUserUseCase
from src.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.users.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
    UserListResponse,
)
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.pagination import get_pagination, PaginationParams
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    pagination: PaginationParams = Depends(get_pagination),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> UserListResponse:
    """List all VPN users with pagination."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        use_case = ListUsersUseCase(gateway=gateway)

        users = await use_case.execute(
            offset=pagination.page * pagination.page_size,
            limit=pagination.page_size,
        )

        return UserListResponse(
            users=[
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
            ],
            total=len(users),
            page=pagination.page,
            page_size=pagination.page_size,
        )
@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "User already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_user(
    request: CreateUserRequest,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_CREATE)),
) -> UserResponse:
    """Create a new VPN user."""
    try:
        gateway = RemnawaveUserGateway(client=client)

        use_case = CreateUserUseCase(gateway=gateway)

        dto = CreateUserDTO(
            username=request.username,
            password=request.password,
            email=request.email,
            data_limit=request.data_limit,
            expire_at=request.expire_at,
        )

        user = await use_case.execute(dto=dto)

        return UserResponse(
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
@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: UUID,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> UserResponse:
    """Get a specific VPN user by UUID."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        use_case = GetUserUseCase(gateway=gateway)

        user = await use_case.execute(uuid=user_id)

        if user is None:
            raise UserNotFoundError(f"User with UUID {user_id} not found")

        return UserResponse(
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
@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        404: {"description": "User not found"},
        422: {"description": "Validation error"},
    },
)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserResponse:
    """Update a VPN user."""
    try:
        gateway = RemnawaveUserGateway(client=client)

        use_case = UpdateUserUseCase(gateway=gateway)

        update_data = {}
        if request.username is not None:
            update_data["username"] = request.username
        if request.password is not None:
            update_data["password"] = request.password
        if request.email is not None:
            update_data["email"] = request.email
        if request.data_limit is not None:
            update_data["data_limit"] = request.data_limit
        if request.expire_at is not None:
            update_data["expire_at"] = request.expire_at

        user = await use_case.execute(uuid=user_id, **update_data)

        return UserResponse(
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
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "User not found"}},
)
async def delete_user(
    user_id: UUID,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_DELETE)),
):
    """Delete a VPN user."""
    try:
        gateway = RemnawaveUserGateway(client=client)
        use_case = DeleteUserUseCase(gateway=gateway)

        await use_case.execute(uuid=user_id)
        return None