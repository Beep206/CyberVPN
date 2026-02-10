"""Pydantic schemas for the trial period endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrialActivateResponse(BaseModel):
    """Response schema for trial activation."""

    model_config = ConfigDict(from_attributes=True)

    activated: bool = Field(description="Whether trial was successfully activated")
    trial_end: datetime = Field(description="When the trial period ends")
    message: str = Field(description="Human-readable status message")


class TrialStatusResponse(BaseModel):
    """Response schema for trial status inquiry."""

    model_config = ConfigDict(from_attributes=True)

    is_trial_active: bool = Field(description="Whether user is currently on trial")
    trial_start: datetime | None = Field(None, description="When trial started")
    trial_end: datetime | None = Field(None, description="When trial ends/ended")
    days_remaining: int = Field(0, description="Days remaining in trial")
    is_eligible: bool = Field(description="Whether user is eligible for trial (hasn't used one)")
