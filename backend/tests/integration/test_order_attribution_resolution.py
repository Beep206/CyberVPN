from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.domain.enums import AttributionTouchpointType, CustomerCommercialBindingStatus, CustomerCommercialBindingType
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_commercial_binding_model import CustomerCommercialBindingModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_attribution_result_model import OrderAttributionResultModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.dependencies.services import get_crypto_client
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.integration]


class FakeCryptoBotClient:
    def __init__(self) -> None:
        self._counter = 4000

    async def create_invoice(self, amount: str, currency: str, description: str, payload: str | None = None) -> dict:
        _ = amount, currency, description, payload
        self._counter += 1
        invoice_id = str(self._counter)
        return {
            "invoice_id": invoice_id,
            "pay_url": f"https://pay.example.test/{invoice_id}",
            "status": "pending",
            "expiration_date": "2030-01-01T00:00:00+00:00",
        }


def _partner_code(
    *,
    code: str,
    partner_owner_id: uuid.UUID,
    partner_account_id: uuid.UUID | None = None,
    owner_type: str = "affiliate",
    markup_pct: int = 5,
    attribution_model: str = "last_eligible_touch",
) -> PartnerCodeModel:
    return PartnerCodeModel(
        id=uuid.uuid4(),
        code=code,
        code_normalized=code,
        public_slug=f"px-{code.lower()}",
        public_token_hash=f"hash-{code.lower()}",
        partner_account_id=partner_account_id,
        partner_user_id=partner_owner_id,
        markup_pct=markup_pct,
        is_active=True,
        lifecycle_status="active",
        approval_status="approved",
        owner_type=owner_type,
        attribution_model=attribution_model,
    )


def _policy_snapshot(*, code: PartnerCodeModel, attribution_model: str, allowed: bool = True) -> dict:
    return {
        "allowed": allowed,
        "reason_codes": [] if allowed else ["policy_denied"],
        "owner_type": code.owner_type,
        "partner_account_id": str(code.partner_account_id) if code.partner_account_id else None,
        "partner_code_id": str(code.id),
        "attribution_model": attribution_model,
        "snapshot_complete": True,
    }


def _touchpoint_model(
    *,
    quote_id: uuid.UUID,
    checkout_id: uuid.UUID,
    user_id: uuid.UUID,
    realm_id: uuid.UUID,
    storefront_id: uuid.UUID,
    code: PartnerCodeModel,
    touchpoint_type: str,
    occurred_at: datetime,
    attribution_model: str,
    source_suffix: str,
    evidence_payload: dict | None = None,
) -> AttributionTouchpointModel:
    payload = {"policy_snapshot": _policy_snapshot(code=code, attribution_model=attribution_model)}
    payload.update(evidence_payload or {})
    return AttributionTouchpointModel(
        id=uuid.uuid4(),
        touchpoint_type=touchpoint_type,
        source_event_id=f"order-attr-{source_suffix}-{uuid.uuid4()}",
        idempotency_key=f"order-attr-{source_suffix}-{uuid.uuid4()}",
        user_id=user_id,
        auth_realm_id=realm_id,
        storefront_id=storefront_id,
        quote_session_id=quote_id,
        checkout_session_id=checkout_id,
        partner_code_id=code.id,
        sale_channel="web",
        source_host="partner.example.test",
        source_path=f"/campaign/{source_suffix}",
        campaign_params={"case": source_suffix},
        evidence_payload=payload,
        occurred_at=occurred_at,
        created_at=occurred_at,
    )


def _binding_model(
    *,
    user_id: uuid.UUID,
    realm_id: uuid.UUID,
    storefront_id: uuid.UUID | None,
    code: PartnerCodeModel,
    binding_type: str,
    owner_type: str,
    effective_from: datetime,
) -> CustomerCommercialBindingModel:
    return CustomerCommercialBindingModel(
        id=uuid.uuid4(),
        user_id=user_id,
        auth_realm_id=realm_id,
        storefront_id=storefront_id,
        binding_type=binding_type,
        binding_status=CustomerCommercialBindingStatus.ACTIVE.value,
        owner_type=owner_type,
        partner_account_id=code.partner_account_id,
        partner_code_id=code.id,
        reason_code="order_attribution_test",
        evidence_payload={
            "policy_snapshot": _policy_snapshot(code=code, attribution_model=code.attribution_model),
        },
        effective_from=effective_from,
    )


