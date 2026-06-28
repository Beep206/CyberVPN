from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.application.services.config_service import CustomerSiteRuntimeConfig
from src.infrastructure.monitoring.instrumentation.growth_codes import observe_customer_site_policy_decision

CustomerSiteRouteAction = Literal["allow", "redirect", "maintenance", "not_found"]
CustomerSiteRouteClass = Literal["cabinet", "auth", "marketing", "legal", "operational", "unknown"]

_AUTH_PATH_PREFIXES = (
    "/login",
    "/register",
    "/verify",
    "/verify-email",
    "/forgot-password",
    "/reset-password",
    "/magic-link",
    "/oauth",
    "/telegram-link",
    "/onboarding",
)


@dataclass(frozen=True, slots=True)
class CustomerSiteRouteDecision:
    action: CustomerSiteRouteAction
    mode: str
    reason: str
    target_host: str | None = None
    target_path: str | None = None
    preserve_query_keys: tuple[str, ...] = ()
    route_class: CustomerSiteRouteClass = "unknown"


class CustomerSiteRuntimePolicy:
    """Pure application policy for frontend/proxy cabinet-only routing decisions."""

    def __init__(self, config: CustomerSiteRuntimeConfig) -> None:
        self._config = config

    def evaluate(self, *, host: str | None, path: str) -> CustomerSiteRouteDecision:
        normalized_host = _normalize_host(host)
        normalized_path = _normalize_path(path)
        route_class = _classify_route(normalized_path, self._config)
        public_hosts = {_normalize_host(item) for item in self._config.public_hosts}
        cabinet_hosts = {_normalize_host(item) for item in self._config.cabinet_hosts}
        scoped_host = normalized_host in public_hosts or normalized_host in cabinet_hosts

        if self._config.mode == "maintenance":
            if route_class in {"legal", "operational"}:
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="allow",
                        mode=self._config.mode,
                        reason="maintenance_safe_route",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )
            if not scoped_host:
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="allow",
                        mode=self._config.mode,
                        reason="host_out_of_scope",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )
            return self._decision(
                CustomerSiteRouteDecision(
                    action="maintenance",
                    mode=self._config.mode,
                    reason="customer_site_maintenance",
                    preserve_query_keys=self._config.preserve_query_keys,
                    route_class=route_class,
                )
            )

        if self._config.mode != "cabinet_only":
            return self._decision(
                CustomerSiteRouteDecision(
                    action="allow",
                    mode=self._config.mode,
                    reason="full_site",
                    preserve_query_keys=self._config.preserve_query_keys,
                    route_class=route_class,
                )
            )

        if normalized_host in cabinet_hosts:
            if route_class in {"cabinet", "auth", "legal", "operational"}:
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="allow",
                        mode=self._config.mode,
                        reason="cabinet_allowed_path",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )
            if self._config.cabinet_marketing_route_action == "allow":
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="allow",
                        mode=self._config.mode,
                        reason="cabinet_marketing_allowed",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )
            if self._config.cabinet_marketing_route_action == "not_found":
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="not_found",
                        mode=self._config.mode,
                        reason="cabinet_marketing_not_found",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )
            return self._decision(
                CustomerSiteRouteDecision(
                    action="redirect",
                    mode=self._config.mode,
                    reason="cabinet_marketing_redirect_public",
                    target_host=_first_host(self._config.public_hosts),
                    target_path=self._config.public_marketing_destination_path,
                    preserve_query_keys=self._config.preserve_query_keys,
                    route_class=route_class,
                )
            )

        if normalized_host in public_hosts:
            if route_class in {"legal", "operational"}:
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="allow",
                        mode=self._config.mode,
                        reason="cabinet_only_public_safe_path",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )
            if _is_allowed_cabinet_only_path(normalized_path, self._config.allowed_path_prefixes):
                return self._decision(
                    CustomerSiteRouteDecision(
                        action="allow",
                        mode=self._config.mode,
                        reason="cabinet_only_allowed_path",
                        preserve_query_keys=self._config.preserve_query_keys,
                        route_class=route_class,
                    )
                )

            target_host = _first_host(self._config.cabinet_hosts)
            return self._decision(
                CustomerSiteRouteDecision(
                    action="redirect",
                    mode=self._config.mode,
                    reason="cabinet_only_marketing_gate",
                    target_host=target_host,
                    target_path=self._config.cabinet_destination_path,
                    preserve_query_keys=self._config.preserve_query_keys,
                    route_class=route_class,
                )
            )

        return self._decision(
            CustomerSiteRouteDecision(
                action="allow",
                mode=self._config.mode,
                reason="host_out_of_scope",
                preserve_query_keys=self._config.preserve_query_keys,
                route_class=route_class,
            )
        )

    def _decision(self, decision: CustomerSiteRouteDecision) -> CustomerSiteRouteDecision:
        observe_customer_site_policy_decision(
            mode=decision.mode,
            action=decision.action,
            route_class=decision.route_class,
            reason=decision.reason,
        )
        return decision


def _normalize_host(host: str | None) -> str:
    if not host:
        return ""
    return host.split(":", 1)[0].strip().lower()


def _normalize_path(path: str) -> str:
    normalized = path.strip() or "/"
    return normalized if normalized.startswith("/") else f"/{normalized}"


def _is_allowed_cabinet_only_path(path: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        normalized_prefix = prefix.rstrip("/") or "/"
        if normalized_prefix == "/":
            return True
        if prefix.endswith("/"):
            if path == normalized_prefix or path.startswith(prefix):
                return True
            continue
        if path == normalized_prefix or path.startswith(f"{normalized_prefix}/"):
            return True
    return False


def _classify_route(path: str, config: CustomerSiteRuntimeConfig) -> CustomerSiteRouteClass:
    if _is_allowed_cabinet_only_path(path, config.legal_path_prefixes):
        return "legal"
    if _is_allowed_cabinet_only_path(path, config.operational_path_prefixes):
        return "operational"
    if _is_allowed_cabinet_only_path(path, _AUTH_PATH_PREFIXES):
        return "auth"
    if _is_allowed_cabinet_only_path(path, config.cabinet_allowed_prefixes):
        return "cabinet"
    if path == "/" or path.startswith("/"):
        return "marketing"
    return "unknown"


def _first_host(hosts: tuple[str, ...]) -> str | None:
    return hosts[0] if hosts else None
