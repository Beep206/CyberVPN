from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "cybervpn-node-fleet-controller"
    environment: str = "development"
    log_level: str = "INFO"
    sentry_dsn: str = ""
    sentry_release: str = ""
    observability_internal_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "observability_internal_secret",
            "FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET",
        ),
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8085

    database_url: str = "sqlite+aiosqlite:///./node_fleet_controller.db"
    database_echo: bool = False

    nats_url: str = "nats://localhost:4222"
    nats_stream_name: str = "NODE_LIFECYCLE_EVENTS"
    nats_publish_enabled: bool = False
    nats_source: str = "node-fleet-controller"

    opentofu_binary: str = "tofu"
    opentofu_execution_enabled: bool = False
    opentofu_runner_pool: str = "preview-only"
    opentofu_default_stack_root: str = "infra/terraform/live"
    opentofu_plan_timeout_seconds: int = 900

    openbao_enabled: bool = False
    openbao_address: str = "https://127.0.0.1:8200"
    openbao_platform_namespace: str = "platform"
    openbao_bootstrap_auth_mount: str = "auth/approle-bootstrap"
    openbao_fleet_cert_auth_mount: str = "auth/cert-fleet"
    openbao_bootstrap_role: str = "bootstrap-fleet-node-enrollment"
    openbao_fleet_cert_role: str = "fleet-node-enrolled"
    openbao_response_wrap_ttl: str = "15m"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
