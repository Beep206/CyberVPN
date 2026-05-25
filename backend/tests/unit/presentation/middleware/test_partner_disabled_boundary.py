from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config.settings import settings
from src.presentation.middleware.partner_disabled_boundary import PartnerDisabledBoundaryMiddleware


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(PartnerDisabledBoundaryMiddleware)

    @app.get("/api/v1/partner/dashboard")
    async def partner_dashboard() -> dict[str, str]:
        return {"status": "open"}

    @app.get("/api/v1/partner/codes")
    async def partner_codes() -> dict[str, str]:
        return {"status": "codes-open"}

    @app.get("/api/v1/partner-workspaces/me")
    async def partner_workspaces_me() -> dict[str, str]:
        return {"status": "open"}

    @app.get("/api/v1/partner-workspaces/workspace-1/codes")
    async def partner_workspace_codes() -> dict[str, str]:
        return {"status": "workspace-codes-open"}

    @app.get("/api/v1/partner-workspaces/workspace-1/reporting-summary")
    async def partner_workspace_reporting_summary() -> dict[str, str]:
        return {"status": "workspace-reporting-open"}

    @app.get("/api/v1/partner-workspaces/workspace-1/settlement-sandbox")
    async def partner_workspace_settlement_sandbox() -> dict[str, str]:
        return {"status": "workspace-settlement-sandbox-open"}

    @app.get("/api/v1/reporting/partner-workspaces/workspace-1/snapshot")
    async def partner_reporting_snapshot() -> dict[str, str]:
        return {"status": "reporting-api-open"}

    @app.get("/api/v1/partner-application-drafts/current")
    async def current_partner_application_draft() -> dict[str, str]:
        return {"status": "application-open"}

    @app.get("/api/v1/attribution/touchpoints")
    async def attribution_touchpoints() -> dict[str, str]:
        return {"status": "attribution-open"}

    @app.get("/api/v1/storefronts/partner-web/preview")
    async def storefront_preview() -> dict[str, str]:
        return {"status": "storefront-open"}

    @app.get("/api/v1/partner-payout-accounts")
    async def partner_payout_accounts() -> dict[str, str]:
        return {"status": "open"}

    @app.get("/api/v1/admin/partner-workspaces")
    async def admin_partner_workspaces() -> dict[str, str]:
        return {"status": "admin-preview"}

    return TestClient(app)


def test_partner_public_routes_are_hidden_when_portal_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", False)

    response = _client().get("/api/v1/partner/dashboard")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_portal_disabled"
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_portal_disabled"


def test_partner_workspace_routes_are_hidden_when_portal_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", False)

    response = _client().get("/api/v1/partner-workspaces/me")

    assert response.status_code == 404
    assert response.json()["detail"]["stage"] == "S3-STAGE-05"


def test_admin_partner_preview_routes_are_not_blocked_by_public_portal_boundary(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", False)

    response = _client().get("/api/v1/admin/partner-workspaces")

    assert response.status_code == 200
    assert response.json() == {"status": "admin-preview"}


def test_partner_public_routes_pass_when_portal_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)

    response = _client().get("/api/v1/partner/dashboard")

    assert response.status_code == 200
    assert response.json() == {"status": "open"}


def test_partner_application_routes_need_portal_and_applications_flags(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_applications_enabled", False)

    response = _client().get("/api/v1/partner-application-drafts/current")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "partner_applications_disabled",
        "message": "Partner applications are not enabled for this release.",
        "stage": "S3-STAGE-06",
    }
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_applications_disabled"


def test_partner_application_routes_stay_hidden_when_portal_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", False)
    monkeypatch.setattr(settings, "partner_applications_enabled", True)

    response = _client().get("/api/v1/partner-application-drafts/current")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_portal_disabled"


def test_partner_application_routes_pass_when_portal_and_applications_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_applications_enabled", True)

    response = _client().get("/api/v1/partner-application-drafts/current")

    assert response.status_code == 200
    assert response.json() == {"status": "application-open"}


