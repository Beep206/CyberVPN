from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.services.config_service import MiniAppRuntimeConfig
from src.application.use_cases.trial.stage1_trial_policy import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_DURATION_DAYS,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
)
from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.presentation.api.v1.miniapp import routes as miniapp_routes
from src.presentation.api.v1.miniapp.routes import (
    _build_primary_cta,
    _build_usage_snapshot,
    _has_canonical_service_config,
    _is_rtl_locale,
    activate_miniapp_trial,
    commit_miniapp_checkout,
    get_miniapp_config,
    get_miniapp_offers,
    get_miniapp_payment_status,
    quote_miniapp_checkout,
)


async def _default_rollout_config(_db=None) -> MiniAppRuntimeConfig:
    return MiniAppRuntimeConfig()


def _customer_realm() -> SimpleNamespace:
    return SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4()))


class _ScalarResult:
    def __init__(self, value: object | None, *, duplicate: bool = False) -> None:
        self._value = value
        self._duplicate = duplicate

    def scalars(self):
        return self

    def all(self) -> list[object]:
        if self._value is None:
            return []
        return [self._value, self._value] if self._duplicate else [self._value]


class _ReconciliationDb:
    def __init__(self, reconciliation: object | None, *, duplicate: bool = False) -> None:
        self._reconciliation = reconciliation
        self._duplicate = duplicate

    async def execute(self, _statement) -> _ScalarResult:
        return _ScalarResult(self._reconciliation, duplicate=self._duplicate)


def _mapped_reconciliation(
    *,
    subject_id,
    numeric_id: int,
    legacy_uuid,
    state: str = "mapped",
) -> SimpleNamespace:
    return SimpleNamespace(
        subject_type="mobile_user",
        subject_id=subject_id,
        reconciliation_state=state,
        numeric_user_id=numeric_id,
        legacy_uuid=str(legacy_uuid),
    )


def test_build_primary_cta_prefers_trial_for_new_users() -> None:
    cta = _build_primary_cta(subscription_status="none", trial_eligible=True, has_config=False)

    assert cta.kind == "start_trial"
    assert cta.label == "Start trial"


def test_build_primary_cta_uses_select_server_for_active_users_with_config() -> None:
    cta = _build_primary_cta(subscription_status="active", trial_eligible=False, has_config=True)

    assert cta.kind == "select_server"


def test_bootstrap_config_readiness_ignores_legacy_url_without_canonical_state() -> None:
    has_config = _has_canonical_service_config(
        legacy_subscription_url="https://legacy.example/must-not-enable-config",
        selected_service_state=None,
        current_service_state=None,
    )
    cta = _build_primary_cta(subscription_status="active", trial_eligible=False, has_config=has_config)

    assert has_config is False
    assert cta.kind == "get_config"


@pytest.mark.parametrize("canonical_field", ["service_identity", "access_delivery_channel"])
def test_bootstrap_config_readiness_accepts_canonical_service_state(canonical_field: str) -> None:
    state = SimpleNamespace(
        service_identity=object() if canonical_field == "service_identity" else None,
        access_delivery_channel=object() if canonical_field == "access_delivery_channel" else None,
    )

    assert (
        _has_canonical_service_config(
            legacy_subscription_url="https://legacy.example/cache-is-not-authoritative",
            selected_service_state=state,
            current_service_state=None,
        )
        is True
    )


def test_rtl_locale_detection_supports_telegram_locales() -> None:
    assert _is_rtl_locale("fa-IR") is True
    assert _is_rtl_locale("he-IL") is True
    assert _is_rtl_locale("en-EN") is False


def test_evaluate_miniapp_runtime_access_allows_live_runtime() -> None:
    decision = miniapp_routes._evaluate_miniapp_runtime_access(
        MiniAppRuntimeConfig(),
        feature="checkout",
        telegram_user_id=123456789,
    )

    assert decision.allowed is True
    assert decision.is_canary_user is False
    assert decision.gate_reason_code is None


