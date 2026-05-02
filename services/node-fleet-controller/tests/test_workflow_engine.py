from __future__ import annotations

import unittest

from src.application.services.workflow_engine import WorkflowEngine
from src.domain.entities import FleetRequestRecord
from src.domain.enums import RequestStatus, RequestType


class WorkflowEngineTests(unittest.TestCase):
    def test_failover_plan_contains_guardrails_and_shift(self) -> None:
        request = FleetRequestRecord(
            request_id="req_test",
            request_type=RequestType.FAILOVER,
            requested_by="system",
            idempotency_key="failover-001",
            status=RequestStatus.ACCEPTED,
            environment="prod",
            country="jp",
        )
        steps = WorkflowEngine().build_plan(request)
        self.assertEqual(steps[0].step_name, "evaluate_guardrails")
        self.assertEqual(steps[1].step_name, "create_parallel_capacity")
        self.assertEqual(steps[2].step_name, "canary_traffic_shift")

