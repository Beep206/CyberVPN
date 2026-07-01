"""Static and semantic Mihomo template analyzer for Premium Smart RU."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

try:  # PyYAML is provided by uvicorn[standard] in the backend runtime image.
    import yaml
except ImportError:  # pragma: no cover - fallback keeps diagnostics safe in minimal envs
    yaml = None  # type: ignore[assignment]

REQUIRED_GROUPS = ("🇩🇪 DE Auto", "🇷🇺 RU Sites", "🧲 Torrents")
RU_POLICY_NAME = "ru-services-inline"
EU_POLICY_NAME = "ru-eu-exceptions"
MATCH_PREFIX = "MATCH,"


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


def _group_names(groups: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(group.get("name") or "").strip() for group in groups if str(group.get("name") or "").strip()}


def _has_filtered_provider(group: Mapping[str, Any], marker: str) -> bool:
    normalized = json.dumps(group, ensure_ascii=False, sort_keys=True).lower()
    filter_tokens = ("filter", "include", "exclude", "provider")
    return marker.lower() in normalized and any(token in normalized for token in filter_tokens)


def _route_domains(route_entries: Sequence[Any]) -> set[str]:
    domains: set[str] = set()
    for entry in route_entries:
        metadata = getattr(entry, "metadata_json", None)
        if isinstance(metadata, dict):
            domain = str(metadata.get("domain") or "").strip().lower()
            if domain and not domain.endswith(".invalid"):
                domains.add(domain)
    return domains


def _rule_index(rules: Sequence[str], marker: str) -> int | None:
    marker_lower = marker.lower()
    for index, rule in enumerate(rules):
        if marker_lower in rule.lower():
            return index
    return None


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
    group_names = _group_names(groups)
    results: list[dict[str, Any]] = [
        _result(
            check_key="mihomo.yaml.parse",
            check_name="Mihomo YAML parses",
            status="pass",
            safe_summary="Mihomo template parsed without exposing generated credentials.",
            details={"group_count": len(groups), "rule_count": len(rules), "provider_count": len(providers)},
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

    match_indexes = [index for index, rule in enumerate(rules) if rule.strip().upper().startswith(MATCH_PREFIX)]
    match_is_last = bool(rules) and match_indexes == [len(rules) - 1] and not rules[-1].upper().endswith(",DIRECT")
    results.append(
        _result(
            check_key="mihomo.match.default",
            check_name="Mihomo MATCH default is safe",
            status="pass" if match_is_last else "fail",
            safe_summary="MATCH rule is the final fallback and does not use DIRECT"
            if match_is_last
            else "MATCH rule must be last and must not route DIRECT",
            details={"match_indexes": match_indexes, "last_rule": rules[-1] if rules else None},
        )
    )

    ru_index = _rule_index(rules, RU_POLICY_NAME)
    eu_index = _rule_index(rules, EU_POLICY_NAME)
    rule_order_ok = ru_index is not None and eu_index is not None and ru_index < eu_index
    results.append(
        _result(
            check_key="mihomo.rule_order.ru_before_eu",
            check_name="Mihomo RU/EU policy order",
            status="pass" if rule_order_ok else "fail",
            safe_summary="ru-services-inline appears before ru-eu-exceptions"
            if rule_order_ok
            else "ru-eu-exceptions must not shadow ru-services-inline",
            details={"ru_services_index": ru_index, "ru_eu_exceptions_index": eu_index},
        )
    )

    ru_group = next((group for group in groups if str(group.get("name")) == "🇷🇺 RU Sites"), {})
    de_group = next((group for group in groups if str(group.get("name")) == "🇩🇪 DE Auto"), {})
    ru_filtered = _has_filtered_provider(ru_group, "ru")
    de_filtered = _has_filtered_provider(de_group, "de")
    results.append(
        _result(
            check_key="mihomo.location_groups.filtered",
            check_name="Mihomo location groups filter providers",
            status="pass" if ru_filtered and de_filtered else "fail",
            safe_summary="RU and DE location groups use provider filters"
            if ru_filtered and de_filtered
            else "Location groups must not include all proxies without country filters",
            details={"ru_filtered": ru_filtered, "de_filtered": de_filtered},
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

    required_domains = _route_domains(route_entries)
    rule_text = "\n".join(rules).lower()
    covered_domains = sorted(domain for domain in required_domains if domain in rule_text)
    coverage_ratio = len(covered_domains) / max(1, len(required_domains))
    results.append(
        _result(
            check_key="mihomo.route_registry.coverage",
            check_name="Mihomo golden route coverage",
            status="pass" if coverage_ratio >= 0.75 else "fail",
            safe_summary="Mihomo rules cover the golden route registry"
            if coverage_ratio >= 0.75
            else "Mihomo rules do not cover enough golden routes",
            details={
                "required_route_count": len(required_domains),
                "covered_route_count": len(covered_domains),
                "coverage_ratio": round(coverage_ratio, 3),
            },
        )
    )

    abuse_ok = "🧲 Torrents" in group_names and any(
        "bittorrent" in rule.lower() or "torrent" in rule.lower() for rule in rules
    )
    results.append(
        _result(
            check_key="mihomo.abuse_sentinel",
            check_name="Mihomo abuse sentinel policy",
            status="pass" if abuse_ok else "fail",
            safe_summary="Torrent abuse route is explicitly handled"
            if abuse_ok
            else "Torrent abuse route is missing from static client policy",
            details={"torrent_group_present": "🧲 Torrents" in group_names},
        )
    )

    return results
