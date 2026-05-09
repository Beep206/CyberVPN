"""Minimal CyberVPN backend client for internal reconciliation hooks."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class BackendAPIError(Exception):
    """Raised when the internal backend reconciliation API fails."""

    pass


class BackendAPIClient:
    """Async client for internal backend endpoints used by the task worker."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._enabled = bool(
            self._settings.backend_api_url
            and self._settings.backend_internal_secret is not None
            and self._settings.backend_internal_secret.get_secret_value().strip()
        )
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def __aenter__(self) -> BackendAPIClient:
        if not self._enabled:
            return self

        self._client = httpx.AsyncClient(
            base_url=str(self._settings.backend_api_url).rstrip("/"),
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CyberVPN-TaskWorker/1.0",
                "X-Telegram-Bot-Secret": self._settings.backend_internal_secret.get_secret_value().strip(),
            },
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def reconcile_telegram_stars_refund(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("telegram/payments/stars/reconcile-refund", json=payload)
        if response.status_code >= 400:
            logger.error(
                "backend_reconciliation_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(f"Backend reconciliation failed: {response.status_code} {response.text}")
        return response.json()

    async def run_stage1_payment_reconciliation(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("payments/internal/reconciliation/run", params=payload)
        if response.status_code >= 400:
            logger.error(
                "backend_stage1_payment_reconciliation_failed",
                status_code=response.status_code,
            )
            raise BackendAPIError(
                f"Stage 1 payment reconciliation failed: {response.status_code}"
            )
        return response.json()

    async def get_public_network_regions(self) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.get("public/network/regions")
        if response.status_code >= 400:
            logger.error(
                "backend_public_network_regions_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Public network regions request failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def publish_public_network_dpi_score(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("public/network/internal/dpi-score/publish", json=payload)
        if response.status_code >= 400:
            logger.error(
                "backend_public_network_dpi_publish_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Public network DPI publish failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def claim_partner_bot_provisioning_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("partner-bots/internal/provisioning-jobs/claim", json=payload)
        if response.status_code >= 400:
            logger.error(
                "backend_partner_bot_claim_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(f"Partner bot claim failed: {response.status_code} {response.text}")
        return response.json()

    async def finalize_partner_bot_provisioning_job(
        self,
        *,
        provisioning_job_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            f"partner-bots/internal/provisioning-jobs/{provisioning_job_id}/finalize",
            json=payload,
        )
        if response.status_code >= 400:
            logger.error(
                "backend_partner_bot_finalize_failed",
                provisioning_job_id=provisioning_job_id,
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Partner bot finalize failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def refresh_growth_reporting(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("admin/growth-reporting/internal/refresh", params=payload)
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_refresh_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Growth reporting refresh failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def claim_growth_reporting_deliveries(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("admin/growth-reporting/internal/deliveries/claim", params=payload)
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_claim_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Growth reporting claim failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def complete_growth_reporting_delivery(
        self,
        *,
        delivery_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post(
            f"admin/growth-reporting/internal/deliveries/{delivery_id}/complete",
            json=payload,
        )
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_complete_failed",
                delivery_id=delivery_id,
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Growth reporting complete failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def cleanup_growth_reporting_artifacts(self) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("admin/growth-reporting/internal/cleanup")
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_cleanup_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                f"Growth reporting cleanup failed: {response.status_code} {response.text}"
            )
        return response.json()

    async def process_growth_reporting_governance_followups(self) -> dict[str, Any]:
        if not self._enabled:
            raise BackendAPIError("Internal backend reconciliation API is not configured")
        if self._client is None:
            raise RuntimeError("BackendAPIClient must be used as a context manager")

        response = await self._client.post("admin/growth-reporting/internal/governance/followups/process")
        if response.status_code >= 400:
            logger.error(
                "backend_growth_reporting_governance_followups_failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise BackendAPIError(
                "Growth reporting governance follow-up processing failed: "
                f"{response.status_code} {response.text}"
            )
        return response.json()
