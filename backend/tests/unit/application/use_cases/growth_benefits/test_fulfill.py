from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from prometheus_client import REGISTRY, generate_latest

from src.application.use_cases.growth_benefits.fulfill import (
    BenefitFulfillmentRecord,
    DuplicateBenefitFulfillmentError,
    DuplicateInviteBatchError,
    FulfillGrowthBenefitsUseCase,
    GrowthBenefitConfigurationError,
    GrowthBenefitSettlementNotEligibleError,
    InviteBatchRecord,
    InviteCodeRecord,
    NewBenefitFulfillment,
    NewInviteBatch,
    NewInviteCode,
    build_growth_benefit_idempotency_key,
    build_invite_batch_idempotency_key,
    copy_fulfillment_with_result,
)

ORDER_ID = UUID("00000000-0000-0000-0000-000000000101")
PAYMENT_ID = UUID("00000000-0000-0000-0000-000000000202")
USER_ID = UUID("00000000-0000-0000-0000-000000000303")
GROWTH_CODE_ID = UUID("00000000-0000-0000-0000-000000000404")
CAMPAIGN_ID = UUID("00000000-0000-0000-0000-000000000505")
BENEFIT_ID = UUID("00000000-0000-0000-0000-000000000606")
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


class FakeGrowthBenefitFulfillmentRepository:
    def __init__(self) -> None:
        self.fulfillments_by_key: dict[str, BenefitFulfillmentRecord] = {}
        self.invite_batches_by_key: dict[str, InviteBatchRecord] = {}
        self.invite_codes_by_batch: dict[UUID, list[InviteCodeRecord]] = {}
        self.create_fulfillment_calls = 0
        self.create_invite_batch_calls = 0
        self.create_invite_code_calls = 0
        self.wallet_credits: list[dict] = []
        self.bonus_days_applications: list[dict] = []
        self.gift_issuances: list[dict] = []
        self.addon_grants: list[dict] = []
        self.duplicate_next_fulfillment_create = False
        self.duplicate_next_invite_batch_create = False

    async def get_fulfillment_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BenefitFulfillmentRecord | None:
        return self.fulfillments_by_key.get(idempotency_key)

    async def create_fulfillment(self, data: NewBenefitFulfillment) -> BenefitFulfillmentRecord:
        self.create_fulfillment_calls += 1
        record = BenefitFulfillmentRecord(
            id=uuid4(),
            benefit_id=data.benefit_id,
            growth_code_id=data.growth_code_id,
            user_id=data.user_id,
            order_id=data.order_id,
            payment_id=data.payment_id,
            idempotency_key=data.idempotency_key,
            status=data.status,
            attempt_count=data.attempt_count,
            config_snapshot=dict(data.config_snapshot),
            result_payload=dict(data.result_payload),
            started_at=data.started_at,
        )
        if self.duplicate_next_fulfillment_create:
            self.duplicate_next_fulfillment_create = False
            self.fulfillments_by_key.setdefault(data.idempotency_key, record)
            raise DuplicateBenefitFulfillmentError(data.idempotency_key)
        self.fulfillments_by_key[data.idempotency_key] = record
        return record

    async def set_fulfillment_result(
        self,
        *,
        fulfillment_id: UUID,
        status: str,
        result_payload: dict,
        completed_at: datetime | None,
    ) -> BenefitFulfillmentRecord:
        for key, record in self.fulfillments_by_key.items():
            if record.id == fulfillment_id:
                updated = copy_fulfillment_with_result(
                    record,
                    status=status,
                    result_payload=result_payload,
                    completed_at=completed_at,
                )
                self.fulfillments_by_key[key] = updated
                return updated
        raise AssertionError("fulfillment id not found")

    async def get_invite_batch_by_idempotency_key(self, idempotency_key: str) -> InviteBatchRecord | None:
        return self.invite_batches_by_key.get(idempotency_key)

    async def create_invite_batch(self, data: NewInviteBatch) -> InviteBatchRecord:
        self.create_invite_batch_calls += 1
        record = InviteBatchRecord(
            id=uuid4(),
            owner_user_id=data.owner_user_id,
            campaign_id=data.campaign_id,
            source_growth_code_id=data.source_growth_code_id,
            source_benefit_id=data.source_benefit_id,
            source_order_id=data.source_order_id,
            source_payment_id=data.source_payment_id,
            source_type=data.source_type,
            requested_count=data.requested_count,
            issued_count=data.issued_count,
            friend_days=data.friend_days,
            expiry_mode=data.expiry_mode,
            expiry_days=data.expiry_days,
            expires_at=data.expires_at,
            entitlement_mode=data.entitlement_mode,
            entitlement_profile_key=data.entitlement_profile_key,
            plan_id=data.plan_id,
            entitlement_snapshot=dict(data.entitlement_snapshot),
            status=data.status,
            idempotency_key=data.idempotency_key,
        )
        if self.duplicate_next_invite_batch_create:
            self.duplicate_next_invite_batch_create = False
            self.invite_batches_by_key.setdefault(data.idempotency_key, record)
            raise DuplicateInviteBatchError(data.idempotency_key)
        self.invite_batches_by_key[data.idempotency_key] = record
        return record

    async def set_invite_batch_issued(
        self,
        *,
        batch_id: UUID,
        issued_count: int,
        status: str,
    ) -> InviteBatchRecord:
        for key, record in self.invite_batches_by_key.items():
            if record.id == batch_id:
                updated = InviteBatchRecord(
                    id=record.id,
                    owner_user_id=record.owner_user_id,
                    campaign_id=record.campaign_id,
                    source_growth_code_id=record.source_growth_code_id,
                    source_benefit_id=record.source_benefit_id,
                    source_order_id=record.source_order_id,
                    source_payment_id=record.source_payment_id,
                    source_type=record.source_type,
                    requested_count=record.requested_count,
                    issued_count=issued_count,
                    friend_days=record.friend_days,
                    expiry_mode=record.expiry_mode,
                    expiry_days=record.expiry_days,
                    expires_at=record.expires_at,
                    entitlement_mode=record.entitlement_mode,
                    entitlement_profile_key=record.entitlement_profile_key,
                    plan_id=record.plan_id,
                    entitlement_snapshot=dict(record.entitlement_snapshot),
                    status=status,
                    idempotency_key=record.idempotency_key,
                )
                self.invite_batches_by_key[key] = updated
                return updated
        raise AssertionError("invite batch id not found")

    async def list_invite_codes_for_batch(self, batch_id: UUID) -> tuple[InviteCodeRecord, ...]:
        return tuple(self.invite_codes_by_batch.get(batch_id, ()))

    async def create_invite_codes(self, data: tuple[NewInviteCode, ...]) -> tuple[InviteCodeRecord, ...]:
        self.create_invite_code_calls += len(data)
        records = tuple(
            InviteCodeRecord(
                id=uuid4(),
                owner_user_id=item.owner_user_id,
                batch_id=item.batch_id,
                source_growth_code_id=item.source_growth_code_id,
                source_benefit_id=item.source_benefit_id,
                source_payment_id=item.source_payment_id,
                free_days=item.free_days,
                expires_at=item.expires_at,
                code_hash=item.code_hash,
                code_prefix=item.code_prefix,
                status="issued",
            )
            for item in data
        )
        for record in records:
            self.invite_codes_by_batch.setdefault(record.batch_id, []).append(record)
        return records

    async def apply_wallet_credit_benefit(
        self,
        *,
        user_id: UUID,
        fulfillment_id: UUID,
        amount,
        currency: str,
        description_key: str,
    ) -> dict:
        for credit in self.wallet_credits:
            if credit["fulfillment_id"] == str(fulfillment_id):
                return {**credit, "duplicate": True}
        credit = {
            "wallet_transaction_id": str(uuid4()),
            "fulfillment_id": str(fulfillment_id),
            "user_id": str(user_id),
            "amount": str(amount),
            "currency": currency,
            "description_key": description_key,
            "balance_after": str(amount),
            "duplicate": False,
        }
        self.wallet_credits.append(credit)
        return credit

    async def apply_bonus_days_benefit(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        fulfillment_id: UUID,
        benefit_id: UUID,
        growth_code_id: UUID,
        days: int,
        grant_mode: str,
        entitlement_profile_key: str | None,
        reversal_mode: str,
        occurred_at: datetime,
    ) -> dict:
        payload = {
            "side_effect_mode": "reward_allocation",
            "growth_reward_allocation_id": str(uuid4()),
            "user_id": str(user_id),
            "order_id": str(order_id),
            "payment_id": str(payment_id),
            "fulfillment_id": str(fulfillment_id),
            "benefit_id": str(benefit_id),
            "growth_code_id": str(growth_code_id),
            "days": days,
            "grant_mode": grant_mode,
            "entitlement_profile_key": entitlement_profile_key,
            "reversal_mode": reversal_mode,
            "occurred_at": occurred_at.isoformat(),
            "duplicate": False,
        }
        self.bonus_days_applications.append(payload)
        return payload

    async def issue_gift_benefit(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        fulfillment_id: UUID,
        benefit_id: UUID,
        growth_code_id: UUID,
        config,
        occurred_at: datetime,
    ) -> dict:
        payload = {
            "gift_batch_id": str(uuid4()),
            "issued_count": config.count,
            "requested_count": config.count,
            "user_id": str(user_id),
            "order_id": str(order_id),
            "payment_id": str(payment_id),
            "fulfillment_id": str(fulfillment_id),
            "benefit_id": str(benefit_id),
            "growth_code_id": str(growth_code_id),
            "issued_at": occurred_at.isoformat(),
            "gift_code_refs": [
                {
                    "id": str(uuid4()),
                    "code_hash": f"{index:064x}",
                    "code_prefix": f"GF{index}",
                    "status": "active",
                }
                for index in range(config.count)
            ],
            "duplicate": False,
        }
        self.gift_issuances.append(payload)
        return payload

    async def grant_addon_benefit(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        fulfillment_id: UUID,
        benefit_id: UUID,
        growth_code_id: UUID,
        config,
        occurred_at: datetime,
    ) -> dict:
        payload = {
            "side_effect_mode": "subscription_addon_grant",
            "subscription_addon_id": str(uuid4()),
            "user_id": str(user_id),
            "order_id": str(order_id),
            "payment_id": str(payment_id),
            "fulfillment_id": str(fulfillment_id),
            "benefit_id": str(benefit_id),
            "growth_code_id": str(growth_code_id),
            "addon_code": config.addon_code,
            "quantity": config.quantity,
            "occurred_at": occurred_at.isoformat(),
            "duplicate": False,
        }
        self.addon_grants.append(payload)
        return payload


