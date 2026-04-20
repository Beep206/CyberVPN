import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

PHASE1_REQUIRED_PATHS = (
    f"{API_V1_PREFIX}/auth/login",
    f"{API_V1_PREFIX}/auth/me",
    f"{API_V1_PREFIX}/realms/",
    f"{API_V1_PREFIX}/realms/resolve",
    f"{API_V1_PREFIX}/admin/partner-workspaces",
    f"{API_V1_PREFIX}/admin/partner-workspaces/{{workspace_id}}",
    f"{API_V1_PREFIX}/partner-workspaces/me",
    f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}",
    f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/members",
    f"{API_V1_PREFIX}/offers/",
    f"{API_V1_PREFIX}/offers/admin",
    f"{API_V1_PREFIX}/pricebooks/resolve",
    f"{API_V1_PREFIX}/pricebooks/admin",
    f"{API_V1_PREFIX}/program-eligibility/",
    f"{API_V1_PREFIX}/program-eligibility/admin",
    f"{API_V1_PREFIX}/policies/",
    f"{API_V1_PREFIX}/policies/{{policy_version_id}}/approve",
    f"{API_V1_PREFIX}/legal-documents/",
    f"{API_V1_PREFIX}/legal-documents/sets",
    f"{API_V1_PREFIX}/legal-documents/sets/resolve",
    f"{API_V1_PREFIX}/policy-acceptance/",
    f"{API_V1_PREFIX}/policy-acceptance/me",
    f"{API_V1_PREFIX}/security/risk-subjects",
    f"{API_V1_PREFIX}/security/risk-subjects/{{risk_subject_id}}/identifiers",
    f"{API_V1_PREFIX}/security/risk-subjects/{{risk_subject_id}}/links",
    f"{API_V1_PREFIX}/security/risk-subjects/{{risk_subject_id}}/reviews",
    f"{API_V1_PREFIX}/security/risk-reviews",
    f"{API_V1_PREFIX}/security/eligibility/checks",
)

PHASE1_REQUIRED_SCHEMAS = (
    "RealmResponse",
    "RealmResolutionResponse",
    "PartnerWorkspaceResponse",
    "PartnerWorkspaceMemberResponse",
    "OfferResponse",
    "PricebookResponse",
    "ProgramEligibilityPolicyResponse",
    "PolicyVersionResponse",
    "LegalDocumentResponse",
    "LegalDocumentSetResponse",
    "AcceptedLegalDocumentResponse",
    "RiskSubjectResponse",
    "RiskLinkResponse",
    "RiskReviewResponse",
    "EligibilityCheckResponse",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for generated client workflows"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def test_live_openapi_contains_phase1_foundation_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    for required_path in PHASE1_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase1_foundation_paths() -> None:
    schema = _exported_openapi_schema()
    paths = schema["paths"]

    for required_path in PHASE1_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase1_foundation_schemas() -> None:
    schema = _exported_openapi_schema()
    components = schema["components"]["schemas"]

    for schema_name in PHASE1_REQUIRED_SCHEMAS:
        assert schema_name in components
