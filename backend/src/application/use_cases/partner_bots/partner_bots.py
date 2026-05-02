from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.domain.enums import (
    PartnerAccountStatus,
    PartnerBotProvisioningJobStatus,
    PartnerBotProvisioningPath,
    PartnerBotStatus,
    PartnerBotTokenStatus,
)
from src.infrastructure.database.models.partner_bot_model import (
    PartnerBotModel,
    PartnerBotProvisioningJobModel,
)
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_bot_repo import PartnerBotRepository

_WORKSPACE_BOT_ALLOWED_STATUSES = {
    PartnerAccountStatus.APPROVED_PROBATION.value,
    PartnerAccountStatus.ACTIVE.value,
    PartnerAccountStatus.RESTRICTED.value,
}
_ACTIVE_PROVISIONING_JOB_STATUSES = {
    PartnerBotProvisioningJobStatus.QUEUED.value,
    PartnerBotProvisioningJobStatus.VALIDATING_PARTNER.value,
    PartnerBotProvisioningJobStatus.RESERVING_BOT_IDENTITY.value,
    PartnerBotProvisioningJobStatus.APPLYING_BRANDING.value,
    PartnerBotProvisioningJobStatus.CONFIGURING_COMMANDS.value,
    PartnerBotProvisioningJobStatus.CONFIGURING_MENU_BUTTON.value,
    PartnerBotProvisioningJobStatus.BINDING_WEBHOOK.value,
    PartnerBotProvisioningJobStatus.BINDING_MINIAPP.value,
    PartnerBotProvisioningJobStatus.GENERATING_LAUNCH_ASSETS.value,
    PartnerBotProvisioningJobStatus.PUBLISHING.value,
}
_TERMINAL_PROVISIONING_JOB_STATUSES = {
    PartnerBotProvisioningJobStatus.COMPLETED.value,
    PartnerBotProvisioningJobStatus.FAILED_VALIDATION.value,
    PartnerBotProvisioningJobStatus.FAILED_BOT_CREATION.value,
    PartnerBotProvisioningJobStatus.FAILED_TOKEN_FETCH.value,
    PartnerBotProvisioningJobStatus.FAILED_WEBHOOK_BINDING.value,
    PartnerBotProvisioningJobStatus.FAILED_BRANDING.value,
    PartnerBotProvisioningJobStatus.ROLLBACK_REQUIRED.value,
    PartnerBotProvisioningJobStatus.MANUAL_INTERVENTION_REQUIRED.value,
}
_FAILED_PROVISIONING_JOB_STATUSES = _TERMINAL_PROVISIONING_JOB_STATUSES - {
    PartnerBotProvisioningJobStatus.COMPLETED.value,
    PartnerBotProvisioningJobStatus.MANUAL_INTERVENTION_REQUIRED.value,
}


@dataclass(frozen=True)
class PartnerBotBundle:
    bot: PartnerBotModel
    latest_provisioning_job: PartnerBotProvisioningJobModel | None


