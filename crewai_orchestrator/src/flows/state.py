"""Flow state models for CrewAI orchestration."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field


class WorkflowState(BaseModel):
    """Shared state across all Flow steps."""

    # Input
    request: str = ""
    request_type: str = "feature"  # feature, pricing, incident

    # CEO analysis
    departments_needed: list[str] = Field(default_factory=list)
    execution_plan: str = ""
    priority: str = "medium"

    # Department outputs
    engineering_analysis: str = ""
    product_analysis: str = ""
    business_analysis: str = ""
    security_analysis: str = ""

    # Synthesis
    synthesized_plan: str = ""
    final_output: str = ""

    # Implementation
    implementation_mode: bool = False
    implementation_result: str = ""
    files_written: list[str] = Field(default_factory=list)

    # Metrics
    start_time: float = Field(default_factory=time.time)
    end_time: float = 0.0
    step_times: dict[str, float] = Field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)