def test_evaluate_miniapp_runtime_access_blocks_non_allowlisted_canary_user() -> None:
    decision = miniapp_routes._evaluate_miniapp_runtime_access(
        MiniAppRuntimeConfig(
            mode="canary",
            canary_telegram_user_ids=(111111111,),
        ),
        feature="checkout",
        telegram_user_id=222222222,
    )

    assert decision.allowed is False
    assert decision.is_canary_user is False
    assert decision.gate_reason_code == "canary_not_allowed"


def test_evaluate_miniapp_runtime_access_blocks_checkout_during_rollback() -> None:
    decision = miniapp_routes._evaluate_miniapp_runtime_access(
        MiniAppRuntimeConfig(mode="rollback"),
        feature="checkout",
        telegram_user_id=123456789,
    )

    assert decision.allowed is False
    assert decision.gate_reason_code == "rollback"


def test_evaluate_miniapp_runtime_access_allows_config_during_rollback() -> None:
    decision = miniapp_routes._evaluate_miniapp_runtime_access(
        MiniAppRuntimeConfig(mode="rollback"),
        feature="config",
        telegram_user_id=123456789,
    )

    assert decision.allowed is True
    assert decision.gate_reason_code is None


def test_build_usage_snapshot_maps_remnawave_user() -> None:
    remnawave_user = User(
        uuid=uuid4(),
        username="cyber",
        status=UserStatus.ACTIVE,
        short_uuid="abcd1234",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        traffic_limit_bytes=1024,
        used_traffic_bytes=512,
        hwid_device_limit=3,
        online_at=datetime(2026, 4, 22, 8, 0, tzinfo=UTC),
        last_traffic_reset_at=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        expire_at=datetime(2026, 4, 30, 0, 0, tzinfo=UTC),
    )

    usage = _build_usage_snapshot(remnawave_user)

    assert usage.usage_available is True
    assert usage.usage_source == "remnawave"
    assert usage.usage_unavailable_reason is None
    assert usage.bandwidth_used_bytes == 512
    assert usage.bandwidth_limit_bytes == 1024
    assert usage.connections_active == 1
    assert usage.connections_limit == 3
    assert usage.last_connection_at == datetime(2026, 4, 22, 8, 0, tzinfo=UTC)


def test_build_usage_snapshot_marks_missing_remnawave_user_unavailable() -> None:
    usage = _build_usage_snapshot(None)

    assert usage.usage_available is False
    assert usage.usage_source == "unavailable"
    assert usage.usage_unavailable_reason == "upstream_user_not_found"
    assert usage.bandwidth_used_bytes == 0
    assert usage.bandwidth_limit_bytes == 0
    assert usage.connections_active == 0
    assert usage.last_connection_at is None