def _normalize_bot_key(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("bot_key is required")
    return normalized


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class CreatePartnerBotUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._partners = PartnerAccountRepository(session)
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        bot_key: str,
        display_name: str,
        default_locale: str = "en-EN",
        primary_color: str | None = None,
        short_description: str | None = None,
        long_description: str | None = None,
        storefront_id: UUID | None = None,
        release_channel: str = "stable",
        provisioning_path: str = PartnerBotProvisioningPath.MANAGED_BOT.value,
        created_by_admin_user_id: UUID | None = None,
    ) -> PartnerBotBundle:
        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")
        if workspace.status not in _WORKSPACE_BOT_ALLOWED_STATUSES:
            raise ValueError("Partner workspace must be approved before creating partner bots")

        normalized_bot_key = _normalize_bot_key(bot_key)
        existing = await self._repo.get_bot_by_key(partner_account_id=partner_account_id, bot_key=normalized_bot_key)
        if existing is not None:
            raise ValueError("Partner bot with this bot_key already exists")

        normalized_display_name = display_name.strip()
        if not normalized_display_name:
            raise ValueError("display_name is required")

        model = PartnerBotModel(
            partner_account_id=partner_account_id,
            storefront_id=storefront_id,
            bot_key=normalized_bot_key,
            display_name=normalized_display_name,
            default_locale=(default_locale or "en-EN").strip() or "en-EN",
            primary_color=_normalize_text(primary_color),
            short_description=_normalize_text(short_description),
            long_description=_normalize_text(long_description),
            provisioning_path=PartnerBotProvisioningPath(provisioning_path).value,
            token_status=PartnerBotTokenStatus.MISSING.value,
            status=PartnerBotStatus.DRAFT.value,
            release_channel=(release_channel or "stable").strip() or "stable",
            created_by_admin_user_id=created_by_admin_user_id,
            updated_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._repo.create_bot(model)
        await self._outbox.append_event(
            event_name="partner_bot.created",
            aggregate_type="partner_bot",
            aggregate_id=str(created.id),
            partition_key=str(partner_account_id),
            event_payload={
                "partner_bot_id": str(created.id),
                "partner_account_id": str(partner_account_id),
                "bot_key": created.bot_key,
                "status": created.status,
                "provisioning_path": created.provisioning_path,
            },
            actor_context=_build_actor_context(created_by_admin_user_id),
            source_context={"source_use_case": "CreatePartnerBotUseCase"},
        )
        return PartnerBotBundle(bot=created, latest_provisioning_job=None)


class ListPartnerBotsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        bot_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerBotBundle]:
        bots = await self._repo.list_bots(
            partner_account_id=partner_account_id,
            bot_status=bot_status,
            limit=limit,
            offset=offset,
        )
        jobs = await self._repo.list_provisioning_jobs(
            partner_bot_ids=[item.id for item in bots],
            limit=max(len(bots) * 5, 1),
            offset=0,
        )
        latest_by_bot_id: dict[UUID, PartnerBotProvisioningJobModel] = {}
        for job in jobs:
            latest_by_bot_id.setdefault(job.partner_bot_id, job)
        return [
            PartnerBotBundle(
                bot=item,
                latest_provisioning_job=latest_by_bot_id.get(item.id),
            )
            for item in bots
        ]


class GetPartnerBotUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)

    async def execute(self, *, partner_bot_id: UUID) -> PartnerBotBundle | None:
        bot = await self._repo.get_bot_by_id(partner_bot_id)
        if bot is None:
            return None
        latest_job = await self._repo.get_latest_provisioning_job(partner_bot_id=partner_bot_id)
        return PartnerBotBundle(bot=bot, latest_provisioning_job=latest_job)


class RequestPartnerBotProvisioningUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        partner_bot_id: UUID,
        requested_by_admin_user_id: UUID | None,
        provisioning_path: str | None = None,
        request_payload: dict | None = None,
    ) -> PartnerBotBundle:
        bot = await self._repo.get_bot_by_id(partner_bot_id)
        if bot is None:
            raise ValueError("Partner bot not found")
        if bot.status in {
            PartnerBotStatus.SUSPENDED.value,
            PartnerBotStatus.REVOKED.value,
        }:
            raise ValueError("Suspended or revoked partner bots cannot be provisioned")

        latest_job = await self._repo.get_latest_provisioning_job(partner_bot_id=partner_bot_id)
        if latest_job is not None and latest_job.job_status in _ACTIVE_PROVISIONING_JOB_STATUSES:
            raise ValueError("Provisioning is already in progress for this partner bot")

        normalized_path = (
            PartnerBotProvisioningPath(provisioning_path).value
            if provisioning_path is not None
            else bot.provisioning_path
        )
        now = datetime.now(UTC)
        previous_status = bot.status
        bot.provisioning_path = normalized_path
        bot.provisioning_requested_at = now
        bot.provisioning_last_error = None
        bot.status = PartnerBotStatus.PROVISIONING_REQUESTED.value
        bot.updated_by_admin_user_id = requested_by_admin_user_id
        await self._repo.update_bot(bot)

        job = await self._repo.create_provisioning_job(
            PartnerBotProvisioningJobModel(
                partner_bot_id=bot.id,
                partner_account_id=bot.partner_account_id,
                requested_by_admin_user_id=requested_by_admin_user_id,
                provisioning_path=normalized_path,
                job_status=PartnerBotProvisioningJobStatus.QUEUED.value,
                attempt_count=0,
                request_payload=dict(request_payload or {}),
                result_payload={},
                queued_at=now,
            )
        )
        await _append_provisioning_requested_event(
            outbox=self._outbox,
            bot=bot,
            job=job,
            actor_context=_build_actor_context(requested_by_admin_user_id),
            source_use_case="RequestPartnerBotProvisioningUseCase",
        )
        await _append_status_changed_event(
            outbox=self._outbox,
            bot=bot,
            previous_status=previous_status,
            actor_context=_build_actor_context(requested_by_admin_user_id),
            source_use_case="RequestPartnerBotProvisioningUseCase",
            metadata={
                "partner_bot_provisioning_job_id": str(job.id),
                "job_status": job.job_status,
            },
        )
        return PartnerBotBundle(bot=bot, latest_provisioning_job=job)


class ClaimPartnerBotProvisioningJobUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._partners = PartnerAccountRepository(session)
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        processor_id: str,
        max_scan_count: int = 10,
    ) -> PartnerBotBundle | None:
        normalized_processor_id = processor_id.strip() or "task-worker:partner-bot-provisioning"

        for _ in range(max(max_scan_count, 1)):
            job = await self._repo.claim_next_queued_provisioning_job()
            if job is None:
                return None

            bot = await self._repo.get_bot_by_id(job.partner_bot_id)
            if bot is None:
                await self._finalize_missing_bot_job(job=job, processor_id=normalized_processor_id)
                continue

            workspace = await self._partners.get_account_by_id(job.partner_account_id)
            if workspace is None or workspace.status not in _WORKSPACE_BOT_ALLOWED_STATUSES:
                await self._fail_validation(
                    bot=bot,
                    job=job,
                    processor_id=normalized_processor_id,
                    reason="Partner workspace is missing or not eligible for provisioning",
                )
                continue

            now = datetime.now(UTC)
            previous_status = bot.status
            job.job_status = PartnerBotProvisioningJobStatus.VALIDATING_PARTNER.value
            job.attempt_count += 1
            job.started_at = job.started_at or now
            job.last_error = None
            job.result_payload = {
                **dict(job.result_payload or {}),
                "claimed_by": normalized_processor_id,
                "claimed_at": now.isoformat(),
                "validation": "passed",
            }
            bot.status = PartnerBotStatus.PROVISIONING_RUNNING.value
            bot.provisioning_last_error = None
            await self._repo.update_provisioning_job(job)
            await self._repo.update_bot(bot)
            await _append_status_changed_event(
                outbox=self._outbox,
                bot=bot,
                previous_status=previous_status,
                actor_context=_build_system_actor_context(normalized_processor_id),
                source_use_case="ClaimPartnerBotProvisioningJobUseCase",
                metadata={
                    "partner_bot_provisioning_job_id": str(job.id),
                    "job_status": job.job_status,
                },
            )
            return PartnerBotBundle(bot=bot, latest_provisioning_job=job)

        return None

    async def _finalize_missing_bot_job(
        self,
        *,
        job: PartnerBotProvisioningJobModel,
        processor_id: str,
    ) -> None:
        now = datetime.now(UTC)
        job.job_status = PartnerBotProvisioningJobStatus.FAILED_VALIDATION.value
        job.attempt_count += 1
        job.started_at = job.started_at or now
        job.completed_at = now
        job.last_error = "Partner bot not found for provisioning job"
        job.result_payload = {
            **dict(job.result_payload or {}),
            "claimed_by": processor_id,
            "completed_by": processor_id,
            "completed_at": now.isoformat(),
            "reason_code": "partner_bot_missing",
        }
        await self._repo.update_provisioning_job(job)

    async def _fail_validation(
        self,
        *,
        bot: PartnerBotModel,
        job: PartnerBotProvisioningJobModel,
        processor_id: str,
        reason: str,
    ) -> None:
        now = datetime.now(UTC)
        previous_status = bot.status
        job.job_status = PartnerBotProvisioningJobStatus.FAILED_VALIDATION.value
        job.attempt_count += 1
        job.started_at = job.started_at or now
        job.completed_at = now
        job.last_error = reason
        job.result_payload = {
            **dict(job.result_payload or {}),
            "claimed_by": processor_id,
            "completed_by": processor_id,
            "completed_at": now.isoformat(),
            "reason_code": "workspace_validation_failed",
        }
        bot.status = PartnerBotStatus.FAILED.value
        bot.provisioning_last_error = reason
        await self._repo.update_provisioning_job(job)
        await self._repo.update_bot(bot)
        await _append_status_changed_event(
            outbox=self._outbox,
            bot=bot,
            previous_status=previous_status,
            actor_context=_build_system_actor_context(processor_id),
            source_use_case="ClaimPartnerBotProvisioningJobUseCase",
            metadata={
                "partner_bot_provisioning_job_id": str(job.id),
                "job_status": job.job_status,
                "reason": reason,
            },
        )

class FinalizePartnerBotProvisioningJobUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        partner_bot_provisioning_job_id: UUID,
        processor_id: str,
        job_status: str,
        result_payload: dict | None = None,
        last_error: str | None = None,
        telegram_bot_id: str | None = None,
        telegram_username: str | None = None,
        managed_by_bot_id: str | None = None,
        token_status: str | None = None,
    ) -> PartnerBotBundle:
        normalized_processor_id = processor_id.strip() or "task-worker:partner-bot-provisioning"
        normalized_job_status = PartnerBotProvisioningJobStatus(job_status).value
        if normalized_job_status not in _TERMINAL_PROVISIONING_JOB_STATUSES:
            raise ValueError("Provisioning jobs can only be finalized to terminal statuses")

        job = await self._repo.get_provisioning_job_by_id(partner_bot_provisioning_job_id)
        if job is None:
            raise ValueError("Partner bot provisioning job not found")

        bot = await self._repo.get_bot_by_id(job.partner_bot_id)
        if bot is None:
            raise ValueError("Partner bot not found")

        if job.job_status in _TERMINAL_PROVISIONING_JOB_STATUSES:
            if job.job_status != normalized_job_status:
                raise ValueError("Partner bot provisioning job has already been finalized")
            return PartnerBotBundle(bot=bot, latest_provisioning_job=job)

        now = datetime.now(UTC)
        previous_status = bot.status
        normalized_last_error = _normalize_text(last_error)

        job.job_status = normalized_job_status
        job.started_at = job.started_at or now
        job.completed_at = now
        job.last_error = normalized_last_error
        job.result_payload = {
            **dict(job.result_payload or {}),
            **dict(result_payload or {}),
            "completed_by": normalized_processor_id,
            "completed_at": now.isoformat(),
        }

        if normalized_job_status == PartnerBotProvisioningJobStatus.COMPLETED.value:
            bot.status = PartnerBotStatus.ACTIVE.value
            bot.provisioned_at = now
            bot.provisioning_last_error = None
            if token_status is not None:
                bot.token_status = PartnerBotTokenStatus(token_status).value
            if telegram_bot_id is not None:
                bot.telegram_bot_id = _normalize_text(telegram_bot_id)
            if telegram_username is not None:
                bot.telegram_username = _normalize_text(telegram_username)
            if managed_by_bot_id is not None:
                bot.managed_by_bot_id = _normalize_text(managed_by_bot_id)
        elif normalized_job_status == PartnerBotProvisioningJobStatus.MANUAL_INTERVENTION_REQUIRED.value:
            bot.status = PartnerBotStatus.DEGRADED.value
            bot.provisioning_last_error = normalized_last_error or "Manual intervention required"
        elif normalized_job_status == PartnerBotProvisioningJobStatus.ROLLBACK_REQUIRED.value:
            bot.status = PartnerBotStatus.DEGRADED.value
            bot.provisioning_last_error = normalized_last_error or "Provisioning rollback required"
        elif normalized_job_status in _FAILED_PROVISIONING_JOB_STATUSES:
            bot.status = PartnerBotStatus.FAILED.value
            bot.provisioning_last_error = normalized_last_error or normalized_job_status

        await self._repo.update_provisioning_job(job)
        await self._repo.update_bot(bot)
        await _append_status_changed_event(
            outbox=self._outbox,
            bot=bot,
            previous_status=previous_status,
            actor_context=_build_system_actor_context(normalized_processor_id),
            source_use_case="FinalizePartnerBotProvisioningJobUseCase",
            metadata={
                "partner_bot_provisioning_job_id": str(job.id),
                "job_status": job.job_status,
            },
        )
        return PartnerBotBundle(bot=bot, latest_provisioning_job=job)


class SuspendPartnerBotUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        partner_bot_id: UUID,
        suspended_by_admin_user_id: UUID | None,
        reason_code: str | None = None,
    ) -> PartnerBotBundle:
        bot = await self._repo.get_bot_by_id(partner_bot_id)
        if bot is None:
            raise ValueError("Partner bot not found")
        if bot.status == PartnerBotStatus.REVOKED.value:
            raise ValueError("Revoked partner bots cannot be suspended")
        if bot.status == PartnerBotStatus.SUSPENDED.value:
            latest_job = await self._repo.get_latest_provisioning_job(partner_bot_id=partner_bot_id)
            return PartnerBotBundle(bot=bot, latest_provisioning_job=latest_job)

        previous_status = bot.status
        bot.status = PartnerBotStatus.SUSPENDED.value
        bot.suspended_at = datetime.now(UTC)
        bot.suspension_reason_code = (_normalize_text(reason_code) or "operator_suspend")[:80]
        bot.updated_by_admin_user_id = suspended_by_admin_user_id
        await self._repo.update_bot(bot)
        await _append_status_changed_event(
            outbox=self._outbox,
            bot=bot,
            previous_status=previous_status,
            actor_context=_build_actor_context(suspended_by_admin_user_id),
            source_use_case="SuspendPartnerBotUseCase",
            metadata={"suspension_reason_code": bot.suspension_reason_code},
        )
        latest_job = await self._repo.get_latest_provisioning_job(partner_bot_id=partner_bot_id)
        return PartnerBotBundle(bot=bot, latest_provisioning_job=latest_job)


class RestorePartnerBotUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        partner_bot_id: UUID,
        restored_by_admin_user_id: UUID | None,
    ) -> PartnerBotBundle:
        bot = await self._repo.get_bot_by_id(partner_bot_id)
        if bot is None:
            raise ValueError("Partner bot not found")
        if bot.status != PartnerBotStatus.SUSPENDED.value:
            raise ValueError("Only suspended partner bots can be restored")

        previous_status = bot.status
        bot.suspended_at = None
        bot.suspension_reason_code = None
        bot.updated_by_admin_user_id = restored_by_admin_user_id
        bot.status = _resolve_restored_partner_bot_status(bot)
        await self._repo.update_bot(bot)
        await _append_status_changed_event(
            outbox=self._outbox,
            bot=bot,
            previous_status=previous_status,
            actor_context=_build_actor_context(restored_by_admin_user_id),
            source_use_case="RestorePartnerBotUseCase",
            metadata={},
        )
        latest_job = await self._repo.get_latest_provisioning_job(partner_bot_id=partner_bot_id)
        return PartnerBotBundle(bot=bot, latest_provisioning_job=latest_job)


class RotatePartnerBotTokenUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PartnerBotRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        partner_bot_id: UUID,
        requested_by_admin_user_id: UUID | None,
        request_payload: dict | None = None,
    ) -> PartnerBotBundle:
        bot = await self._repo.get_bot_by_id(partner_bot_id)
        if bot is None:
            raise ValueError("Partner bot not found")
        if bot.status in {
            PartnerBotStatus.REVOKED.value,
            PartnerBotStatus.SUSPENDED.value,
        }:
            raise ValueError("Suspended or revoked partner bots cannot rotate tokens")

        latest_job = await self._repo.get_latest_provisioning_job(partner_bot_id=partner_bot_id)
        if latest_job is not None and latest_job.job_status in _ACTIVE_PROVISIONING_JOB_STATUSES:
            raise ValueError("Provisioning is already in progress for this partner bot")

        previous_status = bot.status
        now = datetime.now(UTC)
        bot.token_status = PartnerBotTokenStatus.ROTATING.value
        bot.provisioning_requested_at = now
        bot.provisioning_last_error = None
        bot.status = PartnerBotStatus.PROVISIONING_REQUESTED.value
        bot.updated_by_admin_user_id = requested_by_admin_user_id
        await self._repo.update_bot(bot)

        job = await self._repo.create_provisioning_job(
            PartnerBotProvisioningJobModel(
                partner_bot_id=bot.id,
                partner_account_id=bot.partner_account_id,
                requested_by_admin_user_id=requested_by_admin_user_id,
                provisioning_path=bot.provisioning_path,
                job_status=PartnerBotProvisioningJobStatus.QUEUED.value,
                attempt_count=0,
                request_payload={
                    **dict(request_payload or {}),
                    "token_rotation_requested": True,
                },
                result_payload={},
                queued_at=now,
            )
        )
        await _append_provisioning_requested_event(
            outbox=self._outbox,
            bot=bot,
            job=job,
            actor_context=_build_actor_context(requested_by_admin_user_id),
            source_use_case="RotatePartnerBotTokenUseCase",
        )
        await _append_status_changed_event(
            outbox=self._outbox,
            bot=bot,
            previous_status=previous_status,
            actor_context=_build_actor_context(requested_by_admin_user_id),
            source_use_case="RotatePartnerBotTokenUseCase",
            metadata={
                "partner_bot_provisioning_job_id": str(job.id),
                "job_status": job.job_status,
                "token_status": bot.token_status,
            },
        )
        return PartnerBotBundle(bot=bot, latest_provisioning_job=job)


def _build_actor_context(admin_user_id: UUID | None) -> OutboxActorContext | None:
    if admin_user_id is None:
        return None
    return OutboxActorContext(principal_type="admin", principal_id=str(admin_user_id))


def _build_system_actor_context(processor_id: str) -> OutboxActorContext:
    return OutboxActorContext(principal_type="system", principal_id=processor_id)


async def _append_status_changed_event(
    *,
    outbox: EventOutboxService,
    bot: PartnerBotModel,
    previous_status: str,
    actor_context: OutboxActorContext | None,
    source_use_case: str,
    metadata: dict,
) -> None:
    if previous_status == bot.status:
        return
    await outbox.append_event(
        event_name="partner_bot.status_changed",
        aggregate_type="partner_bot",
        aggregate_id=str(bot.id),
        partition_key=str(bot.partner_account_id),
        event_payload={
            "partner_bot_id": str(bot.id),
            "partner_account_id": str(bot.partner_account_id),
            "previous_status": previous_status,
            "status": bot.status,
            **metadata,
        },
        actor_context=actor_context,
        source_context={"source_use_case": source_use_case},
    )


async def _append_provisioning_requested_event(
    *,
    outbox: EventOutboxService,
    bot: PartnerBotModel,
    job: PartnerBotProvisioningJobModel,
    actor_context: OutboxActorContext | None,
    source_use_case: str,
) -> None:
    await outbox.append_event(
        event_name="partner_bot.provisioning_requested",
        aggregate_type="partner_bot",
        aggregate_id=str(bot.id),
        partition_key=str(bot.partner_account_id),
        event_payload={
            "partner_bot_id": str(bot.id),
            "partner_account_id": str(bot.partner_account_id),
            "partner_bot_provisioning_job_id": str(job.id),
            "status": bot.status,
            "job_status": job.job_status,
            "provisioning_path": bot.provisioning_path,
        },
        actor_context=actor_context,
        source_context={"source_use_case": source_use_case},
    )


def _resolve_restored_partner_bot_status(bot: PartnerBotModel) -> str:
    if bot.provisioned_at is None:
        if bot.token_status == PartnerBotTokenStatus.ROTATING.value:
            return PartnerBotStatus.PROVISIONING_REQUESTED.value
        return PartnerBotStatus.DRAFT.value
    if bot.token_status == PartnerBotTokenStatus.ACTIVE.value:
        return PartnerBotStatus.ACTIVE.value
    return PartnerBotStatus.DEGRADED.value
