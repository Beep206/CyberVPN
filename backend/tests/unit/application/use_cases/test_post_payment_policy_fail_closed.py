from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payments.payment_completed_earnings import ProcessPaymentCompletedEarningsUseCase
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.config.settings import settings


def _allowed_policy_result() -> SimpleNamespace:
    return SimpleNamespace(
        qualifying_event=SimpleNamespace(qualifying_first_payment=True),
        payout_rules=SimpleNamespace(
            referral_cash_payout_allowed=True,
            partner_cash_payout_allowed=True,
            no_double_payout=True,
            referral_reason_codes=[],
            partner_reason_codes=[],
        ),
    )


@pytest.mark.asyncio
async def test_post_payment_policy_failure_blocks_referral_and_partner_cash_rewards() -> None:
    payment_id = uuid4()
    user_id = uuid4()
    order_id = uuid4()
    referrer_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("25.00"),
        currency="USD",
        metadata_={},
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=None,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    payment_attempt = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        status="succeeded",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="paid",
        commission_base_amount=Decimal("25.00"),
        storefront_id=uuid4(),
    )
    user = SimpleNamespace(referred_by_user_id=referrer_id, partner_user_id=None)

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=payment_attempt))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("policy unavailable")))
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock())
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._record_earning_event = SimpleNamespace(record=AsyncMock())
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    result = await use_case.execute(payment_id, process_cash_rewards=True)

    assert payment.status == "completed"
    assert result["referral_reward_amount"] is None
    assert result["referral_reward_status"] is None
    assert result["referral_commission"] is None
    assert result["referral_policy_block_reasons"] == ["policy_evaluation_failed"]
    assert result["partner_earning"] is None
    assert result["settlement_earning_event_id"] is None
    assert result["settlement_earning_event_status"] is None
    assert result["partner_policy_block_reasons"] == ["policy_evaluation_failed"]
    use_case._process_referral.execute.assert_not_awaited()
    use_case._create_partner_earning_event.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_post_payment_legacy_partner_earning_is_gated_by_feature_flag(monkeypatch) -> None:
    payment_id = uuid4()
    user_id = uuid4()
    partner_code_id = uuid4()
    partner_user_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("25.00"),
        currency="USD",
        metadata_={"partner_earning_mode": "legacy"},
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=partner_code_id,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    user = SimpleNamespace(referred_by_user_id=None, partner_user_id=partner_user_id)

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=None))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock())
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock())
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._process_partner = SimpleNamespace(execute=AsyncMock())
    use_case._record_earning_event = SimpleNamespace(record=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock())
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    monkeypatch.setattr(settings, "partner_legacy_partner_earning_enabled", False)

    result = await use_case.execute(payment_id, process_cash_rewards=True)

    assert result["partner_earning"] is None
    assert result["settlement_earning_event_id"] is None
    assert result["settlement_earning_event_status"] is None
    assert result["partner_policy_block_reasons"] == ["legacy_partner_earning_disabled"]
    use_case._process_partner.execute.assert_not_awaited()
    use_case._record_earning_event.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_order_legacy_partner_earning_remains_available_with_flag_and_metadata_gate(monkeypatch) -> None:
    payment_id = uuid4()
    user_id = uuid4()
    partner_code_id = uuid4()
    partner_user_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("25.00"),
        currency="USD",
        metadata_={
            "commission_base_amount": "25.00",
            "partner_earning_mode": "legacy",
        },
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=partner_code_id,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    user = SimpleNamespace(referred_by_user_id=None, partner_user_id=partner_user_id)
    earning = SimpleNamespace(total_earning=Decimal("5.00"))

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=None))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock())
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock())
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._process_partner = SimpleNamespace(execute=AsyncMock(return_value=earning))
    use_case._record_earning_event = SimpleNamespace(execute=AsyncMock(), record=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock())
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    monkeypatch.setattr(settings, "partner_legacy_partner_earning_enabled", True)

    result = await use_case.execute(payment_id, process_cash_rewards=True)

    assert result["partner_earning"] == 5.0
    partner_kwargs = use_case._process_partner.execute.await_args.kwargs
    assert partner_kwargs["base_price"] == Decimal("25.00")
    assert partner_kwargs["partner_code_id"] == partner_code_id
    use_case._create_partner_earning_event.execute.assert_not_awaited()
    use_case._record_earning_event.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_backed_referral_reward_uses_order_amount_not_tampered_payment_metadata() -> None:
    payment_id = uuid4()
    user_id = uuid4()
    order_id = uuid4()
    referrer_id = uuid4()
    storefront_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("999.00"),
        currency="USD",
        metadata_={"commission_base_amount": "999.00"},
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=None,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    payment_attempt = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        status="succeeded",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="paid",
        commission_base_amount=Decimal("25.00"),
        storefront_id=storefront_id,
    )
    user = SimpleNamespace(referred_by_user_id=referrer_id, partner_user_id=None)
    reward = SimpleNamespace(quantity=Decimal("2.50"), allocation_status="available")

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=payment_attempt))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock(return_value=_allowed_policy_result()))
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock(return_value=reward))
    use_case._process_partner = SimpleNamespace(execute=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock(return_value=(None, None)))
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._record_earning_event = SimpleNamespace(execute=AsyncMock(), record=AsyncMock())
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    result = await use_case.execute(payment_id, process_cash_rewards=True)

    assert result["referral_reward_amount"] == 2.5
    assert result["referral_reward_status"] == "available"
    referral_kwargs = use_case._process_referral.execute.await_args.kwargs
    assert referral_kwargs["base_amount"] == Decimal("25.00")
    assert referral_kwargs["order_id"] == order_id
    assert referral_kwargs["storefront_id"] == storefront_id
    partner_kwargs = use_case._create_partner_earning_event.execute.await_args.kwargs
    assert partner_kwargs["commission_base_amount"] == Decimal("25.00")
    use_case._process_partner.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_backed_partner_earning_uses_order_amount_and_skips_legacy_metadata_path() -> None:
    payment_id = uuid4()
    user_id = uuid4()
    order_id = uuid4()
    partner_code_id = uuid4()
    partner_user_id = uuid4()
    earning_event_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("1000.00"),
        currency="USD",
        metadata_={
            "commission_base_amount": "1000.00",
            "partner_earning_mode": "legacy",
        },
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=partner_code_id,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    payment_attempt = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        status="succeeded",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="paid",
        commission_base_amount=Decimal("40.00"),
        storefront_id=uuid4(),
    )
    user = SimpleNamespace(referred_by_user_id=None, partner_user_id=partner_user_id)
    earning_event = SimpleNamespace(
        id=earning_event_id,
        total_amount=Decimal("6.00"),
        event_status="available",
    )

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=payment_attempt))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock(return_value=_allowed_policy_result()))
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._process_partner = SimpleNamespace(execute=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock(return_value=(earning_event, None)))
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._record_earning_event = SimpleNamespace(execute=AsyncMock(), record=AsyncMock())
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    result = await use_case.execute(payment_id, process_cash_rewards=True)

    assert result["partner_earning"] == 6.0
    assert result["settlement_earning_event_id"] == str(earning_event_id)
    assert result["settlement_earning_event_status"] == "available"
    partner_kwargs = use_case._create_partner_earning_event.execute.await_args.kwargs
    assert partner_kwargs["commission_base_amount"] == Decimal("40.00")
    use_case._process_partner.execute.assert_not_awaited()
    use_case._record_earning_event.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_backed_zero_commission_does_not_fall_back_to_legacy_metadata_amount() -> None:
    payment_id = uuid4()
    user_id = uuid4()
    order_id = uuid4()
    partner_code_id = uuid4()
    partner_user_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("1000.00"),
        currency="USD",
        metadata_={
            "commission_base_amount": "1000.00",
            "partner_earning_mode": "legacy",
        },
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=partner_code_id,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    payment_attempt = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        status="succeeded",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="paid",
        commission_base_amount=Decimal("0"),
        storefront_id=uuid4(),
    )
    user = SimpleNamespace(referred_by_user_id=None, partner_user_id=partner_user_id)

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=payment_attempt))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock(return_value=_allowed_policy_result()))
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._process_partner = SimpleNamespace(execute=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock())
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._record_earning_event = SimpleNamespace(execute=AsyncMock(), record=AsyncMock())
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    result = await use_case.execute(payment_id, process_cash_rewards=True)

    assert result["partner_earning"] is None
    assert result["settlement_earning_event_id"] is None
    assert result["settlement_earning_event_status"] is None
    use_case._create_partner_earning_event.execute.assert_not_awaited()
    use_case._process_partner.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_post_payment_defaults_to_deferred_cash_rewards_for_order_backed_payment() -> None:
    payment_id = uuid4()
    user_id = uuid4()
    order_id = uuid4()
    referrer_id = uuid4()
    partner_code_id = uuid4()
    partner_user_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("1000.00"),
        currency="USD",
        metadata_={
            "commission_base_amount": "1000.00",
            "partner_earning_mode": "legacy",
        },
        addons_snapshot=[],
        subscription_days=30,
        plan_id=None,
        promo_code_id=None,
        partner_code_id=partner_code_id,
        external_id="provider-reference-not-logged",
        wallet_amount_used=Decimal("0"),
        created_at=datetime.now(UTC),
    )
    payment_attempt = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        status="succeeded",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="paid",
        commission_base_amount=Decimal("40.00"),
        storefront_id=uuid4(),
    )
    user = SimpleNamespace(referred_by_user_id=referrer_id, partner_user_id=partner_user_id)

    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._payment_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempt_repo = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=payment_attempt))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._renewal_orders = SimpleNamespace(get_by_order_id=AsyncMock(return_value=None))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock(return_value=_allowed_policy_result()))
    use_case._user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._process_partner = SimpleNamespace(execute=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock())
    use_case._generate_invites = SimpleNamespace(execute=AsyncMock())
    use_case._issue_gift = SimpleNamespace(execute=AsyncMock())
    use_case._subscription_addons = SimpleNamespace(
        create_batch=AsyncMock(),
        list_active_for_user=AsyncMock(return_value=[]),
    )
    use_case._partner_repo = SimpleNamespace(get_code_by_id=AsyncMock(return_value=None))
    use_case._record_earning_event = SimpleNamespace(execute=AsyncMock(), record=AsyncMock())
    use_case._wallet = SimpleNamespace()
    use_case._config = SimpleNamespace()
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    result = await use_case.execute(payment_id)

    assert result["cash_rewards_deferred"] is True
    assert result["referral_reward_amount"] is None
    assert result["partner_earning"] is None
    assert result["settlement_earning_event_id"] is None
    use_case._policy_evaluator.execute.assert_not_awaited()
    use_case._process_referral.execute.assert_not_awaited()
    use_case._create_partner_earning_event.execute.assert_not_awaited()
    use_case._process_partner.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_payment_completed_worker_uses_order_amount_not_tampered_payment_metadata() -> None:
    payment_id = uuid4()
    user_id = uuid4()
    order_id = uuid4()
    earning_event_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        amount=Decimal("1000.00"),
        provider="wallet",
        currency="USD",
        metadata_={"commission_base_amount": "1000.00"},
        subscription_days=30,
    )
    payment_attempt = SimpleNamespace(
        id=uuid4(),
        payment_id=payment_id,
        order_id=order_id,
        status="succeeded",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="paid",
        commission_base_amount=Decimal("40.00"),
        storefront_id=uuid4(),
    )
    user = SimpleNamespace(referred_by_user_id=None)
    earning_event = SimpleNamespace(
        id=earning_event_id,
        partner_account_id=uuid4(),
        partner_user_id=None,
        total_amount=Decimal("6.00"),
        currency_code="USD",
        event_status="available",
    )

    use_case = ProcessPaymentCompletedEarningsUseCase.__new__(ProcessPaymentCompletedEarningsUseCase)
    use_case._payments = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    use_case._payment_attempts = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=payment_attempt))
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._users = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    use_case._policy_evaluator = SimpleNamespace(execute=AsyncMock(return_value=_allowed_policy_result()))
    use_case._process_referral = SimpleNamespace(execute=AsyncMock())
    use_case._create_partner_earning_event = SimpleNamespace(execute=AsyncMock(return_value=(earning_event, None)))
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    use_case._session = SimpleNamespace(flush=AsyncMock())

    result = await use_case.execute(payment_id=payment_id, source_event_id="event-id")

    assert result["partner_earning"] == "6.00"
    partner_kwargs = use_case._create_partner_earning_event.execute.await_args.kwargs
    assert partner_kwargs["commission_base_amount"] == Decimal("40.00")
    assert partner_kwargs["order_id"] == order_id
    assert partner_kwargs["payment_id"] == payment_id
    use_case._process_referral.execute.assert_not_awaited()
