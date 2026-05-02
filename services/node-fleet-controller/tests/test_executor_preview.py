from __future__ import annotations

import unittest

from src.config import Settings
from src.domain.entities import FleetRequestRecord
from src.domain.enums import RequestStatus, RequestType
from src.infra.execution.opentofu_executor import ExecutorPlanInput, OpenTofuExecutor


class ExecutorPreviewTests(unittest.TestCase):
    def test_preview_redacts_sensitive_variables_and_requires_locking(self) -> None:
        executor = OpenTofuExecutor(
            Settings(opentofu_default_stack_root="infra/terraform/live", environment="test")
        )
        request = FleetRequestRecord(
            request_id="req_exec_1",
            request_type=RequestType.PROVISIONING,
            requested_by="operator@example.com",
            idempotency_key="provision-exec-1",
            status=RequestStatus.ACCEPTED,
            environment="nonprod",
        )
        preview = executor.build_plan_preview(
            request=request,
            plan_input=ExecutorPlanInput(
                operation_run_id="opr_exec_1",
                stack_slug="edge",
                workspace_key="nonprod-fr-standard",
                variables={"country": "fr", "hcloud_token": "top-secret"},
            ),
        )
        self.assertTrue(preview.state_lock_required)
        self.assertEqual(preview.redacted_variables["hcloud_token"], "***redacted***")
        self.assertIn("plan", preview.command_preview)
