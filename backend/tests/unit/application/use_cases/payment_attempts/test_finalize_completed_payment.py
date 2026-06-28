from __future__ import annotations

from uuid import uuid4

from src.application.use_cases.growth_benefits.fulfill import FulfillmentResult
from src.application.use_cases.payment_attempts.finalize_completed_payment import _benefit_result_payload


def test_benefit_result_payload_scrubs_raw_idempotency_key() -> None:
    raw_key = "growth-benefit:raw-sensitive-benefit-key"

    payload = _benefit_result_payload(
        FulfillmentResult(
            fulfillment_id=uuid4(),
            benefit_id=uuid4(),
            benefit_type="bonus_days",
            growth_code_id=uuid4(),
            idempotency_key=raw_key,
            status="completed",
            duplicate=False,
            result_payload={"side_effect_mode": "reward_allocation"},
        )
    )

    assert "idempotency_key" not in payload
    assert payload["idempotency_key_present"] is True
    assert payload["idempotency_key_hash"].startswith("sha256:")
    assert raw_key not in str(payload)
