"""Typed Remnawave 3.4.3 host and subscription-template contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

HostAlpn = Literal["h3", "h2", "http/1.1", "h2,http/1.1", "h3,h2,http/1.1", "h3,h2"]
HostSecurityLayer = Literal["DEFAULT", "TLS", "NONE"]
HostMihomoIpVersion = Literal["dual", "ipv4", "ipv6", "ipv4-prefer", "ipv6-prefer"]
SubscriptionTemplateType = Literal["XRAY_JSON", "XRAY_BASE64", "MIHOMO", "STASH", "CLASH", "SINGBOX"]


class _RemnawaveResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_alias=True,
        validate_by_name=True,
        extra="ignore",
    )


class RemnawaveHostMapperCopy(_RemnawaveResponse):
    op: Literal["copy"]
    from_path: str = Field(alias="from", min_length=1, max_length=512)
    to: str = Field(min_length=1, max_length=512)


class RemnawaveHostMapperSet(_RemnawaveResponse):
    op: Literal["set"]
    value: Any
    to: str = Field(min_length=1, max_length=512)

    @field_validator("value")
    @classmethod
    def reject_null_value(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("mapper set value cannot be null")
        return value


class RemnawaveHostMapperUnset(_RemnawaveResponse):
    op: Literal["unset"]
    to: str = Field(min_length=1, max_length=512)


RemnawaveHostMapperOperation = Annotated[
    RemnawaveHostMapperCopy | RemnawaveHostMapperSet | RemnawaveHostMapperUnset,
    Field(discriminator="op"),
]


class RemnawaveHostMapper(_RemnawaveResponse):
    xray_json: list[RemnawaveHostMapperOperation] = Field(default_factory=list, alias="xrayJson")
    mihomo: list[RemnawaveHostMapperOperation] = Field(default_factory=list)
    base64_operations: list[RemnawaveHostMapperOperation] = Field(default_factory=list, alias="base64")
    singbox: list[RemnawaveHostMapperOperation] = Field(default_factory=list)


class RemnawaveHostInboundResponse(_RemnawaveResponse):
    config_profile_uuid: UUID | None = Field(alias="configProfileUuid")
    config_profile_inbound_uuid: UUID | None = Field(alias="configProfileInboundUuid")


class RemnawaveHostInternalSquadsResponse(_RemnawaveResponse):
    mode: Literal["EXCLUDE", "ALLOW_ONLY"]
    squads: list[UUID]


class RemnawaveHostV34Response(_RemnawaveResponse):
    """Unwrapped ``HostResponseDto.response`` from Remnawave 3.4.3."""

    uuid: UUID
    view_position: int = Field(alias="viewPosition", ge=-(2**53 - 1), le=2**53 - 1)
    remark: str
    address: str
    port: int = Field(ge=-(2**53 - 1), le=2**53 - 1)
    path: str | None
    sni: str | None
    host: str | None
    alpn: HostAlpn | None
    fingerprint: str | None
    is_disabled: bool = Field(alias="isDisabled")
    security_layer: HostSecurityLayer = Field(default="DEFAULT", alias="securityLayer")
    xhttp_extra_params: Any = Field(alias="xhttpExtraParams")
    mux_params: Any = Field(alias="muxParams")
    sockopt_params: Any = Field(alias="sockoptParams")
    final_mask: Any = Field(alias="finalMask")
    inbound: RemnawaveHostInboundResponse
    server_description: str | None = Field(alias="serverDescription")
    tags: list[str] = Field(default_factory=list)
    is_hidden: bool = Field(default=False, alias="isHidden")
    override_sni_from_address: bool = Field(default=False, alias="overrideSniFromAddress")
    keep_sni_blank: bool = Field(default=False, alias="keepSniBlank")
    vless_route_id: int | None = Field(alias="vlessRouteId")
    pinned_peer_cert_sha256: str | None = Field(alias="pinnedPeerCertSha256")
    verify_peer_cert_by_name: str | None = Field(alias="verifyPeerCertByName")
    shuffle_host: bool = Field(alias="shuffleHost")
    mihomo_x25519: bool = Field(alias="mihomoX25519")
    mihomo_ip_version: HostMihomoIpVersion | None = Field(alias="mihomoIpVersion")
    nodes: list[UUID]
    xray_json_template_uuid: UUID | None = Field(alias="xrayJsonTemplateUuid")
    exclude_from_subscription_types: list[SubscriptionTemplateType] = Field(alias="excludeFromSubscriptionTypes")
    mapper: RemnawaveHostMapper
    internal_squads: RemnawaveHostInternalSquadsResponse = Field(alias="internalSquads")


class RemnawaveSubscriptionTemplateV34Response(_RemnawaveResponse):
    """Unwrapped template response shared by target create/update/get DTOs."""

    uuid: UUID
    view_position: int = Field(alias="viewPosition", ge=-(2**53 - 1), le=2**53 - 1)
    name: str
    tags: list[str]
    template_type: SubscriptionTemplateType = Field(alias="templateType")
    template_json: dict[str, Any] | None = Field(alias="templateJson")
    encoded_template_yaml: str | None = Field(alias="encodedTemplateYaml")
