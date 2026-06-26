from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.application.services.config_service import CustomerSiteRuntimeConfig

CustomerSiteRouteAction = Literal["allow", "redirect", "maintenance"]


@dataclass(frozen=True, slots=True)
class CustomerSiteRouteDecision:
    action: CustomerSiteRouteAction
    mode: str
    reason: str
    target_host: str | None = None
    target_path: str | None = None
    preserve_query_keys: tuple[str, ...] = ()


class CustomerSiteRuntimePolicy:
    """Pure application policy for frontend/proxy cabinet-only routing decisions."""

    def __init__(self, config: CustomerSiteRuntimeConfig) -> None:
        self._config = config

    def evaluate(self, *, host: str | None, path: str) -> CustomerSiteRouteDecision:
        normalized_host = _normalize_host(host)
        normalized_path = _normalize_path(path)

        if self._config.mode == "maintenance":
            return CustomerSiteRouteDecision(
                action="maintenance",
                mode=self._config.mode,
                reason="customer_site_maintenance",
                preserve_query_keys=self._config.preserve_query_keys,
            )

        if self._config.mode != "cabinet_only":
            return CustomerSiteRouteDecision(
                action="allow",
                mode=self._config.mode,
                reason="full_site",
                preserve_query_keys=self._config.preserve_query_keys,
            )

        if normalized_host in {_normalize_host(item) for item in self._config.cabinet_hosts}:
            return CustomerSiteRouteDecision(
                action="allow",
                mode=self._config.mode,
                reason="cabinet_host",
                preserve_query_keys=self._config.preserve_query_keys,
            )

        if _is_allowed_cabinet_only_path(normalized_path, self._config.allowed_path_prefixes):
            return CustomerSiteRouteDecision(
                action="allow",
                mode=self._config.mode,
                reason="cabinet_only_allowed_path",
                preserve_query_keys=self._config.preserve_query_keys,
            )

        target_host = _first_host(self._config.cabinet_hosts)
        return CustomerSiteRouteDecision(
            action="redirect",
            mode=self._config.mode,
            reason="cabinet_only_marketing_gate",
            target_host=target_host,
            target_path=self._config.cabinet_destination_path,
            preserve_query_keys=self._config.preserve_query_keys,
        )


def _normalize_host(host: str | None) -> str:
    if not host:
        return ""
    return host.split(":", 1)[0].strip().lower()


def _normalize_path(path: str) -> str:
    normalized = path.strip() or "/"
    return normalized if normalized.startswith("/") else f"/{normalized}"


def _is_allowed_cabinet_only_path(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _first_host(hosts: tuple[str, ...]) -> str | None:
    return hosts[0] if hosts else None