def test_get_miniapp_offers_aggregates_catalog_and_current_state(monkeypatch) -> None:
    user_id = uuid4()
    realm = _customer_realm()

    plan = SimpleNamespace(
        id=uuid4(),
        name="plus_365",
        plan_code="plus",
        display_name="Plus",
        catalog_visibility="public",
        duration_days=365,
        traffic_limit_bytes=None,
        device_limit=5,
        price_usd=79,
        price_rub=None,
        traffic_policy={"mode": "fair_use", "display_label": "Unlimited"},
        connection_modes=["standard", "stealth"],
        server_pool=["shared_plus"],
        support_sla="standard",
        dedicated_ip={"included": 0, "eligible": True},
        sale_channels=["miniapp"],
        invite_bundle={"count": 2, "friend_days": 14, "expiry_days": 60},
        trial_eligible=False,
        features={"telegram_stars_amount": 500},
        is_active=True,
        sort_order=20,
    )
    semiannual_plan = SimpleNamespace(
        **{
            **plan.__dict__,
            "id": uuid4(),
            "name": "plus_180",
            "duration_days": 180,
            "sort_order": 19,
        }
    )
    unsupported_plan = SimpleNamespace(
        **{
            **plan.__dict__,
            "id": uuid4(),
            "name": "plus_60",
            "duration_days": 60,
            "sort_order": 18,
        }
    )
    addon = SimpleNamespace(
        id=uuid4(),
        code="extra_device",
        display_name="Extra device",
        duration_mode="inherits_subscription",
        is_stackable=True,
        quantity_step=1,
        price_usd=4,
        price_rub=None,
        max_quantity_by_plan={"plus": 3},
        delta_entitlements={"device_limit": 1},
        requires_location=False,
        sale_channels=["miniapp"],
        is_active=True,
    )

    class FakePlanRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **_kwargs):
            return [unsupported_plan, semiannual_plan, plan]

    class FakeAddonRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **_kwargs):
            return [addon]

    class FakeTrialUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, _user_id):
            return SimpleNamespace(
                is_trial_active=False,
                trial_start=None,
                trial_end=None,
                days_remaining=0,
                is_eligible=True,
            )

    class FakeEntitlementsUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, _user_id, auth_realm_id):
            return {
                "status": "none",
                "plan_uuid": None,
                "plan_code": None,
                "display_name": None,
                "period_days": None,
                "expires_at": None,
                "effective_entitlements": {},
                "invite_bundle": {},
                "is_trial": False,
                "addons": [],
                "auth_realm_id": str(auth_realm_id),
            }

    monkeypatch.setattr(miniapp_routes, "SubscriptionPlanRepository", FakePlanRepo)
    monkeypatch.setattr(miniapp_routes, "PlanAddonRepository", FakeAddonRepo)
    monkeypatch.setattr(miniapp_routes, "GetTrialStatusUseCase", FakeTrialUseCase)
    monkeypatch.setattr(miniapp_routes, "GetCurrentEntitlementsUseCase", FakeEntitlementsUseCase)
    monkeypatch.setattr(miniapp_routes.settings, "stage1_addons_enabled", False)

    response = asyncio.run(
        get_miniapp_offers(
            selected_subscription_key=None,
            db=object(),
            user_id=user_id,
            current_realm=realm,
        )
    )

    assert response.plans[0].plan_code == "plus"
    assert [offer.duration_days for offer in response.plans] == [180, 365]
    assert len(response.plans) == 2
    assert response.addons == []
    assert response.trial.is_eligible is True
    assert response.current_entitlements.status == "none"


def test_get_miniapp_config_prefers_remnawave_generated_config(monkeypatch) -> None:
    user_id = uuid4()
    remnawave_user_id = 42
    legacy_uuid = uuid4()
    realm = _customer_realm()

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _user_id):
            return SimpleNamespace(
                id=user_id,
                telegram_id=123456789,
                remnawave_user_id=remnawave_user_id,
                remnawave_uuid=str(legacy_uuid),
                subscription_url="https://legacy.example/sub",
            )

    class FakeGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            pass

        async def execute(self, user_ref):
            assert user_ref == RemnawaveUserRef(id=remnawave_user_id, legacy_uuid=legacy_uuid)
            return {
                "config": "vless://generated",
                "config_string": "vless://generated",
                "client_type": "vless",
                "is_found": True,
                "links": ["vless://generated"],
                "ss_conf_links": {},
                "subscription_url": "https://generated.example/sub",
            }

    monkeypatch.setattr(miniapp_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(miniapp_routes, "GenerateConfigUseCase", FakeGenerateConfigUseCase)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    response = asyncio.run(
        get_miniapp_config(
            selected_subscription_key=None,
            db=_ReconciliationDb(
                _mapped_reconciliation(
                    subject_id=user_id,
                    numeric_id=remnawave_user_id,
                    legacy_uuid=legacy_uuid,
                )
            ),
            user_id=user_id,
            current_realm=realm,
            remnawave_client=object(),
        )
    )

    assert response.config == "https://generated.example/sub"
    assert response.config_string == "https://generated.example/sub"
    assert response.client_type == "subscription"
    assert response.source == "remnawave_generated"
    assert response.subscription_url == "https://generated.example/sub"


@pytest.mark.parametrize(
    ("state", "mapped_numeric_id", "duplicate"),
    [
        (None, None, False),
        ("pending", 42, False),
        ("mapped", 99, False),
        ("mapped", 42, True),
    ],
)
def test_get_miniapp_config_rejects_non_exact_reconciliation_without_fallback(
    monkeypatch,
    state: str | None,
    mapped_numeric_id: int | None,
    duplicate: bool,
) -> None:
    user_id = uuid4()
    legacy_uuid = uuid4()
    realm = _customer_realm()
    reconciliation = (
        _mapped_reconciliation(
            subject_id=user_id,
            numeric_id=mapped_numeric_id,
            legacy_uuid=legacy_uuid,
            state=state,
        )
        if state is not None and mapped_numeric_id is not None
        else None
    )

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _user_id):
            return SimpleNamespace(
                id=user_id,
                telegram_id=123456789,
                remnawave_user_id=42,
                remnawave_uuid=str(legacy_uuid),
                subscription_url="https://legacy.example/must-not-leak",
            )

    class ForbiddenGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            raise AssertionError("config generation must not run for a non-exact mapping")

    monkeypatch.setattr(miniapp_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(miniapp_routes, "GenerateConfigUseCase", ForbiddenGenerateConfigUseCase)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            get_miniapp_config(
                selected_subscription_key=None,
                db=_ReconciliationDb(reconciliation, duplicate=duplicate),
                user_id=user_id,
                current_realm=realm,
                remnawave_client=object(),
            )
        )

    assert exc_info.value.status_code == 409


