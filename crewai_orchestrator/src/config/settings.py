from __future__ import annotations

import json
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings


def _read_oauth_token() -> str | None:
    """Read OAuth access token from Claude Code credentials."""
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if not creds_path.exists():
        return None
    try:
        data = json.loads(creds_path.read_text())
        return data.get("claudeAiOauth", {}).get("accessToken")
    except (json.JSONDecodeError, KeyError, OSError):
        return None


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Anthropic API key (from .env or environment)
    anthropic_api_key: SecretStr | None = None

    # Custom API base URL (for proxies)
    anthropic_base_url: str | None = None

    # Optional research provider
    perplexity_api_key: SecretStr | None = None

    # Model configuration — all agents on Opus 4.5
    model_name: str = "anthropic/claude-opus-4-5-20251101"

    # CEO gets extended thinking
    ceo_thinking_budget: int = 10000
    ceo_max_tokens: int = 16000

    # Default max tokens for non-CEO agents
    default_max_tokens: int = 8192

    # Rate limiting (Anthropic tier-dependent)
    max_rpm: int = 50

    # Project paths
    project_root: Path = Path("/home/beep/projects/VPNBussiness")
    agents_dir: Path = Path("/home/beep/projects/VPNBussiness/.claude/agents")

    # Verbose output
    verbose: bool = True

    # Implementation mode
    implement: bool = False
    output_dir: Path | None = None

    def resolve_api_key(self) -> str:
        """Return API key: try .env key first, then Claude Code OAuth token."""
        if self.anthropic_api_key is not None:
            return self.anthropic_api_key.get_secret_value()

        token = _read_oauth_token()
        if token:
            return token

        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY in .env "
            "or log in to Claude Code (OAuth token at ~/.claude/.credentials.json)."
        )


settings = Settings()
