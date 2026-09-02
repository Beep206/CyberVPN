"""CyberVPN boundary schemas for the Remnawave 3.4.3 hosts API."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.infrastructure.remnawave.control_plane_contracts import (
    HostAlpn,
    HostMihomoIpVersion,
    HostSecurityLayer,
    RemnawaveHostMapper,
    RemnawaveHostV34Response,
    SubscriptionTemplateType,
)

HostTag = Annotated[str, Field(max_length=36, pattern=r"^[A-Z0-9_:]+$")]


class _HostRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_alias=True,
        validate_by_name=True,
        extra="forbid",
    )

    def to_upstream_payload(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json", exclude_unset=True)


class HostInboundRequest(_HostRequest):
    config_profile_uuid: UUID = Field(alias="configProfileUuid")
    config_profile_inbound_uuid: UUID = Field(alias="configProfileInboundUuid")


class HostInternalSquadsRequest(_HostRequest):
    mode: str = Field(pattern=r"^(EXCLUDE|ALLOW_ONLY)$")
    squads: list[UUID]


class CreateHostRequest(_HostRequest):
    """Exact target ``CreateHostBodyDto`` shape."""

    inbound: HostInboundRequest
    remark: str = Field(min_length=1, max_length=100)
    address: str
    port: int = Field(ge=-(2**53 - 1), le=2**53 - 1)
    path: list[str] | None = None
    sni: list[str] | None = None
    host: list[str] | None = None
    alpn: HostAlpn | None = None
    fingerprint: list[str] | None = None
    is_disabled: bool = Field(default=False, alias="isDisabled")
    security_layer: HostSecurityLayer = Field(default="DEFAULT", alias="securityLayer")
    xhttp_extra_params: Any | None = Field(default=None, alias="xhttpExtraParams")
    mux_params: Any | None = Field(default=None, alias="muxParams")
    sockopt_params: Any | None = Field(default=None, alias="sockoptParams")
    final_mask: Any | None = Field(default=None, alias="finalMask")
    server_description: str | None = Field(default=None, alias="serverDescription", max_length=30)
    tags: list[HostTag] | None = Field(default=None, max_length=10)
    is_hidden: bool = Field(default=False, alias="isHidden")
    override_sni_from_address: bool = Field(default=False, alias="overrideSniFromAddress")
    keep_sni_blank: bool = Field(default=False, alias="keepSniBlank")
    pinned_peer_cert_sha256: list[str] | None = Field(default=None, alias="pinnedPeerCertSha256")
    verify_peer_cert_by_name: list[str] | None = Field(default=None, alias="verifyPeerCertByName")
    vless_route_id: int | None = Field(default=None, alias="vlessRouteId", ge=0, le=65535)
    shuffle_host: bool = Field(default=False, alias="shuffleHost")
    mihomo_x25519: bool = Field(default=False, alias="mihomoX25519")
    mihomo_ip_version: HostMihomoIpVersion | None = Field(default=None, alias="mihomoIpVersion")
    nodes: list[UUID] | None = None
    xray_json_template_uuid: UUID | None = Field(default=None, alias="xrayJsonTemplateUuid")
    exclude_from_subscription_types: list[SubscriptionTemplateType] | None = Field(
        default=None,
        alias="excludeFromSubscriptionTypes",
    )
    mapper: RemnawaveHostMapper | None = None
    internal_squads: HostInternalSquadsRequest | None = Field(default=None, alias="internalSquads")

    @model_validator(mode="after")
    def reject_explicit_null_for_non_nullable_fields(self) -> CreateHostRequest:
        non_nullable_optional = {
            "path",
            "sni",
            "host",
            "fingerprint",
            "tags",
            "pinned_peer_cert_sha256",
            "verify_peer_cert_by_name",
            "nodes",
            "exclude_from_subscription_types",
            "mapper",
            "internal_squads",
        }
        for field in non_nullable_optional & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class UpdateHostRequest(_HostRequest):
    """Exact target ``UpdateHostBodyDto`` fields except path-owned UUID."""

    inbound: HostInboundRequest | None = None
    remark: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = None
    port: int | None = Field(default=None, ge=-(2**53 - 1), le=2**53 - 1)
    path: list[str] | None = None
    sni: list[str] | None = None
    host: list[str] | None = None
    alpn: HostAlpn | None = None
    fingerprint: list[str] | None = None
    is_disabled: bool | None = Field(default=None, alias="isDisabled")
    security_layer: HostSecurityLayer | None = Field(default=None, alias="securityLayer")
    xhttp_extra_params: Any | None = Field(default=None, alias="xhttpExtraParams")
    mux_params: Any | None = Field(default=None, alias="muxParams")
    sockopt_params: Any | None = Field(default=None, alias="sockoptParams")
    final_mask: Any | None = Field(default=None, alias="finalMask")
    server_description: str | None = Field(default=None, alias="serverDescription", max_length=30)
    tags: list[HostTag] | None = Field(default=None, max_length=10)
    is_hidden: bool | None = Field(default=None, alias="isHidden")
    override_sni_from_address: bool | None = Field(default=None, alias="overrideSniFromAddress")
    keep_sni_blank: bool | None = Field(default=None, alias="keepSniBlank")
    vless_route_id: int | None = Field(default=None, alias="vlessRouteId", ge=0, le=65535)
    pinned_peer_cert_sha256: list[str] | None = Field(default=None, alias="pinnedPeerCertSha256")
    verify_peer_cert_by_name: list[str] | None = Field(default=None, alias="verifyPeerCertByName")
    shuffle_host: bool | None = Field(default=None, alias="shuffleHost")
    mihomo_x25519: bool | None = Field(default=None, alias="mihomoX25519")
    mihomo_ip_version: HostMihomoIpVersion | None = Field(default=None, alias="mihomoIpVersion")
    nodes: list[UUID] | None = None
    xray_json_template_uuid: UUID | None = Field(default=None, alias="xrayJsonTemplateUuid")
    exclude_from_subscription_types: list[SubscriptionTemplateType] | None = Field(
        default=None,
        alias="excludeFromSubscriptionTypes",
    )
    mapper: RemnawaveHostMapper | None = None
    internal_squads: HostInternalSquadsRequest | None = Field(default=None, alias="internalSquads")

    @model_validator(mode="after")
    def reject_explicit_null_for_non_nullable_fields(self) -> UpdateHostRequest:
        nullable = {
            "alpn",
            "xhttp_extra_params",
            "mux_params",
            "sockopt_params",
            "final_mask",
            "server_description",
            "vless_route_id",
            "mihomo_ip_version",
            "xray_json_template_uuid",
        }
        for field in self.model_fields_set - nullable:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class HostResponse(RemnawaveHostV34Response):
    """CyberVPN response mirrors the unwrapped target host DTO."""


class ServerStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    online: int
    offline: int
    warning: int
    maintenance: int
    total: int