def _issue_invites_config(*, allow_zero: bool, count: int = 10) -> dict:
    return {
        "count": count,
        "friend_days": 7,
        "expiry_mode": "relative",
        "expiry_days": 30,
        "absolute_expires_at": None,
        "entitlement_mode": "profile_key",
        "entitlement_profile_key": "invite_limited_access_v1",
        "plan_id": None,
        "entitlement_snapshot": None,
        "allow_zero_net_payment": allow_zero,
        "minimum_net_paid_amount": "0",
        "owner_mode": "buyer",
        "reversal_mode": "revoke_unredeemed",
    }


def _benefit(
    *,
    benefit_id: UUID = BENEFIT_ID,
    benefit_type: str = "issue_invites",
    config: dict | None = None,
    merge_mode: str = "append",
    source_priority: int | None = None,
    trigger_type: str = "payment_completed",
) -> dict:
    payload = {
        "benefit_id": str(benefit_id),
        "type": benefit_type,
        "trigger_type": trigger_type,
        "merge_mode": merge_mode,
        "sort_order": 0,
        "config": config if config is not None else _issue_invites_config(allow_zero=True),
    }
    if source_priority is not None:
        payload["source_priority"] = source_priority
    return payload


def _snapshot(
    *,
    net_paid: str = "0",
    benefits: list[dict] | None = None,
    raw_application_fields: dict | None = None,
) -> dict:
    application = {
        "growth_code_id": str(GROWTH_CODE_ID),
        "campaign_id": str(CAMPAIGN_ID),
        "source_type": "promo",
        "masked_code": "PR-...abcdef12",
        "code_ref": {
            "redacted": True,
            "code_hash": "abcdef1234567890",
            "code_prefix": "PR-",
            "code_length": 16,
        },
        "benefits": benefits if benefits is not None else [_benefit()],
    }
    application.update(raw_application_fields or {})
    return {
        "settlement": {
            "net_customer_paid_amount": net_paid,
            "gateway_amount": net_paid,
            "settlement_mode": "internal_zero" if net_paid == "0" else "external_payment",
        },
        "code_set": {"applications": [application]},
    }


