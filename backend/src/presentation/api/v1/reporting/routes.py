from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.reporting import (
    ClaimOutboxPublicationsUseCase,
    GetOutboxEventUseCase,
    GetPartnerWorkspaceReportingApiSnapshotUseCase,
    ListOutboxEventsUseCase,
    ListOutboxPublicationsUseCase,
    MarkOutboxPublicationFailedUseCase,
    MarkOutboxPublicationPublishedUseCase,
    MarkOutboxPublicationSubmittedUseCase,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_reporting_token import require_partner_reporting_token
from src.presentation.dependencies.roles import require_role

from .schemas import (
    ClaimOutboxPublicationsRequest,
    ClaimOutboxPublicationsResponse,
    MarkOutboxPublicationFailedRequest,
    MarkOutboxPublicationPublishedRequest,
    MarkOutboxPublicationSubmittedRequest,
    OutboxEventResponse,
    OutboxPublicationResponse,
    PartnerReportingApiSnapshotResponse,
    PartnerReportingDeliveryLogResponse,
    PartnerReportingPostbackReadinessResponse,
)

router = APIRouter(prefix="/reporting", tags=["reporting"])


def _serialize_publication(model) -> OutboxPublicationResponse:
    return OutboxPublicationResponse(
        id=model.id,
        outbox_event_id=model.outbox_event_id,
        consumer_key=model.consumer_key,
        publication_status=model.publication_status,
        attempts=model.attempts,
        lease_owner=model.lease_owner,
        leased_until=model.leased_until,
        next_attempt_at=model.next_attempt_at,
        submitted_at=model.submitted_at,
        published_at=model.published_at,
        last_error=model.last_error,
        publication_payload=dict(model.publication_payload or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_event(model) -> OutboxEventResponse:
    return OutboxEventResponse(
        id=model.id,
        event_key=model.event_key,
        event_name=model.event_name,
        event_family=model.event_family,
        aggregate_type=model.aggregate_type,
        aggregate_id=model.aggregate_id,
        partition_key=model.partition_key,
        schema_version=model.schema_version,
        event_status=model.event_status,
        event_payload=dict(model.event_payload or {}),
        actor_context=dict(model.actor_context or {}),
        source_context=dict(model.source_context or {}),
        occurred_at=model.occurred_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        publications=[_serialize_publication(item) for item in model.publications],
    )


def _serialize_delivery_log(item) -> PartnerReportingDeliveryLogResponse:
    return PartnerReportingDeliveryLogResponse(
        id=item.id,
        channel=item.channel,
        status=item.status,
        destination=item.destination,
        last_attempt_at=item.last_attempt_at,
        notes=list(item.notes),
    )


def _serialize_postback_readiness(item) -> PartnerReportingPostbackReadinessResponse:
    return PartnerReportingPostbackReadinessResponse(
        status=item.status,
        delivery_status=item.delivery_status,
        scope_label=item.scope_label,
        credential_id=item.credential.id if item.credential is not None else None,
        notes=list(item.notes),
    )


@router.get("/outbox-events", response_model=list[OutboxEventResponse])
async def list_outbox_events(
    event_family: str | None = Query(None),
    event_name: str | None = Query(None),
    event_status: str | None = Query(None),
    aggregate_type: str | None = Query(None),
    aggregate_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[OutboxEventResponse]:
    items = await ListOutboxEventsUseCase(db).execute(
        event_family=event_family,
        event_name=event_name,
        event_status=event_status,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        limit=limit,
        offset=offset,
    )
    return [_serialize_event(item) for item in items]


@router.get("/outbox-events/{event_id}", response_model=OutboxEventResponse)
async def get_outbox_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> OutboxEventResponse:
    item = await GetOutboxEventUseCase(db).execute(outbox_event_id=event_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbox event not found")
    return _serialize_event(item)


@router.get("/outbox-publications", response_model=list[OutboxPublicationResponse])
async def list_outbox_publications(
    consumer_key: str | None = Query(None),
    publication_status: str | None = Query(None),
    outbox_event_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[OutboxPublicationResponse]:
    items = await ListOutboxPublicationsUseCase(db).execute(
        consumer_key=consumer_key,
        publication_status=publication_status,
        outbox_event_id=outbox_event_id,
        limit=limit,
        offset=offset,
    )
    return [_serialize_publication(item) for item in items]


@router.post("/outbox-publications/claim", response_model=ClaimOutboxPublicationsResponse)
async def claim_outbox_publications(
    payload: ClaimOutboxPublicationsRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> ClaimOutboxPublicationsResponse:
    result = await ClaimOutboxPublicationsUseCase(db).execute(
        consumer_key=payload.consumer_key,
        lease_owner=payload.lease_owner,
        batch_size=payload.batch_size,
        lease_seconds=payload.lease_seconds,
    )
    return ClaimOutboxPublicationsResponse(
        claimed_publications=[_serialize_publication(item) for item in result.claimed_publications]
    )


@router.post("/outbox-publications/{publication_id}/submitted", response_model=OutboxPublicationResponse)
async def mark_outbox_publication_submitted(
    publication_id: UUID,
    payload: MarkOutboxPublicationSubmittedRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> OutboxPublicationResponse:
    try:
        item = await MarkOutboxPublicationSubmittedUseCase(db).execute(
            publication_id=publication_id,
            lease_owner=payload.lease_owner,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_publication(item)


@router.post("/outbox-publications/{publication_id}/published", response_model=OutboxPublicationResponse)
async def mark_outbox_publication_published(
    publication_id: UUID,
    payload: MarkOutboxPublicationPublishedRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> OutboxPublicationResponse:
    try:
        item = await MarkOutboxPublicationPublishedUseCase(db).execute(
            publication_id=publication_id,
            lease_owner=payload.lease_owner,
            publication_payload=payload.publication_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_publication(item)


@router.post("/outbox-publications/{publication_id}/failed", response_model=OutboxPublicationResponse)
async def mark_outbox_publication_failed(
    publication_id: UUID,
    payload: MarkOutboxPublicationFailedRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> OutboxPublicationResponse:
    try:
        item = await MarkOutboxPublicationFailedUseCase(db).execute(
            publication_id=publication_id,
            lease_owner=payload.lease_owner,
            retry_after_seconds=payload.retry_after_seconds,
            error_message=payload.error_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_publication(item)


@router.get(
    "/partner-workspaces/{workspace_id}/snapshot",
    response_model=PartnerReportingApiSnapshotResponse,
)
async def get_partner_workspace_reporting_snapshot(
    workspace_id: UUID,
    token_access=Depends(require_partner_reporting_token),
    db: AsyncSession = Depends(get_db),
) -> PartnerReportingApiSnapshotResponse:
    snapshot = await GetPartnerWorkspaceReportingApiSnapshotUseCase(db).execute(
        partner_account_id=token_access.workspace_id,
        workspace_key=token_access.workspace_key,
        workspace_status=token_access.workspace_status,
        workspace_label=token_access.workspace_display_name,
    )
    return PartnerReportingApiSnapshotResponse(
        workspace_id=snapshot.workspace_id,
        workspace_key=snapshot.workspace_key,
        generated_at=snapshot.generated_at,
        partner_reporting_row=dict(snapshot.partner_reporting_row),
        consumer_health_views=[dict(item) for item in snapshot.consumer_health_views],
        delivery_logs=[_serialize_delivery_log(item) for item in snapshot.delivery_logs],
        postback_readiness=_serialize_postback_readiness(snapshot.postback_readiness),
    )
