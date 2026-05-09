from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.application.services.config_service import MiniAppRuntimeConfig
from src.application.use_cases.trial.stage1_trial_policy import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_DURATION_DAYS,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
)
from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.presentation.api.v1.miniapp import routes as miniapp_routes
from src.presentation.api.v1.miniapp.routes import (
    _build_primary_cta,
    _build_usage_snapshot,
    _is_rtl_locale,
    activate_miniapp_trial,
    get_miniapp_config,
    get_miniapp_offers,
    get_miniapp_payment_status,
    quote_miniapp_checkout,
)


async def _default_rollout_config(_db=None) -> MiniAppRuntimeConfig:
    return MiniAppRuntimeConfig()


def test_build_primary_cta_prefers_trial_for_new_users() -> None:
    cta = _build_primary_cta(subscription_status="none", trial_eligible=True, has_config=False)

    assert cta.kind == "start_trial"
    assert cta.label == "Start trial"


def test_build_primary_cta_uses_select_server_for_active_users_with_config() -> None:
    cta = _build_primary_cta(subscription_status="active", trial_eligible=False, has_config=True)

    assert cta.kind == "select_server"


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
    realm = SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4()))

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
    remnawave_user_id = uuid4()

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _user_id):
            return SimpleNamespace(
                id=user_id,
                telegram_id=123456789,
                subscription_url="https://legacy.example/sub",
            )

    class FakeGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            pass

        async def execute(self, user_uuid):
            assert user_uuid == remnawave_user_id
            return {
                "config": "vless://generated",
                "config_string": "vless://generated",
                "client_type": "vless",
                "is_found": True,
                "links": ["vless://generated"],
                "ss_conf_links": {},
                "subscription_url": "https://generated.example/sub",
            }

    async def fake_get_remnawave_user(*, client, telegram_id):
        assert telegram_id == 123456789
        return SimpleNamespace(uuid=remnawave_user_id)

    monkeypatch.setattr(miniapp_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(miniapp_routes, "GenerateConfigUseCase", FakeGenerateConfigUseCase)
    monkeypatch.setattr(miniapp_routes, "_get_remnawave_user", fake_get_remnawave_user)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    response = asyncio.run(
        get_miniapp_config(
            db=object(),
            user_id=user_id,
            remnawave_client=object(),
        )
    )

    assert response.config == "vless://generated"
    assert response.config_string == "vless://generated"
    assert response.client_type == "vless"
    assert response.source == "remnawave_generated"
    assert response.subscription_url == "https://generated.example/sub"


def test_get_miniapp_config_falls_back_to_legacy_subscription_url(monkeypatch) -> None:
    user_id = uuid4()

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _user_id):
            return SimpleNamespace(
                id=user_id,
                telegram_id=None,
                subscription_url="https://legacy.example/sub",
            )

    async def fake_get_remnawave_user(*, client, telegram_id):
        assert telegram_id is None
        return None

    monkeypatch.setattr(miniapp_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(miniapp_routes, "_get_remnawave_user", fake_get_remnawave_user)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", _default_rollout_config)

    response = asyncio.run(
        get_miniapp_config(
            db=object(),
            user_id=user_id,
            remnawave_client=object(),
        )
    )

    assert response.config == "https://legacy.example/sub"
    assert response.client_type == "subscription"
    assert response.source == "legacy_subscription_url"
    assert response.subscription_url == "https://legacy.example/sub"


def test_quote_miniapp_checkout_uses_surface_specific_flow(monkeypatch) -> None:
    user_id = uuid4()
    request = miniapp_routes.MiniAppCheckoutRequest(
        flow="checkout",
        plan_id=uuid4(),
        addons=[],
        code_input="SAVE20",
        promo_code=None,
        use_wallet=0,
        currency="USD",
    )

    async def fake_build_quote(*, body, db, user_id):
        assert body.channel == "miniapp"
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
        )
    )

    assert response.displayed_price == 79


def test_activate_miniapp_trial_preserves_rate_limit_and_activation(monkeypatch) -> None:
    user_id = uuid4()

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
        def __init__(self, _db) -> None:
            pass

        async def execute(self, _user_id):
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
