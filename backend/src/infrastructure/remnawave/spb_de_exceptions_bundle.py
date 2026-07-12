"""Remnawave routing helpers for Premium SPB + DE Exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.services.vpn_product_readiness import (
    SPB_DE_EXCEPTIONS_PRODUCT_CODE,
    VpnProductReadinessError,
    configured_plan_codes,
)
from src.application.services.vpn_product_readiness import (
    ensure_spb_de_exceptions_data_plane_ready as ensure_task2_data_plane_ready,
)
from src.application.services.vpn_product_readiness import (
    is_spb_de_exceptions_plan as is_task2_spb_de_exceptions_plan,
)
from src.config.settings import settings

SPB_DE_EXCEPTIONS_PRODUCT_KEY = SPB_DE_EXCEPTIONS_PRODUCT_CODE
SPB_DE_EXCEPTIONS_EXTERNAL_SQUAD_NAME = "CYBERVPN_SPB_DE_EXCEPTIONS"
SPB_DE_EXCEPTIONS_INTERNAL_SQUAD_NAME = "CYBERVPN_SPB_DE_NODES"


class SpbDeExceptionsConfigurationError(RuntimeError):
    """Raised when an eligible SPB/DE plan lacks isolated routing settings."""


@dataclass(frozen=True)
class SpbDeExceptionsRoutingBundle:
    external_squad_uuid: str
    internal_squad_uuids: tuple[str, ...]
    bridge_squad_uuid: str
    profile_name: str
    policy_version: str

    def service_context(self) -> dict[str, object]:
        return {
            "remnawave_routing_product": SPB_DE_EXCEPTIONS_PRODUCT_KEY,
            "remnawave_external_squad_uuid": self.external_squad_uuid,
            "remnawave_internal_squad_uuids": list(self.internal_squad_uuids),
            "remnawave_config_profile": self.profile_name,
            "remnawave_policy_version": self.policy_version,
            "remnawave_fail_closed_for_matched_exceptions": True,
        }


def _configured_plan_codes(raw_codes: str) -> set[str]:
    return configured_plan_codes(raw_codes)


def _required_uuid(value: str, *, setting_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise SpbDeExceptionsConfigurationError(f"Premium SPB/DE provisioning requires {setting_name}")
    try:
        UUID(normalized)
    except ValueError as exc:
        raise SpbDeExceptionsConfigurationError(f"Premium SPB/DE provisioning has invalid {setting_name}") from exc
    return normalized


def _required_text(value: str, *, setting_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise SpbDeExceptionsConfigurationError(f"Premium SPB/DE provisioning requires {setting_name}")
    return normalized


def _uuid_key(value: str) -> str:
    return str(UUID(value.strip()))


def _optional_uuid_key(value: str, *, setting_name: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return str(UUID(normalized))
    except ValueError as exc:
        raise SpbDeExceptionsConfigurationError(
            f"Premium SPB/DE provisioning cannot compare invalid {setting_name}"
        ) from exc


def _reject_smart_ru_squad_reuse(*, external_squad_uuid: str, internal_squad_uuids: tuple[str, ...]) -> None:
    smart_squad_uuids = {
        value
        for value in (
            _optional_uuid_key(
                settings.remnawave_smart_ru_external_squad_uuid,
                setting_name="REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID",
            ),
            _optional_uuid_key(
                settings.remnawave_smart_ru_internal_squad_uuid,
                setting_name="REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID",
            ),
        )
        if value is not None
    }
    if not smart_squad_uuids:
        return

    spb_de_squad_uuids = {_uuid_key(external_squad_uuid), *(_uuid_key(value) for value in internal_squad_uuids)}
    if spb_de_squad_uuids & smart_squad_uuids:
        raise SpbDeExceptionsConfigurationError("Premium SPB/DE provisioning must not reuse Premium Smart RU squads")


def _reject_bridge_squad_reuse(
    *,
    bridge_squad_uuid: str,
    external_squad_uuid: str,
    internal_squad_uuids: tuple[str, ...],
) -> None:
    bridge_uuid_key = _uuid_key(bridge_squad_uuid)
    customer_squad_uuids = {_uuid_key(external_squad_uuid), *(_uuid_key(value) for value in internal_squad_uuids)}
    if bridge_uuid_key in customer_squad_uuids:
        raise SpbDeExceptionsConfigurationError("Premium SPB/DE customer provisioning must not use bridge squad")


def _reject_smart_ru_plan_code_overlap(plan_code: str | None) -> None:
    normalized_plan_code = (plan_code or "").strip().lower()
    if normalized_plan_code in _configured_plan_codes(settings.remnawave_smart_ru_plan_codes):
        raise SpbDeExceptionsConfigurationError(
            "Premium SPB/DE provisioning plan codes must not overlap Premium Smart RU plan codes"
        )


def ensure_spb_de_exceptions_data_plane_ready(plan_code: str | None) -> bool:
    """Fail closed for Task2 plans until the deployed data plane is explicitly ready."""

    try:
        return ensure_task2_data_plane_ready(plan_code)
    except VpnProductReadinessError as exc:
        raise SpbDeExceptionsConfigurationError("Premium SPB/DE data-plane is not marked ready") from exc


def is_spb_de_exceptions_plan(plan_code: str | None) -> bool:
    """Return whether a plan must use the SPB default with DE exceptions routing."""

    return is_task2_spb_de_exceptions_plan(plan_code)


def resolve_spb_de_exceptions_bundle(plan_code: str | None) -> SpbDeExceptionsRoutingBundle | None:
    """Return the isolated Remnawave routing bundle for eligible SPB/DE plans."""

    if not is_spb_de_exceptions_plan(plan_code):
        return None

    ensure_spb_de_exceptions_data_plane_ready(plan_code)
    _reject_smart_ru_plan_code_overlap(plan_code)
    external_squad_uuid = _required_uuid(
        settings.remnawave_spb_de_exceptions_external_squad_uuid,
        setting_name="REMNAWAVE_SPB_DE_EXCEPTIONS_EXTERNAL_SQUAD_UUID",
    )
    internal_squad_uuids = (
        _required_uuid(
            settings.remnawave_spb_de_exceptions_internal_squad_uuid,
            setting_name="REMNAWAVE_SPB_DE_EXCEPTIONS_INTERNAL_SQUAD_UUID",
        ),
    )
    bridge_squad_uuid = _required_uuid(
        settings.remnawave_spb_de_exceptions_bridge_squad_uuid,
        setting_name="REMNAWAVE_SPB_DE_EXCEPTIONS_BRIDGE_SQUAD_UUID",
    )
    _reject_smart_ru_squad_reuse(
        external_squad_uuid=external_squad_uuid,
        internal_squad_uuids=internal_squad_uuids,
    )
    _reject_bridge_squad_reuse(
        bridge_squad_uuid=bridge_squad_uuid,
        external_squad_uuid=external_squad_uuid,
        internal_squad_uuids=internal_squad_uuids,
    )
    return SpbDeExceptionsRoutingBundle(
        external_squad_uuid=external_squad_uuid,
        internal_squad_uuids=internal_squad_uuids,
        bridge_squad_uuid=bridge_squad_uuid,
        profile_name=_required_text(
            settings.remnawave_spb_de_exceptions_profile_name,
            setting_name="REMNAWAVE_SPB_DE_EXCEPTIONS_PROFILE_NAME",
        ),
        policy_version=_required_text(
            settings.remnawave_spb_de_exceptions_policy_version,
            setting_name="REMNAWAVE_SPB_DE_EXCEPTIONS_POLICY_VERSION",
        ),
    )


def resolve_spb_de_exceptions_external_squad_uuid(plan_code: str | None) -> str | None:
    bundle = resolve_spb_de_exceptions_bundle(plan_code)
    return bundle.external_squad_uuid if bundle is not None else None


def resolve_spb_de_exceptions_internal_squad_uuids(plan_code: str | None) -> list[str]:
    bundle = resolve_spb_de_exceptions_bundle(plan_code)
    return list(bundle.internal_squad_uuids) if bundle is not None else []
