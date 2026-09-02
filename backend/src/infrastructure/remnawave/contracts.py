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
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
    model_validator,
)

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
        validate_by_name=True,
        validate_by_alias=True,
        extra="ignore",
    )


_REMNAWAVE_PUBLIC_CONFIG_DENY_KEYS = frozenset(
    {
        "accesstoken",
        "client",
        "clientid",
        "clients",
        "keys",
        "password",
        "passwd",
        "privatekey",
        "realityprivatekey",
        "refreshtoken",
        "secret",
        "token",
    }
)


def _sanitize_remnawave_public_config(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_item in value.items():
            key = str(raw_key)
            normalized_key = key.replace("_", "").replace("-", "").lower()
            if normalized_key in _REMNAWAVE_PUBLIC_CONFIG_DENY_KEYS:
                continue
            sanitized[key] = _sanitize_remnawave_public_config(raw_item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_remnawave_public_config(item) for item in value]
    return value


class StatusMessageResponse(RemnawaveBaseResponse):
    """Generic status + message response returned by many mutating endpoints."""

    status: str = Field(..., description="Operation status")
    message: str | None = Field(default=None, max_length=1000, description="Status message")


class RemnawaveDeleteResponse(RemnawaveBaseResponse):
    """Validated delete acknowledgement from Remnawave.

    Some delete endpoints return ``{"isDeleted": true}``, while others may
    acknowledge deletion with an empty ``204`` body. ``is_deleted`` defaults to
    ``True`` so an empty body still validates as a successful delete, but
    unexpected extra fields are forbidden to avoid silently accepting unrelated
    payloads.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid",
    )

    is_deleted: bool = Field(True, alias="isDeleted", description="Delete acknowledged by upstream")


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------


class RemnawaveUserResponse(RemnawaveBaseResponse):
    """Full user object as returned by the Remnawave ``/api/users`` endpoints.

    Mirrors every field from the upstream JSON including traffic counters and
    optional metadata that the admin dashboard needs for the user detail view.
    """

    uuid: str | None = Field(default=None, description="Legacy Remnawave 2.x user UUID retained for rollback")
    username: str = Field(..., description="Unique username")
    status: str = Field(..., description="User status (active/disabled/limited/expired)")
    short_uuid: str = Field(default="", alias="shortUuid", description="Short UUID for display")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")

    # Subscription
    subscription_uuid: str | None = Field(
        default=None, alias="subscriptionUuid", description="Linked subscription UUID"
    )
    subscription_url: str | None = Field(default=None, alias="subscriptionUrl", description="User subscription URL")
    expire_at: datetime | None = Field(default=None, alias="expireAt", description="Expiration timestamp")
    auto_renew: bool | None = Field(
        default=None,
        alias="autoRenew",
        validation_alias=AliasChoices("autoRenew", "auto_renew"),
        description="Legacy 2.8 renewal opt-in captured only during expand reconciliation",
    )
    traffic_limit_strategy: str | None = Field(
        default=None,
        alias="trafficLimitStrategy",
        description="Traffic reset strategy returned by Remnawave 3.x",
    )
    active_internal_squads: list[str | dict[str, Any]] | None = Field(
        default=None,
        alias="activeInternalSquads",
        description="Assigned internal squads as UUID strings or expanded squad objects",
    )
    external_squad_uuid: str | None = Field(
        default=None,
        alias="externalSquadUuid",
        description="Assigned external squad UUID",
    )

    # Traffic counters
    traffic_limit_bytes: int | None = Field(
        default=None, alias="trafficLimitBytes", description="Traffic limit in bytes (None = unlimited)"
    )
    used_traffic_bytes: int | None = Field(
        default=None,
        alias="usedTrafficBytes",
        validation_alias=AliasChoices("usedTrafficBytes", AliasPath("userTraffic", "usedTrafficBytes")),
        description="Current period used traffic",
    )
    download_bytes: int | None = Field(default=None, alias="downloadBytes", description="Download traffic in bytes")
    upload_bytes: int | None = Field(default=None, alias="uploadBytes", description="Upload traffic in bytes")
    lifetime_used_traffic_bytes: int | None = Field(
        default=None,
        alias="lifetimeUsedTrafficBytes",
        validation_alias=AliasChoices(
            "lifetimeUsedTrafficBytes",
            AliasPath("userTraffic", "lifetimeUsedTrafficBytes"),
        ),
        description="Lifetime total traffic",
    )

    # Connectivity and subscription state
    online_at: datetime | None = Field(
        default=None,
        alias="onlineAt",
        validation_alias=AliasChoices("onlineAt", AliasPath("userTraffic", "onlineAt")),
        description="Last online timestamp",
    )
    sub_last_user_agent: str | None = Field(
        default=None, alias="subLastUserAgent", description="Last subscription user-agent"
    )
    sub_revoked_at: datetime | None = Field(
        default=None, alias="subRevokedAt", description="Subscription revocation timestamp"
    )
    last_traffic_reset_at: datetime | None = Field(
        default=None, alias="lastTrafficResetAt", description="Last traffic counter reset"
    )

    # External identifiers
    telegram_id: int | None = Field(default=None, alias="telegramId", description="Linked Telegram user ID")
    email: str | None = Field(default=None, description="User email address")
    remnawave_numeric_id: int | None = Field(
        default=None,
        alias="id",
        validation_alias=AliasChoices("id", "userId", "numericId"),
        description="Optional numeric identifier returned by newer Remnawave APIs",
    )

    @field_validator("remnawave_numeric_id", mode="before")
    @classmethod
    def require_exact_positive_numeric_identity(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("Remnawave numeric user id must be an exact positive integer")
        return value

    used_traffic_percentage: float | None = Field(
        default=None,
        alias="usedTrafficPercentage",
        description="Optional upstream traffic usage percentage",
    )

    # Device management
    hwid_device_limit: int | None = Field(
        default=None, alias="hwidDeviceLimit", description="Max hardware-ID bound devices"
    )
    hwid_active: int | bool | None = Field(
        default=None,
        alias="hwidActive",
        validation_alias=AliasChoices("hwidActive", "hwidDevicesActive", "activeHwidDevices"),
        description="Remnawave 2.8 active HWID device signal when included in payloads",
    )

    # Nested relationships (present in some response variants)
    active_user_inbounds: list[dict[str, Any]] | None = Field(
        default=None, alias="activeUserInbounds", description="Active inbound assignments"
    )

    @model_validator(mode="after")
    def require_user_identity(self) -> RemnawaveUserResponse:
        if self.remnawave_numeric_id is None and not self.uuid:
            raise ValueError("Remnawave user response requires id or legacy uuid")
        return self


class RemnawaveUserListResponse(RemnawaveBaseResponse):
    """Wrapper returned by ``GET /api/users`` when the upstream paginates."""

    response: list[RemnawaveUserResponse] = Field(default_factory=list, description="List of users")
    total: int | None = Field(default=None, description="Total user count")


# ---------------------------------------------------------------------------
# Node / Server models
# ---------------------------------------------------------------------------


class RemnawaveNodeIpResponse(RemnawaveBaseResponse):
    """One typed IP assignment from the Remnawave 3.4 node contract."""

    ip: IPvAnyAddress
    status: Literal[
        "INBOUND",
        "OUTBOUND",
        "MANAGEMENT",
        "TRANSIT",
        "MONITORING",
        "RESERVE",
        "BLOCKED",
        "FLAGGED",
        "DEPRECATED",
        "UNKNOWN",
    ]


class RemnawaveNodeResponse(RemnawaveBaseResponse):
    """Node (server) object from the Remnawave ``/api/nodes`` endpoints."""

    uuid: str = Field(..., description="Node UUID")
    id: int | None = Field(default=None, gt=0, description="Remnawave 3.x numeric node identifier")
    name: str = Field(..., description="Node display name")
    address: str = Field(default="", description="Node address or hostname")
    port: int | None = Field(default=None, description="Node port")
    is_connected: bool = Field(False, alias="isConnected", description="Connection status")
    is_disabled: bool = Field(False, alias="isDisabled", description="Disabled flag")
    is_connecting: bool = Field(False, alias="isConnecting", description="Currently connecting")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")

    # Optional metadata
    country_code: str | None = Field(default=None, alias="countryCode", description="ISO country code")
    traffic_limit_bytes: int | None = Field(default=None, alias="trafficLimitBytes", description="Node traffic limit")
    used_traffic_bytes: int | None = Field(
        default=None,
        alias="usedTrafficBytes",
        validation_alias=AliasChoices("usedTrafficBytes", "trafficUsedBytes"),
        description="Node used traffic",
    )
    inbound_count: int | None = Field(default=None, alias="inboundCount", description="Number of inbound configs")
    users_online: int | None = Field(default=None, alias="usersOnline", description="Currently connected users")
    xray_version: str | None = Field(
        default=None,
        alias="xrayVersion",
        validation_alias=AliasChoices("xrayVersion", AliasPath("versions", "xray")),
        description="Running Xray version",
    )
    node_version: str | None = Field(
        default=None,
        alias="nodeVersion",
        validation_alias=AliasChoices("nodeVersion", AliasPath("versions", "node")),
        description="Running Remnawave node version",
    )
    vpn_protocol: str | None = Field(default=None, alias="vpnProtocol", description="Primary VPN protocol")
    active_plugin_uuid: str | None = Field(
        default=None, alias="activePluginUuid", description="Active governance plugin UUID"
    )
    consumption_multiplier: float | None = Field(
        default=None,
        alias="consumptionMultiplier",
        validation_alias=AliasChoices("consumptionMultiplier", "nodeConsumptionMultiplier"),
        description="Traffic consumption multiplier",
    )
    node_consumption_multiplier: float | None = Field(
        default=None,
        alias="nodeConsumptionMultiplier",
        description="Remnawave 2.8 node consumption multiplier",
    )
    note: str | None = Field(default=None, description="Operator note")
    proxy_url: str | None = Field(default=None, alias="proxyUrl", description="Optional upstream node proxy URL")
    tags: list[str] = Field(default_factory=list, description="Node tags when returned by upstream")
    ips: list[RemnawaveNodeIpResponse] = Field(
        default_factory=list,
        description="Remnawave 3.x node IPv4/IPv6 address inventory",
    )
    integration_uuids: list[str] = Field(
        default_factory=list,
        alias="integrationUuids",
        description="Remnawave integrations assigned to this node",
    )
    cpu_load_1m: float | None = Field(
        default=None,
        alias="cpuLoad1m",
        validation_alias=AliasChoices(
            "cpuLoad1m",
            "cpuLoadAverage1m",
            "loadAverage1m",
            AliasPath("metrics", "cpuLoad1m"),
        ),
        description="Remnawave 2.8 node CPU load average over 1 minute",
    )
    cpu_load_5m: float | None = Field(
        default=None,
        alias="cpuLoad5m",
        validation_alias=AliasChoices(
            "cpuLoad5m",
            "cpuLoadAverage5m",
            "loadAverage5m",
            AliasPath("metrics", "cpuLoad5m"),
        ),
        description="Remnawave 2.8 node CPU load average over 5 minutes",
    )
    cpu_load_15m: float | None = Field(
        default=None,
        alias="cpuLoad15m",
        validation_alias=AliasChoices(
            "cpuLoad15m",
            "cpuLoadAverage15m",
            "loadAverage15m",
            AliasPath("metrics", "cpuLoad15m"),
        ),
        description="Remnawave 2.8 node CPU load average over 15 minutes",
    )
    notification_enabled: bool | None = Field(
        default=None, alias="notificationEnabled", description="Notification flag"
    )


class RemnawaveNodeListResponse(RemnawaveBaseResponse):
    """Wrapper for ``GET /api/nodes`` list responses."""

    response: list[RemnawaveNodeResponse] = Field(default_factory=list, description="List of nodes")


# ---------------------------------------------------------------------------
# Inbound models
# ---------------------------------------------------------------------------


class RemnawaveInboundResponse(RemnawaveBaseResponse):
    """Inbound (protocol listener) from Remnawave config-profile inbound endpoints."""

    uuid: str = Field(..., description="Inbound UUID")
    tag: str = Field(..., description="Inbound tag identifier")
    protocol: str = Field(
        ...,
        validation_alias=AliasChoices("protocol", "type", AliasPath("rawInbound", "protocol")),
        description="Protocol (vless, vmess, trojan, shadowsocks, etc.)",
    )
    port: int = Field(..., description="Listening port")
    network: str | None = Field(default=None, description="Transport network type (tcp, ws, grpc, etc.)")
    transport: str | None = Field(default=None, description="Transport identifier when returned separately")
    security: str | None = Field(default=None, description="Security type (tls, reality, none)")
    tls: str | None = Field(default=None, description="TLS mode")
    settings: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("settings", AliasPath("rawInbound", "settings")),
        description="Raw protocol settings",
    )
    stream_settings: dict[str, Any] | None = Field(
        default=None,
        alias="streamSettings",
        validation_alias=AliasChoices("streamSettings", AliasPath("rawInbound", "streamSettings")),
        description="Stream/transport settings",
    )
    sniffing: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("sniffing", AliasPath("rawInbound", "sniffing")),
        description="Sniffing configuration",
    )

    # Node association
    node_uuid: str | None = Field(default=None, alias="nodeUuid", description="Parent node UUID")
    tags: list[str] = Field(default_factory=list, description="Inbound tags when returned by upstream")

    @field_validator("settings", "stream_settings", "sniffing", mode="before")
    @classmethod
    def _sanitize_public_config(cls, value: Any) -> Any:
        return _sanitize_remnawave_public_config(value)


class RemnawaveInboundListResponse(RemnawaveBaseResponse):
    """Wrapper for Remnawave inbound list responses."""

    response: list[RemnawaveInboundResponse] = Field(default_factory=list, description="List of inbounds")


# ---------------------------------------------------------------------------
# Host models
# ---------------------------------------------------------------------------


class RemnawaveHostResponse(RemnawaveBaseResponse):
    """Host entry from the Remnawave ``/api/hosts`` endpoints."""

    uuid: str = Field(..., description="Host UUID")
    inbound_uuid: str | None = Field(default=None, alias="inboundUuid", description="Associated inbound UUID")
    remark: str | None = Field(default=None, description="Host remark/display name")
    address: str = Field(default="", description="Host address")
    port: int | None = Field(default=None, description="Host port (overrides inbound port)")
    sni: str | None = Field(default=None, description="Server Name Indication")
    host: str | None = Field(default=None, description="HTTP Host header value")
    path: str | None = Field(default=None, description="WebSocket / HTTP path")
    alpn: list[str] | None = Field(default=None, description="ALPN protocols")
    fingerprint: str | None = Field(default=None, description="TLS fingerprint profile")
    is_disabled: bool = Field(False, alias="isDisabled", description="Disabled flag")
    security: str | None = Field(default=None, description="Security layer (tls/reality/none)")
    reality_public_key: str | None = Field(default=None, alias="realityPublicKey", description="REALITY public key")
    reality_short_id: str | None = Field(default=None, alias="realityShortId", description="REALITY short ID")
    reality_private_key: str | None = Field(default=None, alias="realityPrivateKey", description="REALITY private key")
    tag: str | None = Field(default=None, description="Legacy single Remnawave host tag")
    tags: list[str] = Field(default_factory=list, description="Remnawave 2.8 multiple host tags")
    verify_peer_cert_by_name: bool | None = Field(
        default=None,
        alias="verifyPeerCertByName",
        description="Remnawave 2.8 peer certificate name verification flag",
    )
    mihomo_ip_version: str | None = Field(
        default=None,
        alias="mihomoIpVersion",
        description="Mihomo IP version selector",
    )
    pinned_peer_cert_sha256: str | None = Field(
        default=None,
        alias="pinnedPeerCertSha256",
        description="Pinned upstream peer certificate SHA-256",
    )
    allow_insecure: bool | None = Field(
        default=None,
        alias="allowInsecure",
        description="Legacy compatibility for pre-2.8 allowInsecure hosts",
    )
    xhttp_extra_params: dict[str, Any] | None = Field(
        default=None,
        alias="xhttpExtraParams",
        validation_alias=AliasChoices("xhttpExtraParams", "xhttp", "xhttpOpts", "xhttpOptions"),
        description="XHTTP transport options when Remnawave exposes them on hosts",
    )
    ech: dict[str, Any] | None = Field(default=None, description="ECH settings when exposed by Remnawave")
    exclude_hosts_by_tags: list[str] | None = Field(
        default=None,
        alias="excludeHostsByTags",
        description="Response-rule host tag exclusion policy when embedded",
    )
    internal_squads: dict[str, Any] | None = Field(
        default=None,
        alias="internalSquads",
        description="Remnawave 3.x host squad selector: {mode, squads}",
    )

    @model_validator(mode="after")
    def normalize_tags(self) -> RemnawaveHostResponse:
        if not self.tags and self.tag:
            self.tags = [self.tag]
        return self


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
    host_uuid: str | None = Field(default=None, alias="hostUuid", description="Associated host UUID")
    inbound_tag: str | None = Field(default=None, alias="inboundTag", description="Inbound tag reference")
    flow: str | None = Field(default=None, description="Flow control method (xtls-rprx-vision, etc.)")
    config_data: dict[str, Any] | None = Field(default=None, alias="configData", description="Additional config blob")
    description: str | None = Field(
        default=None, alias="description", description="Template description/DESCRIPTION key"
    )
    client_type: str | None = Field(default=None, alias="clientType", description="Subscription client family")
    xhttp: dict[str, Any] | None = Field(default=None, description="XHTTP template metadata when returned")
    hysteria2: dict[str, Any] | None = Field(default=None, description="Hysteria2 template metadata when returned")
    v2plus: dict[str, Any] | None = Field(default=None, description="v2plus fallback metadata when returned")


class RemnawaveSubscriptionUserSummary(RemnawaveBaseResponse):
    """Minimal user summary embedded in subscription lookup responses."""

    short_uuid: str = Field(..., alias="shortUuid", description="User short UUID")
    username: str = Field(..., description="Username")
    days_left: int | None = Field(default=None, alias="daysLeft", description="Days left until expiration")
    expires_at: datetime | None = Field(default=None, alias="expiresAt", description="Expiration timestamp")
    is_active: bool | None = Field(default=None, alias="isActive", description="Whether subscription is active")
    user_status: str | None = Field(default=None, alias="userStatus", description="Remnawave user status")


class RemnawaveSubscriptionDetailsResponse(RemnawaveBaseResponse):
    """Validated response for ``GET /api/subscriptions/by-uuid/{uuid}``."""

    is_found: bool = Field(..., alias="isFound", description="Whether the subscription record exists")
    user: RemnawaveSubscriptionUserSummary | None = Field(default=None, description="Embedded user summary")
    links: list[str] = Field(default_factory=list, description="Generated connection links")
    ss_conf_links: dict[str, str] = Field(
        default_factory=dict,
        alias="ssConfLinks",
        description="Shadowsocks config links keyed by remark",
    )
    subscription_url: str | None = Field(
        default=None,
        alias="subscriptionUrl",
        max_length=5000,
        description="Subscription URL for VPN clients",
    )
    headers: dict[str, Any] | None = Field(default=None, description="Optional upstream response headers snapshot")
    xhttp_links: list[str] = Field(default_factory=list, alias="xhttpLinks", description="XHTTP links when returned")
    hysteria2_links: list[str] = Field(
        default_factory=list,
        alias="hysteria2Links",
        description="Hysteria2 links when returned",
    )


class RemnawaveSubscriptionConfigResponse(RemnawaveBaseResponse):
    """Generated subscription config for a specific user."""

    config: str = Field(..., description="Generated VPN configuration string")
    is_found: bool = Field(True, alias="isFound", description="Whether the upstream subscription record exists")
    links: list[str] = Field(default_factory=list, description="All generated connection links")
    ss_conf_links: dict[str, str] = Field(
        default_factory=dict,
        alias="ssConfLinks",
        description="Shadowsocks config links keyed by remark",
    )
    subscription_url: str | None = Field(
        default=None,
        alias="subscriptionUrl",
        max_length=5000,
        description="Subscription URL for VPN clients",
    )
    xhttp_enabled: bool = Field(False, alias="xhttpEnabled", description="Whether XHTTP links are present")
    xhttp_links: list[str] = Field(default_factory=list, alias="xhttpLinks", description="XHTTP connection links")
    x_hwid_active: str | int | bool | None = Field(
        default=None,
        alias="xHwidActive",
        validation_alias=AliasChoices("xHwidActive", "x-hwid-active", "x-hwid-limit"),
        description="Remnawave 2.8 HWID active signal with legacy header compatibility",
    )


class RemnawaveCursorPage(RemnawaveBaseResponse):
    """Cursor pagination envelope introduced by newer Remnawave user sync APIs."""

    response: list[dict[str, Any]] = Field(default_factory=list, description="Raw cursor page items")
    users: list[dict[str, Any]] = Field(default_factory=list, description="Alternate users key")
    next_cursor: str | None = Field(
        default=None,
        alias="nextCursor",
        validation_alias=AliasChoices("nextCursor", "cursor", "next"),
        description="Cursor for the next page",
    )
    has_next_page: bool | None = Field(
        default=None,
        alias="hasNextPage",
        validation_alias=AliasChoices("hasNextPage", "hasMore", "hasNext"),
        description="Whether more items are available",
    )
    total: int | None = Field(default=None, description="Total users when reported by upstream")

    @property
    def items(self) -> list[dict[str, Any]]:
        return self.response or self.users


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
    data_limit_gb: int | None = Field(default=None, alias="dataLimitGb", description="Data limit in gigabytes")
    max_devices: int | None = Field(default=None, alias="maxDevices", description="Max simultaneous devices")
    features: list[str] | None = Field(default=None, description="Plan feature list")
    is_active: bool = Field(True, alias="isActive", description="Plan active flag")


# ---------------------------------------------------------------------------
# System / Settings models
# ---------------------------------------------------------------------------


class RemnawaveSettingResponse(RemnawaveBaseResponse):
    """System setting key-value pair from Remnawave."""

    id: int = Field(..., description="Setting ID")
    key: str = Field(..., description="Setting key")
    value: Any = Field(..., description="Setting value (any JSON type)")
    description: str | None = Field(default=None, description="Setting description")
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
    total_bytes: int | None = Field(default=None, alias="totalBytes", description="Total bytes (in + out)")


class RemnawaveBandwidthWindowResponse(RemnawaveBaseResponse):
    """Single analytics window from ``/api/system/stats/bandwidth``."""

    current: int = Field(0, description="Current period bandwidth")
    previous: int = Field(0, description="Previous period bandwidth")
    difference: int = Field(0, description="Difference between periods")


class RemnawaveBandwidthAnalyticsResponse(RemnawaveBaseResponse):
    """Raw Remnawave bandwidth analytics payload."""

    bandwidth_last_two_days: RemnawaveBandwidthWindowResponse = Field(alias="bandwidthLastTwoDays")
    bandwidth_last_seven_days: RemnawaveBandwidthWindowResponse = Field(alias="bandwidthLastSevenDays")
    bandwidth_last_30_days: RemnawaveBandwidthWindowResponse = Field(alias="bandwidthLast30Days")
    bandwidth_calendar_month: RemnawaveBandwidthWindowResponse = Field(alias="bandwidthCalendarMonth")
    bandwidth_current_year: RemnawaveBandwidthWindowResponse = Field(alias="bandwidthCurrentYear")


class RemnawaveUsersStatsPayload(RemnawaveBaseResponse):
    """User aggregate block from ``/api/system/stats``."""

    total_users: int = Field(0, alias="totalUsers")
    status_counts: dict[str, int] = Field(default_factory=dict, alias="statusCounts")


class RemnawaveOnlineStatsPayload(RemnawaveBaseResponse):
    """Online user metrics block from ``/api/system/stats``."""

    last_day: int = Field(0, alias="lastDay")
    last_week: int = Field(0, alias="lastWeek")
    never_online: int = Field(0, alias="neverOnline")
    online_now: int = Field(0, alias="onlineNow")


class RemnawaveNodesStatsPayload(RemnawaveBaseResponse):
    """Node aggregate block from ``/api/system/stats``."""

    total_online: int = Field(0, alias="totalOnline")
    total_bytes_lifetime: int = Field(0, alias="totalBytesLifetime")


class RemnawaveRawSystemStatsResponse(RemnawaveBaseResponse):
    """Raw Remnawave system stats payload used by monitoring use cases."""

    users: RemnawaveUsersStatsPayload
    online_stats: RemnawaveOnlineStatsPayload = Field(alias="onlineStats")
    nodes: RemnawaveNodesStatsPayload


class RemnawaveRecapPeriodResponse(RemnawaveBaseResponse):
    """Period summary block from ``/api/system/stats/recap``."""

    users: int = Field(0, description="User count for the period")
    traffic: int = Field(0, description="Traffic for the period")


class RemnawaveRecapTotalResponse(RemnawaveBaseResponse):
    """Lifetime recap totals from Remnawave."""

    users: int = Field(0, description="Total users")
    nodes: int = Field(0, description="Total nodes")
    traffic: int = Field(0, description="Lifetime traffic")
    nodes_ram: str | None = Field(default=None, alias="nodesRam")
    nodes_cpu_cores: int | None = Field(default=None, alias="nodesCpuCores")
    distinct_countries: int | None = Field(default=None, alias="distinctCountries")


class RemnawaveRecapResponse(RemnawaveBaseResponse):
    """Raw Remnawave recap payload used by monitoring use cases."""

    total: RemnawaveRecapTotalResponse
    this_month: RemnawaveRecapPeriodResponse | None = Field(default=None, alias="thisMonth")
    version: str | None = None
    init_date: datetime | None = Field(default=None, alias="initDate")


class RemnawaveMetadataBuildResponse(RemnawaveBaseResponse):
    """Build metadata from ``/api/system/metadata``."""

    time: str = Field(..., description="Build timestamp")
    number: str = Field(..., description="Build number")


class RemnawaveMetadataGitBackendResponse(RemnawaveBaseResponse):
    """Backend git metadata from ``/api/system/metadata``."""

    commit_sha: str = Field(..., alias="commitSha")
    branch: str = Field(..., description="Backend branch")
    commit_url: str = Field(..., alias="commitUrl")


class RemnawaveMetadataGitFrontendResponse(RemnawaveBaseResponse):
    """Frontend git metadata from ``/api/system/metadata``."""

    commit_sha: str = Field(..., alias="commitSha")
    commit_url: str = Field(..., alias="commitUrl")


class RemnawaveMetadataGitResponse(RemnawaveBaseResponse):
    """Git metadata block from ``/api/system/metadata``."""

    backend: RemnawaveMetadataGitBackendResponse
    frontend: RemnawaveMetadataGitFrontendResponse


class RemnawaveMetadataResponse(RemnawaveBaseResponse):
    """Validated response for ``GET /api/system/metadata``."""

    version: str = Field(..., description="Remnawave panel version")
    build: RemnawaveMetadataBuildResponse
    git: RemnawaveMetadataGitResponse


class RemnawaveCreatedSubscriptionResponse(RemnawaveBaseResponse):
    """Create-subscription acknowledgement returned by Remnawave."""

    id: str | int | None = Field(default=None, description="Subscription identifier")
    uuid: str | None = Field(default=None, description="Subscription UUID")
    expires_at: datetime | None = Field(
        default=None, alias="expiresAt", description="Subscription expiration timestamp"
    )


# ---------------------------------------------------------------------------
# Xray config models
# ---------------------------------------------------------------------------


class RemnawaveXrayConfigResponse(RemnawaveBaseResponse):
    """Xray-core configuration blob from Remnawave ``/api/xray/config``."""

    log: dict[str, Any] | None = Field(default=None, description="Xray log configuration")
    inbounds: list[dict[str, Any]] | None = Field(default=None, description="Xray inbound listeners")
    outbounds: list[dict[str, Any]] | None = Field(default=None, description="Xray outbound proxies")
    routing: dict[str, Any] | None = Field(default=None, description="Xray routing rules")
    dns: dict[str, Any] | None = Field(default=None, description="Xray DNS configuration")
    policy: dict[str, Any] | None = Field(default=None, description="Xray policy configuration")


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
    payment_method: str | None = Field(default=None, alias="paymentMethod", description="Payment method")
    created_at: datetime | None = Field(default=None, alias="createdAt", description="Creation timestamp")


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
    description: str | None = Field(default=None, description="Profile description")

    @model_validator(mode="before")
    @classmethod
    def normalize_remnawave_2_8_profile(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        if "profileType" not in normalized and "profile_type" not in normalized:
            normalized["profileType"] = "xray" if isinstance(normalized.get("config"), dict) else "unknown"
        if "content" not in normalized:
            normalized["content"] = ""
        if "isDefault" not in normalized and "is_default" not in normalized:
            normalized["isDefault"] = False
        return normalized


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
    order: int | None = Field(default=None, description="Display/execution order")


# ---------------------------------------------------------------------------
# Squad models
# ---------------------------------------------------------------------------


class RemnawaveSquadResponse(RemnawaveBaseResponse):
    """Squad (user group) from Remnawave."""

    uuid: str = Field(..., description="Squad UUID")
    name: str = Field(..., description="Squad name")
    squad_type: str = Field(..., alias="squadType", description="Squad type (internal/external)")
    max_members: int | None = Field(default=None, alias="maxMembers", description="Maximum squad members")
    is_active: bool = Field(True, alias="isActive", description="Active flag")
    description: str | None = Field(default=None, description="Squad description")
    member_count: int | None = Field(default=None, alias="memberCount", description="Current member count")


class RemnawaveRawSquadInfoResponse(RemnawaveBaseResponse):
    """Nested info object returned by the upstream squads endpoints."""

    members_count: int | None = Field(default=None, alias="membersCount", description="Current member count")


class RemnawaveRawSquadResponse(RemnawaveBaseResponse):
    """Raw squad item from the upstream internal/external squads endpoints."""

    uuid: str = Field(..., description="Squad UUID")
    name: str = Field(..., description="Squad name")
    info: RemnawaveRawSquadInfoResponse | None = Field(default=None, description="Additional squad info")


# ---------------------------------------------------------------------------
# Keygen models
# ---------------------------------------------------------------------------


class RemnawavePublicKeyResponse(RemnawaveBaseResponse):
    """Public key response from Remnawave ``/api/keygen``."""

    public_key: str = Field(..., alias="publicKey", description="Public key in PEM format")
    algorithm: str = Field(default="RS256", description="Key algorithm")


class RemnawaveSignPayloadResponse(RemnawaveBaseResponse):
    """Signed payload response from Remnawave ``/api/keygen``."""

    signature: str = Field(..., description="Generated digital signature")
    algorithm: str = Field(default="RS256", description="Signing algorithm used")


# ---------------------------------------------------------------------------
# Health / diagnostic models
# ---------------------------------------------------------------------------


class RemnawaveHealthResponse(RemnawaveBaseResponse):
    """Health check response from Remnawave ``/api/health``."""

    status: str = Field(..., description="Health status")
    version: str | None = Field(default=None, description="Remnawave version")
    uptime: int | None = Field(default=None, description="Uptime in seconds")
