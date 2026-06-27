from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel, GrowthCodeReservationModel
from src.infrastructure.database.models.growth_code_set_model import (
    CheckoutCodeApplicationModel,
    CheckoutCodeSetModel,
    GrowthCodeReservationGroupModel,
)
from src.infrastructure.database.models.growth_risk_fx_model import (
    FxDiscountConversionModel,
    GrowthRiskDecisionModel,
    RiskFeatureSnapshotModel,
    RiskModelVersionModel,
)
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.presentation.api.v3.admin_growth_code_sets import (
    AdminGrowthCodeSetSimulationRequest,
    get_growth_code_application_support_view,
    get_growth_code_set_support_view,
    inspect_growth_code_sets,
    list_order_growth_code_applications,
    simulate_growth_code_set,
)

pytestmark = [pytest.mark.asyncio]


async def _admin_user(db: AsyncSession) -> AdminUserModel:
    suffix = uuid4().hex[:8]
    user = AdminUserModel(
        id=uuid4(),
        login=f"growth-code-set-admin-{suffix}",
        email=f"growth-code-set-admin-{suffix}@example.test",
        role=AdminRole.ADMIN.value,
        is_active=True,
        is_email_verified=True,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.flush()
    return user


async def _count_rows(db: AsyncSession, model: type[object]) -> int:
    return int(await db.scalar(select(func.count()).select_from(model)) or 0)


async def test_admin_growth_code_set_inspector_returns_safe_support_chain(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    realm = AuthRealmModel(
        id=uuid4(),
        realm_key=f"inspect-realm-{suffix}",
        realm_type="customer",
        display_name="Inspect Realm",
        audience=f"cybervpn:inspect:{suffix}",
        cookie_namespace=f"inspect-{suffix}",
        status="active",
    )
    policy = PolicyVersionModel(
        id=uuid4(),
        policy_family="growth_discount",
        policy_key=f"inspect-policy-{suffix}",
        subject_type="global",
        version_number=1,
        payload={"benefit": "fixed_discount"},
        approval_state="approved",
        version_status="active",
        effective_from=now - timedelta(minutes=1),
    )
    db.add_all([realm, policy])
    await db.flush()

    growth_code = GrowthCodeModel(
        id=uuid4(),
        code_hash=f"inspect-hash-{suffix}",
        code_prefix="PROM",
        code_type="promo",
        status="active",
        issuer_type="admin",
        code_namespace="customer_input",
        policy_version_id=policy.id,
    )
    code_set = CheckoutCodeSetModel(
        id=uuid4(),
        code_set_hash=hashlib.sha256(f"inspect-{suffix}".encode()).hexdigest(),
        anonymous_session_id=f"anon-session-{suffix}",
        auth_realm_id=realm.id,
        sale_channel="web",
        action_context="checkout",
        status="accepted",
        acceptance_mode="all_or_nothing",
        aggregate_result={
            "total_discount": "5.00",
            "raw_code": "PROMO-RAW-SECRET",
        },
        risk_snapshot={"action": "allow", "token": "risk-token-secret"},
    )
    db.add_all([growth_code, code_set])
    await db.flush()

    group = GrowthCodeReservationGroupModel(
        id=uuid4(),
        code_set_id=code_set.id,
        status="reserved",
        reserved_at=now,
        expires_at=now + timedelta(minutes=10),
        idempotency_key="group-idempotency-secret",
    )
    db.add(group)
    await db.flush()

    reservation = GrowthCodeReservationModel(
        id=uuid4(),
        growth_code_id=growth_code.id,
        reservation_group_id=group.id,
        status="reserved",
        reserved_at=now,
        expires_at=now + timedelta(minutes=10),
        capacity_context={"device_key_hash": "device-hash", "raw_code": "PROMO-RAW-SECRET"},
    )
    db.add(reservation)
    await db.flush()

    application = CheckoutCodeApplicationModel(
        id=uuid4(),
        code_set_id=code_set.id,
        position_entered=0,
        canonical_order=0,
        growth_code_id=growth_code.id,
        legacy_code_type="promo",
        masked_code="PROM••••",
        roles={"discount": True},
        resolution_status="accepted",
        policy_version_id=policy.id,
        reservation_id=reservation.id,
        discount_snapshot={"applied_amount": "5.00", "raw_code": "PROMO-RAW-SECRET"},
        benefits_snapshot={"items": []},
        private_access_snapshot={"grant_token": "grant-token-secret"},
        evaluation_trace={"message_key": "growth.code.accepted", "code_input": "PROMO-RAW-SECRET"},
    )
    db.add(application)
    await db.flush()

    fx_conversion = FxDiscountConversionModel(
        id=uuid4(),
        code_application_id=application.id,
        growth_code_id=growth_code.id,
        policy_version_id=policy.id,
        source_amount=Decimal("5.00"),
        source_currency="EUR",
        target_currency="USD",
        conversion_mode="pricebook",
        raw_converted_amount=Decimal("5.50"),
        rounded_amount=Decimal("5.50"),
        applied_amount=Decimal("5.50"),
        target_minor_units=2,
        rounding_mode="ROUND_HALF_UP",
    )
    db.add(fx_conversion)
    await db.flush()
    application.fx_conversion_id = fx_conversion.id
    await db.flush()

    response = await inspect_growth_code_sets(
        code_set_id=code_set.id,
        code_set_hash=None,
        quote_session_id=None,
        checkout_session_id=None,
        order_id=None,
        limit=20,
        offset=0,
        _current_user=admin,
        db=db,
    )

    assert response.total == 1
    item = response.items[0]
    assert item.id == code_set.id
    assert item.anonymous_session_id_hash == hashlib.sha256(f"anon-session-{suffix}".encode()).hexdigest()
    assert item.applications[0].masked_code == "PROM••••"
    assert item.applications[0].reservation_id == reservation.id
    assert item.reservation_groups[0].idempotency_key_hash == hashlib.sha256(b"group-idempotency-secret").hexdigest()
    assert item.reservations[0].capacity_context["raw_code"] == "[REDACTED]"
    assert item.fx_conversions[0].conversion_mode == "pricebook"

    support_item = await get_growth_code_set_support_view(code_set.id, admin, db)
    assert support_item.id == code_set.id

    application_detail = await get_growth_code_application_support_view(application.id, admin, db)
    assert application_detail.application.id == application.id
    assert application_detail.code_set is not None
    assert application_detail.code_set.id == code_set.id

    order_applications = await list_order_growth_code_applications(uuid4(), admin, db)
    assert order_applications.total == 0
    assert order_applications.items == []

    serialized = response.model_dump_json()
    assert "PROMO-RAW-SECRET" not in serialized
    assert "grant-token-secret" not in serialized
    assert "group-idempotency-secret" not in serialized
    assert "anon-session" not in serialized
    assert "[REDACTED]" in serialized


async def test_admin_growth_code_set_inspector_requires_filter(db: AsyncSession) -> None:
    admin = await _admin_user(db)

    with pytest.raises(HTTPException) as exc_info:
        await inspect_growth_code_sets(
            code_set_id=None,
            code_set_hash=None,
            quote_session_id=None,
            checkout_session_id=None,
            order_id=None,
            limit=20,
            offset=0,
            _current_user=admin,
            db=db,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "CODE_SET_INSPECT_FILTER_REQUIRED"


async def test_admin_growth_code_set_simulation_uses_checkout_dry_run(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = await _admin_user(db)
    user_id = uuid4()
    plan_id = uuid4()
    growth_code_id = uuid4()
    calls: list[dict[str, object]] = []

    class FakeCheckoutUseCase:
        def __init__(self, session: AsyncSession) -> None:
            assert session is db

        async def execute(self, **kwargs: object) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(
                base_price=Decimal("10.00"),
                discount_amount=Decimal("2.50"),
                wallet_amount=Decimal("0.00"),
                gateway_amount=Decimal("7.50"),
                is_zero_gateway=False,
                code_set_hash="dry-run-code-set-hash",
                code_set_acceptance_mode="all_or_nothing",
                private_catalog_grant_id=None,
                code_set_applications=[
                    {
                        "position_entered": 0,
                        "canonical_order": 0,
                        "growth_code_id": str(growth_code_id),
                        "legacy_code_type": "promo",
                        "masked_code": "PRO••••",
                        "roles": ["discount"],
                        "status": "accepted",
                        "discount": {
                            "applied_amount": "2.50",
                            "source_currency": "USD",
                            "raw_code": "PROMO-RAW-SECRET",
                        },
                        "benefits": [{"kind": "discount"}],
                        "private_access": {"grant_token": "grant-token-secret"},
                        "evaluation_trace": {
                            "code_input": "PROMO-RAW-SECRET",
                            "message_key": "growth_codes.accepted",
                        },
                    }
                ],
            )

    monkeypatch.setattr(
        "src.presentation.api.v3.admin_growth_code_sets.CheckoutUseCase",
        FakeCheckoutUseCase,
    )

    response = await simulate_growth_code_set(
        AdminGrowthCodeSetSimulationRequest(
            codes=["PROMO-RAW-SECRET"],
            user_id=user_id,
            plan_id=plan_id,
            currency="USD",
            sale_channel="web",
        ),
        admin,
        db,
    )

    assert response.accepted is True
    assert response.dry_run is True
    assert response.code_set_hash == "dry-run-code-set-hash"
    assert response.applications[0].growth_code_id == growth_code_id
    assert response.applications[0].roles == {"items": ["discount"]}
    assert response.applications[0].discount_snapshot["raw_code"] == "[REDACTED]"
    assert response.applications[0].private_access_snapshot["grant_token"] == "[REDACTED]"
    assert response.trace["reservation_created"] is False
    assert response.trace["payment_created"] is False
    assert calls
    assert calls[0]["user_id"] == user_id
    assert calls[0]["plan_id"] == plan_id
    assert [item.code for item in calls[0]["code_basket"]] == ["PROMO-RAW-SECRET"]

    serialized = response.model_dump_json()
    assert "PROMO-RAW-SECRET" not in serialized
    assert "grant-token-secret" not in serialized


async def test_admin_growth_code_set_simulation_rolls_back_durable_risk_writes(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = await _admin_user(db)
    user_id = uuid4()
    plan_id = uuid4()
    counted_models = (
        RiskSubjectModel,
        PolicyVersionModel,
        RiskModelVersionModel,
        RiskFeatureSnapshotModel,
        GrowthRiskDecisionModel,
        RiskReviewModel,
        GrowthCodeReservationModel,
    )
    before = {model: await _count_rows(db, model) for model in counted_models}

    class FakeCheckoutUseCase:
        def __init__(self, session: AsyncSession) -> None:
            self.session = session

        async def execute(self, **_kwargs: object) -> SimpleNamespace:
            suffix = uuid4().hex
            now = datetime.now(UTC)
            subject = RiskSubjectModel(
                id=uuid4(),
                principal_class="customer",
                principal_subject=str(user_id),
                status="active",
                risk_level="low",
                metadata_payload={"source": "simulation-test"},
            )
            policy = PolicyVersionModel(
                id=uuid4(),
                policy_family="growth_risk",
                policy_key=f"simulation-policy-{suffix}",
                subject_type="global",
                version_number=1,
                payload={"thresholds": {"allow": "0.40"}},
                approval_state="approved",
                version_status="active",
                effective_from=now,
                approved_at=now,
            )
            model = RiskModelVersionModel(
                id=uuid4(),
                model_key=f"simulation-model-{suffix}",
                version="runtime-v6-test",
                artifact_uri="internal://simulation-test",
                artifact_checksum=hashlib.sha256(suffix.encode()).hexdigest(),
                feature_schema_version="growth-risk.v1",
                model_type="deterministic_runtime_guard",
                metrics={},
                calibration={},
                deployment_mode="champion",
                approval_state="approved",
                status="active",
                deployed_at=now,
            )
            self.session.add_all([subject, policy, model])
            await self.session.flush()

            snapshot = RiskFeatureSnapshotModel(
                id=uuid4(),
                risk_subject_id=subject.id,
                feature_schema_version="growth-risk.v1",
                features_payload={"simulation": True},
                feature_hash=hashlib.sha256(f"features-{suffix}".encode()).hexdigest(),
                source_freshness={},
                generated_at=now,
            )
            self.session.add(snapshot)
            await self.session.flush()

            decision = GrowthRiskDecisionModel(
                id=uuid4(),
                risk_subject_id=subject.id,
                action_context="checkout_eval",
                rules_policy_version_id=policy.id,
                model_version_id=model.id,
                feature_snapshot_id=snapshot.id,
                rules_outcome="allow",
                ml_score=Decimal("0.120000"),
                risk_band="low",
                final_action="allow",
                reason_codes=[],
                decision_trace={"simulation": True},
                decided_at=now,
            )
            review = RiskReviewModel(
                id=uuid4(),
                risk_subject_id=subject.id,
                review_type="growth_code",
                status="open",
                decision="pending",
                reason="simulation write that must rollback",
                evidence={},
            )
            self.session.add_all([decision, review])
            await self.session.flush()

            return SimpleNamespace(
                base_price=Decimal("10.00"),
                discount_amount=Decimal("1.00"),
                wallet_amount=Decimal("0.00"),
                gateway_amount=Decimal("9.00"),
                is_zero_gateway=False,
                code_set_hash="dry-run-code-set-hash",
                code_set_acceptance_mode="all_or_nothing",
                private_catalog_grant_id=None,
                code_set_applications=[
                    {
                        "position_entered": 0,
                        "canonical_order": 0,
                        "growth_code_id": str(uuid4()),
                        "legacy_code_type": "promo",
                        "masked_code": "PRO••••",
                        "roles": {"discount": True},
                        "status": "accepted",
                        "risk_decision_id": str(decision.id),
                        "reservation_id": str(uuid4()),
                        "fx_conversion_id": str(uuid4()),
                        "discount": {"applied_amount": "1.00"},
                    }
                ],
            )

    monkeypatch.setattr(
        "src.presentation.api.v3.admin_growth_code_sets.CheckoutUseCase",
        FakeCheckoutUseCase,
    )

    for _ in range(2):
        response = await simulate_growth_code_set(
            AdminGrowthCodeSetSimulationRequest(
                codes=["PROMO-RAW-SECRET"],
                user_id=user_id,
                plan_id=plan_id,
                currency="USD",
                sale_channel="web",
            ),
            admin,
            db,
        )
        assert response.accepted is True
        assert response.trace["risk_decision_persisted"] is False
        assert response.applications[0].risk_decision_id is None
        assert response.applications[0].reservation_id is None
        assert response.applications[0].fx_conversion_id is None
        after = {model: await _count_rows(db, model) for model in counted_models}
        assert after == before
