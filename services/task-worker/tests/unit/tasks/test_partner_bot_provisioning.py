"""Unit tests for partner bot provisioning orchestration tasks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.tasks.partner_bots.process_provisioning_jobs import (
    _build_manual_intervention_payload,
    process_partner_bot_provisioning_jobs,
)


@pytest.mark.asyncio
async def test_process_partner_bot_provisioning_jobs_marks_managed_bot_for_manual_intervention(
    mock_settings,
):
    claimed_bot = {
        "id": "bot-1",
        "bot_key": "alpha-bot",
        "provisioning_path": "managed_bot",
        "latest_provisioning_job": {
            "id": "job-1",
            "job_status": "validating_partner",
        },
    }
    finalized_bot = {
        "id": "bot-1",
        "latest_provisioning_job": {
            "id": "job-1",
            "job_status": "manual_intervention_required",
        },
    }

    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.claim_partner_bot_provisioning_job = AsyncMock(
        side_effect=[{"bot": claimed_bot}, {"bot": None}]
    )
    mock_backend.finalize_partner_bot_provisioning_job = AsyncMock(return_value=finalized_bot)

    with (
        patch(
            "src.tasks.partner_bots.process_provisioning_jobs.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.partner_bots.process_provisioning_jobs.BackendAPIClient"
        ) as mock_backend_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_partner_bot_provisioning_jobs()

    assert result["processed"] == 1
    assert result["errors"] == 0
    assert result["actions"] == {"manual_intervention_required": 1}
    mock_backend.finalize_partner_bot_provisioning_job.assert_awaited_once()
    finalize_kwargs = mock_backend.finalize_partner_bot_provisioning_job.await_args.kwargs
    assert finalize_kwargs["provisioning_job_id"] == "job-1"
    assert finalize_kwargs["payload"]["job_status"] == "manual_intervention_required"
    assert (
        finalize_kwargs["payload"]["result_payload"]["reason_code"]
        == "managed_bot_runtime_not_implemented"
    )


@pytest.mark.asyncio
async def test_process_partner_bot_provisioning_jobs_skips_when_backend_not_configured(
    mock_settings,
):
    mock_settings.backend_api_url = None

    with patch(
        "src.tasks.partner_bots.process_provisioning_jobs.get_settings",
        return_value=mock_settings,
    ):
        result = await process_partner_bot_provisioning_jobs()

    assert result == {"skipped": True, "reason": "backend_api_not_configured"}


def test_build_manual_intervention_payload_for_manual_token_path() -> None:
    payload = _build_manual_intervention_payload(
        {
            "bot_key": "alpha-bot",
            "provisioning_path": "manual_token",
        }
    )

    assert payload["job_status"] == "manual_intervention_required"
    assert payload["result_payload"]["reason_code"] == "manual_token_required"
    assert payload["result_payload"]["operator_action"] == "collect_manual_bot_token_and_resume_provisioning"
