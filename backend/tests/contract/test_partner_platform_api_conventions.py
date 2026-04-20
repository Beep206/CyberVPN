from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX, PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def _read_api_conventions() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "docs/api/partner-platform-api-conventions.md").read_text(encoding="utf-8")


def test_api_conventions_document_contains_canonical_headers_and_error_shape() -> None:
    content = _read_api_conventions()

    for required_term in (
        API_V1_PREFIX,
        "X-Request-ID",
        "Idempotency-Key",
        "error.code",
        "error.message",
        "request_id",
        "payment_dispute",
    ):
        assert required_term in content


def test_reserved_resource_groups_cover_phase_foundations_and_payout_account_family() -> None:
    assert "storefronts" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "realms" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "offers" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "pricebooks" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "legal-documents" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "merchant-profiles" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "invoice-profiles" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "billing-descriptors" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "attribution" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "commercial-bindings" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "quotes" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "orders" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "order-attribution-results" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "growth-rewards" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "renewal-orders" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "payment-disputes" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "earning-events" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "earning-holds" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "partner-payout-accounts" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "partner-statements" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "payouts" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "settlement-periods" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "reserves" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "reporting" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "exports" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "postbacks" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "service-identities" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "entitlements" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "provisioning-profiles" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "device-credentials" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "access-delivery-channels" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "risk-subjects" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "risk-reviews" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "governance-actions" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "eligibility-checks" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "traffic-declarations" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "creative-approvals" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "dispute-cases" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "pilot-cohorts" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def test_openapi_still_exposes_existing_api_v1_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/auth/login" in paths
    assert f"{API_V1_PREFIX}/plans/" in paths
    assert f"{API_V1_PREFIX}/payments/checkout/quote" in paths
