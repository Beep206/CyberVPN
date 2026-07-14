"""Safe generated subscription dry-run checks for VPN Tester."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from src.application.vpn_testing.mihomo_rules import (
    mihomo_block_targets,
    mihomo_rule_provider_ids,
    mihomo_rule_subject_and_target,
    mihomo_text_matches_domains,
    split_mihomo_rule,
)
from src.config.settings import settings
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel

try:  # PyYAML is present in backend runtime through uvicorn[standard].
    import yaml
except ImportError:  # pragma: no cover - keeps import safe in minimal tooling envs
    yaml = None  # type: ignore[assignment]

PREMIUM_SMART_RU_MIHOMO_GROUPS = (
    "🌍 World / EU",
    "🇷🇺 RU Sites",
    "📺 YouTube",
    "💬 Discord",
    "➤ Telegram",
    "💬 Messengers",
    "🤖 AI",
    "👨‍💻 Dev Services",
    "🎮 Games",
    "🧪 Speedtest",
    "⚡ EU Auto",
    "🇩🇪 DE Auto",
    "🇳🇱 NL Auto",
    "⚡ RU Auto",
    "🇷🇺 Moscow Auto",
    "🇷🇺 SPB Auto",
    "♻️ DIRECT",
    "⛔ BLOCK",
    "PROXY",
)
FORBIDDEN_STATIC_TORRENT_GROUPS = frozenset({"torrents", "🧲 torrents"})
TORRENT_BLOCK_TARGETS = frozenset(
    {
        "reject",
        "reject-drop",
        "block",
        "block policy",
        "⛔ block",
        *FORBIDDEN_STATIC_TORRENT_GROUPS,
    }
)
TORRENT_CATALOG_MARKERS = frozenset(
    {
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
    }
)
CATALOG_ACCESS_PROVIDER = "catalog-access-inline"
CATALOG_ACCESS_TARGETS = frozenset({"world / eu", "🌍 world / eu"})
REQUIRED_CATALOG_ACCESS_DOMAINS = TORRENT_CATALOG_MARKERS
EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT = 4
PREMIUM_SMART_RU_ENDPOINT_PORTS = {
    "de-relay.cyber-vpn.org": {"raw": 2053, "xhttp": 2083},
    "nl-4.cyber-vpn.org": {"raw": 443, "xhttp": 8443},
    "msk-relay.cyber-vpn.org": {"raw": 2053, "xhttp": 2083},
    "ru-spb-3.cyber-vpn.org": {"raw": 443, "xhttp": 8443},
}
PREMIUM_SMART_RU_REQUIRED_SERVERS = frozenset(PREMIUM_SMART_RU_ENDPOINT_PORTS)


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip().lower() for item in value.split(",") if item.strip()]
    return []


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _reality_opts(proxy: Mapping[str, Any]) -> Mapping[str, Any]:
    reality = proxy.get("reality-opts")
    return reality if isinstance(reality, Mapping) else {}


def _port_equals(proxy: Mapping[str, Any], expected: int) -> bool:
    try:
        return int(proxy.get("port") or 0) == expected
    except (TypeError, ValueError):
        return False


def _expected_port(proxy: Mapping[str, Any], transport: str) -> int | None:
    server = str(proxy.get("server") or "").strip().lower()
    return PREMIUM_SMART_RU_ENDPOINT_PORTS.get(server, {}).get(transport)


def _has_reality_sni(proxy: Mapping[str, Any]) -> bool:
    return bool(proxy.get("servername") or proxy.get("sni"))


def _has_reality_public_fields(proxy: Mapping[str, Any]) -> bool:
    reality = _reality_opts(proxy)
    return bool(reality.get("public-key")) and "short-id" in reality


def _is_xhttp_reality_vless(proxy: Mapping[str, Any]) -> bool:
    expected_port = _expected_port(proxy, "xhttp")
    return (
        str(proxy.get("type") or "").lower() == "vless"
        and str(proxy.get("network") or "").lower() == "xhttp"
        and expected_port is not None
        and _port_equals(proxy, expected_port)
        and proxy.get("tls") is True
        and _has_reality_sni(proxy)
        and _has_reality_public_fields(proxy)
    )


def _is_raw_tcp_reality_vless(proxy: Mapping[str, Any]) -> bool:
    network = str(proxy.get("network") or "tcp").lower()
    expected_port = _expected_port(proxy, "raw")
    return (
        str(proxy.get("type") or "").lower() == "vless"
        and network in {"", "tcp", "raw"}
        and expected_port is not None
        and _port_equals(proxy, expected_port)
        and proxy.get("tls") is True
        and str(proxy.get("flow") or "") == "xtls-rprx-vision"
        and _has_reality_sni(proxy)
        and _has_reality_public_fields(proxy)
    )


def _plan_code(plan: SubscriptionPlanModel) -> str:
    return str(plan.plan_code or plan.name or plan.id)


def _plan_target(plan: SubscriptionPlanModel) -> str:
    plan_code = _plan_code(plan)
    plan_name = str(plan.name or "").strip()
    return plan_name or plan_code


def _artifact_text(artifact: Any) -> str | None:
    if isinstance(artifact, str) and artifact.strip():
        return artifact
    if not isinstance(artifact, Mapping):
        return None
    for key in (
        "generated_mihomo_yaml",
        "mihomo_yaml",
        "generated_subscription_yaml",
        "subscription_yaml",
        "yaml",
        "body",
        "text",
        "content",
    ):
        value = artifact.get(key)
        if isinstance(value, str) and value.strip():
            return value
    nested = artifact.get("mihomo") or artifact.get("generated_mihomo")
    if isinstance(nested, Mapping):
        return _artifact_text(nested)
    return None


def _artifact_mapping(artifact: Any) -> Mapping[str, Any] | None:
    if isinstance(artifact, Mapping):
        if "proxy-groups" in artifact or "proxy_groups" in artifact:
            return artifact
        nested = artifact.get("mihomo") or artifact.get("generated_mihomo")
        if isinstance(nested, Mapping):
            if "proxy-groups" in nested or "proxy_groups" in nested or "groups" in nested:
                return nested
    return None


def _manual_torrent_rules(mapping: Mapping[str, Any]) -> list[str]:
    rules = mapping.get("rules")
    if not isinstance(rules, list):
        return []
    providers_value = mapping.get("rule-providers") or mapping.get("rule_providers")
    providers = providers_value if isinstance(providers_value, Mapping) else {}
    torrent_provider_ids: set[str] = set()
    for name, provider in providers.items():
        provider_text = json.dumps(
            {"name": name, "provider": provider},
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).casefold()
        if "torrent" in provider_text or mihomo_text_matches_domains(
            provider_text,
            TORRENT_CATALOG_MARKERS,
        ):
            torrent_provider_ids.add(str(name).strip().casefold())
    groups_value = mapping.get("proxy-groups") or mapping.get("proxy_groups")
    groups = [item for item in groups_value if isinstance(item, Mapping)] if isinstance(groups_value, list) else []
    block_targets = mihomo_block_targets(groups, TORRENT_BLOCK_TARGETS)
    manual_rules: list[str] = []
    for value in rules:
        if not isinstance(value, str):
            continue
        subject, policy = mihomo_rule_subject_and_target(value)
        torrent_related = (
            "torrent" in subject
            or mihomo_text_matches_domains(subject, TORRENT_CATALOG_MARKERS)
            or bool(mihomo_rule_provider_ids(subject) & torrent_provider_ids)
        )
        if torrent_related and policy in block_targets:
            manual_rules.append(value)
    return manual_rules


def _catalog_access_summary(mapping: Mapping[str, Any]) -> dict[str, Any]:
    rules = [str(rule).strip() for rule in mapping.get("rules", []) if str(rule).strip()]
    groups = _list_dicts(mapping.get("proxy-groups") or mapping.get("proxy_groups"))
    providers = mapping.get("rule-providers") or mapping.get("rule_providers")
    provider = (
        next(
            (value for name, value in providers.items() if str(name).strip().casefold() == CATALOG_ACCESS_PROVIDER),
            None,
        )
        if isinstance(providers, Mapping)
        else None
    )
    payload = provider.get("payload") if isinstance(provider, Mapping) else None
    catalog_hosts = (
        {
            parts[1].strip().casefold()
            for item in payload
            if isinstance(item, str)
            for parts in [split_mihomo_rule(item)]
            if len(parts) >= 2 and parts[0].casefold() in {"domain", "domain-suffix"}
        }
        if isinstance(payload, list)
        else set()
    )
    block_targets = mihomo_block_targets(groups, TORRENT_BLOCK_TARGETS)
    parsed_rules = [mihomo_rule_subject_and_target(rule) for rule in rules]
    catalog_rule_indexes = [
        index
        for index, (subject, target) in enumerate(parsed_rules)
        if CATALOG_ACCESS_PROVIDER in mihomo_rule_provider_ids(subject) and target in CATALOG_ACCESS_TARGETS
    ]
    block_rule_indexes = [index for index, (_subject, target) in enumerate(parsed_rules) if target in block_targets]
    dns = mapping.get("dns")
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
    safe = (
        REQUIRED_CATALOG_ACCESS_DOMAINS.issubset(catalog_hosts)
        and len(catalog_rule_indexes) == 1
        and bool(block_rule_indexes)
        and all(catalog_rule_indexes[0] < index for index in block_rule_indexes)
        and catalog_dns_index is not None
        and bool(blocked_dns_indexes)
        and all(catalog_dns_index < index for index in blocked_dns_indexes)
    )
    return {
        "safe": safe,
        "catalog_hosts": sorted(catalog_hosts),
        "catalog_rule_indexes": catalog_rule_indexes,
        "block_rule_indexes": block_rule_indexes,
        "catalog_dns_index": catalog_dns_index,
        "blocked_dns_indexes": blocked_dns_indexes,
    }


def generated_mihomo_artifact_summary(artifact: Any) -> dict[str, Any]:
    text = _artifact_text(artifact)
    mapping = _artifact_mapping(artifact)
    parse_error: str | None = None
    source = "mapping" if mapping is not None else "missing"

    if mapping is None and text is not None:
        source = "yaml_text"
        try:
            if yaml is not None:
                parsed = yaml.safe_load(text)
            else:
                parsed = json.loads(text)
            if isinstance(parsed, Mapping):
                mapping = parsed
            else:
                parse_error = "artifact_root_not_object"
        except Exception as exc:  # noqa: BLE001 - checker reports safe typed failure
            parse_error = type(exc).__name__

    groups: list[str] = []
    xhttp_proxy_count = 0
    vless_reality_tcp_proxy_count = 0
    raw_server_counts: Counter[str] = Counter()
    xhttp_server_counts: Counter[str] = Counter()
    proxy_count = 0
    manual_torrent_groups: list[str] = []
    manual_torrent_rules: list[str] = []
    catalog_access = {
        "safe": False,
        "catalog_hosts": [],
        "catalog_rule_indexes": [],
        "block_rule_indexes": [],
        "catalog_dns_index": None,
        "blocked_dns_indexes": [],
    }
    if mapping is not None:
        if isinstance(mapping.get("groups"), list):
            groups = [str(item).strip() for item in mapping.get("groups", []) if str(item).strip()]
        else:
            groups = [
                str(group.get("name") or "").strip()
                for group in _list_dicts(mapping.get("proxy-groups") or mapping.get("proxy_groups"))
                if str(group.get("name") or "").strip()
            ]
        proxies = _list_dicts(mapping.get("proxies"))
        proxy_count = len(proxies)
        valid_xhttp = [proxy for proxy in proxies if _is_xhttp_reality_vless(proxy)]
        valid_raw = [proxy for proxy in proxies if _is_raw_tcp_reality_vless(proxy)]
        xhttp_proxy_count = len(valid_xhttp)
        vless_reality_tcp_proxy_count = len(valid_raw)
        raw_server_counts.update(str(proxy.get("server") or "").strip().lower() for proxy in valid_raw)
        xhttp_server_counts.update(str(proxy.get("server") or "").strip().lower() for proxy in valid_xhttp)
        manual_torrent_groups = sorted(group for group in groups if group.casefold() in FORBIDDEN_STATIC_TORRENT_GROUPS)
        manual_torrent_rules = _manual_torrent_rules(mapping)
        catalog_access = _catalog_access_summary(mapping)

    expected_server_counts = Counter({server: 1 for server in PREMIUM_SMART_RU_REQUIRED_SERVERS})
    raw_location_matrix_valid = raw_server_counts == expected_server_counts
    xhttp_location_matrix_valid = xhttp_server_counts == expected_server_counts

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None
    return {
        "source": source,
        "present": mapping is not None and parse_error is None,
        "parse_error": parse_error,
        "groups": groups,
        "group_count": len(groups),
        "proxy_count": proxy_count,
        "xhttp_proxy_count": xhttp_proxy_count,
        "vless_reality_tcp_proxy_count": vless_reality_tcp_proxy_count,
        "raw_location_matrix_valid": raw_location_matrix_valid,
        "xhttp_location_matrix_valid": xhttp_location_matrix_valid,
        "manual_torrent_policy_absent": not manual_torrent_groups and not manual_torrent_rules,
        "manual_torrent_groups": manual_torrent_groups,
        "manual_torrent_rules": manual_torrent_rules,
        "catalog_access_before_block": catalog_access["safe"],
        "catalog_access": catalog_access,
        "byte_count": len(text.encode("utf-8")) if text is not None else 0,
        "sha256": digest,
    }


def expected_remnawave_assignment(plan: SubscriptionPlanModel) -> dict[str, Any]:
    plan_code = _plan_code(plan).lower()
    connection_modes = _str_list(plan.connection_modes)
    server_pool = _str_list(plan.server_pool)
    smart_ru_codes = set(_str_list(settings.remnawave_smart_ru_plan_codes))
    is_smart_ru = plan_code in smart_ru_codes or "premium_smart_ru" in server_pool
    internal_squad_present = bool(settings.remnawave_smart_ru_internal_squad_uuid) if is_smart_ru else None
    external_squad_present = bool(settings.remnawave_smart_ru_external_squad_uuid) if is_smart_ru else None
    template_present = bool(settings.remnawave_smart_ru_subscription_template_name) if is_smart_ru else None
    return {
        "plan_code": plan_code,
        "is_premium_smart_ru": is_smart_ru,
        "expected_internal_squad_uuid_present": internal_squad_present,
        "expected_external_squad_uuid_present": external_squad_present,
        "expected_subscription_template_name_present": template_present,
        "requires_xhttp": is_smart_ru or "xhttp" in connection_modes,
        "server_pool": server_pool,
        "connection_modes": connection_modes,
    }


def build_subscription_dry_run(plan: SubscriptionPlanModel, route_entries: Sequence[Any]) -> dict[str, Any]:
    assignment = expected_remnawave_assignment(plan)
    expected_groups = (
        list(PREMIUM_SMART_RU_MIHOMO_GROUPS) if assignment["is_premium_smart_ru"] else ["🇩🇪 DE Auto", "🇷🇺 RU Sites"]
    )
    route_domains = []
    for entry in route_entries:
        metadata = getattr(entry, "metadata_json", None)
        if isinstance(metadata, Mapping):
            domain = str(metadata.get("domain") or "").strip()
            if domain:
                route_domains.append(domain)
    return {
        "source": "dry_run",
        "synthetic_user_created": False,
        "plan_code": assignment["plan_code"],
        "assignment": assignment,
        "mihomo": {
            "groups": [],
            "expected_groups": expected_groups,
            "route_domain_count": len(route_domains),
            "links_redacted": True,
            "requires_generated_artifact": bool(assignment["is_premium_smart_ru"]),
        },
        "xray": {
            "outbounds": ["premium_smart_ru_internal", "premium_smart_ru_external"]
            if assignment["is_premium_smart_ru"]
            else ["default"],
            "links_redacted": True,
        },
    }


def generated_subscription_checks(
    plan: SubscriptionPlanModel,
    route_entries: Sequence[Any],
    *,
    generated_mihomo_artifact: Any = None,
) -> list[dict[str, Any]]:
    dry_run = build_subscription_dry_run(plan, route_entries)
    assignment = dry_run["assignment"]
    target = _plan_target(plan)
    artifact_summary = generated_mihomo_artifact_summary(generated_mihomo_artifact)
    required_groups = (
        list(PREMIUM_SMART_RU_MIHOMO_GROUPS) if assignment["is_premium_smart_ru"] else ["🇩🇪 DE Auto", "🇷🇺 RU Sites"]
    )
    artifact_groups = artifact_summary["groups"]
    missing_groups = sorted(set(required_groups) - set(artifact_groups))
    generated_groups_ok = (
        artifact_summary["present"]
        and not missing_groups
        and artifact_summary["manual_torrent_policy_absent"]
        and artifact_summary["catalog_access_before_block"]
        if assignment["is_premium_smart_ru"]
        else (not missing_groups and artifact_summary["manual_torrent_policy_absent"])
        or not artifact_summary["present"]
    )
    checks: list[dict[str, Any]] = [
        {
            "check_key": "generated_subscription.synthetic_safety",
            "check_name": "Generated subscription synthetic safety",
            "category": "generated_subscription",
            "status": "pass" if not settings.vpn_tester_synthetic_users_enabled else "degraded",
            "severity": "warning",
            "target": target,
            "safe_summary": "Dry-run subscription validation did not create a production synthetic user"
            if not settings.vpn_tester_synthetic_users_enabled
            else "Synthetic user creation is enabled by environment and must be operator-approved",
            "details": {"synthetic_user_created": False, "source": dry_run["source"]},
            "duration_ms": 0,
        },
        {
            "check_key": "generated_subscription.mihomo_groups",
            "check_name": "Generated Mihomo groups",
            "category": "generated_subscription",
            "status": "pass" if generated_groups_ok else "fail",
            "severity": "error",
            "target": target,
            "safe_summary": (
                "Generated Mihomo artifact exposes required groups and early "
                "catalog access without static torrent policy"
            )
            if generated_groups_ok
            else (
                "Generated Mihomo artifact has missing groups, unsafe catalog order, or forbidden static torrent policy"
            ),
            "details": {
                "artifact_source": artifact_summary["source"],
                "artifact_present": artifact_summary["present"],
                "artifact_parse_error": artifact_summary["parse_error"],
                "group_count": artifact_summary["group_count"],
                "proxy_count": artifact_summary["proxy_count"],
                "xhttp_proxy_count": artifact_summary["xhttp_proxy_count"],
                "vless_reality_tcp_proxy_count": artifact_summary["vless_reality_tcp_proxy_count"],
                "byte_count": artifact_summary["byte_count"],
                "sha256": artifact_summary["sha256"],
                "groups": artifact_groups,
                "required_groups": required_groups,
                "missing_groups": missing_groups if assignment["is_premium_smart_ru"] else [],
                "manual_torrent_policy_absent": artifact_summary["manual_torrent_policy_absent"],
                "manual_torrent_groups": artifact_summary["manual_torrent_groups"],
                "manual_torrent_rules": artifact_summary["manual_torrent_rules"],
                "catalog_access_before_block": artifact_summary["catalog_access_before_block"],
                "catalog_access": artifact_summary["catalog_access"],
                "links_redacted": True,
            },
            "duration_ms": 0,
        },
        {
            "check_key": "generated_subscription.xray_outbounds",
            "check_name": "Generated Xray outbounds",
            "category": "generated_subscription",
            "status": "pass" if dry_run["xray"]["outbounds"] else "fail",
            "severity": "error",
            "target": target,
            "safe_summary": "Dry-run Xray artifact contains outbound assignment metadata",
            "details": {"outbound_count": len(dry_run["xray"]["outbounds"]), "links_redacted": True},
            "duration_ms": 0,
        },
    ]
    if assignment["is_premium_smart_ru"]:
        expected_profile_count = EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT
        raw_vless_ok = (
            artifact_summary["vless_reality_tcp_proxy_count"] == expected_profile_count
            and artifact_summary["raw_location_matrix_valid"] is True
        )
        checks.append(
            {
                "check_key": "generated_subscription.vless_reality_raw_tcp",
                "check_name": "Generated VLESS Reality RAW/TCP profiles",
                "category": "generated_subscription",
                "status": "pass" if raw_vless_ok else "fail",
                "severity": "error",
                "target": target,
                "safe_summary": "Generated subscription contains four valid VLESS Reality RAW/TCP profiles"
                if raw_vless_ok
                else "Generated subscription does not contain four valid VLESS Reality RAW/TCP profiles",
                "details": {
                    "expected_count": expected_profile_count,
                    "actual_count": artifact_summary["vless_reality_tcp_proxy_count"],
                    "required_location_count": len(PREMIUM_SMART_RU_REQUIRED_SERVERS),
                    "location_matrix_valid": artifact_summary["raw_location_matrix_valid"],
                    "links_redacted": True,
                },
                "duration_ms": 0,
            }
        )
        xhttp_transport_ok = (
            artifact_summary["xhttp_proxy_count"] == expected_profile_count
            and artifact_summary["xhttp_location_matrix_valid"] is True
        )
        checks.append(
            {
                "check_key": "generated_subscription.xhttp_transport",
                "check_name": "Generated XHTTP transport",
                "category": "generated_subscription",
                "status": "pass" if xhttp_transport_ok else "fail",
                "severity": "error",
                "target": target,
                "safe_summary": "Generated subscription contains four valid XHTTP Reality profiles"
                if xhttp_transport_ok
                else "Generated subscription does not contain four valid XHTTP Reality profiles",
                "details": {
                    "artifact_source": artifact_summary["source"],
                    "artifact_present": artifact_summary["present"],
                    "expected_count": expected_profile_count,
                    "actual_count": artifact_summary["xhttp_proxy_count"],
                    "required_location_count": len(PREMIUM_SMART_RU_REQUIRED_SERVERS),
                    "location_matrix_valid": artifact_summary["xhttp_location_matrix_valid"],
                    "xhttp_proxy_count": artifact_summary["xhttp_proxy_count"],
                    "vless_reality_tcp_proxy_count": artifact_summary["vless_reality_tcp_proxy_count"],
                    "proxy_count": artifact_summary["proxy_count"],
                    "links_redacted": True,
                },
                "duration_ms": 0,
            }
        )
        squad_ok = bool(assignment["expected_internal_squad_uuid_present"]) and bool(
            assignment["expected_external_squad_uuid_present"]
        )
        checks.append(
            {
                "check_key": "generated_subscription.remnawave_assignment",
                "check_name": "Premium Smart RU Remnawave assignment",
                "category": "generated_subscription",
                "status": "pass" if squad_ok else "fail",
                "severity": "error",
                "target": target,
                "safe_summary": "Premium Smart RU has internal and external squad assignment intent"
                if squad_ok
                else "Premium Smart RU squad assignment environment is incomplete",
                "details": {
                    "internal_squad_configured": bool(assignment["expected_internal_squad_uuid_present"]),
                    "external_squad_configured": bool(assignment["expected_external_squad_uuid_present"]),
                    "template_configured": bool(assignment["expected_subscription_template_name_present"]),
                },
                "duration_ms": 0,
            }
        )
    return checks
