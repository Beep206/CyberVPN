from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import (
    PartnerIntegrationCredentialKind,
    PartnerIntegrationCredentialStatus,
    PartnerIntegrationDeliveryChannel,
    PartnerIntegrationDeliveryStatus,
)
from src.infrastructure.database.models.partner_integration_credential_model import (
    PartnerIntegrationCredentialModel,
)
from src.infrastructure.database.repositories.partner_integration_credential_repo import (
    PartnerIntegrationCredentialRepository,
)

from .workspace_reporting import BuildPartnerWorkspaceReportingUseCase

_REPORTING_SCOPE = "reporting:partner:read"
_POSTBACK_SCOPE = "service:postbacks:write"
_BLOCKED_WORKSPACE_STATUSES = {"restricted", "suspended", "rejected", "terminated"}
_REVIEW_WORKSPACE_STATUSES = {
    "draft",
    "email_verified",
    "submitted",
    "under_review",
    "waitlisted",
    "approved_probation",
    "needs_info",
}


@dataclass(frozen=True)
class IssuedPartnerIntegrationCredential:
    model: PartnerIntegrationCredentialModel
    issued_secret: str
    issued_at: datetime


@dataclass(frozen=True)
class PartnerWorkspacePostbackReadinessView:
    status: str
    delivery_status: str
    scope_label: str
    notes: list[str]
    credential: PartnerIntegrationCredentialModel | None


@dataclass(frozen=True)
class PartnerWorkspaceIntegrationDeliveryLogView:
    id: str
    channel: str
    status: str
    destination: str
    last_attempt_at: datetime
    notes: list[str]


@dataclass(frozen=True)
class PartnerReportingApiSnapshotView:
    workspace_id: UUID
    workspace_key: str
    generated_at: datetime
    partner_reporting_row: dict[str, Any]
    consumer_health_views: list[dict[str, Any]]
    delivery_logs: list[PartnerWorkspaceIntegrationDeliveryLogView]
    postback_readiness: PartnerWorkspacePostbackReadinessView


class ListPartnerWorkspaceIntegrationCredentialsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerIntegrationCredentialRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
    ) -> list[PartnerIntegrationCredentialModel]:
        return await self._repo.list_for_workspace(partner_account_id=partner_account_id)


class RotatePartnerWorkspaceIntegrationCredentialUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerIntegrationCredentialRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        credential_kind: PartnerIntegrationCredentialKind,
        actor_admin_user_id: UUID,
        destination_ref: str | None = None,
        credential_metadata: dict[str, Any] | None = None,
    ) -> IssuedPartnerIntegrationCredential:
        issued_at = datetime.now(UTC)
        issued_secret = _generate_secret(credential_kind)
        hashed_secret = _hash_secret(issued_secret)
        token_hint = _build_token_hint(credential_kind, issued_secret)
        model = await self._repo.get_for_workspace_and_kind(
            partner_account_id=partner_account_id,
            credential_kind=credential_kind.value,
        )

        if model is None:
            model = PartnerIntegrationCredentialModel(
                partner_account_id=partner_account_id,
                credential_kind=credential_kind.value,
                credential_status=PartnerIntegrationCredentialStatus.READY.value,
                credential_hash=hashed_secret,
                token_hint=token_hint,
                scope_key=_scope_for_kind(credential_kind),
                destination_ref=_default_destination_ref(
                    partner_account_id=partner_account_id,
                    credential_kind=credential_kind,
                    destination_ref=destination_ref,
                ),
                credential_metadata=dict(credential_metadata or {}),
                created_by_admin_user_id=actor_admin_user_id,
                rotated_by_admin_user_id=actor_admin_user_id,
                last_rotated_at=issued_at,
            )
            model = await self._repo.create(model)
        else:
            model.credential_status = PartnerIntegrationCredentialStatus.READY.value
            model.credential_hash = hashed_secret
            model.token_hint = token_hint
            model.scope_key = _scope_for_kind(credential_kind)
            model.destination_ref = _default_destination_ref(
                partner_account_id=partner_account_id,
                credential_kind=credential_kind,
                destination_ref=destination_ref or model.destination_ref,
            )
            model.credential_metadata = dict(credential_metadata or model.credential_metadata or {})
            model.rotated_by_admin_user_id = actor_admin_user_id
            model.last_rotated_at = issued_at
            model = await self._repo.update(model)

        return IssuedPartnerIntegrationCredential(
            model=model,
            issued_secret=issued_secret,
            issued_at=issued_at,
        )


