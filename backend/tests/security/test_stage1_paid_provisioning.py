"""S1-VPN-005 paid provisioning checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    STAGE1_PAID_ORDER_STATUS,
    STAGE1_PAID_SETTLEMENT_STATUS,
    STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY,
    Stage1PaidProvisioningError,
    Stage1PaidProvisioningRequest,
    Stage1PaidProvisioningResult,
    Stage1PaidProvisioningService,
    build_stage1_paid_provisioning_request,
)
from src.infrastructure.remnawave.stage1_paid_gateway import RemnawaveStage1PaidProvisioningGateway
from src.presentation.api.shared import STAGE1_DEFAULT_VPN_PROFILE_ID, STAGE1_XHTTP_VPN_PROFILE_ID


class RecordingPaidGateway:
    def __init__(self) -> None:
        self.requests: list[Stage1PaidProvisioningRequest] = []

    async def provision_paid_access(
        self,
        request: Stage1PaidProvisioningRequest,
    ) -> Stage1PaidProvisioningResult:
        self.requests.append(request)
        return Stage1PaidProvisioningResult(
            customer_account_id=request.customer_account_id,
            order_id=request.order_id,
            remnawave_uuid=request.existing_remnawave_uuid or str(uuid4()),
            profile_id=request.profile_id,
            status="active",
            expires_at=request.access_expires_at,
            subscription_url="https://subscription.example.local/sub/redacted-paid-user",
            created=request.existing_remnawave_uuid is None,
        )


class FakeRemnawaveUserGateway:
    def __init__(self) -> None:
        self.created_payloads: list[tuple[str, dict]] = []
        self.updated_payloads: list[tuple[UUID, dict]] = []

    async def create(self, username: str, **kwargs) -> SimpleNamespace:
        self.created_payloads.append((username, kwargs))
        return SimpleNamespace(
            uuid=uuid4(),
            status="ACTIVE",
            expires_at=kwargs["expire_at"],
            subscription_url="https://subscription.example.local/sub/redacted-created",
        )

    async def update(self, uuid: UUID, **kwargs) -> SimpleNamespace:
        self.updated_payloads.append((uuid, kwargs))
        return SimpleNamespace(
            uuid=uuid,
            status="ACTIVE",
            expires_at=kwargs["expire_at"],
            subscription_url="https://subscription.example.local/sub/redacted-updated",
        )


def test_stage1_paid_request_creates_access_from_requested_time() -> None:
    user_id = uuid4()
    order_id = uuid4()
    requested_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)

    request = build_stage1_paid_provisioning_request(
        customer_account_id=user_id,
        order_id=order_id,
        email="paid-user@example.test",
        username="paid-user",
        telegram_id=123456,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=requested_at - timedelta(minutes=3),
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=200 * 1024 * 1024 * 1024,
        device_limit=3,
    )

    assert request.profile_id == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert request.access_starts_at == requested_at
    assert request.access_expires_at == requested_at + timedelta(days=30)
    assert request.traffic_limit_bytes == 200 * 1024 * 1024 * 1024
    assert request.device_limit == 3
    assert request.traffic_limit_strategy == STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY
    assert request.remnawave_username == f"cvpn_paid_{user_id.hex}"


def test_stage1_paid_request_extends_from_existing_future_access() -> None:
    requested_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    current_expires_at = requested_at + timedelta(days=12)

    request = build_stage1_paid_provisioning_request(
        customer_account_id=uuid4(),
        order_id=uuid4(),
        email="paid-user@example.test",
        username=None,
        telegram_id=None,
        order_status=" committed ",
        settlement_status=" PAID ",
        plan_duration_days=90,
        paid_at=requested_at,
        current_access_expires_at=current_expires_at,
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=None,
        device_limit=5,
        existing_remnawave_uuid=str(uuid4()),
    )

    assert request.access_starts_at == current_expires_at
    assert request.access_expires_at == current_expires_at + timedelta(days=90)
    assert request.traffic_limit_bytes is None


@pytest.mark.parametrize("settlement_status", ["pending_payment", "processing", "refunded", "failed", ""])
def test_stage1_paid_rejects_non_final_settlement_statuses(settlement_status: str) -> None:
    with pytest.raises(Stage1PaidProvisioningError):
        build_stage1_paid_provisioning_request(
            customer_account_id=uuid4(),
            order_id=uuid4(),
            email="paid-user@example.test",
            username=None,
            telegram_id=None,
            order_status=STAGE1_PAID_ORDER_STATUS,
            settlement_status=settlement_status,
            plan_duration_days=30,
            paid_at=datetime.now(UTC),
            traffic_limit_bytes=100,
            device_limit=1,
        )


@pytest.mark.parametrize("order_status", ["draft", "cancelled", "failed", ""])
def test_stage1_paid_rejects_uncommitted_orders(order_status: str) -> None:
    with pytest.raises(Stage1PaidProvisioningError):
        build_stage1_paid_provisioning_request(
            customer_account_id=uuid4(),
            order_id=uuid4(),
            email="paid-user@example.test",
            username=None,
            telegram_id=None,
            order_status=order_status,
            settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
            plan_duration_days=30,
            paid_at=datetime.now(UTC),
            traffic_limit_bytes=100,
            device_limit=1,
        )


def test_stage1_paid_rejects_disabled_profile() -> None:
    with pytest.raises(Stage1PaidProvisioningError):
        build_stage1_paid_provisioning_request(
            customer_account_id=uuid4(),
            order_id=uuid4(),
            email="paid-user@example.test",
            username=None,
            telegram_id=None,
            order_status=STAGE1_PAID_ORDER_STATUS,
            settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
            plan_duration_days=30,
            paid_at=datetime.now(UTC),
            traffic_limit_bytes=100,
            device_limit=1,
            profile_id="wireguard",
        )


@pytest.mark.asyncio
async def test_stage1_paid_provisioning_service_creates_safe_result() -> None:
    gateway = RecordingPaidGateway()
    user_id = uuid4()
    order_id = uuid4()
    requested_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)

    result = await Stage1PaidProvisioningService(gateway).provision(
        customer_account_id=user_id,
        order_id=order_id,
        email="paid-user@example.test",
        username="paid-user",
        telegram_id=None,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=requested_at,
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=200 * 1024 * 1024 * 1024,
        device_limit=3,
        source_provider="nowpayments",
        source_payment_id="provider-payment-redacted",
    )

    assert len(gateway.requests) == 1
    assert gateway.requests[0].profile_id == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert gateway.requests[0].source_provider == "nowpayments"
    assert result.status == "active"
    assert result.created is True
    safe = result.to_safe_dict()
    serialized = str(safe).lower()
    assert safe["order_id"] == str(order_id)
    assert safe["profile_id"] == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert "subscription" not in serialized
    assert "config_link" not in serialized
    assert "secret" not in serialized
    assert "token" not in serialized
    assert "provider-payment-redacted" not in serialized


@pytest.mark.asyncio
async def test_stage1_paid_provisioning_service_updates_existing_access_with_xhttp_profile() -> None:
    gateway = RecordingPaidGateway()
    existing_remnawave_uuid = str(uuid4())
    requested_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    current_expires_at = requested_at + timedelta(days=5)

    result = await Stage1PaidProvisioningService(gateway).provision(
        customer_account_id=uuid4(),
        order_id=uuid4(),
        email="paid-user@example.test",
        username=None,
        telegram_id=777,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=requested_at,
        current_access_expires_at=current_expires_at,
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=None,
        device_limit=5,
        existing_remnawave_uuid=existing_remnawave_uuid,
        profile_id=STAGE1_XHTTP_VPN_PROFILE_ID,
    )

    assert result.created is False
    assert result.remnawave_uuid == existing_remnawave_uuid
    assert result.profile_id == STAGE1_XHTTP_VPN_PROFILE_ID
    assert result.expires_at == current_expires_at + timedelta(days=30)
    assert gateway.requests[0].traffic_limit_bytes is None


@pytest.mark.asyncio
async def test_remnawave_paid_gateway_uses_create_and_update_contracts() -> None:
    user_gateway = FakeRemnawaveUserGateway()
    gateway = RemnawaveStage1PaidProvisioningGateway(user_gateway)  # type: ignore[arg-type]
    requested_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    existing_remnawave_uuid = uuid4()
    create_request = build_stage1_paid_provisioning_request(
        customer_account_id=uuid4(),
        order_id=uuid4(),
        email="paid-user@example.test",
        username=None,
        telegram_id=None,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=requested_at,
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=200 * 1024 * 1024 * 1024,
        device_limit=3,
    )
    update_request = build_stage1_paid_provisioning_request(
        customer_account_id=uuid4(),
        order_id=uuid4(),
        email="paid-user@example.test",
        username=None,
        telegram_id=123,
        order_status=STAGE1_PAID_ORDER_STATUS,
        settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
        plan_duration_days=30,
        paid_at=requested_at,
        provisioning_requested_at=requested_at,
        traffic_limit_bytes=None,
        device_limit=5,
        existing_remnawave_uuid=str(existing_remnawave_uuid),
    )

    create_result = await gateway.provision_paid_access(create_request)
    update_result = await gateway.provision_paid_access(update_request)

    assert create_result.created is True
    assert update_result.created is False
    assert user_gateway.created_payloads[0][0] == create_request.remnawave_username
    assert user_gateway.created_payloads[0][1]["expire_at"] == create_request.access_expires_at
    assert user_gateway.created_payloads[0][1]["traffic_limit_bytes"] == create_request.traffic_limit_bytes
    assert user_gateway.updated_payloads[0][0] == existing_remnawave_uuid
    assert user_gateway.updated_payloads[0][1]["expire_at"] == update_request.access_expires_at
    assert user_gateway.updated_payloads[0][1]["traffic_limit_bytes"] is None
    assert user_gateway.updated_payloads[0][1]["hwid_device_limit"] == 5


@pytest.mark.asyncio
async def test_stage1_paid_provisioning_contract_serializes_through_asgi_route() -> None:
    app = FastAPI()
    gateway = RecordingPaidGateway()

    @app.post("/s1/vpn/paid-provisioning")
    async def paid_provisioning() -> dict[str, str | bool]:
        result = await Stage1PaidProvisioningService(gateway).provision(
            customer_account_id=uuid4(),
            order_id=uuid4(),
            email="paid-user@example.test",
            username=None,
            telegram_id=None,
            order_status=STAGE1_PAID_ORDER_STATUS,
            settlement_status=STAGE1_PAID_SETTLEMENT_STATUS,
            plan_duration_days=30,
            paid_at=datetime(2026, 5, 4, 9, 30, tzinfo=UTC),
            provisioning_requested_at=datetime(2026, 5, 4, 9, 31, tzinfo=UTC),
            traffic_limit_bytes=200 * 1024 * 1024 * 1024,
            device_limit=3,
        )
        return result.to_safe_dict()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        response = await client.post("/s1/vpn/paid-provisioning")

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert body["status"] == "active"
    assert body["created"] is True
    serialized = str(body).lower()
    assert "subscription" not in serialized
    assert "secret" not in serialized
    assert "token" not in serialized
