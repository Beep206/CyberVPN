from __future__ import annotations

import base64
import copy
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from .models import PolicyRule, PolicySource, PremiumSmartRuPolicy

MIHOMO_NAME = "mihomo.yaml"
XRAY_CLIENT_NAME = "xray-client.json"
XRAY_SERVER_NAME = "xray-server.json"
LEGACY_HEADER_NAME = "legacy-routing-header.json"
MIHOMO_BASE_TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "cybervpn-premium-smart-ru.yaml"
)

_XRAY_SOURCE_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "geosite-private": {"domain": ("geosite:private",)},
    "remote-control": {"domain": ("geosite:category-remote-control",)},
    "ads-all": {"domain": ("geosite:category-ads-all",)},
    "youtube": {"domain": ("geosite:youtube",)},
    "discord-domains": {"domain": ("geosite:discord",)},
    "telegram-domains": {"domain": ("geosite:telegram",)},
    "telegram-ips": {"ip": ("geoip:telegram",)},
    "additional-telegram-domains": {"domain": ("geosite:telegram",)},
    "additional-telegram-ips": {"ip": ("geoip:telegram",)},
    "whatsapp": {"domain": ("geosite:whatsapp",)},
    "meta-ips": {"ip": ("geoip:facebook",)},
    "ai": {"domain": ("geosite:category-ai-!cn",)},
    "google-deepmind": {"domain": ("geosite:google-deepmind",)},
    "github": {"domain": ("geosite:github",)},
    "geosite-ru": {"domain": ("geosite:category-ru",)},
    "geoip-for-ru": {"ip": ("geoip:ru",)},
}

_NETWORK_PORT_RULE = re.compile(
    r"AND,\(\(NETWORK,(?P<network>TCP|UDP)\),\(DST-PORT,(?P<port>[0-9,-]+)\)\)",
    re.IGNORECASE,
)
_MIHOMO_EU_SOURCE_TARGETS = {
    "youtube": "📺 YouTube",
    "discord-domains": "💬 Discord",
    "discord-voice": "💬 Discord",
    "telegram-domains": "➤ Telegram",
    "telegram-ips": "➤ Telegram",
    "additional-telegram-domains": "➤ Telegram",
    "additional-telegram-ips": "➤ Telegram",
    "whatsapp": "💬 Messengers",
    "meta-ips": "💬 Messengers",
    "ai": "🤖 AI",
    "google-deepmind": "🤖 AI",
    "github": "👨‍💻 Dev Services",
}


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode()


def _source_descriptor(source_id: str, source: PolicySource) -> dict[str, object]:
    descriptor: dict[str, object] = {
        "id": source_id,
        "kind": source.kind,
        "behavior": source.behavior,
        "entries": list(source.entries),
    }
    if source.url is not None:
        assert source.integrity is not None
        descriptor.update(
            {
                "format": source.format,
                "url": source.url,
                "intervalSeconds": source.interval_seconds,
                "revision": source.integrity.revision,
                "sha256": source.integrity.sha256,
            }
        )
    return descriptor


def _source_ids(policy: PremiumSmartRuPolicy, rule: PolicyRule) -> tuple[str, ...]:
    if rule.source_group is None:
        return ()
    groups = policy.source_groups.model_dump(mode="python")
    return tuple(groups[rule.source_group])


