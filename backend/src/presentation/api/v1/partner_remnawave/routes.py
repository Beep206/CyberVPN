"""Fail-closed partner views over explicitly granted Remnawave resources.

The partner API intentionally exposes the CyberVPN access ledger only. It is
not a generic Remnawave proxy and never returns provider payloads, topology,
credentials, tokens, integration identifiers, or SSH capabilities.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptDecision,
    RemnawaveMutationAttemptService,
    remnawave_create_sensitive_request_hash,
)
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.entities.partner_permission import PartnerPermission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel, PartnerAccountModel
from src.infrastructure.database.models.partner_role_model import PartnerRoleModel
from src.infrastructure.database.models.partner_workspace_profile_model import PartnerWorkspaceProfileModel
from src.infrastructure.database.models.remnawave_upgrade_model import PartnerRemnawaveResourceGrantModel
from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveProtocolError,
    RemnawaveTransportError,
)
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.api.v1.remnawave_operator.schemas import NodeIntegration, SetTagsResponse
from src.presentation.dependencies import get_remnawave_client
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    enforce_loaded_partner_workspace_permission,
    enforce_partner_remnawave_resource_grant,
    enforce_partner_workspace_permission,
    resolve_partner_workspace_access,
)

from .grant_queries import load_readable_partner_remnawave_grants

router = APIRouter(
    prefix="/partner-workspaces/{workspace_id}/remnawave",
    tags=["partner-remnawave"],
)


class PartnerRemnawaveResourceType(StrEnum):
    NODE = "node"
    HOST = "host"
    PROFILE = "profile"
    SQUAD = "squad"
    TAG = "tag"
    INTEGRATION = "integration"
    SHARED_LIST = "shared_list"
    SERVICE_IDENTITY = "service_identity"


class PartnerRemnawavePermission(StrEnum):
    READ = "remnawave_read"
    WRITE = "remnawave_write"
    EXECUTE = "remnawave_execute"


class PartnerRemnawaveOperation(StrEnum):
    INSPECT_ASSIGNMENT = "inspect_assignment"
    MUTATE_RESOURCE = "mutate_resource"
    EXECUTE_RESOURCE = "execute_resource"
    BROWSER_SSH = "browser_ssh"


class PartnerRemnawaveSafeMutation(StrEnum):
    PROFILE_TAGS = "profile_tags"
    INTEGRATION_METADATA = "integration_metadata"


class PartnerRemnawaveControlCapabilities(BaseModel):
    inspect_assignment: bool
    mutate_resource: bool
    execute_resource: bool
    browser_ssh: bool
    mutation_unavailable_reason: str
    safe_mutations: list[PartnerRemnawaveSafeMutation] = Field(default_factory=list)


class PartnerRemnawaveResourceResponse(BaseModel):
    workspace_id: UUID
    resource_type: PartnerRemnawaveResourceType
    resource_uuid: UUID
    effective_permissions: list[PartnerRemnawavePermission]
    available_operations: list[PartnerRemnawaveOperation]
    unavailable_operations: list[PartnerRemnawaveOperation]
    forbidden_operations: list[PartnerRemnawaveOperation]
    provider_details_available: bool
    safe_mutations: list[PartnerRemnawaveSafeMutation] = Field(default_factory=list)


class PartnerRemnawaveResourceListResponse(BaseModel):
    workspace_id: UUID
    items: list[PartnerRemnawaveResourceResponse]
    total: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)
    capabilities: PartnerRemnawaveControlCapabilities


class _PartnerMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


PartnerTagValue = Annotated[str, Field(min_length=1, max_length=36, pattern=r"^[A-Z0-9_:]+$")]


class PartnerProfileTagsMutationRequest(_PartnerMutationRequest):
    tags: list[PartnerTagValue] = Field(max_length=10)

    @model_validator(mode="after")
    def reject_duplicate_tags(self) -> PartnerProfileTagsMutationRequest:
        if len(self.tags) != len(set(self.tags)):
            raise ValueError("tags must be unique")
        return self


class PartnerProfileTagsMutationResponse(BaseModel):
    resource_uuid: UUID
    tags: list[PartnerTagValue] = Field(max_length=10)


class PartnerIntegrationMetadataMutationRequest(_PartnerMutationRequest):
    name: str | None = Field(default=None, min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_metadata_field(self) -> PartnerIntegrationMetadataMutationRequest:
        if not self.model_fields_set:
            raise ValueError("at least one integration metadata field is required")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("integration name cannot be null")
        return self


class PartnerIntegrationMetadataMutationResponse(BaseModel):
    resource_uuid: UUID
    name: str = Field(min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=255)


class PartnerRemnawaveMutationReceipt(BaseModel):
    attempt_id: UUID
    state: Literal["accepted", "reconciliation_required"]
    resource_type: PartnerRemnawaveResourceType
    resource_uuid: UUID
    requires_reconciliation: bool


PartnerIdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$"),
]


async def get_partner_remnawave_workspace_access(
    workspace_id: UUID,
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceAccess:
    """Resolve a partner workspace without exposing foreign workspace existence."""

    if current_realm.realm_type != "partner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner realm session required")
    try:
        access = await resolve_partner_workspace_access(
            workspace_id=workspace_id,
            current_user=current_user,
            db=db,
            allow_internal_admin_override=False,
        )
    except HTTPException as exc:
        if exc.status_code in {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Remnawave workspace not found",
            ) from exc
        raise

    await enforce_partner_workspace_permission(
        access=access,
        permission=PartnerPermission.REMNAWAVE_READ,
        current_user=current_user,
        db=db,
    )
    return access


def _effective_permissions(
    *,
    access: PartnerWorkspaceAccess,
    grant: PartnerRemnawaveResourceGrantModel,
) -> list[PartnerRemnawavePermission]:
    # A capability is effective only when both the member's explicit role and
    # the audited exact-object grant include it. Built-in roles intentionally
    # contain no Remnawave permissions.
    return [
        permission
        for permission in PartnerRemnawavePermission
        if permission.value in access.permission_keys and permission.value in grant.permission_keys
    ]


def _safe_mutations(
    *,
    access: PartnerWorkspaceAccess,
    grant: PartnerRemnawaveResourceGrantModel,
) -> list[PartnerRemnawaveSafeMutation]:
    if PartnerRemnawavePermission.WRITE not in _effective_permissions(access=access, grant=grant):
        return []
    if grant.resource_type == PartnerRemnawaveResourceType.PROFILE.value:
        return [PartnerRemnawaveSafeMutation.PROFILE_TAGS]
    if grant.resource_type == PartnerRemnawaveResourceType.INTEGRATION.value:
        return [PartnerRemnawaveSafeMutation.INTEGRATION_METADATA]
    return []


def _serialize_resource(
    *,
    access: PartnerWorkspaceAccess,
    grant: PartnerRemnawaveResourceGrantModel,
) -> PartnerRemnawaveResourceResponse:
    safe_mutations = _safe_mutations(access=access, grant=grant)
    return PartnerRemnawaveResourceResponse(
        workspace_id=access.workspace.id,
        resource_type=PartnerRemnawaveResourceType(grant.resource_type),
        resource_uuid=grant.resource_uuid,
        effective_permissions=_effective_permissions(access=access, grant=grant),
        available_operations=[
            PartnerRemnawaveOperation.INSPECT_ASSIGNMENT,
            *([PartnerRemnawaveOperation.MUTATE_RESOURCE] if safe_mutations else []),
        ],
        unavailable_operations=[
            *([] if safe_mutations else [PartnerRemnawaveOperation.MUTATE_RESOURCE]),
            PartnerRemnawaveOperation.EXECUTE_RESOURCE,
        ],
        forbidden_operations=[PartnerRemnawaveOperation.BROWSER_SSH],
        provider_details_available=False,
        safe_mutations=safe_mutations,
    )


def _control_capabilities(
    *,
    access: PartnerWorkspaceAccess,
    grants: list[PartnerRemnawaveResourceGrantModel],
) -> PartnerRemnawaveControlCapabilities:
    effective_safe_mutations = {
        mutation for grant in grants for mutation in _safe_mutations(access=access, grant=grant)
    }
    safe_mutations = [mutation for mutation in PartnerRemnawaveSafeMutation if mutation in effective_safe_mutations]
    can_mutate = bool(safe_mutations)
    return PartnerRemnawaveControlCapabilities(
        inspect_assignment=True,
        mutate_resource=can_mutate,
        execute_resource=False,
        browser_ssh=False,
        mutation_unavailable_reason=(
            "limited_to_explicit_profile_and_integration_grants"
            if can_mutate
            else "no_current_write_granted_safe_mutation"
        ),
        safe_mutations=safe_mutations,
    )


def _is_definitive_provider_rejection(exc: Exception) -> bool:
    return (
        isinstance(exc, RemnawaveHTTPStatusError)
        and 400 <= exc.response.status_code < 500
        and exc.response.status_code != status.HTTP_408_REQUEST_TIMEOUT
    )


def _is_upstream_validation_failure(exc: HTTPException) -> bool:
    return exc.status_code == status.HTTP_502_BAD_GATEWAY and exc.detail in {
        "Upstream service returned invalid response",
        "Upstream service returned invalid response format",
    }


def _raise_partner_provider_rejection(exc: RemnawaveHTTPStatusError) -> NoReturn:
    if exc.response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found") from exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Remnawave rejected the scoped partner mutation",
    ) from exc


async def _begin_partner_mutation_attempt(
    *,
    db: AsyncSession,
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    operation: PartnerRemnawaveSafeMutation,
    idempotency_key: str,
    payload: dict[str, object],
) -> tuple[RemnawaveMutationAttemptService, RemnawaveCreateAttemptDecision]:
    service = RemnawaveMutationAttemptService(
        db,
        resource_type=f"partner_remnawave_{operation.value}",
    )
    try:
        decision = await service.begin(
            scope=f"partner-remnawave:{operation.value}:{workspace_id}",
            idempotency_key=idempotency_key,
            request_hash=remnawave_create_sensitive_request_hash(
                {
                    "workspace_id": str(workspace_id),
                    "resource_type": resource_type.value,
                    "resource_uuid": str(resource_uuid),
                    "operation": operation.value,
                    "payload": payload,
                }
            ),
        )
    except RemnawaveCreateAttemptConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used for another partner mutation",
        ) from exc
    return service, decision


def _partner_mutation_receipt(
    record: ApiIdempotencyRecordModel,
    *,
    state: Literal["accepted", "reconciliation_required"],
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
) -> PartnerRemnawaveMutationReceipt:
    return PartnerRemnawaveMutationReceipt(
        attempt_id=record.id,
        state=state,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        requires_reconciliation=state == "reconciliation_required",
    )


def _partner_receipt_response(receipt: PartnerRemnawaveMutationReceipt) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=jsonable_encoder(receipt))


async def _audit_partner_mutation(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    operation: PartnerRemnawaveSafeMutation,
    record: ApiIdempotencyRecordModel,
    state: str,
) -> None:
    await write_required_admin_audit_entry(
        db=db,
        action=f"partner_remnawave.{operation.value}.{state}",
        resource_type="partner_remnawave_mutation_attempt",
        resource_id=record.id,
        actor=actor,
        request=request,
        details={
            "workspace_id": str(workspace_id),
            "resource_type": resource_type.value,
            "resource_uuid": str(resource_uuid),
            "operation": operation.value,
            "attempt_id": str(record.id),
            "state": state,
        },
    )
    await db.commit()


async def _mark_partner_reconciliation_required(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    operation: PartnerRemnawaveSafeMutation,
    service: RemnawaveMutationAttemptService,
    record: ApiIdempotencyRecordModel,
) -> JSONResponse:
    if record.status != "reconciliation_required":
        await service.stage_reconciliation_required(record)
    if record.status == "completed":
        return _partner_receipt_response(
            _partner_mutation_receipt(
                record,
                state="accepted",
                resource_type=resource_type,
                resource_uuid=resource_uuid,
            )
        )
    if record.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Remnawave mutation attempt was rejected",
        )
    if record.status != "reconciliation_required":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Remnawave mutation attempt state changed",
        )
    await _audit_partner_mutation(
        db=db,
        request=request,
        actor=actor,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        record=record,
        state="reconciliation_required",
    )
    return _partner_receipt_response(
        _partner_mutation_receipt(
            record,
            state="reconciliation_required",
            resource_type=resource_type,
            resource_uuid=resource_uuid,
        )
    )


async def _complete_partner_mutation(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    operation: PartnerRemnawaveSafeMutation,
    service: RemnawaveMutationAttemptService,
    record: ApiIdempotencyRecordModel,
    reference: dict[str, str | int | bool],
) -> None:
    await service.mark_completed_reference(record, reference=reference)
    await _audit_partner_mutation(
        db=db,
        request=request,
        actor=actor,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        record=record,
        state="completed",
    )


async def _reject_partner_mutation(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    operation: PartnerRemnawaveSafeMutation,
    service: RemnawaveMutationAttemptService,
    record: ApiIdempotencyRecordModel,
    exc: RemnawaveHTTPStatusError,
) -> NoReturn:
    await service.stage_rejected(record, error_code="provider_request_rejected")
    await _audit_partner_mutation(
        db=db,
        request=request,
        actor=actor,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        record=record,
        state="rejected",
    )
    _raise_partner_provider_rejection(exc)


async def _authorize_partner_mutation(
    *,
    access: PartnerWorkspaceAccess,
    current_user: AdminUserModel,
    db: AsyncSession,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
) -> PartnerRemnawaveResourceGrantModel:
    await enforce_partner_workspace_permission(
        access=access,
        permission=PartnerPermission.REMNAWAVE_WRITE,
        current_user=current_user,
        db=db,
    )
    grant = await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type=resource_type.value,
        resource_uuid=resource_uuid,
        permission=PartnerPermission.REMNAWAVE_WRITE,
        db=db,
    )
    # Profiles and integrations are global provider objects. A write grant is
    # safe only while exactly one active workspace owns the object; otherwise
    # a locally authorized PATCH would mutate another tenant's dependency.
    active_workspace_ids = (
        (
            await db.execute(
                select(PartnerRemnawaveResourceGrantModel.workspace_id)
                .where(
                    PartnerRemnawaveResourceGrantModel.resource_type == resource_type.value,
                    PartnerRemnawaveResourceGrantModel.resource_uuid == resource_uuid,
                    PartnerRemnawaveResourceGrantModel.revoked_at.is_(None),
                )
                .limit(2)
            )
        )
        .scalars()
        .all()
    )
    if active_workspace_ids != [access.workspace.id]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found")
    return grant


async def _lock_reserved_partner_mutation_ownership(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    access: PartnerWorkspaceAccess,
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    operation: PartnerRemnawaveSafeMutation,
    service: RemnawaveMutationAttemptService,
    decision: RemnawaveCreateAttemptDecision,
) -> None:
    """Linearize provider mutation with every mutable authorization row.

    ``begin`` intentionally commits the durable stop marker, so the initial
    authorization transaction cannot protect the later provider call. Lock
    order is workspace -> membership -> role -> workspace policy -> grant ->
    actor -> attempt. Admin grant paths start at grant and acquire only the
    audit actor FK afterwards, so no path takes these locks in reverse order.
    Revocation or reassignment therefore happens wholly before or after the
    provider mutation.
    """

    locked_workspace = (
        await db.execute(
            select(PartnerAccountModel)
            .where(PartnerAccountModel.id == workspace_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    locked_membership = (
        await db.execute(
            select(PartnerAccountUserModel)
            .where(
                PartnerAccountUserModel.partner_account_id == workspace_id,
                PartnerAccountUserModel.admin_user_id == actor.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    locked_role = None
    if locked_membership is not None:
        locked_role = (
            await db.execute(
                select(PartnerRoleModel)
                .where(PartnerRoleModel.id == locked_membership.role_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
    locked_profile = (
        await db.execute(
            select(PartnerWorkspaceProfileModel)
            .where(PartnerWorkspaceProfileModel.partner_account_id == workspace_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    active_grants = list(
        (
            await db.execute(
                select(PartnerRemnawaveResourceGrantModel)
                .where(
                    PartnerRemnawaveResourceGrantModel.resource_type == resource_type.value,
                    PartnerRemnawaveResourceGrantModel.resource_uuid == resource_uuid,
                    PartnerRemnawaveResourceGrantModel.revoked_at.is_(None),
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    grant = active_grants[0] if len(active_grants) == 1 else None
    locked_actor = (
        await db.execute(
            select(AdminUserModel)
            .where(AdminUserModel.id == actor.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()

    if (
        not access.is_internal_admin_override
        and access.workspace.id == workspace_id
        and locked_workspace is not None
        and locked_membership is not None
        and locked_membership.membership_status == "active"
        and locked_role is not None
        and locked_actor is not None
        and locked_actor.is_active
        and locked_actor.deleted_at is None
        and locked_actor.status == "active"
        and grant is not None
        and grant.workspace_id == workspace_id
        and PartnerPermission.REMNAWAVE_WRITE.value in locked_role.permission_keys
        and PartnerPermission.REMNAWAVE_WRITE.value in grant.permission_keys
    ):
        locked_access = PartnerWorkspaceAccess(
            workspace=locked_workspace,
            membership=locked_membership,
            role=locked_role,
            permission_keys=frozenset(locked_role.permission_keys),
            is_internal_admin_override=False,
        )
        try:
            enforce_loaded_partner_workspace_permission(
                access=locked_access,
                permission=PartnerPermission.REMNAWAVE_WRITE,
                current_user=locked_actor,
                profile=locked_profile,
            )
        except HTTPException:
            pass
        else:
            return

    if decision.should_mutate and decision.record.status == "pending":
        await service.stage_rejected(
            decision.record,
            error_code="authorization_changed_before_provider",
        )
        await _audit_partner_mutation(
            db=db,
            request=request,
            actor=actor,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=resource_uuid,
            operation=operation,
            record=decision.record,
            state="rejected",
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found")


async def _integration_or_none(client: RemnawaveClient, integration_uuid: UUID) -> NodeIntegration | None:
    try:
        return await client.get_validated(f"/node-integrations/{integration_uuid}", NodeIntegration)
    except RemnawaveHTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            return None
        raise


@router.get("/resources", response_model=PartnerRemnawaveResourceListResponse)
async def list_partner_remnawave_resources(
    workspace_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    db: AsyncSession = Depends(get_db),
) -> PartnerRemnawaveResourceListResponse:
    readable_grants = await load_readable_partner_remnawave_grants(
        db=db,
        workspace_id=access.workspace.id,
    )
    total = len(readable_grants)
    grants = readable_grants[offset : offset + limit]
    next_offset = offset + len(grants) if offset + len(grants) < total else None
    return PartnerRemnawaveResourceListResponse(
        workspace_id=workspace_id,
        items=[_serialize_resource(access=access, grant=grant) for grant in grants],
        total=total,
        next_offset=next_offset,
        capabilities=_control_capabilities(access=access, grants=readable_grants),
    )


@router.get(
    "/resources/{resource_type}/{resource_uuid}",
    response_model=PartnerRemnawaveResourceResponse,
)
async def get_partner_remnawave_resource(
    workspace_id: UUID,
    resource_type: PartnerRemnawaveResourceType,
    resource_uuid: UUID,
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    db: AsyncSession = Depends(get_db),
) -> PartnerRemnawaveResourceResponse:
    grant = await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type=resource_type.value,
        resource_uuid=resource_uuid,
        permission=PartnerPermission.REMNAWAVE_READ,
        db=db,
    )
    return _serialize_resource(access=access, grant=grant)


@router.patch(
    "/resources/profile/{resource_uuid}/tags",
    response_model=PartnerProfileTagsMutationResponse | PartnerRemnawaveMutationReceipt,
    responses={202: {"model": PartnerRemnawaveMutationReceipt}},
)
async def update_partner_profile_tags(
    workspace_id: UUID,
    resource_uuid: UUID,
    body: PartnerProfileTagsMutationRequest,
    request: Request,
    idempotency_key: PartnerIdempotencyKey,
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> PartnerProfileTagsMutationResponse | JSONResponse:
    """Update only tags on an exact granted profile; topology stays private."""

    resource_type = PartnerRemnawaveResourceType.PROFILE
    operation = PartnerRemnawaveSafeMutation.PROFILE_TAGS
    await _authorize_partner_mutation(
        access=access,
        current_user=current_user,
        db=db,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
    )
    payload: dict[str, object] = {"uuid": str(resource_uuid), "tags": body.tags}
    service, decision = await _begin_partner_mutation_attempt(
        db=db,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    await _lock_reserved_partner_mutation_ownership(
        db=db,
        request=request,
        actor=current_user,
        access=access,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        service=service,
        decision=decision,
    )
    if not decision.should_mutate:
        if decision.record.status == "pending":
            return await _mark_partner_reconciliation_required(
                db=db,
                request=request,
                actor=current_user,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_uuid=resource_uuid,
                operation=operation,
                service=service,
                record=decision.record,
            )
        state: Literal["accepted", "reconciliation_required"] = (
            "accepted" if decision.record.status == "completed" else "reconciliation_required"
        )
        return _partner_receipt_response(
            _partner_mutation_receipt(
                decision.record,
                state=state,
                resource_type=resource_type,
                resource_uuid=resource_uuid,
            )
        )

    try:
        result = await client.patch_validated(
            "/config-profiles/tags",
            SetTagsResponse,
            json=payload,
        )
    except RemnawaveHTTPStatusError as exc:
        if _is_definitive_provider_rejection(exc):
            await _reject_partner_mutation(
                db=db,
                request=request,
                actor=current_user,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_uuid=resource_uuid,
                operation=operation,
                service=service,
                record=decision.record,
                exc=exc,
            )
        return await _mark_partner_reconciliation_required(
            db=db,
            request=request,
            actor=current_user,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=resource_uuid,
            operation=operation,
            service=service,
            record=decision.record,
        )
    except (RemnawaveTransportError, RemnawaveProtocolError):
        return await _mark_partner_reconciliation_required(
            db=db,
            request=request,
            actor=current_user,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=resource_uuid,
            operation=operation,
            service=service,
            record=decision.record,
        )
    except HTTPException as exc:
        if not _is_upstream_validation_failure(exc):
            raise
        return await _mark_partner_reconciliation_required(
            db=db,
            request=request,
            actor=current_user,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=resource_uuid,
            operation=operation,
            service=service,
            record=decision.record,
        )

    if result is None or result.uuid != resource_uuid or result.tags != body.tags:
        return await _mark_partner_reconciliation_required(
            db=db,
            request=request,
            actor=current_user,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=resource_uuid,
            operation=operation,
            service=service,
            record=decision.record,
        )
    await _complete_partner_mutation(
        db=db,
        request=request,
        actor=current_user,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        service=service,
        record=decision.record,
        reference={"resource_uuid": str(resource_uuid), "tag_count": len(result.tags)},
    )
    return PartnerProfileTagsMutationResponse(resource_uuid=resource_uuid, tags=result.tags)


@router.patch(
    "/resources/integration/{resource_uuid}/metadata",
    response_model=PartnerIntegrationMetadataMutationResponse | PartnerRemnawaveMutationReceipt,
    responses={202: {"model": PartnerRemnawaveMutationReceipt}},
)
async def update_partner_integration_metadata(
    workspace_id: UUID,
    resource_uuid: UUID,
    body: PartnerIntegrationMetadataMutationRequest,
    request: Request,
    idempotency_key: PartnerIdempotencyKey,
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> PartnerIntegrationMetadataMutationResponse | JSONResponse:
    """Update allowlisted integration metadata without exposing config or restart controls."""

    resource_type = PartnerRemnawaveResourceType.INTEGRATION
    operation = PartnerRemnawaveSafeMutation.INTEGRATION_METADATA
    await _authorize_partner_mutation(
        access=access,
        current_user=current_user,
        db=db,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
    )
    payload: dict[str, object] = {"uuid": str(resource_uuid)}
    if "name" in body.model_fields_set:
        payload["name"] = body.name
    if "description" in body.model_fields_set:
        payload["description"] = body.description

    def matches(item: NodeIntegration | None) -> bool:
        return (
            item is not None
            and item.uuid == resource_uuid
            and ("name" not in body.model_fields_set or item.name == body.name)
            and ("description" not in body.model_fields_set or item.description == body.description)
        )

    def response(item: NodeIntegration) -> PartnerIntegrationMetadataMutationResponse:
        return PartnerIntegrationMetadataMutationResponse(
            resource_uuid=item.uuid,
            name=item.name,
            description=item.description,
        )

    service, decision = await _begin_partner_mutation_attempt(
        db=db,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    await _lock_reserved_partner_mutation_ownership(
        db=db,
        request=request,
        actor=current_user,
        access=access,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        service=service,
        decision=decision,
    )
    if not decision.should_mutate:
        try:
            current = await _integration_or_none(client, resource_uuid)
        except (RemnawaveHTTPStatusError, RemnawaveTransportError, RemnawaveProtocolError):
            current = None
        except HTTPException as exc:
            if not _is_upstream_validation_failure(exc):
                raise
            current = None
        if current is not None and matches(current):
            if decision.record.status != "completed":
                await _complete_partner_mutation(
                    db=db,
                    request=request,
                    actor=current_user,
                    workspace_id=workspace_id,
                    resource_type=resource_type,
                    resource_uuid=resource_uuid,
                    operation=operation,
                    service=service,
                    record=decision.record,
                    reference={"resource_uuid": str(resource_uuid)},
                )
            return response(current)
        if decision.record.status == "pending":
            return await _mark_partner_reconciliation_required(
                db=db,
                request=request,
                actor=current_user,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_uuid=resource_uuid,
                operation=operation,
                service=service,
                record=decision.record,
            )
        state: Literal["accepted", "reconciliation_required"] = (
            "accepted" if decision.record.status == "completed" else "reconciliation_required"
        )
        return _partner_receipt_response(
            _partner_mutation_receipt(
                decision.record,
                state=state,
                resource_type=resource_type,
                resource_uuid=resource_uuid,
            )
        )

    result: NodeIntegration | None
    try:
        result = await client.patch_validated(
            "/node-integrations",
            NodeIntegration,
            json=payload,
        )
    except RemnawaveHTTPStatusError as exc:
        if _is_definitive_provider_rejection(exc):
            await _reject_partner_mutation(
                db=db,
                request=request,
                actor=current_user,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_uuid=resource_uuid,
                operation=operation,
                service=service,
                record=decision.record,
                exc=exc,
            )
        result = None
    except (RemnawaveTransportError, RemnawaveProtocolError):
        result = None
    except HTTPException as exc:
        if not _is_upstream_validation_failure(exc):
            raise
        result = None

    if not matches(result):
        try:
            result = await _integration_or_none(client, resource_uuid)
        except (RemnawaveHTTPStatusError, RemnawaveTransportError, RemnawaveProtocolError):
            result = None
        except HTTPException as exc:
            if not _is_upstream_validation_failure(exc):
                raise
            result = None
    if result is None or not matches(result):
        return await _mark_partner_reconciliation_required(
            db=db,
            request=request,
            actor=current_user,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=resource_uuid,
            operation=operation,
            service=service,
            record=decision.record,
        )
    await _complete_partner_mutation(
        db=db,
        request=request,
        actor=current_user,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        operation=operation,
        service=service,
        record=decision.record,
        reference={"resource_uuid": str(resource_uuid)},
    )
    return response(result)


@router.post("/node-ssh/tickets", status_code=status.HTTP_403_FORBIDDEN)
async def reject_partner_browser_ssh(
    _access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
) -> None:
    """Make the partner SSH boundary explicit even for otherwise privileged grants."""

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Browser SSH is admin-only")
