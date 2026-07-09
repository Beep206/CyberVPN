"""Safe generated subscription dry-run checks for VPN Tester."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.config.settings import settings
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel

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


def _plan_code(plan: SubscriptionPlanModel) -> str:
    return str(plan.plan_code or plan.name or plan.id)


def _plan_target(plan: SubscriptionPlanModel) -> str:
    plan_code = _plan_code(plan)
    plan_name = str(plan.name or "").strip()
    return plan_name or plan_code


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
    groups = list(PREMIUM_SMART_RU_MIHOMO_GROUPS) if assignment["is_premium_smart_ru"] else [
        "🇩🇪 DE Auto",
        "🇷🇺 RU Sites",
        "🧲 Torrents",
    ]
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
            "groups": groups,
            "route_domain_count": len(route_domains),
            "links_redacted": True,
        },
        "xray": {
            "outbounds": ["premium_smart_ru_internal", "premium_smart_ru_external"]
            if assignment["is_premium_smart_ru"]
            else ["default"],
            "links_redacted": True,
        },
    }


def generated_subscription_checks(plan: SubscriptionPlanModel, route_entries: Sequence[Any]) -> list[dict[str, Any]]:
    dry_run = build_subscription_dry_run(plan, route_entries)
    assignment = dry_run["assignment"]
    target = _plan_target(plan)
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
            "status": "pass"
            if set(PREMIUM_SMART_RU_MIHOMO_GROUPS).issubset(set(dry_run["mihomo"]["groups"]))
            or not assignment["is_premium_smart_ru"]
            else "fail",
            "severity": "error",
            "target": target,
            "safe_summary": "Dry-run Mihomo artifact exposes required route groups",
            "details": {
                "groups": dry_run["mihomo"]["groups"],
                "required_groups": list(PREMIUM_SMART_RU_MIHOMO_GROUPS)
                if assignment["is_premium_smart_ru"]
                else ["🇩🇪 DE Auto", "🇷🇺 RU Sites", "🧲 Torrents"],
                "missing_groups": sorted(
                    set(PREMIUM_SMART_RU_MIHOMO_GROUPS) - set(dry_run["mihomo"]["groups"])
                )
                if assignment["is_premium_smart_ru"]
                else [],
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
