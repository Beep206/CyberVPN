"""Stage 1 Remnawave RU bundle routing helpers."""

from __future__ import annotations

from src.config.settings import settings

STAGE1_RU_BUNDLE_TEMPLATE_NAME = "Mihomo (RU bundle)"


def is_stage1_ru_bundle_plan(plan_code: str | None) -> bool:
    """Return whether a plan should use the S1 RU Mihomo bundle."""

    normalized_plan_code = (plan_code or "").strip().lower()
    if not normalized_plan_code:
        return False
    configured_plan_codes = {
        item.strip().lower()
        for item in settings.remnawave_ru_bundle_plan_codes.split(",")
        if item.strip()
    }
    return normalized_plan_code in configured_plan_codes


def resolve_stage1_ru_bundle_external_squad_uuid(plan_code: str | None) -> str | None:
    """Return the external squad UUID for RU bundle plans when configured."""

    if not is_stage1_ru_bundle_plan(plan_code):
        return None

    configured_uuid = settings.remnawave_ru_bundle_external_squad_uuid.strip()
    return configured_uuid or None
