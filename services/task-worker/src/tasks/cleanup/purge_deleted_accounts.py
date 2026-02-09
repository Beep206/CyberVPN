"""GDPR data purge task for soft-deleted accounts past the 30-day grace period.

When a user deletes their account the backend sets ``deleted_at`` and
``is_active=False``.  After 30 days this task permanently removes all
personally identifiable information (PII) to comply with GDPR Article 17
("Right to Erasure").

The task is **idempotent**: re-running it on already-purged rows is a no-op
because the WHERE clause filters on ``deleted_at IS NOT NULL`` and
``email IS NOT NULL`` (non-anonymised records only).

Purge strategy per record:
    1. Anonymise the ``admin_users`` row -- set email/password_hash/telegram_id
       to NULL, replace login with ``deleted_<uuid>``
    2. Hard-delete related ``otp_codes``
    3. Hard-delete related ``refresh_tokens``
    4. Write a structured audit log entry (no PII) for each purged user

Processing is batched (default 100 users per iteration) to avoid long
transactions and excessive memory consumption.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import delete, select, update

from src.broker import broker
from src.database.session import get_session_factory
from src.metrics import GDPR_PURGE_RELATED_RECORDS, GDPR_PURGE_TOTAL
from src.models.admin_user import AdminUserModel
from src.models.otp_code import OtpCodeModel
from src.models.refresh_token import RefreshTokenModel

logger = structlog.get_logger(__name__)

# GDPR grace period before hard-purge (calendar days)
GRACE_PERIOD_DAYS: int = 30

# Maximum users to purge in one task invocation (keeps transaction short)
BATCH_SIZE: int = 100


@broker.task(task_name="purge_deleted_accounts", queue="cleanup")
async def purge_deleted_accounts() -> dict:
    """Find and permanently purge PII for accounts deleted over 30 days ago.

    Returns:
        dict with ``purged_count``, ``otp_deleted``, ``tokens_deleted``,
        and ``purged_user_ids`` (list of UUID strings) for audit.
    """
    factory = get_session_factory()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=GRACE_PERIOD_DAYS)

    total_purged = 0
    total_otp_deleted = 0
    total_tokens_deleted = 0
    purged_user_ids: list[str] = []

    async with factory() as session:
        # ------------------------------------------------------------------
        # 1. Find candidates: soft-deleted before cutoff AND not yet purged
        #    (email IS NOT NULL serves as "not yet anonymised" guard)
        # ------------------------------------------------------------------
        candidates_stmt = (
            select(AdminUserModel.id)
            .where(
                AdminUserModel.deleted_at.is_not(None),
                AdminUserModel.deleted_at < cutoff,
                AdminUserModel.is_active.is_(False),
                AdminUserModel.email.is_not(None),
            )
            .limit(BATCH_SIZE)
        )
        result = await session.execute(candidates_stmt)
        user_ids: list[UUID] = [row[0] for row in result.all()]

        if not user_ids:
            logger.info("gdpr_purge_no_candidates")
            return {
                "purged_count": 0,
                "otp_deleted": 0,
                "tokens_deleted": 0,
                "purged_user_ids": [],
            }

        logger.info("gdpr_purge_started", candidate_count=len(user_ids))

        # ------------------------------------------------------------------
        # 2. Delete related OTP codes
        # ------------------------------------------------------------------
        otp_stmt = delete(OtpCodeModel).where(OtpCodeModel.user_id.in_(user_ids))
        otp_result = await session.execute(otp_stmt)
        total_otp_deleted = otp_result.rowcount or 0  # type: ignore[union-attr]

        # ------------------------------------------------------------------
        # 3. Delete related refresh tokens
        # ------------------------------------------------------------------
        token_stmt = delete(RefreshTokenModel).where(RefreshTokenModel.user_id.in_(user_ids))
        token_result = await session.execute(token_stmt)
        total_tokens_deleted = token_result.rowcount or 0  # type: ignore[union-attr]

        # ------------------------------------------------------------------
        # 4. Anonymise the user records (PII removal)
        #    login  -> "deleted_<original_uuid>"  (preserves FK references)
        #    email  -> NULL
        #    password_hash -> NULL
        #    telegram_id   -> NULL
        # ------------------------------------------------------------------
        for user_id in user_ids:
            anonymised_login = f"deleted_{user_id}"
            anon_stmt = (
                update(AdminUserModel)
                .where(AdminUserModel.id == user_id)
                .values(
                    login=anonymised_login,
                    email=None,
                    password_hash=None,
                    telegram_id=None,
                )
            )
            await session.execute(anon_stmt)

            purged_user_ids.append(str(user_id))

            logger.info(
                "gdpr_account_purged",
                user_id=str(user_id),
                anonymised_login=anonymised_login,
            )

        total_purged = len(user_ids)

        await session.commit()

    # Emit Prometheus metrics after successful commit
    GDPR_PURGE_TOTAL.inc(total_purged)
    GDPR_PURGE_RELATED_RECORDS.labels(record_type="otp_codes").inc(total_otp_deleted)
    GDPR_PURGE_RELATED_RECORDS.labels(record_type="refresh_tokens").inc(total_tokens_deleted)

    logger.info(
        "gdpr_purge_complete",
        purged_count=total_purged,
        otp_deleted=total_otp_deleted,
        tokens_deleted=total_tokens_deleted,
    )

    return {
        "purged_count": total_purged,
        "otp_deleted": total_otp_deleted,
        "tokens_deleted": total_tokens_deleted,
        "purged_user_ids": purged_user_ids,
    }
