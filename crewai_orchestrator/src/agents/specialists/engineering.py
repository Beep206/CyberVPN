"""Engineering department specialist agents."""

from crewai import Agent, LLM

from ..base import create_agents_batch

ENGINEERING_AGENTS = [
    "backend-lead",
    "backend-dev",
    "frontend-lead",
    "ui-engineer",
    "mobile-lead",
    "devops-lead",
    "devops-engineer",
    "qa-lead",
    "test-runner",
    "telegram-bot-dev",
    "task-worker-dev",
]


def create_engineering_agents(llm_registry: dict[str, LLM], tools: list | None = None) -> dict[str, Agent]:
    """Create all engineering department agents."""
    return create_agents_batch(ENGINEERING_AGENTS, llm_registry, tools)
