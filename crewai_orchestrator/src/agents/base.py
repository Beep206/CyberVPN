"""Agent factory — converts Claude Code agent .md files to CrewAI Agents."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from crewai import Agent, LLM


# Agents that get the CEO-tier LLM (extended thinking)
CEO_AGENTS = {"ceo-orchestrator"}

# Agents that can delegate to others
DELEGATION_AGENTS = {
    "ceo-orchestrator",
    "cto-architect",
    "product-manager",
    "marketing-lead",
    "finance-strategist",
    "frontend-lead",
    "backend-lead",
    "mobile-lead",
    "devops-lead",
    "qa-lead",
}


def parse_agent_md(path: Path) -> dict:
    """Parse a Claude Code agent .md file into role, goal, backstory.

    Format:
    ---
    name: agent-name
    description: One-line description
    model: opus
    tools: Read, Write, ...
    skills:
      - skill-1
      - skill-2
    ---

    # Agent Title

    System prompt / backstory text...
    """
    content = path.read_text(encoding="utf-8")

    # Split frontmatter from body
    parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)
    if len(parts) < 3:
        raise ValueError(f"Invalid agent file format: {path}")

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()

    # Extract first heading as role title
    heading_match = re.match(r"#\s+(.+?)(?:\s*—.*)?$", body, re.MULTILINE)
    role_title = heading_match.group(1) if heading_match else frontmatter.get("name", path.stem)

    return {
        "name": frontmatter["name"],
        "description": frontmatter.get("description", ""),
        "role": role_title,
        "goal": frontmatter.get("description", f"Perform duties as {role_title}"),
        "backstory": body[:3000],  # Cap backstory to manage context window
        "tools_list": frontmatter.get("tools", "").split(", ") if isinstance(frontmatter.get("tools"), str) else [],
        "skills": frontmatter.get("skills", []),
    }


def create_agent(
    agent_name: str,
    llm_registry: dict[str, LLM],
    tools: list | None = None,
    agents_dir: Path | None = None,
) -> Agent:
    """Create a CrewAI Agent from a Claude Code agent .md file."""
    if agents_dir is None:
        agents_dir = Path("/home/beep/projects/VPNBussiness/.claude/agents")

    md_path = agents_dir / f"{agent_name}.md"
    if not md_path.exists():
        raise FileNotFoundError(f"Agent file not found: {md_path}")

    spec = parse_agent_md(md_path)
    tier = "ceo" if agent_name in CEO_AGENTS else "default"

    return Agent(
        role=spec["role"],
        goal=spec["goal"],
        backstory=spec["backstory"],
        llm=llm_registry[tier],
        tools=tools or [],
        allow_delegation=agent_name in DELEGATION_AGENTS,
        verbose=True,
        max_iter=20,
        max_rpm=50,
        respect_context_window=True,
    )


def create_agents_batch(
    agent_names: list[str],
    llm_registry: dict[str, LLM],
    tools: list | None = None,
    agents_dir: Path | None = None,
) -> dict[str, Agent]:
    """Create multiple agents at once. Returns dict of name -> Agent."""
    return {
        name: create_agent(name, llm_registry, tools, agents_dir)
        for name in agent_names
    }
