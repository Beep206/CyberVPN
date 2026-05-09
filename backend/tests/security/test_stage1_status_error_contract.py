"""S1-BE-008 canonical status/error contract checks."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse

from src.domain.enums.enums import (
    AccessDeliveryChannelStatus,
    DeviceCredentialStatus,
    EntitlementGrantStatus,
    PaymentAttemptStatus,
    PaymentStatus,
    ProvisioningProfileStatus,
    ServiceIdentityStatus,
    UserStatus,
)
from src.presentation.api.shared.stage1_contract import (
    ACCESS_DELIVERY_STATUS_TO_STAGE1_PROVISIONING_STATE,
    DEVICE_CREDENTIAL_STATUS_TO_STAGE1_PROVISIONING_STATE,
    ENTITLEMENT_GRANT_STATUS_TO_STAGE1_ACCESS_STATE,
    PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE,
    PAYMENT_STATUS_TO_STAGE1_STATE,
    PROVISIONING_PROFILE_STATUS_TO_STAGE1_PROVISIONING_STATE,
    SERVICE_IDENTITY_STATUS_TO_STAGE1_PROVISIONING_STATE,
    STAGE1_ERROR_MATRIX,
    USER_STATUS_TO_STAGE1_ACCESS_STATE,
    Stage1AccessState,
    Stage1ErrorCode,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
    Stage1Surface,
    build_stage1_error_response,
)


def test_stage1_error_matrix_covers_every_error_code() -> None:
    assert set(STAGE1_ERROR_MATRIX) == set(Stage1ErrorCode)


def test_stage1_error_matrix_covers_launch_critical_surfaces() -> None:
    surfaces = {spec.surface for spec in STAGE1_ERROR_MATRIX.values()}

    assert surfaces == {
        Stage1Surface.AUTH,
        Stage1Surface.PAYMENT,
        Stage1Surface.PROVISIONING,
        Stage1Surface.SUPPORT,
        Stage1Surface.SYSTEM,
        Stage1Surface.VALIDATION,
    }


@pytest.mark.parametrize(
    "error_code",
    [
        Stage1ErrorCode.PAYMENT_ORPHAN_REVIEW_REQUIRED,
        Stage1ErrorCode.PROVISIONING_FAILED,
        Stage1ErrorCode.PROVISIONING_RECONCILIATION_REQUIRED,
        Stage1ErrorCode.REMNAWAVE_UNAVAILABLE,
        Stage1ErrorCode.SUPPORT_ESCALATION_REQUIRED,
    ],
)
def test_stage1_manual_review_errors_escalate_to_support(error_code: Stage1ErrorCode) -> None:
    response = build_stage1_error_response(error_code, request_id="req-s1-test")

    assert response.support_escalation is True
    assert response.request_id == "req-s1-test"
    assert response.surface in {
        Stage1Surface.PAYMENT,
        Stage1Surface.PROVISIONING,
        Stage1Surface.SUPPORT,
    }


@pytest.mark.parametrize(
    "error_code",
    [
        Stage1ErrorCode.AUTH_RATE_LIMITED,
        Stage1ErrorCode.RATE_LIMITED,
        Stage1ErrorCode.PAYMENT_PENDING,
        Stage1ErrorCode.PAYMENT_PROVIDER_UNAVAILABLE,
        Stage1ErrorCode.PROVISIONING_PENDING,
        Stage1ErrorCode.PROVISIONING_RETRYING,
        Stage1ErrorCode.PROVISIONING_FAILED,
        Stage1ErrorCode.REMNAWAVE_UNAVAILABLE,
    ],
)
def test_stage1_retryable_errors_are_explicit(error_code: Stage1ErrorCode) -> None:
    assert STAGE1_ERROR_MATRIX[error_code].retryable is True


def test_stage1_internal_error_message_is_redacted() -> None:
    response = build_stage1_error_response(
        Stage1ErrorCode.INTERNAL_ERROR,
        request_id="req-internal",
        details={"safe_reference": "incident-1"},
    )
    serialized = response.model_dump(mode="json")
    combined_text = " ".join(str(value).lower() for value in serialized.values())

    assert serialized == {
        "code": "internal_error",
        "message": "Unexpected service error.",
        "surface": "system",
        "http_status": 500,
        "user_action": "Try again later or contact support with the request id.",
        "retryable": True,
        "support_escalation": False,
        "request_id": "req-internal",
        "details": {"safe_reference": "incident-1"},
    }
    assert "traceback" not in combined_text
    assert "password" not in combined_text
    assert "secret" not in combined_text
    assert "token" not in combined_text


def test_stage1_domain_status_mapping_is_exhaustive() -> None:
    assert set(USER_STATUS_TO_STAGE1_ACCESS_STATE) == set(UserStatus)
    assert set(PAYMENT_STATUS_TO_STAGE1_STATE) == set(PaymentStatus)
    assert set(PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE) == set(PaymentAttemptStatus)
    assert set(SERVICE_IDENTITY_STATUS_TO_STAGE1_PROVISIONING_STATE) == set(ServiceIdentityStatus)
    assert set(PROVISIONING_PROFILE_STATUS_TO_STAGE1_PROVISIONING_STATE) == set(ProvisioningProfileStatus)
    assert set(ENTITLEMENT_GRANT_STATUS_TO_STAGE1_ACCESS_STATE) == set(EntitlementGrantStatus)
    assert set(DEVICE_CREDENTIAL_STATUS_TO_STAGE1_PROVISIONING_STATE) == set(DeviceCredentialStatus)
    assert set(ACCESS_DELIVERY_STATUS_TO_STAGE1_PROVISIONING_STATE) == set(AccessDeliveryChannelStatus)


def test_stage1_payment_statuses_map_to_customer_safe_states() -> None:
    assert PAYMENT_STATUS_TO_STAGE1_STATE == {
        PaymentStatus.PENDING: Stage1PaymentState.PENDING,
        PaymentStatus.COMPLETED: Stage1PaymentState.PAID,
        PaymentStatus.FAILED: Stage1PaymentState.FAILED,
        PaymentStatus.REFUNDED: Stage1PaymentState.REFUNDED,
    }
    assert PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE[PaymentAttemptStatus.SUCCEEDED] == Stage1PaymentState.PAID
    assert PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE[PaymentAttemptStatus.CANCELLED] == Stage1PaymentState.CANCELLED


def test_stage1_access_and_provisioning_statuses_map_to_customer_safe_states() -> None:
    assert USER_STATUS_TO_STAGE1_ACCESS_STATE[UserStatus.DISABLED] == Stage1AccessState.SUSPENDED
    assert (
        ENTITLEMENT_GRANT_STATUS_TO_STAGE1_ACCESS_STATE[EntitlementGrantStatus.REVOKED] == Stage1AccessState.NO_ACCESS
    )
    assert (
        DEVICE_CREDENTIAL_STATUS_TO_STAGE1_PROVISIONING_STATE[DeviceCredentialStatus.ACTIVE]
        == Stage1ProvisioningState.READY
    )
    assert (
        SERVICE_IDENTITY_STATUS_TO_STAGE1_PROVISIONING_STATE[ServiceIdentityStatus.SUSPENDED]
        == Stage1ProvisioningState.SUSPENDED
    )


@pytest.mark.asyncio
async def test_stage1_error_contract_serializes_through_asgi_response() -> None:
    app = FastAPI()

    @app.get("/s1/error")
    async def stage1_error() -> JSONResponse:
        payload = build_stage1_error_response(
            Stage1ErrorCode.PAYMENT_ORPHAN_REVIEW_REQUIRED,
            request_id="req-orphan-test",
            details={"payment_id": "pay_test", "age_hours": 1},
        )
        return JSONResponse(
            status_code=payload.http_status,
            content=payload.model_dump(mode="json"),
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        response = await client.get("/s1/error")

    assert response.status_code == 409
    assert response.json() == {
        "code": "payment_orphan_review_required",
        "message": "Payment was received, but access is not ready yet.",
        "surface": "payment",
        "http_status": 409,
        "user_action": "Support must review and restore access within the S1 orphan-payment SLA.",
        "retryable": True,
        "support_escalation": True,
        "request_id": "req-orphan-test",
        "details": {"payment_id": "pay_test", "age_hours": 1},
    }


def test_stage1_support_state_has_manual_review_and_ops_escalation_values() -> None:
    assert Stage1SupportState.SUPPORT_REVIEW.value == "support_review"
    assert Stage1SupportState.OPS_ESCALATION.value == "ops_escalation"
