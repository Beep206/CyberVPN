from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.use_cases.attribution.order_resolution.resolve_order_attribution import (
    _infer_owner_type_from_code,
)
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.partner_attribution.attribution import (
    CapturePartnerAttributionCommand,
    CapturePartnerAttributionUseCase,
    ClaimPartnerAttributionCommand,
    ClaimPartnerAttributionUseCase,
    ConsumePartnerAttributionTransferCommand,
    ConsumePartnerAttributionTransferUseCase,
)
from src.application.use_cases.partner_attribution.utils import (
    build_public_token_for_code_id,
    hash_partner_attribution_token,
)
from src.config import settings
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _enable_partner_attribution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", True)


def _realm() -> AuthRealmModel:
    return AuthRealmModel(
        id=uuid.uuid4(),
        realm_key="customer",
        realm_type="customer",
        display_name="Customer Realm",
        audience="cybervpn:customer",
        cookie_namespace="customer",
        status="active",
        is_default=True,
    )


def _user(*, realm_id: uuid.UUID, email: str, partner_account_id: uuid.UUID | None = None) -> MobileUserModel:
    return MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=realm_id,
        email=email,
        password_hash="hashed-password",
        is_active=True,
        status="active",
        partner_account_id=partner_account_id,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_partner_attribution_capture_transfer_claim_creates_commercial_binding() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-owner@example.test")
            customer = _user(realm_id=realm.id, email="customer-claim@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="creator-partner",
                display_name="Creator Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="CREATOR42",
                code_normalized="CREATOR42",
                public_token_hash=hash_partner_attribution_token(build_public_token_for_code_id(uuid.uuid4())),
                partner_account_id=account.id,
                partner_user_id=partner_owner.id,
                markup_pct=7,
                is_active=True,
                lifecycle_status="active",
                approval_status="approved",
                owner_type="affiliate",
                lane_key="creator_affiliate",
                attribution_model="last_eligible_touch",
                attribution_window_seconds=30 * 24 * 60 * 60,
                allowed_channels=["content"],
                allowed_storefront_ids=["*"],
                allowed_geographies=["*"],
                sub_id_schema={},
            )
            code.public_token_hash = hash_partner_attribution_token(build_public_token_for_code_id(code.id))
            db.add_all([realm, partner_owner, customer, account, code])
            db.commit()

            adapter = SyncSessionAdapter(db)
            current_realm = RealmResolution(auth_realm=realm, source="test")
            capture = await CapturePartnerAttributionUseCase(adapter).execute(
                CapturePartnerAttributionCommand(
                    public_token=build_public_token_for_code_id(code.id),
                    source_host="cyber-vpn.net",
                    source_path="/p/demo",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={"creator": "demo"},
                    click_id="click-123",
                    browser_key="browser-abc",
                    campaign_params={"utm_source": "creator"},
                    current_realm=current_realm,
                )
            )
            transfer = await ConsumePartnerAttributionTransferUseCase(adapter).execute(
                ConsumePartnerAttributionTransferCommand(transfer_token=capture.transfer_token)
            )
            assert transfer.cookie_token != capture.transfer_token
            with pytest.raises(Exception) as replay_error:
                await ConsumePartnerAttributionTransferUseCase(adapter).execute(
                    ConsumePartnerAttributionTransferCommand(transfer_token=capture.transfer_token)
                )
            assert getattr(replay_error.value, "code", None) == "PARTNER_TRANSFER_TOKEN_CONSUMED"
            claim = await ClaimPartnerAttributionUseCase(adapter).execute(
                ClaimPartnerAttributionCommand(
                    user_id=customer.id,
                    cookie_token=transfer.cookie_token,
                    current_realm=current_realm,
                )
            )

            assert claim.status == "claimed"
            assert claim.partner_account_id == account.id
            assert claim.partner_code_id == code.id
            assert claim.binding_id is not None

            binding = db.get(CustomerCommercialBindingModel, claim.binding_id)
            assert binding is not None
            assert binding.binding_type == "partner_attribution"
            assert binding.owner_type == "affiliate"
            assert binding.partner_account_id == account.id
            assert binding.partner_code_id == code.id
            assert binding.attribution_session_id == capture.attribution_id
            assert binding.claimed_at is not None
            assert binding.storefront_id == code.default_storefront_id
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


def test_partner_code_owner_type_is_not_inferred_from_partner_account_id() -> None:
    code = PartnerCodeModel(
        id=uuid.uuid4(),
        code="ACCOUNTED",
        partner_account_id=uuid.uuid4(),
        partner_user_id=None,
        markup_pct=0,
        is_active=True,
        owner_type="affiliate",
    )

    assert _infer_owner_type_from_code(code) == "affiliate"
