from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.referrals.attribution import (
    CaptureReferralAttributionCommand,
    CaptureReferralAttributionUseCase,
    ClaimReferralAttributionCommand,
    ClaimReferralAttributionUseCase,
    ReferralAttributionError,
)
from src.config import settings
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _enable_referrals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "referral_enabled", True)


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


def _user(*, realm_id: uuid.UUID, email: str, referral_code: str | None = None) -> MobileUserModel:
    return MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=realm_id,
        email=email,
        password_hash="hashed-password",
        referral_code=referral_code,
        is_active=True,
        status="active",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_referral_attribution_capture_then_claim_sets_immutable_user_binding() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            referrer = _user(realm_id=realm.id, email="referrer@example.test", referral_code="CYBER42")
            referred = _user(realm_id=realm.id, email="referred@example.test")
            db.add_all([realm, referrer, referred])
            db.commit()

            adapter = SyncSessionAdapter(db)
            current_realm = RealmResolution(auth_realm=realm, source="test")
            capture = await CaptureReferralAttributionUseCase(adapter).execute(
                CaptureReferralAttributionCommand(
                    referral_code="cyber42",
                    source_host="cyber-vpn.net",
                    source_path="/ru-RU/register",
                    campaign_params={"utm_source": "share"},
                    existing_cookie_token=None,
                    current_realm=current_realm,
                )
            )
            assert capture.set_cookie_token is not None

            claim = await ClaimReferralAttributionUseCase(adapter).execute(
                ClaimReferralAttributionCommand(
                    user_id=referred.id,
                    cookie_token=capture.set_cookie_token,
                    fallback_referral_code=None,
                    current_realm=current_realm,
                )
            )

            assert claim.status == "claimed"
            assert claim.referrer_user_id == referrer.id
            assert claim.clear_cookie is True
            assert referred.referred_by_user_id == referrer.id
            assert referred.referral_claimed_at is not None
            assert referred.referral_source_code_id is not None
            assert referred.referral_attribution_session_id == capture.attribution_id
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_referral_attribution_blocks_self_referral() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            referrer = _user(realm_id=realm.id, email="self@example.test", referral_code="SELF42")
            db.add_all([realm, referrer])
            db.commit()

            adapter = SyncSessionAdapter(db)
            current_realm = RealmResolution(auth_realm=realm, source="test")
            capture = await CaptureReferralAttributionUseCase(adapter).execute(
                CaptureReferralAttributionCommand(
                    referral_code="SELF42",
                    source_host="cyber-vpn.net",
                    source_path="/ru-RU/register",
                    campaign_params={},
                    existing_cookie_token=None,
                    current_realm=current_realm,
                )
            )

            with pytest.raises(ReferralAttributionError) as exc:
                await ClaimReferralAttributionUseCase(adapter).execute(
                    ClaimReferralAttributionCommand(
                        user_id=referrer.id,
                        cookie_token=capture.set_cookie_token,
                        fallback_referral_code=None,
                        current_realm=current_realm,
                    )
                )

            assert exc.value.code == "REFERRAL_SELF_ATTRIBUTION_BLOCKED"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_referral_attribution_blocks_partner_owned_customer() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            referrer = _user(realm_id=realm.id, email="owner@example.test", referral_code="PART42")
            partner_owned = _user(realm_id=realm.id, email="partner-owned@example.test")
            partner_owned.partner_user_id = referrer.id
            db.add_all([realm, referrer, partner_owned])
            db.commit()

            adapter = SyncSessionAdapter(db)
            current_realm = RealmResolution(auth_realm=realm, source="test")

            with pytest.raises(ReferralAttributionError) as exc:
                await ClaimReferralAttributionUseCase(adapter).execute(
                    ClaimReferralAttributionCommand(
                        user_id=partner_owned.id,
                        cookie_token=None,
                        fallback_referral_code="PART42",
                        current_realm=current_realm,
                    )
                )

            assert exc.value.code == "REFERRAL_PARTNER_ATTRIBUTION_CONFLICT"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