def test_get_miniapp_config_rejects_unmapped_legacy_subscription_url(monkeypatch) -> None:
    user_id = uuid4()
    realm = _customer_realm()

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _user_id):
            return SimpleNamespace(
                id=user_id,
                telegram_id=None,
                remnawave_user_id=None,
                remnawave_uuid=None,
                subscription_url="https://legacy.example/sub",
            )

    monkeypatch.setattr(miniapp_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            get_miniapp_config(
                selected_subscription_key=None,
                db=object(),
                user_id=user_id,
                current_realm=realm,
                remnawave_client=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_exact_remnawave_user_lookup_uses_only_numeric_id(monkeypatch) -> None:
    remnawave_uuid = uuid4()
    seen: dict[str, object] = {}

    class FakeGateway:
        def __init__(self, _client) -> None:
            pass

        async def get_by_id(self, user_id):
            seen["id"] = user_id
            return SimpleNamespace(remnawave_id=user_id, uuid=remnawave_uuid)

        async def get_by_uuid(self, _user_uuid):
            raise AssertionError("legacy UUID lookup must remain rollback-only")

        async def get_by_telegram_id(self, _telegram_id: int):
            raise AssertionError("Telegram lookup must not run after numeric cutover")

    monkeypatch.setattr(miniapp_routes, "RemnawaveUserGateway", FakeGateway)

    response = asyncio.run(
        miniapp_routes._get_exact_remnawave_user(
            client=object(),
            user_ref=RemnawaveUserRef(id=42, legacy_uuid=remnawave_uuid),
        )
    )

    assert seen["id"] == 42
    assert response.uuid == remnawave_uuid


def test_exact_remnawave_user_accepts_numeric_only_upstream_response(monkeypatch) -> None:
    legacy_uuid = uuid4()

    class FakeGateway:
        def __init__(self, _client) -> None:
            pass

        async def get_by_id(self, user_id):
            return SimpleNamespace(remnawave_id=user_id, uuid=None)

    monkeypatch.setattr(miniapp_routes, "RemnawaveUserGateway", FakeGateway)

    response = asyncio.run(
        miniapp_routes._get_exact_remnawave_user(
            client=object(),
            user_ref=RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
        )
    )

    assert response.remnawave_id == 42
    assert response.uuid is None


def test_exact_remnawave_user_rejects_present_mismatched_legacy_uuid(monkeypatch) -> None:
    class FakeGateway:
        def __init__(self, _client) -> None:
            pass

        async def get_by_id(self, user_id):
            return SimpleNamespace(remnawave_id=user_id, uuid=uuid4())

    monkeypatch.setattr(miniapp_routes, "RemnawaveUserGateway", FakeGateway)

    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            miniapp_routes._get_exact_remnawave_user(
                client=object(),
                user_ref=RemnawaveUserRef(id=42, legacy_uuid=uuid4()),
            )
        )

    assert exc_info.value.status_code == 409


@pytest.mark.parametrize(
    ("state", "mapped_numeric_id"),
    [
        (None, None),
        ("pending", 42),
        ("mapped", 99),
    ],
)
def test_exact_miniapp_identity_rejects_missing_pending_or_wrong_numeric_mapping(
    state: str | None,
    mapped_numeric_id: int | None,
) -> None:
    legacy_uuid = uuid4()
    subject_id = uuid4()
    reconciliation = (
        _mapped_reconciliation(
            subject_id=subject_id,
            numeric_id=mapped_numeric_id,
            legacy_uuid=legacy_uuid,
            state=state,
        )
        if state is not None and mapped_numeric_id is not None
        else None
    )
    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            miniapp_routes._resolve_exact_mapped_remnawave_ref(
                db=_ReconciliationDb(reconciliation),
                subject_type="mobile_user",
                subject_id=subject_id,
                numeric_user_id=42,
                legacy_uuid_raw=str(legacy_uuid),
            )
        )

    assert exc_info.value.status_code == 409