def _append_unique(target: list[str], values: Iterable[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def _xray_domain(entry: str) -> str | None:
    if "," not in entry:
        return f"domain:{entry.casefold()}" if "." in entry else None
    kind, value = entry.split(",", 1)
    normalized_kind = kind.strip().upper()
    normalized_value = value.strip().casefold().removeprefix("+.").removeprefix(".")
    if normalized_kind == "DOMAIN-SUFFIX":
        if normalized_value in {"onion", "\u0440\u0444"}:
            return rf"regexp:\.{normalized_value}$"
        return f"domain:{normalized_value}"
    if normalized_kind == "DOMAIN":
        return f"full:{normalized_value}"
    if normalized_kind == "DOMAIN-KEYWORD":
        return f"keyword:{normalized_value}"
    return None


def _xray_matches(
    policy: PremiumSmartRuPolicy, source_ids: tuple[str, ...]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    domains: list[str] = []
    ips: list[str] = []
    protocols: list[str] = []
    processes: list[str] = []
    network_ports: dict[str, list[str]] = {}
    providers: list[dict[str, object]] = []

    for source_id in source_ids:
        source = policy.sources[source_id]
        alias = _XRAY_SOURCE_ALIASES.get(source_id, {})
        _append_unique(domains, alias.get("domain", ()))
        _append_unique(ips, alias.get("ip", ()))
        if source.kind == "http":
            providers.append(_source_descriptor(source_id, source))
        for entry in source.entries:
            if source.kind == "process":
                _append_unique(processes, (f"regexp:{entry}",))
                continue
            if source.kind == "builtin" and source.behavior == "protocol":
                _append_unique(protocols, (entry,))
                continue
            domain = _xray_domain(entry)
            if domain is not None:
                _append_unique(domains, (domain,))
                continue
            if entry.upper().startswith("IP-CIDR,"):
                _append_unique(ips, (entry.split(",", 1)[1].strip(),))
                continue
            network_port = _NETWORK_PORT_RULE.fullmatch(entry.strip())
            if network_port is not None:
                network = network_port.group("network").casefold()
                _append_unique(
                    network_ports.setdefault(network, []),
                    (network_port.group("port"),),
                )

    matches: list[dict[str, object]] = []
    for key, values in (
        ("domain", domains),
        ("ip", ips),
        ("protocol", protocols),
        ("process", processes),
    ):
        if values:
            matches.append({key: values})
    matches.extend(
        {"network": network, "port": ",".join(ports)}
        for network, ports in network_ports.items()
    )
    return matches, providers


def _typed_rules(policy: PremiumSmartRuPolicy) -> list[dict[str, object]]:
    rendered: list[dict[str, object]] = []
    for rule in policy.rules:
        source_ids = _source_ids(policy, rule)
        matches, providers = _xray_matches(policy, source_ids)
        if rule.network is not None:
            matches = [{"network": rule.network}]
        rendered.append(
            {
                "id": rule.id,
                "stage": rule.stage,
                "action": rule.action,
                "assurance": rule.assurance,
                "sourceGroup": rule.source_group,
                "sourceIds": list(source_ids),
                "matches": matches,
                "providers": providers,
            }
        )
    return rendered


def _health(policy: PremiumSmartRuPolicy) -> dict[str, object]:
    result: dict[str, object] = {}
    for region_name in ("eu", "ru"):
        group = getattr(policy.transport_groups, region_name)
        result[region_name] = {
            "primary": group.primary,
            "fallback": group.fallback,
            "primaryTransport": group.primary_transport,
            "fallbackTransport": group.fallback_transport,
            "members": {
                name: list(transports) for name, transports in group.members.items()
            },
            "probe": {
                "url": group.health.probe_url,
                "expectedStatus": group.health.expected_status,
                "intervalSeconds": group.health.interval_seconds,
                "lazy": group.health.lazy,
                "transportChecks": group.health.transport_checks,
                "constrainToRegion": group.health.constrain_probe_to_region,
            },
            "degraded": {
                "onPrimaryUnavailable": group.degraded.on_primary_unavailable,
                "onFallbackUnavailable": group.degraded.on_fallback_unavailable,
                "onAllUnavailable": group.degraded.on_all_unavailable,
                "crossRegionFallback": group.degraded.cross_region_fallback,
                "event": group.degraded.event,
                "metric": group.degraded.metric,
            },
        }
    return result


def render_xray_client(policy: PremiumSmartRuPolicy) -> dict[str, object]:
    return {
        "schemaVersion": policy.version,
        "product": policy.product,
        "consumer": "incy-happ-xray",
        "ruleOrder": [rule.stage for rule in policy.rules],
        "rules": _typed_rules(policy),
        "transportPolicy": _health(policy),
    }


def render_xray_server(policy: PremiumSmartRuPolicy) -> dict[str, object]:
    rules = _typed_rules(policy)
    return {
        "schemaVersion": policy.version,
        "product": policy.product,
        "consumer": "remnawave-xray-server",
        "ruleOrder": [rule["stage"] for rule in rules],
        "nodePluginPolicy": {
            "torrentBlocker": {
                "required": True,
                "protocol": "bittorrent",
                "injectedRulePosition": "first",
            }
        },
        "rules": rules,
    }


def _mihomo_provider(source_id: str, source: PolicySource) -> dict[str, object] | None:
    if source.kind in {"builtin", "process"}:
        return None
    if source.kind == "inline":
        return {
            "type": "inline",
            "behavior": source.behavior,
            "payload": list(source.entries),
        }
    assert source.url is not None
    assert source.format is not None
    assert source.interval_seconds is not None
    assert source.integrity is not None
    suffix = {"mrs": "mrs", "yaml": "yaml", "text": "txt"}[source.format]
    return {
        "type": "http",
        "behavior": source.behavior,
        "format": source.format,
        "proxy": "🌍 World / EU",
        "interval": source.interval_seconds,
        "url": source.url,
        "path": f"./rule-sets/{source_id}.{suffix}",
    }


def _base_group(groups: list[object], name: str) -> dict[str, object]:
    for item in groups:
        if isinstance(item, dict) and item.get("name") == name:
            return copy.deepcopy(item)
    raise RuntimeError(f"Mihomo base template is missing proxy group {name}")


def _regional_mihomo_groups(
    base_groups: list[object], policy: PremiumSmartRuPolicy
) -> list[dict[str, object]]:
    eu = policy.transport_groups.eu
    ru = policy.transport_groups.ru
    de = _base_group(base_groups, "🇩🇪 DE Auto")
    nl = _base_group(base_groups, "🇳🇱 NL Auto")
    moscow = _base_group(base_groups, "🇷🇺 Moscow Auto")
    spb = _base_group(base_groups, "🇷🇺 SPB Auto")
    for group in (de, nl):
        group["url"] = eu.health.probe_url
        group["expected-status"] = eu.health.expected_status
        group["interval"] = eu.health.interval_seconds
        group["lazy"] = eu.health.lazy
    for group in (moscow, spb):
        group["url"] = ru.health.probe_url
        group["expected-status"] = ru.health.expected_status
        group["interval"] = ru.health.interval_seconds
        group["lazy"] = ru.health.lazy

    eu_auto: dict[str, object] = {
        "name": "⚡ EU Auto",
        "type": "fallback",
        "remnawave": {"include-proxies": False},
        "proxies": ["🇩🇪 DE Auto", "🇳🇱 NL Auto"],
        "url": eu.health.probe_url,
        "expected-status": eu.health.expected_status,
        "interval": eu.health.interval_seconds,
        "lazy": eu.health.lazy,
        "hidden": True,
    }
    world: dict[str, object] = {
        "name": "🌍 World / EU",
        "type": "select",
        "remnawave": {"include-proxies": False},
        "proxies": ["⚡ EU Auto", "🇩🇪 DE Auto", "🇳🇱 NL Auto", "DIRECT"],
    }
    ru_auto: dict[str, object] = {
        "name": "⚡ RU Auto",
        "type": "fallback",
        "remnawave": {"include-proxies": False},
        "proxies": [
            {"moscow": "🇷🇺 Moscow Auto", "spb": "🇷🇺 SPB Auto"}[ru.primary],
            {"moscow": "🇷🇺 Moscow Auto", "spb": "🇷🇺 SPB Auto"}[ru.fallback],
        ],
        "url": ru.health.probe_url,
        "expected-status": ru.health.expected_status,
        "interval": ru.health.interval_seconds,
        "lazy": ru.health.lazy,
        "hidden": True,
    }
    ru_sites: dict[str, object] = {
        "name": "🇷🇺 RU Sites",
        "type": "select",
        "remnawave": {"include-proxies": False},
        "proxies": [
            "⚡ RU Auto",
            {"moscow": "🇷🇺 Moscow Auto", "spb": "🇷🇺 SPB Auto"}[ru.primary],
            {"moscow": "🇷🇺 Moscow Auto", "spb": "🇷🇺 SPB Auto"}[ru.fallback],
            "🌍 World / EU",
            "DIRECT",
        ],
    }
    category_groups = [
        {
            "name": name,
            "type": "select",
            "remnawave": {"include-proxies": False},
            "proxies": proxies,
        }
        for name, proxies in (
            ("📺 YouTube", ["🌍 World / EU", "🇩🇪 DE Auto", "🇳🇱 NL Auto"]),
            ("💬 Discord", ["🌍 World / EU", "🇩🇪 DE Auto", "🇳🇱 NL Auto", "DIRECT"]),
            ("➤ Telegram", ["🌍 World / EU", "🇷🇺 RU Sites", "DIRECT"]),
            ("💬 Messengers", ["🌍 World / EU", "🇷🇺 RU Sites", "DIRECT"]),
            ("🤖 AI", ["🌍 World / EU", "🇩🇪 DE Auto", "🇳🇱 NL Auto"]),
            (
                "👨‍💻 Dev Services",
                ["🌍 World / EU", "🇩🇪 DE Auto", "🇳🇱 NL Auto", "DIRECT"],
            ),
            ("🎮 Games", ["DIRECT", "🌍 World / EU", "🇷🇺 RU Sites"]),
            ("🧪 Speedtest", ["🌍 World / EU", "🇷🇺 RU Sites", "DIRECT"]),
        )
    ]
    direct: dict[str, object] = {
        "name": "♻️ DIRECT",
        "type": "select",
        "remnawave": {"include-proxies": False},
        "hidden": True,
        "proxies": ["DIRECT"],
    }
    block: dict[str, object] = {
        "name": "⛔ BLOCK",
        "type": "select",
        "remnawave": {"include-proxies": False},
        "hidden": True,
        "proxies": ["REJECT", "REJECT-DROP"],
    }
    proxy: dict[str, object] = {
        "name": "PROXY",
        "type": "select",
        "remnawave": {"include-proxies": False},
        "hidden": True,
        "proxies": ["🌍 World / EU"],
    }
    return [
        world,
        ru_sites,
        *category_groups,
        eu_auto,
        nl,
        de,
        ru_auto,
        moscow,
        spb,
        direct,
        block,
        proxy,
    ]


def _mihomo_target(action: str) -> str:
    if action == "direct":
        return "♻️ DIRECT"
    if action == "eu":
        return "🌍 World / EU"
    if action == "ru":
        return "🇷🇺 RU Sites"
    if action == "block":
        return "⛔ BLOCK"
    raise RuntimeError(f"Unsupported Mihomo policy action {action}")


def _mihomo_rules(policy: PremiumSmartRuPolicy) -> list[str]:
    rendered: list[str] = []
    for rule in policy.rules:
        target = _mihomo_target(rule.action)
        if rule.stage == "final":
            rendered.append(f"MATCH,{target}")
            continue
        source_ids = _source_ids(policy, rule)
        for source_id in source_ids:
            source = policy.sources[source_id]
            source_target = _MIHOMO_EU_SOURCE_TARGETS.get(source_id, target)
            if source.kind == "process":
                rendered.extend(
                    f"PROCESS-NAME-REGEX,{entry},{source_target}"
                    for entry in source.entries
                )
            elif source.kind == "builtin":
                continue
            else:
                suffix = ",no-resolve" if source.behavior == "ipcidr" else ""
                rendered.append(f"RULE-SET,{source_id},{source_target}{suffix}")
    return rendered


def _supports_mihomo_dns_policy(source: PolicySource) -> bool:
    return source.kind not in {"builtin", "process"} and source.behavior != "ipcidr"


def render_mihomo(policy: PremiumSmartRuPolicy) -> dict[str, object]:
    try:
        loaded = yaml.safe_load(MIHOMO_BASE_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"Cannot load Mihomo base template: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeError("Mihomo base template must contain a YAML mapping")
    base_groups = loaded.get("proxy-groups")
    if not isinstance(base_groups, list):
        raise RuntimeError("Mihomo base template contains no proxy groups")

    config = copy.deepcopy(loaded)
    config["proxy-groups"] = _regional_mihomo_groups(base_groups, policy)
    config["rule-providers"] = {
        source_id: provider
        for source_id, source in policy.sources.items()
        if (provider := _mihomo_provider(source_id, source)) is not None
    }
    config["rules"] = _mihomo_rules(policy)

    dns = config.get("dns")
    if not isinstance(dns, dict):
        raise RuntimeError("Mihomo base template contains no DNS config")
    dns["proxy-server-nameserver"] = [
        "system",
        "https://8.8.8.8/dns-query",
        "https://1.1.1.1/dns-query",
        "https://77.88.8.8/dns-query",
    ]
    dns["nameserver"] = [
        "https://8.8.8.8/dns-query#🌍 World / EU",
        "https://1.1.1.1/dns-query#🌍 World / EU",
    ]
    nameserver_policy: dict[str, list[str]] = {"rule-set:geosite-private": ["system"]}
    for source_id in policy.source_groups.catalog_exceptions:
        if _supports_mihomo_dns_policy(policy.sources[source_id]):
            nameserver_policy[f"rule-set:{source_id}"] = [
                str(item) for item in dns["nameserver"]
            ]
    for source_id in policy.source_groups.ads_trackers + policy.source_groups.tor:
        if _supports_mihomo_dns_policy(policy.sources[source_id]):
            nameserver_policy[f"rule-set:{source_id}"] = ["rcode://name_error"]
    for source_id in policy.source_groups.eu_exceptions:
        if _supports_mihomo_dns_policy(policy.sources[source_id]):
            nameserver_policy[f"rule-set:{source_id}"] = [
                "https://8.8.8.8/dns-query#🌍 World / EU",
                "https://1.1.1.1/dns-query#🌍 World / EU",
            ]
    for source_id in policy.source_groups.ru_services + policy.source_groups.broad_ru:
        if _supports_mihomo_dns_policy(policy.sources[source_id]):
            nameserver_policy[f"rule-set:{source_id}"] = [
                "https://77.88.8.8/dns-query#🇷🇺 RU Sites",
                "https://8.8.8.8/dns-query#🇷🇺 RU Sites",
            ]
    dns["nameserver-policy"] = nameserver_policy
    return config


def _yaml_bytes(value: object) -> bytes:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    ).encode("utf-8")


def _legacy_sites(policy: PremiumSmartRuPolicy, stages: tuple[str, ...]) -> list[str]:
    sites: list[str] = []
    rules_by_stage: dict[str, PolicyRule] = {rule.stage: rule for rule in policy.rules}
    for stage in stages:
        for source_id in _source_ids(policy, rules_by_stage[stage]):
            source = policy.sources[source_id]
            if source.kind == "process":
                continue
            alias = _XRAY_SOURCE_ALIASES.get(source_id, {})
            _append_unique(sites, alias.get("domain", ()))
            for entry in source.entries:
                domain = _xray_domain(entry)
                if domain is not None:
                    _append_unique(sites, (domain,))
    return sites


def render_legacy_header(policy: PremiumSmartRuPolicy) -> dict[str, object]:
    private_rule = next(
        rule for rule in policy.rules if rule.stage == "private_networks"
    )
    private_matches, _providers = _xray_matches(
        policy, _source_ids(policy, private_rule)
    )
    private_domains: list[str] = []
    private_ips: list[str] = []
    for match in private_matches:
        domain_values = match.get("domain")
        if isinstance(domain_values, list):
            private_domains.extend(str(item) for item in domain_values)
        ip_values = match.get("ip")
        if isinstance(ip_values, list):
            private_ips.extend(str(item) for item in ip_values)
    block_stages = ("ads_trackers", "tor")
    decoded: dict[str, Any] = {
        "Name": "CyberVPN Premium Smart RU",
        "GlobalProxy": "true",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
        "BlockSites": _legacy_sites(policy, block_stages),
        "BlockIp": [],
        "DirectSites": private_domains,
        "DirectIp": private_ips,
        "DomainStrategy": "AsIs",
        "FakeDNS": "false",
    }
    encoded = base64.b64encode(
        json.dumps(decoded, ensure_ascii=True, separators=(",", ":")).encode()
    ).decode("ascii")
    return {
        "schemaVersion": policy.version,
        "product": policy.product,
        "consumer": "remnawave-legacy-routing-header",
        "encoding": "base64-json",
        "sourceStages": list(block_stages),
        "decoded": decoded,
        "value": encoded,
    }


def render_artifacts(policy: PremiumSmartRuPolicy) -> dict[str, bytes]:
    return {
        MIHOMO_NAME: _yaml_bytes(render_mihomo(policy)),
        XRAY_CLIENT_NAME: _json_bytes(render_xray_client(policy)),
        XRAY_SERVER_NAME: _json_bytes(render_xray_server(policy)),
        LEGACY_HEADER_NAME: _json_bytes(render_legacy_header(policy)),
    }
