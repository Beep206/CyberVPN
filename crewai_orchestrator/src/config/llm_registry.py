import os

from crewai import LLM

from .settings import Settings


def create_llm_registry(s: Settings) -> dict[str, LLM]:
    """Create tiered LLM instances for different agent roles."""
    api_key = s.resolve_api_key()

    # CrewAI's native Anthropic provider reads env vars directly.
    os.environ["ANTHROPIC_API_KEY"] = api_key
    if s.anthropic_base_url:
        os.environ["ANTHROPIC_BASE_URL"] = s.anthropic_base_url

    base_url_kwarg = {"base_url": s.anthropic_base_url} if s.anthropic_base_url else {}

    return {
        "ceo": LLM(
            model=s.model_name,
            api_key=api_key,
            max_tokens=s.ceo_max_tokens,
            thinking={"type": "enabled", "budget_tokens": s.ceo_thinking_budget},
            **base_url_kwarg,
        ),
        "default": LLM(
            model=s.model_name,
            api_key=api_key,
            max_tokens=s.default_max_tokens,
            **base_url_kwarg,
        ),
    }
