from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.application.use_cases.customer_subscriptions.service_access import CustomerSubscriptionServiceAccessUseCase
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)

pytestmark = [pytest.mark.integration]


def _spb_de_routing_context(*, external_squad_uuid: str, internal_squad_uuid: str) -> dict[str, object]:
    return {
        "remnawave_routing_product": "premium_spb_de_exceptions",
        "remnawave_external_squad_uuid": external_squad_uuid,
        "remnawave_internal_squad_uuids": [internal_squad_uuid],
        "remnawave_config_profile": "S1 SPB DE Exceptions",
        "remnawave_policy_version": "premium_spb_de_exceptions.v1",
        "remnawave_fail_closed_for_matched_exceptions": True,
    }


@pytest.mark.asyncio
async def test_spb_de_service_context_and_provisioning_routing_payload_persist() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    auth_realm_id = uuid.uuid4()
    customer_account_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    provisioning_profile_id = uuid.uuid4()
    subscription_key = f"grant:{uuid.uuid4()}"
    external_squad_uuid = str(uuid.uuid4())
    internal_squad_uuid = str(uuid.uuid4())
    routing_context = _spb_de_routing_context(
        external_squad_uuid=external_squad_uuid,
        internal_squad_uuid=internal_squad_uuid,
    )

    try:
        with sessionmaker() as db:
            db.add(
                AuthRealmModel(
                    id=auth_realm_id,
                    realm_key="customer-spb-de",
                    realm_type="customer",
                    display_name="Customer SPB/DE",
                    audience="customer-spb-de",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
            )
            db.add(
                MobileUserModel(
                    id=customer_account_id,
                    public_uid=910_002_001,
                    auth_realm_id=auth_realm_id,
                    email="spb-de-persist@example.test",
                    password_hash="hashed",
                    remnawave_uuid=str(uuid.uuid4()),
                    subscription_url="https://subscription.example.local/sub/legacy-spb-de",
                )
            )
            service_identity = ServiceIdentityModel(
                id=service_identity_id,
                service_key="svc_spb_de_persist",
                customer_account_id=customer_account_id,
                auth_realm_id=auth_realm_id,
                provider_name="remnawave",
                identity_scope="subscription",
                subscription_key=subscription_key,
                provider_subject_ref=str(uuid.uuid4()),
                identity_status="active",
                service_context={
                    "plan_code": "premium_spb_de_exceptions",
                    "subscription_url": "https://subscription.example.local/sub/selected-spb-de",
                    **routing_context,
                },
            )
            db.add(service_identity)
            db.add(
                ProvisioningProfileModel(
                    id=provisioning_profile_id,
                    service_identity_id=service_identity_id,
                    profile_key="shared_client-default",
                    target_channel="shared_client",
                    delivery_method="shared_client",
                    profile_status="active",
                    provider_name="remnawave",
                    provisioning_payload={"resolved_from": "legacy"},
                )
            )
            db.commit()

            use_case = CustomerSubscriptionServiceAccessUseCase(SyncSessionAdapter(db))
            provisioning_profile = await use_case._ensure_provisioning_profile(
                service_identity=service_identity,
                profile_key="shared_client-default",
                channel_type="shared_client",
            )
            db.commit()

            assert provisioning_profile.id == provisioning_profile_id
            assert provisioning_profile.service_identity_id == service_identity_id

        with sessionmaker() as db:
            persisted_identity = db.get(ServiceIdentityModel, service_identity_id)
            persisted_profile = db.execute(
                select(ProvisioningProfileModel).where(
                    ProvisioningProfileModel.service_identity_id == service_identity_id,
                    ProvisioningProfileModel.profile_key == "shared_client-default",
                )
            ).scalar_one()

            assert persisted_identity is not None
            assert persisted_identity.service_context["plan_code"] == "premium_spb_de_exceptions"
            assert persisted_identity.service_context | routing_context == persisted_identity.service_context
            assert persisted_profile.id == provisioning_profile_id
            assert persisted_profile.provisioning_payload["resolved_from"] == "legacy"
            assert persisted_profile.provisioning_payload["remnawave_routing"] == routing_context
            assert "subscription_url" not in persisted_profile.provisioning_payload["remnawave_routing"]
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
