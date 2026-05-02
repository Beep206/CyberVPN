"""Admin API schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Response schema for audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_id: UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class WebhookLogResponse(BaseModel):
    """Response schema for webhook log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    event_type: str | None = None
    payload: dict[str, Any]
    is_valid: bool | None = None
    error_message: str | None = None
    processed_at: datetime | None = None
    created_at: datetime


class AdminSettingsResponse(BaseModel):
    """Response schema for admin settings."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: Any
    description: str | None = None
    updated_at: datetime


class AdminMiniAppRuntimeRolloutResponse(BaseModel):
    enabled: bool
    mode: Literal["live", "canary", "maintenance", "rollback"] = "live"
    trial_enabled: bool
    checkout_enabled: bool
    config_enabled: bool
    maintenance_message: str | None = None
    canary_telegram_user_ids: list[int] = Field(default_factory=list)


class AdminMiniAppRuntimeConfigResponse(BaseModel):
    key: str
    rollout: AdminMiniAppRuntimeRolloutResponse
    description: str | None = None
    updated_at: datetime | None = None
    updated_by: UUID | None = None


class UpdateAdminMiniAppRuntimeConfigRequest(BaseModel):
    enabled: bool
    mode: Literal["live", "canary", "maintenance", "rollback"] = "live"
    trial_enabled: bool
    checkout_enabled: bool
    config_enabled: bool
    maintenance_message: str | None = None
    canary_telegram_user_ids: list[int] = Field(default_factory=list)
    change_reason: str | None = None


class AdminMiniAppLaunchReadinessResponse(BaseModel):
    observability_acknowledged: bool
    incident_runbook_acknowledged: bool
    checkout_canary_passed: bool
    config_delivery_canary_passed: bool
    rollback_drill_acknowledged: bool
    support_window_confirmed: bool
    customer_comms_ready: bool
    status_page_template_ready: bool
    incident_channel: str | None = None
    rollback_commander: str | None = None
    primary_oncall_contact: str | None = None
    release_window_note: str | None = None
    is_ready: bool


class AdminMiniAppLaunchReadinessConfigResponse(BaseModel):
    key: str
    readiness: AdminMiniAppLaunchReadinessResponse
    description: str | None = None
    updated_at: datetime | None = None
    updated_by: UUID | None = None


class UpdateAdminMiniAppLaunchReadinessConfigRequest(BaseModel):
    observability_acknowledged: bool
    incident_runbook_acknowledged: bool
    checkout_canary_passed: bool
    config_delivery_canary_passed: bool
    rollback_drill_acknowledged: bool
    support_window_confirmed: bool
    customer_comms_ready: bool
    status_page_template_ready: bool
    incident_channel: str | None = None
    rollback_commander: str | None = None
    primary_oncall_contact: str | None = None
    release_window_note: str | None = None
    change_reason: str | None = None


class AdminMiniAppLaunchSummaryResponse(BaseModel):
    launch_state: Literal[
        "live",
        "ready_for_live",
        "canary_in_progress",
        "rollback_in_progress",
        "maintenance",
        "blocked",
    ]
    live_switch_allowed: bool
    next_action: Literal[
        "promote_to_live",
        "complete_launch_gates",
        "keep_canary",
        "finish_rollback",
        "hold_maintenance",
        "stabilize_runtime",
    ]
    primary_action: Literal[
        "promote_to_live",
        "enter_maintenance",
        "start_rollback",
        "return_to_canary",
    ] | None = None
    available_actions: list[
        Literal[
            "promote_to_live",
            "enter_maintenance",
            "start_rollback",
            "return_to_canary",
        ]
    ] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    runtime: AdminMiniAppRuntimeRolloutResponse
    readiness: AdminMiniAppLaunchReadinessResponse


class AdminMiniAppLaunchTimelineEntryResponse(BaseModel):
    id: UUID
    created_at: datetime
    admin_id: UUID | None = None
    action: str
    event_type: Literal[
        "runtime_update",
        "launch_readiness_update",
        "launch_action",
    ]
    action_name: Literal[
        "promote_to_live",
        "enter_maintenance",
        "start_rollback",
        "return_to_canary",
    ] | None = None
    resulting_runtime_mode: Literal["live", "canary", "maintenance", "rollback"] | None = None
    resulting_launch_state: Literal[
        "live",
        "ready_for_live",
        "canary_in_progress",
        "rollback_in_progress",
        "maintenance",
        "blocked",
    ] | None = None
    readiness_ready: bool | None = None
    change_reason: str | None = None
    entity_id: str | None = None


class ExecuteAdminMiniAppLaunchActionRequest(BaseModel):
    action: Literal[
        "promote_to_live",
        "enter_maintenance",
        "start_rollback",
        "return_to_canary",
    ]
    change_reason: str | None = None