def _make_admin_token(auth_service: AuthService, *, user_id, realm) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=realm.audience,
        principal_type="admin",
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family="admin",
    )
    return token


async def _create_quote_checkout(
    *,
    async_client: AsyncClient,
    headers: dict[str, str],
    storefront_key: str,
    pricebook_key: str,
    offer_key: str,
    plan_id: str,
    partner_code: str | None = None,
    idempotency_key: str = "attribution-checkout",
    currency: str = "USD",
) -> tuple[dict, dict]:
    quote_response = await async_client.post(
        "/api/v1/quotes/",
        headers=headers,
        json={
            "storefront_key": storefront_key,
            "pricebook_key": pricebook_key,
            "offer_key": offer_key,
            "plan_id": plan_id,
            "currency": currency,
            "channel": "web",
            "partner_code": partner_code,
            "use_wallet": 0,
            "addons": [],
        },
    )
    assert quote_response.status_code == 201
    quote_payload = quote_response.json()

    checkout_response = await async_client.post(
        "/api/v1/checkout-sessions/",
        headers={**headers, "Idempotency-Key": idempotency_key},
        json={"quote_session_id": quote_payload["id"]},
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout_payload = checkout_response.json()
    return quote_payload, checkout_payload


@pytest.mark.asyncio
async def test_order_attribution_persists_touchpoint_strategy_explainability(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )
            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            partner_owner_id = uuid.uuid4()
            partner_account_id = uuid.uuid4()
            with sessionmaker() as db:
                partner_owner = MobileUserModel(
                    id=partner_owner_id,
                    auth_realm_id=customer_realm.id,
                    email="strategy-owner@example.test",
                    password_hash=await auth_service.hash_password("StrategyOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=partner_account_id,
                    account_key="strategy-account",
                    display_name="Strategy Account",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                codes = {
                    "first_a": _partner_code(
                        code="STRFIRSTA",
                        partner_owner_id=partner_owner.id,
                        partner_account_id=partner_account.id,
                        attribution_model="first_eligible_touch",
                    ),
                    "first_b": _partner_code(
                        code="STRFIRSTB",
                        partner_owner_id=partner_owner.id,
                        partner_account_id=partner_account.id,
                        attribution_model="first_eligible_touch",
                    ),
                    "last_a": _partner_code(
                        code="STRLASTA",
                        partner_owner_id=partner_owner.id,
                        partner_account_id=partner_account.id,
                        attribution_model="last_eligible_touch",
                    ),
                    "last_b": _partner_code(
                        code="STRLASTB",
                        partner_owner_id=partner_owner.id,
                        partner_account_id=partner_account.id,
                        attribution_model="last_eligible_touch",
                    ),
                    "click": _partner_code(
                        code="STRCLICKA",
                        partner_owner_id=partner_owner.id,
                        partner_account_id=partner_account.id,
                        attribution_model="last_eligible_click",
                    ),
                    "non_click": _partner_code(
                        code="STRCLICKB",
                        partner_owner_id=partner_owner.id,
                        partner_account_id=partner_account.id,
                        attribution_model="last_eligible_click",
                    ),
                }
                db.add_all([partner_owner, partner_account, *codes.values()])
                db.commit()

            async def resolve_case(
                *,
                case_key: str,
                touchpoint_specs: list[tuple[str, str, str, int]],
                expected_code: PartnerCodeModel,
                expected_strategy: str,
            ) -> OrderAttributionResultModel:
                quote_payload, checkout_payload = await _create_quote_checkout(
                    async_client=async_client,
                    headers=customer_headers,
                    storefront_key=seeded["storefront_key"],
                    pricebook_key=seeded["pricebook_key"],
                    offer_key=seeded["offer_key"],
                    plan_id=seeded["plan_id"],
                    idempotency_key=f"strategy-checkout-{case_key}",
                )
                base_time = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
                with sessionmaker() as db:
                    touchpoints = [
                        _touchpoint_model(
                            quote_id=uuid.UUID(quote_payload["id"]),
                            checkout_id=uuid.UUID(checkout_payload["id"]),
                            user_id=uuid.UUID(seeded["customer_user_id"]),
                            realm_id=customer_realm.id,
                            storefront_id=uuid.UUID(seeded["storefront_id"]),
                            code=codes[code_key],
                            touchpoint_type=touchpoint_type,
                            occurred_at=base_time + timedelta(minutes=offset_minutes),
                            attribution_model=attribution_model,
                            source_suffix=f"{case_key}-{code_key}",
                        )
                        for code_key, touchpoint_type, attribution_model, offset_minutes in touchpoint_specs
                    ]
                    db.add_all(touchpoints)
                    db.commit()

                order_response = await async_client.post(
                    "/api/v1/orders/commit",
                    headers=customer_headers,
                    json={"checkout_session_id": checkout_payload["id"]},
                )
                assert order_response.status_code == 201, order_response.text
                order_id = uuid.UUID(order_response.json()["id"])
                with sessionmaker() as db:
                    result = (
                        db.query(OrderAttributionResultModel)
                        .filter(OrderAttributionResultModel.order_id == order_id)
                        .one()
                    )
                    assert result.partner_code_id == expected_code.id
                    assert result.winning_touchpoint_id is not None
                    assert result.explainability_snapshot["policy_strategy"] == expected_strategy
                    evaluations = result.explainability_snapshot["candidate_evaluations"]
                    winner = next(item for item in evaluations if item["result"] == "winner")
                    assert winner["candidate_kind"] == "touchpoint"
                    assert winner["partner_code_id"] == str(expected_code.id)
                    assert result.evidence_snapshot["eligible_touchpoint_ids"]
                    return result

            await resolve_case(
                case_key="first",
                touchpoint_specs=[
                    (
                        "first_a",
                        AttributionTouchpointType.PASSIVE_CLICK.value,
                        "first_eligible_touch",
                        0,
                    ),
                    (
                        "first_b",
                        AttributionTouchpointType.PASSIVE_CLICK.value,
                        "first_eligible_touch",
                        5,
                    ),
                ],
                expected_code=codes["first_a"],
                expected_strategy="first_eligible_touch",
            )

            await resolve_case(
                case_key="last",
                touchpoint_specs=[
                    (
                        "last_a",
                        AttributionTouchpointType.PASSIVE_CLICK.value,
                        "last_eligible_touch",
                        0,
                    ),
                    (
                        "last_b",
                        AttributionTouchpointType.PASSIVE_CLICK.value,
                        "last_eligible_touch",
                        5,
                    ),
                ],
                expected_code=codes["last_b"],
                expected_strategy="last_eligible_touch",
            )

            last_click_result = await resolve_case(
                case_key="last-click",
                touchpoint_specs=[
                    (
                        "click",
                        AttributionTouchpointType.PASSIVE_CLICK.value,
                        "last_eligible_click",
                        0,
                    ),
                    (
                        "non_click",
                        AttributionTouchpointType.EXPLICIT_CODE.value,
                        "last_eligible_click",
                        5,
                    ),
                ],
                expected_code=codes["click"],
                expected_strategy="last_eligible_click",
            )
            non_click_loser = next(
                item
                for item in last_click_result.explainability_snapshot["candidate_evaluations"]
                if item["candidate_kind"] == "touchpoint" and item["partner_code_id"] == str(codes["non_click"].id)
            )
            assert non_click_loser["result"] == "loser"
            assert non_click_loser["reason_codes"] == ["not_click_touchpoint"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_attribution_persists_precedence_losers_and_exclusions(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )
            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            partner_owner_id = uuid.uuid4()
            partner_account_id = uuid.uuid4()
            with sessionmaker() as db:
                current_storefront = db.get(StorefrontModel, uuid.UUID(seeded["storefront_id"]))
                assert current_storefront is not None
                foreign_storefront = StorefrontModel(
                    id=uuid.uuid4(),
                    storefront_key="foreign-order-attr",
                    brand_id=current_storefront.brand_id,
                    display_name="Foreign Order Attribution",
                    host="foreign-order-attr.example.test",
                    merchant_profile_id=current_storefront.merchant_profile_id,
                    auth_realm_id=current_storefront.auth_realm_id,
                    status="active",
                )
                partner_owner = MobileUserModel(
                    id=partner_owner_id,
                    auth_realm_id=customer_realm.id,
                    email="precedence-owner@example.test",
                    password_hash=await auth_service.hash_password("PrecedenceOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=partner_account_id,
                    account_key="precedence-account",
                    display_name="Precedence Account",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                manual_code = _partner_code(
                    code="ATTRMANUAL",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="performance",
                    attribution_model="manual_override",
                )
                contract_code = _partner_code(
                    code="ATTRCONTRACT",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="performance",
                    attribution_model="contract_assignment",
                )
                passive_code = _partner_code(
                    code="ATTRPASSIVE",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    attribution_model="first_eligible_touch",
                )
                expired_code = _partner_code(
                    code="ATTREXPIRED",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                )
                wrong_storefront_code = _partner_code(
                    code="ATTRWRONG",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                )
                db.add_all(
                    [
                        foreign_storefront,
                        partner_owner,
                        partner_account,
                        manual_code,
                        contract_code,
                        passive_code,
                        expired_code,
                        wrong_storefront_code,
                    ]
                )
                db.commit()

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="precedence-checkout-manual",
            )
            base_time = datetime(2026, 6, 21, 13, 0, tzinfo=UTC)
            with sessionmaker() as db:
                foreign_storefront = (
                    db.query(StorefrontModel).filter(StorefrontModel.storefront_key == "foreign-order-attr").one()
                )
                manual_binding = _binding_model(
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=None,
                    code=manual_code,
                    binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                    owner_type="performance",
                    effective_from=base_time,
                )
                contract_binding = _binding_model(
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    code=contract_code,
                    binding_type=CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value,
                    owner_type="performance",
                    effective_from=base_time + timedelta(minutes=1),
                )
                wrong_storefront_binding = _binding_model(
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=foreign_storefront.id,
                    code=wrong_storefront_code,
                    binding_type=CustomerCommercialBindingType.RESELLER_BINDING.value,
                    owner_type="reseller",
                    effective_from=base_time + timedelta(minutes=2),
                )
                passive_touchpoint = _touchpoint_model(
                    quote_id=uuid.UUID(quote_payload["id"]),
                    checkout_id=uuid.UUID(checkout_payload["id"]),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    code=passive_code,
                    touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                    occurred_at=base_time,
                    attribution_model="first_eligible_touch",
                    source_suffix="manual-passive",
                )
                expired_touchpoint = _touchpoint_model(
                    quote_id=uuid.UUID(quote_payload["id"]),
                    checkout_id=uuid.UUID(checkout_payload["id"]),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    code=expired_code,
                    touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                    occurred_at=base_time + timedelta(minutes=1),
                    attribution_model="last_eligible_touch",
                    source_suffix="manual-expired",
                    evidence_payload={"expires_at": (base_time - timedelta(minutes=1)).isoformat()},
                )
                wrong_storefront_touchpoint = _touchpoint_model(
                    quote_id=uuid.UUID(quote_payload["id"]),
                    checkout_id=uuid.UUID(checkout_payload["id"]),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=foreign_storefront.id,
                    code=wrong_storefront_code,
                    touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                    occurred_at=base_time + timedelta(minutes=2),
                    attribution_model="last_eligible_touch",
                    source_suffix="manual-wrong-storefront",
                )
                db.add_all(
                    [
                        manual_binding,
                        contract_binding,
                        wrong_storefront_binding,
                        passive_touchpoint,
                        expired_touchpoint,
                        wrong_storefront_touchpoint,
                    ]
                )
                db.commit()
                manual_binding_id = manual_binding.id
                contract_binding_id = contract_binding.id
                wrong_storefront_binding_id = wrong_storefront_binding.id
                passive_touchpoint_id = passive_touchpoint.id
                expired_touchpoint_id = expired_touchpoint.id
                wrong_storefront_touchpoint_id = wrong_storefront_touchpoint.id

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_id = uuid.UUID(order_response.json()["id"])
            with sessionmaker() as db:
                result = (
                    db.query(OrderAttributionResultModel).filter(OrderAttributionResultModel.order_id == order_id).one()
                )
                assert result.owner_source == "contract_assignment"
                assert result.winning_binding_id == contract_binding_id
                evaluations = result.explainability_snapshot["candidate_evaluations"]
                by_id = {item["id"]: item for item in evaluations}
                assert by_id[str(contract_binding_id)]["result"] == "winner"
                assert by_id[str(manual_binding_id)]["result"] == "loser"
                assert by_id[str(manual_binding_id)]["reason_codes"] == ["lower_precedence_contract_assignment"]
                assert by_id[str(passive_touchpoint_id)]["result"] == "loser"
                assert by_id[str(passive_touchpoint_id)]["reason_codes"] == ["lower_precedence_contract_assignment"]
                assert by_id[str(expired_touchpoint_id)]["result"] == "excluded"
                assert "attribution_window_expired" in by_id[str(expired_touchpoint_id)]["reason_codes"]
                assert by_id[str(wrong_storefront_touchpoint_id)]["result"] == "excluded"
                assert "wrong_storefront" in by_id[str(wrong_storefront_touchpoint_id)]["reason_codes"]
                assert by_id[str(wrong_storefront_binding_id)]["result"] == "excluded"
                assert "wrong_storefront" in by_id[str(wrong_storefront_binding_id)]["reason_codes"]
                assert result.evidence_snapshot["excluded_touchpoints"]
                assert result.evidence_snapshot["excluded_bindings"]

            with sessionmaker() as db:
                manual_binding = db.get(CustomerCommercialBindingModel, manual_binding_id)
                assert manual_binding is not None
                manual_binding.binding_status = CustomerCommercialBindingStatus.SUPERSEDED.value
                manual_binding.effective_to = datetime.now(UTC)
                db.commit()

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="precedence-checkout-contract",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            contract_order_id = uuid.UUID(order_response.json()["id"])
            with sessionmaker() as db:
                result = (
                    db.query(OrderAttributionResultModel)
                    .filter(OrderAttributionResultModel.order_id == contract_order_id)
                    .one()
                )
                assert result.owner_source == "contract_assignment"
                assert result.winning_binding_id == contract_binding_id
                winner = result.explainability_snapshot["winning_candidate"]
                assert winner["winning_binding_id"] == str(contract_binding_id)
                assert "contract_assignment_binding_selected" in winner["rule_path"]
                assert "exact_storefront_binding_selected" in winner["rule_path"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_attribution_uses_touchpoint_policy_snapshot_after_partner_code_mutation(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )
            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            original_account_id = uuid.uuid4()
            mutated_account_id = uuid.uuid4()
            partner_owner_id = uuid.uuid4()
            with sessionmaker() as db:
                partner_owner = MobileUserModel(
                    id=partner_owner_id,
                    auth_realm_id=customer_realm.id,
                    email="snapshot-owner@example.test",
                    password_hash=await auth_service.hash_password("SnapshotOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                original_account = PartnerAccountModel(
                    id=original_account_id,
                    account_key="snapshot-original-account",
                    display_name="Snapshot Original Account",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                mutated_account = PartnerAccountModel(
                    id=mutated_account_id,
                    account_key="snapshot-mutated-account",
                    display_name="Snapshot Mutated Account",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                code = _partner_code(
                    code="SNAPSHOT42",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=original_account.id,
                    owner_type="affiliate",
                    markup_pct=6,
                    attribution_model="first_eligible_touch",
                )
                db.add_all([partner_owner, original_account, mutated_account, code])
                db.commit()
                code_id = code.id

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="snapshot-mutation-checkout",
            )
            with sessionmaker() as db:
                code = db.get(PartnerCodeModel, code_id)
                assert code is not None
                touchpoint = _touchpoint_model(
                    quote_id=uuid.UUID(quote_payload["id"]),
                    checkout_id=uuid.UUID(checkout_payload["id"]),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    code=code,
                    touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                    occurred_at=datetime(2026, 6, 21, 14, 0, tzinfo=UTC),
                    attribution_model="first_eligible_touch",
                    source_suffix="snapshot-mutation",
                    evidence_payload={
                        "access_token": "secret-access-token-value",
                        "cookie": "cv_session=secret-cookie-value",
                        "telegram_initData": "raw-init-data-value",
                        "email": "evidence@example.test",
                        "pat": "pat-secret-value",
                    },
                )
                touchpoint.campaign_params = {
                    "utm_source": "newsletter",
                    "access_token": "query-access-token-value",
                    "email": "query@example.test",
                    "custom": "pat=query-pat-secret",
                }
                db.add(touchpoint)
                db.flush()
                touchpoint_id = touchpoint.id
                code.owner_type = "performance"
                code.partner_account_id = mutated_account_id
                code.markup_pct = 99
                code.attribution_model = "last_eligible_touch"
                db.commit()

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_id = uuid.UUID(order_response.json()["id"])
            with sessionmaker() as db:
                result = (
                    db.query(OrderAttributionResultModel).filter(OrderAttributionResultModel.order_id == order_id).one()
                )
                assert result.winning_touchpoint_id == touchpoint_id
                assert result.owner_type == "affiliate"
                assert result.partner_account_id == original_account_id
                assert result.policy_snapshot["resolved_attribution_model"] == "first_eligible_touch"
                commercial_snapshot = result.policy_snapshot["commercial_policy_snapshot"]
                assert commercial_snapshot["owner_type"] == "affiliate"
                assert commercial_snapshot["partner_account_id"] == str(original_account_id)
                assert commercial_snapshot["attribution_model"] == "first_eligible_touch"
                assert "owner_policy_loaded_from_immutable_touchpoint_snapshot" in result.rule_path

                snapshot_text = f"{result.explainability_snapshot} {result.policy_snapshot}"
                assert "secret-access-token-value" not in snapshot_text
                assert "secret-cookie-value" not in snapshot_text
                assert "raw-init-data-value" not in snapshot_text
                assert "evidence@example.test" not in snapshot_text
                assert "pat-secret-value" not in snapshot_text
                assert "query-access-token-value" not in snapshot_text
                assert "query@example.test" not in snapshot_text
                assert "query-pat-secret" not in snapshot_text
                evaluated_touchpoint = result.explainability_snapshot["evaluated_touchpoints"][0]
                assert evaluated_touchpoint["campaign_params"]["utm_source"] == "newsletter"
                assert "redacted_keys" in evaluated_touchpoint["campaign_params"]
                assert "redacted_keys" in evaluated_touchpoint["evidence_payload"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_attribution_excludes_future_and_wrong_realm_bindings(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )
            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            partner_owner_id = uuid.uuid4()
            partner_account_id = uuid.uuid4()
            with sessionmaker() as db:
                wrong_realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="wrong-order-realm",
                    realm_type="customer",
                    display_name="Wrong Order Realm",
                    audience="cybervpn:wrong-order-realm",
                    cookie_namespace="wrong-order-realm",
                    status="active",
                    is_default=False,
                )
                partner_owner = MobileUserModel(
                    id=partner_owner_id,
                    auth_realm_id=customer_realm.id,
                    email="future-owner@example.test",
                    password_hash=await auth_service.hash_password("FutureOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=partner_account_id,
                    account_key="future-account",
                    display_name="Future Account",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                current_code = _partner_code(
                    code="CURRENTCONTRACT",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="performance",
                    attribution_model="contract_assignment",
                )
                future_manual_code = _partner_code(
                    code="FUTUREMANUAL",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="performance",
                    attribution_model="manual_override",
                )
                future_contract_code = _partner_code(
                    code="FUTURECONTRACT",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="performance",
                    attribution_model="contract_assignment",
                )
                future_reseller_code = _partner_code(
                    code="FUTURERES",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="reseller",
                    attribution_model="persistent_storefront_binding",
                )
                future_default_code = _partner_code(
                    code="FUTUREDEFAULT",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="affiliate",
                    attribution_model="persistent_storefront_binding",
                )
                wrong_realm_code = _partner_code(
                    code="WRONGREALM",
                    partner_owner_id=partner_owner.id,
                    partner_account_id=partner_account.id,
                    owner_type="performance",
                    attribution_model="manual_override",
                )
                db.add_all(
                    [
                        wrong_realm,
                        partner_owner,
                        partner_account,
                        current_code,
                        future_manual_code,
                        future_contract_code,
                        future_reseller_code,
                        future_default_code,
                        wrong_realm_code,
                    ]
                )
                db.commit()

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="future-binding-checkout",
            )
            with sessionmaker() as db:
                wrong_realm = db.query(AuthRealmModel).filter(AuthRealmModel.realm_key == "wrong-order-realm").one()
                future_time = datetime.now(UTC) + timedelta(days=1)
                current_time = datetime.now(UTC) - timedelta(days=1)
                current_binding = _binding_model(
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    code=current_code,
                    binding_type=CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value,
                    owner_type="performance",
                    effective_from=current_time,
                )
                future_bindings = [
                    _binding_model(
                        user_id=uuid.UUID(seeded["customer_user_id"]),
                        realm_id=customer_realm.id,
                        storefront_id=None,
                        code=future_manual_code,
                        binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                        owner_type="performance",
                        effective_from=future_time,
                    ),
                    _binding_model(
                        user_id=uuid.UUID(seeded["customer_user_id"]),
                        realm_id=customer_realm.id,
                        storefront_id=uuid.UUID(seeded["storefront_id"]),
                        code=future_contract_code,
                        binding_type=CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value,
                        owner_type="performance",
                        effective_from=future_time,
                    ),
                    _binding_model(
                        user_id=uuid.UUID(seeded["customer_user_id"]),
                        realm_id=customer_realm.id,
                        storefront_id=uuid.UUID(seeded["storefront_id"]),
                        code=future_reseller_code,
                        binding_type=CustomerCommercialBindingType.RESELLER_BINDING.value,
                        owner_type="reseller",
                        effective_from=future_time,
                    ),
                    _binding_model(
                        user_id=uuid.UUID(seeded["customer_user_id"]),
                        realm_id=customer_realm.id,
                        storefront_id=uuid.UUID(seeded["storefront_id"]),
                        code=future_default_code,
                        binding_type=CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER.value,
                        owner_type="affiliate",
                        effective_from=future_time,
                    ),
                ]
                wrong_realm_binding = _binding_model(
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    realm_id=wrong_realm.id,
                    storefront_id=None,
                    code=wrong_realm_code,
                    binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                    owner_type="performance",
                    effective_from=current_time,
                )
                db.add_all([current_binding, wrong_realm_binding, *future_bindings])
                db.commit()
                current_binding_id = current_binding.id
                future_binding_ids = [binding.id for binding in future_bindings]
                wrong_realm_binding_id = wrong_realm_binding.id

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_id = uuid.UUID(order_response.json()["id"])
            with sessionmaker() as db:
                result = (
                    db.query(OrderAttributionResultModel).filter(OrderAttributionResultModel.order_id == order_id).one()
                )
                assert result.owner_source == "contract_assignment"
                assert result.winning_binding_id == current_binding_id
                evaluations = result.explainability_snapshot["candidate_evaluations"]
                by_id = {item["id"]: item for item in evaluations}
                for binding_id in future_binding_ids:
                    assert by_id[str(binding_id)]["result"] == "excluded"
                    assert "binding_not_yet_effective" in by_id[str(binding_id)]["reason_codes"]
                assert str(wrong_realm_binding_id) not in result.evidence_snapshot["binding_ids"]
                assert str(wrong_realm_binding_id) not in by_id
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_attribution_prefers_explicit_code_over_passive_click_and_binding(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="owner-attribution@example.test",
                    password_hash=await auth_service.hash_password("OwnerAttribution123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="reseller-attribution",
                    display_name="Reseller Attribution",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="RESELLER88",
                    partner_account_id=reseller_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=18,
                    is_active=True,
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="AFFILIATE12",
                    partner_user_id=partner_owner.id,
                    markup_pct=12,
                    is_active=True,
                )
                passive_click_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="CLICK09",
                    partner_user_id=partner_owner.id,
                    markup_pct=9,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="order_attr_admin",
                    email="order-attr-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("OrderAttrAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="order_attr_support",
                    email="order-attr-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("OrderAttrSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all(
                    [
                        partner_owner,
                        reseller_workspace,
                        reseller_code,
                        affiliate_code,
                        passive_click_code,
                        admin_user,
                        support_user,
                    ]
                )
                db.commit()
                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert bind_response.status_code == 200

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=affiliate_code.code,
                idempotency_key="attribution-explicit-checkout",
            )

            manual_touchpoint = await async_client.post(
                "/api/v1/attribution/touchpoints",
                headers=admin_headers,
                json={
                    "touchpoint_type": "passive_click",
                    "auth_realm_key": seeded["customer_realm_key"],
                    "quote_session_id": quote_payload["id"],
                    "partner_code": passive_click_code.code,
                    "sale_channel": "web",
                    "source_host": "partner.example.test",
                    "source_path": "/reviews/best-vpn",
                    "evidence_payload": {"click_id": "click-explicit-1"},
                },
            )
            assert manual_touchpoint.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            result_response = await async_client.get(
                f"/api/v1/attribution/orders/{order_payload['id']}/result",
                headers=support_headers,
            )
            assert result_response.status_code == 200
            result_payload = result_response.json()
            assert result_payload["owner_type"] == "affiliate"
            assert result_payload["owner_source"] == "explicit_code"
            assert result_payload["partner_code_id"] == str(affiliate_code.id)
            assert result_payload["winning_binding_id"] is None
            assert "explicit_code_touchpoint_selected" in result_payload["rule_path"]

            quote_touchpoints = await async_client.get(
                f"/api/v1/attribution/touchpoints?quote_session_id={quote_payload['id']}",
                headers=support_headers,
            )
            assert quote_touchpoints.status_code == 200
            explicit_touchpoint_id = next(
                item["id"] for item in quote_touchpoints.json() if item["touchpoint_type"] == "explicit_code"
            )
            assert result_payload["winning_touchpoint_id"] == explicit_touchpoint_id

            resolve_again = await async_client.post(
                f"/api/v1/attribution/orders/{order_payload['id']}/resolve",
                headers=admin_headers,
            )
            assert resolve_again.status_code == 200
            assert resolve_again.json()["id"] == result_payload["id"]

    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_attribution_prefers_reseller_binding_over_passive_click(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="binding-owner@example.test",
                    password_hash=await auth_service.hash_password("BindingOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="binding-reseller",
                    display_name="Binding Reseller",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="RESELLER55",
                    partner_account_id=reseller_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                passive_click_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="CLICK07",
                    partner_user_id=partner_owner.id,
                    markup_pct=7,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="binding_attr_admin",
                    email="binding-attr-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("BindingAttrAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="binding_attr_support",
                    email="binding-attr-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("BindingAttrSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all(
                    [
                        partner_owner,
                        reseller_workspace,
                        reseller_code,
                        passive_click_code,
                        admin_user,
                        support_user,
                    ]
                )
                db.commit()
                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert bind_response.status_code == 200

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=None,
                idempotency_key="attribution-binding-checkout",
            )

            manual_touchpoint = await async_client.post(
                "/api/v1/attribution/touchpoints",
                headers=admin_headers,
                json={
                    "touchpoint_type": "passive_click",
                    "auth_realm_key": seeded["customer_realm_key"],
                    "quote_session_id": quote_payload["id"],
                    "partner_code": passive_click_code.code,
                    "sale_channel": "web",
                    "source_host": "partner.example.test",
                    "source_path": "/ads/telegram",
                    "evidence_payload": {"click_id": "click-binding-1"},
                },
            )
            assert manual_touchpoint.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            result_response = await async_client.get(
                f"/api/v1/attribution/orders/{order_payload['id']}/result",
                headers=support_headers,
            )
            assert result_response.status_code == 200
            result_payload = result_response.json()
            assert result_payload["owner_type"] == "reseller"
            assert result_payload["owner_source"] == "persistent_reseller_binding"
            assert result_payload["partner_code_id"] == str(reseller_code.id)
            assert result_payload["partner_account_id"] == str(reseller_workspace.id)
            assert result_payload["winning_touchpoint_id"] is None
            assert result_payload["winning_binding_id"] is not None
            assert "persistent_reseller_binding_selected" in result_payload["rule_path"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
