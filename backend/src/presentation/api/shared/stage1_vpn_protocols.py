"""S1 VPN protocol allowlist for Remnawave-backed provisioning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Stage1VpnProtocol(StrEnum):
    """Protocol names used in Remnawave/Xray-facing S1 contracts."""

    VLESS = "vless"
    WIREGUARD = "wireguard"
    OPENVPN = "openvpn"
    VMESS = "vmess"
    TROJAN = "trojan"
    SHADOWSOCKS = "shadowsocks"
    HYSTERIA2 = "hysteria2"
    TUIC = "tuic"
    HELIX = "helix"
    VERTA = "verta"
    BEEP = "beep"


class Stage1VpnTransport(StrEnum):
    """Transport/network names used by Xray/Remnawave raw subscription configs."""

    RAW = "raw"
    TCP = "tcp"
    XHTTP = "xhttp"
    WS = "ws"
    HTTPUPGRADE = "httpupgrade"
    GRPC = "grpc"
    KCP = "kcp"
    QUIC = "quic"
    UNKNOWN = "unknown"


class Stage1VpnSecurity(StrEnum):
    """Security mode used by S1 proxy configs."""

    REALITY = "reality"
    TLS = "tls"
    NONE = "none"
    UNKNOWN = "unknown"


class Stage1VpnProfileStatus(StrEnum):
    """S1 enablement state for a protocol profile."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class Stage1VpnProfileStage(StrEnum):
    """Launch stage that owns a protocol profile."""

    S1 = "S1"
    S2 = "S2"
    S4 = "S4"
    S5 = "S5"
    S6 = "S6"
    S7 = "S7"


