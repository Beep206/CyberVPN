"""Trusted-admin Remnawave 3.4.3 control-plane operations.

Every provider mutation is protected by a durable stop-before-retry marker.
Known resources are read back after empty/ambiguous responses; creates use an
exact unique name where the upstream contract exposes one.  If authoritative
state cannot prove the requested postcondition, the attempt remains latched
for reconciliation and the provider mutation is never replayed blindly.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptDecision,
    RemnawaveMutationAttemptService,
    remnawave_create_sensitive_request_hash,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel
from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
)
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.dependencies.database import get_db

from .schemas import (
    AdminNodeIntegrationCollection,
    AdminSharedListPreviewCollection,
    AdminSnippetCollection,
    CreateNodeIntegrationRequest,
    GeoCheckJobResponse,
    GeoCheckRequest,
    GeoCheckResultResponse,
    MutableTagResource,
    NodeIntegration,
    NodeIntegrationCollection,
    OperatorMutationReceipt,
    SetTagsRequest,
    SetTagsResponse,
    SharedList,
    SharedListMutationRequest,
    SharedListNameRequest,
    SharedListPreviewCollection,
    Snippet,
    SnippetCollection,
    SnippetMutationRequest,
    SnippetNameRequest,
    TagResource,
    TagsResponse,
    UpdateNodeIntegrationRequest,
    UpstreamTagsResponse,
)

router = APIRouter(
    prefix="/admin/remnawave-operator",
    tags=["admin", "remnawave-operator"],
)

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=8, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$"),
]


@dataclass(frozen=True, slots=True)
class _GuardedOutcome[T: BaseModel]:
    record: ApiIdempotencyRecordModel
    value: T | None = None
    receipt: OperatorMutationReceipt | None = None


def _receipt(
    record: ApiIdempotencyRecordModel,
    *,
    resource_kind: str,
    state: Literal["accepted", "reconciliation_required"],
) -> OperatorMutationReceipt:
    if state not in {"accepted", "reconciliation_required"}:
        raise ValueError("unsupported mutation receipt state")
    return OperatorMutationReceipt(
        attempt_id=record.id,
        state=state,
        resource_kind=resource_kind,
        requires_reconciliation=state == "reconciliation_required",
    )


def _receipt_response(receipt: OperatorMutationReceipt) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=jsonable_encoder(receipt),
    )


def _is_definitive_rejection(exc: Exception) -> bool:
    return (
        isinstance(exc, RemnawaveHTTPStatusError)
        and 400 <= exc.response.status_code < 500
        and exc.response.status_code != status.HTTP_408_REQUEST_TIMEOUT
    )


async def _begin_attempt(
    *,
    db: AsyncSession,
    resource_kind: str,
    operation: str,
    idempotency_key: str,
    payload: dict[str, object],
) -> tuple[RemnawaveMutationAttemptService, RemnawaveCreateAttemptDecision]:
    service = RemnawaveMutationAttemptService(
        db,
        resource_type=f"remnawave_{resource_kind}_{operation}".replace("-", "_"),
    )
    try:
        decision = await service.begin(
            scope=f"remnawave-operator:{resource_kind}:{operation}",
            idempotency_key=idempotency_key,
            request_hash=remnawave_create_sensitive_request_hash(
                {
                    "operation": operation,
                    "resource_kind": resource_kind,
                    "payload": payload,
                }
            ),
        )
    except RemnawaveCreateAttemptConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "remnawave_operator_idempotency_conflict"},
        ) from exc
    return service, decision


async def _mark_reconciliation_required(
    service: RemnawaveMutationAttemptService,
    record: ApiIdempotencyRecordModel,
    *,
    resource_kind: str,
) -> _GuardedOutcome:
    if record.status != "reconciliation_required":
        await service.stage_reconciliation_required(record)
    if record.status == "completed":
        return _GuardedOutcome(
            record=record,
            receipt=_receipt(record, resource_kind=resource_kind, state="accepted"),
        )
    if record.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "remnawave_operator_attempt_rejected"},
        )
    if record.status != "reconciliation_required":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "remnawave_operator_attempt_state_conflict"},
        )
    return _GuardedOutcome(
        record=record,
        receipt=_receipt(
            record,
            resource_kind=resource_kind,
            state="reconciliation_required",
        ),
    )


async def _complete_attempt(
    *,
    db: AsyncSession,
    service: RemnawaveMutationAttemptService,
    record: ApiIdempotencyRecordModel,
    reference: dict[str, str | int | bool],
) -> None:
    await service.mark_completed_reference(record, reference=reference)


async def _guarded_resource_mutation[T: BaseModel](
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    resource_kind: str,
    operation: str,
    idempotency_key: str,
    payload: dict[str, object],
    mutate: Callable[[], Awaitable[T | None]],
    reconcile: Callable[[], Awaitable[T | None]],
    postcondition: Callable[[T], bool],
    completion_reference: Callable[[T], dict[str, str | int | bool]],
    ambiguous_reconciliation_is_authoritative: bool = True,
) -> _GuardedOutcome[T]:
    service, raw_decision = await _begin_attempt(
        db=db,
        resource_kind=resource_kind,
        operation=operation,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    decision = raw_decision
    record = decision.record

    if not decision.should_mutate:
        if record.status == "completed":
            try:
                current = await reconcile()
            except Exception:
                current = None
            if current is not None and postcondition(current):
                return _GuardedOutcome(record=record, value=current)
            return _GuardedOutcome(
                record=record,
                receipt=_receipt(record, resource_kind=resource_kind, state="accepted"),
            )
        if ambiguous_reconciliation_is_authoritative:
            try:
                reconciled = await reconcile()
            except Exception:
                reconciled = None
            if reconciled is not None and postcondition(reconciled):
                await _complete_attempt(
                    db=db,
                    service=service,
                    record=record,
                    reference=completion_reference(reconciled),
                )
                return _GuardedOutcome(record=record, value=reconciled)
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )

    try:
        result = await mutate()
    except Exception as exc:
        if _is_definitive_rejection(exc):
            await service.stage_rejected(record, error_code="provider_request_rejected")
            await _audit_outcome(
                db=db,
                request=request,
                actor=actor,
                record=record,
                resource_kind=resource_kind,
                operation=operation,
                state="rejected",
            )
            raise
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )

    if (result is None or not postcondition(result)) and ambiguous_reconciliation_is_authoritative:
        try:
            result = await reconcile()
        except Exception:
            result = None
    if result is None or not postcondition(result):
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )

    await _complete_attempt(
        db=db,
        service=service,
        record=record,
        reference=completion_reference(result),
    )
    return _GuardedOutcome(record=record, value=result)


async def _guarded_delete(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    resource_kind: str,
    idempotency_key: str,
    payload: dict[str, object],
    mutate: Callable[[], Awaitable[object]],
    exists: Callable[[], Awaitable[bool]],
    completion_reference: dict[str, str | int | bool],
) -> _GuardedOutcome[BaseModel]:
    service, raw_decision = await _begin_attempt(
        db=db,
        resource_kind=resource_kind,
        operation="delete",
        idempotency_key=idempotency_key,
        payload=payload,
    )
    decision = raw_decision
    record = decision.record
    if not decision.should_mutate:
        if record.status == "completed":
            return _GuardedOutcome(record=record)
        try:
            still_exists = await exists()
        except Exception:
            still_exists = True
        if not still_exists:
            await _complete_attempt(
                db=db,
                service=service,
                record=record,
                reference=completion_reference,
            )
            return _GuardedOutcome(record=record)
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )

    try:
        await mutate()
    except Exception as exc:
        if _is_definitive_rejection(exc):
            await service.stage_rejected(record, error_code="provider_request_rejected")
            await _audit_outcome(
                db=db,
                request=request,
                actor=actor,
                record=record,
                resource_kind=resource_kind,
                operation="delete",
                state="rejected",
            )
            raise
        try:
            still_exists = await exists()
        except Exception:
            still_exists = True
        if still_exists:
            return await _mark_reconciliation_required(
                service,
                record,
                resource_kind=resource_kind,
            )

    try:
        still_exists = await exists()
    except Exception:
        still_exists = True
    if still_exists:
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )
    await _complete_attempt(
        db=db,
        service=service,
        record=record,
        reference=completion_reference,
    )
    return _GuardedOutcome(record=record)


async def _guarded_accepted_action(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    resource_kind: str,
    operation: str,
    idempotency_key: str,
    payload: dict[str, object],
    mutate: Callable[[], Awaitable[object]],
    completion_reference: dict[str, str | int | bool],
) -> _GuardedOutcome[BaseModel]:
    service, raw_decision = await _begin_attempt(
        db=db,
        resource_kind=resource_kind,
        operation=operation,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    decision = raw_decision
    record = decision.record
    if not decision.should_mutate:
        if record.status == "completed":
            return _GuardedOutcome(
                record=record,
                receipt=_receipt(record, resource_kind=resource_kind, state="accepted"),
            )
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )
    try:
        await mutate()
    except Exception as exc:
        if _is_definitive_rejection(exc):
            await service.stage_rejected(record, error_code="provider_request_rejected")
            await _audit_outcome(
                db=db,
                request=request,
                actor=actor,
                record=record,
                resource_kind=resource_kind,
                operation=operation,
                state="rejected",
            )
            raise
        return await _mark_reconciliation_required(
            service,
            record,
            resource_kind=resource_kind,
        )
    await _complete_attempt(
        db=db,
        service=service,
        record=record,
        reference=completion_reference,
    )
    return _GuardedOutcome(
        record=record,
        receipt=_receipt(record, resource_kind=resource_kind, state="accepted"),
    )


async def _audit_outcome(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    record: ApiIdempotencyRecordModel,
    resource_kind: str,
    operation: str,
    state: str,
) -> None:
    await write_required_admin_audit_entry(
        db=db,
        action=f"remnawave_operator.{resource_kind}.{operation}.{state}",
        resource_type="remnawave_operator_attempt",
        resource_id=record.id,
        actor=actor,
        request=request,
        details={
            "attempt_id": str(record.id),
            "resource_kind": resource_kind,
            "operation": operation,
            "state": state,
        },
    )
    await db.commit()


async def _finalize_http_outcome[T: BaseModel](
    outcome: _GuardedOutcome[T],
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    resource_kind: str,
    operation: str,
) -> T | JSONResponse:
    state = outcome.receipt.state if outcome.receipt is not None else "completed"
    await _audit_outcome(
        db=db,
        request=request,
        actor=actor,
        record=outcome.record,
        resource_kind=resource_kind,
        operation=operation,
        state=state,
    )
    if outcome.receipt is not None:
        return _receipt_response(outcome.receipt)
    if outcome.value is None:
        raise RuntimeError("guarded resource mutation completed without a value")
    return outcome.value


async def _integration_by_uuid_or_none(
    client: RemnawaveClient,
    integration_uuid: UUID,
) -> NodeIntegration | None:
    try:
        return await client.get_validated(
            f"/node-integrations/{integration_uuid}",
            NodeIntegration,
        )
    except RemnawaveHTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            return None
        raise


async def _integration_by_exact_name(
    client: RemnawaveClient,
    name: str,
) -> NodeIntegration | None:
    collection = await client.get_validated(
        "/node-integrations",
        NodeIntegrationCollection,
    )
    matches = [item for item in collection.node_integrations if item.name == name]
    return matches[0] if len(matches) == 1 else None


async def _shared_list_or_none(client: RemnawaveClient, name: str) -> SharedList | None:
    try:
        return await client.get_validated(
            "/node-plugins/shared-lists/by-name",
            SharedList,
            params={"name": name},
        )
    except RemnawaveHTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            return None
        raise


async def _snippet_or_none(client: RemnawaveClient, name: str) -> Snippet | None:
    collection = await client.get_validated("/snippets", SnippetCollection)
    matches = [item for item in collection.snippets if item.name == name]
    return matches[0] if len(matches) == 1 else None


@router.get("/tags/{resource}", response_model=TagsResponse)
async def list_tags(
    resource: TagResource,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> TagsResponse:
    response = await client.get_validated(f"/{resource}/tags", UpstreamTagsResponse)
    return TagsResponse(resource=resource, tags=response.tags)


@router.patch(
    "/tags/{resource}",
    response_model=SetTagsResponse | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def set_tags(
    resource: MutableTagResource,
    body: SetTagsRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> SetTagsResponse | JSONResponse:
    payload = body.model_dump(mode="json")
    outcome = await _guarded_resource_mutation(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="tags",
        operation=f"set-{resource}",
        idempotency_key=idempotency_key,
        payload=payload,
        mutate=lambda: client.patch_validated(
            f"/{resource}/tags",
            SetTagsResponse,
            json=payload,
        ),
        reconcile=lambda: _no_reconciliation_result(),
        postcondition=lambda result: result.uuid == body.uuid and result.tags == body.tags,
        completion_reference=lambda result: {
            "resource_uuid": str(result.uuid),
            "tag_count": len(result.tags),
        },
    )
    return await _finalize_http_outcome(
        outcome,
        db=db,
        request=request,
        actor=current_user,
        resource_kind="tags",
        operation=f"set-{resource}",
    )


async def _no_reconciliation_result() -> None:
    return None


@router.post(
    "/geocheck/nodes/{node_uuid}",
    response_model=GeoCheckJobResponse | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def start_geocheck(
    node_uuid: UUID,
    body: GeoCheckRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> GeoCheckJobResponse | JSONResponse:
    payload = {"node_uuid": str(node_uuid), **body.model_dump(mode="json", exclude_none=True)}
    service, raw_decision = await _begin_attempt(
        db=db,
        resource_kind="geocheck",
        operation="start",
        idempotency_key=idempotency_key,
        payload=payload,
    )
    decision = raw_decision
    record = decision.record
    if decision.should_mutate:
        try:
            job = await client.post_validated(
                f"/connections/geocheck/{node_uuid}",
                GeoCheckJobResponse,
                json=body.model_dump(mode="json", exclude_none=True),
            )
        except Exception as exc:
            if _is_definitive_rejection(exc):
                await service.stage_rejected(record, error_code="provider_request_rejected")
                await _audit_outcome(
                    db=db,
                    request=request,
                    actor=current_user,
                    record=record,
                    resource_kind="geocheck",
                    operation="start",
                    state="rejected",
                )
                raise
            outcome: _GuardedOutcome[GeoCheckJobResponse] = await _mark_reconciliation_required(
                service,
                record,
                resource_kind="geocheck",
            )
        else:
            if job is None:
                outcome = await _mark_reconciliation_required(
                    service,
                    record,
                    resource_kind="geocheck",
                )
            else:
                await _complete_attempt(
                    db=db,
                    service=service,
                    record=record,
                    reference={"job_id": job.job_id, "node_uuid": str(node_uuid)},
                )
                outcome = _GuardedOutcome(record=record, value=job)
    elif record.status == "completed":
        reference = service.completed_reference(record) or {}
        job_id = reference.get("job_id")
        if not isinstance(job_id, str):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "remnawave_geocheck_receipt_invalid"},
            )
        outcome = _GuardedOutcome(
            record=record,
            value=GeoCheckJobResponse.model_validate({"jobId": job_id}),
        )
    else:
        outcome = await _mark_reconciliation_required(
            service,
            record,
            resource_kind="geocheck",
        )
    return await _finalize_http_outcome(
        outcome,
        db=db,
        request=request,
        actor=current_user,
        resource_kind="geocheck",
        operation="start",
    )


@router.get("/geocheck/jobs/{job_id}", response_model=GeoCheckResultResponse)
async def get_geocheck_result(
    job_id: str,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> GeoCheckResultResponse:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,255}", job_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid GeoCheck job id")
    return await client.get_validated(
        f"/connections/geocheck/{job_id}",
        GeoCheckResultResponse,
    )


@router.get("/node-integrations", response_model=AdminNodeIntegrationCollection)
async def list_node_integrations(
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> AdminNodeIntegrationCollection:
    collection = await client.get_validated("/node-integrations", NodeIntegrationCollection)
    return AdminNodeIntegrationCollection(total=collection.total, items=collection.node_integrations)


@router.post(
    "/node-integrations",
    response_model=NodeIntegration | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def create_node_integration(
    body: CreateNodeIntegrationRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodeIntegration | JSONResponse:
    payload = body.model_dump(mode="json", by_alias=True, exclude_none=True)

    def matches(item: NodeIntegration) -> bool:
        return item.name == body.name and item.description == body.description and item.config == body.config

    outcome = await _guarded_resource_mutation(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="node-integration",
        operation="create",
        idempotency_key=idempotency_key,
        payload=payload,
        mutate=lambda: client.post_validated(
            "/node-integrations",
            NodeIntegration,
            json=payload,
        ),
        reconcile=lambda: _integration_by_exact_name(client, body.name),
        postcondition=matches,
        completion_reference=lambda result: {"resource_uuid": str(result.uuid)},
    )
    return await _finalize_http_outcome(
        outcome,
        db=db,
        request=request,
        actor=current_user,
        resource_kind="node-integration",
        operation="create",
    )


@router.patch(
    "/node-integrations",
    response_model=NodeIntegration | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def update_node_integration(
    body: UpdateNodeIntegrationRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NodeIntegration | JSONResponse:
    payload = body.model_dump(mode="json", by_alias=True, exclude_unset=True)

    def matches(item: NodeIntegration) -> bool:
        fields = body.model_fields_set
        return (
            item.uuid == body.uuid
            and ("name" not in fields or item.name == body.name)
            and ("description" not in fields or item.description == body.description)
            and ("config" not in fields or item.config == body.config)
        )

    outcome = await _guarded_resource_mutation(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="node-integration",
        operation="update",
        idempotency_key=idempotency_key,
        payload=payload,
        mutate=lambda: client.patch_validated(
            "/node-integrations",
            NodeIntegration,
            json=payload,
        ),
        reconcile=lambda: _integration_by_uuid_or_none(client, body.uuid),
        postcondition=matches,
        completion_reference=lambda result: {"resource_uuid": str(result.uuid)},
        # A matching GET proves the integration fields, but it cannot prove
        # that the one-shot restartNodes side effect ran.  A latched attempt
        # must therefore remain reconciliation-required instead of being
        # falsely settled from resource readback.
        ambiguous_reconciliation_is_authoritative=body.restart_nodes is not True,
    )
    return await _finalize_http_outcome(
        outcome,
        db=db,
        request=request,
        actor=current_user,
        resource_kind="node-integration",
        operation="update",
    )


@router.delete(
    "/node-integrations/{integration_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def delete_node_integration(
    integration_uuid: UUID,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Response:
    async def exists() -> bool:
        return await _integration_by_uuid_or_none(client, integration_uuid) is not None

    outcome = await _guarded_delete(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="node-integration",
        idempotency_key=idempotency_key,
        payload={"resource_uuid": str(integration_uuid)},
        mutate=lambda: client.delete_validated(f"/node-integrations/{integration_uuid}"),
        exists=exists,
        completion_reference={"resource_uuid": str(integration_uuid), "deleted": True},
    )
    state = outcome.receipt.state if outcome.receipt else "completed"
    await _audit_outcome(
        db=db,
        request=request,
        actor=current_user,
        record=outcome.record,
        resource_kind="node-integration",
        operation="delete",
        state=state,
    )
    return _receipt_response(outcome.receipt) if outcome.receipt else Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/shared-lists", response_model=AdminSharedListPreviewCollection)
async def list_shared_lists(
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> AdminSharedListPreviewCollection:
    collection = await client.get_validated(
        "/node-plugins/shared-lists",
        SharedListPreviewCollection,
    )
    return AdminSharedListPreviewCollection(total=collection.total, items=collection.shared_lists)


@router.get("/shared-lists/by-name", response_model=SharedList)
async def get_shared_list(
    name: str = Query(min_length=2, max_length=255, pattern=r"^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*$"),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> SharedList:
    result = await _shared_list_or_none(client, name)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared list not found")
    return result


async def _mutate_shared_list(
    *,
    operation: str,
    body: SharedListMutationRequest,
    request: Request,
    idempotency_key: str,
    current_user: AdminUserModel,
    db: AsyncSession,
    client: RemnawaveClient,
) -> SharedList | JSONResponse:
    payload = body.model_dump(mode="json")
    outcome = await _guarded_resource_mutation(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="shared-list",
        operation=operation,
        idempotency_key=idempotency_key,
        payload=payload,
        mutate=lambda: (
            client.post_validated("/node-plugins/shared-lists", SharedList, json=payload)
            if operation == "create"
            else client.patch_validated("/node-plugins/shared-lists", SharedList, json=payload)
        ),
        reconcile=lambda: _shared_list_or_none(client, body.name),
        postcondition=lambda result: result.name == body.name and result.config == body.config,
        completion_reference=lambda result: {"resource_name": result.name},
    )
    return await _finalize_http_outcome(
        outcome,
        db=db,
        request=request,
        actor=current_user,
        resource_kind="shared-list",
        operation=operation,
    )


@router.post(
    "/shared-lists",
    response_model=SharedList | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def create_shared_list(
    body: SharedListMutationRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> SharedList | JSONResponse:
    return await _mutate_shared_list(
        operation="create",
        body=body,
        request=request,
        idempotency_key=idempotency_key,
        current_user=current_user,
        db=db,
        client=client,
    )


@router.patch(
    "/shared-lists",
    response_model=SharedList | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def update_shared_list(
    body: SharedListMutationRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> SharedList | JSONResponse:
    return await _mutate_shared_list(
        operation="update",
        body=body,
        request=request,
        idempotency_key=idempotency_key,
        current_user=current_user,
        db=db,
        client=client,
    )


@router.delete(
    "/shared-lists",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def delete_shared_list(
    body: SharedListNameRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Response:
    async def exists() -> bool:
        return await _shared_list_or_none(client, body.name) is not None

    outcome = await _guarded_delete(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="shared-list",
        idempotency_key=idempotency_key,
        payload={"resource_name": body.name},
        mutate=lambda: client.delete_validated(
            "/node-plugins/shared-lists",
            json=body.model_dump(mode="json"),
        ),
        exists=exists,
        completion_reference={"resource_name": body.name, "deleted": True},
    )
    state = outcome.receipt.state if outcome.receipt else "completed"
    await _audit_outcome(
        db=db,
        request=request,
        actor=current_user,
        record=outcome.record,
        resource_kind="shared-list",
        operation="delete",
        state=state,
    )
    return _receipt_response(outcome.receipt) if outcome.receipt else Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/shared-lists/actions/sync",
    response_model=OperatorMutationReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_shared_list(
    body: SharedListNameRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> JSONResponse:
    outcome = await _guarded_accepted_action(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="shared-list",
        operation="sync",
        idempotency_key=idempotency_key,
        payload={"resource_name": body.name},
        mutate=lambda: client.post_validated(
            "/node-plugins/shared-lists/actions/sync",
            OperatorMutationReceipt,
            json=body.model_dump(mode="json"),
        ),
        completion_reference={"resource_name": body.name, "accepted": True},
    )
    if outcome.receipt is None:
        raise RuntimeError("shared-list sync completed without an acceptance receipt")
    await _audit_outcome(
        db=db,
        request=request,
        actor=current_user,
        record=outcome.record,
        resource_kind="shared-list",
        operation="sync",
        state=outcome.receipt.state,
    )
    return _receipt_response(outcome.receipt)


@router.get("/snippets", response_model=AdminSnippetCollection)
async def list_snippets(
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> AdminSnippetCollection:
    collection = await client.get_validated("/snippets", SnippetCollection)
    return AdminSnippetCollection(total=collection.total, items=collection.snippets)


async def _mutate_snippet(
    *,
    operation: str,
    body: SnippetMutationRequest,
    request: Request,
    idempotency_key: str,
    current_user: AdminUserModel,
    db: AsyncSession,
    client: RemnawaveClient,
) -> Snippet | JSONResponse:
    payload = body.model_dump(mode="json")

    async def mutate() -> Snippet | None:
        collection = (
            await client.post_validated("/snippets", SnippetCollection, json=payload)
            if operation == "create"
            else await client.patch_validated("/snippets", SnippetCollection, json=payload)
        )
        if collection is None:
            return None
        matches = [item for item in collection.snippets if item.name == body.name]
        return matches[0] if len(matches) == 1 else None

    outcome = await _guarded_resource_mutation(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="snippet",
        operation=operation,
        idempotency_key=idempotency_key,
        payload=payload,
        mutate=mutate,
        reconcile=lambda: _snippet_or_none(client, body.name),
        postcondition=lambda result: result.name == body.name and result.snippet == body.snippet,
        completion_reference=lambda result: {"resource_name": result.name},
    )
    return await _finalize_http_outcome(
        outcome,
        db=db,
        request=request,
        actor=current_user,
        resource_kind="snippet",
        operation=operation,
    )


@router.post(
    "/snippets",
    response_model=Snippet | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def create_snippet(
    body: SnippetMutationRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Snippet | JSONResponse:
    return await _mutate_snippet(
        operation="create",
        body=body,
        request=request,
        idempotency_key=idempotency_key,
        current_user=current_user,
        db=db,
        client=client,
    )


@router.patch(
    "/snippets",
    response_model=Snippet | OperatorMutationReceipt,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def update_snippet(
    body: SnippetMutationRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Snippet | JSONResponse:
    return await _mutate_snippet(
        operation="update",
        body=body,
        request=request,
        idempotency_key=idempotency_key,
        current_user=current_user,
        db=db,
        client=client,
    )


@router.delete(
    "/snippets",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={202: {"model": OperatorMutationReceipt}},
)
async def delete_snippet(
    body: SnippetNameRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> Response:
    async def exists() -> bool:
        return await _snippet_or_none(client, body.name) is not None

    outcome = await _guarded_delete(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="snippet",
        idempotency_key=idempotency_key,
        payload={"resource_name": body.name},
        mutate=lambda: client.delete_validated("/snippets", json=body.model_dump(mode="json")),
        exists=exists,
        completion_reference={"resource_name": body.name, "deleted": True},
    )
    state = outcome.receipt.state if outcome.receipt else "completed"
    await _audit_outcome(
        db=db,
        request=request,
        actor=current_user,
        record=outcome.record,
        resource_kind="snippet",
        operation="delete",
        state=state,
    )
    return _receipt_response(outcome.receipt) if outcome.receipt else Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/snippets/actions/sync",
    response_model=OperatorMutationReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_snippet(
    body: SnippetNameRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> JSONResponse:
    outcome = await _guarded_accepted_action(
        db=db,
        request=request,
        actor=current_user,
        resource_kind="snippet",
        operation="sync",
        idempotency_key=idempotency_key,
        payload={"resource_name": body.name},
        mutate=lambda: client.post_validated(
            "/snippets/actions/sync",
            OperatorMutationReceipt,
            json=body.model_dump(mode="json"),
        ),
        completion_reference={"resource_name": body.name, "accepted": True},
    )
    if outcome.receipt is None:
        raise RuntimeError("snippet sync completed without an acceptance receipt")
    await _audit_outcome(
        db=db,
        request=request,
        actor=current_user,
        record=outcome.record,
        resource_kind="snippet",
        operation="sync",
        state=outcome.receipt.state,
    )
    return _receipt_response(outcome.receipt)