class BuildPartnerWorkspacePostbackReadinessUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerIntegrationCredentialRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        workspace_status: str,
        workspace_label: str,
    ) -> PartnerWorkspacePostbackReadinessView:
        credential = await self._repo.get_for_workspace_and_kind(
            partner_account_id=partner_account_id,
            credential_kind=PartnerIntegrationCredentialKind.POSTBACK_SECRET.value,
        )
        readiness_status = _postback_readiness_status(
            workspace_status=workspace_status,
            credential=credential,
        )
        if readiness_status == "blocked":
            delivery_status = PartnerIntegrationDeliveryStatus.FAILED.value
        else:
            delivery_status = PartnerIntegrationDeliveryStatus.PAUSED.value
        notes = [
            (
                "Portal visibility stays anchored to canonical order, attribution, and settlement truth."
            ),
            (
                "Workspace restrictions block postback rollout until governance posture is restored."
                if readiness_status == "blocked"
                else "Postback credential is missing or rotation is still required before rollout."
                if readiness_status == "action_required"
                else "Postback readiness remains in an explicit review loop until the workspace exits probation."
                if readiness_status == "under_review"
                else (
                    "Postback credential is present and workspace-scoped delivery can be promoted "
                    "when the consumer is enabled."
                )
            ),
            f"Workspace label: {workspace_label}",
        ]
        return PartnerWorkspacePostbackReadinessView(
            status=readiness_status,
            delivery_status=delivery_status,
            scope_label="Tracking and postback handoff",
            notes=notes,
            credential=credential,
        )


class BuildPartnerWorkspaceIntegrationDeliveryLogsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._credential_repo = PartnerIntegrationCredentialRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        workspace_status: str,
        workspace_key: str,
        workspace_label: str,
    ) -> list[PartnerWorkspaceIntegrationDeliveryLogView]:
        report_pack = (
            await BuildPartnerWorkspaceReportingUseCase(self._session).execute(
                partner_account_id=partner_account_id,
                order_limit=200,
                order_offset=0,
                statement_limit=100,
                statement_offset=0,
                payout_limit=100,
                payout_offset=0,
            )
        ).report_pack
        credentials = await self._credential_repo.list_for_workspace(
            partner_account_id=partner_account_id
        )
        credential_by_kind = {item.credential_kind: item for item in credentials}
        partner_row = _get_partner_reporting_row(
            report_pack=report_pack,
            partner_account_id=partner_account_id,
        )
        generated_at = _generated_at(report_pack)
        consumer_views = report_pack.get("reporting_health_views", {}).get("consumer_health_views", [])
        analytics_consumer = next(
            (item for item in consumer_views if item.get("consumer_key") == "analytics_mart"),
            {},
        )
        replay_consumer = next(
            (item for item in consumer_views if item.get("consumer_key") == "operational_replay"),
            {},
        )
        reporting_credential = credential_by_kind.get(
            PartnerIntegrationCredentialKind.REPORTING_API_TOKEN.value
        )
        reporting_status = _reporting_delivery_status(
            workspace_status=workspace_status,
            credential=reporting_credential,
            consumer_views=(analytics_consumer, replay_consumer),
        )
        reporting_notes = [
            "Reporting export delivery stays row-level scoped to the workspace.",
            (
                "Canonical analytical and replay consumers are green for this workspace."
                if reporting_status == PartnerIntegrationDeliveryStatus.DELIVERED.value
                else "Reporting consumers still show backlog or the workspace lacks a ready reporting token."
                if reporting_status == PartnerIntegrationDeliveryStatus.PAUSED.value
                else "Reporting publication failures require replay or credential remediation."
            ),
            f"Paid conversions in mart scope: {int(partner_row.get('paid_conversion_count', 0) or 0)}.",
        ]
        postback_readiness = await BuildPartnerWorkspacePostbackReadinessUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            workspace_status=workspace_status,
            workspace_label=workspace_label,
        )
        postback_destination = (
            postback_readiness.credential.destination_ref
            if postback_readiness.credential is not None and postback_readiness.credential.destination_ref
            else f"postback://workspace/{workspace_key}"
        )
        return [
            PartnerWorkspaceIntegrationDeliveryLogView(
                id=f"reporting-export:{partner_account_id}",
                channel=PartnerIntegrationDeliveryChannel.REPORTING_EXPORT.value,
                status=reporting_status,
                destination=f"reporting://partner-workspace/{workspace_key}",
                last_attempt_at=generated_at,
                notes=reporting_notes,
            ),
            PartnerWorkspaceIntegrationDeliveryLogView(
                id=f"postback:{partner_account_id}",
                channel=PartnerIntegrationDeliveryChannel.POSTBACK.value,
                status=postback_readiness.delivery_status,
                destination=postback_destination,
                last_attempt_at=generated_at,
                notes=list(postback_readiness.notes),
            ),
        ]


