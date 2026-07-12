from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RouteTarget = Literal["direct", "block", "eu", "ru"]
SourceKind = Literal["builtin", "http", "inline", "process"]
SourceBehavior = Literal["classical", "domain", "ipcidr", "protocol"]
SourceFormat = Literal["mrs", "text", "yaml"]

RULE_STAGES = (
    "private_networks",
    "direct_processes",
    "bittorrent_protocol",
    "torrent_processes",
    "torrent_sources",
    "ads_trackers",
    "tor",
    "quic_doq",
    "smtp_abuse",
    "eu_exceptions",
    "ru_services",
    "broad_ru",
    "final",
)

RULE_ACTIONS: dict[str, RouteTarget] = {
    "private_networks": "direct",
    "direct_processes": "direct",
    "bittorrent_protocol": "block",
    "torrent_processes": "block",
    "torrent_sources": "block",
    "ads_trackers": "block",
    "tor": "block",
    "quic_doq": "block",
    "smtp_abuse": "block",
    "eu_exceptions": "eu",
    "ru_services": "ru",
    "broad_ru": "ru",
    "final": "eu",
}


def _critical_entry_identity(entry: str) -> str:
    normalized = entry.strip().casefold()
    for prefix in ("domain-suffix,", "domain,"):
        if normalized.startswith(prefix):
            return "domain:" + normalized.removeprefix(prefix).removeprefix(
                "+."
            ).removeprefix(".")
    if "," not in normalized and "." in normalized:
        return "domain:" + normalized.removeprefix("+.").removeprefix(".")
    return normalized


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Routes(StrictModel):
    private: Literal["direct"]
    default: Literal["eu"]
    ru_services: Literal["ru"]
    eu_exceptions: Literal["eu"]


class Blocks(StrictModel):
    ads: Literal[True]
    trackers: Literal[True]
    torrent: Literal[True]
    tor: Literal["best_effort"]
    quic_doq: Literal["block"]
    smtp_abuse_ports: tuple[int, ...]

    @model_validator(mode="after")
    def validate_smtp_ports(self) -> Blocks:
        if self.smtp_abuse_ports != (25, 465, 587):
            raise ValueError(
                "smtp_abuse_ports must preserve ports 25, 465, and 587 in order"
            )
        return self


class SourceIntegrity(StrictModel):
    revision: str = Field(min_length=1)
    pinned: bool
    sha256: str | None = None

    @model_validator(mode="after")
    def validate_pin(self) -> SourceIntegrity:
        if self.pinned:
            if (
                self.sha256 is None
                or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None
            ):
                raise ValueError("pinned source integrity requires a lowercase SHA-256")
        elif self.sha256 is not None:
            raise ValueError("mutable source integrity cannot claim a content SHA-256")
        return self


class PolicySource(StrictModel):
    kind: SourceKind
    behavior: SourceBehavior
    format: SourceFormat | None = None
    url: str | None = None
    interval_seconds: int | None = Field(default=None, ge=300, le=604800)
    entries: tuple[str, ...] = ()
    integrity: SourceIntegrity | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> PolicySource:
        if self.kind == "http":
            if self.url is None or not self.url.startswith("https://"):
                raise ValueError("http source requires an HTTPS url")
            if (
                self.format is None
                or self.interval_seconds is None
                or self.integrity is None
            ):
                raise ValueError(
                    "http source requires format, interval_seconds, and integrity"
                )
            if self.entries:
                raise ValueError("http source cannot also define inline entries")
        else:
            if (
                self.url is not None
                or self.format is not None
                or self.interval_seconds is not None
            ):
                raise ValueError(
                    f"{self.kind} source cannot define remote-source fields"
                )
            if self.integrity is not None:
                raise ValueError(f"{self.kind} source cannot define remote integrity")
            if not self.entries:
                raise ValueError(f"{self.kind} source must define at least one entry")

        normalized = [entry.strip().casefold() for entry in self.entries]
        duplicates = sorted(
            {entry for entry in normalized if normalized.count(entry) > 1}
        )
        if duplicates:
            raise ValueError(
                f"source contains duplicate entries: {', '.join(duplicates)}"
            )
        return self


