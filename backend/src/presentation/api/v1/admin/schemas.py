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
    primary_action: (
        Literal[
            "promote_to_live",
            "enter_maintenance",
            "start_rollback",
            "return_to_canary",
        ]
        | None
    ) = None
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
    action_name: (
        Literal[
            "promote_to_live",
            "enter_maintenance",
            "start_rollback",
            "return_to_canary",
        ]
        | None
    ) = None
    resulting_runtime_mode: Literal["live", "canary", "maintenance", "rollback"] | None = None
    resulting_launch_state: (
        Literal[
            "live",
            "ready_for_live",
            "canary_in_progress",
            "rollback_in_progress",
            "maintenance",
            "blocked",
        ]
        | None
    ) = None
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


class AdminCustomerSiteRuntimeResponse(BaseModel):
    mode: Literal["full_site", "cabinet_only", "maintenance"] = "full_site"
    version: int = 1
    public_hosts: list[str] = Field(default_factory=list)
    cabinet_hosts: list[str] = Field(default_factory=list)
    cabinet_destination_path: str = "/dashboard"
    allowed_path_prefixes: list[str] = Field(default_factory=list)
    cabinet_allowed_prefixes: list[str] = Field(default_factory=list)
    cabinet_marketing_route_action: Literal["redirect_public", "allow", "not_found"] = "redirect_public"
    public_marketing_destination_path: str = "/"
    legal_path_prefixes: list[str] = Field(default_factory=list)
    operational_path_prefixes: list[str] = Field(default_factory=list)
    preserve_query_keys: list[str] = Field(default_factory=list)
    cabinet_only: bool = False
    registration_policy_independent: bool = True


class AdminCustomerSiteRuntimeConfigResponse(BaseModel):
    key: str
    site: AdminCustomerSiteRuntimeResponse
    description: str | None = None
    updated_at: datetime | None = None
    updated_by: UUID | None = None
    last_change_reason: str | None = None


class UpdateAdminCustomerSiteRuntimeConfigRequest(BaseModel):
    mode: Literal["full_site", "cabinet_only", "maintenance"]
    public_hosts: list[str] = Field(default_factory=list, max_length=50)
    cabinet_hosts: list[str] = Field(default_factory=list, max_length=50)
    cabinet_destination_path: str = Field(default="/dashboard", min_length=1, max_length=160)
    allowed_path_prefixes: list[str] = Field(default_factory=list, max_length=50)
    cabinet_allowed_prefixes: list[str] = Field(default_factory=list, max_length=100)
    cabinet_marketing_route_action: Literal["redirect_public", "allow", "not_found"] | None = None
    public_marketing_destination_path: str | None = Field(None, min_length=1, max_length=160)
    legal_path_prefixes: list[str] = Field(default_factory=list, max_length=50)
    operational_path_prefixes: list[str] = Field(default_factory=list, max_length=50)
    preserve_query_keys: list[str] = Field(default_factory=list, max_length=50)
    expected_version: int = Field(ge=1)
    change_reason: str = Field(min_length=3, max_length=200)


class ExecuteAdminCustomerSiteRuntimeActionRequest(BaseModel):
    action: Literal["rollback_to_full_site"]
    expected_version: int = Field(ge=1)
    change_reason: str = Field(min_length=3, max_length=200)


class AdminCustomerSiteRuntimeTimelineEntryResponse(BaseModel):
    id: UUID
    created_at: datetime
    admin_id: UUID | None = None
    action: str
    event_type: Literal["site_mode_update", "site_mode_action"]
    resulting_mode: Literal["full_site", "cabinet_only", "maintenance"] | None = None
    resulting_version: int | None = None
    change_reason: str | None = None
    entity_id: str | None = None
