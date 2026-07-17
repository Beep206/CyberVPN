"""Static and semantic Mihomo template analyzer for Premium Smart RU."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

from src.application.vpn_testing.mihomo_rules import (
    mihomo_block_targets,
    mihomo_rule_provider_ids,
    mihomo_rule_subject_and_target,
    mihomo_text_matches_domains,
    split_mihomo_rule,
)

try:  # PyYAML is provided by uvicorn[standard] in the backend runtime image.
    import yaml
except ImportError:  # pragma: no cover - fallback keeps diagnostics safe in minimal envs
    yaml = None  # type: ignore[assignment]

REQUIRED_GROUPS = (
    "🌍 World / EU",
    "🇩🇪 DE Auto",
    "🇳🇱 NL Auto",
    "⚡ RU Auto",
    "🇷🇺 RU Sites",
    "🇷🇺 Moscow Auto",
    "🇷🇺 SPB Auto",
)
RU_POLICY_NAMES = ("ru-services-inline", "ru-apps", "geosite-ru", "geoip-for-ru")
EU_POLICY_NAMES = (
    "manual-eu-inline",
    "ru-eu-exceptions",
    "ru-inside",
    "refilter-domains",
    "refilter-ipsum",
    "ru-bundle",
    "rknasnblock",
)
REJECT_TARGETS = {"REJECT", "REJECT-DROP"}
MATCH_PREFIX = "MATCH,"
MATCH_TARGET = "🌍 World / EU"
STATIC_TORRENT_POLICY_MARKERS = (
    "bittorrent",
    "torrent-clients",
    "torrent-trackers",
    "torrent-websites",
    "torrent-domains-inline",
    "1337x.to",
    "eztv.re",
    "kinozal.tv",
    "limetorrents.lol",
    "nnmclub.to",
    "rutracker.org",
    "rutor.info",
    "thepiratebay.org",
    "torrentdownload.info",
    "torrentgalaxy.to",
    "yts.mx",
)
TORRENT_CATALOG_DOMAINS = STATIC_TORRENT_POLICY_MARKERS[5:]
TORRENT_GROUP_NAMES = {"🧲 Torrents", "Torrents"}
BLOCK_GROUP_NAMES = {*REJECT_TARGETS, "⛔ BLOCK", *TORRENT_GROUP_NAMES}
BLOCK_GROUP_TARGETS = {
    "block",
    "block policy",
    *(name.casefold() for name in BLOCK_GROUP_NAMES),
}
CATALOG_ACCESS_PROVIDER = "catalog-access-inline"
CATALOG_ACCESS_TARGETS = {"world / eu", "🌍 world / eu"}
REQUIRED_CATALOG_ACCESS_DOMAINS = set(TORRENT_CATALOG_DOMAINS)


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


def _result(
    *,
    check_key: str,
    check_name: str,
    status: str,
    safe_summary: str,
    details: Mapping[str, Any] | None = None,
    severity: str = "error",
    target: str = "mihomo",
    started: float | None = None,
) -> dict[str, Any]:
    return {
        "check_key": check_key,
        "check_name": check_name,
        "category": "mihomo",
        "status": status,
        "severity": severity,
        "target": target,
        "safe_summary": safe_summary,
        "details": dict(details or {}),
        "duration_ms": _elapsed_ms(started) if started is not None else 0,
    }


def _parse_template(template_text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not template_text.strip():
        return None, "empty_template"
    if yaml is not None:
        try:
            parsed = yaml.safe_load(template_text)
        except Exception as exc:  # noqa: BLE001 - analyzer returns safe typed failure
            return None, type(exc).__name__
    else:
        try:
            parsed = json.loads(template_text)
        except json.JSONDecodeError as exc:
            return None, f"json:{exc.msg}"
    if not isinstance(parsed, dict):
        return None, "template_root_not_object"
    return parsed, None


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _str_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _proxy_groups(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _list_dicts(config.get("proxy-groups") or config.get("proxy_groups"))


def _rules(config: Mapping[str, Any]) -> list[str]:
    return _str_items(config.get("rules"))


def _providers(config: Mapping[str, Any]) -> dict[str, Any]:
    value = config.get("proxy-providers") or config.get("proxy_providers") or {}
    return value if isinstance(value, dict) else {}


def _rule_providers(config: Mapping[str, Any]) -> dict[str, Any]:
    value = config.get("rule-providers") or config.get("rule_providers") or {}
    return value if isinstance(value, dict) else {}


def _group_names(groups: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(group.get("name") or "").strip() for group in groups if str(group.get("name") or "").strip()}


def _group_by_name(groups: Sequence[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
    return next((group for group in groups if str(group.get("name") or "").strip() == name), {})


def _group_proxies(group: Mapping[str, Any]) -> list[str]:
    value = group.get("proxies")
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _has_filtered_provider(group: Mapping[str, Any], marker: str) -> bool:
    normalized = json.dumps(group, ensure_ascii=False, sort_keys=True).lower()
    filter_tokens = ("filter", "include", "exclude", "provider")
    return marker.lower() in normalized and any(token in normalized for token in filter_tokens)


def _route_markers(route_entry: Any) -> list[str]:
    metadata = getattr(route_entry, "metadata_json", None)
    if not isinstance(metadata, dict):
        return []
    markers: list[str] = []
    domain = str(metadata.get("domain") or "").strip().lower()
    if domain and not domain.endswith(".invalid"):
        markers.append(domain)
    for key in ("expected_policy", "expected_group"):
        value = str(metadata.get(key) or "").strip().lower()
        if value:
            markers.append(value)
    return markers


def _rule_provider_text(rule_providers: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    for name, provider in rule_providers.items():
        chunks.append(str(name))
        if not isinstance(provider, Mapping):
            continue
        payload = provider.get("payload")
        if isinstance(payload, list):
            chunks.extend(str(item) for item in payload)
        url = provider.get("url")
        if url:
            chunks.append(str(url))
        path = provider.get("path")
        if path:
            chunks.append(str(path))
    return "\n".join(chunks).lower()


def _static_torrent_provider_ids(rule_providers: Mapping[str, Any]) -> list[str]:
    provider_ids: list[str] = []
    for name, provider in rule_providers.items():
        chunks = [str(name)]
        if isinstance(provider, Mapping):
            for field in ("url", "path"):
                value = provider.get(field)
                if value:
                    chunks.append(str(value))
            payload = provider.get("payload")
            if isinstance(payload, list):
                chunks.extend(str(item) for item in payload)
        normalized = "\n".join(chunks).casefold()
        if "torrent" in normalized or any(
            mihomo_text_matches_domains(chunk, TORRENT_CATALOG_DOMAINS) for chunk in chunks
        ):
            provider_ids.append(str(name))
    return sorted(provider_ids)


def _static_torrent_rules(
    rules: Sequence[str],
    rule_providers: Mapping[str, Any] | None = None,
    *,
    block_targets: set[str] | None = None,
) -> list[str]:
    torrent_provider_ids = {
        provider_id.casefold() for provider_id in _static_torrent_provider_ids(rule_providers or {})
    }
    static_rules: list[str] = []
    for rule in rules:
        subject, target = mihomo_rule_subject_and_target(rule)
        torrent_related = "torrent" in subject or mihomo_text_matches_domains(
            subject,
            TORRENT_CATALOG_DOMAINS,
        )
        torrent_related = torrent_related or bool(mihomo_rule_provider_ids(subject) & torrent_provider_ids)
        if torrent_related and target in (block_targets or BLOCK_GROUP_TARGETS):
            static_rules.append(rule)
    return static_rules


def _provider_domain_hosts(provider: Any) -> set[str]:
    if not isinstance(provider, Mapping):
        return set()
    payload = provider.get("payload")
    if not isinstance(payload, list):
        return set()
    return {
        parts[1].strip().casefold()
        for item in payload
        if isinstance(item, str)
        for parts in [split_mihomo_rule(item)]
        if len(parts) >= 2 and parts[0].casefold() in {"domain", "domain-suffix"}
    }


def _rule_index(rules: Sequence[str], marker: str) -> int | None:
    marker_lower = marker.lower()
    for index, rule in enumerate(rules):
        if marker_lower in rule.lower():
            return index
    return None


def _rule_indexes(rules: Sequence[str], marker: str) -> list[int]:
    marker_lower = marker.lower()
    return [index for index, rule in enumerate(rules) if marker_lower in rule.lower()]


def analyze_mihomo_template(template_text: str, route_entries: Sequence[Any]) -> list[dict[str, Any]]:
    started = perf_counter()
    config, parse_error = _parse_template(template_text)
    if config is None:
        return [
            _result(
                check_key="mihomo.yaml.parse",
                check_name="Mihomo YAML parses",
                status="fail",
                safe_summary=f"Mihomo template is not parseable: {parse_error}",
                details={"error": parse_error},
                started=started,
            )
        ]

    groups = _proxy_groups(config)
    rules = _rules(config)
    providers = _providers(config)
    rule_providers = _rule_providers(config)
    group_names = _group_names(groups)
    results: list[dict[str, Any]] = [
        _result(
            check_key="mihomo.yaml.parse",
            check_name="Mihomo YAML parses",
            status="pass",
            safe_summary="Mihomo template parsed without exposing generated credentials.",
            details={
                "group_count": len(groups),
                "rule_count": len(rules),
                "provider_count": len(providers),
                "rule_provider_count": len(rule_providers),
            },
            started=started,
        )
    ]

    missing_groups = sorted(set(REQUIRED_GROUPS) - group_names)
    results.append(
        _result(
            check_key="mihomo.required_groups",
            check_name="Mihomo required groups",
            status="pass" if not missing_groups else "fail",
            safe_summary="Required Premium Smart RU groups are present"
            if not missing_groups
            else f"Missing Mihomo groups: {', '.join(missing_groups)}",
            details={"required_groups": list(REQUIRED_GROUPS), "missing_groups": missing_groups},
        )
    )

    block_targets = mihomo_block_targets(groups, BLOCK_GROUP_TARGETS)
    parsed_rules = [mihomo_rule_subject_and_target(rule) for rule in rules]
    catalog_rule_indexes = [
        index
        for index, (subject, target) in enumerate(parsed_rules)
        if CATALOG_ACCESS_PROVIDER in mihomo_rule_provider_ids(subject) and target in CATALOG_ACCESS_TARGETS
    ]
    block_rule_indexes = [index for index, (_subject, target) in enumerate(parsed_rules) if target in block_targets]
    catalog_provider = next(
        (
            provider
            for name, provider in rule_providers.items()
            if str(name).strip().casefold() == CATALOG_ACCESS_PROVIDER
        ),
        None,
    )
    catalog_hosts = _provider_domain_hosts(catalog_provider)
    dns = config.get("dns")
    nameserver_policy = dns.get("nameserver-policy") if isinstance(dns, Mapping) else None
    dns_keys = (
        [str(key).strip().casefold() for key in nameserver_policy] if isinstance(nameserver_policy, Mapping) else []
    )
    catalog_dns_key = f"rule-set:{CATALOG_ACCESS_PROVIDER}"
    catalog_dns_index = dns_keys.index(catalog_dns_key) if catalog_dns_key in dns_keys else None
    blocked_dns_indexes = (
        [
            index
            for index, value in enumerate(nameserver_policy.values())
            if isinstance(value, list) and any(str(item).strip().casefold() == "rcode://name_error" for item in value)
        ]
        if isinstance(nameserver_policy, Mapping)
        else []
    )
    catalog_access_ok = (
        REQUIRED_CATALOG_ACCESS_DOMAINS.issubset(catalog_hosts)
        and len(catalog_rule_indexes) == 1
        and bool(block_rule_indexes)
        and all(catalog_rule_indexes[0] < index for index in block_rule_indexes)
        and catalog_dns_index is not None
        and bool(blocked_dns_indexes)
        and all(catalog_dns_index < index for index in blocked_dns_indexes)
    )
    results.append(
        _result(
            check_key="mihomo.rule_order.catalog_before_block",
            check_name="Mihomo catalog access precedes block policies",
            status="pass" if catalog_access_ok else "fail",
            safe_summary="Torrent catalog websites route through EU before block policies"
            if catalog_access_ok
            else "Catalog access must be an explicit EU and DNS exception before block policies",
            details={
                "catalog_provider": CATALOG_ACCESS_PROVIDER,
                "catalog_hosts": sorted(catalog_hosts),
                "required_catalog_hosts": sorted(REQUIRED_CATALOG_ACCESS_DOMAINS),
                "catalog_rule_indexes": catalog_rule_indexes,
                "block_rule_indexes": block_rule_indexes,
                "catalog_dns_index": catalog_dns_index,
                "blocked_dns_indexes": blocked_dns_indexes,
            },
        )
    )

    match_indexes = [index for index, rule in enumerate(rules) if rule.strip().upper().startswith(MATCH_PREFIX)]
    last_rule = rules[-1].strip() if rules else None
    match_is_last = bool(rules) and match_indexes == [len(rules) - 1] and last_rule == f"{MATCH_PREFIX}{MATCH_TARGET}"
    results.append(
        _result(
            check_key="mihomo.match.default",
            check_name="Mihomo MATCH default is safe",
            status="pass" if match_is_last else "fail",
            safe_summary="MATCH rule is the final World / EU fallback"
            if match_is_last
            else "MATCH rule must be last and must route to World / EU, not DIRECT",
            details={
                "match_indexes": match_indexes,
                "last_rule": last_rule,
                "required_last_rule": f"{MATCH_PREFIX}{MATCH_TARGET}",
            },
        )
    )

    eu_indexes = {name: _rule_indexes(rules, name) for name in EU_POLICY_NAMES}
    ru_indexes = {name: _rule_indexes(rules, name) for name in RU_POLICY_NAMES}
    present_eu_indexes = [index for indexes in eu_indexes.values() for index in indexes]
    present_ru_indexes = [index for indexes in ru_indexes.values() for index in indexes]
    rule_order_ok = (
        len(present_eu_indexes) == len(EU_POLICY_NAMES)
        and len(present_ru_indexes) == len(RU_POLICY_NAMES)
        and all(eu_index < ru_index for eu_index in present_eu_indexes for ru_index in present_ru_indexes)
    )
    results.append(
        _result(
            check_key="mihomo.rule_order.eu_before_ru",
            check_name="Mihomo RU/EU policy order",
            status="pass" if rule_order_ok else "fail",
            safe_summary="EU exceptions appear before broad RU services"
            if rule_order_ok
            else "Broad RU services must not shadow EU exceptions",
            details={"eu_indexes": eu_indexes, "ru_indexes": ru_indexes},
        )
    )

    location_group_markers = {
        "🇷🇺 RU Sites": "ru",
        "🇩🇪 DE Auto": "de",
        "🇳🇱 NL Auto": "nl",
        "🇷🇺 Moscow Auto": "moscow",
        "🇷🇺 SPB Auto": "spb",
    }
    location_filters = {}
    for group_name, marker in location_group_markers.items():
        group = _group_by_name(groups, group_name)
        location_filters[group_name] = _has_filtered_provider(group, marker)
    location_groups_filtered = all(location_filters.values())
    results.append(
        _result(
            check_key="mihomo.location_groups.filtered",
            check_name="Mihomo location groups filter providers",
            status="pass" if location_groups_filtered else "fail",
            safe_summary="RU, DE, NL, Moscow, and SPB location groups use provider filters"
            if location_groups_filtered
            else "Location groups must not include all proxies without country filters",
            details={"location_filters": location_filters},
        )
    )

    dns = config.get("dns")
    dns_ok = isinstance(dns, dict) and bool(dns.get("nameserver") or dns.get("enhanced-mode"))
    results.append(
        _result(
            check_key="mihomo.dns.policy",
            check_name="Mihomo DNS policy",
            status="pass" if dns_ok else "degraded",
            severity="warning",
            safe_summary="DNS policy is explicit" if dns_ok else "DNS policy is missing or sparse",
            details={"has_dns": isinstance(dns, dict)},
        )
    )

    route_markers = {
        getattr(entry, "route_key", str(index)): _route_markers(entry) for index, entry in enumerate(route_entries)
    }
    rule_text = "\n".join((("\n".join(rules)).lower(), _rule_provider_text(rule_providers)))
    covered_routes = sorted(
        route_key
        for route_key, markers in route_markers.items()
        if markers and any(marker in rule_text for marker in markers)
    )
    uncovered_routes = sorted(
        route_key for route_key, markers in route_markers.items() if markers and route_key not in covered_routes
    )
    coverage_ratio = len(covered_routes) / max(1, len(route_markers))
    results.append(
        _result(
            check_key="mihomo.route_registry.coverage",
            check_name="Mihomo golden route coverage",
            status="pass" if coverage_ratio >= 0.75 else "fail",
            safe_summary="Mihomo rules cover the golden route registry"
            if coverage_ratio >= 0.75
            else "Mihomo rules do not cover enough golden routes",
            details={
                "required_route_count": len(route_markers),
                "covered_route_count": len(covered_routes),
                "coverage_ratio": round(coverage_ratio, 3),
                "uncovered_route_keys": uncovered_routes[:20],
            },
        )
    )

    torrent_group_names = sorted(group_name for group_name in group_names if group_name in TORRENT_GROUP_NAMES)
    catalog_provider_ids = {provider_id.casefold() for provider_id in _static_torrent_provider_ids(rule_providers)}
    torrent_rules = _static_torrent_rules(
        rules,
        rule_providers,
        block_targets=block_targets,
    )
    blocked_torrent_provider_ids = sorted(
        {
            provider_id
            for rule in torrent_rules
            for provider_id in mihomo_rule_provider_ids(mihomo_rule_subject_and_target(rule)[0])
            if provider_id in catalog_provider_ids
        }
    )
    abuse_ok = not torrent_group_names and not torrent_rules
    results.append(
        _result(
            check_key="mihomo.abuse_sentinel",
            check_name="Mihomo abuse sentinel policy",
            status="pass" if abuse_ok else "fail",
            safe_summary="Torrent catalog traffic is not statically blocked by Mihomo"
            if abuse_ok
            else "Mihomo must not contain a torrent block group or static torrent process/domain block rules",
            details={
                "torrent_group_names": torrent_group_names,
                "static_torrent_provider_ids": blocked_torrent_provider_ids,
                "torrent_rule_count": len(torrent_rules),
                "static_torrent_rules": torrent_rules[:10],
                "protocol_block_owner": "remnawave_node_plugin_torrentBlocker",
            },
        )
    )

    block_group = _group_by_name(groups, "⛔ BLOCK")
    block_proxies = _group_proxies(block_group)
    tor_rules = [
        rule
        for rule in rules
        if rule.lower().startswith("rule-set,tor-inline,")
        or "torbrowser" in rule.lower()
        or "obfs4proxy" in rule.lower()
        or "snowflake-client" in rule.lower()
    ]
    block_group_rejects = bool(block_proxies) and set(block_proxies).issubset(REJECT_TARGETS)
    tor_rules_route_to_block_group = bool(tor_rules) and all(rule.strip().endswith(",⛔ BLOCK") for rule in tor_rules)
    tor_block_ok = block_group_rejects and tor_rules_route_to_block_group
    results.append(
        _result(
            check_key="mihomo.tor_block_sentinel",
            check_name="Mihomo TOR block policy",
            status="pass" if tor_block_ok else "fail",
            safe_summary="TOR routes are explicitly sent to BLOCK"
            if tor_block_ok
            else "TOR routes must be blocked through the BLOCK group",
            details={
                "block_group_present": "⛔ BLOCK" in group_names,
                "block_group_proxies": block_proxies,
                "block_group_rejects": block_group_rejects,
                "tor_rule_count": len(tor_rules),
                "tor_rules_route_to_block_group": tor_rules_route_to_block_group,
            },
        )
    )

    return results
