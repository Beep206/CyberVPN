from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import httpx
import pytest
from fastapi import FastAPI, HTTPException, status
from pydantic import ValidationError

from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.api.v1.billing import routes as billing_routes
from src.presentation.api.v1.billing.schemas import CreatePaymentRequest
from src.presentation.api.v1.keygen import routes as keygen_routes
from src.presentation.api.v1.keygen.schemas import SignPayloadRequest
from src.presentation.api.v1.node_plugins import routes as node_plugin_routes
from src.presentation.api.v1.node_plugins.schemas import (
    TorrentBlockerReportsResponse,
    TorrentBlockerReportsStatsResponse,
)
from src.presentation.api.v1.remnawave_status.routes import _build_admin_capabilities
from src.presentation.api.v1.settings import routes as settings_routes
from src.presentation.api.v1.settings.schemas import (
    CreateSettingRequest,
    RemnawaveSettingsResponse,
    UpdateRemnawaveSettingsRequest,
    UpdateSettingRequest,
)
from src.presentation.dependencies import get_remnawave_client
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.auth_realms import get_request_admin_realm

_SETTINGS_RESPONSE_FIXTURE = {
    "passkeySettings": {
        "enabled": True,
        "rpId": "panel.cybervpn.test",
        "origin": "https://panel.cybervpn.test",
    },
    "oauth2Settings": {
        "github": {
            "enabled": False,
            "clientId": None,
            "clientSecret": None,
            "allowedEmails": [],
        },
        "pocketid": {
            "enabled": False,
            "clientId": None,
            "clientSecret": None,
            "frontendDomain": None,
            "plainDomain": None,
            "allowedEmails": [],
        },
        "yandex": {
            "enabled": True,
            "clientId": "client-id",
            "clientSecret": "client-secret",
            "allowedEmails": ["admin@cybervpn.test"],
        },
    },
    "passwordSettings": {"enabled": True},
    "brandingSettings": {
        "title": "CyberVPN",
        "logoUrl": "https://panel.cybervpn.test/logo.svg",
    },
}

_TORRENT_REPORTS_FIXTURE = {
    "records": [
        {
            "id": 1,
            "userId": 42,
            "nodeId": 7,
            "user": {"username": "alice"},
            "node": {
                "uuid": "31a820ad-a760-4b57-9a37-20b0ab4f2510",
                "name": "staging-node",
                "countryCode": "DE",
            },
            "report": {
                "actionReport": {
                    "blocked": True,
                    "ip": "192.0.2.10",
                    "blockDuration": 120.5,
                    "willUnblockAt": "2026-08-31T12:02:00Z",
                    "userId": "42",
                    "processedAt": "2026-08-31T12:00:00Z",
                },
                "xrayReport": {
                    "email": None,
                    "level": None,
                    "protocol": "vless",
                    "network": "tcp",
                    "source": None,
                    "destination": "198.51.100.5:443",
                    "routeTarget": None,
                    "originalTarget": None,
                    "inboundTag": "RAW-443",
                    "inboundName": None,
                    "inboundLocal": None,
                    "outboundTag": "BLOCK",
                    "ts": 1.5,
                },
            },
            "createdAt": "2026-08-31T12:00:00Z",
        }
    ],
    "total": 1,
}

_TORRENT_STATS_FIXTURE = {
    "stats": {
        "distinctNodes": 1,
        "distinctUsers": 1,
        "totalReports": 3,
        "reportsLast24Hours": 2,
    },
    "topUsers": [
        {
            "userId": 42,
            "color": "#ffffff",
            "username": "alice",
            "total": 3,
        }
    ],
    "topNodes": [
        {
            "uuid": "31a820ad-a760-4b57-9a37-20b0ab4f2510",
            "countryCode": "DE",
            "color": "#000000",
            "name": "staging-node",
            "total": 3,
        }
    ],
}


@pytest.mark.unit
def test_client_normalizes_exact_342_operator_paths() -> None:
    assert RemnawaveClient._normalize_path("/remnawave-settings") == "/api/remnawave-settings"
    assert (
        RemnawaveClient._normalize_path("/node-plugins/torrent-blocker/stats")
        == "/api/node-plugins/torrent-blocker/stats"
    )


@pytest.mark.unit
async def test_settings_use_exact_342_get_and_patch_contracts() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    target_response = RemnawaveSettingsResponse.model_validate(_SETTINGS_RESPONSE_FIXTURE)
    client.get_validated.return_value = target_response
    client.patch_validated.return_value = target_response

    fetched = await settings_routes.get_settings(current_user=object(), client=client)
    updated = await settings_routes.update_settings(
        setting_data=UpdateRemnawaveSettingsRequest.model_validate(
            {
                "brandingSettings": {
                    "title": "CyberVPN 3.4",
                    "logoUrl": "https://panel.cybervpn.test/logo-3.4.svg",
                }
            }
        ),
        current_user=object(),
        client=client,
    )

    assert fetched is target_response
    assert updated is target_response
    client.get_validated.assert_awaited_once_with(
        "/remnawave-settings",
        RemnawaveSettingsResponse,
    )
    client.patch_validated.assert_awaited_once_with(
        "/remnawave-settings",
        RemnawaveSettingsResponse,
        json={
            "brandingSettings": {
                "title": "CyberVPN 3.4",
                "logoUrl": "https://panel.cybervpn.test/logo-3.4.svg",
            }
        },
    )


