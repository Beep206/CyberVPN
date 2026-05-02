from __future__ import annotations

import sentry_sdk

from src.domain.entities import FleetRequestRecord, WorkflowStepDefinition
from src.domain.enums import LifecycleState, RequestType
from src.domain.exceptions import UnsupportedRequestTypeError


class WorkflowEngine:
    """Maps durable request types to canonical workflow steps."""

    def build_plan(self, request: FleetRequestRecord) -> tuple[WorkflowStepDefinition, ...]:
        with sentry_sdk.start_span(
            op="workflow.plan",
            name="node-fleet-controller.workflow.build_plan",
        ) as span:
            span.set_data("node_fleet.request_type", request.request_type.value)
            span.set_data("node_fleet.request_environment", request.environment)

            if request.request_type is RequestType.PROVISIONING:
                return (
                    WorkflowStepDefinition("select_placement", LifecycleState.PLACEMENT_SELECTED),
                    WorkflowStepDefinition(
                        "create_plan",
                        LifecycleState.PLAN_CREATED,
                        requires_external_dependency=True,
                    ),
                    WorkflowStepDefinition("apply_infrastructure", LifecycleState.APPLYING_INFRA, True),
                    WorkflowStepDefinition("issue_bootstrap", LifecycleState.BOOTSTRAP_ISSUED, True),
                    WorkflowStepDefinition("await_enrollment", LifecycleState.ENROLLING, True),
                    WorkflowStepDefinition("verify_node", LifecycleState.VERIFYING, True),
                    WorkflowStepDefinition("admit_traffic", LifecycleState.TRAFFIC_ELIGIBLE, True),
                )
            if request.request_type is RequestType.REPLACEMENT:
                return (
                    WorkflowStepDefinition("create_replacement_capacity", LifecycleState.REQUESTED, True),
                    WorkflowStepDefinition("verify_replacement", LifecycleState.VERIFYING, True),
                    WorkflowStepDefinition("drain_target_node", LifecycleState.DRAINING, True),
                    WorkflowStepDefinition("terminate_target_node", LifecycleState.TERMINATING, True),
                )
            if request.request_type is RequestType.DRAIN:
                return (
                    WorkflowStepDefinition("revoke_traffic", LifecycleState.DRAINING, True),
                    WorkflowStepDefinition("await_drain_completion", LifecycleState.DRAINING, True),
                    WorkflowStepDefinition("mark_ready_for_termination", LifecycleState.READY),
                )
            if request.request_type is RequestType.QUARANTINE:
                return (
                    WorkflowStepDefinition("isolate_runtime", LifecycleState.QUARANTINED, True),
                    WorkflowStepDefinition("record_revocation_requirements", LifecycleState.QUARANTINED, True),
                )
            if request.request_type is RequestType.FAILOVER:
                return (
                    WorkflowStepDefinition("evaluate_guardrails", LifecycleState.REQUESTED),
                    WorkflowStepDefinition("create_parallel_capacity", LifecycleState.REQUESTED, True),
                    WorkflowStepDefinition("canary_traffic_shift", LifecycleState.READY, True),
                    WorkflowStepDefinition("drain_or_quarantine_impaired_nodes", LifecycleState.DRAINING, True),
                )
            raise UnsupportedRequestTypeError(f"Unsupported request type: {request.request_type}")
