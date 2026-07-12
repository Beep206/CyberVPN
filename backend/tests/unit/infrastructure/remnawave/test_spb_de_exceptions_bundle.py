from __future__ import annotations

from uuid import uuid4

import pytest

from src.config.settings import settings
from src.infrastructure.remnawave.spb_de_exceptions_bundle import (
    SPB_DE_EXCEPTIONS_PRODUCT_KEY,
    SpbDeExceptionsConfigurationError,
    is_spb_de_exceptions_plan,
    resolve_spb_de_exceptions_bundle,
    resolve_spb_de_exceptions_external_squad_uuid,
    resolve_spb_de_exceptions_internal_squad_uuids,
)
from tests.helpers.spb_de_readiness import enable_spb_de_readiness

OVERLAPPING_PLAN_CODES = "premium_smart_ru,premium_spb_de_exceptions"


def _configure_spb_de(
    monkeypatch: pytest.MonkeyPatch,
    *,
    external_squad_uuid: str | None = None,
    internal_squad_uuid: str | None = None,
    bridge_squad_uuid: str | None = None,
    profile_name: str = "S1 SPB DE Exceptions",
    policy_version: str = "premium_spb_de_exceptions.v1",
) -> tuple[str, str, str]:
    external = external_squad_uuid or str(uuid4())
    internal = internal_squad_uuid or str(uuid4())
    bridge = bridge_squad_uuid or str(uuid4())
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", external)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", internal)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", bridge)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_profile_name", profile_name)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_policy_version", policy_version)
    enable_spb_de_readiness(monkeypatch)
    return external, internal, bridge


def test_spb_de_exceptions_resolver_ignores_non_matching_plans(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", "")

    assert is_spb_de_exceptions_plan("premium_smart_ru") is False
    assert resolve_spb_de_exceptions_bundle("premium_smart_ru") is None
    assert resolve_spb_de_exceptions_external_squad_uuid("premium_smart_ru") is None
    assert resolve_spb_de_exceptions_internal_squad_uuids("premium_smart_ru") == []


def test_spb_de_exceptions_resolver_does_not_gate_smart_ru_when_plan_codes_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", OVERLAPPING_PLAN_CODES)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_bridge_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)

    assert is_spb_de_exceptions_plan("premium_smart_ru") is False
    assert resolve_spb_de_exceptions_bundle("premium_smart_ru") is None


@pytest.mark.parametrize(
    ("configured_plan_codes", "plan_code"),
    [
        ("premium_spb_de_exceptions", "premium_spb_de_exceptions"),
        ("premium_spb_de_exceptions", " Premium_SPB_DE_EXCEPTIONS "),
        ("task2_alias", "task2_alias"),
    ],
)
def test_spb_de_exceptions_resolver_fails_closed_until_data_plane_is_explicitly_ready(
    monkeypatch: pytest.MonkeyPatch,
    configured_plan_codes: str,
    plan_code: str,
) -> None:
    _configure_spb_de(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", configured_plan_codes)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)

    with pytest.raises(SpbDeExceptionsConfigurationError, match="data-plane is not marked ready"):
        resolve_spb_de_exceptions_bundle(plan_code)


def test_spb_de_exceptions_resolver_protects_canonical_plan_when_setting_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external, internal, bridge = _configure_spb_de(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "")
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    bundle = resolve_spb_de_exceptions_bundle("premium_spb_de_exceptions")

    assert is_spb_de_exceptions_plan("premium_spb_de_exceptions") is True
    assert bundle is not None
    assert bundle.external_squad_uuid == external
    assert bundle.internal_squad_uuids == (internal,)
    assert bundle.bridge_squad_uuid == bridge


def test_spb_de_exceptions_resolver_returns_isolated_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    smart_external = str(uuid4())
    smart_internal = str(uuid4())
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal)
    external, internal, bridge = _configure_spb_de(monkeypatch)

    bundle = resolve_spb_de_exceptions_bundle(" Premium_SPB_DE_EXCEPTIONS ")

    assert bundle is not None
    assert bundle.external_squad_uuid == external
    assert bundle.internal_squad_uuids == (internal,)
    assert bundle.bridge_squad_uuid == bridge
    assert bundle.external_squad_uuid != smart_external
    assert smart_internal not in bundle.internal_squad_uuids
    assert bundle.profile_name == "S1 SPB DE Exceptions"
    assert bundle.policy_version == "premium_spb_de_exceptions.v1"
    assert bundle.service_context() == {
        "remnawave_routing_product": SPB_DE_EXCEPTIONS_PRODUCT_KEY,
        "remnawave_external_squad_uuid": external,
        "remnawave_internal_squad_uuids": [internal],
        "remnawave_config_profile": "S1 SPB DE Exceptions",
        "remnawave_policy_version": "premium_spb_de_exceptions.v1",
        "remnawave_fail_closed_for_matched_exceptions": True,
    }
    assert bridge not in str(bundle.service_context())


@pytest.mark.parametrize(
    ("field_name", "value", "error_match"),
    [
        ("remnawave_spb_de_exceptions_external_squad_uuid", "", "EXTERNAL_SQUAD_UUID"),
        ("remnawave_spb_de_exceptions_internal_squad_uuid", "not-a-uuid", "INTERNAL_SQUAD_UUID"),
        ("remnawave_spb_de_exceptions_bridge_squad_uuid", "", "BRIDGE_SQUAD_UUID"),
        ("remnawave_spb_de_exceptions_bridge_squad_uuid", "not-a-uuid", "BRIDGE_SQUAD_UUID"),
        ("remnawave_spb_de_exceptions_profile_name", " ", "PROFILE_NAME"),
        ("remnawave_spb_de_exceptions_policy_version", "", "data-plane is not marked ready"),
    ],
)
def test_spb_de_exceptions_resolver_fails_closed_when_required_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    value: str,
    error_match: str,
) -> None:
    _configure_spb_de(monkeypatch)
    monkeypatch.setattr(settings, field_name, value)

    with pytest.raises(SpbDeExceptionsConfigurationError, match=error_match):
        resolve_spb_de_exceptions_bundle("premium_spb_de_exceptions")


