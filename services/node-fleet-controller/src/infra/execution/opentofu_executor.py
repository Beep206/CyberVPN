from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from src.config import Settings
from src.domain.entities import ExecutionPreview, FleetRequestRecord, OperationStepRecord
from src.domain.enums import OperationStepStatus

SENSITIVE_VARIABLE_MARKERS = ("token", "secret", "password", "key")


@dataclass(frozen=True)
class ExecutorPlanInput:
    operation_run_id: str
    stack_slug: str
    workspace_key: str
    variables: dict[str, object]


class OpenTofuExecutor:
    """Builds auditable preview-safe execution plans for later live runners."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_plan_preview(self, *, request: FleetRequestRecord, plan_input: ExecutorPlanInput) -> ExecutionPreview:
        stack_dir = str(PurePosixPath(self._settings.opentofu_default_stack_root) / request.environment / plan_input.stack_slug)
        artifact_ref = f"artifacts/opentofu/{plan_input.workspace_key}/{plan_input.operation_run_id}.plan.json"
        command_preview = (
            self._settings.opentofu_binary,
            "-chdir",
            stack_dir,
            "plan",
            "-lock=true",
            f"-out={plan_input.operation_run_id}.tfplan",
        )
        return ExecutionPreview(
            operation_run_id=plan_input.operation_run_id,
            mode="preview" if not self._settings.opentofu_execution_enabled else "live-enabled",
            stack_dir=stack_dir,
            workspace_key=plan_input.workspace_key,
            runner_pool=self._settings.opentofu_runner_pool,
            state_lock_required=True,
            policy_check_required=True,
            plan_artifact_ref=artifact_ref,
            redacted_variables=self._redact_variables(plan_input.variables),
            command_preview=command_preview,
        )

    def build_plan_step(self, *, operation_run_id: str, preview: ExecutionPreview) -> OperationStepRecord:
        return OperationStepRecord(
            operation_step_id=f"step_plan_{operation_run_id}",
            operation_run_id=operation_run_id,
            step_name="create_plan",
            status=OperationStepStatus.PENDING,
            attempt=1,
            artifact_ref=preview.plan_artifact_ref,
        )

    @staticmethod
    def _redact_variables(values: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, value in values.items():
            if any(marker in key.lower() for marker in SENSITIVE_VARIABLE_MARKERS):
                redacted[key] = "***redacted***"
            else:
                redacted[key] = value
        return redacted

