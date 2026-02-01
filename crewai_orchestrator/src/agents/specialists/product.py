"""Product department specialist agents."""

from crewai import Agent, LLM

from ..base import create_agents_batch

PRODUCT_AGENTS = [
    "design-lead",
    "i18n-manager",
]


def create_product_agents(llm_registry: dict[str, LLM], tools: list | None = None) -> dict[str, Agent]:
    """Create all product department agents."""
    return create_agents_batch(PRODUCT_AGENTS, llm_registry, tools)
