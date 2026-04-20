from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_application_onboarding_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/partner-application-drafts/current" in paths
    assert f"{API_V1_PREFIX}/partner-application-drafts" in paths
    assert f"{API_V1_PREFIX}/partner-application-drafts/{{draft_id}}/submit" in paths
    assert f"{API_V1_PREFIX}/partner-application-drafts/{{draft_id}}/withdraw" in paths
    assert f"{API_V1_PREFIX}/partner-application-drafts/{{draft_id}}/resubmit" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/lane-applications" in paths
    assert f"{API_V1_PREFIX}/admin/partner-applications" in paths
    assert f"{API_V1_PREFIX}/admin/partner-applications/{{workspace_id}}" in paths
    assert (
        f"{API_V1_PREFIX}/admin/partner-applications/{{workspace_id}}/request-info"
        in paths
    )

    assert "PartnerApplicationDraftDetailResponse" in components
    assert "PartnerApplicationDraftResponse" in components
    assert "PartnerApplicationWorkspaceSummaryResponse" in components
    assert "PartnerLaneApplicationResponse" in components
    assert "PartnerApplicationReviewRequestDetailResponse" in components
    assert "PartnerApplicationAttachmentResponse" in components
