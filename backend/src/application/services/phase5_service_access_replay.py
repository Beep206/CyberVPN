"""Phase 5 service-access replay and channel-parity reconciliation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.application.use_cases.service_access.access_delivery_channels import (
    _default_channel_subject_ref,
    _default_provisioning_profile_key,
)

REPORT_VERSION = "phase5-service-access-replay-v1"

BLOCKING_MISMATCH_CODES = {
    "service_identity_duplicate_customer_realm_provider",
    "entitlement_grant_missing_service_identity",
    "provisioning_profile_missing_service_identity",
    "device_credential_missing_service_identity",
    "device_credential_missing_provisioning_profile",
    "access_delivery_channel_missing_service_identity",
    "access_delivery_channel_missing_provisioning_profile",
    "access_delivery_channel_missing_device_credential",
    "access_delivery_channel_realm_mismatch",
    "provider_name_mismatch",
    "multiple_active_entitlement_grants_for_scope",
}


@dataclass(frozen=True)
class ServiceAccessMismatch:
    code: str
    severity: str
    object_family: str
    source_reference: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "object_family": self.object_family,
            "source_reference": self.source_reference,
            "message": self.message,
            "details": self.details,
        }


def build_phase5_service_access_replay_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    service_identities = _sorted_rows(snapshot.get("service_identities", []))
    entitlement_grants = _sorted_rows(snapshot.get("entitlement_grants", []))
    provisioning_profiles = _sorted_rows(snapshot.get("provisioning_profiles", []))
    device_credentials = _sorted_rows(snapshot.get("device_credentials", []))
    access_delivery_channels = _sorted_rows(snapshot.get("access_delivery_channels", []))
    channel_expectations = _sorted_expectations(snapshot.get("channel_expectations", []))

    service_identity_by_id = _rows_by_id(service_identities)
    provisioning_profile_by_id = _rows_by_id(provisioning_profiles)
    device_credential_by_id = _rows_by_id(device_credentials)

    mismatches: list[ServiceAccessMismatch] = []
    scope_to_service_identities: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    scope_to_grants: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    grants_by_service_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    provisioning_profiles_by_service_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    device_credentials_by_service_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    access_delivery_channels_by_service_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for service_identity in service_identities:
        scope = _scope_key(service_identity)
        scope_to_service_identities[scope].append(service_identity)

    for scope, scoped_identities in scope_to_service_identities.items():
        if len(scoped_identities) > 1:
            mismatches.append(
                ServiceAccessMismatch(
                    code="service_identity_duplicate_customer_realm_provider",
                    severity="blocking",
                    object_family="service_identity",
                    source_reference="|".join(scope),
                    message=(
                        "Multiple canonical service identities exist for the same "
                        "customer-account, auth-realm, and provider scope."
                    ),
                    details={
                        "service_identity_ids": [str(item["id"]) for item in scoped_identities],
                    },
                )
            )

    for entitlement_grant in entitlement_grants:
        service_identity_id = _string_or_none(entitlement_grant.get("service_identity_id"))
        if service_identity_id is None or service_identity_id not in service_identity_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="entitlement_grant_missing_service_identity",
                    severity="blocking",
                    object_family="entitlement_grant",
                    source_reference=str(entitlement_grant.get("id", "unknown")),
                    message="Entitlement grant references a service identity that is missing from the snapshot.",
                    details={"service_identity_id": service_identity_id},
                )
            )
            continue
        grants_by_service_identity[service_identity_id].append(entitlement_grant)
        scope_to_grants[_scope_key(service_identity_by_id[service_identity_id])].append(entitlement_grant)
        service_identity_provider_name = service_identity_by_id[service_identity_id].get("provider_name")
        grant_provider_name = entitlement_grant.get("provider_name", service_identity_provider_name)
        if service_identity_provider_name != grant_provider_name:
            # Grant rows currently do not require provider_name, so only compare when present in fixture input.
            if entitlement_grant.get("provider_name") is not None:
                mismatches.append(
                    ServiceAccessMismatch(
                        code="provider_name_mismatch",
                        severity="blocking",
                        object_family="entitlement_grant",
                        source_reference=str(entitlement_grant.get("id", "unknown")),
                        message="Entitlement grant provider does not match the linked service identity provider.",
                        details={
                            "service_identity_id": service_identity_id,
                            "service_identity_provider_name": service_identity_provider_name,
                            "grant_provider_name": grant_provider_name,
                        },
                    )
                )

    for scope, scoped_grants in scope_to_grants.items():
        active_grants = [item for item in scoped_grants if str(item.get("grant_status")) == "active"]
        if len(active_grants) > 1:
            mismatches.append(
                ServiceAccessMismatch(
                    code="multiple_active_entitlement_grants_for_scope",
                    severity="blocking",
                    object_family="entitlement_grant",
                    source_reference="|".join(scope),
                    message=(
                        "More than one active entitlement grant exists for the same "
                        "customer-account, auth-realm, and provider scope."
                    ),
                    details={"entitlement_grant_ids": [str(item["id"]) for item in active_grants]},
                )
            )

    for provisioning_profile in provisioning_profiles:
        service_identity_id = _string_or_none(provisioning_profile.get("service_identity_id"))
        if service_identity_id is None or service_identity_id not in service_identity_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="provisioning_profile_missing_service_identity",
                    severity="blocking",
                    object_family="provisioning_profile",
                    source_reference=str(provisioning_profile.get("id", "unknown")),
                    message="Provisioning profile references a service identity that is missing from the snapshot.",
                    details={"service_identity_id": service_identity_id},
                )
            )
            continue
        provisioning_profiles_by_service_identity[service_identity_id].append(provisioning_profile)
        _append_provider_name_mismatch(
            mismatches=mismatches,
            object_family="provisioning_profile",
            row=provisioning_profile,
            service_identity=service_identity_by_id[service_identity_id],
        )

    for device_credential in device_credentials:
        service_identity_id = _string_or_none(device_credential.get("service_identity_id"))
        if service_identity_id is None or service_identity_id not in service_identity_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="device_credential_missing_service_identity",
                    severity="blocking",
                    object_family="device_credential",
                    source_reference=str(device_credential.get("id", "unknown")),
                    message="Device credential references a service identity that is missing from the snapshot.",
                    details={"service_identity_id": service_identity_id},
                )
            )
            continue
        provisioning_profile_id = _string_or_none(device_credential.get("provisioning_profile_id"))
        if provisioning_profile_id is not None and provisioning_profile_id not in provisioning_profile_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="device_credential_missing_provisioning_profile",
                    severity="blocking",
                    object_family="device_credential",
                    source_reference=str(device_credential.get("id", "unknown")),
                    message="Device credential references a provisioning profile that is missing from the snapshot.",
                    details={"provisioning_profile_id": provisioning_profile_id},
                )
            )
        device_credentials_by_service_identity[service_identity_id].append(device_credential)
        _append_provider_name_mismatch(
            mismatches=mismatches,
            object_family="device_credential",
            row=device_credential,
            service_identity=service_identity_by_id[service_identity_id],
        )

    for access_delivery_channel in access_delivery_channels:
        service_identity_id = _string_or_none(access_delivery_channel.get("service_identity_id"))
        if service_identity_id is None or service_identity_id not in service_identity_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="access_delivery_channel_missing_service_identity",
                    severity="blocking",
                    object_family="access_delivery_channel",
                    source_reference=str(access_delivery_channel.get("id", "unknown")),
                    message="Access delivery channel references a service identity that is missing from the snapshot.",
                    details={"service_identity_id": service_identity_id},
                )
            )
            continue
        service_identity = service_identity_by_id[service_identity_id]
        provisioning_profile_id = _string_or_none(access_delivery_channel.get("provisioning_profile_id"))
        if provisioning_profile_id is not None and provisioning_profile_id not in provisioning_profile_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="access_delivery_channel_missing_provisioning_profile",
                    severity="blocking",
                    object_family="access_delivery_channel",
                    source_reference=str(access_delivery_channel.get("id", "unknown")),
                    message=(
                        "Access delivery channel references a provisioning profile "
                        "that is missing from the snapshot."
                    ),
                    details={"provisioning_profile_id": provisioning_profile_id},
                )
            )
        device_credential_id = _string_or_none(access_delivery_channel.get("device_credential_id"))
        if device_credential_id is not None and device_credential_id not in device_credential_by_id:
            mismatches.append(
                ServiceAccessMismatch(
                    code="access_delivery_channel_missing_device_credential",
                    severity="blocking",
                    object_family="access_delivery_channel",
                    source_reference=str(access_delivery_channel.get("id", "unknown")),
                    message="Access delivery channel references a device credential that is missing from the snapshot.",
                    details={"device_credential_id": device_credential_id},
                )
            )
        if str(access_delivery_channel.get("auth_realm_id")) != str(service_identity.get("auth_realm_id")):
            mismatches.append(
                ServiceAccessMismatch(
                    code="access_delivery_channel_realm_mismatch",
                    severity="blocking",
                    object_family="access_delivery_channel",
                    source_reference=str(access_delivery_channel.get("id", "unknown")),
                    message="Access delivery channel auth realm does not match the linked service identity auth realm.",
                    details={
                        "channel_auth_realm_id": access_delivery_channel.get("auth_realm_id"),
                        "service_identity_auth_realm_id": service_identity.get("auth_realm_id"),
                    },
                )
            )
        access_delivery_channels_by_service_identity[service_identity_id].append(access_delivery_channel)
        _append_provider_name_mismatch(
            mismatches=mismatches,
            object_family="access_delivery_channel",
            row=access_delivery_channel,
            service_identity=service_identity,
        )

    service_identity_views = [
        _build_service_identity_view(
            service_identity=service_identity,
            scope_to_service_identities=scope_to_service_identities,
            grants_by_service_identity=grants_by_service_identity,
            provisioning_profiles_by_service_identity=provisioning_profiles_by_service_identity,
            device_credentials_by_service_identity=device_credentials_by_service_identity,
            access_delivery_channels_by_service_identity=access_delivery_channels_by_service_identity,
        )
        for service_identity in service_identities
    ]

    channel_parity_views = [
        _build_channel_parity_view(
            expectation=expectation,
            scope_to_service_identities=scope_to_service_identities,
            scope_to_grants=scope_to_grants,
            provisioning_profiles_by_service_identity=provisioning_profiles_by_service_identity,
            device_credentials_by_service_identity=device_credentials_by_service_identity,
            access_delivery_channels_by_service_identity=access_delivery_channels_by_service_identity,
        )
        for expectation in channel_expectations
    ]

    for view in channel_parity_views:
        for mismatch_code in view["mismatch_codes"]:
            mismatches.append(
                ServiceAccessMismatch(
                    code=mismatch_code,
                    severity="warning",
                    object_family="channel_parity",
                    source_reference=view["parity_key"],
                    message=_parity_mismatch_message(mismatch_code),
                    details={
                        "channel_type": view["channel_type"],
                        "resolved_provisioning_profile_key": view["resolved_provisioning_profile_key"],
                        "resolved_channel_subject_ref": view["resolved_channel_subject_ref"],
                    },
                )
            )

    mismatch_counts = dict(Counter(item.code for item in mismatches))
    blocking_mismatches = [item.to_dict() for item in mismatches if item.code in BLOCKING_MISMATCH_CODES]
    status = "green"
    if blocking_mismatches:
        status = "red"
    elif mismatches:
        status = "yellow"

    return {
        "metadata": {
            "report_version": REPORT_VERSION,
            "generated_at": metadata.get("replay_generated_at") or datetime.now(UTC).isoformat(),
            "snapshot_id": metadata.get("snapshot_id"),
            "source": metadata.get("source"),
        },
        "input_summary": {
            "service_identities": len(service_identities),
            "entitlement_grants": len(entitlement_grants),
            "provisioning_profiles": len(provisioning_profiles),
            "device_credentials": len(device_credentials),
            "access_delivery_channels": len(access_delivery_channels),
            "channel_expectations": len(channel_expectations),
        },
        "service_identity_views": service_identity_views,
        "channel_parity_views": channel_parity_views,
        "reconciliation": {
            "status": status,
            "mismatch_counts": mismatch_counts,
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
        },
    }


def _build_service_identity_view(
    *,
    service_identity: dict[str, Any],
    scope_to_service_identities: dict[tuple[str, str, str], list[dict[str, Any]]],
    grants_by_service_identity: dict[str, list[dict[str, Any]]],
    provisioning_profiles_by_service_identity: dict[str, list[dict[str, Any]]],
    device_credentials_by_service_identity: dict[str, list[dict[str, Any]]],
    access_delivery_channels_by_service_identity: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    service_identity_id = str(service_identity["id"])
    scope = _scope_key(service_identity)
    grants = grants_by_service_identity.get(service_identity_id, [])
    provisioning_profiles = provisioning_profiles_by_service_identity.get(service_identity_id, [])
    device_credentials = device_credentials_by_service_identity.get(service_identity_id, [])
    access_delivery_channels = access_delivery_channels_by_service_identity.get(service_identity_id, [])
    active_grants = [item for item in grants if str(item.get("grant_status")) == "active"]
    active_entitlement_grant = _first_row(active_grants)
    active_entitlement_status = None
    active_plan_code = None
    if active_entitlement_grant is not None:
        grant_snapshot = dict(active_entitlement_grant.get("grant_snapshot") or {})
        active_entitlement_status = grant_snapshot.get("status")
        active_plan_code = grant_snapshot.get("plan_code")

    return {
        "service_identity_id": service_identity_id,
        "service_key": service_identity.get("service_key"),
        "customer_account_id": service_identity.get("customer_account_id"),
        "auth_realm_id": service_identity.get("auth_realm_id"),
        "provider_name": service_identity.get("provider_name"),
        "provider_subject_ref": service_identity.get("provider_subject_ref"),
        "duplicate_scope_count": len(scope_to_service_identities.get(scope, [])),
        "active_entitlement_grant_id": (
            str(active_entitlement_grant["id"]) if active_entitlement_grant is not None else None
        ),
        "active_entitlement_status": active_entitlement_status,
        "active_plan_code": active_plan_code,
        "entitlement_counts": dict(Counter(str(item.get("grant_status")) for item in grants)),
        "provisioning_profile_keys": [str(item.get("profile_key")) for item in provisioning_profiles],
        "device_credentials": [
            {
                "credential_key": item.get("credential_key"),
                "credential_type": item.get("credential_type"),
                "subject_key": item.get("subject_key"),
                "credential_status": item.get("credential_status"),
            }
            for item in device_credentials
        ],
        "access_delivery_channels": [
            {
                "delivery_key": item.get("delivery_key"),
                "channel_type": item.get("channel_type"),
                "channel_subject_ref": item.get("channel_subject_ref"),
                "channel_status": item.get("channel_status"),
            }
            for item in access_delivery_channels
        ],
        "bridge_provenance": {
            "legacy_provider_subject_present": bool(service_identity.get("provider_subject_ref")),
            "legacy_subscription_url_present": _has_legacy_subscription_bridge(
                service_identity=service_identity,
                access_delivery_channels=access_delivery_channels,
            ),
        },
    }


def _build_channel_parity_view(
    *,
    expectation: dict[str, Any],
    scope_to_service_identities: dict[tuple[str, str, str], list[dict[str, Any]]],
    scope_to_grants: dict[tuple[str, str, str], list[dict[str, Any]]],
    provisioning_profiles_by_service_identity: dict[str, list[dict[str, Any]]],
    device_credentials_by_service_identity: dict[str, list[dict[str, Any]]],
    access_delivery_channels_by_service_identity: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    customer_account_id = _string_or_none(expectation.get("customer_account_id")) or ""
    auth_realm_id = _string_or_none(expectation.get("auth_realm_id")) or ""
    provider_name = str(expectation.get("provider_name") or "")
    channel_type = str(expectation.get("channel_type") or "")
    credential_type = _string_or_none(expectation.get("credential_type"))
    credential_subject_key = _string_or_none(expectation.get("credential_subject_key"))
    scope = (customer_account_id, auth_realm_id, provider_name)
    service_identity = _first_row(scope_to_service_identities.get(scope, []))
    scoped_grants = scope_to_grants.get(scope, [])
    active_grant = _first_row([item for item in scoped_grants if str(item.get("grant_status")) == "active"])

    resolved_provisioning_profile_key = _string_or_none(expectation.get("provisioning_profile_key")) or (
        _default_provisioning_profile_key(channel_type) if channel_type else None
    )
    resolved_channel_subject_ref = _string_or_none(expectation.get("channel_subject_ref"))
    if resolved_channel_subject_ref is None and credential_subject_key is not None:
        resolved_channel_subject_ref = credential_subject_key
    elif resolved_channel_subject_ref is None and service_identity is not None and channel_type:
        resolved_channel_subject_ref = _default_channel_subject_ref(
            channel_type=channel_type,
            provided_subject_ref=None,
            credential_subject_key=None,
            service_identity_key=str(service_identity.get("service_key") or ""),
        )

    selected_provisioning_profile = None
    selected_device_credential = None
    selected_access_delivery_channel = None
    if service_identity is not None:
        service_identity_id = str(service_identity["id"])
        selected_provisioning_profile = _first_row(
            [
                item
                for item in provisioning_profiles_by_service_identity.get(service_identity_id, [])
                if str(item.get("profile_key")) == resolved_provisioning_profile_key
            ]
        )
        if credential_type is not None and credential_subject_key is not None:
            selected_device_credential = _first_row(
                [
                    item
                    for item in device_credentials_by_service_identity.get(service_identity_id, [])
                    if str(item.get("credential_type")) == credential_type
                    and str(item.get("subject_key")) == credential_subject_key
                ]
            )
        if resolved_channel_subject_ref is not None:
            selected_access_delivery_channel = _first_row(
                [
                    item
                    for item in access_delivery_channels_by_service_identity.get(service_identity_id, [])
                    if str(item.get("channel_type")) == channel_type
                    and str(item.get("channel_subject_ref")) == resolved_channel_subject_ref
                ]
            )

    mismatch_codes: list[str] = []
    if expectation.get("requires_service_identity", True) and service_identity is None:
        mismatch_codes.append("parity_missing_service_identity")
    expected_entitlement_status = _string_or_none(expectation.get("expected_entitlement_status"))
    if expected_entitlement_status is not None:
        if active_grant is None:
            mismatch_codes.append("parity_missing_active_entitlement_grant")
        else:
            grant_status = _string_or_none((active_grant.get("grant_snapshot") or {}).get("status"))
            if grant_status != expected_entitlement_status:
                mismatch_codes.append("parity_entitlement_status_mismatch")
    if expectation.get("requires_provisioning_profile", False) and selected_provisioning_profile is None:
        mismatch_codes.append("parity_missing_provisioning_profile")
    if expectation.get("requires_device_credential", False) and selected_device_credential is None:
        mismatch_codes.append("parity_missing_device_credential")
    if expectation.get("requires_access_delivery_channel", False) and selected_access_delivery_channel is None:
        mismatch_codes.append("parity_missing_access_delivery_channel")
    elif selected_access_delivery_channel is not None:
        expected_channel_status = _string_or_none(expectation.get("expected_channel_status"))
        actual_channel_status = str(selected_access_delivery_channel.get("channel_status"))
        if expected_channel_status is not None and actual_channel_status != expected_channel_status:
            mismatch_codes.append("parity_channel_status_mismatch")
        expected_payload_keys = _string_list(expectation.get("expected_delivery_payload_keys"))
        delivery_payload = dict(selected_access_delivery_channel.get("delivery_payload") or {})
        for payload_key in expected_payload_keys:
            if payload_key not in delivery_payload:
                mismatch_codes.append("parity_delivery_payload_key_missing")

    return {
        "parity_key": str(expectation.get("parity_key") or _default_parity_key(expectation)),
        "customer_account_id": customer_account_id,
        "auth_realm_id": auth_realm_id,
        "provider_name": provider_name,
        "channel_type": channel_type,
        "credential_type": credential_type,
        "credential_subject_key": credential_subject_key,
        "resolved_provisioning_profile_key": resolved_provisioning_profile_key,
        "resolved_channel_subject_ref": resolved_channel_subject_ref,
        "service_identity_id": str(service_identity["id"]) if service_identity is not None else None,
        "active_entitlement_grant_id": str(active_grant["id"]) if active_grant is not None else None,
        "selected_provisioning_profile_id": (
            str(selected_provisioning_profile["id"]) if selected_provisioning_profile is not None else None
        ),
        "selected_device_credential_id": (
            str(selected_device_credential["id"]) if selected_device_credential is not None else None
        ),
        "selected_access_delivery_channel_id": (
            str(selected_access_delivery_channel["id"]) if selected_access_delivery_channel is not None else None
        ),
        "mismatch_codes": mismatch_codes,
    }


def _append_provider_name_mismatch(
    *,
    mismatches: list[ServiceAccessMismatch],
    object_family: str,
    row: dict[str, Any],
    service_identity: dict[str, Any],
) -> None:
    if str(row.get("provider_name")) == str(service_identity.get("provider_name")):
        return
    mismatches.append(
        ServiceAccessMismatch(
            code="provider_name_mismatch",
            severity="blocking",
            object_family=object_family,
            source_reference=str(row.get("id", "unknown")),
            message=f"{object_family} provider does not match the linked service identity provider.",
            details={
                "row_provider_name": row.get("provider_name"),
                "service_identity_provider_name": service_identity.get("provider_name"),
                "service_identity_id": service_identity.get("id"),
            },
        )
    )


def _parity_mismatch_message(code: str) -> str:
    messages = {
        "parity_missing_service_identity": (
            "Channel parity expectation could not resolve a canonical service identity."
        ),
        "parity_missing_active_entitlement_grant": (
            "Channel parity expectation could not resolve an active entitlement grant."
        ),
        "parity_entitlement_status_mismatch": (
            "Resolved active entitlement status does not match the expected status."
        ),
        "parity_missing_provisioning_profile": (
            "Channel parity expectation could not resolve the expected provisioning profile."
        ),
        "parity_missing_device_credential": (
            "Channel parity expectation could not resolve the expected device credential."
        ),
        "parity_missing_access_delivery_channel": (
            "Channel parity expectation could not resolve the expected access delivery channel."
        ),
        "parity_channel_status_mismatch": (
            "Resolved access delivery channel status does not match the expected status."
        ),
        "parity_delivery_payload_key_missing": (
            "Resolved access delivery channel payload is missing a required key."
        ),
    }
    return messages.get(code, "Unknown channel parity mismatch.")


def _has_legacy_subscription_bridge(
    *,
    service_identity: dict[str, Any],
    access_delivery_channels: list[dict[str, Any]],
) -> bool:
    service_context = dict(service_identity.get("service_context") or {})
    if bool(service_context.get("legacy_subscription_url")):
        return True
    if bool(service_context.get("legacy_subscription_url_present")):
        return True
    for channel in access_delivery_channels:
        delivery_payload = dict(channel.get("delivery_payload") or {})
        if bool(delivery_payload.get("legacy_subscription_url")):
            return True
    return False


def _scope_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("customer_account_id") or ""),
        str(row.get("auth_realm_id") or ""),
        str(row.get("provider_name") or ""),
    )


def _default_parity_key(expectation: dict[str, Any]) -> str:
    return (
        f"{expectation.get('provider_name', 'unknown')}:"
        f"{expectation.get('channel_type', 'channel')}:"
        f"{expectation.get('customer_account_id', 'customer')}"
    )


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row["id"]): row
        for row in rows
        if row.get("id") is not None
    }


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            str(row.get("id") or ""),
            str(row.get("service_identity_id") or ""),
            str(row.get("customer_account_id") or ""),
            str(row.get("auth_realm_id") or ""),
            str(row.get("provider_name") or ""),
        ),
    )


def _sorted_expectations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            str(row.get("parity_key") or ""),
            str(row.get("customer_account_id") or ""),
            str(row.get("auth_realm_id") or ""),
            str(row.get("provider_name") or ""),
            str(row.get("channel_type") or ""),
        ),
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value]


def _first_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(rows, key=lambda row: str(row.get("id") or ""))[0]
