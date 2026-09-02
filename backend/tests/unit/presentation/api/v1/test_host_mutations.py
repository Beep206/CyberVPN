from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import HTTPException, Response, status
from pydantic import ValidationError

from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveProtocolError,
    RemnawaveTransportError,
)
from src.infrastructure.remnawave.control_plane_contracts import RemnawaveHostV34Response
from src.presentation.api.v1.hosts import routes
from src.presentation.api.v1.hosts.schemas import (
    CreateHostRequest,
    HostInboundRequest,
    HostInternalSquadsRequest,
    HostResponse,
    UpdateHostRequest,
)

HOST_UUID = UUID("11111111-1111-4111-8111-111111111111")
PROFILE_UUID = UUID("22222222-2222-4222-8222-222222222222")
INBOUND_UUID = UUID("33333333-3333-4333-8333-333333333333")


def _target_host(**overrides: object) -> RemnawaveHostV34Response:
    payload: dict[str, object] = {
        "uuid": str(HOST_UUID),
        "viewPosition": 1,
        "remark": "Target host",
        "address": "edge.example.com",
        "port": 443,
        "path": "/xhttp",
        "sni": "one.example,two.example",
        "host": None,
        "alpn": "h2,http/1.1",
        "fingerprint": "chrome",
        "isDisabled": False,
        "securityLayer": "TLS",
        "xhttpExtraParams": None,
        "muxParams": None,
        "sockoptParams": None,
        "finalMask": None,
        "inbound": {
            "configProfileUuid": str(PROFILE_UUID),
            "configProfileInboundUuid": str(INBOUND_UUID),
        },
        "serverDescription": None,
        "tags": ["EDGE:PROD"],
        "isHidden": False,
        "overrideSniFromAddress": False,
        "keepSniBlank": False,
        "vlessRouteId": None,
        "pinnedPeerCertSha256": None,
        "verifyPeerCertByName": None,
        "shuffleHost": False,
        "mihomoX25519": False,
        "mihomoIpVersion": None,
        "nodes": [],
        "xrayJsonTemplateUuid": None,
        "excludeFromSubscriptionTypes": [],
        "mapper": {},
        "internalSquads": {"mode": "EXCLUDE", "squads": []},
    }
    payload.update(overrides)
    return RemnawaveHostV34Response.model_validate(payload)


@pytest.mark.unit
async def test_host_create_is_503_before_provider_io() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    request = CreateHostRequest(
        inbound=HostInboundRequest(
            config_profile_uuid=PROFILE_UUID,
            config_profile_inbound_uuid=INBOUND_UUID,
        ),
        remark="Target host",
        address="edge.example.com",
        port=443,
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.create_host(request, object(), client)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail == {"code": "remnawave_host_create_safety_disabled"}
    client.post_validated.assert_not_awaited()
    client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_host_update_uses_exact_target_method_path_body_and_direct_postcondition() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.return_value = _target_host(remark="Updated host")
    request = UpdateHostRequest(
        remark="Updated host",
        sni=["one.example", "two.example"],
        internal_squads=HostInternalSquadsRequest(mode="EXCLUDE", squads=[]),
    )

    result = await routes.update_host(HOST_UUID, request, object(), client)

    assert isinstance(result, HostResponse)
    client.patch_validated.assert_awaited_once_with(
        "/hosts",
        RemnawaveHostV34Response,
        json={
            "uuid": str(HOST_UUID),
            "remark": "Updated host",
            "sni": ["one.example", "two.example"],
            "internalSquads": {"mode": "EXCLUDE", "squads": []},
        },
    )
    client.get_validated.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "ambiguous_result",
    [
        None,
        RemnawaveTransportError(),
        RemnawaveHTTPStatusError(status_code=500),
        RemnawaveProtocolError(),
        HTTPException(status_code=502, detail="invalid provider response"),
    ],
)
async def test_host_update_reconciles_empty_or_transport_ambiguity_once_without_replay(
    ambiguous_result: object,
) -> None:
    client = AsyncMock(spec=RemnawaveClient)
    if isinstance(ambiguous_result, Exception):
        client.patch_validated.side_effect = ambiguous_result
    else:
        client.patch_validated.return_value = ambiguous_result
    client.get_validated.return_value = _target_host(remark="Updated host")

    result = await routes.update_host(
        HOST_UUID,
        UpdateHostRequest(remark="Updated host"),
        object(),
        client,
    )

    assert isinstance(result, HostResponse)
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once_with(
        f"/hosts/{HOST_UUID}",
        RemnawaveHostV34Response,
    )


@pytest.mark.unit
async def test_host_update_keeps_provider_4xx_terminal_without_readback() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.side_effect = RemnawaveHTTPStatusError(status_code=400)

    with pytest.raises(RemnawaveHTTPStatusError) as exc_info:
        await routes.update_host(
            HOST_UUID,
            UpdateHostRequest(remark="Updated host"),
            object(),
            client,
        )

    assert exc_info.value.response.status_code == 400
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_not_awaited()


@pytest.mark.unit
async def test_host_update_returns_pending_when_readback_is_stale() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.return_value = None
    client.get_validated.return_value = _target_host(remark="Old host")

    result = await routes.update_host(
        HOST_UUID,
        UpdateHostRequest(remark="Updated host"),
        object(),
        client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_202_ACCEPTED
    assert result.headers["retry-after"] == "30"
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once()


@pytest.mark.unit
async def test_host_update_rejects_stale_direct_response_without_replay_or_readback() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.return_value = _target_host(remark="Old host")

    result = await routes.update_host(
        HOST_UUID,
        UpdateHostRequest(remark="Updated host"),
        object(),
        client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_202_ACCEPTED
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_not_awaited()


def test_host_response_requires_target_341_shape() -> None:
    parsed = HostResponse.model_validate(_target_host().model_dump(by_alias=True, mode="json"))
    assert parsed.inbound.config_profile_uuid == PROFILE_UUID
    assert parsed.internal_squads.mode == "EXCLUDE"

    with pytest.raises(ValidationError):
        HostResponse.model_validate(
            {
                "uuid": str(HOST_UUID),
                "name": "legacy host",
                "address": "edge.example.com",
                "port": 443,
                "isDisabled": False,
            }
        )


@pytest.mark.unit
async def test_host_delete_matches_target_no_content_contract() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.delete_validated.return_value = None

    response = await routes.delete_host(HOST_UUID, object(), client)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.body == b""
    client.delete_validated.assert_awaited_once_with(f"/hosts/{HOST_UUID}")