async def _execute(repo: FakeGrowthBenefitFulfillmentRepository, snapshot: dict) -> list:
    return await FulfillGrowthBenefitsUseCase(repo).execute(
        order_id=ORDER_ID,
        payment_id=PAYMENT_ID,
        user_id=USER_ID,
        growth_effects_snapshot=snapshot,
        occurred_at=NOW,
    )


@pytest.mark.asyncio
async def test_issue_invites_records_completed_fulfillment_batch_and_codes_once() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()

    results = await _execute(repo, _snapshot())

    expected_fulfillment_key = build_growth_benefit_idempotency_key(
        benefit_id=BENEFIT_ID,
        payment_id=PAYMENT_ID,
    )
    expected_batch_key = build_invite_batch_idempotency_key(
        benefit_id=BENEFIT_ID,
        payment_id=PAYMENT_ID,
    )
    assert [result.idempotency_key for result in results] == [expected_fulfillment_key]
    assert results[0].status == "completed"
    assert results[0].duplicate is False
    assert len(repo.fulfillments_by_key) == 1
    assert len(repo.invite_batches_by_key) == 1

    fulfillment = repo.fulfillments_by_key[expected_fulfillment_key]
    batch = repo.invite_batches_by_key[expected_batch_key]
    assert fulfillment.config_snapshot["count"] == 10
    assert fulfillment.config_snapshot["allow_zero_net_payment"] is True
    assert fulfillment.config_snapshot["reversal_policy"] == "revoke_if_unused"
    assert fulfillment.result_payload["invite_batch_id"] == str(batch.id)
    assert fulfillment.result_payload["requested_count"] == 10
    assert fulfillment.result_payload["issued_count"] == 10
    assert fulfillment.result_payload["reversal_policy"] == "revoke_if_unused"
    assert len(fulfillment.result_payload["invite_code_ids"]) == 10
    assert len(fulfillment.result_payload["invite_code_refs"]) == 10
    assert {item["status"] for item in fulfillment.result_payload["invite_code_refs"]} == {"issued"}
    assert all(len(item["code_prefix"]) <= 8 for item in fulfillment.result_payload["invite_code_refs"])
    assert all(len(item["code_hash"]) == 64 for item in fulfillment.result_payload["invite_code_refs"])
    assert batch.status == "issued"
    assert batch.issued_count == 10
    assert repo.create_invite_code_calls == 10
    assert len(repo.invite_codes_by_batch[batch.id]) == 10
    assert repo.invite_codes_by_batch[batch.id][0].free_days == 7
    assert batch.owner_user_id == USER_ID
    assert batch.campaign_id == CAMPAIGN_ID
    assert batch.source_growth_code_id == GROWTH_CODE_ID
    assert batch.source_benefit_id == BENEFIT_ID
    assert batch.source_order_id == ORDER_ID
    assert batch.source_payment_id == PAYMENT_ID
    assert batch.requested_count == 10
    assert batch.issued_count == 10
    assert batch.friend_days == 7
    assert batch.expires_at == NOW + timedelta(days=30)
    assert "PR-PRO100-INV10" not in json.dumps(
        {
            "fulfillment": fulfillment,
            "batch": batch,
        },
        default=str,
    )
    metric_payload = generate_latest(REGISTRY).decode()
    assert "growth_benefit_fulfillment_total" in metric_payload
    assert 'benefit_type="issue_invites"' in metric_payload
    assert 'status="completed"' in metric_payload


