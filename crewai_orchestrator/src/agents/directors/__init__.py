"""Director-level agents for department management."""

from crewai import Agent, LLM

from ..base import create_agent

DIRECTOR_AGENTS = ["cto-architect", "product-manager", "marketing-lead", "finance-strategist"]


def create_cto(llm_registry: dict[str, LLM], tools: list | None = None) -> Agent:
    """CTO — manages Engineering Crew."""
    return create_agent("cto-architect", llm_registry, tools)


def create_product_director(llm_registry: dict[str, LLM], tools: list | None = None) -> Agent:
    """Product Manager — manages Product Crew."""
    return create_agent("product-manager", llm_registry, tools)


def create_marketing_director(llm_registry: dict[str, LLM], tools: list | None = None) -> Agent:
    """Marketing Lead — co-manages Business Crew."""
    return create_agent("marketing-lead", llm_registry, tools)


def create_finance_director(llm_registry: dict[str, LLM], tools: list | None = None) -> Agent:
    """Finance Strategist — co-manages Business Crew."""
    return create_agent("finance-strategist", llm_registry, tools)


def create_all_directors(llm_registry: dict[str, LLM], tools: list | None = None) -> dict[str, Agent]:
    """Create all director agents."""
    return {
        name: create_agent(name, llm_registry, tools)
        for name in DIRECTOR_AGENTS
    }
