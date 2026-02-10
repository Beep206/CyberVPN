"""Pydantic v2 response models for all Remnawave proxy endpoints.

These schemas are used for:
- FastAPI ``response_model`` declarations on proxy routes
- ``RemnawaveClient.*_validated()`` methods that strip unexpected fields
  and raise 502 on validation failure

Design decisions:
- camelCase aliases match the Remnawave JSON wire format; ``populate_by_name``
  lets callers use either snake_case or camelCase.
- ``from_attributes=True`` enables constructing from domain dataclasses.
- ``Optional`` fields default to ``None`` because the upstream API may omit
  them depending on user state (e.g. ``expire_at`` is absent for unlimited
  accounts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared / generic helpers
# ---------------------------------------------------------------------------


class RemnawaveBaseResponse(BaseModel):
    """Common base for all Remnawave response schemas.

    Sets ``from_attributes`` for ORM / dataclass compat and enables
    ``populate_by_name`` so both camelCase (upstream JSON) and snake_case
    (Python) field names are accepted.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class StatusMessageResponse(RemnawaveBaseResponse):
    """Generic status + message response returned by many mutating endpoints."""

    status: str = Field(..., description="Operation status")
    message: str | None = Field(None, max_length=1000, description="Status message")


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------


class RemnawaveUserResponse(RemnawaveBaseResponse):
    """Full user object as returned by the Remnawave ``/api/users`` endpoints.

    Mirrors every field from the upstream JSON including traffic counters and
    optional metadata that the admin dashboard needs for the user detail view.
    """

    uuid: str = Field(..., description="User UUID")
    username: str = Field(..., description="Unique username")
    status: str = Field(..., description="User status (active/disabled/limited/expired)")
    short_uuid: str = Field("", alias="shortUuid", description="Short UUID for display")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")

    # Subscription
    subscription_uuid: str | None = Field(None, alias="subscriptionUuid", description="Linked subscription UUID")
    subscription_url: str | None = Field(None, alias="subscriptionUrl", description="User subscription URL")
    expire_at: datetime | None = Field(None, alias="expireAt", description="Expiration timestamp")

    # Traffic counters
    traffic_limit_bytes: int | None = Field(
        None, alias="trafficLimitBytes", description="Traffic limit in bytes (None = unlimited)"
    )
    used_traffic_bytes: int | None = Field(None, alias="usedTrafficBytes", description="Current period used traffic")
    download_bytes: int | None = Field(None, alias="downloadBytes", description="Download traffic in bytes")
    upload_bytes: int | None = Field(None, alias="uploadBytes", description="Upload traffic in bytes")
    lifetime_used_traffic_bytes: int | None = Field(
        None, alias="lifetimeUsedTrafficBytes", description="Lifetime total traffic"
    )

    # Connectivity and subscription state
    online_at: datetime | None = Field(None, alias="onlineAt", description="Last online timestamp")
    sub_last_user_agent: str | None = Field(None, alias="subLastUserAgent", description="Last subscription user-agent")
    sub_revoked_at: datetime | None = Field(None, alias="subRevokedAt", description="Subscription revocation timestamp")
    last_traffic_reset_at: datetime | None = Field(
        None, alias="lastTrafficResetAt", description="Last traffic counter reset"
    )

    # External identifiers
    telegram_id: int | None = Field(None, alias="telegramId", description="Linked Telegram user ID")
    email: str | None = Field(None, description="User email address")

    # Device management
    hwid_device_limit: int | None = Field(None, alias="hwidDeviceLimit", description="Max hardware-ID bound devices")

    # Nested relationships (present in some response variants)
    active_user_inbounds: list[dict[str, Any]] | None = Field(
        None, alias="activeUserInbounds", description="Active inbound assignments"
    )


class RemnawaveUserListResponse(RemnawaveBaseResponse):
    """Wrapper returned by ``GET /api/users`` when the upstream paginates."""

    response: list[RemnawaveUserResponse] = Field(default_factory=list, description="List of users")
    total: int | None = Field(None, description="Total user count")


# ---------------------------------------------------------------------------
# Node / Server models
# ---------------------------------------------------------------------------