class SourceGroups(StrictModel):
    private_networks: tuple[str, ...]
    direct_processes: tuple[str, ...]
    bittorrent_protocol: tuple[str, ...]
    torrent_processes: tuple[str, ...]
    torrent_sources: tuple[str, ...]
    ads_trackers: tuple[str, ...]
    tor: tuple[str, ...]
    quic_doq: tuple[str, ...]
    smtp_abuse: tuple[str, ...]
    eu_exceptions: tuple[str, ...]
    ru_services: tuple[str, ...]
    broad_ru: tuple[str, ...]


class Region(StrictModel):
    primary: Literal["de", "nl", "moscow", "spb"]
    fallback: Literal["de", "nl", "moscow", "spb"]

    @model_validator(mode="after")
    def validate_distinct_members(self) -> Region:
        if self.primary == self.fallback:
            raise ValueError("regional primary and fallback must be different")
        return self


class Regions(StrictModel):
    eu: Region
    ru: Region

    @model_validator(mode="after")
    def validate_region_membership(self) -> Regions:
        if (self.eu.primary, self.eu.fallback) != ("de", "nl"):
            raise ValueError("EU order must be DE primary then NL fallback")
        if (self.ru.primary, self.ru.fallback) not in {
            ("moscow", "spb"),
            ("spb", "moscow"),
        }:
            raise ValueError("RU order must contain distinct Moscow and SPB roles")
        return self


class Health(StrictModel):
    probe_url: str
    expected_status: int = Field(ge=100, le=599)
    interval_seconds: int = Field(ge=30, le=3600)
    lazy: bool
    transport_checks: Literal["independent"]
    constrain_probe_to_region: Literal[True]

    @model_validator(mode="after")
    def validate_probe_url(self) -> Health:
        if not self.probe_url.startswith("https://"):
            raise ValueError("health probe URL must use HTTPS")
        return self


class DegradedSemantics(StrictModel):
    on_primary_unavailable: Literal["use_fallback"]
    on_fallback_unavailable: Literal["use_primary_if_healthy"]
    on_all_unavailable: Literal["explicit_degraded"]
    cross_region_fallback: Literal[False]
    event: str = Field(pattern=r"^[a-z][a-z0-9_.]+$")
    metric: str = Field(pattern=r"^[a-z][a-z0-9_]+$")


class TransportGroup(StrictModel):
    primary: Literal["de", "nl", "moscow", "spb"]
    fallback: Literal["de", "nl", "moscow", "spb"]
    primary_transport: Literal["raw", "xhttp"]
    fallback_transport: Literal["raw", "xhttp"]
    members: dict[str, tuple[Literal["raw", "xhttp"], ...]]
    health: Health
    degraded: DegradedSemantics

    @model_validator(mode="after")
    def validate_transport_members(self) -> TransportGroup:
        if set(self.members) != {self.primary, self.fallback}:
            raise ValueError(
                "transport group members must exactly match primary and fallback"
            )
        for location, transports in self.members.items():
            if transports != ("raw", "xhttp"):
                raise ValueError(
                    f"{location} must expose RAW and XHTTP in deterministic order"
                )
        if self.primary_transport not in self.members[self.primary]:
            raise ValueError("primary automatic transport must be a declared member")
        if self.fallback_transport not in self.members[self.fallback]:
            raise ValueError("fallback automatic transport must be a declared member")
        return self


class TransportGroups(StrictModel):
    eu: TransportGroup
    ru: TransportGroup

    @model_validator(mode="after")
    def validate_region_alignment(self) -> TransportGroups:
        if (self.eu.primary, self.eu.fallback) != ("de", "nl"):
            raise ValueError("EU transport group must be DE then NL")
        if (self.ru.primary, self.ru.fallback) not in {
            ("moscow", "spb"),
            ("spb", "moscow"),
        }:
            raise ValueError("RU transport group must contain Moscow and SPB")
        return self


