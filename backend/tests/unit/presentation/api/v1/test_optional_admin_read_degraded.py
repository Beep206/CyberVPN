from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx
import pytest

from src.application.services.helix_service import HelixDisabledError
from src.infrastructure.remnawave.contracts import RemnawaveConfigProfileResponse, RemnawaveSnippetResponse
from src.presentation.api.v1.config_profiles import routes as config_profile_routes
from src.presentation.api.v1.helix import routes as helix_routes
from src.presentation.api.v1.hosts import routes as host_routes
from src.presentation.api.v1.hosts.schemas import HostResponse
from src.presentation.api.v1.inbounds import routes as inbound_routes
from src.presentation.api.v1.node_plugins import routes as node_plugin_routes
from src.presentation.api.v1.settings import routes as setting_routes
from src.presentation.api.v1.snippets import routes as snippet_routes
from src.presentation.api.v1.subscriptions import routes as subscription_routes
from src.presentation.api.v1.xray import routes as xray_routes


def _http_status_error(status_code: int, path: str = "/api/hosts") -> httpx.HTTPStatusError:
    request = httpx.Request("GET", f"https://remnawave.invalid{path}")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"Remnawave returned {status_code}", request=request, response=response)


class _FailingRemnawaveClient:
    def __init__(self, exc_factory: Callable[[], Exception]) -> None:
        self._exc_factory = exc_factory

    async def get_list_validated(self, *_args, **_kwargs):
        raise self._exc_factory()

    async def get_collection_validated(self, *_args, **_kwargs):
        raise self._exc_factory()

    async def get_validated(self, *_args, **_kwargs):
        raise self._exc_factory()


class _RecordingRemnawaveClient:
    def __init__(self) -> None:
        self.collection_calls: list[tuple[str, str, type[object]]] = []

    async def get_list_validated(self, *_args, **_kwargs):
        raise AssertionError("admin optional list routes must accept Remnawave keyed collection envelopes")

    async def get_collection_validated(self, path: str, collection_key: str, schema: type[object], **_kwargs):
        self.collection_calls.append((path, collection_key, schema))
        return []

    async def get_validated(self, *_args, **_kwargs):
        raise AssertionError("unexpected single-object Remnawave read")


class _DisabledHelixService:
    async def list_nodes(self):
        raise HelixDisabledError("helix disabled")

    async def list_transport_profiles(self):
        raise HelixDisabledError("helix disabled")


def test_optional_remnawave_admin_lists_degrade_when_upstream_endpoint_is_missing() -> None:
    client = _FailingRemnawaveClient(lambda: _http_status_error(404))

    assert asyncio.run(host_routes.list_hosts(_current_user=object(), client=client)) == []
    assert asyncio.run(config_profile_routes.list_config_profiles(current_user=object(), client=client)) == []
    assert asyncio.run(inbound_routes.list_inbounds(current_user=object(), client=client)) == []
    assert asyncio.run(setting_routes.get_settings(current_user=object(), client=client)) == []
    assert asyncio.run(snippet_routes.list_snippets(current_user=object(), client=client)) == []

    subscription_response = asyncio.run(
        subscription_routes.list_subscription_templates(current_user=object(), client=client)
    )
    assert subscription_response.total == 0
    assert subscription_response.templates == []


def test_optional_remnawave_admin_objects_degrade_to_safe_empty_shapes() -> None:
    client = _FailingRemnawaveClient(lambda: httpx.ConnectError("remnawave unavailable"))

    node_plugins = asyncio.run(node_plugin_routes.list_node_plugins(_current_user=object(), client=client))
    assert node_plugins.total == 0
    assert node_plugins.node_plugins == []
    assert node_plugins.model_dump(by_alias=True) == {"total": 0, "nodePlugins": []}

    torrent_stats = asyncio.run(node_plugin_routes.get_torrent_blocker_stats(_current_user=object(), client=client))
    assert torrent_stats.stats.total_reports == 0
    assert torrent_stats.stats.reports_last_24_hours == 0
    assert torrent_stats.top_users == []
    assert torrent_stats.top_nodes == []
    torrent_payload = torrent_stats.model_dump(by_alias=True)
    assert {"distinctNodes", "distinctUsers", "totalReports", "reportsLast24Hours"} <= torrent_payload["stats"].keys()
    assert {"topUsers", "topNodes"} <= torrent_payload.keys()

    xray_config = asyncio.run(xray_routes.get_xray_config(current_user=object(), client=client))
    assert xray_config.inbounds == []
    assert xray_config.outbounds == []
    assert xray_config.routing == {"rules": []}


def test_optional_remnawave_admin_reads_do_not_hide_auth_failures() -> None:
    client = _FailingRemnawaveClient(lambda: _http_status_error(401))

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        asyncio.run(host_routes.list_hosts(_current_user=object(), client=client))

    assert exc_info.value.response.status_code == 401


def test_optional_remnawave_admin_lists_accept_keyed_collection_envelopes() -> None:
    client = _RecordingRemnawaveClient()

    assert asyncio.run(host_routes.list_hosts(_current_user=object(), client=client)) == []
    assert asyncio.run(config_profile_routes.list_config_profiles(current_user=object(), client=client)) == []
    assert asyncio.run(snippet_routes.list_snippets(current_user=object(), client=client)) == []

    assert client.collection_calls == [
        ("/hosts", "hosts", HostResponse),
        ("/config-profiles", "configProfiles", RemnawaveConfigProfileResponse),
        ("/snippets", "snippets", RemnawaveSnippetResponse),
    ]


def test_host_response_accepts_remnawave_2_8_host_shape() -> None:
    host = HostResponse.model_validate(
        {
            "uuid": "host-1",
            "remark": "Edge XHTTP",
            "address": "edge.example.net",
            "port": 443,
            "host": "cdn.example.net",
            "path": "/xhttp",
            "alpn": "h2,http/1.1",
            "isDisabled": False,
            "securityLayer": "tls",
            "inbound": {
                "configProfileUuid": "profile-1",
                "configProfileInboundUuid": "inbound-1",
            },
        }
    )

    assert host.name == "Edge XHTTP"
    assert host.host_header == "cdn.example.net"
    assert host.alpn == ["h2", "http/1.1"]
    assert host.is_disabled is False


def test_helix_admin_read_lists_degrade_when_feature_is_disabled() -> None:
    service = _DisabledHelixService()

    assert asyncio.run(helix_routes.list_nodes(_current_user=object(), service=service)) == []
    assert asyncio.run(helix_routes.list_transport_profiles(_current_user=object(), service=service)) == []
