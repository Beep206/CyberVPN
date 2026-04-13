"""Normalization helpers for Remnawave payloads consumed by task-worker.

The task-worker still has a number of jobs that expect legacy field names like
``expiresAt`` or ``trafficUp``. These helpers add a small compatibility layer
for current Remnawave 2.7.x payloads while also exposing stable snake_case keys
for future task migrations.
"""

from __future__ import annotations

from typing import Any


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


def normalize_user(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)

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

    return result


def normalize_nodes(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_node(payload) for payload in payloads]
