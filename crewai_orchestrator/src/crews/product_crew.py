"""Product Crew — Product Manager manages design and i18n specialists."""

from __future__ import annotations

from crewai import Agent, Crew, LLM, Process, Task

from ..agents.directors import create_product_director
from ..agents.specialists.product import create_product_agents


class ProductCrew:
    """Product department crew with PM as hierarchical manager."""

    def __init__(self, llm_registry: dict[str, LLM], tools: list | None = None):
        # Manager agent must NOT have tools in hierarchical mode
        self.pm = create_product_director(llm_registry, tools=None)
        self.specialists = create_product_agents(llm_registry, tools)

    def build(self, tasks: list[Task]) -> Crew:
        """Build a sequential crew (hierarchical has delegation bugs in CrewAI 1.9)."""
        all_agents = [self.pm] + list(self.specialists.values())
        return Crew(
            agents=all_agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
            max_rpm=50,
        )

    def create_analysis_task(self, request: str, execution_plan: str) -> list[Task]:
        """Create tasks for product analysis of a feature request."""
        return [
            Task(
                description=f"""Analyze this feature request from a product perspective.

REQUEST: {request}

CEO EXECUTION PLAN: {execution_plan}

Your analysis should cover:
1. User stories — who benefits and how (As a <role>, I want <feature>, so that <benefit>)
2. Requirements decomposition — break into atomic tasks with acceptance criteria
3. Priority assessment — P0 (critical), P1 (important), P2 (nice-to-have)
4. User impact — how many users affected, retention/conversion impact
5. Design requirements — what UI/UX changes are needed
6. Localization impact — new translation keys needed, RTL considerations
7. Dependencies — what must exist before this feature can ship
8. Definition of Done — clear criteria for completion

Output a structured product requirements document.""",
                expected_output="A structured PRD with user stories, requirements, priority, design needs, localization impact, and definition of done.",
                agent=self.pm,
            ),
            Task(
                description=f"""Based on the PM's requirements analysis, assess design and localization needs.

For Design:
- What new UI components or screens are needed?
- Does this follow existing design patterns or require new ones?
- Accessibility considerations (WCAG 2.2 compliance)
- Mobile vs desktop layout differences

For Localization:
- New translation keys needed (list them)
- RTL language considerations (Arabic, Hebrew, Farsi)
- Cultural sensitivity issues
- Content that needs professional translation vs machine translation""",
                expected_output="Design requirements with component list, accessibility notes, and localization plan with translation key list.",
                agent=self.pm,
            ),
        ]
