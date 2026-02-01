"""Feature Development Flow — CEO orchestrates Engineering + Product crews."""

from __future__ import annotations

import json
import time

from crewai import LLM, Task
from crewai.flow.flow import Flow, and_, listen, start

from pathlib import Path

from ..agents.ceo import create_ceo_agent
from ..crews.engineering_crew import EngineeringCrew
from ..crews.product_crew import ProductCrew
from ..tools.codebase_reader import list_project_files, read_project_file, search_codebase
from ..tools.code_writer import set_output_dir, write_code_file
from ..tools.task_master_bridge import get_task_master_task_detail, get_task_master_tasks
from .state import WorkflowState

ANALYSIS_TOOLS = [read_project_file, search_codebase, list_project_files, get_task_master_tasks, get_task_master_task_detail]
IMPL_TOOLS = ANALYSIS_TOOLS + [write_code_file]


class FeatureDevelopmentFlow(Flow[WorkflowState]):
    """Multi-crew flow for feature development.

    Steps:
    1. CEO analyzes request → determines departments
    2. Engineering Crew + Product Crew run in parallel
    3. CEO synthesizes results into unified plan
    """

    def __init__(self, llm_registry: dict[str, LLM], output_dir: Path | None = None, **kwargs):
        super().__init__(**kwargs)
        self.llm_registry = llm_registry
        self.output_dir = output_dir
        self.ceo = create_ceo_agent(llm_registry, tools=ANALYSIS_TOOLS)
        self.engineering_crew = EngineeringCrew(llm_registry, tools=ANALYSIS_TOOLS)
        self.product_crew = ProductCrew(llm_registry, tools=ANALYSIS_TOOLS)

    @start()
    def analyze_request(self):
        """CEO analyzes the incoming feature request."""
        step_start = time.time()

        analysis_task = Task(
            description=f"""Analyze this feature request and create an execution plan.

FEATURE REQUEST: {self.state.request}

You must determine:
1. Which department crews to involve: "engineering", "product", or both
2. Priority: "high", "medium", or "low"
3. A step-by-step execution plan for the crews

IMPORTANT: For a Feature Development workflow, you should almost always involve BOTH engineering and product.

Respond with a structured analysis including:
- departments_needed (list)
- priority (string)
- execution_plan (detailed text)""",
            expected_output="Structured analysis with departments_needed, priority, and execution_plan.",
            agent=self.ceo,
        )

        # Run CEO analysis as a simple task
        from crewai import Crew, Process

        crew = Crew(agents=[self.ceo], tasks=[analysis_task], process=Process.sequential, verbose=True)
        result = crew.kickoff()

        # Parse CEO output
        self.state.execution_plan = result.raw
        self.state.departments_needed = ["engineering", "product"]  # Default for feature dev
        self.state.priority = "medium"

        # Try to extract structured data from CEO response
        raw = result.raw.lower()
        if "high" in raw:
            self.state.priority = "high"
        elif "low" in raw:
            self.state.priority = "low"

        self.state.step_times["analyze_request"] = round(time.time() - step_start, 2)
        print(f"\n{'='*60}")
        print(f"CEO Analysis complete. Departments: {self.state.departments_needed}")
        print(f"Priority: {self.state.priority}")
        print(f"Time: {self.state.step_times['analyze_request']}s")
        print(f"{'='*60}\n")

    @listen(analyze_request)
    def run_engineering_crew(self):
        """Engineering crew analyzes technical feasibility."""
        if "engineering" not in self.state.departments_needed:
            self.state.engineering_analysis = "N/A — engineering not needed for this request."
            return

        step_start = time.time()
        print("\n>> Starting Engineering Crew...")

        tasks = self.engineering_crew.create_analysis_task(self.state.request, self.state.execution_plan)
        crew = self.engineering_crew.build(tasks)
        result = crew.kickoff()

        self.state.engineering_analysis = result.raw
        self.state.step_times["engineering_crew"] = round(time.time() - step_start, 2)
        print(f"\n>> Engineering Crew done ({self.state.step_times['engineering_crew']}s)")

    @listen(analyze_request)
    def run_product_crew(self):
        """Product crew analyzes requirements and user impact."""
        if "product" not in self.state.departments_needed:
            self.state.product_analysis = "N/A — product not needed for this request."
            return

        step_start = time.time()
        print("\n>> Starting Product Crew...")

        tasks = self.product_crew.create_analysis_task(self.state.request, self.state.execution_plan)
        crew = self.product_crew.build(tasks)
        result = crew.kickoff()

        self.state.product_analysis = result.raw
        self.state.step_times["product_crew"] = round(time.time() - step_start, 2)
        print(f"\n>> Product Crew done ({self.state.step_times['product_crew']}s)")

    @listen(and_(run_engineering_crew, run_product_crew))
    def synthesize_results(self):
        """CEO synthesizes all department outputs into a unified plan."""
        step_start = time.time()
        print("\n>> CEO synthesizing results...")

        synthesis_task = Task(
            description=f"""Synthesize the department analyses into a unified execution plan.

ORIGINAL REQUEST: {self.state.request}

ENGINEERING ANALYSIS:
{self.state.engineering_analysis[:3000]}

PRODUCT ANALYSIS:
{self.state.product_analysis[:3000]}

Create a unified execution plan that:
1. Merges both department recommendations
2. Resolves any conflicts between departments
3. Defines the execution sequence with dependencies
4. Lists specific deliverables and acceptance criteria
5. Identifies risks and mitigation strategies
6. Provides a clear recommendation to the Founder

Format as a structured execution plan ready for Founder approval.""",
            expected_output="Unified execution plan with merged recommendations, sequence, deliverables, and risks.",
            agent=self.ceo,
        )

        from crewai import Crew, Process

        crew = Crew(agents=[self.ceo], tasks=[synthesis_task], process=Process.sequential, verbose=True)
        result = crew.kickoff()

        self.state.synthesized_plan = result.raw
        self.state.final_output = result.raw
        self.state.end_time = time.time()
        self.state.step_times["synthesis"] = round(time.time() - step_start, 2)

        if not self.state.implementation_mode:
            print(f"\n{'='*60}")
            print("FEATURE DEVELOPMENT FLOW COMPLETE (plan only)")
            print(f"Total time: {self.state.elapsed_seconds}s")
            print(f"Step times: {json.dumps(self.state.step_times, indent=2)}")
            print(f"{'='*60}\n")

    @listen(synthesize_results)
    def implement_code(self):
        """Generate actual code files based on the synthesized plan."""
        if not self.state.implementation_mode:
            return

        if self.output_dir is None:
            print("\n>> Skipping implementation: no --output-dir specified.")
            return

        step_start = time.time()
        print(f"\n>> Starting Implementation (output: {self.output_dir})...")

        # Configure the code writer tool with the output directory
        set_output_dir(self.output_dir)

        # Create an implementation agent with write access
        impl_agent = create_ceo_agent(self.llm_registry, tools=IMPL_TOOLS)

        impl_task = Task(
            description=f"""You are a senior engineer. Based on the plan below, write ALL code files
using the write_code_file tool. Write complete, production-ready code.

PLAN:
{self.state.synthesized_plan[:6000]}

ENGINEERING ANALYSIS:
{self.state.engineering_analysis[:4000]}

INSTRUCTIONS:
- Use write_code_file(file_path, content) for each file
- Use relative paths like "src/main.py", "requirements.txt"
- Write complete files, not snippets
- Include all imports, all functions, all classes
- After writing all files, list every file you wrote""",
            expected_output="List of all files written with write_code_file, confirming each was successful.",
            agent=impl_agent,
        )

        from crewai import Crew, Process

        crew = Crew(
            agents=[impl_agent],
            tasks=[impl_task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()

        self.state.implementation_result = result.raw
        self.state.end_time = time.time()
        self.state.step_times["implementation"] = round(time.time() - step_start, 2)

        print(f"\n{'='*60}")
        print("FEATURE DEVELOPMENT FLOW COMPLETE (with implementation)")
        print(f"Total time: {self.state.elapsed_seconds}s")
        print(f"Step times: {json.dumps(self.state.step_times, indent=2)}")
        print(f"{'='*60}\n")
