from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities.storefront import BillingDescriptor, InvoiceProfile, MerchantProfile


def test_merchant_profile_exposes_invoice_and_tax_foundation_fields() -> None:
    invoice_profile_id = uuid4()
    merchant = MerchantProfile(
        id=uuid4(),
        profile_key="cybervpn-mor",
        legal_entity_name="CyberVPN LLC",
        billing_descriptor="CYBERVPN",
        supported_currencies=["EUR", "USD"],
        tax_behavior={"pricing_mode": "tax_inclusive", "country": "DE"},
        refund_responsibility_model="merchant_of_record",
        chargeback_liability_model="merchant_of_record",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        invoice_profile_id=invoice_profile_id,
        settlement_reference="stripe-main",
    )

    assert merchant.invoice_profile_id == invoice_profile_id
    assert merchant.supported_currencies == ["EUR", "USD"]
    assert merchant.tax_behavior["pricing_mode"] == "tax_inclusive"
    assert merchant.settlement_reference == "stripe-main"


def test_invoice_profile_and_billing_descriptor_capture_snapshot_ready_fields() -> None:
    invoice_profile = InvoiceProfile(
        id=uuid4(),
        profile_key="cybervpn-eu",
        display_name="CyberVPN EU",
        issuer_legal_name="CyberVPN EU GmbH",
        tax_identifier="DE123456789",
        issuer_email="billing@cybervpn.test",
        tax_behavior={"invoice_mode": "consumer", "tax_exclusive": False},
        invoice_footer="VAT applied where required",
        receipt_footer="Thank you",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    descriptor = BillingDescriptor(
        id=uuid4(),
        descriptor_key="cybervpn-eu-default",
        merchant_profile_id=uuid4(),
        statement_descriptor="CYBERVPN EU",
        soft_descriptor="CYBERVPN*EU",
        support_phone="+49-555-0101",
        support_url="https://support.cybervpn.test",
        is_default=True,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        invoice_profile_id=invoice_profile.id,
    )

    assert invoice_profile.tax_behavior["invoice_mode"] == "consumer"
    assert descriptor.invoice_profile_id == invoice_profile.id
    assert descriptor.is_default is True
    assert descriptor.statement_descriptor == "CYBERVPN EU"
