"""Tenant-safe Remnawave connection operations for admin, partner and customer UIs."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from math import ceil
from typing import Literal, NoReturn
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_mobile_user_ref,
    resolve_exact_mapped_remnawave_ref,
)
from src.application.use_cases.auth.permissions import check_minimum_role
from src.config.settings import settings
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveProtocolError,
    RemnawaveTransportError,
)
from src.infrastructure.remnawave.connections_gateway import (
    RemnawaveConnectionDropCommand,
    RemnawaveConnectionIp,
    RemnawaveConnectionsGateway,
    RemnawaveConnectionsInvalidResponseError,
    RemnawaveDropByUserIds,
    RemnawaveDropOnAllNodes,
    RemnawaveNodeConnectionsJobResult,
    RemnawaveUserConnectionsJobResult,
)
from src.presentation.api.v1.partner_remnawave.grant_queries import load_readable_partner_remnawave_grants
from src.presentation.api.v1.partner_remnawave.routes import get_partner_remnawave_workspace_access
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.dependencies.auth import get_current_active_web_user, get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    enforce_partner_remnawave_resource_grant,
    enforce_partner_workspace_permission,
)

from .audit import (
    RemnawaveConnectionDropAuditContext,
    RemnawaveConnectionDropAuditUnavailableError,
    persist_privileged_connection_drop_audit,
    validate_privileged_connection_drop_audit_configuration,
)
from .drop_receipts import (
    RemnawaveConnectionDropReceiptConflictError,
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropReceiptRegistry,
    RemnawaveConnectionDropReceiptUnavailableError,
    RemnawaveConnectionDropState,
    configured_connection_drop_hmac_secret,
)
from .job_registry import (
    RemnawaveConnectionJobAudience,
    RemnawaveConnectionJobKind,
    RemnawaveConnectionJobNotFoundError,
    RemnawaveConnectionJobRecord,
    RemnawaveConnectionJobRegistry,
    RemnawaveConnectionJobRegistryUnavailableError,
)
from .reconciliation import (
    RECEIPT_ID_PATTERN,
    RemnawaveConnectionDropReconciliationConflictError,
    RemnawaveConnectionDropReconciliationNotFoundError,
    RemnawaveConnectionDropReconciliationReason,
    RemnawaveConnectionDropReconciliationService,
    RemnawaveConnectionDropReconciliationUnavailableError,
)
from .schemas import (
    AdminRemnawaveConnectionDropReceiptResponse,
    AdminRemnawaveConnectionDropReconciliationRequest,
    AdminRemnawaveConnectionDropRequest,
    AdminRemnawaveConnectionDropUnresolvedPageResponse,
    AdminRemnawaveConnectionIpResponse,
    AdminRemnawaveNodeConnectionsResultResponse,
    AdminRemnawaveNodeConnectionsStatusResponse,
    AdminRemnawaveNodeConnectionUserResponse,
    AdminRemnawaveUserConnectionNodeResponse,
    AdminRemnawaveUserConnectionsResultResponse,
    AdminRemnawaveUserConnectionsStatusResponse,
    CustomerRemnawaveConnectionsStatusResponse,
    PartnerRemnawaveConnectionDropRequest,
    PartnerRemnawaveNodeConnectionsStatusResponse,
    RemnawaveConnectionDropReceiptResponse,
    RemnawaveConnectionProgressResponse,
    RemnawaveConnectionReadRequestResponse,
    RemnawaveConnectionsCapabilitiesResponse,
)

router = APIRouter(tags=["remnawave-connections"])

_REQUEST_ID_PATH = Path(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")
_RECEIPT_ID_PATH = Path(min_length=43, max_length=43, pattern=RECEIPT_ID_PATTERN)
_IDEMPOTENCY_KEY_HEADER = Header(
    min_length=16,
    max_length=128,
    pattern=r"^[A-Za-z0-9._:-]{16,128}$",
    alias="Idempotency-Key",
)


def get_remnawave_connections_gateway(
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> RemnawaveConnectionsGateway:
    return RemnawaveConnectionsGateway(client)


def get_remnawave_connection_job_registry(
    redis_client: redis.Redis = Depends(get_redis),
) -> RemnawaveConnectionJobRegistry:
    return RemnawaveConnectionJobRegistry(redis_client)


def get_remnawave_connection_drop_receipt_registry(
    db: AsyncSession = Depends(get_db),
) -> RemnawaveConnectionDropReceiptRegistry:
    try:
        return RemnawaveConnectionDropReceiptRegistry(
            db,
            hmac_secret=configured_connection_drop_hmac_secret(),
            terminal_ttl_seconds=settings.remnawave_connection_drop_terminal_ttl_seconds,
            max_active_receipts=settings.remnawave_connection_drop_max_active_receipts,
            max_active_per_actor=settings.remnawave_connection_drop_max_active_per_actor,
            max_pending_per_actor=settings.remnawave_connection_drop_max_pending_per_actor,
            cleanup_batch_size=settings.remnawave_connection_drop_cleanup_batch_size,
        )
    except RemnawaveConnectionDropReceiptUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection drop receipt registry is temporarily unavailable",
        ) from exc


def get_remnawave_connection_drop_reconciliation_service(
    db: AsyncSession = Depends(get_db),
) -> RemnawaveConnectionDropReconciliationService:
    # Deliberately independent of the HMAC secret: an operator must still be
    # able to resolve durable tombstones during secret recovery or rotation.
    return RemnawaveConnectionDropReconciliationService(
        db,
        terminal_ttl_seconds=settings.remnawave_connection_drop_terminal_ttl_seconds,
    )


def _raise_provider_failure(
    exc: RemnawaveHTTPStatusError
    | RemnawaveTransportError
    | RemnawaveProtocolError
    | RemnawaveConnectionsInvalidResponseError,
) -> NoReturn:
    if isinstance(exc, RemnawaveConnectionsInvalidResponseError | RemnawaveProtocolError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Remnawave returned an invalid connections response",
        ) from exc
    if isinstance(exc, RemnawaveHTTPStatusError) and exc.response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remnawave connection target not found",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Remnawave connections are temporarily unavailable",
    ) from exc


async def _issue_job(
    *,
    registry: RemnawaveConnectionJobRegistry,
    record: RemnawaveConnectionJobRecord,
    capabilities: RemnawaveConnectionsCapabilitiesResponse,
) -> RemnawaveConnectionReadRequestResponse:
    try:
        request_id = await registry.issue(record)
    except RemnawaveConnectionJobRegistryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection request registry is temporarily unavailable",
        ) from exc
    return RemnawaveConnectionReadRequestResponse(request_id=request_id, capabilities=capabilities)


def _drop_receipt_runtime_available() -> bool:
    try:
        configured_connection_drop_hmac_secret()
    except RemnawaveConnectionDropReceiptUnavailableError:
        return False
    return True


def _connections_capabilities(*, drop_connections: bool) -> RemnawaveConnectionsCapabilitiesResponse:
    return RemnawaveConnectionsCapabilitiesResponse(drop_connections=drop_connections)


def _admin_drop_available(current_user: AdminUserModel) -> bool:
    try:
        role = AdminRole(current_user.role)
    except (AttributeError, ValueError):
        return False
    return check_minimum_role(role, AdminRole.ADMIN) and _drop_receipt_runtime_available()


def _drop_receipt_response(
    record: RemnawaveConnectionDropReceiptRecord,
) -> RemnawaveConnectionDropReceiptResponse:
    if record.state is RemnawaveConnectionDropState.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Remnawave rejected the connection drop",
        )
    public_state: Literal["accepted", "outcome_unknown"] = (
        "accepted" if record.state is RemnawaveConnectionDropState.ACCEPTED else "outcome_unknown"
    )
    if public_state == "outcome_unknown":
        return RemnawaveConnectionDropReceiptResponse(
            receipt_id=record.receipt_id,
            state=public_state,
            requires_reconciliation=True,
            expires_at=None,
            expires_in_seconds=None,
        )
    if record.expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection drop receipt registry is temporarily unavailable",
        )
    expires_at = record.expires_at.astimezone(UTC)
    # Database/application clocks can differ by a fraction of a second. Clamp
    # the public remaining TTL instead of leaking a negative value or reviving
    # an already elapsed terminal window.
    expires_in_seconds = max(0, ceil((expires_at - datetime.now(UTC)).total_seconds()))
    return RemnawaveConnectionDropReceiptResponse(
        receipt_id=record.receipt_id,
        state=public_state,
        requires_reconciliation=False,
        expires_at=expires_at,
        expires_in_seconds=expires_in_seconds,
    )


def _admin_reconciliation_receipt_response(
    record: RemnawaveConnectionDropReceiptRecord,
    *,
    now: datetime | None = None,
) -> AdminRemnawaveConnectionDropReceiptResponse:
    expires_at = record.expires_at.astimezone(UTC) if record.expires_at is not None else None
    expires_in_seconds = (
        max(0, ceil((expires_at - (now or datetime.now(UTC))).total_seconds())) if expires_at is not None else None
    )
    try:
        reason = (
            RemnawaveConnectionDropReconciliationReason(record.reconciliation_reason)
            if record.reconciliation_reason is not None
            else None
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection drop reconciliation receipt is invalid",
        ) from exc
    return AdminRemnawaveConnectionDropReceiptResponse(
        receipt_id=record.receipt_id,
        state=record.state.value,
        audience=record.audience.value,
        created_at=record.created_at,
        updated_at=record.updated_at,
        expires_at=expires_at,
        expires_in_seconds=expires_in_seconds,
        requires_reconciliation=record.state is RemnawaveConnectionDropState.OUTCOME_UNKNOWN,
        reconciled_at=record.reconciled_at,
        reconciliation_reason=reason,
        reconciliation_reference=record.reconciliation_reference,
    )


def _raise_reconciliation_failure(
    exc: RemnawaveConnectionDropReconciliationNotFoundError
    | RemnawaveConnectionDropReconciliationConflictError
    | RemnawaveConnectionDropReconciliationUnavailableError,
) -> NoReturn:
    if isinstance(exc, RemnawaveConnectionDropReconciliationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection drop receipt not found") from exc
    if isinstance(exc, RemnawaveConnectionDropReconciliationConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Connection drop receipt already has an immutable terminal outcome",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Connection drop reconciliation is temporarily unavailable",
    ) from exc


async def _execute_connection_drop(
    *,
    audience: RemnawaveConnectionJobAudience,
    actor_id: UUID,
    workspace_id: UUID | None = None,
    scope: str,
    client_idempotency_key: str,
    command: RemnawaveConnectionDropCommand,
    gateway: RemnawaveConnectionsGateway,
    receipts: RemnawaveConnectionDropReceiptRegistry,
    audit_context: RemnawaveConnectionDropAuditContext | None = None,
) -> RemnawaveConnectionDropReceiptResponse:
    if audit_context is not None:
        try:
            validate_privileged_connection_drop_audit_configuration(command)
        except RemnawaveConnectionDropAuditUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Connection drop audit is temporarily unavailable",
            ) from exc
    try:
        reservation = await receipts.reserve(
            audience=audience,
            actor_id=actor_id,
            workspace_id=workspace_id,
            scope=scope,
            client_idempotency_key=client_idempotency_key,
            payload=command.canonical_payload(),
        )
    except RemnawaveConnectionDropReceiptConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different connection drop",
        ) from exc
    except RemnawaveConnectionDropReceiptUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection drop receipt registry is temporarily unavailable",
        ) from exc

    if not reservation.is_new:
        return await _finalize_connection_drop(
            audience=audience,
            command=command,
            record=reservation.record,
            audit_context=audit_context,
        )

    try:
        await gateway.drop_once(command)
    except (RemnawaveTransportError, RemnawaveProtocolError):
        # The request may already have been applied upstream. The receipt was
        # reserved as outcome_unknown before I/O and forbids another send.
        return await _finalize_connection_drop(
            audience=audience,
            command=command,
            record=reservation.record,
            audit_context=audit_context,
        )
    except RemnawaveHTTPStatusError as exc:
        if exc.response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            return await _finalize_connection_drop(
                audience=audience,
                command=command,
                record=reservation.record,
                audit_context=audit_context,
            )
        try:
            rejected = await receipts.update_state(
                reservation,
                RemnawaveConnectionDropState.REJECTED,
            )
        except RemnawaveConnectionDropReceiptUnavailableError:
            # The provider rejection is definitive, but the durable receipt is
            # still the canonical source. Never fabricate a terminal audit or
            # response that contradicts its persisted ambiguous state.
            return await _finalize_connection_drop(
                audience=audience,
                command=command,
                record=reservation.record,
                audit_context=audit_context,
            )
        return await _finalize_connection_drop(
            audience=audience,
            command=command,
            record=rejected,
            audit_context=audit_context,
        )

    try:
        accepted = await receipts.update_state(
            reservation,
            RemnawaveConnectionDropState.ACCEPTED,
        )
    except RemnawaveConnectionDropReceiptUnavailableError:
        # Provider acknowledgement was lost locally. Conservatively expose the
        # already durable unknown receipt and never send the command again.
        return await _finalize_connection_drop(
            audience=audience,
            command=command,
            record=reservation.record,
            audit_context=audit_context,
        )
    return await _finalize_connection_drop(
        audience=audience,
        command=command,
        record=accepted,
        audit_context=audit_context,
    )


async def _finalize_connection_drop(
    *,
    audience: RemnawaveConnectionJobAudience,
    command: RemnawaveConnectionDropCommand,
    record: RemnawaveConnectionDropReceiptRecord,
    audit_context: RemnawaveConnectionDropAuditContext | None,
) -> RemnawaveConnectionDropReceiptResponse:
    if audit_context is not None:
        try:
            await persist_privileged_connection_drop_audit(
                context=audit_context,
                audience=audience,
                command=command,
                payload_hmac=record.payload_hmac,
                receipt=record,
            )
        except RemnawaveConnectionDropAuditUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Connection drop audit is temporarily unavailable",
            ) from exc
    return _drop_receipt_response(record)


async def _load_scoped_job(
    *,
    registry: RemnawaveConnectionJobRegistry,
    request_id: str,
    audience: RemnawaveConnectionJobAudience,
    kind: RemnawaveConnectionJobKind,
    actor_id: UUID,
    workspace_id: UUID | None = None,
    user_id: int | None = None,
    node_uuid: UUID | None = None,
) -> RemnawaveConnectionJobRecord:
    try:
        record = await registry.load(request_id)
    except RemnawaveConnectionJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection request not found",
        ) from exc
    except RemnawaveConnectionJobRegistryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection request registry is temporarily unavailable",
        ) from exc
    if (
        record.audience is not audience
        or record.kind is not kind
        or record.actor_id != actor_id
        or record.workspace_id != workspace_id
        or record.user_id != user_id
        or record.node_uuid != node_uuid
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection request not found",
        )
    return record


async def _customer_numeric_user_id(*, customer_account_id: UUID, db: AsyncSession) -> int:
    customer = await db.get(MobileUserModel, customer_account_id)
    if customer is None or not customer.is_active or customer.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer account not found")
    try:
        user_ref = await resolve_exact_mapped_mobile_user_ref(db, customer)
    except RemnawaveIdentityAccessConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer VPN identity is not reconciled",
        ) from exc
    if user_ref is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer VPN identity is not reconciled",
        )
    return user_ref.require_numeric_id()


async def _partner_service_identity_numeric_user_id(
    *,
    service_identity_uuid: UUID,
    access: PartnerWorkspaceAccess,
    db: AsyncSession,
) -> int:
    """Resolve one opaque, active, exactly mapped and granted identity."""

    result = await db.execute(
        select(ServiceIdentityModel)
        .join(MobileUserModel, MobileUserModel.id == ServiceIdentityModel.customer_account_id)
        .where(
            ServiceIdentityModel.id == service_identity_uuid,
            ServiceIdentityModel.provider_name == "remnawave",
            ServiceIdentityModel.identity_status == "active",
            MobileUserModel.is_active.is_(True),
            MobileUserModel.status == "active",
        )
    )
    identity = result.scalar_one_or_none()
    if identity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found")
    try:
        user_ref = await resolve_exact_mapped_remnawave_ref(
            db,
            subject_type="service_identity",
            subject_id=identity.id,
            numeric_user_id=identity.provider_numeric_subject_id,
            legacy_uuid_raw=identity.provider_subject_ref,
        )
    except RemnawaveIdentityAccessConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remnawave resource not found",
        ) from exc
    if user_ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found")
    await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type="service_identity",
        resource_uuid=identity.id,
        permission=PartnerPermission.REMNAWAVE_EXECUTE,
        db=db,
    )
    return user_ref.require_numeric_id()


async def _partner_drop_available(
    *,
    node_uuid: UUID,
    access: PartnerWorkspaceAccess,
    current_user: AdminUserModel,
    db: AsyncSession,
) -> bool:
    """Prove the same role/object/identity prerequisites used by Partner drop."""

    if PartnerPermission.REMNAWAVE_EXECUTE.value not in access.permission_keys or not _drop_receipt_runtime_available():
        return False
    try:
        await enforce_partner_workspace_permission(
            access=access,
            permission=PartnerPermission.REMNAWAVE_EXECUTE,
            current_user=current_user,
            db=db,
        )
    except HTTPException:
        return False
    readable_grants = await load_readable_partner_remnawave_grants(
        db=db,
        workspace_id=access.workspace.id,
    )
    node_executable = any(
        grant.resource_type == "node"
        and grant.resource_uuid == node_uuid
        and PartnerPermission.REMNAWAVE_EXECUTE.value in grant.permission_keys
        for grant in readable_grants
    )
    if not node_executable:
        return False
    for grant in readable_grants:
        if (
            grant.resource_type != "service_identity"
            or PartnerPermission.REMNAWAVE_EXECUTE.value not in grant.permission_keys
        ):
            continue
        try:
            await _partner_service_identity_numeric_user_id(
                service_identity_uuid=grant.resource_uuid,
                access=access,
                db=db,
            )
        except HTTPException:
            continue
        return True
    return False


def _require_exact_partner_workspace(*, access: PartnerWorkspaceAccess, workspace_id: UUID) -> None:
    if access.workspace.id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remnawave workspace not found",
        )


def _last_seen(ips: Iterable[RemnawaveConnectionIp]) -> datetime | None:
    return max((item.last_seen for item in ips), default=None)


def _admin_user_status(
    result: RemnawaveUserConnectionsJobResult,
    *,
    capabilities: RemnawaveConnectionsCapabilitiesResponse,
) -> AdminRemnawaveUserConnectionsStatusResponse:
    public_result: AdminRemnawaveUserConnectionsResultResponse | None = None
    if result.result is not None:
        public_result = AdminRemnawaveUserConnectionsResultResponse(
            success=result.result.success,
            user_id=result.result.user_id,
            nodes=[
                AdminRemnawaveUserConnectionNodeResponse(
                    node_uuid=node.node_uuid,
                    node_name=node.node_name,
                    country_code=node.country_code,
                    ips=[
                        AdminRemnawaveConnectionIpResponse(ip=item.public_ip, last_seen=item.last_seen)
                        for item in node.ips
                    ],
                )
                for node in result.result.nodes
            ],
        )
    return AdminRemnawaveUserConnectionsStatusResponse(
        is_completed=result.is_completed,
        is_failed=result.is_failed,
        progress=RemnawaveConnectionProgressResponse.model_validate(result.progress.model_dump()),
        result=public_result,
        capabilities=capabilities,
    )


def _admin_node_status(
    result: RemnawaveNodeConnectionsJobResult,
    *,
    capabilities: RemnawaveConnectionsCapabilitiesResponse,
) -> AdminRemnawaveNodeConnectionsStatusResponse:
    public_result: AdminRemnawaveNodeConnectionsResultResponse | None = None
    if result.result is not None:
        public_result = AdminRemnawaveNodeConnectionsResultResponse(
            success=result.result.success,
            node_uuid=result.result.node_uuid,
            users=[
                AdminRemnawaveNodeConnectionUserResponse(
                    user_id=user.user_id,
                    ips=[
                        AdminRemnawaveConnectionIpResponse(ip=item.public_ip, last_seen=item.last_seen)
                        for item in user.ips
                    ],
                )
                for user in result.result.users
            ],
        )
    return AdminRemnawaveNodeConnectionsStatusResponse(
        is_completed=result.is_completed,
        is_failed=result.is_failed,
        result=public_result,
        capabilities=capabilities,
    )


def _partner_node_status(
    *,
    node_uuid: UUID,
    result: RemnawaveNodeConnectionsJobResult,
    capabilities: RemnawaveConnectionsCapabilitiesResponse,
) -> PartnerRemnawaveNodeConnectionsStatusResponse:
    if result.result is None:
        return PartnerRemnawaveNodeConnectionsStatusResponse(
            is_completed=result.is_completed,
            is_failed=result.is_failed,
            success=None,
            node_uuid=node_uuid,
            last_seen_at=None,
            capabilities=capabilities,
        )
    all_ips = [item for user in result.result.users for item in user.ips]
    return PartnerRemnawaveNodeConnectionsStatusResponse(
        is_completed=result.is_completed,
        is_failed=result.is_failed,
        success=result.result.success,
        node_uuid=node_uuid,
        connected_user_count=sum(bool(user.ips) for user in result.result.users),
        active_ip_count=len(all_ips),
        last_seen_at=_last_seen(all_ips),
        capabilities=capabilities,
    )


def _customer_user_status(
    result: RemnawaveUserConnectionsJobResult,
    *,
    capabilities: RemnawaveConnectionsCapabilitiesResponse,
) -> CustomerRemnawaveConnectionsStatusResponse:
    progress = RemnawaveConnectionProgressResponse.model_validate(result.progress.model_dump())
    if result.result is None:
        return CustomerRemnawaveConnectionsStatusResponse(
            is_completed=result.is_completed,
            is_failed=result.is_failed,
            progress=progress,
            success=None,
            connected=None,
            last_seen_at=None,
            capabilities=capabilities,
        )
    all_ips = [item for node in result.result.nodes for item in node.ips]
    connected_nodes = sum(bool(node.ips) for node in result.result.nodes)
    return CustomerRemnawaveConnectionsStatusResponse(
        is_completed=result.is_completed,
        is_failed=result.is_failed,
        progress=progress,
        success=result.result.success,
        connected=bool(all_ips),
        connected_node_count=connected_nodes,
        active_ip_count=len(all_ips),
        last_seen_at=_last_seen(all_ips),
        capabilities=capabilities,
    )


@router.post(
    "/admin/remnawave/connections/users/{user_id}/requests",
    response_model=RemnawaveConnectionReadRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_admin_user_connections(
    user_id: int = Path(ge=1),
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> RemnawaveConnectionReadRequestResponse:
    try:
        job = await gateway.request_by_user(user_id)
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return await _issue_job(
        registry=registry,
        capabilities=_connections_capabilities(drop_connections=_admin_drop_available(current_user)),
        record=RemnawaveConnectionJobRecord(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            kind=RemnawaveConnectionJobKind.USER,
            actor_id=current_user.id,
            user_id=user_id,
            upstream_job_id=job.job_id,
        ),
    )


@router.get(
    "/admin/remnawave/connections/users/{user_id}/requests/{request_id}",
    response_model=AdminRemnawaveUserConnectionsStatusResponse,
)
async def get_admin_user_connections(
    user_id: int = Path(ge=1),
    request_id: str = _REQUEST_ID_PATH,
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> AdminRemnawaveUserConnectionsStatusResponse:
    record = await _load_scoped_job(
        registry=registry,
        request_id=request_id,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        kind=RemnawaveConnectionJobKind.USER,
        actor_id=current_user.id,
        user_id=user_id,
    )
    try:
        result = await gateway.get_by_user_result(
            job_id=record.upstream_job_id,
            expected_user_id=user_id,
        )
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return _admin_user_status(
        result,
        capabilities=_connections_capabilities(drop_connections=_admin_drop_available(current_user)),
    )


@router.post(
    "/admin/remnawave/connections/nodes/{node_uuid}/requests",
    response_model=RemnawaveConnectionReadRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_admin_node_connections(
    node_uuid: UUID,
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> RemnawaveConnectionReadRequestResponse:
    try:
        job = await gateway.request_by_node(node_uuid)
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return await _issue_job(
        registry=registry,
        capabilities=_connections_capabilities(drop_connections=_admin_drop_available(current_user)),
        record=RemnawaveConnectionJobRecord(
            audience=RemnawaveConnectionJobAudience.ADMIN,
            kind=RemnawaveConnectionJobKind.NODE,
            actor_id=current_user.id,
            node_uuid=node_uuid,
            upstream_job_id=job.job_id,
        ),
    )


@router.get(
    "/admin/remnawave/connections/nodes/{node_uuid}/requests/{request_id}",
    response_model=AdminRemnawaveNodeConnectionsStatusResponse,
)
async def get_admin_node_connections(
    node_uuid: UUID,
    request_id: str = _REQUEST_ID_PATH,
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> AdminRemnawaveNodeConnectionsStatusResponse:
    record = await _load_scoped_job(
        registry=registry,
        request_id=request_id,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        kind=RemnawaveConnectionJobKind.NODE,
        actor_id=current_user.id,
        node_uuid=node_uuid,
    )
    try:
        result = await gateway.get_by_node_result(
            job_id=record.upstream_job_id,
            expected_node_uuid=node_uuid,
        )
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return _admin_node_status(
        result,
        capabilities=_connections_capabilities(drop_connections=_admin_drop_available(current_user)),
    )


@router.get(
    "/admin/remnawave/connections/drop-receipts/unresolved",
    response_model=AdminRemnawaveConnectionDropUnresolvedPageResponse,
)
async def list_admin_unresolved_connection_drop_receipts(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(
        default=None,
        min_length=43,
        max_length=43,
        pattern=RECEIPT_ID_PATTERN,
    ),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    reconciliation: RemnawaveConnectionDropReconciliationService = Depends(
        get_remnawave_connection_drop_reconciliation_service
    ),
) -> AdminRemnawaveConnectionDropUnresolvedPageResponse:
    try:
        page = await reconciliation.list_unresolved(limit=limit, cursor=cursor)
    except RemnawaveConnectionDropReconciliationUnavailableError as exc:
        _raise_reconciliation_failure(exc)
    return AdminRemnawaveConnectionDropUnresolvedPageResponse(
        items=[_admin_reconciliation_receipt_response(item) for item in page.items],
        next_cursor=page.next_cursor,
    )


@router.get(
    "/admin/remnawave/connections/drop-receipts/{receipt_id}",
    response_model=AdminRemnawaveConnectionDropReceiptResponse,
    responses={404: {"description": "Receipt not found"}, 503: {"description": "Receipt store unavailable"}},
)
async def get_admin_connection_drop_receipt(
    receipt_id: str = _RECEIPT_ID_PATH,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    reconciliation: RemnawaveConnectionDropReconciliationService = Depends(
        get_remnawave_connection_drop_reconciliation_service
    ),
) -> AdminRemnawaveConnectionDropReceiptResponse:
    try:
        record = await reconciliation.get(receipt_id)
    except (
        RemnawaveConnectionDropReconciliationNotFoundError,
        RemnawaveConnectionDropReconciliationUnavailableError,
    ) as exc:
        _raise_reconciliation_failure(exc)
    return _admin_reconciliation_receipt_response(record)


@router.post(
    "/admin/remnawave/connections/drop-receipts/{receipt_id}/reconcile",
    response_model=AdminRemnawaveConnectionDropReceiptResponse,
    responses={
        404: {"description": "Receipt not found"},
        409: {"description": "Receipt already has a different terminal outcome"},
        503: {"description": "Receipt or required audit store unavailable"},
    },
)
async def reconcile_admin_connection_drop_receipt(
    body: AdminRemnawaveConnectionDropReconciliationRequest,
    request: Request,
    receipt_id: str = _RECEIPT_ID_PATH,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    reconciliation: RemnawaveConnectionDropReconciliationService = Depends(
        get_remnawave_connection_drop_reconciliation_service
    ),
) -> AdminRemnawaveConnectionDropReceiptResponse:
    try:
        record = await reconciliation.reconcile(
            receipt_id=receipt_id,
            outcome=RemnawaveConnectionDropState(body.outcome),
            reason=body.reason,
            reference=body.reference,
            actor=current_user,
            request=request,
        )
    except (
        RemnawaveConnectionDropReconciliationNotFoundError,
        RemnawaveConnectionDropReconciliationConflictError,
        RemnawaveConnectionDropReconciliationUnavailableError,
    ) as exc:
        _raise_reconciliation_failure(exc)
    return _admin_reconciliation_receipt_response(record)


@router.post(
    "/admin/remnawave/connections/drop",
    response_model=RemnawaveConnectionDropReceiptResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        409: {"description": "Idempotency key payload conflict"},
        502: {"description": "Upstream rejected the drop"},
        503: {"description": "Receipt registry unavailable before provider I/O"},
    },
)
async def drop_admin_connections(
    body: AdminRemnawaveConnectionDropRequest,
    request: Request,
    idempotency_key: str = _IDEMPOTENCY_KEY_HEADER,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    receipts: RemnawaveConnectionDropReceiptRegistry = Depends(get_remnawave_connection_drop_receipt_registry),
) -> RemnawaveConnectionDropReceiptResponse:
    command = RemnawaveConnectionDropCommand.model_validate(body.model_dump(by_alias=True, mode="json"))
    return await _execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=current_user.id,
        workspace_id=None,
        scope="admin:global",
        client_idempotency_key=idempotency_key,
        command=command,
        gateway=gateway,
        receipts=receipts,
        audit_context=RemnawaveConnectionDropAuditContext(
            db=db,
            request=request,
            actor=current_user,
        ),
    )


@router.post(
    "/partner-workspaces/{workspace_id}/remnawave/connections/nodes/{node_uuid}/requests",
    response_model=RemnawaveConnectionReadRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_partner_node_connections(
    workspace_id: UUID,
    node_uuid: UUID,
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> RemnawaveConnectionReadRequestResponse:
    _require_exact_partner_workspace(access=access, workspace_id=workspace_id)
    await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type="node",
        resource_uuid=node_uuid,
        permission=PartnerPermission.REMNAWAVE_READ,
        db=db,
    )
    try:
        job = await gateway.request_by_node(node_uuid)
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return await _issue_job(
        registry=registry,
        capabilities=_connections_capabilities(
            drop_connections=await _partner_drop_available(
                node_uuid=node_uuid,
                access=access,
                current_user=current_user,
                db=db,
            )
        ),
        record=RemnawaveConnectionJobRecord(
            audience=RemnawaveConnectionJobAudience.PARTNER,
            kind=RemnawaveConnectionJobKind.NODE,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            node_uuid=node_uuid,
            upstream_job_id=job.job_id,
        ),
    )


@router.get(
    "/partner-workspaces/{workspace_id}/remnawave/connections/nodes/{node_uuid}/requests/{request_id}",
    response_model=PartnerRemnawaveNodeConnectionsStatusResponse,
)
async def get_partner_node_connections(
    workspace_id: UUID,
    node_uuid: UUID,
    request_id: str = _REQUEST_ID_PATH,
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> PartnerRemnawaveNodeConnectionsStatusResponse:
    _require_exact_partner_workspace(access=access, workspace_id=workspace_id)
    await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type="node",
        resource_uuid=node_uuid,
        permission=PartnerPermission.REMNAWAVE_READ,
        db=db,
    )
    record = await _load_scoped_job(
        registry=registry,
        request_id=request_id,
        audience=RemnawaveConnectionJobAudience.PARTNER,
        kind=RemnawaveConnectionJobKind.NODE,
        actor_id=current_user.id,
        workspace_id=workspace_id,
        node_uuid=node_uuid,
    )
    try:
        result = await gateway.get_by_node_result(
            job_id=record.upstream_job_id,
            expected_node_uuid=node_uuid,
        )
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return _partner_node_status(
        node_uuid=node_uuid,
        result=result,
        capabilities=_connections_capabilities(
            drop_connections=await _partner_drop_available(
                node_uuid=node_uuid,
                access=access,
                current_user=current_user,
                db=db,
            )
        ),
    )


@router.post(
    "/partner-workspaces/{workspace_id}/remnawave/connections/nodes/{node_uuid}/drop",
    response_model=RemnawaveConnectionDropReceiptResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        409: {"description": "Idempotency key payload conflict"},
        502: {"description": "Upstream rejected the drop"},
        503: {"description": "Receipt registry unavailable before provider I/O"},
    },
)
async def drop_partner_node_connections(
    workspace_id: UUID,
    node_uuid: UUID,
    body: PartnerRemnawaveConnectionDropRequest,
    request: Request,
    idempotency_key: str = _IDEMPOTENCY_KEY_HEADER,
    access: PartnerWorkspaceAccess = Depends(get_partner_remnawave_workspace_access),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    receipts: RemnawaveConnectionDropReceiptRegistry = Depends(get_remnawave_connection_drop_receipt_registry),
) -> RemnawaveConnectionDropReceiptResponse:
    _require_exact_partner_workspace(access=access, workspace_id=workspace_id)
    await enforce_partner_workspace_permission(
        access=access,
        permission=PartnerPermission.REMNAWAVE_EXECUTE,
        current_user=current_user,
        db=db,
    )
    await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type="node",
        resource_uuid=node_uuid,
        permission=PartnerPermission.REMNAWAVE_EXECUTE,
        db=db,
    )
    user_id = await _partner_service_identity_numeric_user_id(
        service_identity_uuid=body.service_identity_uuid,
        access=access,
        db=db,
    )
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": {"by": "userIds", "userIds": [user_id]},
            "targetNodes": {
                "target": "specificNodes",
                "nodeUuids": [str(node_uuid)],
            },
        }
    )
    return await _execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.PARTNER,
        actor_id=current_user.id,
        workspace_id=workspace_id,
        scope=f"partner:{workspace_id}:node:{node_uuid}",
        client_idempotency_key=idempotency_key,
        command=command,
        gateway=gateway,
        receipts=receipts,
        audit_context=RemnawaveConnectionDropAuditContext(
            db=db,
            request=request,
            actor=current_user,
            workspace_id=workspace_id,
            service_identity_uuids=(body.service_identity_uuid,),
        ),
    )


@router.post(
    "/customer/remnawave/connections/requests",
    response_model=RemnawaveConnectionReadRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_customer_connections(
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> RemnawaveConnectionReadRequestResponse:
    user_id = await _customer_numeric_user_id(customer_account_id=customer_account_id, db=db)
    try:
        job = await gateway.request_by_user(user_id)
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return await _issue_job(
        registry=registry,
        capabilities=_connections_capabilities(drop_connections=_drop_receipt_runtime_available()),
        record=RemnawaveConnectionJobRecord(
            audience=RemnawaveConnectionJobAudience.CUSTOMER,
            kind=RemnawaveConnectionJobKind.USER,
            actor_id=customer_account_id,
            user_id=user_id,
            upstream_job_id=job.job_id,
        ),
    )


@router.get(
    "/customer/remnawave/connections/requests/{request_id}",
    response_model=CustomerRemnawaveConnectionsStatusResponse,
)
async def get_customer_connections(
    request_id: str = _REQUEST_ID_PATH,
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    registry: RemnawaveConnectionJobRegistry = Depends(get_remnawave_connection_job_registry),
) -> CustomerRemnawaveConnectionsStatusResponse:
    user_id = await _customer_numeric_user_id(customer_account_id=customer_account_id, db=db)
    record = await _load_scoped_job(
        registry=registry,
        request_id=request_id,
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        kind=RemnawaveConnectionJobKind.USER,
        actor_id=customer_account_id,
        user_id=user_id,
    )
    try:
        result = await gateway.get_by_user_result(
            job_id=record.upstream_job_id,
            expected_user_id=user_id,
        )
    except (
        RemnawaveHTTPStatusError,
        RemnawaveTransportError,
        RemnawaveProtocolError,
        RemnawaveConnectionsInvalidResponseError,
    ) as exc:
        _raise_provider_failure(exc)
    return _customer_user_status(
        result,
        capabilities=_connections_capabilities(drop_connections=_drop_receipt_runtime_available()),
    )


@router.post(
    "/customer/remnawave/connections/drop",
    response_model=RemnawaveConnectionDropReceiptResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        409: {"description": "Idempotency key payload conflict"},
        502: {"description": "Upstream rejected the drop"},
        503: {"description": "Receipt registry unavailable before provider I/O"},
    },
)
async def drop_customer_connections(
    idempotency_key: str = _IDEMPOTENCY_KEY_HEADER,
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    gateway: RemnawaveConnectionsGateway = Depends(get_remnawave_connections_gateway),
    receipts: RemnawaveConnectionDropReceiptRegistry = Depends(get_remnawave_connection_drop_receipt_registry),
) -> RemnawaveConnectionDropReceiptResponse:
    user_id = await _customer_numeric_user_id(customer_account_id=customer_account_id, db=db)
    command = RemnawaveConnectionDropCommand.model_validate(
        {
            "dropBy": RemnawaveDropByUserIds.model_validate({"userIds": [user_id], "by": "userIds"}),
            "targetNodes": RemnawaveDropOnAllNodes.model_validate({"target": "allNodes"}),
        }
    )
    return await _execute_connection_drop(
        audience=RemnawaveConnectionJobAudience.CUSTOMER,
        actor_id=customer_account_id,
        workspace_id=None,
        scope=f"customer:{customer_account_id}",
        client_idempotency_key=idempotency_key,
        command=command,
        gateway=gateway,
        receipts=receipts,
    )
