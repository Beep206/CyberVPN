from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from src.application.vpn_testing.generated_subscription_checker import (
    PREMIUM_SMART_RU_MIHOMO_GROUPS,
    build_subscription_dry_run,
    generated_mihomo_artifact_summary,
    generated_subscription_checks,
)
from src.config.settings import settings


def _premium_smart_ru_plan() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name="premium_smart_ru_30",
        plan_code="premium_smart_ru",
        connection_modes=["standard", "stealth", "smart_routing"],
        server_pool=["premium_smart_ru"],
    )


def _generated_mihomo_yaml(*, include_all_groups: bool = True, include_xhttp: bool = True) -> str:
    groups = list(PREMIUM_SMART_RU_MIHOMO_GROUPS)
    if not include_all_groups:
        groups.remove("🇳🇱 NL Auto")
    proxy_network = "xhttp" if include_xhttp else "tcp"
    group_yaml = "\n".join(f"  - name: {name!r}\n    type: select\n    proxies: ['node-1']" for name in groups)
    return f"""
proxies:
  - name: node-1
    type: vless
    server: de-3.cyber-vpn.org
    port: 8443
    network: {proxy_network}
proxy-groups:
{group_yaml}
rules:
  - MATCH,🌍 World / EU
"""


def test_generated_subscription_requires_real_hardened_mihomo_artifact(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_subscription_template_name", "CyberVPN Premium Smart RU")
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", False)

    dry_run = build_subscription_dry_run(
        _premium_smart_ru_plan(),
        [SimpleNamespace(metadata_json={"domain": "gosuslugi.ru"})],
    )
    missing_artifact_checks = generated_subscription_checks(_premium_smart_ru_plan(), [])
    checks = generated_subscription_checks(
        _premium_smart_ru_plan(),
        [],
        generated_mihomo_artifact=_generated_mihomo_yaml(),
    )
    missing_by_key = {check["check_key"]: check for check in missing_artifact_checks}
    by_key = {check["check_key"]: check for check in checks}

    assert dry_run["mihomo"]["groups"] == []
    assert dry_run["mihomo"]["requires_generated_artifact"] is True
    assert missing_by_key["generated_subscription.mihomo_groups"]["status"] == "fail"
    assert missing_by_key["generated_subscription.xhttp_transport"]["status"] == "fail"
    assert by_key["generated_subscription.synthetic_safety"]["status"] == "pass"
    assert by_key["generated_subscription.mihomo_groups"]["status"] == "pass"
    assert by_key["generated_subscription.mihomo_groups"]["details"]["missing_groups"] == []
    assert by_key["generated_subscription.xhttp_transport"]["status"] == "pass"
    assert by_key["generated_subscription.remnawave_assignment"]["status"] == "pass"
    assert dry_run["mihomo"]["links_redacted"] is True
    assert dry_run["xray"]["links_redacted"] is True


def test_generated_subscription_rejects_mutated_artifact() -> None:
    missing_group = generated_subscription_checks(
        _premium_smart_ru_plan(),
        [],
        generated_mihomo_artifact=_generated_mihomo_yaml(include_all_groups=False),
    )
    no_xhttp = generated_subscription_checks(
        _premium_smart_ru_plan(),
        [],
        generated_mihomo_artifact=_generated_mihomo_yaml(include_xhttp=False),
    )
    missing_by_key = {check["check_key"]: check for check in missing_group}
    no_xhttp_by_key = {check["check_key"]: check for check in no_xhttp}

    assert missing_by_key["generated_subscription.mihomo_groups"]["status"] == "fail"
    assert "🇳🇱 NL Auto" in missing_by_key["generated_subscription.mihomo_groups"]["details"]["missing_groups"]
    assert no_xhttp_by_key["generated_subscription.xhttp_transport"]["status"] == "fail"
    assert generated_mihomo_artifact_summary(_generated_mihomo_yaml())["xhttp_proxy_count"] == 1