@pytest.mark.asyncio
async def test_issue_invites_accepts_spec_reversal_policy_without_legacy_mode() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    config = _issue_invites_config(allow_zero=True, count=2)
    config.pop("reversal_mode")
    config["reversal_policy"] = "revoke_if_unused"

    results = await _execute(repo, _snapshot(benefits=[_benefit(config=config)]))

    expected_fulfillment_key = build_growth_benefit_idempotency_key(
        benefit_id=BENEFIT_ID,
        payment_id=PAYMENT_ID,
    )
    fulfillment = repo.fulfillments_by_key[expected_fulfillment_key]
    assert results[0].status == "completed"
    assert fulfillment.config_snapshot["reversal_mode"] == "revoke_if_unused"
    assert fulfillment.config_snapshot["reversal_policy"] == "revoke_if_unused"
    assert fulfillment.result_payload["reversal_policy"] == "revoke_if_unused"


@pytest.mark.asyncio
async def test_wallet_credit_records_completed_fulfillment_and_wallet_side_effect_once() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    wallet_benefit_id = UUID("00000000-0000-0000-0000-000000000611")
    snapshot = _snapshot(
        net_paid="25",
        benefits=[
            _benefit(
                benefit_id=wallet_benefit_id,
                benefit_type="wallet_credit",
                config={
                    "amount": "3.50",
                    "currency": "USD",
                    "description_key": "growth.benefit.walletCredit",
                    "allow_zero_net_payment": False,
                    "minimum_net_paid_amount": "10.00",
                    "reversal_mode": "manual_review",
                },
            )
        ],
    )

    results = await _execute(repo, snapshot)
    replay = await _execute(repo, snapshot)

    assert len(results) == 1
    assert results[0].benefit_id == wallet_benefit_id
    assert results[0].benefit_type == "wallet_credit"
    assert results[0].status == "completed"
    assert results[0].result_payload["side_effect_mode"] == "wallet_transaction"
    assert results[0].result_payload["reversal_policy"] == "manual_review"
    assert results[0].result_payload["wallet_credit"]["amount"] == "3.50"
    assert results[0].result_payload["wallet_credit"]["currency"] == "USD"
    assert len(repo.wallet_credits) == 1
    assert replay[0].duplicate is True
    assert replay[0].result_payload == results[0].result_payload
    assert repo.create_invite_batch_calls == 0
    assert repo.create_invite_code_calls == 0


