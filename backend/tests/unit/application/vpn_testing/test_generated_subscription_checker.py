from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from src.application.vpn_testing.generated_subscription_checker import (
    PREMIUM_SMART_RU_MIHOMO_GROUPS,
    build_subscription_dry_run,
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


def test_generated_subscription_dry_run_requires_hardened_mihomo_groups(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_subscription_template_name", "CyberVPN Premium Smart RU")
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", False)

    dry_run = build_subscription_dry_run(
        _premium_smart_ru_plan(),
        [SimpleNamespace(metadata_json={"domain": "gosuslugi.ru"})],
    )
    checks = generated_subscription_checks(_premium_smart_ru_plan(), [])
    by_key = {check["check_key"]: check for check in checks}

    assert set(PREMIUM_SMART_RU_MIHOMO_GROUPS).issubset(dry_run["mihomo"]["groups"])
    assert by_key["generated_subscription.synthetic_safety"]["status"] == "pass"
    assert by_key["generated_subscription.mihomo_groups"]["status"] == "pass"
    assert by_key["generated_subscription.mihomo_groups"]["details"]["missing_groups"] == []
    assert by_key["generated_subscription.remnawave_assignment"]["status"] == "pass"
    assert dry_run["mihomo"]["links_redacted"] is True
    assert dry_run["xray"]["links_redacted"] is True
