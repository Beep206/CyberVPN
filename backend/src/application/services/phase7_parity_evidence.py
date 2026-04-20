"""Phase 7 replay, parity, and external-evidence helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.application.services.phase7_reporting_marts import build_phase7_reporting_marts_pack

REPORT_VERSION = "phase7-parity-evidence-v1"

BLOCKING_MISMATCH_CODES = {
    "analytical_reference_red",
    "channel_parity_missing_official_reference",
    "channel_parity_missing_required_channel",
    "channel_parity_duplicate_observation",
    "channel_paid_order_count_mismatch",
    "channel_active_entitlement_count_mismatch",
    "channel_visible_order_ids_mismatch",
    "channel_service_state_status_mismatch",
    "channel_parity_additional_channel_coverage_insufficient",
    "partner_export_missing_partner_row",
    "partner_export_paid_conversion_count_mismatch",
    "partner_export_available_earnings_amount_mismatch",
    "partner_export_statement_liability_amount_mismatch",
    "partner_export_currency_codes_mismatch",
    "postback_missing_publication",
    "postback_delivery_status_mismatch",
}


@dataclass(frozen=True)
class Phase7EvidenceMismatch:
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


def build_phase7_parity_evidence_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    analytical_snapshot = dict(snapshot.get("analytical_snapshot") or {})
    channel_expectations = _sorted_rows(snapshot.get("channel_parity_expectations", []))
    channel_observations = _sorted_rows(snapshot.get("channel_parity_observations", []))
    partner_export_observations = _sorted_rows(snapshot.get("partner_export_observations", []))
    postback_delivery_observations = _sorted_rows(snapshot.get("postback_delivery_observations", []))

    analytical_report = build_phase7_reporting_marts_pack(analytical_snapshot)
    mismatches: list[Phase7EvidenceMismatch] = []

    analytical_status = str((analytical_report.get("reconciliation") or {}).get("status") or "unknown")
    if analytical_status == "red":
        mismatches.append(
            Phase7EvidenceMismatch(
                code="analytical_reference_red",
                severity="blocking",
                object_family="analytical_reference",
                source_reference=str(metadata.get("snapshot_id") or "phase7"),
                message="Phase 7 analytical reference pack is red and cannot support parity evidence sign-off.",
                details={"analytical_status": analytical_status},
            )
        )
    elif analytical_status == "yellow":
        mismatches.append(
            Phase7EvidenceMismatch(
                code="analytical_reference_not_green",
                severity="warning",
                object_family="analytical_reference",
                source_reference=str(metadata.get("snapshot_id") or "phase7"),
                message="Phase 7 analytical reference pack is not green and parity evidence must be read with caution.",
                details={"analytical_status": analytical_status},
            )
        )

    partner_rows_by_partner_id = {
        str(item["partner_account_id"]): item
        for item in analytical_report.get("partner_reporting_mart", [])
        if item.get("partner_account_id") is not None
    }
    outbox_publications = _sorted_rows(analytical_snapshot.get("outbox_publications", []))
    publications_by_event_consumer = {
        (str(item.get("outbox_event_id")), str(item.get("consumer_key"))): item
        for item in outbox_publications
        if item.get("outbox_event_id") and item.get("consumer_key")
    }

    channel_observations_by_parity: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for observation in channel_observations:
        parity_key = str(observation.get("parity_key") or "unknown")
        channel_key = str(observation.get("channel_key") or "unknown")
        if channel_key in channel_observations_by_parity[parity_key]:
            mismatches.append(
                Phase7EvidenceMismatch(
                    code="channel_parity_duplicate_observation",
                    severity="blocking",
                    object_family="channel_parity",
                    source_reference=f"{parity_key}:{channel_key}",
                    message="More than one channel observation was provided for the same parity key and channel.",
                    details={},
                )
            )
        channel_observations_by_parity[parity_key][channel_key] = observation

    distinct_additional_channels: set[str] = set()
    channel_parity_views = _build_channel_parity_views(
        channel_expectations=channel_expectations,
        observations_by_parity=channel_observations_by_parity,
        distinct_additional_channels=distinct_additional_channels,
        mismatches=mismatches,
    )
    if len(distinct_additional_channels) < 2:
        mismatches.append(
            Phase7EvidenceMismatch(
                code="channel_parity_additional_channel_coverage_insufficient",
                severity="blocking",
                object_family="channel_parity",
                source_reference="phase7-channel-coverage",
                message="Phase 7 evidence must cover official web and at least two additional channels.",
                details={
                    "additional_channels": sorted(distinct_additional_channels),
                    "additional_channel_count": len(distinct_additional_channels),
                },
            )
        )

    partner_export_views = _build_partner_export_views(
        observations=partner_export_observations,
        partner_rows_by_partner_id=partner_rows_by_partner_id,
        mismatches=mismatches,
    )
    postback_delivery_views = _build_postback_delivery_views(
        observations=postback_delivery_observations,
        publications_by_event_consumer=publications_by_event_consumer,
        mismatches=mismatches,
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
            "channel_parity_expectations": len(channel_expectations),
            "channel_parity_observations": len(channel_observations),
            "partner_export_observations": len(partner_export_observations),
            "postback_delivery_observations": len(postback_delivery_observations),
        },
        "analytical_reference": {
            "status": analytical_status,
            "partner_reporting_mart": analytical_report.get("partner_reporting_mart", []),
            "reporting_health_views": analytical_report.get("reporting_health_views", {}),
            "reconciliation": analytical_report.get("reconciliation", {}),
        },
        "channel_coverage": {
            "reference_channel": "official_web",
            "additional_channels": sorted(distinct_additional_channels),
            "additional_channel_count": len(distinct_additional_channels),
        },
        "channel_parity_views": channel_parity_views,
        "partner_export_views": partner_export_views,
        "postback_delivery_views": postback_delivery_views,
        "reconciliation": {
            "status": status,
            "mismatch_counts": mismatch_counts,
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
        },
    }


def _build_channel_parity_views(
    *,
    channel_expectations: list[dict[str, Any]],
    observations_by_parity: dict[str, dict[str, dict[str, Any]]],
    distinct_additional_channels: set[str],
    mismatches: list[Phase7EvidenceMismatch],
) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []

    for expectation in channel_expectations:
        parity_key = str(expectation.get("parity_key") or "unknown")
        reference_channel = str(expectation.get("reference_channel") or "official_web")
        required_channels = _sorted_strings(expectation.get("required_channels") or [reference_channel])
        expected_visible_order_ids = _sorted_strings(expectation.get("expected_visible_order_ids") or [])
        scoped_observations = observations_by_parity.get(parity_key, {})

        if reference_channel not in scoped_observations:
            mismatches.append(
                Phase7EvidenceMismatch(
                    code="channel_parity_missing_official_reference",
                    severity="blocking",
                    object_family="channel_parity",
                    source_reference=parity_key,
                    message="Channel parity evidence is missing the official-web reference observation.",
                    details={"reference_channel": reference_channel},
                )
            )

        channel_results: list[dict[str, Any]] = []
        view_mismatch_codes: set[str] = set()

        for channel_key in required_channels:
            observation = scoped_observations.get(channel_key)
            if observation is None:
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="channel_parity_missing_required_channel",
                        severity="blocking",
                        object_family="channel_parity",
                        source_reference=f"{parity_key}:{channel_key}",
                        message="Required parity channel observation is missing from the evidence snapshot.",
                        details={"required_channel": channel_key},
                    )
                )
                view_mismatch_codes.add("channel_parity_missing_required_channel")
                channel_results.append(
                    {
                        "channel_key": channel_key,
                        "status": "missing",
                        "mismatch_codes": ["channel_parity_missing_required_channel"],
                    }
                )
                continue

            if channel_key != reference_channel:
                distinct_additional_channels.add(channel_key)

            mismatch_codes: list[str] = []
            expected_paid_order_count = _int_or_none(expectation.get("expected_paid_order_count"))
            observed_paid_order_count = _int_or_none(observation.get("observed_paid_order_count")) or 0
            if expected_paid_order_count is not None and observed_paid_order_count != expected_paid_order_count:
                mismatch_codes.append("channel_paid_order_count_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="channel_paid_order_count_mismatch",
                        severity="blocking",
                        object_family="channel_parity",
                        source_reference=f"{parity_key}:{channel_key}",
                        message="Observed paid-order count does not match the expected canonical parity count.",
                        details={
                            "expected_paid_order_count": expected_paid_order_count,
                            "observed_paid_order_count": observed_paid_order_count,
                        },
                    )
                )

            expected_active_entitlement_count = _int_or_none(expectation.get("expected_active_entitlement_count"))
            observed_active_entitlement_count = _int_or_none(observation.get("observed_active_entitlement_count")) or 0
            if (
                expected_active_entitlement_count is not None
                and observed_active_entitlement_count != expected_active_entitlement_count
            ):
                mismatch_codes.append("channel_active_entitlement_count_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="channel_active_entitlement_count_mismatch",
                        severity="blocking",
                        object_family="channel_parity",
                        source_reference=f"{parity_key}:{channel_key}",
                        message="Observed active-entitlement count does not match the expected canonical parity count.",
                        details={
                            "expected_active_entitlement_count": expected_active_entitlement_count,
                            "observed_active_entitlement_count": observed_active_entitlement_count,
                        },
                    )
                )

            expected_service_state_status = _string_or_none(expectation.get("expected_service_state_status"))
            observed_service_state_status = _string_or_none(observation.get("observed_service_state_status"))
            if (
                expected_service_state_status is not None
                and observed_service_state_status != expected_service_state_status
            ):
                mismatch_codes.append("channel_service_state_status_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="channel_service_state_status_mismatch",
                        severity="blocking",
                        object_family="channel_parity",
                        source_reference=f"{parity_key}:{channel_key}",
                        message="Observed service-state status does not match the expected parity status.",
                        details={
                            "expected_service_state_status": expected_service_state_status,
                            "observed_service_state_status": observed_service_state_status,
                        },
                    )
                )

            observed_visible_order_ids = _sorted_strings(observation.get("observed_visible_order_ids") or [])
            if expected_visible_order_ids and observed_visible_order_ids != expected_visible_order_ids:
                mismatch_codes.append("channel_visible_order_ids_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="channel_visible_order_ids_mismatch",
                        severity="blocking",
                        object_family="channel_parity",
                        source_reference=f"{parity_key}:{channel_key}",
                        message="Observed visible order IDs do not match the expected canonical order set.",
                        details={
                            "expected_visible_order_ids": expected_visible_order_ids,
                            "observed_visible_order_ids": observed_visible_order_ids,
                        },
                    )
                )

            view_mismatch_codes.update(mismatch_codes)
            channel_results.append(
                {
                    "channel_key": channel_key,
                    "status": "matched" if not mismatch_codes else "mismatch",
                    "observed_paid_order_count": observed_paid_order_count,
                    "observed_active_entitlement_count": observed_active_entitlement_count,
                    "observed_service_state_status": observed_service_state_status,
                    "observed_visible_order_ids": observed_visible_order_ids,
                    "mismatch_codes": mismatch_codes,
                }
            )

        views.append(
            {
                "parity_key": parity_key,
                "reference_channel": reference_channel,
                "required_channels": required_channels,
                "observed_channels": sorted(scoped_observations),
                "status": "green" if not view_mismatch_codes else "red",
                "mismatch_codes": sorted(view_mismatch_codes),
                "channel_results": channel_results,
            }
        )

    return views


def _build_partner_export_views(
    *,
    observations: list[dict[str, Any]],
    partner_rows_by_partner_id: dict[str, dict[str, Any]],
    mismatches: list[Phase7EvidenceMismatch],
) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []

    for observation in observations:
        export_key = str(observation.get("export_key") or "unknown")
        partner_account_id = _string_or_none(observation.get("partner_account_id"))
        canonical_row = partner_rows_by_partner_id.get(partner_account_id or "")
        mismatch_codes: list[str] = []

        if canonical_row is None:
            mismatch_codes.append("partner_export_missing_partner_row")
            mismatches.append(
                Phase7EvidenceMismatch(
                    code="partner_export_missing_partner_row",
                    severity="blocking",
                    object_family="partner_export",
                    source_reference=export_key,
                    message="Partner export observation does not map to a canonical partner reporting mart row.",
                    details={"partner_account_id": partner_account_id},
                )
            )
        else:
            observed_paid_conversion_count = _int_or_none(observation.get("observed_paid_conversion_count")) or 0
            if observed_paid_conversion_count != int(canonical_row.get("paid_conversion_count", 0)):
                mismatch_codes.append("partner_export_paid_conversion_count_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="partner_export_paid_conversion_count_mismatch",
                        severity="blocking",
                        object_family="partner_export",
                        source_reference=export_key,
                        message="Partner export paid-conversion count differs from the canonical reporting mart.",
                        details={
                            "expected_paid_conversion_count": canonical_row.get("paid_conversion_count", 0),
                            "observed_paid_conversion_count": observed_paid_conversion_count,
                        },
                    )
                )

            observed_available_earnings_amount = _money(observation.get("observed_available_earnings_amount"))
            expected_available_earnings_amount = _money(canonical_row.get("available_earnings_amount"))
            if observed_available_earnings_amount != expected_available_earnings_amount:
                mismatch_codes.append("partner_export_available_earnings_amount_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="partner_export_available_earnings_amount_mismatch",
                        severity="blocking",
                        object_family="partner_export",
                        source_reference=export_key,
                        message="Partner export available-earnings amount differs from canonical partner reporting.",
                        details={
                            "expected_available_earnings_amount": expected_available_earnings_amount,
                            "observed_available_earnings_amount": observed_available_earnings_amount,
                        },
                    )
                )

            observed_statement_liability_amount = _money(observation.get("observed_statement_liability_amount"))
            expected_statement_liability_amount = _money(canonical_row.get("statement_liability_amount"))
            if observed_statement_liability_amount != expected_statement_liability_amount:
                mismatch_codes.append("partner_export_statement_liability_amount_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="partner_export_statement_liability_amount_mismatch",
                        severity="blocking",
                        object_family="partner_export",
                        source_reference=export_key,
                        message="Partner export statement liability differs from canonical partner reporting.",
                        details={
                            "expected_statement_liability_amount": expected_statement_liability_amount,
                            "observed_statement_liability_amount": observed_statement_liability_amount,
                        },
                    )
                )

            observed_currency_codes = _sorted_strings(observation.get("observed_currency_codes") or [])
            expected_currency_codes = _sorted_strings(canonical_row.get("currency_codes") or [])
            if observed_currency_codes != expected_currency_codes:
                mismatch_codes.append("partner_export_currency_codes_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="partner_export_currency_codes_mismatch",
                        severity="blocking",
                        object_family="partner_export",
                        source_reference=export_key,
                        message="Partner export currency coverage differs from canonical partner reporting.",
                        details={
                            "expected_currency_codes": expected_currency_codes,
                            "observed_currency_codes": observed_currency_codes,
                        },
                    )
                )

        views.append(
            {
                "export_key": export_key,
                "workspace_id": _string_or_none(observation.get("workspace_id")),
                "partner_account_id": partner_account_id,
                "export_status": _string_or_none(observation.get("export_status")),
                "mismatch_codes": mismatch_codes,
                "canonical_partner_reporting_row": canonical_row,
            }
        )

    return views


def _build_postback_delivery_views(
    *,
    observations: list[dict[str, Any]],
    publications_by_event_consumer: dict[tuple[str, str], dict[str, Any]],
    mismatches: list[Phase7EvidenceMismatch],
) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []

    for observation in observations:
        delivery_key = str(observation.get("delivery_key") or "unknown")
        outbox_event_id = _string_or_none(observation.get("outbox_event_id")) or "unknown"
        consumer_key = _string_or_none(observation.get("consumer_key")) or "postback"
        observed_delivery_status = _string_or_none(observation.get("observed_delivery_status")) or "unknown"
        publication = publications_by_event_consumer.get((outbox_event_id, consumer_key))
        mismatch_codes: list[str] = []

        if publication is None:
            mismatch_codes.append("postback_missing_publication")
            mismatches.append(
                Phase7EvidenceMismatch(
                    code="postback_missing_publication",
                    severity="blocking",
                    object_family="postback_delivery",
                    source_reference=delivery_key,
                    message="Postback evidence references an outbox event without a matching publication row.",
                    details={
                        "outbox_event_id": outbox_event_id,
                        "consumer_key": consumer_key,
                    },
                )
            )
            publication_status = None
        else:
            publication_status = _string_or_none(publication.get("publication_status"))
            expected_delivery_status = _map_publication_status_to_delivery_status(publication_status)
            if observed_delivery_status != expected_delivery_status:
                mismatch_codes.append("postback_delivery_status_mismatch")
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="postback_delivery_status_mismatch",
                        severity="blocking",
                        object_family="postback_delivery",
                        source_reference=delivery_key,
                        message="Observed postback delivery status does not match the canonical publication lifecycle.",
                        details={
                            "outbox_event_id": outbox_event_id,
                            "consumer_key": consumer_key,
                            "expected_delivery_status": expected_delivery_status,
                            "observed_delivery_status": observed_delivery_status,
                            "publication_status": publication_status,
                        },
                    )
                )

            if publication_status == "failed":
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="postback_publication_failed",
                        severity="warning",
                        object_family="postback_delivery",
                        source_reference=delivery_key,
                        message="Canonical postback publication is failed and requires replay or operator action.",
                        details={
                            "outbox_event_id": outbox_event_id,
                            "consumer_key": consumer_key,
                        },
                    )
                )
            elif publication_status in {"pending", "claimed", "submitted"}:
                mismatches.append(
                    Phase7EvidenceMismatch(
                        code="postback_publication_backlog_present",
                        severity="warning",
                        object_family="postback_delivery",
                        source_reference=delivery_key,
                        message="Canonical postback publication is not terminal and still sits in delivery backlog.",
                        details={
                            "outbox_event_id": outbox_event_id,
                            "consumer_key": consumer_key,
                            "publication_status": publication_status,
                        },
                    )
                )

        views.append(
            {
                "delivery_key": delivery_key,
                "workspace_id": _string_or_none(observation.get("workspace_id")),
                "partner_account_id": _string_or_none(observation.get("partner_account_id")),
                "outbox_event_id": outbox_event_id,
                "consumer_key": consumer_key,
                "observed_delivery_status": observed_delivery_status,
                "publication_status": publication_status,
                "mismatch_codes": mismatch_codes,
            }
        )

    return views


def _map_publication_status_to_delivery_status(publication_status: str | None) -> str:
    if publication_status == "published":
        return "delivered"
    if publication_status == "failed":
        return "failed"
    return "paused"


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(item) for item in rows],
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("updated_at") or ""),
            str(item.get("parity_key") or ""),
            str(item.get("channel_key") or ""),
            str(item.get("export_key") or ""),
            str(item.get("delivery_key") or ""),
            str(item.get("id") or ""),
        ),
    )


def _sorted_strings(values: list[Any]) -> list[str]:
    return sorted(str(value) for value in values)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _money(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(Decimal(str(value)).quantize(Decimal("0.01")))
