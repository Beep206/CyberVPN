"""Pydantic schemas for invite code endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RedeemInviteRequest(BaseModel):
    """Request body for redeeming an invite code."""

    code: str = Field(..., min_length=1, max_length=32, description="Invite code to redeem")


class InviteCodeResponse(BaseModel):
    """Response schema for a single invite code."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    free_days: int
    is_used: bool
    expires_at: datetime | None
    created_at: datetime


class AdminCreateInviteRequest(BaseModel):
    """Request body for admin-created invite codes."""

    user_id: UUID = Field(..., description="User who will own the invite codes")
    free_days: int = Field(..., gt=0, description="Number of free subscription days the code grants")
    count: int = Field(1, ge=1, le=100, description="Number of codes to generate")
    plan_id: UUID | None = Field(None, description="Optional plan to associate with the codes")
