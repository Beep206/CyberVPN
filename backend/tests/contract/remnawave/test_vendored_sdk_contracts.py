from __future__ import annotations

import importlib
import sys
import tomllib
import types
from functools import lru_cache
from pathlib import Path

from src.infrastructure.remnawave.contracts import (
    RemnawaveBandwidthAnalyticsResponse,
    RemnawaveDeleteResponse,
    RemnawaveNodeResponse,
    RemnawaveRawSystemStatsResponse,
    RemnawaveRecapResponse,
    RemnawaveUserResponse,
)
from src.infrastructure.remnawave.mappers.server_mapper import map_remnawave_server
from src.infrastructure.remnawave.mappers.user_mapper import map_remnawave_user

REPO_ROOT = Path(__file__).resolve().parents[4]
SDK_ROOT = REPO_ROOT / "SDK/python-sdk-production"
SDK_PACKAGE_ROOT = SDK_ROOT / "remnawave"


def _sdk_version() -> str:
    with (SDK_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


@lru_cache(maxsize=1)
def _load_vendored_modules() -> dict[str, types.ModuleType]:
    for name in list(sys.modules):
        if name == "remnawave" or name.startswith("remnawave."):
            del sys.modules[name]

    root_package = types.ModuleType("remnawave")
    root_package.__path__ = [str(SDK_PACKAGE_ROOT)]
    sys.modules["remnawave"] = root_package

    models_package = types.ModuleType("remnawave.models")
    models_package.__path__ = [str(SDK_PACKAGE_ROOT / "models")]
    sys.modules["remnawave.models"] = models_package

    utils_package = types.ModuleType("remnawave.utils")
    utils_package.__path__ = [str(SDK_PACKAGE_ROOT / "utils")]
    sys.modules["remnawave.utils"] = utils_package

    return {
        "users": importlib.import_module("remnawave.models.users"),
        "nodes": importlib.import_module("remnawave.models.nodes"),
        "system": importlib.import_module("remnawave.models.system"),
    }


def _user_payload() -> dict[str, object]:
    return {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "shortUuid": "SUB12345",
        "username": "demo-user",
        "status": "ACTIVE",
        "trafficLimitBytes": 10737418240,
        "trafficLimitStrategy": "NO_RESET",
        "expireAt": "2027-12-31T23:59:59+00:00",
        "subscriptionUuid": "550e8400-e29b-41d4-a716-446655440001",
        "trojanPassword": "Sup3rSecret123",
        "vlessUuid": "550e8400-e29b-41d4-a716-446655440002",
        "ssPassword": "Sup3rSecret321",
        "lastTriggeredThreshold": 0,
        "createdAt": "2026-04-12T12:00:00+00:00",
        "updatedAt": "2026-04-12T12:00:00+00:00",
        "subscriptionUrl": "https://vpn.example.com/sub/demo-user",
        "activeInternalSquads": [
            {
                "uuid": "550e8400-e29b-41d4-a716-446655440003",
                "name": "Default-Squad",
            }
        ],
        "userTraffic": {
            "usedTrafficBytes": 1024,
            "lifetimeUsedTrafficBytes": 2048,
            "onlineAt": "2026-04-12T12:05:00+00:00",
            "firstConnectedAt": "2026-04-10T10:00:00+00:00",
            "lastConnectedNodeUuid": "550e8400-e29b-41d4-a716-446655440004",
        },
    }


def _node_payload() -> dict[str, object]:
    return {
        "uuid": "550e8400-e29b-41d4-a716-446655440010",
        "name": "fra-01",
        "address": "10.0.0.1",
        "port": 443,
        "isConnected": True,
        "isDisabled": False,
        "isConnecting": False,
        "xrayUptime": "24h",
        "isTrafficTrackingActive": True,
        "trafficLimitBytes": 1099511627776,
        "trafficUsedBytes": 123456789,
        "usersOnline": 42,
        "viewPosition": 1,
        "countryCode": "DE",
        "consumptionMultiplier": 1.0,
        "createdAt": "2026-04-12T12:00:00+00:00",
        "updatedAt": "2026-04-12T12:00:00+00:00",
        "configProfile": {
            "activeConfigProfileUuid": None,
            "activeInbounds": [],
        },
    }


def _system_stats_payload() -> dict[str, object]:
    return {
        "cpu": {"cores": 8},
        "memory": {"total": 1024, "free": 256, "used": 768},
        "uptime": 12345.0,
        "timestamp": 1712923200,
        "users": {
            "statusCounts": {"ACTIVE": 100, "EXPIRED": 2},
            "totalUsers": 102,
        },
        "onlineStats": {
            "lastDay": 50,
            "lastWeek": 75,
            "neverOnline": 4,
            "onlineNow": 12,
        },
        "nodes": {
            "totalOnline": 8,
            "totalBytesLifetime": "999999",
        },
    }


def _recap_payload() -> dict[str, object]:
    return {
        "thisMonth": {"users": 10, "traffic": "12345"},
        "total": {
            "users": 102,
            "nodes": 9,
            "traffic": "999999",
            "nodesRam": "64 GB",
            "nodesCpuCores": 32,
            "distinctCountries": 5,
        },
        "version": "2.7.4",
        "initDate": "2026-01-01T00:00:00+00:00",
    }


def _bandwidth_payload() -> dict[str, object]:
    return {
        "bandwidthLastTwoDays": {"current": "111", "previous": "90", "difference": "21"},
        "bandwidthLastSevenDays": {"current": "777", "previous": "700", "difference": "77"},
        "bandwidthLast30Days": {"current": "3000", "previous": "2800", "difference": "200"},
        "bandwidthCalendarMonth": {"current": "1200", "previous": "1100", "difference": "100"},
        "bandwidthCurrentYear": {"current": "24000", "previous": "20000", "difference": "4000"},
    }


def test_vendored_sdk_version_is_pinned_to_2_7_4():
    assert _sdk_version() == "2.7.4"


def test_user_payload_matches_vendored_sdk_and_internal_contract():
    vendored_users = _load_vendored_modules()["users"]
    payload = _user_payload()

    vendored = vendored_users.GetUserByUuidResponseDto.model_validate(payload)
    internal = RemnawaveUserResponse.model_validate(payload)
    mapped = map_remnawave_user(internal.model_dump(by_alias=True, mode="json"))

    assert vendored.user_traffic.used_traffic_bytes == internal.used_traffic_bytes == 1024
    assert vendored.user_traffic.lifetime_used_traffic_bytes == internal.lifetime_used_traffic_bytes == 2048
    assert vendored.subscription_url == internal.subscription_url
    assert mapped.status.value == "active"
    assert mapped.used_traffic_bytes == 1024


def test_node_payload_matches_vendored_sdk_and_internal_contract():
    vendored_nodes = _load_vendored_modules()["nodes"]
    payload = _node_payload()

    vendored = vendored_nodes.GetOneNodeResponseDto.model_validate(payload)
    internal = RemnawaveNodeResponse.model_validate(payload)
    mapped = map_remnawave_server(internal.model_dump(by_alias=True, mode="json"))

    assert int(vendored.traffic_used_bytes or 0) == internal.used_traffic_bytes == 123456789
    assert vendored.users_online == internal.users_online == 42
    assert mapped.used_traffic_bytes == 123456789


def test_system_stats_payload_matches_vendored_sdk_and_internal_contract():
    vendored_system = _load_vendored_modules()["system"]
    payload = _system_stats_payload()

    vendored = vendored_system.GetStatsResponseDto.model_validate(payload)
    internal = RemnawaveRawSystemStatsResponse.model_validate(payload)

    assert vendored.users.total_users == internal.users.total_users == 102
    assert vendored.online_stats.online_now == internal.online_stats.online_now == 12
    assert int(vendored.nodes.total_bytes_lifetime) == internal.nodes.total_bytes_lifetime == 999999


def test_recap_payload_matches_vendored_sdk_and_internal_contract():
    vendored_system = _load_vendored_modules()["system"]
    payload = _recap_payload()

    vendored = vendored_system.GetRecapResponseDto.model_validate(payload)
    internal = RemnawaveRecapResponse.model_validate(payload)

    assert vendored.total.nodes == internal.total.nodes == 9
    assert int(vendored.total.traffic) == internal.total.traffic == 999999
    assert vendored.this_month.users == internal.this_month.users == 10


def test_bandwidth_payload_matches_vendored_sdk_and_internal_contract():
    vendored_system = _load_vendored_modules()["system"]
    payload = _bandwidth_payload()

    vendored = vendored_system.GetBandwidthStatsResponseDto.model_validate(payload)
    internal = RemnawaveBandwidthAnalyticsResponse.model_validate(payload)

    assert int(vendored.last_two_days.current) == internal.bandwidth_last_two_days.current == 111
    assert int(vendored.last_seven_days.difference) == internal.bandwidth_last_seven_days.difference == 77
    assert int(vendored.calendar_month.current) == internal.bandwidth_calendar_month.current == 1200


def test_delete_ack_matches_vendored_sdk_and_internal_contract():
    vendored_users = _load_vendored_modules()["users"]
    payload = {"isDeleted": True}

    vendored = vendored_users.DeleteUserResponseDto.model_validate(payload)
    internal = RemnawaveDeleteResponse.model_validate(payload)

    assert vendored.is_deleted is True
    assert internal.is_deleted is True
