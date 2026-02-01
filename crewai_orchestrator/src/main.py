"""CLI entry point for CyberVPN CrewAI Orchestrator.

Usage:
    python -m src.main feature "Add a referral system"
    python -m src.main feature "Build JWT service" --implement --output-dir /path/to/output
    python -m src.main feature  # interactive prompt
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config.llm_registry import create_llm_registry
from .config.settings import Settings
from .flows.feature_flow import FeatureDevelopmentFlow


def run_feature_flow(request: str, settings: Settings) -> dict:
    """Run the Feature Development Flow and return results."""
    llm_registry = create_llm_registry(settings)

    flow = FeatureDevelopmentFlow(
        llm_registry=llm_registry,
        output_dir=settings.output_dir,
    )
    flow.state.request = request
    flow.state.request_type = "feature"
    flow.state.implementation_mode = settings.implement

    print(f"\n{'='*60}")
    print("CyberVPN CrewAI Orchestrator — Feature Development Flow")
    print(f"{'='*60}")
    print(f"Request: {request}")
    print(f"Model: {settings.model_name}")
    print(f"Implementation mode: {settings.implement}")
    if settings.output_dir:
        print(f"Output dir: {settings.output_dir}")
    print(f"{'='*60}\n")

    flow.kickoff()

    return {
        "request": request,
        "final_output": flow.state.final_output,
        "implementation_result": flow.state.implementation_result,
        "engineering_analysis": flow.state.engineering_analysis[:500],
        "product_analysis": flow.state.product_analysis[:500],
        "execution_plan": flow.state.execution_plan[:500],
        "elapsed_seconds": flow.state.elapsed_seconds,
        "step_times": flow.state.step_times,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="CyberVPN CrewAI Orchestrator")
    parser.add_argument("flow_type", choices=["feature"], help="Flow type to run")
    parser.add_argument("request", nargs="?", default="", help="Feature request description")
    parser.add_argument("--implement", action="store_true", help="Generate actual code files")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for generated code")

    args = parser.parse_args()

    request = args.request or input("Enter feature request: ")
    if not request.strip():
        print("Error: empty request")
        raise SystemExit(1)

    settings = Settings()
    settings.implement = args.implement
    settings.output_dir = args.output_dir

    start = time.time()

    if args.flow_type == "feature":
        result = run_feature_flow(request, settings)
    else:
        print(f"Unknown flow type: {args.flow_type}")
        raise SystemExit(1)

    # Output results
    print(f"\n{'='*60}")
    print("FINAL RESULT")
    print(f"{'='*60}")
    print(result["final_output"])
    if result["implementation_result"]:
        print(f"\nIMPLEMENTATION RESULT:")
        print(result["implementation_result"])
    print(f"\nTotal time: {result['elapsed_seconds']}s")
    print(f"Step times: {json.dumps(result['step_times'], indent=2)}")


if __name__ == "__main__":
    main()