class GetPartnerWorkspaceReportingApiSnapshotUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        workspace_key: str,
        workspace_status: str,
        workspace_label: str,
    ) -> PartnerReportingApiSnapshotView:
        report_pack = (
            await BuildPartnerWorkspaceReportingUseCase(self._session).execute(
                partner_account_id=partner_account_id,
                order_limit=200,
                order_offset=0,
                statement_limit=100,
                statement_offset=0,
                payout_limit=100,
                payout_offset=0,
            )
        ).report_pack
        delivery_logs = await BuildPartnerWorkspaceIntegrationDeliveryLogsUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            workspace_status=workspace_status,
            workspace_key=workspace_key,
            workspace_label=workspace_label,
        )
        postback_readiness = await BuildPartnerWorkspacePostbackReadinessUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            workspace_status=workspace_status,
            workspace_label=workspace_label,
        )
        return PartnerReportingApiSnapshotView(
            workspace_id=partner_account_id,
            workspace_key=workspace_key,
            generated_at=_generated_at(report_pack),
            partner_reporting_row=_get_partner_reporting_row(
                report_pack=report_pack,
                partner_account_id=partner_account_id,
            ),
            consumer_health_views=list(
                report_pack.get("reporting_health_views", {}).get("consumer_health_views", [])
            ),
            delivery_logs=delivery_logs,
            postback_readiness=postback_readiness,
        )


def _generate_secret(kind: PartnerIntegrationCredentialKind) -> str:
    prefix = "rpt" if kind == PartnerIntegrationCredentialKind.REPORTING_API_TOKEN else "pbs"
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_token_hint(kind: PartnerIntegrationCredentialKind, secret: str) -> str:
    prefix = "rpt" if kind == PartnerIntegrationCredentialKind.REPORTING_API_TOKEN else "pbs"
    return f"{prefix}_***{secret[-6:]}"


def _scope_for_kind(kind: PartnerIntegrationCredentialKind) -> str:
    if kind == PartnerIntegrationCredentialKind.REPORTING_API_TOKEN:
        return _REPORTING_SCOPE
    return _POSTBACK_SCOPE


def _default_destination_ref(
    *,
    partner_account_id: UUID,
    credential_kind: PartnerIntegrationCredentialKind,
    destination_ref: str | None,
) -> str:
    if destination_ref:
        return destination_ref
    if credential_kind == PartnerIntegrationCredentialKind.REPORTING_API_TOKEN:
        return f"reporting://partner-workspace/{partner_account_id}"
    return f"postback://workspace/{partner_account_id}"


def _effective_credential_status(
    *,
    workspace_status: str,
    credential: PartnerIntegrationCredentialModel | None,
) -> str:
    if workspace_status in _BLOCKED_WORKSPACE_STATUSES:
        return PartnerIntegrationCredentialStatus.BLOCKED.value
    if credential is None or credential.last_rotated_at is None:
        return PartnerIntegrationCredentialStatus.PENDING_ROTATION.value
    if workspace_status in _REVIEW_WORKSPACE_STATUSES:
        return PartnerIntegrationCredentialStatus.PENDING_ROTATION.value
    if credential.credential_status == PartnerIntegrationCredentialStatus.BLOCKED.value:
        return PartnerIntegrationCredentialStatus.BLOCKED.value
    return PartnerIntegrationCredentialStatus.READY.value


def _postback_readiness_status(
    *,
    workspace_status: str,
    credential: PartnerIntegrationCredentialModel | None,
) -> str:
    if workspace_status in _BLOCKED_WORKSPACE_STATUSES:
        return "blocked"
    if workspace_status == "needs_info":
        return "action_required"
    if workspace_status in {
        "draft",
        "email_verified",
        "submitted",
        "under_review",
        "waitlisted",
        "approved_probation",
    }:
        return "under_review"
    if _effective_credential_status(workspace_status=workspace_status, credential=credential) != "ready":
        return "action_required"
    return "complete"


def _generated_at(report_pack: dict[str, Any]) -> datetime:
    raw_value = str(report_pack.get("metadata", {}).get("generated_at") or datetime.now(UTC).isoformat())
    normalized = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _get_partner_reporting_row(
    *,
    report_pack: dict[str, Any],
    partner_account_id: UUID,
) -> dict[str, Any]:
    workspace_id = str(partner_account_id)
    for item in report_pack.get("partner_reporting_mart", []):
        if item.get("partner_account_id") == workspace_id:
            return dict(item)
    return {}


def _reporting_delivery_status(
    *,
    workspace_status: str,
    credential: PartnerIntegrationCredentialModel | None,
    consumer_views: tuple[dict[str, Any], dict[str, Any]],
) -> str:
    effective_status = _effective_credential_status(
        workspace_status=workspace_status,
        credential=credential,
    )
    if effective_status == PartnerIntegrationCredentialStatus.BLOCKED.value:
        return PartnerIntegrationDeliveryStatus.FAILED.value
    if effective_status != PartnerIntegrationCredentialStatus.READY.value:
        return PartnerIntegrationDeliveryStatus.PAUSED.value
    if any(int(item.get("failed_count", 0) or 0) > 0 for item in consumer_views):
        return PartnerIntegrationDeliveryStatus.FAILED.value
    if any(int(item.get("backlog_count", 0) or 0) > 0 for item in consumer_views):
        return PartnerIntegrationDeliveryStatus.PAUSED.value
    return PartnerIntegrationDeliveryStatus.DELIVERED.value
