from pathlib import Path

from tests.factories import (
    AcceptedLegalDocumentFactory,
    AuthRealmFactory,
    PartnerWorkspaceFactory,
    RiskSubjectFactory,
    StorefrontFactory,
)


def _read_validation_pack() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "docs/testing/partner-platform-phase-0-and-phase-1-validation-pack.md").read_text(
        encoding="utf-8"
    )


def test_phase0_validation_pack_contains_required_fixture_and_signoff_sections() -> None:
    content = _read_validation_pack()

    for required_term in (
        "one official realm",
        "one partner realm",
        "one official storefront",
        "one partner storefront",
        "one partner workspace",
        "one legal acceptance record",
        "one risk subject",
        "platform architecture",
        "backend platform",
        "data/BI",
        "QA",
        "risk",
    ):
        assert required_term in content


def test_phase0_synthetic_factories_cover_required_validation_objects() -> None:
    official_realm = AuthRealmFactory()
    partner_storefront = StorefrontFactory()
    partner_workspace = PartnerWorkspaceFactory()
    legal_acceptance = AcceptedLegalDocumentFactory()
    risk_subject = RiskSubjectFactory()

    assert official_realm["realm_type"] == "customer"
    assert partner_storefront["host"].endswith(".example.test")
    assert partner_workspace["status"] == "active"
    assert legal_acceptance["acceptance_channel"] == "official-web"
    assert risk_subject["subject_type"] == "person_cluster"
