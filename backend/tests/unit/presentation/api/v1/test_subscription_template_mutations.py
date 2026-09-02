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
from src.infrastructure.remnawave.control_plane_contracts import RemnawaveSubscriptionTemplateV34Response
from src.presentation.api.v1.subscriptions import routes
from src.presentation.api.v1.subscriptions.schemas import (
    CreateSubscriptionTemplateRequest,
    SubscriptionTemplateResponse,
    UpdateSubscriptionTemplateRequest,
)

TEMPLATE_UUID = UUID("11111111-1111-4111-8111-111111111111")


def _target_template(**overrides: object) -> RemnawaveSubscriptionTemplateV34Response:
    payload: dict[str, object] = {
        "uuid": str(TEMPLATE_UUID),
        "viewPosition": 1,
        "name": "Safe template",
        "tags": ["PROD"],
        "templateType": "XRAY_JSON",
        "templateJson": {"outbounds": []},
        "encodedTemplateYaml": None,
    }
    payload.update(overrides)
    return RemnawaveSubscriptionTemplateV34Response.model_validate(payload)


@pytest.mark.unit
async def test_create_template_is_503_before_provider_io() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    payload = CreateSubscriptionTemplateRequest(name="Safe template", template_type="XRAY_JSON")

    with pytest.raises(HTTPException) as exc_info:
        await routes.create_subscription_template(payload, None, client)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail == {"code": "remnawave_subscription_template_create_safety_disabled"}
    client.post_validated.assert_not_awaited()
    client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_update_template_uses_exact_target_method_path_body_and_direct_postcondition() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.return_value = _target_template(
        name="Updated template",
        templateJson={"outbounds": [{"tag": "DIRECT"}]},
    )
    payload = UpdateSubscriptionTemplateRequest(
        name="Updated template",
        template_json={"outbounds": [{"tag": "DIRECT"}]},
    )

    result = await routes.update_subscription_template(TEMPLATE_UUID, payload, None, client)

    assert isinstance(result, SubscriptionTemplateResponse)
    client.patch_validated.assert_awaited_once_with(
        "/subscription-templates",
        RemnawaveSubscriptionTemplateV34Response,
        json={
            "uuid": str(TEMPLATE_UUID),
            "name": "Updated template",
            "templateJson": {"outbounds": [{"tag": "DIRECT"}]},
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
async def test_update_template_reconciles_empty_or_transport_ambiguity_once_without_replay(
    ambiguous_result: object,
) -> None:
    client = AsyncMock(spec=RemnawaveClient)
    if isinstance(ambiguous_result, Exception):
        client.patch_validated.side_effect = ambiguous_result
    else:
        client.patch_validated.return_value = ambiguous_result
    client.get_validated.return_value = _target_template(name="Updated template")

    result = await routes.update_subscription_template(
        TEMPLATE_UUID,
        UpdateSubscriptionTemplateRequest(name="Updated template"),
        None,
        client,
    )

    assert isinstance(result, SubscriptionTemplateResponse)
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once_with(
        f"/subscription-templates/{TEMPLATE_UUID}",
        RemnawaveSubscriptionTemplateV34Response,
    )


@pytest.mark.unit
async def test_update_template_keeps_provider_4xx_terminal_without_readback() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.side_effect = RemnawaveHTTPStatusError(status_code=400)

    with pytest.raises(RemnawaveHTTPStatusError) as exc_info:
        await routes.update_subscription_template(
            TEMPLATE_UUID,
            UpdateSubscriptionTemplateRequest(name="Updated template"),
            None,
            client,
        )

    assert exc_info.value.response.status_code == 400
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_not_awaited()


@pytest.mark.unit
async def test_update_template_returns_pending_when_readback_is_stale() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.return_value = None
    client.get_validated.return_value = _target_template(name="Old template")

    result = await routes.update_subscription_template(
        TEMPLATE_UUID,
        UpdateSubscriptionTemplateRequest(name="Updated template"),
        None,
        client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_202_ACCEPTED
    assert result.headers["retry-after"] == "30"
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once()


@pytest.mark.unit
async def test_update_template_rejects_stale_direct_response_without_replay_or_readback() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.patch_validated.return_value = _target_template(name="Old template")

    result = await routes.update_subscription_template(
        TEMPLATE_UUID,
        UpdateSubscriptionTemplateRequest(name="Updated template"),
        None,
        client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_202_ACCEPTED
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_not_awaited()


def test_template_response_requires_target_341_shape() -> None:
    parsed = SubscriptionTemplateResponse.model_validate(_target_template().model_dump(by_alias=True, mode="json"))
    assert parsed.template_type == "XRAY_JSON"
    assert parsed.view_position == 1

    with pytest.raises(ValidationError):
        SubscriptionTemplateResponse.model_validate(
            {
                "uuid": str(TEMPLATE_UUID),
                "name": "legacy",
                "templateType": "vless",
            }
        )


@pytest.mark.unit
async def test_delete_template_matches_target_no_content_contract() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.delete_validated.return_value = None

    response = await routes.delete_subscription_template(TEMPLATE_UUID, None, client)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.body == b""
    client.delete_validated.assert_awaited_once_with(f"/subscription-templates/{TEMPLATE_UUID}")


def test_template_mutation_routes_document_target_statuses() -> None:
    routes_by_name = {route.name: route for route in routes.router.routes}

    assert status.HTTP_503_SERVICE_UNAVAILABLE in routes_by_name["create_subscription_template"].responses
    assert status.HTTP_202_ACCEPTED in routes_by_name["update_subscription_template"].responses
    assert routes_by_name["delete_subscription_template"].status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.unit
async def test_template_detail_route_rejects_customer_realm() -> None:
    import uuid

    from src.application.use_cases.auth_realms import RealmResolution
    from src.domain.enums import AdminRole
    from src.infrastructure.database.models.admin_user_model import AdminUserModel
    from src.infrastructure.database.models.auth_realm_model import AuthRealmModel

    route = next(route for route in routes.router.routes if route.name == "get_subscription_template")
    dependency = next(item for item in route.dependant.dependencies if item.name == "current_user")
    customer_realm = RealmResolution(
        auth_realm=AuthRealmModel(
            id=uuid.uuid4(),
            realm_key="customer",
            realm_type="customer",
            display_name="Customer realm",
            audience="cybervpn:customer",
            cookie_namespace="customer",
            is_default=True,
        ),
        source="test",
    )
    admin = AdminUserModel(login="template-admin", email="admin@example.test", role=AdminRole.ADMIN.value)

    with pytest.raises(HTTPException) as exc_info:
        await dependency.call(user=admin, current_realm=customer_realm)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Admin realm required"
