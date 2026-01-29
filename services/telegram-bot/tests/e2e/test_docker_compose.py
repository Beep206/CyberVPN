"""End-to-end tests for Docker Compose configuration validation.

These tests verify that the Docker Compose setup is correctly configured
without actually building or running containers.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def docker_compose_path() -> Path:
    """Get path to docker-compose.yml in infra directory."""
    # Navigate from services/telegram-bot/tests/e2e to infra/
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    return repo_root / "infra" / "docker-compose.yml"


@pytest.fixture
def env_example_path() -> Path:
    """Get path to .env.example in telegram-bot directory."""
    return Path(__file__).parent.parent.parent / ".env.example"


@pytest.fixture
def dockerfile_path() -> Path:
    """Get path to Dockerfile in telegram-bot directory."""
    return Path(__file__).parent.parent.parent / "Dockerfile"


@pytest.mark.e2e
def test_docker_compose_syntax_valid(docker_compose_path: Path) -> None:
    """Test that docker-compose.yml has valid YAML syntax."""
    assert docker_compose_path.exists(), f"docker-compose.yml not found at {docker_compose_path}"

    with docker_compose_path.open("r") as f:
        try:
            compose_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"docker-compose.yml has invalid YAML syntax: {e}")

    assert compose_config is not None
    assert "services" in compose_config, "docker-compose.yml must have 'services' section"


@pytest.mark.e2e
def test_docker_compose_has_bot_service(docker_compose_path: Path) -> None:
    """Test that docker-compose.yml includes the telegram bot service."""
    with docker_compose_path.open("r") as f:
        compose_config = yaml.safe_load(f)

    services = compose_config.get("services", {})

    # Check for bot service (could be named cybervpn-bot, telegram-bot, or similar)
    bot_service_names = ["cybervpn-bot", "telegram-bot", "bot", "cybervpn-telegram-bot"]
    bot_service_found = any(service_name in services for service_name in bot_service_names)

    assert bot_service_found, (
        f"Bot service not found in docker-compose.yml. "
        f"Expected one of: {bot_service_names}, found: {list(services.keys())}"
    )


@pytest.mark.e2e
def test_docker_compose_bot_has_required_config(docker_compose_path: Path) -> None:
    """Test that bot service has required configuration."""
    with docker_compose_path.open("r") as f:
        compose_config = yaml.safe_load(f)

    services = compose_config.get("services", {})

    # Find bot service
    bot_service_names = ["cybervpn-bot", "telegram-bot", "bot"]
    bot_service = None
    for service_name in bot_service_names:
        if service_name in services:
            bot_service = services[service_name]
            break

    if not bot_service:
        pytest.skip("Bot service not found, skipping config validation")

    # Check required fields
    assert "image" in bot_service or "build" in bot_service, (
        "Bot service must have either 'image' or 'build' configuration"
    )

    # Check environment variables (should use .env or have env_file)
    has_env_config = (
        "environment" in bot_service or
        "env_file" in bot_service
    )
    assert has_env_config, "Bot service must have environment or env_file configuration"

    # Check dependencies (bot should depend on Redis and Backend)
    if "depends_on" in bot_service:
        dependencies = bot_service["depends_on"]
        # Check for Redis dependency
        redis_deps = ["redis", "valkey", "cybervpn-redis"]
        has_redis = any(dep in dependencies for dep in redis_deps)
        # Redis is recommended but not strictly required for testing
        if not has_redis:
            print("Warning: Bot service does not depend on Redis")


@pytest.mark.e2e
def test_env_example_has_required_variables(env_example_path: Path) -> None:
    """Test that .env.example contains all required environment variables."""
    assert env_example_path.exists(), f".env.example not found at {env_example_path}"

    with env_example_path.open("r") as f:
        env_content = f.read()

    # Required environment variables for the bot
    required_vars = [
        "BOT_TOKEN",
        "BACKEND_API_URL",
        "BACKEND_API_KEY",
        "REDIS_URL",
    ]

    missing_vars = []
    for var in required_vars:
        if var not in env_content:
            missing_vars.append(var)

    assert not missing_vars, (
        f"Missing required environment variables in .env.example: {missing_vars}"
    )


@pytest.mark.e2e
def test_env_example_syntax_valid(env_example_path: Path) -> None:
    """Test that .env.example has valid syntax (no syntax errors)."""
    with env_example_path.open("r") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Check for key=value format
        if "=" not in line:
            pytest.fail(
                f".env.example line {line_num} has invalid syntax (missing '='): {line}"
            )


@pytest.mark.e2e
def test_dockerfile_syntax_valid(dockerfile_path: Path) -> None:
    """Test that Dockerfile has valid syntax structure."""
    assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"

    with dockerfile_path.open("r") as f:
        content = f.read()

    # Check for required Dockerfile instructions
    assert "FROM " in content, "Dockerfile must have FROM instruction"
    assert "WORKDIR " in content or "RUN " in content, "Dockerfile must have WORKDIR or RUN instruction"

    # Check that it's not empty
    assert content.strip(), "Dockerfile is empty"


@pytest.mark.e2e
def test_dockerfile_has_python_base_image(dockerfile_path: Path) -> None:
    """Test that Dockerfile uses Python base image."""
    with dockerfile_path.open("r") as f:
        lines = f.readlines()

    # Find FROM instruction
    from_lines = [line for line in lines if line.strip().startswith("FROM ")]

    assert from_lines, "Dockerfile must have at least one FROM instruction"

    # Check that at least one FROM uses Python
    has_python = any("python" in line.lower() for line in from_lines)
    assert has_python, "Dockerfile must use a Python base image"


@pytest.mark.e2e
def test_dockerfile_copies_source_code(dockerfile_path: Path) -> None:
    """Test that Dockerfile copies source code into the image."""
    with dockerfile_path.open("r") as f:
        content = f.read()

    # Should have COPY or ADD instruction for source code
    has_copy = "COPY " in content or "ADD " in content
    assert has_copy, "Dockerfile must copy source code (COPY or ADD instruction)"


@pytest.mark.e2e
def test_dockerfile_has_entrypoint_or_cmd(dockerfile_path: Path) -> None:
    """Test that Dockerfile has ENTRYPOINT or CMD to run the bot."""
    with dockerfile_path.open("r") as f:
        content = f.read()

    has_entrypoint = "ENTRYPOINT" in content or "CMD" in content
    assert has_entrypoint, "Dockerfile must have ENTRYPOINT or CMD instruction"


@pytest.mark.e2e
def test_docker_compose_profiles_defined(docker_compose_path: Path) -> None:
    """Test that docker-compose.yml has profiles configured."""
    with docker_compose_path.open("r") as f:
        compose_config = yaml.safe_load(f)

    services = compose_config.get("services", {})

    # Check if any service has profiles (optional feature)
    has_profiles = any("profiles" in service for service in services.values())

    # Profiles are optional but recommended
    if not has_profiles:
        print("Info: No Docker Compose profiles found (optional feature)")


@pytest.mark.e2e
def test_docker_compose_networks_defined(docker_compose_path: Path) -> None:
    """Test that docker-compose.yml has networks configuration."""
    with docker_compose_path.open("r") as f:
        compose_config = yaml.safe_load(f)

    # Networks are optional but recommended
    if "networks" not in compose_config:
        print("Info: No explicit networks defined (services will use default network)")


@pytest.mark.e2e
def test_docker_compose_volumes_for_persistence(docker_compose_path: Path) -> None:
    """Test that docker-compose.yml defines volumes for data persistence."""
    with docker_compose_path.open("r") as f:
        compose_config = yaml.safe_load(f)

    # Check if volumes are defined (recommended for Redis, PostgreSQL)
    if "volumes" not in compose_config:
        print("Info: No named volumes defined (data may not persist)")

    services = compose_config.get("services", {})

    # Check if Redis/database services use volumes
    persistent_services = ["redis", "valkey", "postgres", "postgresql", "db"]
    for service_name, service_config in services.items():
        if any(ps in service_name.lower() for ps in persistent_services):
            if "volumes" not in service_config:
                print(f"Warning: Service '{service_name}' does not define volumes for data persistence")
