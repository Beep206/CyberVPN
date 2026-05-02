from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.presentation.api.v1.partner_bots import routes as partner_bot_routes
from src.presentation.api.v1.partner_bots.routes import (
    claim_partner_bot_provisioning_job,
    create_partner_bot,
    finalize_partner_bot_provisioning_job,
    get_partner_bot,
    list_partner_bots,
    request_partner_bot_provisioning,
    restore_partner_bot,
    rotate_partner_bot_token,
    suspend_partner_bot,
)
from src.presentation.api.v1.partner_bots.schemas import (
    ClaimPartnerBotProvisioningJobRequest,
    CreatePartnerBotRequest,
    FinalizePartnerBotProvisioningJobRequest,
    RequestPartnerBotProvisioningRequest,
    RotatePartnerBotTokenRequest,
    SuspendPartnerBotRequest,
)


def _build_bundle(*, status: str = "draft", latest_job_status: str | None = None):
    bot_id = uuid4()
    partner_account_id = uuid4()
    bot = SimpleNamespace(
        id=bot_id,
        partner_account_id=partner_account_id,
        storefront_id=None,
        bot_key="alpha-bot",
        display_name="Alpha Bot",
        short_description="Partner launch bot",
        long_description=None,
        telegram_bot_id=None,
        telegram_username=None,
        managed_by_bot_id=None,
        default_locale="en-EN",
        primary_color="#00ffaa",
        provisioning_path="managed_bot",
        token_status="missing",
        status=status,
        release_channel="stable",
        provisioning_last_error=None,
        provisioning_requested_at=datetime.now(UTC),
        provisioned_at=None,
        suspended_at=None,
        suspension_reason_code=None,
        created_by_admin_user_id=uuid4(),
        updated_by_admin_user_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    latest_job = (
        SimpleNamespace(
            id=uuid4(),
            partner_bot_id=bot_id,
            partner_account_id=partner_account_id,
            requested_by_admin_user_id=uuid4(),
            provisioning_path="managed_bot",
            job_status=latest_job_status,
            attempt_count=1,
            request_payload={"source": "portal"},
            result_payload={},
            last_error=None,
            queued_at=datetime.now(UTC),
            started_at=None,
            completed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        if latest_job_status is not None
        else None
    )
    return SimpleNamespace(bot=bot, latest_provisioning_job=latest_job)


async def _allow_workspace_permission(**_kwargs) -> None:
    return None


def test_list_partner_bots_serializes_latest_jobs(monkeypatch) -> None:
    bundle = _build_bundle(status="active", latest_job_status="completed")

    class FakeListPartnerBotsUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return [bundle]

    monkeypatch.setattr(partner_bot_routes, "_require_workspace_permission", _allow_workspace_permission)
    monkeypatch.setattr(partner_bot_routes, "ListPartnerBotsUseCase", FakeListPartnerBotsUseCase)

    response = asyncio.run(
        list_partner_bots(
            partner_account_id=bundle.bot.partner_account_id,
            bot_status=None,
            limit=100,
            offset=0,
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
        )
    )

    assert len(response) == 1
    assert response[0].status == "active"
    assert response[0].latest_provisioning_job is not None
    assert response[0].latest_provisioning_job.job_status == "completed"


def test_create_partner_bot_returns_draft_payload(monkeypatch) -> None:
    bundle = _build_bundle(status="draft")

    class FakeCreatePartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return bundle

    monkeypatch.setattr(partner_bot_routes, "_require_workspace_permission", _allow_workspace_permission)
    monkeypatch.setattr(partner_bot_routes, "CreatePartnerBotUseCase", FakeCreatePartnerBotUseCase)

    response = asyncio.run(
        create_partner_bot(
            payload=CreatePartnerBotRequest(
                partner_account_id=bundle.bot.partner_account_id,
                bot_key="alpha-bot",
                display_name="Alpha Bot",
            ),
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
        )
    )

    assert response.bot_key == "alpha-bot"
    assert response.status == "draft"
    assert response.provisioning_path == "managed_bot"


def test_get_partner_bot_raises_404_when_missing(monkeypatch) -> None:
    class FakeGetPartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return None

    monkeypatch.setattr(partner_bot_routes, "GetPartnerBotUseCase", FakeGetPartnerBotUseCase)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            get_partner_bot(
                partner_bot_id=uuid4(),
                current_user=SimpleNamespace(id=uuid4()),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_request_partner_bot_provisioning_returns_queued_job(monkeypatch) -> None:
    existing_bundle = _build_bundle(status="draft")
    queued_bundle = _build_bundle(status="provisioning_requested", latest_job_status="queued")

    class FakeGetPartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return existing_bundle

    class FakeRequestPartnerBotProvisioningUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return queued_bundle

    monkeypatch.setattr(partner_bot_routes, "_require_workspace_permission", _allow_workspace_permission)
    monkeypatch.setattr(partner_bot_routes, "GetPartnerBotUseCase", FakeGetPartnerBotUseCase)
    monkeypatch.setattr(
        partner_bot_routes,
        "RequestPartnerBotProvisioningUseCase",
        FakeRequestPartnerBotProvisioningUseCase,
    )

    response = asyncio.run(
        request_partner_bot_provisioning(
            partner_bot_id=existing_bundle.bot.id,
            payload=RequestPartnerBotProvisioningRequest(request_payload={"trigger": "manual"}),
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
        )
    )

    assert response.status == "provisioning_requested"
    assert response.latest_provisioning_job is not None
    assert response.latest_provisioning_job.job_status == "queued"


def test_claim_partner_bot_provisioning_job_returns_bundle(monkeypatch) -> None:
    bundle = _build_bundle(status="provisioning_running", latest_job_status="validating_partner")

    class FakeClaimPartnerBotProvisioningJobUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return bundle

    monkeypatch.setattr(partner_bot_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(
        partner_bot_routes,
        "ClaimPartnerBotProvisioningJobUseCase",
        FakeClaimPartnerBotProvisioningJobUseCase,
    )

    response = asyncio.run(
        claim_partner_bot_provisioning_job(
            payload=ClaimPartnerBotProvisioningJobRequest(processor_id="task-worker:partner-bot-provisioning"),
            telegram_bot_secret="internal-secret",
            db=object(),
        )
    )

    assert response.bot is not None
    assert response.bot.status == "provisioning_running"
    assert response.bot.latest_provisioning_job is not None
    assert response.bot.latest_provisioning_job.job_status == "validating_partner"


def test_finalize_partner_bot_provisioning_job_returns_updated_bundle(monkeypatch) -> None:
    bundle = _build_bundle(status="degraded", latest_job_status="manual_intervention_required")
    bundle.bot.provisioning_last_error = "Manual intervention required"

    class FakeFinalizePartnerBotProvisioningJobUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return bundle

    monkeypatch.setattr(partner_bot_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(
        partner_bot_routes,
        "FinalizePartnerBotProvisioningJobUseCase",
        FakeFinalizePartnerBotProvisioningJobUseCase,
    )

    response = asyncio.run(
        finalize_partner_bot_provisioning_job(
            partner_bot_provisioning_job_id=bundle.latest_provisioning_job.id,
            payload=FinalizePartnerBotProvisioningJobRequest(
                processor_id="task-worker:partner-bot-provisioning",
                job_status="manual_intervention_required",
                result_payload={"reason_code": "managed_bot_runtime_not_implemented"},
                last_error="Manual intervention required",
            ),
            telegram_bot_secret="internal-secret",
            db=object(),
        )
    )

    assert response.status == "degraded"
    assert response.latest_provisioning_job is not None
    assert response.latest_provisioning_job.job_status == "manual_intervention_required"


def test_suspend_partner_bot_returns_suspended_bundle(monkeypatch) -> None:
    existing_bundle = _build_bundle(status="active")
    suspended_bundle = _build_bundle(status="suspended", latest_job_status="completed")
    suspended_bundle.bot.suspension_reason_code = "policy_hold"

    class FakeGetPartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return existing_bundle

    class FakeSuspendPartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return suspended_bundle

    monkeypatch.setattr(partner_bot_routes, "_require_workspace_permission", _allow_workspace_permission)
    monkeypatch.setattr(partner_bot_routes, "GetPartnerBotUseCase", FakeGetPartnerBotUseCase)
    monkeypatch.setattr(partner_bot_routes, "SuspendPartnerBotUseCase", FakeSuspendPartnerBotUseCase)

    response = asyncio.run(
        suspend_partner_bot(
            partner_bot_id=existing_bundle.bot.id,
            payload=SuspendPartnerBotRequest(reason_code="policy_hold"),
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
        )
    )

    assert response.status == "suspended"
    assert response.suspension_reason_code == "policy_hold"


def test_restore_partner_bot_returns_active_bundle(monkeypatch) -> None:
    existing_bundle = _build_bundle(status="suspended", latest_job_status="completed")
    restored_bundle = _build_bundle(status="active", latest_job_status="completed")

    class FakeGetPartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return existing_bundle

    class FakeRestorePartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return restored_bundle

    monkeypatch.setattr(partner_bot_routes, "_require_workspace_permission", _allow_workspace_permission)
    monkeypatch.setattr(partner_bot_routes, "GetPartnerBotUseCase", FakeGetPartnerBotUseCase)
    monkeypatch.setattr(partner_bot_routes, "RestorePartnerBotUseCase", FakeRestorePartnerBotUseCase)

    response = asyncio.run(
        restore_partner_bot(
            partner_bot_id=existing_bundle.bot.id,
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
        )
    )

    assert response.status == "active"


def test_rotate_partner_bot_token_returns_queued_job(monkeypatch) -> None:
    existing_bundle = _build_bundle(status="active", latest_job_status="completed")
    queued_bundle = _build_bundle(status="provisioning_requested", latest_job_status="queued")
    queued_bundle.bot.token_status = "rotating"

    class FakeGetPartnerBotUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return existing_bundle

    class FakeRotatePartnerBotTokenUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return queued_bundle

    monkeypatch.setattr(partner_bot_routes, "_require_workspace_permission", _allow_workspace_permission)
    monkeypatch.setattr(partner_bot_routes, "GetPartnerBotUseCase", FakeGetPartnerBotUseCase)
    monkeypatch.setattr(
        partner_bot_routes,
        "RotatePartnerBotTokenUseCase",
        FakeRotatePartnerBotTokenUseCase,
    )

    response = asyncio.run(
        rotate_partner_bot_token(
            partner_bot_id=existing_bundle.bot.id,
            payload=RotatePartnerBotTokenRequest(request_payload={"handoff_reference": "bf-001"}),
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
        )
    )

    assert response.status == "provisioning_requested"
    assert response.token_status == "rotating"
    assert response.latest_provisioning_job is not None
    assert response.latest_provisioning_job.job_status == "queued"
