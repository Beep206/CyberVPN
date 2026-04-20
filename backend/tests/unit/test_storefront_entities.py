from datetime import datetime
from uuid import uuid4

from src.domain.entities.storefront import (
    Brand,
    CommunicationProfile,
    MerchantProfile,
    Storefront,
    SupportProfile,
)


def test_brand_entity_creation() -> None:
    brand = Brand(
        id=uuid4(),
        brand_key="cybervpn",
        display_name="CyberVPN",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert brand.brand_key == "cybervpn"
    assert brand.display_name == "CyberVPN"


def test_storefront_entity_allows_nullable_profile_bindings() -> None:
    storefront = Storefront(
        id=uuid4(),
        storefront_key="partner-web",
        brand_id=uuid4(),
        display_name="Partner Web",
        host="partner.example.test",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert storefront.merchant_profile_id is None
    assert storefront.support_profile_id is None
    assert storefront.communication_profile_id is None


def test_profile_entities_keep_identity_fields() -> None:
    merchant = MerchantProfile(
        id=uuid4(),
        profile_key="merchant-main",
        legal_entity_name="CyberVPN LLC",
        billing_descriptor="CYBERVPN",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    support = SupportProfile(
        id=uuid4(),
        profile_key="support-main",
        support_email="support@example.test",
        help_center_url="https://help.example.test",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    communication = CommunicationProfile(
        id=uuid4(),
        profile_key="comm-main",
        sender_domain="mail.example.test",
        from_email="hello@example.test",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert merchant.billing_descriptor == "CYBERVPN"
    assert support.support_email == "support@example.test"
    assert communication.sender_domain == "mail.example.test"
