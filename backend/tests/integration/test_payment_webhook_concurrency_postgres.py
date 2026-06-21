from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.use_cases.invites.generate_invites import GenerateInvitesForPaymentUseCase
from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_postgres_paid_webhook_serializes_duplicate_invoice_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    database_name = f"cvpn_webhook_race_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        token = "test-webhook-token"
        external_id = str(900_000_000_000 + int(uuid.uuid4().hex[:8], 16) % 100_000_000)
        payment_id = uuid.uuid4()
        user_id = uuid.uuid4()
        plan_id = uuid.uuid4()

        async with maker() as session:
            session.add(
                MobileUserModel(
                    id=user_id,
                    public_uid=20_000_000 + int(uuid.uuid4().hex[:6], 16) % 50_000_000,
                    email=f"webhook-race-{uuid.uuid4().hex[:8]}@example.test",
                    password_hash="hash",
                    notification_prefs={},
                    totp_enabled=False,
                    is_active=True,
                    status="active",
                )
            )
            session.add(
                SubscriptionPlanModel(
                    id=plan_id,
                    name=f"webhook-race-plan-{uuid.uuid4().hex[:8]}",
                    tier="pro",
                    plan_code=f"race-{uuid.uuid4().hex[:6]}",
                    display_name="Webhook Race Plan",
                    catalog_visibility="hidden",
                    duration_days=30,
                    traffic_limit_bytes=None,
                    device_limit=1,
                    price_usd=Decimal("9.99"),
                    price_rub=None,
                    sale_channels=["web"],
                    traffic_policy={},
                    connection_modes=[],
                    server_pool=[],
                    support_sla="standard",
                    dedicated_ip={},
                    invite_bundle={"count": 2, "friend_days": 7, "expiry_days": 30},
                    trial_eligible=False,
                    features={},
                    is_active=True,
                    sort_order=0,
                )
            )
            session.add(
                PaymentModel(
                    id=payment_id,
                    external_id=external_id,
                    user_uuid=user_id,
                    amount=Decimal("9.99"),
                    currency="USD",
                    status="pending",
                    provider="cryptobot",
                    subscription_days=30,
                    plan_id=plan_id,
                    final_amount=Decimal("9.99"),
                    addons_snapshot=[],
                    entitlements_snapshot={},
                    metadata_={},
                )
            )
            await session.commit()

        first_invites_started = asyncio.Event()
        release_first_invites = asyncio.Event()
        invite_execute_calls = 0
        original_invite_execute = GenerateInvitesForPaymentUseCase.execute

        async def delayed_invite_execute(
            self: GenerateInvitesForPaymentUseCase,
            owner_user_id: uuid.UUID,
            plan_id: uuid.UUID,
            payment_id: uuid.UUID,
        ) -> list[InviteCodeModel]:
            nonlocal invite_execute_calls
            invite_execute_calls += 1
            first_invites_started.set()
            created = await original_invite_execute(self, owner_user_id, plan_id, payment_id)
            await asyncio.wait_for(release_first_invites.wait(), timeout=5)
            return created

        monkeypatch.setattr(GenerateInvitesForPaymentUseCase, "execute", delayed_invite_execute)
        body, signature = _signed_cryptobot_invoice_paid_body(token, external_id)

        async def process_once() -> dict[str, Any]:
            async with maker() as session:
                use_case = ProcessPaymentWebhookUseCase(
                    session=session,
                    webhook_handler=CryptoBotWebhookHandler(token),
                )
                return await use_case.execute(provider="cryptobot", body=body, signature=signature)

        first = asyncio.create_task(process_once())
        await asyncio.wait_for(first_invites_started.wait(), timeout=5)
        second = asyncio.create_task(process_once())
        await asyncio.sleep(0.2)
        assert not second.done()

        release_first_invites.set()
        first_result, second_result = await asyncio.wait_for(asyncio.gather(first, second), timeout=10)

        assert {first_result["status"], second_result["status"]} == {"processed", "already_processed"}
        assert invite_execute_calls == 1

        async with maker() as session:
            payment_status = await session.scalar(select(PaymentModel.status).where(PaymentModel.id == payment_id))
            invite_count = await session.scalar(
                select(func.count()).select_from(InviteCodeModel).where(InviteCodeModel.source_payment_id == payment_id)
            )
            payment_completed_event_count = await session.scalar(
                select(func.count())
                .select_from(OutboxEventModel)
                .where(OutboxEventModel.event_key == f"payment.completed:{payment_id}")
            )

        assert payment_status == "completed"
        assert invite_count == 2
        assert payment_completed_event_count == 1
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


def _signed_cryptobot_invoice_paid_body(token: str, invoice_id: str) -> tuple[bytes, str]:
    payload = {
        "update_type": "invoice_paid",
        "payload": {"invoice_id": invoice_id, "status": "paid"},
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    secret = hashlib.sha256(token.encode("utf-8")).digest()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return body, signature
