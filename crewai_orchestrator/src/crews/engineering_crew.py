"""Engineering Crew — CTO manages backend, frontend, mobile, devops, QA specialists."""

from __future__ import annotations

from crewai import Agent, Crew, LLM, Process, Task

from ..agents.base import create_agent
from ..agents.directors import create_cto
from ..agents.specialists.engineering import ENGINEERING_AGENTS, create_engineering_agents


class EngineeringCrew:
    """Engineering department crew with CTO as hierarchical manager."""

    def __init__(self, llm_registry: dict[str, LLM], tools: list | None = None):
        # Manager agent must NOT have tools in hierarchical mode
        self.cto = create_cto(llm_registry, tools=None)
        self.specialists = create_engineering_agents(llm_registry, tools)

    def build(self, tasks: list[Task]) -> Crew:
        """Build a sequential crew (hierarchical has delegation bugs in CrewAI 1.9)."""
        all_agents = [self.cto] + list(self.specialists.values())
        return Crew(
            agents=all_agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
            max_rpm=50,
        )

    def create_analysis_task(self, request: str, execution_plan: str) -> list[Task]:
        """Create tasks for engineering analysis of a feature request."""
        return [
            Task(
                description=f"""Analyze the technical feasibility and architecture impact of this feature request.

REQUEST: {request}

CEO EXECUTION PLAN: {execution_plan}

Your analysis should cover:
1. Technical approach — what components, services, and APIs are affected
2. Architecture impact — does this require new domain entities, migrations, API endpoints?
3. Cross-service impact — frontend, backend, mobile, infrastructure
4. Performance implications — caching, database queries, network calls
5. Estimated effort — which engineering specialists are needed
6. Technical risks and mitigation strategies
7. Suggested implementation sequence with dependencies

Output a structured technical analysis document.""",
                expected_output="A structured technical analysis with approach, architecture impact, effort estimate, risks, and implementation sequence.",
                agent=self.cto,
            ),
            Task(
                description=f"""Based on the CTO's technical analysis, create a detailed implementation plan.

Break down the implementation into specific tasks for each engineering discipline:
- Backend: API endpoints, domain entities, database migrations, business logic
- Frontend: UI components, state management, API integration
- Mobile: Flutter screens, native integrations, platform-specific handling
- DevOps: Infrastructure changes, CI/CD updates, monitoring
- QA: Test strategy, test cases, coverage requirements

For each task, specify:
- What exactly needs to be built/changed
- Which files are affected
- Dependencies on other tasks
- Acceptance criteria""",
                expected_output="Detailed implementation plan broken down by engineering discipline with specific tasks, file changes, and acceptance criteria.",
                agent=self.cto,
            ),
        ]