@dataclass(frozen=True, slots=True)
class Stage1VpnProtocolProfile:
    """Single S1 protocol/profile decision row."""

    profile_id: str
    display_name: str
    protocol: Stage1VpnProtocol
    transport: Stage1VpnTransport
    security: Stage1VpnSecurity
    status: Stage1VpnProfileStatus
    stage: Stage1VpnProfileStage
    customer_visible: bool
    default_profile: bool = False
    required_for_s1: bool = False
    flow: str | None = None
    support_note: str = ""

    @property
    def enabled(self) -> bool:
        return self.status == Stage1VpnProfileStatus.ENABLED

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize safe profile metadata for internal APIs, docs and tests."""

        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "protocol": self.protocol.value,
            "transport": self.transport.value,
            "security": self.security.value,
            "status": self.status.value,
            "stage": self.stage.value,
            "customer_visible": self.customer_visible,
            "default_profile": self.default_profile,
            "required_for_s1": self.required_for_s1,
            "flow": self.flow,
            "support_note": self.support_note,
        }


STAGE1_DEFAULT_VPN_PROFILE_ID = "vless-reality-raw"
STAGE1_XHTTP_VPN_PROFILE_ID = "vless-reality-xhttp"


STAGE1_VPN_PROTOCOL_PROFILES: tuple[Stage1VpnProtocolProfile, ...] = (
    Stage1VpnProtocolProfile(
        profile_id=STAGE1_DEFAULT_VPN_PROFILE_ID,
        display_name="VLESS Reality RAW",
        protocol=Stage1VpnProtocol.VLESS,
        transport=Stage1VpnTransport.RAW,
        security=Stage1VpnSecurity.REALITY,
        status=Stage1VpnProfileStatus.ENABLED,
        stage=Stage1VpnProfileStage.S1,
        customer_visible=True,
        default_profile=True,
        required_for_s1=True,
        flow="xtls-rprx-vision",
        support_note="Default compatibility profile for S1 subscription URL, QR and config delivery.",
    ),
    Stage1VpnProtocolProfile(
        profile_id=STAGE1_XHTTP_VPN_PROFILE_ID,
        display_name="VLESS Reality XHTTP",
        protocol=Stage1VpnProtocol.VLESS,
        transport=Stage1VpnTransport.XHTTP,
        security=Stage1VpnSecurity.REALITY,
        status=Stage1VpnProfileStatus.ENABLED,
        stage=Stage1VpnProfileStage.S1,
        customer_visible=True,
        required_for_s1=True,
        support_note="Mandatory S1 alternate profile for clients and networks where XHTTP is the desired route.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="wireguard",
        display_name="WireGuard",
        protocol=Stage1VpnProtocol.WIREGUARD,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S4,
        customer_visible=False,
        support_note="Not part of Remnawave-backed S1 public beta; revisit with native/mobile channel readiness.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="openvpn",
        display_name="OpenVPN",
        protocol=Stage1VpnProtocol.OPENVPN,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S5,
        customer_visible=False,
        support_note="Out of S1; only reconsider for device expansion if operationally justified.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="vmess",
        display_name="VMess",
        protocol=Stage1VpnProtocol.VMESS,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S2,
        customer_visible=False,
        support_note="Legacy V2Ray-style protocol is not customer-visible in S1.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="trojan",
        display_name="Trojan",
        protocol=Stage1VpnProtocol.TROJAN,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S2,
        customer_visible=False,
        support_note="Remnawave may model it, but CyberVPN S1 does not expose it to users.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="shadowsocks",
        display_name="Shadowsocks",
        protocol=Stage1VpnProtocol.SHADOWSOCKS,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S2,
        customer_visible=False,
        support_note="Not a customer-visible S1 protocol profile.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="hysteria2",
        display_name="Hysteria2",
        protocol=Stage1VpnProtocol.HYSTERIA2,
        transport=Stage1VpnTransport.QUIC,
        security=Stage1VpnSecurity.TLS,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S5,
        customer_visible=False,
        support_note="Not part of S1; keep out of customer guides and provisioning contracts.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="tuic",
        display_name="TUIC",
        protocol=Stage1VpnProtocol.TUIC,
        transport=Stage1VpnTransport.QUIC,
        security=Stage1VpnSecurity.TLS,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S5,
        customer_visible=False,
        support_note="Not part of S1; keep out of customer guides and provisioning contracts.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="helix",
        display_name="Helix",
        protocol=Stage1VpnProtocol.HELIX,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S6,
        customer_visible=False,
        support_note="Private transport beta only; disabled/default-off in S1.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="verta",
        display_name="Verta",
        protocol=Stage1VpnProtocol.VERTA,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S6,
        customer_visible=False,
        support_note="Private transport beta only; disabled/default-off in S1.",
    ),
    Stage1VpnProtocolProfile(
        profile_id="beep",
        display_name="Beep",
        protocol=Stage1VpnProtocol.BEEP,
        transport=Stage1VpnTransport.UNKNOWN,
        security=Stage1VpnSecurity.UNKNOWN,
        status=Stage1VpnProfileStatus.DISABLED,
        stage=Stage1VpnProfileStage.S6,
        customer_visible=False,
        support_note="Private transport beta only; disabled/default-off in S1.",
    ),
)


def stage1_enabled_vpn_profiles() -> tuple[Stage1VpnProtocolProfile, ...]:
    """Return customer-visible S1 enabled VPN protocol profiles."""

    return tuple(
        profile
        for profile in STAGE1_VPN_PROTOCOL_PROFILES
        if profile.enabled and profile.stage == Stage1VpnProfileStage.S1
    )


def stage1_disabled_vpn_profiles() -> tuple[Stage1VpnProtocolProfile, ...]:
    """Return profiles that must not be provisioned or shown as S1 customer options."""

    return tuple(profile for profile in STAGE1_VPN_PROTOCOL_PROFILES if not profile.enabled)


def stage1_default_vpn_profile() -> Stage1VpnProtocolProfile:
    """Return the single default S1 VPN profile."""

    defaults = [profile for profile in stage1_enabled_vpn_profiles() if profile.default_profile]
    if len(defaults) != 1:
        raise RuntimeError("S1 VPN protocol contract must have exactly one default profile")
    return defaults[0]


def get_stage1_vpn_profile(profile_id: str) -> Stage1VpnProtocolProfile:
    """Resolve a profile by id."""

    normalized = profile_id.strip().lower()
    for profile in STAGE1_VPN_PROTOCOL_PROFILES:
        if profile.profile_id == normalized:
            return profile
    raise ValueError("Unknown S1 VPN protocol profile")


def resolve_stage1_remnawave_profile(
    *,
    protocol: str | None,
    transport: str | None,
    security: str | None,
) -> Stage1VpnProtocolProfile | None:
    """Map Remnawave/Xray protocol+transport+security fields to the S1 allowlist."""

    normalized_protocol = _normalize_protocol(protocol)
    normalized_transport = _normalize_transport(transport)
    normalized_security = _normalize_security(security)

    for profile in stage1_enabled_vpn_profiles():
        profile_transport = Stage1VpnTransport.RAW if profile.transport == Stage1VpnTransport.TCP else profile.transport
        if (
            profile.protocol == normalized_protocol
            and profile_transport == normalized_transport
            and profile.security == normalized_security
        ):
            return profile
    return None


def is_stage1_vpn_profile_enabled(profile_id: str) -> bool:
    """Return whether the profile id is allowed for S1 provisioning."""

    try:
        return get_stage1_vpn_profile(profile_id).enabled
    except ValueError:
        return False


def stage1_customer_vpn_protocol_summary() -> dict[str, Any]:
    """Return safe customer/support-facing protocol summary."""

    enabled = stage1_enabled_vpn_profiles()
    return {
        "default_profile_id": stage1_default_vpn_profile().profile_id,
        "enabled_profile_ids": [profile.profile_id for profile in enabled],
        "customer_visible_profile_ids": [profile.profile_id for profile in enabled if profile.customer_visible],
        "private_transports_disabled": {
            profile.profile_id: profile.stage.value
            for profile in stage1_disabled_vpn_profiles()
            if profile.protocol in {Stage1VpnProtocol.HELIX, Stage1VpnProtocol.VERTA, Stage1VpnProtocol.BEEP}
        },
    }


def _normalize_protocol(value: str | None) -> Stage1VpnProtocol | None:
    if not value:
        return None
    normalized = value.strip().lower()
    try:
        return Stage1VpnProtocol(normalized)
    except ValueError:
        return None


def _normalize_transport(value: str | None) -> Stage1VpnTransport | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized == Stage1VpnTransport.TCP:
        normalized = Stage1VpnTransport.RAW
    try:
        return Stage1VpnTransport(normalized)
    except ValueError:
        return None


def _normalize_security(value: str | None) -> Stage1VpnSecurity | None:
    if not value:
        return None
    try:
        return Stage1VpnSecurity(value.strip().lower())
    except ValueError:
        return None
