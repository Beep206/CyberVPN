"""Pydantic schemas for notification preferences endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class NotificationPreferencesResponse(BaseModel):
    """Response schema for notification preferences (BF2-5)."""

    model_config = ConfigDict(from_attributes=True)

    email_security: bool = Field(True, description="Security alerts via email")
    email_marketing: bool = Field(False, description="Marketing communications via email")
    push_connection: bool = Field(True, description="VPN connection status push notifications")
    push_payment: bool = Field(True, description="Payment and subscription push notifications")
    push_subscription: bool = Field(True, description="Subscription expiry push notifications")


class NotificationPreferencesUpdateRequest(BaseModel):
    """Request schema for updating notification preferences (BF2-5).

    All fields are optional - only provided fields will be updated.
    """

    email_security: bool | None = Field(None, description="Security alerts via email")
    email_marketing: bool | None = Field(None, description="Marketing communications via email")
    push_connection: bool | None = Field(None, description="VPN connection status push notifications")
    push_payment: bool | None = Field(None, description="Payment and subscription push notifications")
    push_subscription: bool | None = Field(None, description="Subscription expiry push notifications")