@pytest.mark.parametrize(
    ("benefit_type", "config", "expected_key", "expected_mode"),
    [
        (
            "bonus_days",
            {
                "days": 14,
                "grant_mode": "create_reward_allocation",
                "entitlement_profile_key": "bonus_access_v1",
                "allow_zero_net_payment": True,
                "minimum_net_paid_amount": "0",
                "reversal_mode": "revoke_unapplied",
            },
            "days",
            "reward_allocation",
        ),
        (
            "issue_gift",
            {
                "count": 2,
                "friend_days": 30,
                "expiry_mode": "relative",
                "expiry_days": 45,
                "absolute_expires_at": None,
                "entitlement_mode": "profile_key",
                "entitlement_profile_key": "gift_access_v1",
                "plan_id": None,
                "entitlement_snapshot": None,
                "allow_zero_net_payment": True,
                "minimum_net_paid_amount": "0",
                "reversal_mode": "revoke_unredeemed",
            },
            "count",
            "gift_code_issuance",
        ),
        (
            "grant_addon",
            {
                "addon_code": "extra_device",
                "quantity": 1,
                "duration_mode": "match_plan",
                "duration_days": None,
                "location_code": None,
                "allow_zero_net_payment": True,
                "minimum_net_paid_amount": "0",
                "reversal_mode": "revoke_addon",
            },
            "addon_code",
            "subscription_addon_grant",
        ),
    ],
)
@pytest.mark.asyncio
async def test_non_invite_non_wallet_benefits_record_completed_persistent_side_effects(
    benefit_type: str,
    config: dict,
    expected_key: str,
    expected_mode: str,
) -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    snapshot = _snapshot(benefits=[_benefit(benefit_type=benefit_type, config=config)])

    results = await _execute(repo, snapshot)

    assert len(results) == 1
    assert results[0].benefit_type == benefit_type
    assert results[0].status == "completed"
    assert results[0].result_payload["benefit_type"] == benefit_type
    assert results[0].result_payload["side_effect_mode"] == expected_mode
    payload_key = "requested_count" if benefit_type == "issue_gift" else expected_key
    assert results[0].result_payload[benefit_type][payload_key] == config[expected_key]
    assert repo.create_fulfillment_calls == 1
    assert repo.create_invite_batch_calls == 0
    assert repo.create_invite_code_calls == 0
    assert len(repo.bonus_days_applications) == (1 if benefit_type == "bonus_days" else 0)
    assert len(repo.gift_issuances) == (1 if benefit_type == "issue_gift" else 0)
    assert len(repo.addon_grants) == (1 if benefit_type == "grant_addon" else 0)


