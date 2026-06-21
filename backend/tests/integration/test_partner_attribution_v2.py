from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from prometheus_client import REGISTRY

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
    PartnerAttributionError,
)
from src.application.use_cases.partner_attribution.utils import (
    build_public_token_for_code_id,
    hash_partner_attribution_token,
)
from src.config import settings
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_attribution_session_model import PartnerAttributionSessionModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeLinkModel, PartnerCodeModel
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
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    monkeypatch.setattr(settings, "partner_deterministic_public_token_fallback_enabled", True)


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


def _legacy_public_token_metric(*, source: str, result: str) -> float:
    return (
        REGISTRY.get_sample_value(
            "partner_attribution_legacy_public_token_total",
            {"source": source, "result": result},
        )
        or 0.0
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
                allowed_channels=["content", "partner-newsletter"],
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
                    capture_idempotency_key="capture-idempotency-1",
                    campaign_params={"utm_source": "creator"},
                    current_realm=current_realm,
                )
            )
            duplicate_capture = await CapturePartnerAttributionUseCase(adapter).execute(
                CapturePartnerAttributionCommand(
                    public_token=build_public_token_for_code_id(code.id),
                    source_host="cyber-vpn.net",
                    source_path="/p/demo?utm_source=creator",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={"creator": "demo"},
                    click_id="click-123",
                    browser_key="browser-abc",
                    capture_idempotency_key="capture-idempotency-1",
                    campaign_params={"utm_source": "creator"},
                    current_realm=current_realm,
                )
            )
            assert duplicate_capture.attribution_id == capture.attribution_id
            assert duplicate_capture.transfer_token == capture.transfer_token
            assert db.query(PartnerAttributionSessionModel).count() == 1
            assert db.query(AttributionTouchpointModel).count() == 1

            transfer = await ConsumePartnerAttributionTransferUseCase(adapter).execute(
                ConsumePartnerAttributionTransferCommand(transfer_token=capture.transfer_token)
            )
            assert transfer.cookie_token != capture.transfer_token
            stored_capture = db.get(PartnerAttributionSessionModel, capture.attribution_id)
            assert stored_capture is not None
            assert stored_capture.policy_snapshot["allowed"] is True
            assert stored_capture.policy_snapshot["reason_codes"] == []
            assert stored_capture.policy_snapshot["evaluated_sale_channel"] == "content"
            assert stored_capture.transfer_token_hash is None
            assert stored_capture.consumed_transfer_token_hash is not None
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


