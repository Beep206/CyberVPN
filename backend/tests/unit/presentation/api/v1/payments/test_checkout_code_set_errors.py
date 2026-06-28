from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.application.use_cases.growth_code_sets.exceptions import CodeSetRejectedError
from src.presentation.api.v1.payments.routes import _raise_checkout_value_error


def test_checkout_code_set_rejection_maps_to_structured_422() -> None:
    applications = [
        {
            "client_slot_id": "slot-1",
            "masked_code": "PRO...A1",
            "status": "accepted",
            "roles": ["discount"],
            "discount": {
                "applied_amount": "10.00",
                "target_currency": "USD",
            },
        },
        {
            "client_slot_id": "slot-2",
            "masked_code": "OLD...99",
            "status": "rejected",
            "reject_reason": "code_expired",
            "user_message_key": "growth_codes.promo.expired",
        },
    ]

    with pytest.raises(HTTPException) as exc_info:
        _raise_checkout_value_error(CodeSetRejectedError(applications=applications))

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == {
        "code": "CODE_SET_REJECTED",
        "message_key": "growth_codes.code_set.rejected",
        "retryable": False,
        "applications": applications,
    }