class PolicyRule(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    stage: Literal[
        "private_networks",
        "direct_processes",
        "bittorrent_protocol",
        "torrent_processes",
        "torrent_sources",
        "ads_trackers",
        "tor",
        "quic_doq",
        "smtp_abuse",
        "eu_exceptions",
        "ru_services",
        "broad_ru",
        "final",
    ]
    action: RouteTarget
    source_group: str | None = None
    network: Literal["tcp,udp"] | None = None
    assurance: Literal["enforced", "best_effort"] = "enforced"


class PremiumSmartRuPolicy(StrictModel):
    version: Literal[1]
    product: Literal["premium_smart_ru"]
    routes: Routes
    blocks: Blocks
    regions: Regions
    transport_groups: TransportGroups
    sources: dict[str, PolicySource]
    source_groups: SourceGroups
    rules: tuple[PolicyRule, ...]

    @model_validator(mode="after")
    def validate_semantics(self) -> PremiumSmartRuPolicy:
        invalid_source_ids = sorted(
            source_id
            for source_id in self.sources
            if re.fullmatch(r"[a-z][a-z0-9-]+", source_id) is None
        )
        if invalid_source_ids:
            raise ValueError(
                f"source ids must use lowercase kebab-case: {', '.join(invalid_source_ids)}"
            )

        source_urls: dict[str, str] = {}
        for source_id, source in self.sources.items():
            if source.url is None:
                continue
            previous = source_urls.setdefault(source.url, source_id)
            if previous != source_id:
                raise ValueError(
                    f"remote source URL is duplicated by {previous} and {source_id}: {source.url}"
                )

        expected_stages = RULE_STAGES
        actual_stages = tuple(rule.stage for rule in self.rules)
        if actual_stages != expected_stages:
            raise ValueError(
                "rule stages must preserve canonical first-match order: "
                + " -> ".join(expected_stages)
            )

        rule_ids = [rule.id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("rule ids must be unique")

        groups = self.source_groups.model_dump(mode="python")
        unknown = sorted(
            {source_id for ids in groups.values() for source_id in ids}
            - self.sources.keys()
        )
        if unknown:
            raise ValueError(
                f"source groups reference unknown sources: {', '.join(unknown)}"
            )

        memberships: dict[str, list[str]] = {}
        for group_name, source_ids in groups.items():
            if not source_ids:
                raise ValueError(f"critical source group {group_name} cannot be empty")
            for source_id in source_ids:
                memberships.setdefault(source_id, []).append(group_name)
        duplicate_lists = {
            key: value for key, value in memberships.items() if len(value) > 1
        }
        if duplicate_lists:
            details = ", ".join(
                f"{key} ({'/'.join(value)})" for key, value in duplicate_lists.items()
            )
            raise ValueError(
                f"critical source lists cannot be duplicated across groups: {details}"
            )

        inline_entries: dict[str, str] = {}
        for source_id in memberships:
            for entry in self.sources[source_id].entries:
                normalized = _critical_entry_identity(entry)
                previous = inline_entries.setdefault(normalized, source_id)
                if previous != source_id:
                    raise ValueError(
                        f"critical entry {entry!r} is duplicated across sources {previous} and {source_id}"
                    )

        for rule in self.rules:
            if rule.action != RULE_ACTIONS[rule.stage]:
                raise ValueError(
                    f"rule {rule.id} has action {rule.action}; expected {RULE_ACTIONS[rule.stage]}"
                )
            if rule.stage == "final":
                if rule.source_group is not None or rule.network != "tcp,udp":
                    raise ValueError(
                        "final rule must be an effective tcp,udp matcher without a source group"
                    )
            elif rule.source_group != rule.stage or rule.network is not None:
                raise ValueError(
                    f"rule {rule.id} must reference source group {rule.stage}"
                )

        tor_rule = next(rule for rule in self.rules if rule.stage == "tor")
        if tor_rule.assurance != "best_effort":
            raise ValueError("TOR blocking must be represented as best_effort")
        if any(
            rule.assurance != "enforced" for rule in self.rules if rule.stage != "tor"
        ):
            raise ValueError("only TOR may use best_effort assurance in version 1")

        if (
            self.transport_groups.eu.health.probe_url
            == self.transport_groups.ru.health.probe_url
        ):
            raise ValueError("EU and RU health probes must be region-specific")
        return self