def test_partner_payout_routes_stay_hidden_until_payouts_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_payouts_enabled", False)

    response = _client().get("/api/v1/partner-payout-accounts")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_payouts_disabled"


def test_partner_code_routes_stay_hidden_until_codes_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", False)

    response = _client().get("/api/v1/partner/codes")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "partner_codes_disabled",
        "message": "Partner codes are not enabled for this release.",
        "stage": "S3-STAGE-08",
    }
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_codes_disabled"


def test_partner_workspace_code_routes_stay_hidden_until_codes_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", False)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/codes")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_codes_disabled"


def test_partner_code_routes_pass_when_portal_and_codes_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", True)

    response = _client().get("/api/v1/partner/codes")

    assert response.status_code == 200
    assert response.json() == {"status": "codes-open"}


def test_partner_attribution_routes_stay_hidden_until_attribution_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", False)

    response = _client().get("/api/v1/attribution/touchpoints")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "partner_attribution_disabled",
        "message": "Partner attribution is not enabled for this release.",
        "stage": "S3-STAGE-08",
    }
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_attribution_disabled"


def test_partner_attribution_routes_pass_when_attribution_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)

    response = _client().get("/api/v1/attribution/touchpoints")

    assert response.status_code == 200
    assert response.json() == {"status": "attribution-open"}


def test_partner_storefront_routes_stay_hidden_until_storefronts_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_storefronts_enabled", False)

    response = _client().get("/api/v1/storefronts/partner-web/preview")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "partner_storefronts_disabled",
        "message": "Partner storefronts are not enabled for this release.",
        "stage": "S3-STAGE-09",
    }
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_storefronts_disabled"


def test_partner_storefront_routes_pass_when_storefronts_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_storefronts_enabled", True)

    response = _client().get("/api/v1/storefronts/partner-web/preview")

    assert response.status_code == 200
    assert response.json() == {"status": "storefront-open"}


def test_partner_reporting_routes_stay_hidden_until_reporting_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_reporting_enabled", False)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/reporting-summary")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "partner_reporting_disabled",
        "message": "Partner reporting is not enabled for this release.",
        "stage": "S3-STAGE-10",
    }
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_reporting_disabled"


def test_partner_reporting_api_routes_stay_hidden_until_reporting_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_reporting_enabled", False)

    response = _client().get("/api/v1/reporting/partner-workspaces/workspace-1/snapshot")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_reporting_disabled"


def test_partner_reporting_routes_stay_hidden_when_portal_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", False)
    monkeypatch.setattr(settings, "partner_reporting_enabled", True)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/reporting-summary")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_portal_disabled"


def test_partner_reporting_routes_pass_when_portal_and_reporting_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_reporting_enabled", True)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/reporting-summary")

    assert response.status_code == 200
    assert response.json() == {"status": "workspace-reporting-open"}


def test_partner_settlement_sandbox_routes_stay_hidden_until_sandbox_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_settlement_sandbox_enabled", False)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/settlement-sandbox")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "partner_settlement_sandbox_disabled",
        "message": "Partner settlement sandbox is not enabled for this release.",
        "stage": "S3-STAGE-11",
    }
    assert response.headers["x-cybervpn-partner-boundary"] == "partner_settlement_sandbox_disabled"


def test_partner_settlement_sandbox_routes_stay_hidden_when_portal_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", False)
    monkeypatch.setattr(settings, "partner_settlement_sandbox_enabled", True)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/settlement-sandbox")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "partner_portal_disabled"


def test_partner_settlement_sandbox_routes_pass_when_portal_and_sandbox_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_settlement_sandbox_enabled", True)

    response = _client().get("/api/v1/partner-workspaces/workspace-1/settlement-sandbox")

    assert response.status_code == 200
    assert response.json() == {"status": "workspace-settlement-sandbox-open"}