def test_exact_miniapp_identity_rejects_stale_legacy_mapping() -> None:
    subject_id = uuid4()
    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            miniapp_routes._resolve_exact_mapped_remnawave_ref(
                db=_ReconciliationDb(_mapped_reconciliation(subject_id=subject_id, numeric_id=42, legacy_uuid=uuid4())),
                subject_type="mobile_user",
                subject_id=subject_id,
                numeric_user_id=42,
                legacy_uuid_raw=str(uuid4()),
            )
        )

    assert exc_info.value.status_code == 409


def test_exact_miniapp_identity_rejects_duplicate_reconciliation_rows() -> None:
    legacy_uuid = uuid4()
    subject_id = uuid4()
    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            miniapp_routes._resolve_exact_mapped_remnawave_ref(
                db=_ReconciliationDb(
                    _mapped_reconciliation(subject_id=subject_id, numeric_id=42, legacy_uuid=legacy_uuid),
                    duplicate=True,
                ),
                subject_type="mobile_user",
                subject_id=subject_id,
                numeric_user_id=42,
                legacy_uuid_raw=str(legacy_uuid),
            )
        )

    assert exc_info.value.status_code == 409


def test_exact_remnawave_user_rejects_wrong_upstream_numeric_id(monkeypatch) -> None:
    legacy_uuid = uuid4()

    class FakeGateway:
        def __init__(self, _client) -> None:
            pass

        async def get_by_id(self, _user_id):
            return SimpleNamespace(remnawave_id=99, uuid=legacy_uuid)

    monkeypatch.setattr(miniapp_routes, "RemnawaveUserGateway", FakeGateway)

    with pytest.raises(miniapp_routes.HTTPException) as exc_info:
        asyncio.run(
            miniapp_routes._get_exact_remnawave_user(
                client=object(),
                user_ref=RemnawaveUserRef(id=42, legacy_uuid=legacy_uuid),
            )
        )

    assert exc_info.value.status_code == 409


def test_quote_miniapp_checkout_uses_surface_specific_flow(monkeypatch) -> None:
    user_id = uuid4()
    grant_id = uuid4()
    realm = _customer_realm()
    request = miniapp_routes.MiniAppCheckoutRequest(
        flow="checkout",
        plan_id=uuid4(),
        addons=[],
        code_input="SAVE20",
        promo_code=None,
        private_catalog_grant_id=grant_id,
        use_wallet=0,
        currency="USD",
    )

    async def fake_build_quote(*, body, db, user_id):
        assert body.channel == "miniapp"
        assert body.private_catalog_grant_id == grant_id
        assert user_id
        return SimpleNamespace(displayed_price=79)

    def fake_serialize(result):
        assert result.displayed_price == 79
        return SimpleNamespace(displayed_price=79)

    monkeypatch.setattr(miniapp_routes, "_build_base_checkout_quote", fake_build_quote)
    monkeypatch.setattr(miniapp_routes, "_serialize_base_checkout_quote", fake_serialize)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    response = asyncio.run(
        quote_miniapp_checkout(
            body=request,
            db=object(),
            user_id=user_id,
            current_realm=realm,
        )
    )

    assert response.displayed_price == 79


