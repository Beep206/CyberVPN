from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.presentation.api.v1.admin.vpn_tester import (
    InternalScheduledRunRequest,
    InternalScheduleGateRunRequest,
)


@pytest.mark.parametrize("request_type", [InternalScheduledRunRequest, InternalScheduleGateRunRequest])
def test_internal_vpn_tester_trigger_matches_database_limit(request_type: type) -> None:
    assert request_type(trigger="x" * 40).trigger == "x" * 40

    with pytest.raises(ValidationError):
        request_type(trigger="x" * 41)


def test_internal_runtime_artifact_cannot_be_queued_for_persistence() -> None:
    with pytest.raises(ValidationError, match="generated_vpn_artifacts_require_immediate_execution"):
        InternalScheduledRunRequest(
            suite_key="premium_smart_ru_v1",
            mode="runtime",
            execute_immediately=False,
            context={"generated_mihomo_yaml": "proxies: []"},
        )

    request = InternalScheduledRunRequest(
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        execute_immediately=True,
        context={"generated_mihomo_yaml": "proxies: []"},
    )
    assert request.execute_immediately is True
