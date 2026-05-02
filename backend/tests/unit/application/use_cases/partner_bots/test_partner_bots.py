from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.partner_bots.partner_bots import (
    ClaimPartnerBotProvisioningJobUseCase,
    FinalizePartnerBotProvisioningJobUseCase,
    RestorePartnerBotUseCase,
    RotatePartnerBotTokenUseCase,
    SuspendPartnerBotUseCase,
)


def _build_job(*, job_status: str = "queued") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        partner_bot_id=uuid4(),
        partner_account_id=uuid4(),
        requested_by_admin_user_id=uuid4(),
        provisioning_path="managed_bot",
        job_status=job_status,
        attempt_count=0,
        request_payload={},
        result_payload={},
        last_error=None,
        queued_at=datetime.now(UTC),
        started_at=None,
        completed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _build_bot(*, bot_id=None, partner_account_id=None, status: str = "provisioning_requested") -> SimpleNamespace:
    return SimpleNamespace(
        id=bot_id or uuid4(),
        partner_account_id=partner_account_id or uuid4(),
        storefront_id=None,
        bot_key="alpha-bot",
        display_name="Alpha Bot",
        short_description=None,
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
        provisioning_last_error="stale-error",
        provisioning_requested_at=datetime.now(UTC),
        provisioned_at=None,
        suspended_at=None,
        suspension_reason_code=None,
        created_by_admin_user_id=None,
        updated_by_admin_user_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_claim_partner_bot_provisioning_job_moves_bot_to_running() -> None:
    session = AsyncMock()
    job = _build_job()
    bot = _build_bot(bot_id=job.partner_bot_id, partner_account_id=job.partner_account_id)
    workspace = SimpleNamespace(status="active")

    use_case = ClaimPartnerBotProvisioningJobUseCase(session)
    use_case._repo = MagicMock()
    use_case._partners = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.claim_next_queued_provisioning_job = AsyncMock(return_value=job)
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.update_provisioning_job = AsyncMock(return_value=job)
    use_case._repo.update_bot = AsyncMock(return_value=bot)
    use_case._partners.get_account_by_id = AsyncMock(return_value=workspace)
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(processor_id="task-worker:partner-bot-provisioning")

    assert bundle is not None
    assert bundle.bot is bot
    assert bundle.latest_provisioning_job is job
    assert bot.status == "provisioning_running"
    assert bot.provisioning_last_error is None
    assert job.job_status == "validating_partner"
    assert job.attempt_count == 1
    assert job.started_at is not None
    use_case._outbox.append_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_partner_bot_provisioning_job_fails_validation_for_ineligible_workspace() -> None:
    session = AsyncMock()
    job = _build_job()
    bot = _build_bot(bot_id=job.partner_bot_id, partner_account_id=job.partner_account_id)
    workspace = SimpleNamespace(status="pending_review")

    use_case = ClaimPartnerBotProvisioningJobUseCase(session)
    use_case._repo = MagicMock()
    use_case._partners = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.claim_next_queued_provisioning_job = AsyncMock(side_effect=[job, None])
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.update_provisioning_job = AsyncMock(return_value=job)
    use_case._repo.update_bot = AsyncMock(return_value=bot)
    use_case._partners.get_account_by_id = AsyncMock(return_value=workspace)
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(processor_id="task-worker:partner-bot-provisioning")

    assert bundle is None
    assert bot.status == "failed"
    assert bot.provisioning_last_error == "Partner workspace is missing or not eligible for provisioning"
    assert job.job_status == "failed_validation"
    assert job.completed_at is not None
    use_case._outbox.append_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_partner_bot_provisioning_job_marks_manual_intervention_required() -> None:
    session = AsyncMock()
    job = _build_job(job_status="validating_partner")
    bot = _build_bot(
        bot_id=job.partner_bot_id,
        partner_account_id=job.partner_account_id,
        status="provisioning_running",
    )

    use_case = FinalizePartnerBotProvisioningJobUseCase(session)
    use_case._repo = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.get_provisioning_job_by_id = AsyncMock(return_value=job)
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.update_provisioning_job = AsyncMock(return_value=job)
    use_case._repo.update_bot = AsyncMock(return_value=bot)
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(
        partner_bot_provisioning_job_id=job.id,
        processor_id="task-worker:partner-bot-provisioning",
        job_status="manual_intervention_required",
        result_payload={"reason_code": "managed_bot_runtime_not_implemented"},
        last_error="Managed bot provisioning is queued for operator completion",
    )

    assert bundle.bot is bot
    assert bundle.latest_provisioning_job is job
    assert job.job_status == "manual_intervention_required"
    assert job.completed_at is not None
    assert bot.status == "degraded"
    assert bot.provisioning_last_error == "Managed bot provisioning is queued for operator completion"
    use_case._outbox.append_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_partner_bot_provisioning_job_is_idempotent_for_same_terminal_state() -> None:
    session = AsyncMock()
    job = _build_job(job_status="manual_intervention_required")
    job.completed_at = datetime.now(UTC)
    bot = _build_bot(bot_id=job.partner_bot_id, partner_account_id=job.partner_account_id, status="degraded")

    use_case = FinalizePartnerBotProvisioningJobUseCase(session)
    use_case._repo = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.get_provisioning_job_by_id = AsyncMock(return_value=job)
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.update_provisioning_job = AsyncMock()
    use_case._repo.update_bot = AsyncMock()
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(
        partner_bot_provisioning_job_id=job.id,
        processor_id="task-worker:partner-bot-provisioning",
        job_status="manual_intervention_required",
        result_payload={},
        last_error="ignored",
    )

    assert bundle.bot is bot
    assert bundle.latest_provisioning_job is job
    use_case._repo.update_provisioning_job.assert_not_awaited()
    use_case._repo.update_bot.assert_not_awaited()
    use_case._outbox.append_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_suspend_partner_bot_transitions_to_suspended() -> None:
    session = AsyncMock()
    bot = _build_bot(status="active")
    latest_job = _build_job(job_status="completed")

    use_case = SuspendPartnerBotUseCase(session)
    use_case._repo = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.update_bot = AsyncMock(return_value=bot)
    use_case._repo.get_latest_provisioning_job = AsyncMock(return_value=latest_job)
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(
        partner_bot_id=bot.id,
        suspended_by_admin_user_id=uuid4(),
        reason_code="policy_hold",
    )

    assert bundle.bot is bot
    assert bundle.latest_provisioning_job is latest_job
    assert bot.status == "suspended"
    assert bot.suspension_reason_code == "policy_hold"
    assert bot.suspended_at is not None
    use_case._outbox.append_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_partner_bot_returns_to_active_when_token_is_live() -> None:
    session = AsyncMock()
    bot = _build_bot(status="suspended")
    bot.token_status = "active"
    bot.provisioned_at = datetime.now(UTC)

    use_case = RestorePartnerBotUseCase(session)
    use_case._repo = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.update_bot = AsyncMock(return_value=bot)
    use_case._repo.get_latest_provisioning_job = AsyncMock(return_value=None)
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(
        partner_bot_id=bot.id,
        restored_by_admin_user_id=uuid4(),
    )

    assert bundle.bot is bot
    assert bot.status == "active"
    assert bot.suspended_at is None
    assert bot.suspension_reason_code is None
    use_case._outbox.append_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_rotate_partner_bot_token_queues_rotation_job() -> None:
    session = AsyncMock()
    bot = _build_bot(status="active")
    bot.token_status = "active"
    latest_job = _build_job(job_status="completed")
    rotation_job = _build_job(job_status="queued")
    rotation_job.partner_bot_id = bot.id
    rotation_job.partner_account_id = bot.partner_account_id

    use_case = RotatePartnerBotTokenUseCase(session)
    use_case._repo = MagicMock()
    use_case._outbox = MagicMock()
    use_case._repo.get_bot_by_id = AsyncMock(return_value=bot)
    use_case._repo.get_latest_provisioning_job = AsyncMock(return_value=latest_job)
    use_case._repo.update_bot = AsyncMock(return_value=bot)
    use_case._repo.create_provisioning_job = AsyncMock(return_value=rotation_job)
    use_case._outbox.append_event = AsyncMock()

    bundle = await use_case.execute(
        partner_bot_id=bot.id,
        requested_by_admin_user_id=uuid4(),
        request_payload={"handoff_reference": "bf-001"},
    )

    assert bundle.bot is bot
    assert bundle.latest_provisioning_job is rotation_job
    assert bot.status == "provisioning_requested"
    assert bot.token_status == "rotating"
    assert bot.provisioning_requested_at is not None
    use_case._outbox.append_event.assert_awaited()
    create_call = use_case._repo.create_provisioning_job.await_args.args[0]
    assert create_call.request_payload["token_rotation_requested"] is True
    assert create_call.request_payload["handoff_reference"] == "bf-001"
