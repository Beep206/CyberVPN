from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.communication_profile_model import CommunicationProfileModel
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.support_profile_model import SupportProfileModel
from src.infrastructure.database.session import Base


def test_storefront_core_persists_with_optional_profile_bindings() -> None:
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(
        engine,
        tables=[
            BrandModel.__table__,
            MerchantProfileModel.__table__,
            SupportProfileModel.__table__,
            CommunicationProfileModel.__table__,
            StorefrontModel.__table__,
        ],
    )

    brand_id = uuid4()
    merchant_profile_id = uuid4()
    support_profile_id = uuid4()
    communication_profile_id = uuid4()
    storefront_with_profiles_id = uuid4()
    storefront_without_profiles_id = uuid4()

    with Session(engine) as session:
        brand = BrandModel(
            id=brand_id,
            brand_key="cybervpn",
            display_name="CyberVPN",
        )
        merchant_profile = MerchantProfileModel(
            id=merchant_profile_id,
            profile_key="merchant-main",
            legal_entity_name="CyberVPN LLC",
            billing_descriptor="CYBERVPN",
        )
        support_profile = SupportProfileModel(
            id=support_profile_id,
            profile_key="support-main",
            support_email="support@example.test",
            help_center_url="https://help.example.test",
        )
        communication_profile = CommunicationProfileModel(
            id=communication_profile_id,
            profile_key="comm-main",
            sender_domain="mail.example.test",
            from_email="hello@example.test",
        )
        storefront_with_profiles = StorefrontModel(
            id=storefront_with_profiles_id,
            storefront_key="official-web",
            brand_id=brand_id,
            display_name="Official Web",
            host="cybervpn.example.test",
            merchant_profile_id=merchant_profile_id,
            support_profile_id=support_profile_id,
            communication_profile_id=communication_profile_id,
        )
        storefront_without_profiles = StorefrontModel(
            id=storefront_without_profiles_id,
            storefront_key="partner-web",
            brand_id=brand_id,
            display_name="Partner Web",
            host="partner.example.test",
        )

        session.add_all(
            [
                brand,
                merchant_profile,
                support_profile,
                communication_profile,
                storefront_with_profiles,
                storefront_without_profiles,
            ]
        )
        session.commit()

        storefronts = session.execute(
            select(StorefrontModel).where(StorefrontModel.brand_id == brand_id).order_by(StorefrontModel.storefront_key)
        ).scalars().all()

        assert len(storefronts) == 2
        assert storefronts[0].storefront_key == "official-web"
        assert storefronts[0].merchant_profile_id == merchant_profile_id
        assert storefronts[1].storefront_key == "partner-web"
        assert storefronts[1].merchant_profile_id is None
