"""Admin schemas for mobile user management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminMobileDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: str
    platform: str
    platform_id: str
    os_version: str
    app_version: str
    device_model: str
    push_token: str | None
    registered_at: datetime
    last_active_at: datetime | None


class AdminMobileUserListItemResponse(BaseModel):
    id: UUID
    email: str
    username: str | None
    status: str
    is_active: bool
    is_partner: bool
    telegram_id: int | None
    telegram_username: str | None
    remnawave_uuid: str | None
    referral_code: str | None
    referred_by_user_id: UUID | None
    partner_user_id: UUID | None
    partner_promoted_at: datetime | None
    created_at: datetime
    last_login_at: datetime | None
    device_count: int


class AdminMobileUsersListResponse(BaseModel):
    items: list[AdminMobileUserListItemResponse]
    total: int
    offset: int
    limit: int


class AdminMobileUserDetailResponse(AdminMobileUserListItemResponse):
    subscription_url: str | None
    updated_at: datetime
    devices: list[AdminMobileDeviceResponse]


class AdminUpdateMobileUserRequest(BaseModel):
    email: str | None = Field(None, max_length=255)
    username: str | None = Field(None, max_length=50)
    telegram_id: int | None = None
    telegram_username: str | None = Field(None, max_length=100)
    referral_code: str | None = Field(None, max_length=12)
    status: str | None = None
    is_active: bool | None = None


class AdminMobileUserSubscriptionSnapshotResponse(BaseModel):
    exists: bool
    remnawave_uuid: str | None = None
    status: str | None = None
    short_uuid: str | None = None
    subscription_uuid: str | None = None
    expires_at: datetime | None = None
    days_left: int | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    download_bytes: int | None = None
    upload_bytes: int | None = None
    lifetime_used_traffic_bytes: int | None = None
    online_at: datetime | None = None
    sub_last_user_agent: str | None = None
    sub_revoked_at: datetime | None = None
    last_traffic_reset_at: datetime | None = None
    hwid_device_limit: int | None = None
    subscription_url: str | None = None
    config_available: bool = False
    config: str | None = None
    config_client_type: str | None = None
    config_error: str | None = None
    links: list[str] = Field(default_factory=list)
    ss_conf_links: dict[str, str] = Field(default_factory=dict)
