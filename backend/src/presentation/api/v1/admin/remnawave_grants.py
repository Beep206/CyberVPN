"""Explicit object-level grants for partner Remnawave resources."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.application.services.remnawave_identity_retirement import (
    assert_remnawave_service_identity_grantable,
)
from src.application.use_cases.auth.permissions import Permission
from src.domain.entities.partner_permission import PartnerPermission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import PartnerRemnawaveResourceGrantModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

from .audit import write_required_admin_audit_entry

router = APIRouter(
    prefix="/admin/remnawave-resource-grants",
    tags=["admin", "remnawave-resource-grants"],
)

RemnawaveResourceType = Literal[
    "node",
    "host",
    "profile",
    "squad",
    "tag",
    "integration",
    "shared_list",
    "service_identity",
]
_EXCLUSIVE_RESOURCE_TYPES = frozenset({"node", "service_identity", "profile", "integration"})
_ALLOWED_PERMISSION_KEYS = frozenset(
    {
        PartnerPermission.REMNAWAVE_READ.value,
        PartnerPermission.REMNAWAVE_WRITE.value,
        PartnerPermission.REMNAWAVE_EXECUTE.value,
    }
)
_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 100
_MAX_CURSOR_LENGTH = 256
_INVALID_CURSOR_DETAIL = "Invalid Remnawave resource grant cursor"


class RemnawaveResourceGrantCreateRequest(BaseModel):
    workspace_id: UUID
    resource_type: RemnawaveResourceType
    resource_uuid: UUID
    permission_keys: list[str] = Field(min_length=1, max_length=4)
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("permission_keys")
    @classmethod
    def validate_permission_keys(cls, values: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        invalid = sorted(set(normalized) - _ALLOWED_PERMISSION_KEYS)
        if invalid:
            raise ValueError("Unsupported Remnawave partner permission")
        if not normalized:
            raise ValueError("At least one Remnawave partner permission is required")
        return normalized


class RemnawaveResourceGrantRevokeRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RemnawaveResourceGrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    resource_type: RemnawaveResourceType
    resource_uuid: UUID
    permission_keys: list[str]
    granted_by_admin_user_id: UUID
    granted_at: datetime
    revoked_by_admin_user_id: UUID | None
    revoked_at: datetime | None
    audit_reason: str


class RemnawaveResourceGrantListResponse(BaseModel):
    items: list[RemnawaveResourceGrantResponse]
    next_cursor: str | None = None


def _invalid_cursor_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=_INVALID_CURSOR_DETAIL,
    )


def _encode_grant_cursor(*, granted_at: datetime, grant_id: UUID) -> str:
    normalized_granted_at = granted_at.replace(tzinfo=UTC) if granted_at.tzinfo is None else granted_at.astimezone(UTC)
    payload = json.dumps(
        {
            "granted_at": normalized_granted_at.isoformat(timespec="microseconds"),
            "id": str(grant_id),
            "v": 1,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_grant_cursor(cursor: str) -> tuple[datetime, UUID]:
    if not cursor or len(cursor) > _MAX_CURSOR_LENGTH:
        raise _invalid_cursor_error()

    try:
        padding = "=" * (-len(cursor) % 4)
        raw_payload = base64.b64decode(
            cursor + padding,
            altchars=b"-_",
            validate=True,
        ).decode("utf-8")
        payload = json.loads(raw_payload)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _invalid_cursor_error() from exc

    if (
        not isinstance(payload, dict)
        or set(payload) != {"granted_at", "id", "v"}
        or not isinstance(payload.get("v"), int)
        or isinstance(payload.get("v"), bool)
        or payload["v"] != 1
        or not isinstance(payload.get("granted_at"), str)
        or not isinstance(payload.get("id"), str)
    ):
        raise _invalid_cursor_error()

    try:
        granted_at = datetime.fromisoformat(payload["granted_at"])
        grant_id = UUID(payload["id"])
    except ValueError as exc:
        raise _invalid_cursor_error() from exc
    if granted_at.tzinfo is None:
        raise _invalid_cursor_error()
    return granted_at.astimezone(UTC), grant_id


def _validate_page_size(limit: int) -> int:
    if not 1 <= limit <= _MAX_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"limit must be between 1 and {_MAX_PAGE_SIZE}",
        )
    return limit


@router.get("", response_model=RemnawaveResourceGrantListResponse)
async def list_remnawave_resource_grants(
    workspace_id: UUID | None = Query(default=None),
    include_revoked: bool = Query(default=False),
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    cursor: str | None = Query(default=None, min_length=1, max_length=_MAX_CURSOR_LENGTH),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.MANAGE_ADMINS)),
) -> RemnawaveResourceGrantListResponse:
    page_size = _validate_page_size(limit)
    statement = select(PartnerRemnawaveResourceGrantModel).order_by(
        PartnerRemnawaveResourceGrantModel.granted_at.desc(),
        PartnerRemnawaveResourceGrantModel.id.desc(),
    )
    if workspace_id is not None:
        statement = statement.where(PartnerRemnawaveResourceGrantModel.workspace_id == workspace_id)
    if not include_revoked:
        statement = statement.where(PartnerRemnawaveResourceGrantModel.revoked_at.is_(None))
    if cursor is not None:
        cursor_granted_at, cursor_id = _decode_grant_cursor(cursor)
        statement = statement.where(
            or_(
                PartnerRemnawaveResourceGrantModel.granted_at < cursor_granted_at,
                and_(
                    PartnerRemnawaveResourceGrantModel.granted_at == cursor_granted_at,
                    PartnerRemnawaveResourceGrantModel.id < cursor_id,
                ),
            )
        )
    rows = list((await db.execute(statement.limit(page_size + 1))).scalars().all())
    grants = rows[:page_size]
    next_cursor = None
    if len(rows) > page_size:
        last_grant = grants[-1]
        next_cursor = _encode_grant_cursor(
            granted_at=last_grant.granted_at,
            grant_id=last_grant.id,
        )
    return RemnawaveResourceGrantListResponse(
        items=[RemnawaveResourceGrantResponse.model_validate(grant) for grant in grants],
        next_cursor=next_cursor,
    )


@router.post("", response_model=RemnawaveResourceGrantResponse, status_code=status.HTTP_201_CREATED)
async def create_remnawave_resource_grant(
    body: RemnawaveResourceGrantCreateRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.MANAGE_ADMINS)),
) -> RemnawaveResourceGrantResponse:
    if body.resource_type == "service_identity":
        try:
            await assert_remnawave_service_identity_grantable(
                db,
                service_identity_id=body.resource_uuid,
            )
        except RemnawaveIdentityAccessConflict as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Service identity is not grantable",
            ) from exc
    existing = (
        await db.execute(
            select(PartnerRemnawaveResourceGrantModel).where(
                PartnerRemnawaveResourceGrantModel.workspace_id == body.workspace_id,
                PartnerRemnawaveResourceGrantModel.resource_type == body.resource_type,
                PartnerRemnawaveResourceGrantModel.resource_uuid == body.resource_uuid,
            )
        )
    ).scalar_one_or_none()
    if existing is not None and existing.revoked_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource grant already exists")
    if body.resource_type in _EXCLUSIVE_RESOURCE_TYPES:
        active_owner = (
            (
                await db.execute(
                    select(PartnerRemnawaveResourceGrantModel).where(
                        PartnerRemnawaveResourceGrantModel.resource_type == body.resource_type,
                        PartnerRemnawaveResourceGrantModel.resource_uuid == body.resource_uuid,
                        PartnerRemnawaveResourceGrantModel.revoked_at.is_(None),
                    )
                )
            )
            .scalars()
            .first()
        )
        if active_owner is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exclusive Remnawave resource is already granted",
            )

    now = datetime.now(UTC)
    if existing is None:
        grant = PartnerRemnawaveResourceGrantModel(
            workspace_id=body.workspace_id,
            resource_type=body.resource_type,
            resource_uuid=body.resource_uuid,
            permission_keys=body.permission_keys,
            granted_by_admin_user_id=current_user.id,
            granted_at=now,
            audit_reason=body.reason.strip(),
        )
        db.add(grant)
    else:
        grant = existing
        grant.permission_keys = body.permission_keys
        grant.granted_by_admin_user_id = current_user.id
        grant.granted_at = now
        grant.revoked_by_admin_user_id = None
        grant.revoked_at = None
        grant.audit_reason = body.reason.strip()

    try:
        await db.flush()
        await write_required_admin_audit_entry(
            db=db,
            action="partner_remnawave_resource_grant.issued",
            resource_type="partner_remnawave_resource_grant",
            resource_id=grant.id,
            actor=current_user,
            request=request,
            details={
                "workspace_id": body.workspace_id,
                "resource_type": body.resource_type,
                "resource_uuid": body.resource_uuid,
                "permission_keys": body.permission_keys,
                "reason": body.reason.strip(),
            },
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exclusive Remnawave resource is already granted",
        ) from exc
    await db.refresh(grant)
    return RemnawaveResourceGrantResponse.model_validate(grant)


@router.post("/{grant_id}/revoke", response_model=RemnawaveResourceGrantResponse)
async def revoke_remnawave_resource_grant(
    grant_id: UUID,
    body: RemnawaveResourceGrantRevokeRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.MANAGE_ADMINS)),
) -> RemnawaveResourceGrantResponse:
    grant = await db.get(PartnerRemnawaveResourceGrantModel, grant_id)
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource grant not found")
    if grant.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource grant is already revoked")

    grant.revoked_by_admin_user_id = current_user.id
    grant.revoked_at = datetime.now(UTC)
    grant.audit_reason = body.reason.strip()
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="partner_remnawave_resource_grant.revoked",
        resource_type="partner_remnawave_resource_grant",
        resource_id=grant.id,
        actor=current_user,
        request=request,
        details={
            "workspace_id": grant.workspace_id,
            "resource_type": grant.resource_type,
            "resource_uuid": grant.resource_uuid,
            "permission_keys": grant.permission_keys,
            "reason": body.reason.strip(),
        },
    )
    await db.commit()
    await db.refresh(grant)
    return RemnawaveResourceGrantResponse.model_validate(grant)
