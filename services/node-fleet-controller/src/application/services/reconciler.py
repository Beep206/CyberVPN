from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sentry_sdk

from src.domain.entities import NodeRecord, OperationStepRecord, ReconcileExecutionResult, ReconcileWorkItem
from src.domain.enums import (
    BootstrapState,
    CertificateState,
    EnrollmentStatus,
    LifecycleState,
    OperationStatus,
    OperationStepStatus,
    ProviderResourceState,
    RequestStatus,
    RequestType,
)
from src.infra.database.repositories import FleetRequestRepository

from .workflow_engine import WorkflowEngine


class ReconcilerService:
    def __init__(
        self,
        repository: FleetRequestRepository,
        workflow_engine: WorkflowEngine,
    ) -> None:
        self._repository = repository
        self._workflow_engine = workflow_engine

    async def preview(self, *, limit: int = 25) -> list[ReconcileWorkItem]:
        with sentry_sdk.start_span(
            op="controller.reconcile.preview",
            name="node-fleet-controller.reconcile.preview",
        ) as span:
            span.set_data("node_fleet.limit", limit)
            requests = await self._repository.list_pending_requests(limit=limit)
            span.set_data("node_fleet.pending_request_count", len(requests))
            work_items: list[ReconcileWorkItem] = []
            for request in requests:
                operation_runs = await self._repository.get_operation_runs_for_request(request.request_id)
                current_run = operation_runs[-1] if operation_runs else None
                work_items.append(
                    ReconcileWorkItem(
                        request=request,
                        operation_run=current_run,
                        planned_steps=self._workflow_engine.build_plan(request),
                    )
                )
            return work_items

    async def run_once(self, *, limit: int = 25) -> list[ReconcileExecutionResult]:
        with sentry_sdk.start_span(
            op="controller.reconcile.run_once",
            name="node-fleet-controller.reconcile.run_once",
        ) as span:
            span.set_data("node_fleet.limit", limit)
            requests = await self._repository.list_pending_requests(limit=limit)
            span.set_data("node_fleet.pending_request_count", len(requests))
            results: list[ReconcileExecutionResult] = []

            for request in requests:
                operation_runs = await self._repository.get_operation_runs_for_request(request.request_id)
                current_run = operation_runs[-1] if operation_runs else None
                if current_run is None:
                    results.append(
                        ReconcileExecutionResult(
                            request=request,
                            operation_run=None,
                            executed_steps=(),
                            blocked_on_external_dependency=False,
                        )
                    )
                    continue

                if request.status in {RequestStatus.BLOCKED_POLICY, RequestStatus.AWAITING_APPROVAL}:
                    results.append(
                        ReconcileExecutionResult(
                            request=request,
                            operation_run=current_run,
                            executed_steps=(),
                            blocked_on_external_dependency=False,
                        )
                    )
                    continue

                planned_steps = self._workflow_engine.build_plan(request)
                persisted_steps = await self._repository.list_operation_steps(current_run.operation_run_id)
                completed_step_names = {
                    step.step_name
                    for step in persisted_steps
                    if step.status in {OperationStepStatus.RUNNING, OperationStepStatus.SUCCEEDED}
                }
                executed_steps: list[str] = []
                blocked_on_external_dependency = False

                for definition in planned_steps:
                    if definition.step_name in completed_step_names:
                        continue
                    if definition.requires_external_dependency:
                        blocked_on_external_dependency = True
                        break

                    await self._execute_internal_step(
                        request=request,
                        operation_run_id=current_run.operation_run_id,
                        step_name=definition.step_name,
                        target_lifecycle_state=definition.target_lifecycle_state,
                    )
                    completed_step_names.add(definition.step_name)
                    executed_steps.append(definition.step_name)

                next_step_name = next(
                    (
                        definition.step_name
                        for definition in planned_steps
                        if definition.step_name not in completed_step_names
                    ),
                    None,
                )
                request_status = (
                    RequestStatus.RUNNING
                    if blocked_on_external_dependency or next_step_name is not None
                    else RequestStatus.COMPLETED
                )
                operation_status = (
                    OperationStatus.RUNNING
                    if blocked_on_external_dependency or next_step_name is not None
                    else OperationStatus.SUCCEEDED
                )
                finished_at = None if operation_status is OperationStatus.RUNNING else datetime.now(UTC)

                request = await self._repository.update_request_status(request.request_id, request_status) or request
                current_run = (
                    await self._repository.update_operation_run(
                        current_run.operation_run_id,
                        status=operation_status,
                        current_step=next_step_name,
                        finished_at=finished_at,
                    )
                    or current_run
                )

                results.append(
                    ReconcileExecutionResult(
                        request=request,
                        operation_run=current_run,
                        executed_steps=tuple(executed_steps),
                        blocked_on_external_dependency=blocked_on_external_dependency,
                    )
                )

            span.set_data("node_fleet.result_count", len(results))
            return results

    async def _execute_internal_step(
        self,
        *,
        request,
        operation_run_id: str,
        step_name: str,
        target_lifecycle_state: LifecycleState | None,
    ) -> None:
        if step_name == "select_placement":
            await self._ensure_node_for_request(
                request=request,
                operation_run_id=operation_run_id,
                lifecycle_state=target_lifecycle_state or LifecycleState.PLACEMENT_SELECTED,
            )

        await self._repository.append_operation_step(
            OperationStepRecord(
                operation_step_id=f"step_{uuid.uuid4().hex}",
                operation_run_id=operation_run_id,
                step_name=step_name,
                status=OperationStepStatus.SUCCEEDED,
                attempt=1,
            )
        )

    async def _ensure_node_for_request(
        self,
        *,
        request,
        operation_run_id: str,
        lifecycle_state: LifecycleState,
    ) -> None:
        if request.request_type is not RequestType.PROVISIONING:
            return

        existing_nodes = await self._repository.list_nodes_for_request(request.request_id)
        if existing_nodes:
            node = existing_nodes[0]
            await self._repository.upsert_node(
                NodeRecord(
                    node_id=node.node_id,
                    environment=node.environment,
                    role=node.role,
                    country=node.country,
                    provider=node.provider,
                    region=node.region,
                    node_class=node.node_class,
                    current_lifecycle_state=lifecycle_state,
                    enrollment_status=node.enrollment_status,
                    bootstrap_state=node.bootstrap_state,
                    certificate_state=node.certificate_state,
                    provider_resource_state=node.provider_resource_state,
                    request_id=node.request_id,
                    operation_run_id=operation_run_id,
                    created_at=node.created_at,
                )
            )
            return

        country = request.country or "xx"
        region = request.region_selector or "hel1"
        provider = request.provider_selector if request.provider_selector not in {None, "auto"} else "hetzner"
        node_class = request.node_class or "standard"
        node_suffix = request.request_id.removeprefix("req_")[:10]
        node_id = f"node_{country}_{node_suffix}"

        await self._repository.upsert_node(
            NodeRecord(
                node_id=node_id,
                environment=request.environment,
                role="vpn",
                country=country,
                provider=provider,
                region=region,
                node_class=node_class,
                current_lifecycle_state=lifecycle_state,
                enrollment_status=EnrollmentStatus.PENDING,
                bootstrap_state=BootstrapState.NOT_ISSUED,
                certificate_state=CertificateState.NOT_ISSUED,
                provider_resource_state=ProviderResourceState.PLANNED,
                request_id=request.request_id,
                operation_run_id=operation_run_id,
            )
        )
