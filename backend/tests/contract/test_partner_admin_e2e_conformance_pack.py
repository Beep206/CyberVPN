from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_admin_e2e_conformance_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    expected_paths = (
        f"{API_V1_PREFIX}/auth/login",
        f"{API_V1_PREFIX}/auth/logout-all",
        f"{API_V1_PREFIX}/partner-session/bootstrap",
        f"{API_V1_PREFIX}/partner-notifications",
        f"{API_V1_PREFIX}/partner-notifications/counters",
        f"{API_V1_PREFIX}/partner-notifications/{{notification_id}}/read",
        f"{API_V1_PREFIX}/partner-application-drafts",
        f"{API_V1_PREFIX}/partner-application-drafts/{{draft_id}}/attachments",
        f"{API_V1_PREFIX}/partner-application-drafts/{{draft_id}}/submit",
        f"{API_V1_PREFIX}/partner-application-drafts/{{draft_id}}/resubmit",
        f"{API_V1_PREFIX}/admin/partner-applications",
        f"{API_V1_PREFIX}/admin/partner-applications/{{workspace_id}}/request-info",
        f"{API_V1_PREFIX}/admin/partner-applications/{{workspace_id}}/approve-probation",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/review-requests/{{review_request_id}}/responses",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/legal-documents",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/legal-documents/{{document_kind}}/accept",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/members",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/payout-accounts",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/traffic-declarations",
        f"{API_V1_PREFIX}/traffic-declarations/",
        f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/verify",
    )

    for expected_path in expected_paths:
        assert expected_path in paths

    expected_components = (
        "PartnerSessionBootstrapResponse",
        "PartnerNotificationFeedItemResponse",
        "PartnerNotificationCountersResponse",
        "PartnerApplicationDraftDetailResponse",
        "PartnerApplicationAdminDetailResponse",
        "PartnerApplicationReviewRequestDetailResponse",
        "PartnerWorkspaceLegalDocumentResponse",
        "PartnerWorkspacePayoutAccountResponse",
        "PartnerWorkspaceTrafficDeclarationResponse",
        "PartnerWorkspaceThreadEventResponse",
    )

    for component_name in expected_components:
        assert component_name in components
