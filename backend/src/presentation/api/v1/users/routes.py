"""User management routes for Remnawave VPN users."""

import logging
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Response, status
from httpx import HTTPStatusError, RequestError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.user_dto import CreateUserDTO
from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptService,
    remnawave_create_request_hash,
    remnawave_create_sensitive_request_hash,
)
from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.users.create_user import CreateUserUseCase
from src.application.use_cases.users.delete_user import DeleteUserUseCase
from src.application.use_cases.users.get_user import GetUserUseCase
from src.application.use_cases.users.list_users import ListUsersUseCase
from src.application.use_cases.users.update_user import UpdateUserUseCase
from src.domain.exceptions import UserNotFoundError
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.monitoring.metrics import user_management_total
from src.infrastructure.remnawave.user_gateway import (
    RemnawaveIdentityBindingError,
    RemnawaveMutationAcceptedPending,
    RemnawaveUserGateway,
)
from src.presentation.api.v1.users.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.pagination import PaginationParams, get_pagination
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    pagination: PaginationParams = Depends(get_pagination),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> UserListResponse:
    """List all VPN users with pagination."""
    gateway = RemnawaveUserGateway(client=client)
    use_case = ListUsersUseCase(gateway=gateway)

    users = await use_case.execute(
        offset=pagination.page * pagination.page_size,
        limit=pagination.page_size,
    )

    user_management_total.labels(operation="list", status="success").inc()
    return UserListResponse(
        users=[
            UserResponse(
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
        202: {"description": "Creation accepted; authoritative identity reconciliation is required"},
        409: {"description": "User already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_user(
    request: CreateUserRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=160)],
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_CREATE)),
) -> UserResponse | Response:
    """Create a new VPN user."""
    gateway = RemnawaveUserGateway(client=client)
    use_case = CreateUserUseCase(gateway=gateway)
    normalized_username = request.username.strip()
    normalized_email = str(request.email).strip().casefold() if request.email is not None else None
    dto = CreateUserDTO(
        username=normalized_username,
        password=request.password,
        email=normalized_email,
        data_limit=request.data_limit,
        expire_at=request.expire_at,
    )

    attempts = RemnawaveCreateAttemptService(db)
    try:
        decision = await attempts.begin(
            scope="remnawave-user:create",
            idempotency_key=remnawave_create_request_hash({"client_idempotency_key": idempotency_key.strip()}),
            request_hash=remnawave_create_sensitive_request_hash(
                {
                    "username": normalized_username,
                    "password": request.password,
                    "email": normalized_email,
                    "data_limit": request.data_limit,
                    "expire_at": (
                        request.expire_at.astimezone(UTC).isoformat()
                        if request.expire_at is not None and request.expire_at.tzinfo is not None
                        else request.expire_at.isoformat()
                        if request.expire_at is not None
                        else None
                    ),
                }
            ),
        )
    except RemnawaveCreateAttemptConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not decision.should_mutate:
        completed_ref = attempts.completed_ref(decision.record)
        if completed_ref is None:
            user_management_total.labels(operation="create", status="reconciliation_required").inc()
            return Response(
                status_code=status.HTTP_202_ACCEPTED,
                headers={"Retry-After": "30"},
            )
        user = await gateway.get_by_ref(completed_ref)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed Remnawave create no longer resolves to its exact provider identity",
            )
    else:
        try:
            user = await use_case.execute(dto=dto)
        except (
            RemnawaveMutationAcceptedPending,
            RemnawaveIdentityBindingError,
            RequestError,
            HTTPStatusError,
        ):
            await attempts.mark_reconciliation_required(decision.record)
            user_management_total.labels(operation="create", status="reconciliation_required").inc()
            return Response(
                status_code=status.HTTP_202_ACCEPTED,
                headers={"Retry-After": "30"},
            )
        await attempts.mark_completed(decision.record, user_ref=user.ref)
        await db.commit()

    user_management_total.labels(operation="create", status="success").inc()
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


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: Annotated[int, Path(ge=1)],
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> UserResponse:
    """Get a specific VPN user by numeric Remnawave id."""
    gateway = RemnawaveUserGateway(client=client)
    use_case = GetUserUseCase(gateway=gateway)

    user = await use_case.execute(user_id=user_id)

    if user is None:
        raise UserNotFoundError(f"Remnawave user id {user_id} not found")

    user_management_total.labels(operation="get", status="success").inc()
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


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        404: {"description": "User not found"},
        422: {"description": "Validation error"},
    },
)
async def update_user(
    user_id: Annotated[int, Path(ge=1)],
    request: UpdateUserRequest,
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserResponse:
    """Update a VPN user."""
    gateway = RemnawaveUserGateway(client=client)

    use_case = UpdateUserUseCase(gateway=gateway)

    update_data: dict[str, object] = {}
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

    user = await use_case.execute(user_ref=RemnawaveUserRef(id=user_id), **update_data)

    user_management_total.labels(operation="update", status="success").inc()
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


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "User not found"}},
)
async def delete_user(
    user_id: Annotated[int, Path(ge=1)],
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_DELETE)),
):
    """Delete a VPN user."""
    gateway = RemnawaveUserGateway(client=client)
    use_case = DeleteUserUseCase(gateway=gateway)

    await use_case.execute(user_ref=RemnawaveUserRef(id=user_id))
    user_management_total.labels(operation="delete", status="success").inc()
    return None