class RemnawaveNodeResponse(RemnawaveBaseResponse):
    """Node (server) object from the Remnawave ``/api/nodes`` endpoints."""

    uuid: str = Field(..., description="Node UUID")
    name: str = Field(..., description="Node display name")
    address: str = Field("", description="Node address or hostname")
    port: int = Field(0, description="Node port")
    is_connected: bool = Field(False, alias="isConnected", description="Connection status")
    is_disabled: bool = Field(False, alias="isDisabled", description="Disabled flag")
    is_connecting: bool = Field(False, alias="isConnecting", description="Currently connecting")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")

    # Optional metadata
    country_code: str | None = Field(None, alias="countryCode", description="ISO country code")
    traffic_limit_bytes: int | None = Field(None, alias="trafficLimitBytes", description="Node traffic limit")
    used_traffic_bytes: int | None = Field(None, alias="usedTrafficBytes", description="Node used traffic")
    inbound_count: int | None = Field(None, alias="inboundCount", description="Number of inbound configs")
    users_online: int | None = Field(None, alias="usersOnline", description="Currently connected users")
    xray_version: str | None = Field(None, alias="xrayVersion", description="Running Xray version")
    vpn_protocol: str | None = Field(None, alias="vpnProtocol", description="Primary VPN protocol")
    consumption_multiplier: float | None = Field(
        None, alias="consumptionMultiplier", description="Traffic consumption multiplier"
    )
    notification_enabled: bool | None = Field(None, alias="notificationEnabled", description="Notification flag")


class RemnawaveNodeListResponse(RemnawaveBaseResponse):
    """Wrapper for ``GET /api/nodes`` list responses."""

    response: list[RemnawaveNodeResponse] = Field(default_factory=list, description="List of nodes")


# ---------------------------------------------------------------------------
# Inbound models
# ---------------------------------------------------------------------------


class RemnawaveInboundResponse(RemnawaveBaseResponse):
    """Inbound (protocol listener) from the Remnawave ``/api/inbounds`` endpoint."""

    uuid: str = Field(..., description="Inbound UUID")
    tag: str = Field(..., description="Inbound tag identifier")
    protocol: str = Field(..., description="Protocol (vless, vmess, trojan, shadowsocks, etc.)")
    port: int = Field(..., description="Listening port")
    network: str | None = Field(None, description="Transport network type (tcp, ws, grpc, etc.)")
    security: str | None = Field(None, description="Security type (tls, reality, none)")
    tls: str | None = Field(None, description="TLS mode")
    settings: dict[str, Any] | None = Field(None, description="Raw protocol settings")
    stream_settings: dict[str, Any] | None = Field(
        None, alias="streamSettings", description="Stream/transport settings"
    )
    sniffing: dict[str, Any] | None = Field(None, description="Sniffing configuration")

    # Node association
    node_uuid: str | None = Field(None, alias="nodeUuid", description="Parent node UUID")


class RemnawaveInboundListResponse(RemnawaveBaseResponse):
    """Wrapper for ``GET /api/inbounds`` list responses."""

    response: list[RemnawaveInboundResponse] = Field(default_factory=list, description="List of inbounds")


# ---------------------------------------------------------------------------
# Host models
# ---------------------------------------------------------------------------


class RemnawaveHostResponse(RemnawaveBaseResponse):
    """Host entry from the Remnawave ``/api/hosts`` endpoints."""

    uuid: str = Field(..., description="Host UUID")
    inbound_uuid: str | None = Field(None, alias="inboundUuid", description="Associated inbound UUID")
    remark: str | None = Field(None, description="Host remark/display name")
    address: str = Field("", description="Host address")
    port: int | None = Field(None, description="Host port (overrides inbound port)")
    sni: str | None = Field(None, description="Server Name Indication")
    host: str | None = Field(None, description="HTTP Host header value")
    path: str | None = Field(None, description="WebSocket / HTTP path")
    alpn: list[str] | None = Field(None, description="ALPN protocols")
    fingerprint: str | None = Field(None, description="TLS fingerprint profile")
    is_disabled: bool = Field(False, alias="isDisabled", description="Disabled flag")
    security: str | None = Field(None, description="Security layer (tls/reality/none)")
    reality_public_key: str | None = Field(None, alias="realityPublicKey", description="REALITY public key")
    reality_short_id: str | None = Field(None, alias="realityShortId", description="REALITY short ID")
    reality_private_key: str | None = Field(None, alias="realityPrivateKey", description="REALITY private key")