def test_miniapp_checkout_request_accepts_snake_and_camel_private_grant() -> None:
    snake_grant_id = uuid4()
    camel_grant_id = uuid4()

    snake = miniapp_routes.MiniAppCheckoutRequest.model_validate(
        {
            "flow": "checkout",
            "planId": str(uuid4()),
            "private_catalog_grant_id": str(snake_grant_id),
            "useWallet": 0,
            "currency": "USD",
        }
    )
    camel = miniapp_routes.MiniAppCheckoutRequest.model_validate(
        {
            "flow": "checkout",
            "planId": str(uuid4()),
            "privateCatalogGrantId": str(camel_grant_id),
            "useWallet": 0,
            "currency": "USD",
        }
    )

    assert snake.private_catalog_grant_id == snake_grant_id
    assert camel.private_catalog_grant_id == camel_grant_id


def test_commit_miniapp_checkout_forwards_private_catalog_grant(monkeypatch) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    grant_id = uuid4()
    payment_id = uuid4()
    realm = _customer_realm()
    request = miniapp_routes.MiniAppCheckoutRequest(
        flow="checkout",
        plan_id=plan_id,
        addons=[],
        code_input=None,
        promo_code=None,
        private_catalog_grant_id=grant_id,
        use_wallet=0,
        currency="USD",
    )

    async def fake_build_quote(*, body, db, user_id):
        assert body.channel == "miniapp"
        assert body.plan_id == plan_id
        assert body.private_catalog_grant_id == grant_id
        assert user_id
        return SimpleNamespace(plan_id=plan_id, plan_name="Private Plan", duration_days=30, is_zero_gateway=False)

    def fake_serialize(_result):
        return SimpleNamespace(model_dump=lambda: {"displayed_price": 79})

    class FakeCommitCheckoutUseCase:
        def __init__(self, db, crypto_client) -> None:
            self.db = db
            self.crypto_client = crypto_client

        async def execute(self, **kwargs):
            assert kwargs["idempotency_key"] == "miniapp-private-grant"
            return SimpleNamespace(payment=SimpleNamespace(id=payment_id), status="pending", invoice=None)

    async def fake_resolve_telegram_user_id(**_kwargs):
        return 123456789

    monkeypatch.setattr(miniapp_routes, "require_stage1_payments_enabled", lambda: None)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)
    monkeypatch.setattr(miniapp_routes, "_resolve_miniapp_runtime_telegram_user_id", fake_resolve_telegram_user_id)
    monkeypatch.setattr(miniapp_routes, "_build_base_checkout_quote", fake_build_quote)
    monkeypatch.setattr(miniapp_routes, "_serialize_base_checkout_quote", fake_serialize)
    monkeypatch.setattr(miniapp_routes, "CommitCheckoutUseCase", FakeCommitCheckoutUseCase)
    monkeypatch.setattr(miniapp_routes, "MiniAppCheckoutCommitResponse", lambda **kwargs: SimpleNamespace(**kwargs))

    response = asyncio.run(
        commit_miniapp_checkout(
            body=request,
            db=object(),
            user_id=user_id,
            current_realm=realm,
            crypto_client=object(),
            idempotency_key="miniapp-private-grant",
        )
    )

    assert response.payment_id == payment_id
    assert response.status == "pending"


