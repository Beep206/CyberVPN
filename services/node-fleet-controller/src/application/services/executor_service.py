from __future__ import annotations

from src.domain.entities import ExecutionPreview, FleetRequestRecord, OperationRunRecord, OperationStepRecord
from src.infra.database.repositories import FleetRequestRepository
from src.infra.execution.opentofu_executor import ExecutorPlanInput, OpenTofuExecutor


class ExecutorService:
    def __init__(self, repository: FleetRequestRepository, executor: OpenTofuExecutor) -> None:
        self._repository = repository
        self._executor = executor

    async def preview_plan(
        self,
        *,
        request: FleetRequestRecord,
        operation_run: OperationRunRecord,
        stack_slug: str,
        workspace_key: str,
        variables: dict[str, object],
    ) -> tuple[ExecutionPreview, OperationStepRecord]:
        preview = self._executor.build_plan_preview(
            request=request,
            plan_input=ExecutorPlanInput(
                operation_run_id=operation_run.operation_run_id,
                stack_slug=stack_slug,
                workspace_key=workspace_key,
                variables=variables,
            ),
        )
        step = self._executor.build_plan_step(operation_run_id=operation_run.operation_run_id, preview=preview)
        await self._repository.append_operation_step(step)
        return preview, step