@pytest.mark.asyncio
async def test_partner_attribution_capture_uses_persisted_link_snapshot() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-link-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="link-partner",
                display_name="Link Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="LINK42",
                code_normalized="LINK42",
                public_slug="code-level-link42",
                public_token_hash=hash_partner_attribution_token("code-level-link42"),
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
                allowed_channels=["content", "partner-newsletter"],
                allowed_storefront_ids=["*"],
                allowed_geographies=["*"],
                sub_id_schema={},
            )
            link = PartnerCodeLinkModel(
                id=uuid.uuid4(),
                public_slug="link-snapshot-token",
                partner_code_id=code.id,
                partner_account_id=account.id,
                link_kind="deep_link",
                destination_key="pricing",
                destination_path="/pricing",
                locale="en-EN",
                sale_channel="partner-newsletter",
                campaign_params={"utm_source": "persisted"},
                sub_ids={"creator": "persisted"},
                status="active",
            )
            db.add_all([realm, partner_owner, account, code, link])
            db.commit()

            adapter = SyncSessionAdapter(db)
            capture = await CapturePartnerAttributionUseCase(adapter).execute(
                CapturePartnerAttributionCommand(
                    public_token=link.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/link-snapshot-token?destination=download&utm_source=tampered&sub_creator=tampered",
                    destination_path="/download",
                    locale="ru-RU",
                    sale_channel="tampered-channel",
                    sub_ids={"creator": "tampered"},
                    click_id="click-123",
                    browser_key="browser-link-snapshot",
                    capture_idempotency_key="capture-link-snapshot",
                    campaign_params={"utm_source": "tampered"},
                    current_realm=RealmResolution(auth_realm=realm, source="test"),
                )
            )

            stored_capture = db.get(PartnerAttributionSessionModel, capture.attribution_id)
            assert stored_capture is not None
            assert stored_capture.partner_code_link_id == link.id
            assert stored_capture.destination_path == "/pricing"
            assert stored_capture.locale == "en-EN"
            assert stored_capture.sale_channel == "partner-newsletter"
            assert stored_capture.campaign_params == {"utm_source": "persisted"}
            assert stored_capture.sub_ids == {"creator": "persisted"}
            assert stored_capture.evidence_payload["public_token_source"] == "partner_code_link"
            assert stored_capture.evidence_payload["partner_code_link_id"] == str(link.id)
            assert "/en-EN/pricing" in capture.redirect_url
            assert "/download" not in capture.redirect_url
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_legacy_code_slug_is_flagged_and_observed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-code-slug-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="code-slug-partner",
                display_name="Code Slug Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="CODESLUG42",
                code_normalized="CODESLUG42",
                public_slug="legacy-code-slug-token",
                public_token_hash=hash_partner_attribution_token("legacy-code-slug-token"),
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
            db.add_all([realm, partner_owner, account, code])
            db.commit()

            before = _legacy_public_token_metric(source="code_public_slug", result="resolved")
            caplog.set_level(logging.WARNING, logger="src.application.use_cases.partner_attribution.attribution")
            capture = await CapturePartnerAttributionUseCase(SyncSessionAdapter(db)).execute(
                CapturePartnerAttributionCommand(
                    public_token=code.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/legacy-code-slug-token",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    click_id=None,
                    browser_key="browser-code-slug-legacy",
                    capture_idempotency_key="capture-code-slug-legacy",
                    campaign_params={},
                    current_realm=RealmResolution(auth_realm=realm, source="test"),
                )
            )

            stored_capture = db.get(PartnerAttributionSessionModel, capture.attribution_id)
            assert stored_capture is not None
            assert stored_capture.partner_code_id == code.id
            assert stored_capture.partner_code_link_id is None
            assert stored_capture.evidence_payload["public_token_source"] == "partner_code_public_slug_legacy"
            assert _legacy_public_token_metric(source="code_public_slug", result="resolved") == before + 1
            assert "partner_attribution_legacy_public_token_resolved" in caplog.text
            assert code.public_slug not in caplog.text
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_deterministic_legacy_token_is_flagged_observed_and_backfilled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-deterministic-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="deterministic-partner",
                display_name="Deterministic Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="DETERMINISTIC42",
                code_normalized="DETERMINISTIC42",
                public_slug=None,
                public_token_hash=None,
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
            db.add_all([realm, partner_owner, account, code])
            db.commit()

            token = build_public_token_for_code_id(code.id)
            before = _legacy_public_token_metric(source="deterministic_px", result="resolved")
            caplog.set_level(logging.WARNING, logger="src.application.use_cases.partner_attribution.attribution")
            capture = await CapturePartnerAttributionUseCase(SyncSessionAdapter(db)).execute(
                CapturePartnerAttributionCommand(
                    public_token=token,
                    source_host="cyber-vpn.net",
                    source_path="/p/legacy-deterministic",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    click_id=None,
                    browser_key="browser-deterministic-legacy",
                    capture_idempotency_key="capture-deterministic-legacy",
                    campaign_params={},
                    current_realm=RealmResolution(auth_realm=realm, source="test"),
                )
            )

            stored_capture = db.get(PartnerAttributionSessionModel, capture.attribution_id)
            db.refresh(code)
            assert stored_capture is not None
            assert stored_capture.partner_code_id == code.id
            assert stored_capture.partner_code_link_id is None
            assert stored_capture.evidence_payload["public_token_source"] == "partner_code_deterministic_legacy"
            assert code.public_slug == token
            assert code.public_token_hash == hash_partner_attribution_token(token)
            assert _legacy_public_token_metric(source="deterministic_px", result="resolved") == before + 1
            assert "partner_attribution_legacy_public_token_resolved" in caplog.text
            assert token not in caplog.text
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_deterministic_legacy_token_disabled_creates_no_session(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(settings, "partner_deterministic_public_token_fallback_enabled", False)
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-disabled-deterministic-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="disabled-deterministic-partner",
                display_name="Disabled Deterministic Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="DISABLEDDETERMINISTIC42",
                code_normalized="DISABLEDDETERMINISTIC42",
                public_slug=None,
                public_token_hash=None,
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
            db.add_all([realm, partner_owner, account, code])
            db.commit()

            token = build_public_token_for_code_id(code.id)
            before = _legacy_public_token_metric(source="deterministic_px", result="disabled")
            caplog.set_level(logging.WARNING, logger="src.application.use_cases.partner_attribution.attribution")
            with pytest.raises(PartnerAttributionError) as exc_info:
                await CapturePartnerAttributionUseCase(SyncSessionAdapter(db)).execute(
                    CapturePartnerAttributionCommand(
                        public_token=token,
                        source_host="cyber-vpn.net",
                        source_path="/p/legacy-deterministic-disabled",
                        destination_path="/pricing",
                        locale="ru-RU",
                        sale_channel="content",
                        sub_ids={},
                        click_id=None,
                        browser_key="browser-deterministic-disabled",
                        capture_idempotency_key="capture-deterministic-disabled",
                        campaign_params={},
                        current_realm=RealmResolution(auth_realm=realm, source="test"),
                    )
                )

            assert exc_info.value.code == "PARTNER_LEGACY_PUBLIC_TOKEN_DISABLED"
            assert exc_info.value.status_code == 410
            assert db.query(PartnerAttributionSessionModel).count() == 0
            db.refresh(code)
            assert code.public_slug is None
            assert code.public_token_hash is None
            assert _legacy_public_token_metric(source="deterministic_px", result="disabled") == before + 1
            assert "partner_attribution_legacy_public_token_disabled" in caplog.text
            assert token not in caplog.text
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_legacy_code_slug_flag_does_not_disable_persisted_links(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", False)
    monkeypatch.setattr(settings, "partner_deterministic_public_token_fallback_enabled", False)
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-link-no-legacy-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="link-no-legacy-partner",
                display_name="Link No Legacy Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="NOLEGACY42",
                code_normalized="NOLEGACY42",
                public_slug="legacy-code-level-token",
                public_token_hash=hash_partner_attribution_token("legacy-code-level-token"),
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
            link = PartnerCodeLinkModel(
                id=uuid.uuid4(),
                public_slug="persisted-link-token-no-legacy",
                partner_code_id=code.id,
                partner_account_id=account.id,
                link_kind="deep_link",
                destination_key="pricing",
                destination_path="/pricing",
                campaign_params={"utm_source": "persisted"},
                sub_ids={"creator": "persisted"},
                status="active",
            )
            db.add_all([realm, partner_owner, account, code, link])
            db.commit()

            adapter = SyncSessionAdapter(db)
            link_capture = await CapturePartnerAttributionUseCase(adapter).execute(
                CapturePartnerAttributionCommand(
                    public_token=link.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/persisted-link-token-no-legacy",
                    destination_path="/download",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    click_id=None,
                    browser_key="browser-link-no-legacy",
                    capture_idempotency_key="capture-link-no-legacy",
                    campaign_params={},
                    current_realm=RealmResolution(auth_realm=realm, source="test"),
                )
            )
            stored_link_capture = db.get(PartnerAttributionSessionModel, link_capture.attribution_id)
            assert stored_link_capture is not None
            assert stored_link_capture.partner_code_link_id == link.id
            assert stored_link_capture.evidence_payload["public_token_source"] == "partner_code_link"

            before = _legacy_public_token_metric(source="code_public_slug", result="disabled")
            caplog.set_level(logging.WARNING, logger="src.application.use_cases.partner_attribution.attribution")
            with pytest.raises(PartnerAttributionError) as exc_info:
                await CapturePartnerAttributionUseCase(adapter).execute(
                    CapturePartnerAttributionCommand(
                        public_token=code.public_slug,
                        source_host="cyber-vpn.net",
                        source_path="/p/legacy-code-level-token",
                        destination_path="/pricing",
                        locale="ru-RU",
                        sale_channel="content",
                        sub_ids={},
                        click_id=None,
                        browser_key="browser-code-level-disabled",
                        capture_idempotency_key="capture-code-level-disabled",
                        campaign_params={},
                        current_realm=RealmResolution(auth_realm=realm, source="test"),
                    )
                )
            assert exc_info.value.code == "PARTNER_LEGACY_PUBLIC_TOKEN_DISABLED"
            assert exc_info.value.status_code == 410
            assert _legacy_public_token_metric(source="code_public_slug", result="disabled") == before + 1
            assert "partner_attribution_legacy_public_token_disabled" in caplog.text
            assert code.public_slug not in caplog.text
            assert db.query(PartnerAttributionSessionModel).count() == 1
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_capture_rejects_expired_link() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-expired-link-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="expired-link-partner",
                display_name="Expired Link Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="EXPIRED42",
                code_normalized="EXPIRED42",
                public_slug="code-level-expired42",
                public_token_hash=hash_partner_attribution_token("code-level-expired42"),
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
            link = PartnerCodeLinkModel(
                id=uuid.uuid4(),
                public_slug="expired-link-token",
                partner_code_id=code.id,
                partner_account_id=account.id,
                link_kind="deep_link",
                destination_key="pricing",
                destination_path="/pricing",
                campaign_params={},
                sub_ids={},
                status="active",
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
            db.add_all([realm, partner_owner, account, code, link])
            db.commit()

            adapter = SyncSessionAdapter(db)
            with pytest.raises(PartnerAttributionError) as exc_info:
                await CapturePartnerAttributionUseCase(adapter).execute(
                    CapturePartnerAttributionCommand(
                        public_token=link.public_slug,
                        source_host="cyber-vpn.net",
                        source_path="/p/expired-link-token",
                        destination_path="/download",
                        locale="ru-RU",
                        sale_channel="content",
                        sub_ids={},
                        click_id=None,
                        browser_key="browser-expired-link",
                        capture_idempotency_key="capture-expired-link",
                        campaign_params={},
                        current_realm=RealmResolution(auth_realm=realm, source="test"),
                    )
                )

            assert exc_info.value.code == "PARTNER_CODE_LINK_EXPIRED"
            assert exc_info.value.status_code == 410
            assert db.query(PartnerAttributionSessionModel).count() == 0
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_capture_rejects_disallowed_channel_policy() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-channel-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="channel-policy-partner",
                display_name="Channel Policy Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="CHANNEL42",
                code_normalized="CHANNEL42",
                public_slug="channel-policy-token",
                public_token_hash=hash_partner_attribution_token("channel-policy-token"),
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
                allowed_channels=["partner_blog"],
                allowed_storefront_ids=["*"],
                allowed_geographies=["*"],
                sub_id_schema={},
            )
            db.add_all([realm, partner_owner, account, code])
            db.commit()

            with pytest.raises(PartnerAttributionError) as exc_info:
                await CapturePartnerAttributionUseCase(SyncSessionAdapter(db)).execute(
                    CapturePartnerAttributionCommand(
                        public_token=code.public_slug,
                        source_host="cyber-vpn.net",
                        source_path="/p/channel-policy-token",
                        destination_path="/pricing",
                        locale="ru-RU",
                        sale_channel="content",
                        sub_ids={},
                        click_id=None,
                        browser_key="browser-channel-policy",
                        capture_idempotency_key="capture-channel-policy",
                        campaign_params={},
                        current_realm=RealmResolution(auth_realm=realm, source="test"),
                    )
                )

            assert exc_info.value.code == "PARTNER_CODE_CHANNEL_NOT_ALLOWED"
            assert exc_info.value.status_code == 409
            assert db.query(PartnerAttributionSessionModel).count() == 0
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_claim_rejects_revoked_link_after_transfer() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-revoked-link-owner@example.test")
            customer = _user(realm_id=realm.id, email="customer-revoked-link@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="revoked-link-partner",
                display_name="Revoked Link Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="REVOKED42",
                code_normalized="REVOKED42",
                public_slug="code-level-revoked42",
                public_token_hash=hash_partner_attribution_token("code-level-revoked42"),
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
            link = PartnerCodeLinkModel(
                id=uuid.uuid4(),
                public_slug="revoked-link-token",
                partner_code_id=code.id,
                partner_account_id=account.id,
                link_kind="deep_link",
                destination_key="pricing",
                destination_path="/pricing",
                campaign_params={},
                sub_ids={},
                sale_channel="content",
                status="active",
            )
            db.add_all([realm, partner_owner, customer, account, code, link])
            db.commit()

            adapter = SyncSessionAdapter(db)
            current_realm = RealmResolution(auth_realm=realm, source="test")
            capture = await CapturePartnerAttributionUseCase(adapter).execute(
                CapturePartnerAttributionCommand(
                    public_token=link.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/revoked-link-token",
                    destination_path="/download",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    click_id=None,
                    browser_key="browser-revoked-link",
                    capture_idempotency_key="capture-revoked-link",
                    campaign_params={},
                    current_realm=current_realm,
                )
            )
            transfer = await ConsumePartnerAttributionTransferUseCase(adapter).execute(
                ConsumePartnerAttributionTransferCommand(transfer_token=capture.transfer_token)
            )
            link.status = "archived"
            db.commit()

            with pytest.raises(PartnerAttributionError) as exc_info:
                await ClaimPartnerAttributionUseCase(adapter).execute(
                    ClaimPartnerAttributionCommand(
                        user_id=customer.id,
                        cookie_token=transfer.cookie_token,
                        current_realm=current_realm,
                    )
                )

            assert exc_info.value.code == "PARTNER_CODE_LINK_NOT_ACTIVE"
            assert exc_info.value.status_code == 409
            assert db.query(CustomerCommercialBindingModel).count() == 0
            stored_capture = db.get(PartnerAttributionSessionModel, capture.attribution_id)
            assert stored_capture is not None
            assert stored_capture.status == "transferred"
            assert stored_capture.binding_id is None
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_transfer_rejects_revoked_link_before_cookie_issue() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            realm = _realm()
            partner_owner = _user(realm_id=realm.id, email="partner-transfer-revoked-link-owner@example.test")
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key="transfer-revoked-link-partner",
                display_name="Transfer Revoked Link Partner",
                status="active",
                legacy_owner_user_id=partner_owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code="TRREVOKE42",
                code_normalized="TRREVOKE42",
                public_slug="code-level-transfer-revoked42",
                public_token_hash=hash_partner_attribution_token("code-level-transfer-revoked42"),
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
            link = PartnerCodeLinkModel(
                id=uuid.uuid4(),
                public_slug="transfer-revoked-link-token",
                partner_code_id=code.id,
                partner_account_id=account.id,
                link_kind="deep_link",
                destination_key="pricing",
                destination_path="/pricing",
                campaign_params={},
                sub_ids={},
                sale_channel="content",
                status="active",
            )
            db.add_all([realm, partner_owner, account, code, link])
            db.commit()

            adapter = SyncSessionAdapter(db)
            capture = await CapturePartnerAttributionUseCase(adapter).execute(
                CapturePartnerAttributionCommand(
                    public_token=link.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/transfer-revoked-link-token",
                    destination_path="/download",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    click_id=None,
                    browser_key="browser-transfer-revoked-link",
                    capture_idempotency_key="capture-transfer-revoked-link",
                    campaign_params={},
                    current_realm=RealmResolution(auth_realm=realm, source="test"),
                )
            )
            link.status = "archived"
            db.commit()

            with pytest.raises(PartnerAttributionError) as exc_info:
                await ConsumePartnerAttributionTransferUseCase(adapter).execute(
                    ConsumePartnerAttributionTransferCommand(transfer_token=capture.transfer_token)
                )

            assert exc_info.value.code == "PARTNER_CODE_LINK_NOT_ACTIVE"
            assert exc_info.value.status_code == 409
            stored_capture = db.get(PartnerAttributionSessionModel, capture.attribution_id)
            assert stored_capture is not None
            assert stored_capture.status == "pending"
            assert stored_capture.session_token_hash is None
            assert stored_capture.transfer_token_hash is not None
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
