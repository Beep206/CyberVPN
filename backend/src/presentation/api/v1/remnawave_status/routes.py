"""Safe, audience-specific Remnawave capability and stream health views."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from httpx import HTTPError
from pydantic import BaseModel, Field
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import ColumnElement

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_mobile_user_ref,
)
from src.config.settings import settings
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import (
    RemnawaveIdentityReconciliationModel,
    RemnawaveStreamCheckpointModel,
    RemnawaveStreamDeadLetterModel,
    RemnawaveStreamGapModel,
    RemnawaveStreamReceiptModel,
)
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.remnawave.client import RemnawaveClient, RemnawaveProtocolError
from src.presentation.api.v1.admin.remnawave_node_ssh import is_remnawave_node_ssh_available_for
from src.presentation.api.v1.partner_remnawave.grant_queries import load_readable_partner_remnawave_grants
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.dependencies.auth import get_current_active_web_user, get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    enforce_partner_workspace_permission,
    get_partner_workspace_access,
)

router = APIRouter(tags=["remnawave-status"])

RemnawaveStreamKey = Literal["user_usage", "subscription_requests", "node_connections"]
_TARGET_PANEL_READINESS_CACHE_TTL_SECONDS = 5.0
_TARGET_PANEL_READINESS_CACHE_MAX_TTL_SECONDS = 30.0
_STREAM_RETENTION_SETTINGS: tuple[tuple[RemnawaveStreamKey, str], ...] = (
    ("user_usage", "remnawave_user_usage_retention_days"),
    ("subscription_requests", "remnawave_subscription_request_retention_days"),
    ("node_connections", "remnawave_node_connections_retention_days"),
)
_STREAM_KEYS = frozenset(stream_name for stream_name, _ in _STREAM_RETENTION_SETTINGS)
_STREAM_EXPORT_READY_MAX_LAG = 0
_STREAM_EXPORT_READY_MAX_PENDING = 0
_CANONICAL_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


@dataclass(frozen=True, slots=True)
class _TargetPanelReadinessCacheEntry:
    client: RemnawaveClient
    ready: bool
    expires_at: float


@dataclass(frozen=True, slots=True)
class _StreamCheckpointHealth:
    lag: int | None
    pending: int
    stream_exists: bool
    group_exists: bool
    observed_at: datetime | None


class _TargetPanelReadinessCache:
    """Bounded process-local cache for the singleton Remnawave target.

    Only one client/result is retained.  Expired values are never served while
    the single-flight refresh runs, so an expired ``True`` cannot mask an
    upstream failure or version rollback.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = _TARGET_PANEL_READINESS_CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 0 < ttl_seconds <= _TARGET_PANEL_READINESS_CACHE_MAX_TTL_SECONDS:
            raise ValueError("Target panel readiness cache TTL must be between 0 and 30 seconds")
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entry: _TargetPanelReadinessCacheEntry | None = None
        self._refresh_lock = asyncio.Lock()

    async def get(self, client: RemnawaveClient) -> bool:
        now = self._clock()
        entry = self._entry
        if entry is not None and entry.client is client and entry.expires_at > now:
            return entry.ready

        async with self._refresh_lock:
            now = self._clock()
            entry = self._entry
            if entry is not None and entry.client is client and entry.expires_at > now:
                return entry.ready

            ready = await _fetch_target_panel_readiness(client)
            self._entry = _TargetPanelReadinessCacheEntry(
                client=client,
                ready=ready,
                expires_at=self._clock() + self._ttl_seconds,
            )
            return ready


_target_panel_readiness_cache = _TargetPanelReadinessCache()


class AdminRemnawaveStreamHealth(BaseModel):
    key: RemnawaveStreamKey
    retention_days: int = Field(ge=1)
    consumer_group: str
    status: Literal["healthy", "degraded", "unknown"]
    lag: int | None = Field(ge=0)
    pending: int | None = Field(ge=0)
    dead_letters: int = Field(ge=0)
    last_consumed_at: datetime | None
    degraded_reason: str | None


