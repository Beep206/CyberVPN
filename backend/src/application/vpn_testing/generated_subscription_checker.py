"""Safe generated subscription dry-run checks for VPN Tester."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from src.config.settings import settings
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel

try:  # PyYAML is present in backend runtime through uvicorn[standard].
    import yaml
except ImportError:  # pragma: no cover - keeps import safe in minimal tooling envs
    yaml = None  # type: ignore[assignment]

PREMIUM_SMART_RU_MIHOMO_GROUPS = (
    "🌍 World / EU",
    "🇩🇪 DE Auto",
    "🇳🇱 NL Auto",
    "⚡ RU Auto",
    "🇷🇺 RU Sites",
    "🇷🇺 Moscow Auto",
    "🇷🇺 SPB Auto",
    "🧲 Torrents",
)


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
    proxy_count = 0
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
        xhttp_proxy_count = sum(
            1 for proxy in proxies if "xhttp" in json.dumps(proxy, ensure_ascii=False, sort_keys=True).lower()
        )

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None
    return {
        "source": source,
        "present": mapping is not None and parse_error is None,
        "parse_error": parse_error,
        "groups": groups,
        "group_count": len(groups),
        "proxy_count": proxy_count,
        "xhttp_proxy_count": xhttp_proxy_count,
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
        list(PREMIUM_SMART_RU_MIHOMO_GROUPS)
        if assignment["is_premium_smart_ru"]
        else ["🇩🇪 DE Auto", "🇷🇺 RU Sites", "🧲 Torrents"]
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
        list(PREMIUM_SMART_RU_MIHOMO_GROUPS)
        if assignment["is_premium_smart_ru"]
        else ["🇩🇪 DE Auto", "🇷🇺 RU Sites", "🧲 Torrents"]
    )
    artifact_groups = artifact_summary["groups"]
    missing_groups = sorted(set(required_groups) - set(artifact_groups))
    generated_groups_ok = (
        artifact_summary["present"] and not missing_groups
        if assignment["is_premium_smart_ru"]
        else not missing_groups or not artifact_summary["present"]
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
            "safe_summary": "Generated Mihomo artifact exposes required route groups"
            if generated_groups_ok
            else "Premium Smart RU generated Mihomo artifact is missing required route groups",
            "details": {
                "artifact_source": artifact_summary["source"],
                "artifact_present": artifact_summary["present"],
                "artifact_parse_error": artifact_summary["parse_error"],
                "group_count": artifact_summary["group_count"],
                "proxy_count": artifact_summary["proxy_count"],
                "xhttp_proxy_count": artifact_summary["xhttp_proxy_count"],
                "byte_count": artifact_summary["byte_count"],
                "sha256": artifact_summary["sha256"],
                "groups": artifact_groups,
                "required_groups": required_groups,
                "missing_groups": missing_groups if assignment["is_premium_smart_ru"] else [],
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
        xhttp_transport_ok = artifact_summary["xhttp_proxy_count"] > 0
        checks.append(
            {
                "check_key": "generated_subscription.xhttp_transport",
                "check_name": "Generated XHTTP transport",
                "category": "generated_subscription",
                "status": "pass" if xhttp_transport_ok else "fail",
                "severity": "error",
                "target": target,
                "safe_summary": "Generated Mihomo artifact includes XHTTP-capable proxies"
                if xhttp_transport_ok
                else "Generated Mihomo artifact has no XHTTP proxy evidence",
                "details": {
                    "artifact_source": artifact_summary["source"],
                    "artifact_present": artifact_summary["present"],
                    "xhttp_proxy_count": artifact_summary["xhttp_proxy_count"],
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