@pytest.mark.asyncio
async def test_wallet_credit_zero_net_without_allow_flag_rejects_before_persistence() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    snapshot = _snapshot(
        benefits=[
            _benefit(
                benefit_type="wallet_credit",
                config={
                    "amount": "5.00",
                    "currency": "USD",
                    "description_key": "growth.benefit.walletCredit",
                    "allow_zero_net_payment": False,
                    "minimum_net_paid_amount": "0",
                    "reversal_mode": "manual_review",
                },
            )
        ]
    )

    with pytest.raises(GrowthBenefitSettlementNotEligibleError, match="zero-net"):
        await _execute(repo, snapshot)

    assert repo.fulfillments_by_key == {}
    assert repo.wallet_credits == []


@pytest.mark.asyncio
async def test_zero_net_without_explicit_allow_flag_rejects_before_persistence() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    snapshot = _snapshot(benefits=[_benefit(config=_issue_invites_config(allow_zero=False))])

    with pytest.raises(GrowthBenefitSettlementNotEligibleError, match="zero-net"):
        await _execute(repo, snapshot)

    assert repo.fulfillments_by_key == {}
    assert repo.invite_batches_by_key == {}


@pytest.mark.asyncio
async def test_issue_invites_config_validation_rejects_invalid_count_without_rows() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    snapshot = _snapshot(benefits=[_benefit(config={**_issue_invites_config(allow_zero=True), "count": 0})])

    with pytest.raises(GrowthBenefitConfigurationError, match="issue_invites"):
        await _execute(repo, snapshot)

    assert repo.fulfillments_by_key == {}
    assert repo.invite_batches_by_key == {}


@pytest.mark.asyncio
async def test_raw_code_material_in_snapshot_is_rejected_without_persistence() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    snapshot = _snapshot(raw_application_fields={"raw_code": "PR-PRO100-INV10"})

    with pytest.raises(GrowthBenefitConfigurationError, match="raw code"):
        await _execute(repo, snapshot)

    assert repo.fulfillments_by_key == {}
    assert repo.invite_batches_by_key == {}