class RemnawaveHostListResponse(RemnawaveBaseResponse):
    """Wrapper for ``GET /api/hosts`` list responses."""

    response: list[RemnawaveHostResponse] = Field(default_factory=list, description="List of hosts")


# ---------------------------------------------------------------------------
# Subscription / template models
# ---------------------------------------------------------------------------


class RemnawaveSubscriptionResponse(RemnawaveBaseResponse):
    """Subscription template from Remnawave."""

    uuid: str = Field(..., description="Subscription template UUID")
    name: str = Field(..., description="Template display name")
    template_type: str = Field(..., alias="templateType", description="VPN client template type")
    host_uuid: str | None = Field(None, alias="hostUuid", description="Associated host UUID")
    inbound_tag: str | None = Field(None, alias="inboundTag", description="Inbound tag reference")
    flow: str | None = Field(None, description="Flow control method (xtls-rprx-vision, etc.)")
    config_data: dict[str, Any] | None = Field(None, alias="configData", description="Additional config blob")


class RemnawaveSubscriptionConfigResponse(RemnawaveBaseResponse):
    """Generated subscription config for a specific user."""

    config: str = Field(..., description="Generated VPN configuration string")
    subscription_url: str | None = Field(
        None,
        alias="subscriptionUrl",
        max_length=5000,
        description="Subscription URL for VPN clients",
    )


# ---------------------------------------------------------------------------
# Plan models
# ---------------------------------------------------------------------------


class RemnavwavePlanResponse(RemnawaveBaseResponse):
    """Subscription plan from Remnawave."""

    uuid: str = Field(..., description="Plan UUID")
    name: str = Field(..., description="Plan display name")
    price: float = Field(..., description="Plan price")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    duration_days: int = Field(..., alias="durationDays", description="Plan duration in days")
    data_limit_gb: int | None = Field(None, alias="dataLimitGb", description="Data limit in gigabytes")
    max_devices: int | None = Field(None, alias="maxDevices", description="Max simultaneous devices")
    features: list[str] | None = Field(None, description="Plan feature list")
    is_active: bool = Field(True, alias="isActive", description="Plan active flag")


# ---------------------------------------------------------------------------
# System / Settings models
# ---------------------------------------------------------------------------


class RemnawaveSettingResponse(RemnawaveBaseResponse):
    """System setting key-value pair from Remnawave."""

    id: int = Field(..., description="Setting ID")
    key: str = Field(..., description="Setting key")
    value: Any = Field(..., description="Setting value (any JSON type)")
    description: str | None = Field(None, description="Setting description")
    is_public: bool = Field(False, alias="isPublic", description="Public visibility flag")


class RemnawaveSystemStatsResponse(RemnawaveBaseResponse):
    """Aggregated system statistics from Remnawave nodes/users data."""

    total_users: int = Field(0, alias="totalUsers", description="Total user count")
    active_users: int = Field(0, alias="activeUsers", description="Active user count")
    total_servers: int = Field(0, alias="totalServers", description="Total server count")
    online_servers: int = Field(0, alias="onlineServers", description="Online server count")
    total_traffic_bytes: int = Field(0, alias="totalTrafficBytes", description="Total traffic in bytes")


class RemnavwaveBandwidthStatsResponse(RemnawaveBaseResponse):
    """Bandwidth analytics from Remnawave."""

    bytes_in: int = Field(0, alias="bytesIn", description="Incoming bytes")
    bytes_out: int = Field(0, alias="bytesOut", description="Outgoing bytes")
    total_bytes: int | None = Field(None, alias="totalBytes", description="Total bytes (in + out)")


# ---------------------------------------------------------------------------
# Xray config models
# ---------------------------------------------------------------------------


