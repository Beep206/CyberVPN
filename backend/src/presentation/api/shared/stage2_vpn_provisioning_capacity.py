"""S2 VPN provisioning, subscription delivery and capacity contract.

The module is side-effect free: it evaluates redacted evidence collected from
Remnawave, CyberVPN config delivery and the VPN node runtime without exposing
raw subscription URLs, VLESS credentials or provider tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import parse_qs, urlsplit

from src.infrastructure.remnawave.stage1_ru_bundle import (
    STAGE1_RU_BUNDLE_TEMPLATE_NAME,
    is_stage1_ru_bundle_plan,
)
from src.presentation.api.shared.stage1_vpn_protocols import (
    STAGE1_DEFAULT_VPN_PROFILE_ID,
    STAGE1_XHTTP_VPN_PROFILE_ID,
)

S2_SUBSCRIPTION_PUBLIC_HOST = "cyber-vpn.org"
S2_SUBSCRIPTION_PUBLIC_PATH_PREFIX = "/api/sub"
S2_NODE_HOST_SUFFIX = ".cyber-vpn.org"
S2_REQUIRED_NODE_TRANSPORT_PORTS = frozenset({443, 8443})
S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE = 25
S2_FULL_PUBLIC_MIN_CONNECTED_NODES = 2


class S2VpnReadinessState(StrEnum):
    """S2 VPN readiness outcome."""

    READY = "ready"
    READY_WITH_LIMITS = "ready_with_limits"
    BLOCKED = "blocked"


class S2VpnDeliveryMethod(StrEnum):
    """Primary customer config delivery method."""

    SUBSCRIPTION_URL = "subscription_url"
    RAW_PROXY_URI = "raw_proxy_uri"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class S2VpnLinkEvidence:
    """Sanitized single-link evidence from subscription output."""

    scheme: str
    host: str | None
    transport: str | None
    security: str | None
    flow: str | None = None


@dataclass(frozen=True, slots=True)
class S2VpnSubscriptionDeliverySnapshot:
    """Redacted config delivery snapshot for one user/access flow."""

    primary_config: str | None
    subscription_url: str | None
    links: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class S2VpnSubscriptionDeliveryDecision:
    """Customer/support-safe subscription delivery decision."""

    readiness_state: S2VpnReadinessState
    primary_method: S2VpnDeliveryMethod
    subscription_host: str | None
    link_count: int
    vless_reality_raw_present: bool
    vless_reality_xhttp_present: bool
    node_hosts: tuple[str, ...]
    issues: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.readiness_state != S2VpnReadinessState.BLOCKED

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "readiness_state": self.readiness_state.value,
            "primary_method": self.primary_method.value,
            "subscription_host": self.subscription_host,
            "link_count": self.link_count,
            "vless_reality_raw_present": self.vless_reality_raw_present,
            "vless_reality_xhttp_present": self.vless_reality_xhttp_present,
            "node_hosts": list(self.node_hosts),
            "issues": list(self.issues),
        }


@dataclass(frozen=True, slots=True)
class S2VpnNodeEvidence:
    """Sanitized node runtime evidence."""

    name: str
    host: str
    connected: bool
    disabled: bool
    country_code: str | None
    open_transport_ports: frozenset[int] = field(default_factory=frozenset)
    node_only_runtime: bool = True


@dataclass(frozen=True, slots=True)
class S2VpnNodeCapacityDecision:
    """S2 node/capacity decision."""

    readiness_state: S2VpnReadinessState
    connected_nodes: int
    usable_nodes: int
    max_public_canary_users: int
    full_public_opening_allowed: bool
    second_node_required_before_full_public: bool
    issues: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()

    @property
    def canary_allowed(self) -> bool:
        return self.readiness_state != S2VpnReadinessState.BLOCKED and self.usable_nodes > 0

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "readiness_state": self.readiness_state.value,
            "connected_nodes": self.connected_nodes,
            "usable_nodes": self.usable_nodes,
            "max_public_canary_users": self.max_public_canary_users,
            "full_public_opening_allowed": self.full_public_opening_allowed,
            "second_node_required_before_full_public": self.second_node_required_before_full_public,
            "issues": list(self.issues),
            "recommendations": list(self.recommendations),
        }


@dataclass(frozen=True, slots=True)
class S2RuBundleDecision:
    """Decision for RU-only Mihomo bundle routing."""

    plan_code: str | None
    should_apply_ru_bundle: bool
    template_name: str | None
    allowed: bool
    issues: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "plan_code": self.plan_code,
            "should_apply_ru_bundle": self.should_apply_ru_bundle,
            "template_name": self.template_name,
            "allowed": self.allowed,
            "issues": list(self.issues),
        }


def evaluate_s2_subscription_delivery(
    snapshot: S2VpnSubscriptionDeliverySnapshot,
) -> S2VpnSubscriptionDeliveryDecision:
    """Evaluate subscription URL and VLESS/XHTTP delivery expectations."""

    primary_method = _detect_delivery_method(snapshot.primary_config)
    subscription_host = _hostname(snapshot.subscription_url)
    link_evidence = tuple(_parse_link(link) for link in snapshot.links)
    node_hosts = tuple(sorted({item.host for item in link_evidence if item.host}))

    issues: list[str] = []
    if primary_method != S2VpnDeliveryMethod.SUBSCRIPTION_URL:
        issues.append("primary_config_must_be_subscription_url")
    if subscription_host != S2_SUBSCRIPTION_PUBLIC_HOST:
        issues.append("subscription_url_must_use_cyber_vpn_org")
    if snapshot.subscription_url and not _path_starts_with(
        snapshot.subscription_url,
        S2_SUBSCRIPTION_PUBLIC_PATH_PREFIX,
    ):
        issues.append("subscription_url_must_use_api_sub_path")
    if any(
        host and not host.endswith(S2_NODE_HOST_SUFFIX) and host != S2_SUBSCRIPTION_PUBLIC_HOST
        for host in node_hosts
    ):
        issues.append("node_links_must_use_org_hostnames")

    vless_reality_raw_present = any(
        item.scheme == "vless"
        and item.security == "reality"
        and (item.transport in {"tcp", "raw", ""} or item.transport is None)
        for item in link_evidence
    )
    vless_reality_xhttp_present = any(
        item.scheme == "vless" and item.security == "reality" and item.transport == "xhttp" for item in link_evidence
    )
    if not vless_reality_raw_present:
        issues.append(f"missing_{STAGE1_DEFAULT_VPN_PROFILE_ID}")
    if not vless_reality_xhttp_present:
        issues.append(f"missing_{STAGE1_XHTTP_VPN_PROFILE_ID}")

    return S2VpnSubscriptionDeliveryDecision(
        readiness_state=S2VpnReadinessState.BLOCKED if issues else S2VpnReadinessState.READY,
        primary_method=primary_method,
        subscription_host=subscription_host,
        link_count=len(snapshot.links),
        vless_reality_raw_present=vless_reality_raw_present,
        vless_reality_xhttp_present=vless_reality_xhttp_present,
        node_hosts=node_hosts,
        issues=tuple(issues),
    )


def evaluate_s2_node_capacity(nodes: tuple[S2VpnNodeEvidence, ...]) -> S2VpnNodeCapacityDecision:
    """Evaluate S2 node inventory and conservative public-opening capacity."""

    issues: list[str] = []
    recommendations: list[str] = []

    connected_nodes = sum(1 for node in nodes if node.connected)
    usable_nodes = 0
    for node in nodes:
        node_issues = _node_issues(node)
        if node_issues:
            issues.extend(f"{node.name}:{issue}" for issue in node_issues)
            continue
        usable_nodes += 1

    if not nodes:
        issues.append("no_vpn_nodes_reported")
    if usable_nodes == 0:
        issues.append("no_usable_connected_vpn_nodes")

    full_public_allowed = usable_nodes >= S2_FULL_PUBLIC_MIN_CONNECTED_NODES
    second_node_required = not full_public_allowed
    if second_node_required and usable_nodes > 0:
        recommendations.append("add_second_vpn_node_before_unrestricted_public_opening")
        recommendations.append("keep_s2_public_release_as_small_canary_until_second_node_exists")

    if issues:
        state = S2VpnReadinessState.BLOCKED
    elif second_node_required:
        state = S2VpnReadinessState.READY_WITH_LIMITS
    else:
        state = S2VpnReadinessState.READY

    return S2VpnNodeCapacityDecision(
        readiness_state=state,
        connected_nodes=connected_nodes,
        usable_nodes=usable_nodes,
        max_public_canary_users=usable_nodes * S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE,
        full_public_opening_allowed=full_public_allowed,
        second_node_required_before_full_public=second_node_required,
        issues=tuple(issues),
        recommendations=tuple(recommendations),
    )


def evaluate_s2_ru_bundle(
    *,
    plan_code: str | None,
    template_name: str | None,
    external_squad_uuid_present: bool,
) -> S2RuBundleDecision:
    """Ensure Mihomo RU bundle is used only for approved RU plans."""

    normalized_plan_code = plan_code.strip().lower() if plan_code else None
    should_apply = is_stage1_ru_bundle_plan(normalized_plan_code)
    issues: list[str] = []
    if should_apply:
        if template_name != STAGE1_RU_BUNDLE_TEMPLATE_NAME:
            issues.append("ru_plan_requires_mihomo_ru_bundle_template")
        if not external_squad_uuid_present:
            issues.append("ru_plan_requires_external_squad")
    else:
        if external_squad_uuid_present or template_name == STAGE1_RU_BUNDLE_TEMPLATE_NAME:
            issues.append("non_ru_plan_must_not_use_ru_bundle")

    return S2RuBundleDecision(
        plan_code=normalized_plan_code,
        should_apply_ru_bundle=should_apply,
        template_name=template_name,
        allowed=not issues,
        issues=tuple(issues),
    )


def build_s2_support_reprovisioning_steps() -> tuple[str, ...]:
    """Support-safe recovery steps for paid/trial config delivery failures."""

    return (
        "check_customer_lifecycle_state",
        "confirm_payment_or_trial_entitlement",
        "confirm_remnawave_uuid_exists",
        "check_subscription_url_uses_cyber_vpn_org",
        "check_provisioning_retry_job_state",
        "retry_or_recreate_remnawave_user_if_authorized",
        "refresh_stored_subscription_url",
        "ask_user_to_refresh_mini_app_or_bot_config",
        "escalate_to_ops_if_node_or_remnawave_unavailable",
    )


def _node_issues(node: S2VpnNodeEvidence) -> tuple[str, ...]:
    issues: list[str] = []
    if not node.connected:
        issues.append("node_not_connected")
    if node.disabled:
        issues.append("node_disabled")
    if not node.host.endswith(S2_NODE_HOST_SUFFIX):
        issues.append("node_host_must_use_org")
    if not S2_REQUIRED_NODE_TRANSPORT_PORTS.issubset(node.open_transport_ports):
        issues.append("missing_required_transport_ports")
    if not node.node_only_runtime:
        issues.append("vpn_node_must_remain_node_only")
    if not node.country_code:
        issues.append("node_country_missing")
    return tuple(issues)


def _detect_delivery_method(config: str | None) -> S2VpnDeliveryMethod:
    if not config:
        return S2VpnDeliveryMethod.EMPTY
    try:
        parsed = urlsplit(config)
    except ValueError:
        return S2VpnDeliveryMethod.UNKNOWN
    if parsed.scheme in {"http", "https"}:
        return S2VpnDeliveryMethod.SUBSCRIPTION_URL
    if parsed.scheme in {"vless", "vmess", "trojan", "ss", "shadowsocks"}:
        return S2VpnDeliveryMethod.RAW_PROXY_URI
    return S2VpnDeliveryMethod.UNKNOWN


def _parse_link(link: str) -> S2VpnLinkEvidence:
    try:
        parsed = urlsplit(link)
    except ValueError:
        return S2VpnLinkEvidence(scheme="", host=None, transport=None, security=None)
    query = parse_qs(parsed.query)
    return S2VpnLinkEvidence(
        scheme=parsed.scheme.lower(),
        host=parsed.hostname,
        transport=_first_query_value(query, "type"),
        security=_first_query_value(query, "security"),
        flow=_first_query_value(query, "flow"),
    )


def _first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    if not values:
        return None
    return values[0].strip().lower()


def _hostname(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlsplit(url).hostname
    except ValueError:
        return None


def _path_starts_with(url: str, prefix: str) -> bool:
    try:
        return urlsplit(url).path.startswith(prefix)
    except ValueError:
        return False


__all__ = [
    "S2_FULL_PUBLIC_MIN_CONNECTED_NODES",
    "S2_NODE_HOST_SUFFIX",
    "S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE",
    "S2_REQUIRED_NODE_TRANSPORT_PORTS",
    "S2_SUBSCRIPTION_PUBLIC_HOST",
    "S2_SUBSCRIPTION_PUBLIC_PATH_PREFIX",
    "S2RuBundleDecision",
    "S2VpnDeliveryMethod",
    "S2VpnLinkEvidence",
    "S2VpnNodeCapacityDecision",
    "S2VpnNodeEvidence",
    "S2VpnReadinessState",
    "S2VpnSubscriptionDeliveryDecision",
    "S2VpnSubscriptionDeliverySnapshot",
    "build_s2_support_reprovisioning_steps",
    "evaluate_s2_node_capacity",
    "evaluate_s2_ru_bundle",
    "evaluate_s2_subscription_delivery",
]
