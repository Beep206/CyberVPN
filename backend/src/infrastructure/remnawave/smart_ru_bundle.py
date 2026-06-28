"""Remnawave CyberVPN Premium Smart RU routing helpers."""

from __future__ import annotations

from uuid import UUID

from src.config.settings import settings

SMART_RU_BUNDLE_TEMPLATE_NAME = "CyberVPN Premium Smart RU"


class SmartRuConfigurationError(RuntimeError):
    """Raised when an eligible Smart RU plan lacks required routing settings."""


def _configured_plan_codes(raw_codes: str) -> set[str]:
    return {item.strip().lower() for item in raw_codes.split(",") if item.strip()}


def _required_uuid(value: str, *, setting_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise SmartRuConfigurationError(f"Premium Smart RU provisioning requires {setting_name}")
    try:
        UUID(normalized)
    except ValueError as exc:
        raise SmartRuConfigurationError(f"Premium Smart RU provisioning has invalid {setting_name}") from exc
    return normalized


def is_smart_ru_plan(plan_code: str | None) -> bool:
    """Return whether a plan should use the Premium Smart RU Mihomo bundle."""

    normalized_plan_code = (plan_code or "").strip().lower()
    if not normalized_plan_code:
        return False
    return normalized_plan_code in _configured_plan_codes(settings.remnawave_smart_ru_plan_codes)


def resolve_smart_ru_external_squad_uuid(plan_code: str | None) -> str | None:
    """Return the configured Premium Smart RU external squad UUID for eligible plans."""

    if not is_smart_ru_plan(plan_code):
        return None

    return _required_uuid(
        settings.remnawave_smart_ru_external_squad_uuid,
        setting_name="REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID",
    )


def resolve_smart_ru_internal_squad_uuids(plan_code: str | None) -> list[str]:
    """Return Premium Smart RU internal squad UUIDs for Remnawave user payloads."""

    if not is_smart_ru_plan(plan_code):
        return []

    return [
        _required_uuid(
            settings.remnawave_smart_ru_internal_squad_uuid,
            setting_name="REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID",
        )
    ]
