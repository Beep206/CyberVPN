from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerOnboardingCurrentResponse(BaseModel):
    required: bool
    status: Literal["disabled", "unavailable", "pending", "completed", "skipped"]
    flow_key: str
    version: int
    allowed_code_types: list[Literal["promo", "invite", "gift"]]
    flow_token: str | None = None
    message_key: str
    server_state_available: bool
    referral_already_attributed: bool = False
    connection_required: bool = False


class CustomerOnboardingApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=64)
    flow_token: str | None = Field(None, min_length=16, max_length=240)
    idempotency_key: str | None = Field(None, min_length=1, max_length=120)
    source_surface: Literal["web", "miniapp", "telegram_bot"] = "web"
    telegram_id: int | None = Field(None, gt=0)


class CustomerOnboardingApplyResponse(BaseModel):
    status: Literal["pending", "completed", "skipped"]
    message_key: str
    masked_code: str | None = None
    next_destination: str = "/dashboard"
    connection_required: bool = False


class CustomerOnboardingPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=64)
    flow_token: str | None = Field(None, min_length=16, max_length=240)


class CustomerOnboardingPreviewResponse(BaseModel):
    accepted: bool
    detected_code_type: Literal["promo", "invite", "gift", "referral", "partner"] | None
    status: Literal[
        "preview_available",
        "not_found",
        "ambiguous",
        "wrong_context",
        "not_eligible",
        "expired",
        "already_used",
        "blocked",
    ]
    message_key: str
    masked_code: str
    matched_code_types: list[str] = Field(default_factory=list)
    next_action: Literal[
        "apply_now",
        "stage_for_checkout",
        "redeem_entitlement",
        "resolve_ambiguity",
        "none",
    ]
    safe_details: dict[str, object] = Field(default_factory=dict)


class CustomerOnboardingSkipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_token: str | None = Field(None, min_length=16, max_length=240)
    idempotency_key: str | None = Field(None, min_length=1, max_length=120)


class CustomerOnboardingSkipResponse(BaseModel):
    status: Literal["skipped", "completed"]
    message_key: str
    next_destination: str = "/dashboard"


class CustomerOnboardingConnectionInstructionStep(BaseModel):
    order: int = Field(..., ge=1, le=6)
    title_key: str
    body_key: str
    action_url: str | None = None
    copy_value: str | None = None


class CustomerOnboardingConnectionAppRecommendation(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    url: str | None = Field(None, max_length=500)
    platform_store: str | None = Field(None, max_length=80)


class CustomerOnboardingConnectionInstruction(BaseModel):
    platform: Literal["ios", "android", "windows", "macos", "linux"]
    title_key: str
    steps: list[CustomerOnboardingConnectionInstructionStep] = Field(default_factory=list)
    recommended_apps: list[CustomerOnboardingConnectionAppRecommendation] = Field(default_factory=list)


CustomerOnboardingConnectionSupportedAction = Literal[
    "copy_subscription_url",
    "open_subscription_url",
    "show_qr",
    "send_qr_image",
    "show_instructions",
    "mark_connected",
    "open_dashboard",
    "open_miniapp",
]


class TelegramConnectionPayloadResponse(BaseModel):
    intro_message_key: str
    safe_profile_label: str | None = None
    subscription_url_button_text_key: str = "onboarding.connection.openLink"
    instructions_button_text_key: str = "onboarding.connection.instructions"
    mark_connected_button_text_key: str = "onboarding.connection.connected"
    dashboard_button_text_key: str = "onboarding.connection.goDashboard"
    qr_caption_key: str = "onboarding.connection.qrCaption"
    bot_connection_session_id: str | None = None
    preferred_platform: Literal["ios", "android", "windows", "macos", "linux", "unknown"] = "unknown"


class CustomerOnboardingConnectionBootstrapResponse(BaseModel):
    available: bool
    status: Literal[
        "available",
        "no_active_entitlement",
        "service_identity_pending",
        "config_unavailable",
        "disabled",
    ]
    message_key: str
    subscription_url: str | None = None
    qr_payload: str | None = None
    config_profile_name: str | None = None
    expires_at: str | None = None
    device_limit: int | None = Field(None, ge=0)
    traffic_limit_bytes: int | None = Field(None, ge=0)
    instructions: list[CustomerOnboardingConnectionInstruction] = Field(default_factory=list)
    surface: Literal["web", "miniapp", "telegram_bot"] = "web"
    preferred_layout: Literal["desktop_panel", "mobile_panel", "bot_messages"] = "desktop_panel"
    supported_actions: list[CustomerOnboardingConnectionSupportedAction] = Field(default_factory=list)
    connection_session_id: str | None = None
    telegram_payload: TelegramConnectionPayloadResponse | None = None
    flow_key: str | None = None
    version: int | None = None


class MarkOnboardingConnectionConnectedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_session_id: str = Field(..., min_length=1, max_length=80)
    flow_key: str | None = Field(None, min_length=1, max_length=80)
    version: int | None = Field(None, ge=1)
    platform: Literal["ios", "android", "windows", "macos", "linux", "unknown"] | None = "unknown"
    source_surface: Literal["web", "miniapp", "telegram_bot"] = "web"
    telegram_id: int | None = Field(None, gt=0)


class MarkOnboardingConnectionConnectedResponse(BaseModel):
    status: Literal["recorded", "already_recorded", "not_required"]
    next_destination: str
    connected_at: str | None = None
    flow_key: str | None = None
    version: int | None = None