@pytest.mark.unit
async def test_settings_patch_failure_is_not_reported_as_success() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.side_effect = httpx.ConnectError("Remnawave unavailable")

    with pytest.raises(httpx.ConnectError):
        await settings_routes.update_settings(
            setting_data=UpdateRemnawaveSettingsRequest.model_validate({"passwordSettings": {"enabled": True}}),
            current_user=object(),
            client=client,
        )


@pytest.mark.unit
def test_settings_patch_rejects_null_sections_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        UpdateRemnawaveSettingsRequest.model_validate({"brandingSettings": None})
    with pytest.raises(ValidationError):
        UpdateRemnawaveSettingsRequest.model_validate({"unknownSetting": True})


@pytest.mark.unit
async def test_legacy_settings_mutations_fail_before_provider_io() -> None:
    client = AsyncMock(spec=RemnawaveClient)

    with pytest.raises(HTTPException) as create_error:
        await settings_routes.create_setting(
            setting_data=CreateSettingRequest(key="legacy", value=True),
            current_user=object(),
            client=client,
        )
    with pytest.raises(HTTPException) as update_error:
        await settings_routes.update_setting(
            id=7,
            setting_data=UpdateSettingRequest(value=False),
            current_user=object(),
            client=client,
        )

    for error in (create_error.value, update_error.value):
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.detail == {"code": "remnawave_settings_legacy_operation_not_supported"}
    client.post_validated.assert_not_awaited()
    client.put_validated.assert_not_awaited()
    client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_settings_routes_are_admin_only_before_provider_io(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(settings_routes.router)
    remnawave_client = AsyncMock(spec=RemnawaveClient)

    async def viewer_user():
        return SimpleNamespace(role=AdminRole.VIEWER.value, totp_enabled=True)

    async def non_admin_realm():
        return object()

    async def remnawave_dependency():
        return remnawave_client

    monkeypatch.setattr(settings, "admin_2fa_required", False)
    app.dependency_overrides[get_current_active_user] = viewer_user
    app.dependency_overrides[get_request_admin_realm] = non_admin_realm
    app.dependency_overrides[get_remnawave_client] = remnawave_dependency

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        responses = [
            await http_client.get("/settings/"),
            await http_client.patch("/settings/", json={}),
            await http_client.post("/settings/", json={"key": "legacy", "value": True}),
            await http_client.put("/settings/7", json={}),
        ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    remnawave_client.get_validated.assert_not_awaited()
    remnawave_client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_torrent_routes_use_exact_target_paths_and_shapes() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    reports = TorrentBlockerReportsResponse.model_validate(_TORRENT_REPORTS_FIXTURE)
    stats_response = TorrentBlockerReportsStatsResponse.model_validate(_TORRENT_STATS_FIXTURE)
    client.get_validated.side_effect = [reports, stats_response]

    fetched_reports = await node_plugin_routes.get_torrent_blocker_reports(
        query=node_plugin_routes.TorrentBlockerReportsQuery(start=0, size=25),
        _current_user=object(),
        client=client,
    )
    fetched_stats = await node_plugin_routes.get_torrent_blocker_stats(
        _current_user=object(),
        client=client,
    )

    assert fetched_reports.records[0].user.username == "alice"
    assert fetched_stats.top_users[0].user_id == 42
    assert fetched_stats.top_nodes[0].uuid == "31a820ad-a760-4b57-9a37-20b0ab4f2510"
    assert client.get_validated.await_args_list == [
        call(
            "/node-plugins/torrent-blocker",
            TorrentBlockerReportsResponse,
            params={"start": 0, "size": 25},
        ),
        call(
            "/node-plugins/torrent-blocker/stats",
            TorrentBlockerReportsStatsResponse,
        ),
    ]


@pytest.mark.unit
async def test_torrent_stats_failure_is_not_masked_as_zero() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.get_validated.side_effect = httpx.ConnectError("Remnawave unavailable")

    with pytest.raises(httpx.ConnectError):
        await node_plugin_routes.get_torrent_blocker_stats(
            _current_user=object(),
            client=client,
        )


@pytest.mark.unit
async def test_absent_billing_and_keygen_operations_never_call_provider() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    operations = (
        billing_routes.get_billing_info(current_user=object(), client=client),
        billing_routes.create_payment(
            payment_data=CreatePaymentRequest(
                user_uuid="4dac1a06-62fd-462d-82ef-60d75f4fbc52",
                amount=9.99,
                currency="USD",
            ),
            current_user=object(),
            client=client,
        ),
        keygen_routes.get_public_key(current_user=object(), client=client),
        keygen_routes.sign_payload(
            payload_data=SignPayloadRequest(payload="payload"),
            current_user=object(),
            client=client,
        ),
    )

    for operation in operations:
        with pytest.raises(HTTPException) as error:
            await operation
        assert error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.value.detail["code"].endswith("not_supported")

    client.get_list_validated.assert_not_awaited()
    client.get_validated.assert_not_awaited()
    client.post_validated.assert_not_awaited()


@pytest.mark.unit
def test_admin_capabilities_report_only_reachable_implemented_surfaces(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    target = _build_admin_capabilities(
        panel_version="3.4.3",
        node_ssh_available=True,
        numeric_cutover_ready=True,
        stream_export_observed=True,
    )
    mismatch = _build_admin_capabilities(panel_version="3.4.1", node_ssh_available=True)

    assert target.numeric_user_ids is True
    assert target.node_ssh is True
    assert target.redis_stream_export is True
    assert target.connections is True
    assert target.geo_check is True
    assert target.node_integrations is True
    assert target.shared_lists is True
    assert target.tags is True
    assert target.host_mapper is True
    assert target.root_snippets is True
    assert not any(mismatch.model_dump().values())
