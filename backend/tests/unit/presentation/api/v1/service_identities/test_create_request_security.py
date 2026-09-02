from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.api.v1.service_identities.schemas import CreateServiceIdentityRequest

request_app = FastAPI()


@request_app.post("/service-identities")
async def _create_service_identity(payload: CreateServiceIdentityRequest) -> dict[str, bool]:
    return {"accepted": bool(payload.customer_account_id)}


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("provider_subject_ref", "df688eb2-0039-4db4-9eb9-ce9d6632a21b"),
        ("provider_numeric_subject_id", 42),
    ],
)
@pytest.mark.asyncio
async def test_external_create_request_rejects_provider_identity_mass_assignment(
    field_name: str,
    value: object,
) -> None:
    payload = {
        "customer_account_id": str(uuid4()),
        "auth_realm_id": str(uuid4()),
        "provider_name": "remnawave",
        field_name: value,
    }

    async with AsyncClient(transport=ASGITransport(app=request_app), base_url="http://test") as client:
        response = await client.post("/service-identities", json=payload)

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "extra_forbidden"
    assert error["loc"] == ["body", field_name]


def test_external_create_openapi_schema_excludes_provider_identity_fields() -> None:
    schema = CreateServiceIdentityRequest.model_json_schema()

    assert schema["additionalProperties"] is False
    assert "provider_subject_ref" not in schema["properties"]
    assert "provider_numeric_subject_id" not in schema["properties"]
