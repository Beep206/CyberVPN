"""Append-only, replay-safe audit events for privileged connection drops."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from uuid import UUID, uuid5

from fastapi import Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.remnawave.connections_gateway import (
    RemnawaveConnectionDropCommand,
    RemnawaveDropByIpAddresses,
    RemnawaveDropByUserIds,
    RemnawaveDropOnAllNodes,
    RemnawaveDropOnSpecificNodes,
)
from src.presentation.api.v1.admin.audit import build_admin_audit_details, write_required_admin_audit_entry

from .drop_receipts import RemnawaveConnectionDropReceiptRecord, RemnawaveConnectionDropState
from .job_registry import RemnawaveConnectionJobAudience

_AUDIT_ENTITY_TYPE = "remnawave_connection_drop"
_AUDIT_EVENT_NAMESPACE = UUID("1aacd823-e748-49a9-b1cb-e21a942e25c2")
_IP_HMAC_CONTEXT = b"cybervpn/remnawave-connections-drop-audit-ip/v1\0"
_ACTION_BY_STATE = {
    RemnawaveConnectionDropState.ACCEPTED: "remnawave.connections.drop.accepted",
    RemnawaveConnectionDropState.OUTCOME_UNKNOWN: "remnawave.connections.drop.outcome_unknown",
    RemnawaveConnectionDropState.REJECTED: "remnawave.connections.drop.rejected",
}


class RemnawaveConnectionDropAuditUnavailableError(RuntimeError):
    """A required privileged drop audit event could not be persisted."""


@dataclass(frozen=True, slots=True)
class RemnawaveConnectionDropAuditContext:
    db: AsyncSession
    request: Request
    actor: AdminUserModel
    workspace_id: UUID | None = None
    service_identity_uuids: tuple[UUID, ...] = ()


def build_privileged_connection_drop_audit_details(
    *,
    audience: RemnawaveConnectionJobAudience,
    workspace_id: UUID | None,
    command: RemnawaveConnectionDropCommand,
    payload_hmac: str,
    receipt: RemnawaveConnectionDropReceiptRecord,
) -> dict[str, object]:
    """Build an allowlisted audit payload without raw IP or replay material."""

    details: dict[str, object] = {
        "audience": audience.value,
        "scope": "workspace" if workspace_id is not None else "global",
        "payload_hmac": payload_hmac,
        "receipt_id": receipt.receipt_id,
        "outcome": receipt.state.value,
    }
    if workspace_id is not None:
        details["workspace_id"] = workspace_id

    drop_by = command.drop_by
    if isinstance(drop_by, RemnawaveDropByUserIds):
        details["drop_by"] = "user_ids"
        details["user_ids"] = sorted(drop_by.user_ids)
    elif isinstance(drop_by, RemnawaveDropByIpAddresses):
        details["drop_by"] = "ip_hmacs"
        details["ip_hmacs"] = sorted(_hmac_ip(str(ip)) for ip in drop_by.ip_addresses)

    target_nodes = command.target_nodes
    if isinstance(target_nodes, RemnawaveDropOnAllNodes):
        details["target_nodes"] = "all_nodes"
    elif isinstance(target_nodes, RemnawaveDropOnSpecificNodes):
        details["target_nodes"] = "specific_nodes"
        details["node_uuids"] = sorted(str(node_uuid) for node_uuid in target_nodes.node_uuids)
    return details


def validate_privileged_connection_drop_audit_configuration(
    command: RemnawaveConnectionDropCommand,
) -> None:
    """Fail before receipt/provider I/O when an IP audit cannot be anonymized."""

    if isinstance(command.drop_by, RemnawaveDropByIpAddresses):
        _ip_hmac_secret()


async def persist_privileged_connection_drop_audit(
    *,
    context: RemnawaveConnectionDropAuditContext,
    audience: RemnawaveConnectionJobAudience,
    command: RemnawaveConnectionDropCommand,
    payload_hmac: str,
    receipt: RemnawaveConnectionDropReceiptRecord,
) -> None:
    """Persist one immutable event per receipt outcome, safely across replay."""

    if audience is RemnawaveConnectionJobAudience.CUSTOMER:
        raise ValueError("Customer connection drops cannot use the admin audit log")
    if audience is RemnawaveConnectionJobAudience.PARTNER and context.workspace_id is None:
        raise ValueError("Partner connection drop audit requires a workspace")

    action = _ACTION_BY_STATE[receipt.state]
    audit_entry_id = _audit_event_id(receipt_id=receipt.receipt_id, action=action)
    details = build_privileged_connection_drop_audit_details(
        audience=audience,
        workspace_id=context.workspace_id,
        command=command,
        payload_hmac=payload_hmac,
        receipt=receipt,
    )
    if context.service_identity_uuids:
        details["service_identity_uuids"] = sorted(str(value) for value in context.service_identity_uuids)
    sanitized_details = build_admin_audit_details(details)
    existing = await _load_existing_audit(context.db, audit_entry_id)
    if existing is not None:
        _validate_existing_audit(
            existing,
            action=action,
            receipt_id=receipt.receipt_id,
            actor_id=context.actor.id,
            expected_details=sanitized_details,
        )
        return

    try:
        await write_required_admin_audit_entry(
            db=context.db,
            action=action,
            resource_type=_AUDIT_ENTITY_TYPE,
            resource_id=receipt.receipt_id,
            actor=context.actor,
            request=context.request,
            details=details,
            audit_entry_id=audit_entry_id,
        )
        await context.db.commit()
    except IntegrityError as exc:
        await _rollback(context.db)
        existing = await _load_existing_audit(context.db, audit_entry_id)
        if existing is not None:
            _validate_existing_audit(
                existing,
                action=action,
                receipt_id=receipt.receipt_id,
                actor_id=context.actor.id,
                expected_details=sanitized_details,
            )
            return
        raise RemnawaveConnectionDropAuditUnavailableError(
            "Connection drop audit conflict could not be reconciled"
        ) from exc
    except SQLAlchemyError as exc:
        await _rollback(context.db)
        raise RemnawaveConnectionDropAuditUnavailableError("Connection drop audit could not be persisted") from exc


async def _load_existing_audit(db: AsyncSession, audit_entry_id: UUID) -> AuditLog | None:
    try:
        return await db.get(AuditLog, audit_entry_id)
    except SQLAlchemyError as exc:
        await _rollback(db)
        raise RemnawaveConnectionDropAuditUnavailableError("Connection drop audit state could not be read") from exc


def _validate_existing_audit(
    existing: AuditLog,
    *,
    action: str,
    receipt_id: str,
    actor_id: UUID,
    expected_details: dict[str, object] | None,
) -> None:
    if (
        existing.action != action
        or existing.entity_type != _AUDIT_ENTITY_TYPE
        or existing.entity_id != receipt_id
        or existing.admin_id != actor_id
        or existing.new_value != expected_details
    ):
        raise RemnawaveConnectionDropAuditUnavailableError("Connection drop audit identity mismatch")


async def _rollback(db: AsyncSession) -> None:
    try:
        await db.rollback()
    except SQLAlchemyError as rollback_error:
        raise RemnawaveConnectionDropAuditUnavailableError(
            "Connection drop audit transaction could not be rolled back"
        ) from rollback_error


def _audit_event_id(*, receipt_id: str, action: str) -> UUID:
    return uuid5(_AUDIT_EVENT_NAMESPACE, f"{receipt_id}:{action}")


def _hmac_ip(value: str) -> str:
    return hmac.new(
        _ip_hmac_secret(),
        _IP_HMAC_CONTEXT + value.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _ip_hmac_secret() -> bytes:
    secret = settings.remnawave_stream_ip_hmac_secret.get_secret_value().strip()
    if len(secret) < 32:
        raise RemnawaveConnectionDropAuditUnavailableError("Connection drop IP audit hashing is not configured")
    return secret.encode("utf-8")