class RemnawaveXrayConfigResponse(RemnawaveBaseResponse):
    """Xray-core configuration blob from Remnawave ``/api/xray/config``."""

    log: dict[str, Any] | None = Field(None, description="Xray log configuration")
    inbounds: list[dict[str, Any]] | None = Field(None, description="Xray inbound listeners")
    outbounds: list[dict[str, Any]] | None = Field(None, description="Xray outbound proxies")
    routing: dict[str, Any] | None = Field(None, description="Xray routing rules")
    dns: dict[str, Any] | None = Field(None, description="Xray DNS configuration")
    policy: dict[str, Any] | None = Field(None, description="Xray policy configuration")


# ---------------------------------------------------------------------------
# Billing models
# ---------------------------------------------------------------------------


class RemnavwaveBillingRecordResponse(RemnawaveBaseResponse):
    """Billing / payment record from Remnawave."""

    uuid: str = Field(..., description="Billing record UUID")
    user_uuid: str = Field(..., alias="userUuid", description="User UUID")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    status: str = Field(..., description="Payment status")
    payment_method: str | None = Field(None, alias="paymentMethod", description="Payment method")
    created_at: datetime | None = Field(None, alias="createdAt", description="Creation timestamp")


# ---------------------------------------------------------------------------
# Config profile models
# ---------------------------------------------------------------------------


class RemnawaveConfigProfileResponse(RemnawaveBaseResponse):
    """Configuration profile from Remnawave."""

    uuid: str = Field(..., description="Profile UUID")
    name: str = Field(..., description="Profile name")
    profile_type: str = Field(..., alias="profileType", description="Profile type (clash/v2ray/etc.)")
    content: str = Field(..., description="Profile template content")
    is_default: bool = Field(False, alias="isDefault", description="Default profile flag")
    description: str | None = Field(None, description="Profile description")


# ---------------------------------------------------------------------------
# Snippet models
# ---------------------------------------------------------------------------


class RemnawaveSnippetResponse(RemnawaveBaseResponse):
    """Configuration snippet from Remnawave."""

    uuid: str = Field(..., description="Snippet UUID")
    name: str = Field(..., description="Snippet name")
    snippet_type: str = Field(..., alias="snippetType", description="Snippet type")
    content: str = Field(..., description="Snippet content")
    is_active: bool = Field(True, alias="isActive", description="Active flag")
    order: int | None = Field(None, description="Display/execution order")


# ---------------------------------------------------------------------------
# Squad models
# ---------------------------------------------------------------------------


class RemnawaveSquadResponse(RemnawaveBaseResponse):
    """Squad (user group) from Remnawave."""

    uuid: str = Field(..., description="Squad UUID")
    name: str = Field(..., description="Squad name")
    squad_type: str = Field(..., alias="squadType", description="Squad type (internal/external)")
    max_members: int | None = Field(None, alias="maxMembers", description="Maximum squad members")
    is_active: bool = Field(True, alias="isActive", description="Active flag")
    description: str | None = Field(None, description="Squad description")
    member_count: int | None = Field(None, alias="memberCount", description="Current member count")


# ---------------------------------------------------------------------------
# Keygen models
# ---------------------------------------------------------------------------


class RemnawavePublicKeyResponse(RemnawaveBaseResponse):
    """Public key response from Remnawave ``/api/keygen``."""

    public_key: str = Field(..., alias="publicKey", description="Public key in PEM format")
    algorithm: str = Field("RS256", description="Key algorithm")


class RemnawaveSignPayloadResponse(RemnawaveBaseResponse):
    """Signed payload response from Remnawave ``/api/keygen``."""

    signature: str = Field(..., description="Generated digital signature")
    algorithm: str = Field("RS256", description="Signing algorithm used")


# ---------------------------------------------------------------------------
# Health / diagnostic models
# ---------------------------------------------------------------------------


class RemnawaveHealthResponse(RemnawaveBaseResponse):
    """Health check response from Remnawave ``/api/health``."""

    status: str = Field(..., description="Health status")
    version: str | None = Field(None, description="Remnawave version")
    uptime: int | None = Field(None, description="Uptime in seconds")
