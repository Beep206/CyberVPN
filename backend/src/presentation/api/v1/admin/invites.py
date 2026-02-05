"""Admin invite token management endpoints (CRIT-1)."""

import logging

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from src.application.services.invite_service import InviteTokenService
from src.application.use_cases.auth.permissions import Permission
from src.domain.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_user
from src.presentation.dependencies.roles import require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/invites", tags=["admin", "invites"])


class CreateInviteRequest(BaseModel):
    """Request to create an invite token."""

    role: AdminRole = Field(
        default=AdminRole.VIEWER,
        description="Role to assign to the registered user",
    )
    email_hint: EmailStr | None = Field(
        default=None,
        description="Optional: Restrict invite to specific email address",
    )


class CreateInviteResponse(BaseModel):
    """Response containing the generated invite token."""

    token: str = Field(description="The invite token (UUID format)")
    role: str = Field(description="Role that will be assigned to the user")
    email_hint: str | None = Field(
        default=None,
        description="Email address restriction (if set)",
    )
    expires_in_hours: int = Field(description="Token expiry in hours")


class InviteTokenInfo(BaseModel):
    """Information about an invite token."""

    token: str
    role: str
    email_hint: str | None
    created_by: str
    created_at: str
    ttl_seconds: int


class ListInvitesResponse(BaseModel):
    """Response containing list of active invites."""

    invites: list[InviteTokenInfo]
    total: int


@router.post("", response_model=CreateInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    request: CreateInviteRequest,
    redis_client: redis.Redis = Depends(get_redis),
    current_user: AdminUserModel = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.MANAGE_INVITES)),
) -> CreateInviteResponse:
    """
    Create a new invite token for user registration.

    - Requires MANAGE_INVITES permission (ADMIN or SUPER_ADMIN role)
    - Tokens are single-use and expire after 24 hours by default
    - Optionally restrict invite to a specific email address
    """
    # Prevent creating invites for roles higher than own role
    role_hierarchy = [
        AdminRole.VIEWER,
        AdminRole.SUPPORT,
        AdminRole.OPERATOR,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
    ]
    # current_user.role is a string from DB, need to convert
    user_role = AdminRole(current_user.role)
    if role_hierarchy.index(request.role) > role_hierarchy.index(user_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create invite for role higher than your own.",
        )

    invite_service = InviteTokenService(redis_client)
    token = await invite_service.generate(
        created_by=str(current_user.id),
        role=request.role.value,
        email_hint=request.email_hint,
    )

    logger.info(
        "Invite token created",
        extra={
            "created_by": str(current_user.id),
            "role": request.role.value,
            "email_hint": request.email_hint,
        },
    )

    from src.config.settings import settings

    return CreateInviteResponse(
        token=token,
        role=request.role.value,
        email_hint=request.email_hint,
        expires_in_hours=settings.invite_token_expiry_hours,
    )


@router.get("", response_model=ListInvitesResponse)
async def list_invites(
    redis_client: redis.Redis = Depends(get_redis),
    _current_user: AdminUserModel = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.MANAGE_INVITES)),
) -> ListInvitesResponse:
    """
    List all active invite tokens.

    - Requires MANAGE_INVITES permission
    - Returns token details including remaining TTL
    """
    invite_service = InviteTokenService(redis_client)
    invites = await invite_service.list_active()

    return ListInvitesResponse(
        invites=[
            InviteTokenInfo(
                token=invite["token"],
                role=invite.get("role", "VIEWER"),
                email_hint=invite.get("email_hint"),
                created_by=invite.get("created_by", "unknown"),
                created_at=invite.get("created_at", ""),
                ttl_seconds=invite.get("ttl_seconds", 0),
            )
            for invite in invites
        ],
        total=len(invites),
    )


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    token: str,
    redis_client: redis.Redis = Depends(get_redis),
    _current_user: AdminUserModel = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.MANAGE_INVITES)),
) -> None:
    """
    Revoke an invite token.

    - Requires MANAGE_INVITES permission
    - Token will be immediately invalidated
    """
    invite_service = InviteTokenService(redis_client)
    deleted = await invite_service.revoke(token)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite token not found or already expired.",
        )
