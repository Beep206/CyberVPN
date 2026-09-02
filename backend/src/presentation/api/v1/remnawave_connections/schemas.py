"""Audience-specific public schemas for Remnawave connection operations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, model_validator

from .reconciliation import (
    RECEIPT_ID_PATTERN,
    RECONCILIATION_REFERENCE_PATTERN,
    RemnawaveConnectionDropReconciliationReason,
)


class RemnawaveConnectionsCapabilitiesResponse(BaseModel):
    read_connections: bool = True
    # Destructive availability is actor/runtime-specific and must be supplied
    # by the route after RBAC, object grants and receipt configuration checks.
    drop_connections: bool = False
    drop_requires_idempotency_key: bool = True
    drop_outcome_may_be_unknown: bool = True


class RemnawaveConnectionReadRequestResponse(BaseModel):
    request_id: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")
    poll_after_seconds: int = Field(default=1, ge=1, le=10)
    expires_in_seconds: int = Field(default=300, ge=60, le=600)
    capabilities: RemnawaveConnectionsCapabilitiesResponse = Field(
        default_factory=RemnawaveConnectionsCapabilitiesResponse
    )


class RemnawaveConnectionDropReceiptResponse(BaseModel):
    receipt_id: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")
    state: Literal["accepted", "outcome_unknown"]
    retry_allowed: Literal[False] = False
    requires_reconciliation: bool
    expires_at: datetime | None = None
    expires_in_seconds: int | None = Field(default=None, ge=0, le=604_800)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.state == "outcome_unknown":
            if self.expires_at is not None or self.expires_in_seconds is not None:
                raise ValueError("Ambiguous drop receipts do not expire before reconciliation")
            if not self.requires_reconciliation:
                raise ValueError("Ambiguous drop receipts require reconciliation")
        else:
            if self.expires_at is None or self.expires_in_seconds is None:
                raise ValueError("Accepted drop receipts require an expiry")
            if self.requires_reconciliation:
                raise ValueError("Accepted drop receipts do not require reconciliation")
        return self


class AdminRemnawaveConnectionDropReconciliationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["accepted", "rejected"]
    reason: RemnawaveConnectionDropReconciliationReason
    reference: str = Field(min_length=11, max_length=64, pattern=RECONCILIATION_REFERENCE_PATTERN)

    @model_validator(mode="after")
    def validate_reason_matches_outcome(self) -> Self:
        applied = self.reason in {
            RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED,
            RemnawaveConnectionDropReconciliationReason.POSTCONDITION_CONFIRMED_APPLIED,
        }
        if (self.outcome == "accepted") != applied:
            raise ValueError("Reconciliation reason does not match the terminal outcome")
        return self


class AdminRemnawaveConnectionDropReceiptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(min_length=43, max_length=43, pattern=RECEIPT_ID_PATTERN)
    state: Literal["outcome_unknown", "accepted", "rejected"]
    audience: Literal["admin", "partner", "customer"]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    expires_in_seconds: int | None = Field(default=None, ge=0, le=604_800)
    requires_reconciliation: bool
    reconciled_at: datetime | None
    reconciliation_reason: RemnawaveConnectionDropReconciliationReason | None
    reconciliation_reference: str | None = Field(default=None, min_length=11, max_length=64)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        reconciliation_values = (
            self.reconciled_at,
            self.reconciliation_reason,
            self.reconciliation_reference,
        )
        has_reconciliation = all(value is not None for value in reconciliation_values)
        if any(value is not None for value in reconciliation_values) and not has_reconciliation:
            raise ValueError("Reconciliation metadata must be complete")
        if self.state == "outcome_unknown":
            if (
                self.expires_at is not None
                or self.expires_in_seconds is not None
                or not self.requires_reconciliation
                or has_reconciliation
            ):
                raise ValueError("Ambiguous drop receipt lifecycle is inconsistent")
        elif self.expires_at is None or self.expires_in_seconds is None or self.requires_reconciliation:
            raise ValueError("Terminal drop receipt lifecycle is inconsistent")
        return self


class AdminRemnawaveConnectionDropUnresolvedPageResponse(BaseModel):
    items: list[AdminRemnawaveConnectionDropReceiptResponse]
    next_cursor: str | None = Field(default=None, min_length=43, max_length=43, pattern=RECEIPT_ID_PATTERN)


class RemnawaveConnectionProgressResponse(BaseModel):
    total: int = Field(ge=0)
    completed: int = Field(ge=0)
    percent: float = Field(ge=0, le=100)


class AdminRemnawaveConnectionIpResponse(BaseModel):
    ip: str = Field(min_length=2, max_length=64)
    last_seen: datetime


class AdminRemnawaveUserConnectionNodeResponse(BaseModel):
    node_uuid: UUID
    node_name: str = Field(max_length=256)
    country_code: str = Field(max_length=16)
    ips: list[AdminRemnawaveConnectionIpResponse]


class AdminRemnawaveUserConnectionsResultResponse(BaseModel):
    success: bool
    user_id: int = Field(ge=1)
    nodes: list[AdminRemnawaveUserConnectionNodeResponse]


class AdminRemnawaveUserConnectionsStatusResponse(BaseModel):
    is_completed: bool
    is_failed: bool
    progress: RemnawaveConnectionProgressResponse
    result: AdminRemnawaveUserConnectionsResultResponse | None
    capabilities: RemnawaveConnectionsCapabilitiesResponse = Field(
        default_factory=RemnawaveConnectionsCapabilitiesResponse
    )


class AdminRemnawaveNodeConnectionUserResponse(BaseModel):
    user_id: int = Field(ge=1)
    ips: list[AdminRemnawaveConnectionIpResponse]


class AdminRemnawaveNodeConnectionsResultResponse(BaseModel):
    success: bool
    node_uuid: UUID
    users: list[AdminRemnawaveNodeConnectionUserResponse]


class AdminRemnawaveNodeConnectionsStatusResponse(BaseModel):
    is_completed: bool
    is_failed: bool
    result: AdminRemnawaveNodeConnectionsResultResponse | None
    capabilities: RemnawaveConnectionsCapabilitiesResponse = Field(
        default_factory=RemnawaveConnectionsCapabilitiesResponse
    )


class PartnerRemnawaveNodeConnectionsStatusResponse(BaseModel):
    is_completed: bool
    is_failed: bool
    success: bool | None
    node_uuid: UUID
    connected_user_count: int | None = Field(default=None, ge=0)
    active_ip_count: int | None = Field(default=None, ge=0)
    last_seen_at: datetime | None
    capabilities: RemnawaveConnectionsCapabilitiesResponse = Field(
        default_factory=RemnawaveConnectionsCapabilitiesResponse
    )


class CustomerRemnawaveConnectionsStatusResponse(BaseModel):
    is_completed: bool
    is_failed: bool
    progress: RemnawaveConnectionProgressResponse
    success: bool | None
    connected: bool | None
    connected_node_count: int | None = Field(default=None, ge=0)
    active_ip_count: int | None = Field(default=None, ge=0)
    last_seen_at: datetime | None
    capabilities: RemnawaveConnectionsCapabilitiesResponse = Field(
        default_factory=RemnawaveConnectionsCapabilitiesResponse
    )


class AdminDropByUserIds(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    by: Literal["userIds"]
    user_ids: list[int] = Field(alias="userIds", min_length=1, max_length=1_000)


class AdminDropByIpAddresses(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    by: Literal["ipAddresses"]
    ip_addresses: list[IPvAnyAddress] = Field(alias="ipAddresses", min_length=1, max_length=1_000)


class AdminDropOnAllNodes(BaseModel):
    target: Literal["allNodes"]


class AdminDropOnSpecificNodes(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target: Literal["specificNodes"]
    node_uuids: list[UUID] = Field(alias="nodeUuids", min_length=1, max_length=128)


AdminDropBy = Annotated[AdminDropByUserIds | AdminDropByIpAddresses, Field(discriminator="by")]
AdminDropTargetNodes = Annotated[
    AdminDropOnAllNodes | AdminDropOnSpecificNodes,
    Field(discriminator="target"),
]


class AdminRemnawaveConnectionDropRequest(BaseModel):
    """Exact Remnawave 3.4.3 drop shape."""

    model_config = ConfigDict(populate_by_name=True)

    drop_by: AdminDropBy = Field(alias="dropBy")
    target_nodes: AdminDropTargetNodes = Field(alias="targetNodes")


class PartnerRemnawaveConnectionDropRequest(BaseModel):
    """Partner names one opaque, exactly granted service identity.

    Numeric Remnawave IDs and IP targets are deliberately unavailable at this
    boundary. The backend resolves the canonical numeric user only after both
    node and service-identity grants have been verified.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    service_identity_uuid: UUID = Field(alias="serviceIdentityUuid")
