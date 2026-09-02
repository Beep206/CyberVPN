"""Minimal CyberVPN backend client for internal reconciliation hooks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class BackendAPIError(Exception):
    """Raised when the internal backend reconciliation API fails."""

    pass


class BackendAPIStreamTransientError(BackendAPIError):
    """Stream ingestion failed before a durable commit and is retryable."""


class BackendAPIStreamPermanentError(BackendAPIError):
    """Stream ingestion rejected a payload or idempotency key permanently."""


class BackendAPIRemnawaveMaintenanceTransientError(BackendAPIError):
    """A Remnawave retention or DLQ write can be retried safely."""


class BackendAPIRemnawaveMaintenancePermanentError(BackendAPIError):
    """A Remnawave retention or DLQ request violated the internal contract."""


class BackendAPIAutoRenewTransientError(BackendAPIError):
    """Auto-renew invoice creation may be retried with the same key."""


class BackendAPIAutoRenewPermanentError(BackendAPIError):
    """Auto-renew invoice creation was rejected permanently for this expiry."""


@dataclass(frozen=True, slots=True)
class BackendAutoRenewInvoice:
    payment_id: str
    reused: bool
    notification_status: str


@dataclass(frozen=True, slots=True)
class BackendRemnawaveRetentionResult:
    deleted_by_table: dict[str, int]
    total_deleted: int
    has_more: bool
    purged_at: datetime


@dataclass(frozen=True, slots=True)
class BackendRemnawaveStreamObservation:
    loss_detected: bool
    loss_reason: str | None
    gap_id: UUID | None
    reconciliation_status: str | None


@dataclass(frozen=True, slots=True)
class BackendRemnawaveStreamGap:
    gap_id: UUID
    stream_name: str
    reconciliation_status: str


_REMNAWAVE_RETENTION_TABLES = frozenset(
    {
        "remnawave_stream_receipts",
        "remnawave_stream_dead_letters",
        "remnawave_user_usage_hourly",
        "remnawave_subscription_request_events",
        "remnawave_node_user_presence",
        "remnawave_node_connections_hourly",
    }
)


def canonical_auto_renew_expiry(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("expected_expire_at must include a timezone")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def auto_renew_idempotency_key(remnawave_user_id: int, expected_expire_at: datetime) -> str:
    if isinstance(remnawave_user_id, bool) or not isinstance(remnawave_user_id, int) or remnawave_user_id <= 0:
        raise ValueError("remnawave_user_id must be a positive integer")
    canonical_expiry = canonical_auto_renew_expiry(expected_expire_at)
    expiry_digest = hashlib.sha256(canonical_expiry.encode("utf-8")).hexdigest()
    return f"remnawave:auto-renew:{remnawave_user_id}:{expiry_digest}"


class BackendAPIClient:
    """Async client for internal backend endpoints used by the task worker."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._backend_internal_enabled = bool(
            self._settings.backend_api_url
            and self._settings.backend_internal_secret is not None
            and self._settings.backend_internal_secret.get_secret_value().strip()
        )
        self._telegram_bot_internal_enabled = bool(
            self._settings.backend_api_url
            and self._settings.telegram_bot_internal_secret is not None
            and self._settings.telegram_bot_internal_secret.get_secret_value().strip()
        )
        self._payment_settlement_enabled = bool(
            self._settings.backend_api_url
            and self._settings.payment_settlement_worker_secret is not None
            and self._settings.payment_settlement_worker_secret.get_secret_value().strip()
        )
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._backend_internal_enabled or self._telegram_bot_internal_enabled

    @property
    def backend_internal_enabled(self) -> bool:
        return self._backend_internal_enabled

    @property
    def telegram_bot_internal_enabled(self) -> bool:
        return self._telegram_bot_internal_enabled

    @property
    def payment_settlement_enabled(self) -> bool:
        return self._payment_settlement_enabled

    async def __aenter__(self) -> BackendAPIClient:
        if not self.enabled and not self._payment_settlement_enabled:
            return self

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CyberVPN-TaskWorker/1.0",
        }

        self._client = httpx.AsyncClient(
            base_url=str(self._settings.backend_api_url).rstrip("/"),
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0),
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client is not None:
            await self._client.aclose()

    def _telegram_bot_secret_headers(self) -> dict[str, str]:
        secret = self._settings.telegram_bot_internal_secret
        value = secret.get_secret_value().strip() if secret is not None else ""
        return {"X-Telegram-Bot-Secret": value}

    def _backend_internal_secret_headers(self) -> dict[str, str]:
        secret = self._settings.backend_internal_secret
        value = secret.get_secret_value().strip() if secret is not None else ""
        return {"X-Backend-Internal-Secret": value}

    def _require_backend_internal_enabled(self, operation: str) -> None:
        if not self._backend_internal_enabled:
            raise BackendAPIError(f"{operation} API is not configured")

    def _require_telegram_bot_internal_enabled(self, operation: str) -> None:
        if not self._telegram_bot_internal_enabled:
            raise BackendAPIError(f"{operation} API is not configured")

    async def resolve_remnawave_user_id(self, customer_id: str) -> int:
        """Resolve a CyberVPN customer to the authoritative numeric provider ID.

        The backend owns the identity mapping and reconciliation state. This
        client intentionally has no UUID fallback because Remnawave removed
        user UUIDs in 3.0.
        """
        self._require_backend_internal_enabled("Internal Remnawave identity resolver")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        try:
            normalized_customer_id = str(UUID(customer_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise BackendAPIError("Customer ID must be a UUID") from exc

        response = await self._client.get(
            f"internal/remnawave/users/by-customer/{normalized_customer_id}",
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code == 409:
            raise BackendAPIError("Remnawave identity mapping is not reconciled")
        if response.status_code >= 400:
            logger.error(
                "backend_remnawave_identity_resolution_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Remnawave identity resolution failed: {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIError("Remnawave identity resolver returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise BackendAPIError("Remnawave identity resolver returned an invalid payload")

        response_customer_id = payload.get("customer_id")
        try:
            response_customer_uuid = UUID(str(response_customer_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise BackendAPIError("Remnawave identity resolver returned an invalid customer ID") from exc
        if str(response_customer_uuid) != normalized_customer_id:
            raise BackendAPIError("Remnawave identity resolver returned a mismatched customer ID")

        reconciliation_state = payload.get("reconciliation_state")
        if reconciliation_state != "mapped":
            raise BackendAPIError("Remnawave identity resolver returned an incomplete reconciliation state")

        remnawave_user_id = payload.get("remnawave_user_id")
        if isinstance(remnawave_user_id, bool) or not isinstance(remnawave_user_id, int) or remnawave_user_id <= 0:
            raise BackendAPIError("Remnawave identity resolver returned an invalid numeric user ID")
        return remnawave_user_id

    async def persist_remnawave_stream_event(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> None:
        """Commit one normalized stream event through the backend boundary."""
        self._require_backend_internal_enabled("Internal Remnawave stream ingestion")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        try:
            response = await self._client.post(
                "internal/remnawave/streams/events",
                json=payload,
                headers={
                    **self._backend_internal_secret_headers(),
                    "Idempotency-Key": idempotency_key,
                },
            )
        except httpx.HTTPError as exc:
            raise BackendAPIStreamTransientError("Remnawave stream ingestion transport failed") from exc

        if response.status_code == 204:
            return

        logger.error(
            "backend_remnawave_stream_ingestion_failed",
            status_code=response.status_code,
        )
        if response.status_code in {408, 425, 429, 503} or response.status_code >= 500:
            raise BackendAPIStreamTransientError(
                f"Remnawave stream ingestion transient failure: {response.status_code}"
            )
        raise BackendAPIStreamPermanentError(f"Remnawave stream ingestion permanent failure: {response.status_code}")

    async def persist_remnawave_dead_letter(self, payload: dict[str, Any]) -> None:
        """Commit redacted DLQ metadata before the Redis entry may be acknowledged."""
        self._require_backend_internal_enabled("Internal Remnawave dead-letter persistence")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        try:
            response = await self._client.post(
                "internal/remnawave/dead-letters",
                json=payload,
                headers=self._backend_internal_secret_headers(),
            )
        except httpx.HTTPError as exc:
            raise BackendAPIRemnawaveMaintenanceTransientError(
                "Remnawave dead-letter persistence transport failed"
            ) from exc
        if response.status_code == 204:
            return

        logger.error(
            "backend_remnawave_dead_letter_persistence_failed",
            status_code=response.status_code,
        )
        if response.status_code in {408, 425, 429, 502, 503, 504} or response.status_code >= 500:
            raise BackendAPIRemnawaveMaintenanceTransientError(
                f"Remnawave dead-letter persistence transient failure: {response.status_code}"
            )
        raise BackendAPIRemnawaveMaintenancePermanentError(
            f"Remnawave dead-letter persistence permanent failure: {response.status_code}"
        )

    async def create_remnawave_stream_gap(
        self,
        *,
        stream_name: str,
        missing_message_ids: tuple[str, ...],
        detected_at: datetime,
    ) -> BackendRemnawaveStreamGap:
        """Persist exact XAUTOCLAIM-deleted IDs before processing continues."""
        self._require_backend_internal_enabled("Internal Remnawave stream-gap persistence")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")
        if stream_name not in {"user_usage", "subscription_requests", "node_connections"}:
            raise ValueError("unsupported Remnawave stream name")
        if not 1 <= len(missing_message_ids) <= 1_000 or len(set(missing_message_ids)) != len(missing_message_ids):
            raise ValueError("missing_message_ids must contain 1..1000 unique IDs")
        if any(len(value) > 64 or re.fullmatch(r"[0-9]+-[0-9]+", value) is None for value in missing_message_ids):
            raise ValueError("missing_message_ids contains an invalid Redis stream ID")
        if detected_at.tzinfo is None or detected_at.utcoffset() is None:
            raise ValueError("detected_at must include a timezone")
        request_payload = {
            "stream_name": stream_name,
            "missing_message_ids": list(missing_message_ids),
            "detected_at": detected_at.astimezone(UTC).isoformat(),
        }
        try:
            response = await self._client.post(
                "internal/remnawave/stream-gaps",
                json=request_payload,
                headers=self._backend_internal_secret_headers(),
            )
        except httpx.HTTPError as exc:
            raise BackendAPIRemnawaveMaintenanceTransientError(
                "Remnawave stream-gap persistence transport failed"
            ) from exc
        if response.status_code != 201:
            self._raise_remnawave_maintenance_status("stream-gap persistence", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream-gap persistence returned invalid JSON"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("stream_name") != stream_name
            or payload.get("loss_kind") != "exact_ids"
            or payload.get("missing_message_ids") != list(missing_message_ids)
            or payload.get("missing_count") != len(missing_message_ids)
        ):
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream-gap persistence returned a mismatched receipt"
            )
        try:
            gap_id = UUID(str(payload.get("gap_id")))
        except (TypeError, ValueError, AttributeError) as exc:
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream-gap persistence returned an invalid gap ID"
            ) from exc
        reconciliation_status = payload.get("reconciliation_status")
        if reconciliation_status not in {
            "pending",
            "running",
            "reconciled",
            "partial",
        }:
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream-gap persistence returned an invalid reconciliation status"
            )
        return BackendRemnawaveStreamGap(
            gap_id=gap_id,
            stream_name=stream_name,
            reconciliation_status=reconciliation_status,
        )

    async def reconcile_remnawave_stream_gap(
        self,
        *,
        gap_id: UUID,
        stream_name: str,
    ) -> BackendRemnawaveStreamGap:
        """Run the backend-owned bounded REST reconciliation before loss is released."""
        self._require_backend_internal_enabled("Internal Remnawave stream-gap reconciliation")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")
        if stream_name not in {"user_usage", "subscription_requests", "node_connections"}:
            raise ValueError("unsupported Remnawave stream name")
        try:
            response = await self._client.post(
                f"internal/remnawave/stream-gaps/{gap_id}/reconcile",
                headers=self._backend_internal_secret_headers(),
            )
        except httpx.HTTPError as exc:
            raise BackendAPIRemnawaveMaintenanceTransientError(
                "Remnawave stream-gap reconciliation transport failed"
            ) from exc
        if response.status_code != 200:
            self._raise_remnawave_maintenance_status(
                "stream-gap reconciliation",
                response.status_code,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream-gap reconciliation returned invalid JSON"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("gap_id") != str(gap_id)
            or payload.get("stream_name") != stream_name
            or payload.get("reconciliation_status") not in {"reconciled", "partial"}
        ):
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream-gap reconciliation returned a non-terminal receipt"
            )
        return BackendRemnawaveStreamGap(
            gap_id=gap_id,
            stream_name=stream_name,
            reconciliation_status=str(payload["reconciliation_status"]),
        )

    async def observe_remnawave_stream_checkpoint(
        self,
        *,
        stream_name: str,
        observed_stream_identity: str,
        stream_exists: bool,
        group_exists: bool,
        first_message_id: str | None,
        last_message_id: str | None,
        group_last_delivered_id: str | None,
        group_pending_count: int,
        group_pending_min_id: str | None,
        group_pending_max_id: str | None,
        observed_at: datetime,
        group_lag: int | None = None,
    ) -> BackendRemnawaveStreamObservation:
        """Commit live Valkey epoch/range/group state before MKSTREAM repair."""
        self._require_backend_internal_enabled("Internal Remnawave stream checkpoint")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")
        request_payload = {
            "observed_stream_identity": observed_stream_identity,
            "stream_exists": stream_exists,
            "group_exists": group_exists,
            "first_message_id": first_message_id,
            "last_message_id": last_message_id,
            "group_last_delivered_id": group_last_delivered_id,
            "group_pending_count": group_pending_count,
            "group_pending_min_id": group_pending_min_id,
            "group_pending_max_id": group_pending_max_id,
            "group_lag": group_lag,
            "observed_at": observed_at.astimezone(UTC).isoformat(),
        }
        try:
            response = await self._client.post(
                f"internal/remnawave/stream-checkpoints/{stream_name}/observe",
                json=request_payload,
                headers=self._backend_internal_secret_headers(),
            )
        except httpx.HTTPError as exc:
            raise BackendAPIRemnawaveMaintenanceTransientError("Remnawave stream checkpoint transport failed") from exc
        if response.status_code != 200:
            self._raise_remnawave_maintenance_status("stream checkpoint", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream checkpoint returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict) or payload.get("stream_name") != stream_name:
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream checkpoint returned a mismatched receipt"
            )
        loss_detected = payload.get("loss_detected")
        if not isinstance(loss_detected, bool):
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream checkpoint returned an invalid loss decision"
            )
        gap = payload.get("gap")
        gap_id: UUID | None = None
        reconciliation_status: str | None = None
        if loss_detected:
            if not isinstance(gap, dict) or gap.get("loss_kind") != "unknown_range":
                raise BackendAPIRemnawaveMaintenancePermanentError(
                    "Remnawave stream checkpoint omitted durable loss-gap evidence"
                )
            reconciliation_status = gap.get("reconciliation_status")
            if reconciliation_status not in {"pending", "running", "reconciled", "partial", "failed"}:
                raise BackendAPIRemnawaveMaintenancePermanentError(
                    "Remnawave stream checkpoint returned an invalid reconciliation status"
                )
            try:
                gap_id = UUID(str(gap.get("gap_id")))
            except (TypeError, ValueError, AttributeError) as exc:
                raise BackendAPIRemnawaveMaintenancePermanentError(
                    "Remnawave stream checkpoint returned an invalid gap ID"
                ) from exc
        loss_reason = payload.get("loss_reason")
        if loss_reason is not None and not isinstance(loss_reason, str):
            raise BackendAPIRemnawaveMaintenancePermanentError(
                "Remnawave stream checkpoint returned an invalid loss reason"
            )
        return BackendRemnawaveStreamObservation(
            loss_detected=loss_detected,
            loss_reason=loss_reason,
            gap_id=gap_id,
            reconciliation_status=reconciliation_status,
        )

    @staticmethod
    def _raise_remnawave_maintenance_status(operation: str, status_code: int) -> None:
        logger.error("backend_remnawave_maintenance_failed", operation=operation, status_code=status_code)
        if status_code in {408, 425, 429, 502, 503, 504} or status_code >= 500:
            raise BackendAPIRemnawaveMaintenanceTransientError(
                f"Remnawave {operation} transient failure: {status_code}"
            )
        raise BackendAPIRemnawaveMaintenancePermanentError(f"Remnawave {operation} permanent failure: {status_code}")

    async def purge_remnawave_stream_retention(self, *, batch_limit: int) -> BackendRemnawaveRetentionResult:
        """Delete one backend-owned bounded retention batch and validate its receipt."""
        self._require_backend_internal_enabled("Internal Remnawave stream retention")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")
        if isinstance(batch_limit, bool) or not 1 <= batch_limit <= 5_000:
            raise ValueError("batch_limit must be between 1 and 5000")

        try:
            response = await self._client.post(
                "internal/remnawave/retention/purge",
                json={"batch_limit": batch_limit},
                headers=self._backend_internal_secret_headers(),
            )
        except httpx.HTTPError as exc:
            raise BackendAPIRemnawaveMaintenanceTransientError("Remnawave retention transport failed") from exc
        if response.status_code != 200:
            logger.error(
                "backend_remnawave_retention_failed",
                status_code=response.status_code,
            )
            if response.status_code in {408, 425, 429, 502, 503, 504} or response.status_code >= 500:
                raise BackendAPIRemnawaveMaintenanceTransientError(
                    f"Remnawave retention transient failure: {response.status_code}"
                )
            raise BackendAPIRemnawaveMaintenancePermanentError(
                f"Remnawave retention permanent failure: {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned invalid JSON") from exc
        return _validate_remnawave_retention_result(payload)

    async def create_remnawave_auto_renew_invoice(
        self,
        *,
        remnawave_user_id: int,
        expected_expire_at: datetime,
    ) -> BackendAutoRenewInvoice:
        """Create or replay the backend-owned persisted auto-renew invoice."""
        self._require_backend_internal_enabled("Internal Remnawave auto-renew invoice")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")
        if isinstance(remnawave_user_id, bool) or not isinstance(remnawave_user_id, int) or remnawave_user_id <= 0:
            raise ValueError("remnawave_user_id must be a positive integer")

        canonical_expiry = canonical_auto_renew_expiry(expected_expire_at)
        idempotency_key = auto_renew_idempotency_key(remnawave_user_id, expected_expire_at)
        try:
            response = await self._client.post(
                f"internal/remnawave/users/{remnawave_user_id}/auto-renew-invoice",
                json={"expected_expire_at": canonical_expiry},
                headers={
                    **self._backend_internal_secret_headers(),
                    "Idempotency-Key": idempotency_key,
                },
            )
        except httpx.HTTPError as exc:
            raise BackendAPIAutoRenewTransientError("Auto-renew invoice transport failed") from exc

        if response.status_code != 200:
            logger.error(
                "backend_remnawave_auto_renew_failed",
                status_code=response.status_code,
                remnawave_user_id=remnawave_user_id,
            )
            if response.status_code in {408, 425, 429, 502, 503, 504} or response.status_code >= 500:
                raise BackendAPIAutoRenewTransientError(f"Auto-renew invoice transient failure: {response.status_code}")
            raise BackendAPIAutoRenewPermanentError(f"Auto-renew invoice permanent failure: {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIAutoRenewPermanentError("Auto-renew invoice returned invalid JSON") from exc
        return _validate_auto_renew_invoice(payload)

    async def filter_remnawave_auto_renew_eligible(self, user_ids: list[int]) -> frozenset[int]:
        """Filter a bounded Remnawave scan through CyberVPN-owned consent."""
        self._require_backend_internal_enabled("Internal Remnawave auto-renew eligibility")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")
        if not user_ids:
            return frozenset()
        if len(user_ids) > 1000:
            raise ValueError("Auto-renew eligibility batch must not exceed 1000 user IDs")
        if len(set(user_ids)) != len(user_ids) or any(
            isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0 for user_id in user_ids
        ):
            raise ValueError("Auto-renew eligibility requires unique positive integer user IDs")

        try:
            response = await self._client.post(
                "internal/remnawave/auto-renew/eligible",
                json={"user_ids": user_ids},
                headers=self._backend_internal_secret_headers(),
            )
        except httpx.HTTPError as exc:
            raise BackendAPIAutoRenewTransientError("Auto-renew eligibility transport failed") from exc
        if response.status_code != 200:
            logger.error(
                "backend_remnawave_auto_renew_eligibility_failed",
                status_code=response.status_code,
            )
            if response.status_code in {408, 425, 429} or response.status_code >= 500:
                raise BackendAPIAutoRenewTransientError(
                    f"Auto-renew eligibility transient failure: {response.status_code}"
                )
            raise BackendAPIAutoRenewPermanentError(f"Auto-renew eligibility permanent failure: {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIAutoRenewPermanentError("Auto-renew eligibility returned invalid JSON") from exc
        if not isinstance(payload, dict) or set(payload) != {"eligible_user_ids"}:
            raise BackendAPIAutoRenewPermanentError("Auto-renew eligibility returned an invalid payload")
        eligible_values = payload["eligible_user_ids"]
        if not isinstance(eligible_values, list) or any(
            isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0 for user_id in eligible_values
        ):
            raise BackendAPIAutoRenewPermanentError("Auto-renew eligibility returned invalid user IDs")
        if len(set(eligible_values)) != len(eligible_values) or not set(eligible_values).issubset(user_ids):
            raise BackendAPIAutoRenewPermanentError("Auto-renew eligibility returned unexpected user IDs")
        return frozenset(eligible_values)

    async def reconcile_telegram_stars_refund(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend reconciliation")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "telegram/payments/stars/reconcile-refund",
            json=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_reconciliation_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Backend reconciliation failed: {response.status_code}")
        return response.json()

    async def run_stage1_payment_reconciliation(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend reconciliation")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "payments/internal/reconciliation/run",
            params=payload,
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_stage1_payment_reconciliation_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Stage 1 payment reconciliation failed: {response.status_code}")
        return response.json()

    async def run_stage1_provisioning_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend provisioning retry")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "subscriptions/internal/provisioning-retries/run",
            params=payload,
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_stage1_provisioning_retries_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Stage 1 provisioning retries failed: {response.status_code}")
        return response.json()

    async def run_payment_completed_partner_earnings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._payment_settlement_enabled:
            raise BackendAPIError("Internal backend partner earning API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        settlement_secret = self._settings.payment_settlement_worker_secret
        response = await self._client.post(
            "payments/internal/partner-earnings/run",
            params=payload,
            headers={
                "X-Payment-Settlement-Worker-Secret": (
                    settlement_secret.get_secret_value().strip() if settlement_secret is not None else ""
                )
            },
        )
        if response.status_code >= 400:
            logger.error(
                "backend_payment_completed_partner_earnings_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Payment completed partner earnings failed: {response.status_code}")
        return response.json()

    async def get_public_network_regions(self) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.get(
            "public/network/regions",
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_public_network_regions_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Public network regions request failed: {response.status_code}")
        return response.json()

    async def publish_public_network_dpi_score(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "public/network/internal/dpi-score/publish",
            json=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_public_network_dpi_publish_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Public network DPI publish failed: {response.status_code}")
        return response.json()

    async def claim_partner_bot_provisioning_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "partner-bots/internal/provisioning-jobs/claim",
            json=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_partner_bot_claim_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Partner bot claim failed: {response.status_code}")
        return response.json()

    async def finalize_partner_bot_provisioning_job(
        self,
        *,
        provisioning_job_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            f"partner-bots/internal/provisioning-jobs/{provisioning_job_id}/finalize",
            json=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_partner_bot_finalize_failed",
                provisioning_job_id=provisioning_job_id,
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Partner bot finalize failed: {response.status_code}")
        return response.json()

    async def refresh_growth_reporting(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/growth-reporting/internal/refresh",
            params=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_refresh_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Growth reporting refresh failed: {response.status_code}")
        return response.json()

    async def refresh_growth_fx_rates(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend growth FX refresh")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/growth-fx/internal/refresh",
            params=payload,
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_fx_refresh_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Growth FX refresh failed: {response.status_code}")
        return response.json()

    async def claim_growth_reporting_deliveries(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/growth-reporting/internal/deliveries/claim",
            params=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_claim_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Growth reporting claim failed: {response.status_code}")
        return response.json()

    async def complete_growth_reporting_delivery(
        self,
        *,
        delivery_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            f"admin/growth-reporting/internal/deliveries/{delivery_id}/complete",
            json=payload,
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_complete_failed",
                delivery_id=delivery_id,
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Growth reporting complete failed: {response.status_code}")
        return response.json()

    async def cleanup_growth_reporting_artifacts(self) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/growth-reporting/internal/cleanup",
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_cleanup_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Growth reporting cleanup failed: {response.status_code}")
        return response.json()

    async def process_growth_reporting_governance_followups(self) -> dict[str, Any]:
        self._require_telegram_bot_internal_enabled("Internal Telegram bot audience backend")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/growth-reporting/internal/governance/followups/process",
            headers=self._telegram_bot_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_governance_followups_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(f"Growth reporting governance follow-up processing failed: {response.status_code}")
        return response.json()

    async def execute_next_vpn_tester_run(self) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend VPN Tester")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/vpn-tester/internal/queued/execute-next",
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error("backend_vpn_tester_execute_next_failed", status_code=response.status_code)
            raise BackendAPIError(f"VPN Tester execute-next failed: {response.status_code}")
        return response.json()

    async def run_scheduled_vpn_tester(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend VPN Tester")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/vpn-tester/internal/scheduled/run",
            json=payload,
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error("backend_vpn_tester_scheduled_failed", status_code=response.status_code)
            raise BackendAPIError(f"VPN Tester scheduled run failed: {response.status_code}")
        return response.json()

    async def run_vpn_tester_schedule(self, schedule_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend VPN Tester schedule gate")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            f"admin/vpn-tester/internal/schedules/{schedule_key}/run",
            json=payload,
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error("backend_vpn_tester_schedule_gate_failed", status_code=response.status_code)
            raise BackendAPIError(f"VPN Tester schedule gate failed: {response.status_code}")
        return response.json()

    async def cleanup_vpn_tester(self) -> dict[str, Any]:
        self._require_backend_internal_enabled("Internal backend VPN Tester")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            "admin/vpn-tester/internal/cleanup",
            headers=self._backend_internal_secret_headers(),
        )
        if response.status_code >= 400:
            logger.error("backend_vpn_tester_cleanup_failed", status_code=response.status_code)
            raise BackendAPIError(f"VPN Tester cleanup failed: {response.status_code}")
        return response.json()


def _validate_auto_renew_invoice(payload: Any) -> BackendAutoRenewInvoice:
    """Validate the non-sensitive backend delivery receipt."""
    if not isinstance(payload, dict):
        raise BackendAPIAutoRenewPermanentError("Auto-renew invoice returned an invalid payload")
    if set(payload) != {"payment_id", "reused", "notification_status"}:
        raise BackendAPIAutoRenewPermanentError("Auto-renew invoice returned an invalid payload")

    try:
        payment_id = str(UUID(str(payload.get("payment_id"))))
    except (TypeError, ValueError, AttributeError) as exc:
        raise BackendAPIAutoRenewPermanentError("Auto-renew invoice returned an invalid payment ID") from exc

    reused = payload.get("reused")
    if not isinstance(reused, bool):
        raise BackendAPIAutoRenewPermanentError("Auto-renew invoice returned an invalid replay state")
    notification_status = payload.get("notification_status")
    if notification_status not in {"queued", "already_queued"}:
        raise BackendAPIAutoRenewPermanentError("Auto-renew invoice returned an invalid notification receipt")

    return BackendAutoRenewInvoice(
        payment_id=payment_id,
        reused=reused,
        notification_status=notification_status,
    )


def _validate_remnawave_retention_result(payload: Any) -> BackendRemnawaveRetentionResult:
    if not isinstance(payload, dict) or set(payload) != {
        "deleted_by_table",
        "total_deleted",
        "has_more",
        "purged_at",
    }:
        raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned an invalid payload")

    deleted_by_table = payload["deleted_by_table"]
    if not isinstance(deleted_by_table, dict) or set(deleted_by_table) != _REMNAWAVE_RETENTION_TABLES:
        raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned an invalid table receipt")
    if any(
        not isinstance(table, str) or isinstance(count, bool) or not isinstance(count, int) or count < 0
        for table, count in deleted_by_table.items()
    ):
        raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned invalid deletion counts")

    total_deleted = payload["total_deleted"]
    has_more = payload["has_more"]
    if (
        isinstance(total_deleted, bool)
        or not isinstance(total_deleted, int)
        or total_deleted < 0
        or total_deleted != sum(deleted_by_table.values())
        or not isinstance(has_more, bool)
    ):
        raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned an inconsistent receipt")

    purged_at_raw = payload["purged_at"]
    if not isinstance(purged_at_raw, str):
        raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned an invalid purge timestamp")
    try:
        purged_at = datetime.fromisoformat(purged_at_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BackendAPIRemnawaveMaintenancePermanentError(
            "Remnawave retention returned an invalid purge timestamp"
        ) from exc
    if purged_at.tzinfo is None or purged_at.utcoffset() is None:
        raise BackendAPIRemnawaveMaintenancePermanentError("Remnawave retention returned a naive purge timestamp")

    return BackendRemnawaveRetentionResult(
        deleted_by_table={table: int(count) for table, count in deleted_by_table.items()},
        total_deleted=total_deleted,
        has_more=has_more,
        purged_at=purged_at.astimezone(UTC),
    )