def test_activate_miniapp_trial_preserves_rate_limit_and_activation(monkeypatch) -> None:
    user_id = uuid4()
    provisioning_gateway = object()

    class FakePipeline:
        async def incr(self, _key):
            return self

        async def expire(self, _key, _ttl):
            return self

        async def execute(self):
            return None

    class FakeRedis:
        async def get(self, _key):
            return None

        async def ttl(self, _key):
            return 0

        def pipeline(self):
            return FakePipeline()

    class FakeActivateTrialUseCase:
        def __init__(self, _db, provisioning_gateway=None) -> None:
            self.provisioning_gateway = provisioning_gateway

        async def execute(self, _user_id):
            assert self.provisioning_gateway is provisioning_gateway
            return SimpleNamespace(
                activated=True,
                trial_end=datetime(2026, 4, 29, 0, 0, tzinfo=UTC),
                message="Trial activated successfully.",
            )

    tracked = {"called": False}

    def fake_track_trial_activation():
        tracked["called"] = True

    monkeypatch.setattr(miniapp_routes, "ActivateTrialUseCase", FakeActivateTrialUseCase)
    monkeypatch.setattr(miniapp_routes, "track_trial_activation", fake_track_trial_activation)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    response = asyncio.run(
        activate_miniapp_trial(
            db=object(),
            user_id=user_id,
            redis_client=FakeRedis(),
            provisioning_gateway=provisioning_gateway,
        )
    )

    assert response.activated is True
    assert response.duration_days == STAGE1_TRIAL_DURATION_DAYS
    assert response.device_limit == STAGE1_TRIAL_DEVICE_LIMIT
    assert response.traffic_limit_bytes == STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    assert tracked["called"] is True


def test_get_miniapp_payment_status_scopes_to_authenticated_user(monkeypatch) -> None:
    user_id = uuid4()
    payment_id = uuid4()

    class FakePaymentRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _payment_id):
            assert _payment_id == payment_id
            return SimpleNamespace(
                id=payment_id,
                user_uuid=user_id,
                status="completed",
                provider="telegram_stars",
                external_id="charge-1",
                amount=500,
                currency="XTR",
                created_at=datetime(2026, 4, 22, 10, 0, tzinfo=UTC),
                updated_at=datetime(2026, 4, 22, 10, 1, tzinfo=UTC),
            )

    monkeypatch.setattr(miniapp_routes, "PaymentRepository", FakePaymentRepo)

    response = asyncio.run(
        get_miniapp_payment_status(
            payment_id=payment_id,
            db=object(),
            user_id=user_id,
        )
    )

    assert str(response.payment_id) == str(payment_id)
    assert response.status == "completed"
    assert response.provider == "telegram_stars"


def test_activate_miniapp_trial_returns_503_when_trial_gate_disabled(monkeypatch) -> None:
    user_id = uuid4()

    class FakeRedis:
        async def get(self, _key):
            return None

        async def ttl(self, _key):
            return 0

        def pipeline(self):
            raise AssertionError("pipeline should not be used when gate is disabled")

    async def fake_rollout(_db=None) -> MiniAppRuntimeConfig:
        return MiniAppRuntimeConfig(enabled=True, trial_enabled=False, maintenance_message="Trial paused")

    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", fake_rollout)

    try:
        asyncio.run(
            activate_miniapp_trial(
                db=object(),
                user_id=user_id,
                redis_client=FakeRedis(),
                provisioning_gateway=None,
            )
        )
    except miniapp_routes.HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Trial paused"
    else:
        raise AssertionError("Expected HTTPException")


def test_quote_miniapp_checkout_returns_503_when_checkout_gate_disabled(monkeypatch) -> None:
    request = miniapp_routes.MiniAppCheckoutRequest(
        flow="checkout",
        plan_id=uuid4(),
        addons=[],
        code_input=None,
        promo_code=None,
        use_wallet=0,
        currency="USD",
    )

    async def fake_rollout(_db=None) -> MiniAppRuntimeConfig:
        return MiniAppRuntimeConfig(enabled=True, checkout_enabled=False, maintenance_message="Checkout paused")

    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", fake_rollout)

    try:
        asyncio.run(
            quote_miniapp_checkout(
                body=request,
                db=object(),
                user_id=uuid4(),
            )
        )
    except miniapp_routes.HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Checkout paused"
    else:
        raise AssertionError("Expected HTTPException")


def test_get_miniapp_config_returns_503_when_config_gate_disabled(monkeypatch) -> None:
    async def fake_rollout(_db=None) -> MiniAppRuntimeConfig:
        return MiniAppRuntimeConfig(enabled=True, config_enabled=False, maintenance_message="Config paused")

    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", fake_rollout)

    try:
        asyncio.run(
            get_miniapp_config(
                db=object(),
                user_id=uuid4(),
                remnawave_client=object(),
            )
        )
    except miniapp_routes.HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Config paused"
    else:
        raise AssertionError("Expected HTTPException")