def test_spb_de_exceptions_resolver_rejects_smart_ru_squad_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    smart_external = str(uuid4())
    smart_internal = str(uuid4())
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_external)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_internal)
    _configure_spb_de(monkeypatch, external_squad_uuid=smart_external, internal_squad_uuid=str(uuid4()))

    with pytest.raises(SpbDeExceptionsConfigurationError, match="must not reuse Premium Smart RU squads"):
        resolve_spb_de_exceptions_bundle("premium_spb_de_exceptions")


@pytest.mark.parametrize("collision_field", ["external", "internal"])
def test_spb_de_exceptions_resolver_rejects_bridge_squad_reuse(
    monkeypatch: pytest.MonkeyPatch,
    collision_field: str,
) -> None:
    bridge_squad_uuid = str(uuid4())
    external_squad_uuid = bridge_squad_uuid if collision_field == "external" else str(uuid4())
    internal_squad_uuid = bridge_squad_uuid if collision_field == "internal" else str(uuid4())
    _configure_spb_de(
        monkeypatch,
        external_squad_uuid=external_squad_uuid,
        internal_squad_uuid=internal_squad_uuid,
        bridge_squad_uuid=bridge_squad_uuid,
    )

    with pytest.raises(SpbDeExceptionsConfigurationError, match="must not use bridge squad"):
        resolve_spb_de_exceptions_bundle("premium_spb_de_exceptions")


def test_spb_de_exceptions_resolver_wraps_invalid_smart_ru_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_spb_de(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", "not-a-uuid")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")

    with pytest.raises(SpbDeExceptionsConfigurationError, match="REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID"):
        resolve_spb_de_exceptions_bundle("premium_spb_de_exceptions")


def test_spb_de_exceptions_resolver_rejects_smart_ru_plan_code_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_spb_de(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru,premium_spb_de_exceptions")

    with pytest.raises(SpbDeExceptionsConfigurationError, match="must not overlap Premium Smart RU plan codes"):
        resolve_spb_de_exceptions_bundle("premium_spb_de_exceptions")
