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
