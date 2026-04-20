import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_phase0_phase1_validation_context_preserves_realm_and_storefront_separation(
    phase0_phase1_validation_context: dict[str, dict],
) -> None:
    official_realm = phase0_phase1_validation_context["official_realm"]
    partner_realm = phase0_phase1_validation_context["partner_realm"]
    official_storefront = phase0_phase1_validation_context["official_storefront"]
    partner_storefront = phase0_phase1_validation_context["partner_storefront"]
    legal_acceptance = phase0_phase1_validation_context["legal_acceptance"]
    risk_subject = phase0_phase1_validation_context["risk_subject"]
    offer = phase0_phase1_validation_context["offer"]
    pricebook = phase0_phase1_validation_context["pricebook"]
    program_eligibility = phase0_phase1_validation_context["program_eligibility"]
    risk_link = phase0_phase1_validation_context["risk_link"]
    phase1_api_paths = phase0_phase1_validation_context["phase1_api_paths"]

    assert official_realm["id"] != partner_realm["id"]
    assert official_storefront["auth_realm_id"] == official_realm["id"]
    assert partner_storefront["auth_realm_id"] == partner_realm["id"]
    assert legal_acceptance["storefront_id"] == partner_storefront["id"]
    assert legal_acceptance["auth_realm_id"] == partner_realm["id"]
    assert risk_subject["primary_realm_id"] == partner_realm["id"]
    assert pricebook["storefront_id"] == partner_storefront["id"]
    assert program_eligibility["offer_id"] == offer["id"]
    assert risk_link["left_subject_id"] == risk_subject["id"]
    assert "/api/v1/realms/resolve" in phase1_api_paths
    assert "/api/v1/security/eligibility/checks" in phase1_api_paths
