"""Pydantic schemas for the trial period endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.use_cases.trial.stage1_trial_policy import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_DURATION_DAYS,
    STAGE1_TRIAL_ONE_PER_ACCOUNT,
    STAGE1_TRIAL_POLICY_CONTEXT,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
)


class TrialActivateResponse(BaseModel):
    """Response schema for trial activation."""

    model_config = ConfigDict(from_attributes=True)

    activated: bool = Field(description="Whether trial was successfully activated")
    trial_end: datetime = Field(description="When the trial period ends")
    message: str = Field(description="Human-readable status message")
    duration_days: int = Field(
        STAGE1_TRIAL_DURATION_DAYS,
        description="Canonical S1 trial duration in days",
    )
    device_limit: int = Field(
        STAGE1_TRIAL_DEVICE_LIMIT,
        description="Canonical S1 trial device limit",
    )
    traffic_limit_bytes: int = Field(
        STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
        description="Canonical S1 trial traffic limit in bytes",
    )
    one_trial_per_account: bool = Field(
        STAGE1_TRIAL_ONE_PER_ACCOUNT,
        description="Whether S1 allows only one trial per account",
    )
    policy_context: dict = Field(
        default_factory=lambda: dict(STAGE1_TRIAL_POLICY_CONTEXT),
        description="Smallest compatible S1 policy context; Stage 1 does not vary trial by country/channel/segment.",
    )


class TrialStatusResponse(BaseModel):
    """Response schema for trial status inquiry."""

    model_config = ConfigDict(from_attributes=True)

    is_trial_active: bool = Field(description="Whether user is currently on trial")
    trial_start: datetime | None = Field(None, description="When trial started")
    trial_end: datetime | None = Field(None, description="When trial ends/ended")
    days_remaining: int = Field(0, description="Days remaining in trial")
    is_eligible: bool = Field(description="Whether user is eligible for trial (hasn't used one)")
    duration_days: int = Field(
        STAGE1_TRIAL_DURATION_DAYS,
        description="Canonical S1 trial duration in days",
    )
    device_limit: int = Field(
        STAGE1_TRIAL_DEVICE_LIMIT,
        description="Canonical S1 trial device limit",
    )
    traffic_limit_bytes: int = Field(
        STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
        description="Canonical S1 trial traffic limit in bytes",
    )
    one_trial_per_account: bool = Field(
        STAGE1_TRIAL_ONE_PER_ACCOUNT,
        description="Whether S1 allows only one trial per account",
    )
    policy_context: dict = Field(
        default_factory=lambda: dict(STAGE1_TRIAL_POLICY_CONTEXT),
        description="Smallest compatible S1 policy context; Stage 1 does not vary trial by country/channel/segment.",
    )
