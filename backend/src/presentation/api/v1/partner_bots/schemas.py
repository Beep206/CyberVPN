"""Schemas for PartnerBot foundation APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import (
    PartnerBotProvisioningJobStatus,
    PartnerBotProvisioningPath,
    PartnerBotStatus,
    PartnerBotTokenStatus,
)


class PartnerBotProvisioningJobResponse(BaseModel):
    id: UUID
    partner_bot_id: UUID
    partner_account_id: UUID
    requested_by_admin_user_id: UUID | None = None
    provisioning_path: str
    job_status: str
    attempt_count: int
    request_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    last_error: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PartnerBotResponse(BaseModel):
    id: UUID
    partner_account_id: UUID
    storefront_id: UUID | None = None
    bot_key: str
    display_name: str
    short_description: str | None = None
    long_description: str | None = None
    telegram_bot_id: str | None = None
    telegram_username: str | None = None
    managed_by_bot_id: str | None = None
    default_locale: str
    primary_color: str | None = None
    provisioning_path: str
    token_status: str
    status: str
    release_channel: str
    provisioning_last_error: str | None = None
    provisioning_requested_at: datetime | None = None
    provisioned_at: datetime | None = None
    suspended_at: datetime | None = None
    suspension_reason_code: str | None = None
    created_by_admin_user_id: UUID | None = None
    updated_by_admin_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    latest_provisioning_job: PartnerBotProvisioningJobResponse | None = None


class CreatePartnerBotRequest(BaseModel):
    partner_account_id: UUID
    bot_key: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9](?:[a-z0-9-]{1,48}[a-z0-9])?$")
    display_name: str = Field(..., min_length=1, max_length=120)
    default_locale: str = Field(default="en-EN", min_length=2, max_length=16)
    primary_color: str | None = Field(default=None, max_length=20)
    short_description: str | None = Field(default=None, max_length=255)
    long_description: str | None = None
    storefront_id: UUID | None = None
    release_channel: str = Field(default="stable", pattern=r"^(stable|beta|canary)$")
    provisioning_path: PartnerBotProvisioningPath = PartnerBotProvisioningPath.MANAGED_BOT


class RequestPartnerBotProvisioningRequest(BaseModel):
    provisioning_path: PartnerBotProvisioningPath | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)


class SuspendPartnerBotRequest(BaseModel):
    reason_code: str | None = Field(default=None, max_length=80)


class RotatePartnerBotTokenRequest(BaseModel):
    request_payload: dict[str, Any] = Field(default_factory=dict)


class ListPartnerBotsFilters(BaseModel):
    partner_account_id: UUID
    bot_status: PartnerBotStatus | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ClaimPartnerBotProvisioningJobRequest(BaseModel):
    processor_id: str = Field(..., min_length=1, max_length=120)
    max_scan_count: int = Field(default=10, ge=1, le=100)


class ClaimPartnerBotProvisioningJobResponse(BaseModel):
    bot: PartnerBotResponse | None = None


class FinalizePartnerBotProvisioningJobRequest(BaseModel):
    processor_id: str = Field(..., min_length=1, max_length=120)
    job_status: PartnerBotProvisioningJobStatus
    result_payload: dict[str, Any] = Field(default_factory=dict)
    last_error: str | None = None
    telegram_bot_id: str | None = Field(default=None, max_length=64)
    telegram_username: str | None = Field(default=None, max_length=64)
    managed_by_bot_id: str | None = Field(default=None, max_length=64)
    token_status: PartnerBotTokenStatus | None = None
