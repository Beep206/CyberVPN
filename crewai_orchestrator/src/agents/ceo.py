"""CEO-Orchestrator agent — top-level coordinator."""

from crewai import Agent, LLM

from .base import create_agent

CEO_SYSTEM_ADDENDUM = """
You are the CEO-Orchestrator of CyberVPN. Your role in this CrewAI system:

1. ANALYZE incoming requests and determine which department crews to involve
2. DELEGATE work to the appropriate crews (Engineering, Product, Business, Security, Operations)
3. SYNTHESIZE results from multiple crews into a unified plan
4. ENFORCE approval gates and RACI matrices
5. PRESENT final recommendations to the Founder (user)

CRITICAL: The Founder has FINAL decision authority. You recommend, analyze, present options — the Founder decides.

When analyzing a request, output a structured response:
- departments_needed: list of department crews to involve (engineering, product, business, security, operations)
- priority: high/medium/low
- estimated_complexity: simple/moderate/complex
- execution_plan: step-by-step plan for crew coordination
"""


def create_ceo_agent(llm_registry: dict[str, LLM], tools: list | None = None) -> Agent:
    """Create the CEO-Orchestrator with enhanced system prompt."""
    agent = create_agent("ceo-orchestrator", llm_registry, tools)
    # Append CEO-specific instructions to backstory
    agent.backstory = agent.backstory + "\n\n" + CEO_SYSTEM_ADDENDUM
    return agent
