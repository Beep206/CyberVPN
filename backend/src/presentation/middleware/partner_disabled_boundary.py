"""Partner platform disabled-state boundary for staged rollout."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_404_NOT_FOUND

from src.config.settings import settings

logger = logging.getLogger("cybervpn")

PARTNER_PORTAL_PUBLIC_PREFIXES = (
    "/api/v1/partner/",
    "/api/v1/partner-workspaces",
    "/api/v1/partner-session",
    "/api/v1/partner-notifications",
    "/api/v1/partner-bots",
    "/api/v1/partner-statements",
    "/api/v1/reporting/partner-workspaces",
)

PARTNER_APPLICATION_PREFIXES = (
    "/api/v1/partner-application-drafts",
)

PARTNER_CODE_PREFIXES = (
    "/api/v1/partner/codes",
    "/api/v1/partner/bind",
)

PARTNER_ATTRIBUTION_PREFIXES = (
    "/api/v1/attribution",
)

PARTNER_PAYOUT_PREFIXES = (
    "/api/v1/partner-payout-accounts",
    "/api/v1/payouts",
)

PARTNER_STOREFRONT_PREFIXES = (
    "/api/v1/storefronts",
    "/api/v1/storefront-profiles",
)

PARTNER_REPORTING_PREFIXES = (
    "/api/v1/reporting/partner-workspaces",
)

PARTNER_SETTLEMENT_SANDBOX_PREFIXES = (
    "/api/v1/settlement-sandbox",
)


class PartnerDisabledBoundaryMiddleware(BaseHTTPMiddleware):
    """Blocks public partner surfaces until the relevant S3 flags are enabled.

    Admin preview routes under `/api/v1/admin/partner...` are deliberately left
    to the existing admin auth/RBAC dependencies. This middleware protects
    public/self-serve partner routes from accidental launch while S3 is still
    behind disabled-state gates.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if not bool(settings.partner_portal_enabled) and _matches(path, PARTNER_PORTAL_PUBLIC_PREFIXES):
            return _disabled_response(
                code="partner_portal_disabled",
                message="Partner portal is not enabled for this release.",
                path=path,
            )

        if _matches(path, PARTNER_APPLICATION_PREFIXES):
            if not bool(settings.partner_portal_enabled):
                return _disabled_response(
                    code="partner_portal_disabled",
                    message="Partner portal is not enabled for this release.",
                    path=path,
                )
            if not bool(settings.partner_applications_enabled):
                return _disabled_response(
                    code="partner_applications_disabled",
                    message="Partner applications are not enabled for this release.",
                    path=path,
                    stage="S3-STAGE-06",
                )

        if _matches(path, PARTNER_CODE_PREFIXES) or _matches_partner_workspace_codes_path(path):
            if not bool(settings.partner_portal_enabled):
                return _disabled_response(
                    code="partner_portal_disabled",
                    message="Partner portal is not enabled for this release.",
                    path=path,
                )
            if not bool(settings.partner_codes_enabled):
                return _disabled_response(
                    code="partner_codes_disabled",
                    message="Partner codes are not enabled for this release.",
                    path=path,
                    stage="S3-STAGE-08",
                )

        if _matches(path, PARTNER_ATTRIBUTION_PREFIXES) and not bool(settings.partner_attribution_enabled):
            return _disabled_response(
                code="partner_attribution_disabled",
                message="Partner attribution is not enabled for this release.",
                path=path,
                stage="S3-STAGE-08",
            )

        if not bool(settings.partner_payouts_enabled) and _matches(path, PARTNER_PAYOUT_PREFIXES):
            return _disabled_response(
                code="partner_payouts_disabled",
                message="Partner payouts are not enabled for this release.",
                path=path,
            )

        if not bool(settings.partner_storefronts_enabled) and _matches(path, PARTNER_STOREFRONT_PREFIXES):
            return _disabled_response(
                code="partner_storefronts_disabled",
                message="Partner storefronts are not enabled for this release.",
                path=path,
                stage="S3-STAGE-09",
            )

        if _matches(path, PARTNER_REPORTING_PREFIXES) or _matches_partner_workspace_reporting_path(path):
            if not bool(settings.partner_portal_enabled):
                return _disabled_response(
                    code="partner_portal_disabled",
                    message="Partner portal is not enabled for this release.",
                    path=path,
                )
            if not bool(settings.partner_reporting_enabled):
                return _disabled_response(
                    code="partner_reporting_disabled",
                    message="Partner reporting is not enabled for this release.",
                    path=path,
                    stage="S3-STAGE-10",
                )

        if _matches(path, PARTNER_SETTLEMENT_SANDBOX_PREFIXES) or _matches_partner_workspace_settlement_sandbox_path(
            path
        ):
            if not bool(settings.partner_portal_enabled):
                return _disabled_response(
                    code="partner_portal_disabled",
                    message="Partner portal is not enabled for this release.",
                    path=path,
                )
            if not bool(settings.partner_settlement_sandbox_enabled):
                return _disabled_response(
                    code="partner_settlement_sandbox_disabled",
                    message="Partner settlement sandbox is not enabled for this release.",
                    path=path,
                    stage="S3-STAGE-11",
                )

        return await call_next(request)


def _matches(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _matches_partner_workspace_codes_path(path: str) -> bool:
    if not path.startswith("/api/v1/partner-workspaces/"):
        return False
    return (
        "/codes" in path
        or "/reseller-voucher-batches" in path
    )


def _matches_partner_workspace_reporting_path(path: str) -> bool:
    if not path.startswith("/api/v1/partner-workspaces/"):
        return False
    return any(
        segment in path
        for segment in (
            "/analytics-metrics",
            "/conversion-records",
            "/report-exports",
            "/reporting-summary",
            "/statements",
        )
    )


def _matches_partner_workspace_settlement_sandbox_path(path: str) -> bool:
    if not path.startswith("/api/v1/partner-workspaces/"):
        return False
    return "/settlement-sandbox" in path


def _disabled_response(*, code: str, message: str, path: str, stage: str = "S3-STAGE-05") -> JSONResponse:
    logger.info(
        "Partner S3 disabled boundary blocked request",
        extra={"path": path, "disabled_code": code},
    )
    return JSONResponse(
        status_code=HTTP_404_NOT_FOUND,
        content={
            "detail": {
                "code": code,
                "message": message,
                "stage": stage,
            }
        },
        headers={
            "Cache-Control": "no-store",
            "X-CyberVPN-Partner-Boundary": code,
        },
    )