@pytest.mark.asyncio
async def test_existing_completed_fulfillment_returns_existing_without_duplicate_batch() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    fulfillment_key = build_growth_benefit_idempotency_key(benefit_id=BENEFIT_ID, payment_id=PAYMENT_ID)
    batch_id = uuid4()
    repo.fulfillments_by_key[fulfillment_key] = BenefitFulfillmentRecord(
        id=uuid4(),
        benefit_id=BENEFIT_ID,
        growth_code_id=GROWTH_CODE_ID,
        user_id=USER_ID,
        order_id=ORDER_ID,
        payment_id=PAYMENT_ID,
        idempotency_key=fulfillment_key,
        status="completed",
        attempt_count=1,
        config_snapshot=_issue_invites_config(allow_zero=True),
        result_payload={
            "invite_batch_id": str(batch_id),
            "requested_count": 10,
            "issued_count": 10,
            "invite_code_ids": [str(uuid4()) for _ in range(10)],
            "invite_code_refs": [],
        },
    )

    results = await _execute(repo, _snapshot())

    assert results[0].duplicate is True
    assert results[0].status == "completed"
    assert results[0].result_payload["invite_batch_id"] == str(batch_id)
    assert repo.create_fulfillment_calls == 0
    assert repo.create_invite_batch_calls == 0
    assert repo.invite_batches_by_key == {}


@pytest.mark.asyncio
async def test_duplicate_fulfillment_create_race_reuses_existing_row_and_single_batch() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    repo.duplicate_next_fulfillment_create = True

    results = await _execute(repo, _snapshot())

    assert results[0].duplicate is True
    assert results[0].status == "completed"
    assert repo.create_invite_code_calls == 10
    assert repo.create_fulfillment_calls == 1
    assert repo.create_invite_batch_calls == 1
    assert len(repo.fulfillments_by_key) == 1
    assert len(repo.invite_batches_by_key) == 1


@pytest.mark.asyncio
async def test_replace_same_type_merge_records_only_replacing_promo_benefit() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    plan_benefit_id = UUID("00000000-0000-0000-0000-000000000707")
    promo_benefit_id = UUID("00000000-0000-0000-0000-000000000808")
    snapshot = _snapshot(
        benefits=[
            _benefit(
                benefit_id=plan_benefit_id,
                config=_issue_invites_config(allow_zero=True, count=2),
                source_priority=10,
            ),
            _benefit(
                benefit_id=promo_benefit_id,
                config=_issue_invites_config(allow_zero=True, count=10),
                merge_mode="replace_same_type",
                source_priority=30,
            ),
        ]
    )

    results = await _execute(repo, snapshot)

    assert [result.benefit_id for result in results] == [promo_benefit_id]
    assert next(iter(repo.invite_batches_by_key.values())).requested_count == 10


@pytest.mark.asyncio
async def test_max_merge_records_only_largest_invite_count() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    smaller_id = UUID("00000000-0000-0000-0000-000000000909")
    larger_id = UUID("00000000-0000-0000-0000-000000000910")
    snapshot = _snapshot(
        benefits=[
            _benefit(
                benefit_id=smaller_id,
                config=_issue_invites_config(allow_zero=True, count=3),
                merge_mode="max",
                source_priority=10,
            ),
            _benefit(
                benefit_id=larger_id,
                config=_issue_invites_config(allow_zero=True, count=8),
                merge_mode="max",
                source_priority=20,
            ),
        ]
    )

    results = await _execute(repo, snapshot)

    assert [result.benefit_id for result in results] == [larger_id]
    assert next(iter(repo.invite_batches_by_key.values())).requested_count == 8


@pytest.mark.asyncio
async def test_unsettled_dispatch_rejects_without_rows() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()

    with pytest.raises(GrowthBenefitSettlementNotEligibleError, match="completed settlement"):
        await FulfillGrowthBenefitsUseCase(repo).execute(
            order_id=ORDER_ID,
            payment_id=PAYMENT_ID,
            user_id=USER_ID,
            growth_effects_snapshot=_snapshot(),
            settlement_completed=False,
            occurred_at=NOW,
        )

    assert repo.fulfillments_by_key == {}
    assert repo.invite_batches_by_key == {}


@pytest.mark.asyncio
async def test_quote_preview_trigger_is_ignored_by_post_settlement_dispatcher() -> None:
    repo = FakeGrowthBenefitFulfillmentRepository()
    snapshot = _snapshot(benefits=[_benefit(trigger_type="quote_preview")])

    results = await _execute(repo, snapshot)

    assert results == []
    assert repo.fulfillments_by_key == {}
    assert repo.invite_batches_by_key == {}