class AdminRemnawaveCapabilities(BaseModel):
    numeric_user_ids: bool
    connections: bool
    geo_check: bool
    node_integrations: bool
    shared_lists: bool
    node_ssh: bool
    tags: bool
    host_mapper: bool
    root_snippets: bool
    redis_stream_export: bool


class AdminRemnawaveCapabilitiesAndStreams(BaseModel):
    panel_version: str | None
    target_panel_version: Literal["3.4.3"]
    target_node_version: Literal["3.4.1"]
    contract_version: Literal["3.4.13"]
    capabilities: AdminRemnawaveCapabilities
    streams: list[AdminRemnawaveStreamHealth]
    degraded_reason: str | None


class PartnerVpnCapabilities(BaseModel):
    connections: bool
    usage: bool
    devices: bool


class PartnerVpnServiceStatus(BaseModel):
    workspace_id: UUID
    capabilities: PartnerVpnCapabilities
    assigned_resources: int = Field(ge=0)
    degraded: bool
    degraded_reason: str | None


class CustomerVpnServiceStatus(BaseModel):
    connections_available: bool
    usage_available: bool
    devices_available: bool
    degraded: bool
    degraded_reason: str | None


async def get_partner_vpn_status_access(
    access: PartnerWorkspaceAccess = Depends(get_partner_workspace_access),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceAccess:
    """Require the explicit role permission before exposing VPN assignments."""

    await enforce_partner_workspace_permission(
        access=access,
        permission=PartnerPermission.REMNAWAVE_READ,
        current_user=current_user,
        db=db,
    )
    return access


def _build_admin_capabilities(
    *,
    panel_version: str | None,
    node_ssh_available: bool,
    numeric_cutover_ready: bool = False,
    stream_export_observed: bool = False,
) -> AdminRemnawaveCapabilities:
    """Advertise only target-compatible capabilities implemented by CyberVPN.

    Capabilities are enabled only for the exact target after their trusted-
    admin CyberVPN boundary, durable mutation receipts, and typed contracts
    are registered in the same process.
    """
    target_reachable = panel_version == "3.4.3"
    return AdminRemnawaveCapabilities(
        numeric_user_ids=target_reachable and numeric_cutover_ready,
        connections=target_reachable,
        geo_check=target_reachable,
        node_integrations=target_reachable,
        shared_lists=target_reachable,
        node_ssh=target_reachable and node_ssh_available,
        tags=target_reachable,
        host_mapper=target_reachable,
        root_snippets=target_reachable,
        redis_stream_export=(
            target_reachable and settings.remnawave_stream_ingestion_enabled and stream_export_observed
        ),
    )


def _panel_version(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("version")
    if isinstance(value, str) and value.strip():
        return value.strip().removeprefix("v")
    return None


async def _fetch_target_panel_readiness(client: RemnawaveClient) -> bool:
    """Fetch exact target readiness, mapping expected provider failures to false."""
    try:
        return _panel_version(await client.get("/system/metadata")) == "3.4.3"
    except (HTTPError, RemnawaveProtocolError, TypeError, ValueError):
        return False


async def _target_panel_ready(client: RemnawaveClient) -> bool:
    """Return short-lived, single-flight readiness for customer/partner views."""

    return await _target_panel_readiness_cache.get(client)


async def _numeric_identity_cutover_ready(db: AsyncSession) -> bool:
    """Prove exact two-way coverage and one owner for every provider identity."""

    valid_mobile_ledger = exists(
        select(MobileUserModel.id).where(
            RemnawaveIdentityReconciliationModel.subject_type == "mobile_user",
            MobileUserModel.id == RemnawaveIdentityReconciliationModel.subject_id,
            MobileUserModel.remnawave_user_id == RemnawaveIdentityReconciliationModel.numeric_user_id,
            _normalized_legacy_pair_matches(
                RemnawaveIdentityReconciliationModel.legacy_uuid,
                MobileUserModel.remnawave_uuid,
            ),
        )
    )
    valid_service_ledger = exists(
        select(ServiceIdentityModel.id).where(
            RemnawaveIdentityReconciliationModel.subject_type == "service_identity",
            ServiceIdentityModel.id == RemnawaveIdentityReconciliationModel.subject_id,
            ServiceIdentityModel.provider_name == "remnawave",
            ServiceIdentityModel.provider_numeric_subject_id == RemnawaveIdentityReconciliationModel.numeric_user_id,
            _normalized_legacy_pair_matches(
                RemnawaveIdentityReconciliationModel.legacy_uuid,
                ServiceIdentityModel.provider_subject_ref,
            ),
        )
    )
    invalid_ledger = int(
        (
            await db.execute(
                select(func.count(RemnawaveIdentityReconciliationModel.id)).where(
                    or_(
                        RemnawaveIdentityReconciliationModel.reconciliation_state != "mapped",
                        RemnawaveIdentityReconciliationModel.numeric_user_id.is_(None),
                        ~or_(valid_mobile_ledger, valid_service_ledger),
                    )
                )
            )
        ).scalar_one()
    )
    if invalid_ledger:
        return False

    mobile_ledger = aliased(RemnawaveIdentityReconciliationModel)
    service_ledger = aliased(RemnawaveIdentityReconciliationModel)
    provider_identity_collision = or_(
        and_(
            mobile_ledger.numeric_user_id.is_not(None),
            mobile_ledger.numeric_user_id == service_ledger.numeric_user_id,
        ),
        and_(
            mobile_ledger.legacy_uuid.is_not(None),
            service_ledger.legacy_uuid.is_not(None),
            _normalized_legacy_values_equal(
                mobile_ledger.legacy_uuid,
                service_ledger.legacy_uuid,
            ),
        ),
    )
    exact_provider_pair = and_(
        mobile_ledger.numeric_user_id == service_ledger.numeric_user_id,
        _normalized_legacy_pair_matches(
            mobile_ledger.legacy_uuid,
            service_ledger.legacy_uuid,
        ),
    )
    conflicting_aliases = int(
        (
            await db.execute(
                select(func.count(mobile_ledger.id))
                .select_from(mobile_ledger)
                .join(MobileUserModel, MobileUserModel.id == mobile_ledger.subject_id)
                .join(service_ledger, provider_identity_collision)
                .join(ServiceIdentityModel, ServiceIdentityModel.id == service_ledger.subject_id)
                .where(
                    mobile_ledger.subject_type == "mobile_user",
                    service_ledger.subject_type == "service_identity",
                    mobile_ledger.reconciliation_state == "mapped",
                    service_ledger.reconciliation_state == "mapped",
                    or_(
                        ServiceIdentityModel.customer_account_id != MobileUserModel.id,
                        ~exact_provider_pair,
                    ),
                )
            )
        ).scalar_one()
    )
    if conflicting_aliases:
        return False

    mapped_mobile = exists(
        select(RemnawaveIdentityReconciliationModel.id).where(
            RemnawaveIdentityReconciliationModel.subject_type == "mobile_user",
            RemnawaveIdentityReconciliationModel.subject_id == MobileUserModel.id,
            RemnawaveIdentityReconciliationModel.reconciliation_state == "mapped",
            RemnawaveIdentityReconciliationModel.numeric_user_id == MobileUserModel.remnawave_user_id,
            _normalized_legacy_pair_matches(
                RemnawaveIdentityReconciliationModel.legacy_uuid,
                MobileUserModel.remnawave_uuid,
            ),
        )
    )
    missing_mobile = int(
        (
            await db.execute(
                select(func.count(MobileUserModel.id)).where(
                    or_(
                        MobileUserModel.remnawave_user_id.is_not(None),
                        MobileUserModel.remnawave_uuid.is_not(None),
                    ),
                    ~mapped_mobile,
                )
            )
        ).scalar_one()
    )
    if missing_mobile:
        return False

    mapped_service_identity = exists(
        select(RemnawaveIdentityReconciliationModel.id).where(
            RemnawaveIdentityReconciliationModel.subject_type == "service_identity",
            RemnawaveIdentityReconciliationModel.subject_id == ServiceIdentityModel.id,
            RemnawaveIdentityReconciliationModel.reconciliation_state == "mapped",
            RemnawaveIdentityReconciliationModel.numeric_user_id == ServiceIdentityModel.provider_numeric_subject_id,
            _normalized_legacy_pair_matches(
                RemnawaveIdentityReconciliationModel.legacy_uuid,
                ServiceIdentityModel.provider_subject_ref,
            ),
        )
    )
    missing_service_identity = int(
        (
            await db.execute(
                select(func.count(ServiceIdentityModel.id)).where(
                    ServiceIdentityModel.provider_name == "remnawave",
                    or_(
                        ServiceIdentityModel.provider_numeric_subject_id.is_not(None),
                        ServiceIdentityModel.provider_subject_ref.is_not(None),
                    ),
                    ~mapped_service_identity,
                )
            )
        ).scalar_one()
    )
    return missing_service_identity == 0


def _normalized_legacy_values_equal(
    left: InstrumentedAttribute[str | None],
    right: InstrumentedAttribute[str | None],
) -> ColumnElement[bool]:
    return func.lower(func.trim(left)) == func.lower(func.trim(right))


def _normalized_legacy_pair_matches(
    left: InstrumentedAttribute[str | None],
    right: InstrumentedAttribute[str | None],
) -> ColumnElement[bool]:
    normalized_left = func.lower(func.trim(left))
    normalized_right = func.lower(func.trim(right))
    return and_(
        left.is_not(None),
        right.is_not(None),
        normalized_left.regexp_match(_CANONICAL_UUID_PATTERN),
        normalized_right.regexp_match(_CANONICAL_UUID_PATTERN),
        normalized_left == normalized_right,
    )


async def _stream_health(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[AdminRemnawaveStreamHealth]:
    observed_at = now or datetime.now(UTC)
    stale_cutoff = observed_at - timedelta(seconds=settings.remnawave_stream_receipt_max_idle_seconds)
    receipt_rows = (
        await db.execute(
            select(
                RemnawaveStreamReceiptModel.stream_name,
                func.max(RemnawaveStreamReceiptModel.processed_at),
            )
            .where(
                RemnawaveStreamReceiptModel.processing_status == "committed",
                RemnawaveStreamReceiptModel.expires_at > observed_at,
            )
            .group_by(RemnawaveStreamReceiptModel.stream_name)
        )
    ).all()
    dead_letter_rows = (
        await db.execute(
            select(
                RemnawaveStreamDeadLetterModel.stream_name,
                func.count(RemnawaveStreamDeadLetterModel.id),
            )
            .where(RemnawaveStreamDeadLetterModel.expires_at > observed_at)
            .group_by(RemnawaveStreamDeadLetterModel.stream_name)
        )
    ).all()
    gap_rows = (
        await db.execute(
            select(RemnawaveStreamGapModel.stream_name, func.count(RemnawaveStreamGapModel.id))
            .where(RemnawaveStreamGapModel.reconciliation_status != "reconciled")
            .group_by(RemnawaveStreamGapModel.stream_name)
        )
    ).all()
    checkpoint_rows = (
        await db.execute(
            select(
                RemnawaveStreamCheckpointModel.stream_name,
                RemnawaveStreamCheckpointModel.observed_group_lag,
                RemnawaveStreamCheckpointModel.observed_group_pending_count,
                RemnawaveStreamCheckpointModel.stream_exists,
                RemnawaveStreamCheckpointModel.group_exists,
                RemnawaveStreamCheckpointModel.observed_at,
            )
        )
    ).all()

    last_consumed = {str(name): observed for name, observed in receipt_rows}
    dead_letters = {str(name): int(count) for name, count in dead_letter_rows}
    gaps = {str(name): int(count) for name, count in gap_rows}
    checkpoints = {
        str(name): _StreamCheckpointHealth(
            lag=int(lag) if lag is not None else None,
            pending=int(pending),
            stream_exists=bool(stream_exists),
            group_exists=bool(group_exists),
            observed_at=checkpoint_observed_at,
        )
        for name, lag, pending, stream_exists, group_exists, checkpoint_observed_at in checkpoint_rows
    }
    result: list[AdminRemnawaveStreamHealth] = []
    for stream_name, retention_setting in _STREAM_RETENTION_SETTINGS:
        reason: str | None = None
        stream_status: Literal["healthy", "degraded", "unknown"] = "healthy"
        latest_receipt_at = last_consumed.get(stream_name)
        checkpoint = checkpoints.get(stream_name)
        lag = checkpoint.lag if checkpoint is not None else None
        pending = checkpoint.pending if checkpoint is not None else None
        if not settings.remnawave_stream_ingestion_enabled:
            stream_status = "degraded"
            reason = "stream_ingestion_disabled"
        elif gaps.get(stream_name, 0) > 0:
            stream_status = "degraded"
            reason = "reconciliation_gap_open"
        elif dead_letters.get(stream_name, 0) > 0:
            stream_status = "degraded"
            reason = "dead_letters_present"
        elif latest_receipt_at is None:
            stream_status = "unknown"
            reason = "no_committed_receipt"
        elif latest_receipt_at <= stale_cutoff:
            stream_status = "degraded"
            reason = "stream_receipt_stale"
        elif checkpoint is None or checkpoint.observed_at is None:
            stream_status = "unknown"
            reason = "backlog_unobserved"
        elif checkpoint.observed_at <= stale_cutoff:
            stream_status = "degraded"
            reason = "backlog_observation_stale"
        elif not checkpoint.stream_exists:
            stream_status = "degraded"
            reason = "stream_missing"
        elif not checkpoint.group_exists:
            stream_status = "degraded"
            reason = "consumer_group_missing"
        elif lag is None or pending is None:
            stream_status = "unknown"
            reason = "backlog_unobserved"
        elif lag > _STREAM_EXPORT_READY_MAX_LAG or pending > _STREAM_EXPORT_READY_MAX_PENDING:
            stream_status = "degraded"
            reason = "stream_backlog_present"
        result.append(
            AdminRemnawaveStreamHealth(
                key=stream_name,
                retention_days=int(getattr(settings, retention_setting)),
                consumer_group=settings.remnawave_stream_consumer_group,
                status=stream_status,
                lag=lag,
                pending=pending,
                dead_letters=dead_letters.get(stream_name, 0),
                last_consumed_at=last_consumed.get(stream_name),
                degraded_reason=reason,
            )
        )
    return result


def _stream_export_readiness_observed(streams: list[AdminRemnawaveStreamHealth]) -> bool:
    """Require all streams, fresh receipts and observed bounded backlog state."""

    if len(streams) != len(_STREAM_KEYS) or {item.key for item in streams} != _STREAM_KEYS:
        return False
    return all(
        item.status == "healthy"
        and item.last_consumed_at is not None
        and item.lag is not None
        and item.lag <= _STREAM_EXPORT_READY_MAX_LAG
        and item.pending is not None
        and item.pending <= _STREAM_EXPORT_READY_MAX_PENDING
        for item in streams
    )


@router.get(
    "/admin/remnawave/capabilities-and-streams",
    response_model=AdminRemnawaveCapabilitiesAndStreams,
)
async def get_admin_remnawave_capabilities_and_streams(
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> AdminRemnawaveCapabilitiesAndStreams:
    panel_version: str | None = None
    degraded_reason: str | None = None
    try:
        panel_version = _panel_version(await client.get("/system/metadata"))
    except (HTTPError, RemnawaveProtocolError, TypeError, ValueError):
        degraded_reason = "panel_metadata_unavailable"
    if panel_version is None and degraded_reason is None:
        degraded_reason = "panel_metadata_invalid"
    elif panel_version is not None and panel_version != "3.4.3":
        degraded_reason = "panel_version_mismatch"

    streams = await _stream_health(db)
    numeric_cutover_ready = await _numeric_identity_cutover_ready(db)
    if degraded_reason is None and any(item.status == "degraded" for item in streams):
        degraded_reason = "stream_consumer_degraded"
    elif degraded_reason is None and any(item.status == "unknown" for item in streams):
        degraded_reason = "stream_consumer_unobserved"
    return AdminRemnawaveCapabilitiesAndStreams(
        panel_version=panel_version,
        target_panel_version="3.4.3",
        target_node_version="3.4.1",
        contract_version="3.4.13",
        capabilities=_build_admin_capabilities(
            panel_version=panel_version,
            node_ssh_available=is_remnawave_node_ssh_available_for(current_user),
            numeric_cutover_ready=numeric_cutover_ready,
            stream_export_observed=_stream_export_readiness_observed(streams),
        ),
        streams=streams,
        degraded_reason=degraded_reason,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/vpn-service-status",
    response_model=PartnerVpnServiceStatus,
)
async def get_partner_vpn_service_status(
    workspace_id: UUID,
    access: PartnerWorkspaceAccess = Depends(get_partner_vpn_status_access),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> PartnerVpnServiceStatus:
    readable_grants = await load_readable_partner_remnawave_grants(
        db=db,
        workspace_id=access.workspace.id,
    )
    assigned_resources = len(readable_grants)
    has_node = any(grant.resource_type == "node" for grant in readable_grants)
    # Partner live reads are scoped by the exact readable node grant.  A
    # service-identity execute grant is additionally required by the separate
    # drop route, but must not hide the safe read-only Connections surface.
    target_panel_ready = await _target_panel_ready(client)
    connection_scope_ready = has_node and target_panel_ready
    return PartnerVpnServiceStatus(
        workspace_id=workspace_id,
        capabilities=PartnerVpnCapabilities(
            connections=connection_scope_ready,
            # No tenant-scoped Partner usage or HWID/device route exists yet.
            # Grant presence alone must never advertise a product capability.
            usage=False,
            devices=False,
        ),
        assigned_resources=assigned_resources,
        degraded=has_node and not target_panel_ready,
        degraded_reason=("panel_unavailable_or_mismatched" if has_node and not target_panel_ready else None),
    )


@router.get("/customer/vpn-service-status", response_model=CustomerVpnServiceStatus)
async def get_customer_vpn_service_status(
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> CustomerVpnServiceStatus:
    customer = await db.get(MobileUserModel, customer_account_id)
    identity_ready = False
    if customer is not None and customer.is_active and customer.status == "active":
        try:
            identity_ready = await resolve_exact_mapped_mobile_user_ref(db, customer) is not None
        except RemnawaveIdentityAccessConflict:
            identity_ready = False
    target_panel_ready = await _target_panel_ready(client)
    connections_available = identity_ready and target_panel_ready
    usage_available = identity_ready and target_panel_ready
    degraded_reason: str | None = None
    if not identity_ready:
        degraded_reason = "vpn_identity_not_reconciled"
    elif not target_panel_ready:
        degraded_reason = "panel_unavailable_or_mismatched"
    return CustomerVpnServiceStatus(
        connections_available=connections_available,
        usage_available=usage_available,
        # Account/session devices are a separate product surface.  No
        # self-scoped Remnawave HWID/device API exists yet.
        devices_available=False,
        degraded=degraded_reason is not None,
        degraded_reason=degraded_reason,
    )
