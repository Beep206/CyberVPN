"""Normalization helpers for Remnawave payloads consumed by task-worker.

The task-worker still has a number of jobs that expect legacy field names like
``expiresAt`` or ``trafficUp``. These helpers expose stable snake_case keys for
the Remnawave 3.4.3 contract while retaining harmless field aliases used by
older task code. Remnawave user identity is numeric from 3.0 onward.
"""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from uuid import UUID

NODE_IP_STATUSES = frozenset(
    {
        "INBOUND",
        "OUTBOUND",
        "MANAGEMENT",
        "TRANSIT",
        "MONITORING",
        "RESERVE",
        "BLOCKED",
        "FLAGGED",
        "DEPRECATED",
        "UNKNOWN",
    }
)


def _pick(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _pick_nested(payload: dict[str, Any], container_key: str, *keys: str) -> Any:
    nested = payload.get(container_key)
    if not isinstance(nested, dict):
        return None
    return _pick(nested, *keys)


def _positive_numeric_id(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _canonical_uuid(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID")
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a UUID") from exc


def normalize_user(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)

    user_id = _positive_numeric_id(_pick(result, "id", "userId", "user_id"), field_name="user id")
    status = str(result.get("status", "")).lower() if result.get("status") is not None else ""
    expire_at = _pick(result, "expire_at", "expireAt", "expiresAt")
    traffic_limit_bytes = _pick(result, "traffic_limit_bytes", "trafficLimitBytes", "dataLimit")
    used_traffic_bytes = _pick(
        result,
        "used_traffic_bytes",
        "usedTrafficBytes",
        "dataUsed",
    )
    if used_traffic_bytes is None:
        used_traffic_bytes = _pick_nested(result, "userTraffic", "usedTrafficBytes")

    lifetime_used_traffic_bytes = _pick(result, "lifetime_used_traffic_bytes", "lifetimeUsedTrafficBytes")
    if lifetime_used_traffic_bytes is None:
        lifetime_used_traffic_bytes = _pick_nested(result, "userTraffic", "lifetimeUsedTrafficBytes")

    online_at = _pick(result, "online_at", "onlineAt")
    if online_at is None:
        online_at = _pick_nested(result, "userTraffic", "onlineAt")

    is_online = _pick(result, "is_online", "isOnline")
    if is_online is None:
        is_online = bool(online_at)

    telegram_id = _pick(result, "telegram_id", "telegramId")
    subscription_url = _pick(result, "subscription_url", "subscriptionUrl", "subscriptionURL")
    auto_renew = _pick(result, "auto_renew", "autoRenew")
    plan_name = _pick(result, "plan_name", "planName", "subscriptionPlan")
    plan_price = _pick(result, "plan_price", "planPrice")
    plan_currency = _pick(result, "plan_currency", "planCurrency")

    if status:
        result["status"] = status

    result["id"] = user_id
    result["user_id"] = user_id
    if user_id is not None:
        result.setdefault("userId", user_id)

    result["expire_at"] = expire_at
    result.setdefault("expireAt", expire_at)
    result.setdefault("expiresAt", expire_at)

    result["traffic_limit_bytes"] = traffic_limit_bytes
    result.setdefault("trafficLimitBytes", traffic_limit_bytes)
    result.setdefault("dataLimit", traffic_limit_bytes)

    result["used_traffic_bytes"] = used_traffic_bytes
    result.setdefault("usedTrafficBytes", used_traffic_bytes)
    result.setdefault("dataUsed", used_traffic_bytes)

    result["lifetime_used_traffic_bytes"] = lifetime_used_traffic_bytes
    result.setdefault("lifetimeUsedTrafficBytes", lifetime_used_traffic_bytes)

    result["online_at"] = online_at
    result.setdefault("onlineAt", online_at)

    result["is_online"] = bool(is_online)
    result["isOnline"] = bool(is_online)

    result["telegram_id"] = telegram_id
    result.setdefault("telegramId", telegram_id)

    result["subscription_url"] = subscription_url
    if subscription_url is not None:
        result.setdefault("subscriptionUrl", subscription_url)

    result["auto_renew"] = bool(auto_renew)
    result.setdefault("autoRenew", bool(auto_renew))

    result["plan_name"] = plan_name
    if plan_name is not None:
        result.setdefault("planName", plan_name)
        result.setdefault("subscriptionPlan", plan_name)

    result["plan_price"] = plan_price
    if plan_price is not None:
        result.setdefault("planPrice", plan_price)

    result["plan_currency"] = plan_currency
    if plan_currency is not None:
        result.setdefault("planCurrency", plan_currency)

    return result


def normalize_users(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_user(payload) for payload in payloads]


def normalize_node(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    versions = result.get("versions")
    if not isinstance(versions, dict):
        versions = {}

    node_id = _positive_numeric_id(_pick(result, "id", "nodeId", "node_id"), field_name="node id")
    node_uuid = _canonical_uuid(_pick(result, "uuid", "nodeUuid", "node_uuid"), field_name="node uuid")
    address = _pick(result, "address", "hostname", "host")
    is_disabled = _pick(result, "is_disabled", "isDisabled")
    if is_disabled is None and "enabled" in result and result["enabled"] is not None:
        is_disabled = not bool(result["enabled"])

    is_connected = _pick(result, "is_connected", "isConnected")
    is_connecting = _pick(result, "is_connecting", "isConnecting")
    country_code = _pick(result, "country_code", "countryCode")
    traffic_up = _pick(result, "traffic_up", "trafficUp", "uploadBytes", "upload_bytes")
    traffic_down = _pick(result, "traffic_down", "trafficDown", "downloadBytes", "download_bytes")
    current_bandwidth = _pick(result, "current_bandwidth", "currentBandwidth")
    used_traffic_bytes = _pick(result, "used_traffic_bytes", "usedTrafficBytes", "trafficUsedBytes")
    node_version = _pick(result, "node_version", "nodeVersion") or _pick(versions, "node")
    xray_version = _pick(result, "xray_version", "xrayVersion") or _pick(versions, "xray")
    active_plugin_uuid = _pick(result, "active_plugin_uuid", "activePluginUuid")
    integration_uuids = _pick(result, "integration_uuids", "integrationUuids")
    if not isinstance(integration_uuids, list) or len(integration_uuids) > 20:
        raise ValueError("integrationUuids must be an array with at most 20 values")
    integration_uuids = [_canonical_uuid(value, field_name="integration uuid") for value in integration_uuids]
    raw_ips = result.get("ips")
    if not isinstance(raw_ips, list) or len(raw_ips) > 64:
        raise ValueError("ips must be an array with at most 64 values")
    ips: list[dict[str, str]] = []
    for item in raw_ips:
        if not isinstance(item, dict):
            raise ValueError("each node IP must be an object")
        raw_ip = item.get("ip")
        raw_status = item.get("status")
        if not isinstance(raw_ip, str) or not isinstance(raw_status, str):
            raise ValueError("each node IP requires ip and status strings")
        try:
            canonical_ip = str(ip_address(raw_ip))
        except ValueError as exc:
            raise ValueError("node IP must be a valid IPv4 or IPv6 address") from exc
        status = raw_status.upper()
        if status not in NODE_IP_STATUSES:
            raise ValueError("node IP status is not supported by Remnawave 3.4")
        ips.append({"ip": canonical_ip, "status": status})

    result["id"] = node_id
    result["node_id"] = node_id
    if node_id is not None:
        result.setdefault("nodeId", node_id)

    result["uuid"] = node_uuid
    result["node_uuid"] = node_uuid
    if node_uuid is not None:
        result.setdefault("nodeUuid", node_uuid)

    result["address"] = address
    if address:
        result.setdefault("hostname", address)

    result["is_disabled"] = bool(is_disabled)
    result["isDisabled"] = bool(is_disabled)
    result["enabled"] = not bool(is_disabled)

    result["is_connected"] = bool(is_connected)
    result["isConnected"] = bool(is_connected)

    result["is_connecting"] = bool(is_connecting)
    result["isConnecting"] = bool(is_connecting)

    result["country_code"] = country_code
    result.setdefault("countryCode", country_code)

    result["traffic_up"] = traffic_up or 0
    result.setdefault("trafficUp", result["traffic_up"])

    result["traffic_down"] = traffic_down or 0
    result.setdefault("trafficDown", result["traffic_down"])

    result["current_bandwidth"] = current_bandwidth or 0
    result.setdefault("currentBandwidth", result["current_bandwidth"])

    result["used_traffic_bytes"] = used_traffic_bytes
    if used_traffic_bytes is not None:
        result.setdefault("usedTrafficBytes", used_traffic_bytes)
        result.setdefault("trafficUsedBytes", used_traffic_bytes)

    result["node_version"] = node_version
    if node_version is not None:
        result.setdefault("nodeVersion", node_version)

    result["xray_version"] = xray_version
    if xray_version is not None:
        result.setdefault("xrayVersion", xray_version)

    result["active_plugin_uuid"] = active_plugin_uuid
    if active_plugin_uuid is not None:
        result.setdefault("activePluginUuid", active_plugin_uuid)

    result["integration_uuids"] = integration_uuids
    result["integrationUuids"] = integration_uuids
    result["ips"] = ips

    return result


def normalize_nodes(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_node(payload) for payload in payloads]
