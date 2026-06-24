from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import asyncpg
import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.events.outbox import EventOutboxService
from src.application.use_cases.payments.payment_completed_earnings import (
    PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
    PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS,
    RunPaymentCompletedEarningOutboxUseCase,
)
from src.domain.enums import OutboxPublicationStatus
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.models.outbox_consumer_receipt_model import OutboxConsumerReceiptModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.models.partner_model import PartnerEarningModel

pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
CONTRACT_REVISION = "20260621_partner_comm_contracts"
PREVIOUS_REVISION = "20260621_partner_code_links"


@pytest.mark.asyncio
async def test_partner_commission_contracts_migration_clean_upgrade_downgrade_reupgrade() -> None:
    database_name = f"cvpn_cc_clean_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('partner_commission_contracts')") is not None
            fk_count = await conn.fetchval(
                """
                select count(*)
                from pg_constraint
                where confrelid = 'partner_commission_contracts'::regclass
                """
            )
            assert fk_count == 5
            amount_scales = {
                row["column_name"]: row["numeric_scale"]
                for row in await conn.fetch(
                    """
                    select column_name, numeric_scale
                    from information_schema.columns
                    where table_name = 'earning_events'
                      and column_name = any($1::text[])
                    """,
                    ["commission_base_amount", "markup_amount", "commission_amount", "total_amount"],
                )
            }
            assert amount_scales == {
                "commission_base_amount": 8,
                "markup_amount": 8,
                "commission_amount": 8,
                "total_amount": 8,
            }
            earning_component_default = await conn.fetchval(
                """
                select column_default
                from information_schema.columns
                where table_name = 'earning_events'
                  and column_name = 'earning_component'
                """
            )
            assert earning_component_default is not None
            earning_unique_indexes = {
                row["indexname"]
                for row in await conn.fetch(
                    """
                    select indexname
                    from pg_indexes
                    where tablename = 'earning_events'
                      and indexname = any($1::text[])
                    """,
                    [
                        "uq_earning_events_payment_account_component",
                        "uq_earning_events_payment_user_component",
                    ],
                )
            }
            assert earning_unique_indexes == {
                "uq_earning_events_payment_account_component",
                "uq_earning_events_payment_user_component",
            }
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('partner_commission_contracts')") is None
            assert (
                await conn.fetchval(
                    """
                    select count(*)
                    from information_schema.columns
                    where table_name = 'earning_events'
                      and column_name = 'earning_component'
                    """
                )
                == 0
            )
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('partner_commission_contracts')") is not None
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_partner_commission_contracts_migration_backfills_existing_rows_and_snapshots() -> None:
    database_name = f"cvpn_cc_pop_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await _insert_existing_partner_commission_fixture(conn)
            await _insert_pending_unconsumed_capture_session_fixture(conn)
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert (
                await conn.fetchval(
                    """
                    select is_nullable
                    from information_schema.columns
                    where table_name = 'partner_codes'
                      and column_name = 'public_slug'
                    """
                )
                == "NO"
            )
            public_link = await conn.fetchrow(
                """
                select public_slug, public_token_hash
                from partner_codes
                where id = '10000000-0000-0000-0000-000000000005'
                """
            )
            assert public_link is not None
            assert public_link["public_slug"].startswith("px_")
            assert (
                public_link["public_token_hash"]
                == hashlib.sha256(public_link["public_slug"].encode("utf-8")).hexdigest()
            )
            pending_capture = await conn.fetchrow(
                """
                select status,
                       session_token_hash,
                       transfer_token_hash,
                       consumed_transfer_token_hash,
                       transfer_consumed_at,
                       commission_contract_id,
                       destination_url
                from partner_attribution_sessions
                where id = '10000000-0000-0000-0000-000000000011'
                """
            )
            assert pending_capture is not None
            assert pending_capture["status"] == "pending"
            assert pending_capture["session_token_hash"] is None
            assert pending_capture["transfer_token_hash"] == "pending-transfer-hash"
            assert pending_capture["consumed_transfer_token_hash"] is None
            assert pending_capture["transfer_consumed_at"] is None
            assert pending_capture["commission_contract_id"] is not None
            assert "pat=" not in pending_capture["destination_url"]
            assert "pending-transfer-token" not in pending_capture["destination_url"]
            contract_id_before = await conn.fetchval(
                """
                select commission_contract_id
                from partner_codes
                where id = '10000000-0000-0000-0000-000000000005'
                """
            )
            assert contract_id_before is not None
            terms = await conn.fetchrow(
                """
                select markup_pct::text as markup_pct,
                       commission_pct::text as commission_pct,
                       payout_hold_days,
                       terms_snapshot->>'snapshot_complete' as snapshot_complete,
                       terms_snapshot->>'contract_version' as contract_version
                from partner_commission_contracts
                where id = $1
                """,
                contract_id_before,
            )
            assert terms is not None
            assert terms["markup_pct"] == "12.3400"
            assert terms["commission_pct"] == "17.5000"
            assert terms["payout_hold_days"] == 9
            assert terms["snapshot_complete"] == "true"
            assert terms["contract_version"] == "7"
            order_snapshot = await conn.fetchrow(
                """
                select (policy_snapshot::jsonb #>>
                            '{commercial_policy_snapshot,commission_contract_snapshot,markup_pct}')::numeric
                            as markup_pct,
                       policy_snapshot::jsonb #>>
                            '{commercial_policy_snapshot,commission_contract_snapshot,snapshot_complete}'
                            as snapshot_complete,
                       policy_snapshot::jsonb #>>
                            '{commercial_policy_snapshot,commission_contract_snapshot,missing_terms,0}'
                            as missing_term,
                       (policy_snapshot::jsonb #>>
                            '{commercial_policy_snapshot,commission_contract_snapshot,inferred_from_current_config}')
                            ::boolean as inferred_from_current_config
                from order_attribution_results
                where id = '10000000-0000-0000-0000-000000000009'
                """
            )
            earning_snapshot = await conn.fetchrow(
                """
                select (calculation_snapshot::jsonb #>>
                            '{commission_contract_snapshot,commission_pct}')::numeric
                            as commission_pct,
                       calculation_snapshot::jsonb #>>
                            '{commission_contract_snapshot,snapshot_complete}' as snapshot_complete,
                       calculation_snapshot::jsonb #>>
                            '{commission_contract_snapshot,missing_terms,0}' as missing_term,
                       (calculation_snapshot::jsonb #>>
                            '{commission_contract_snapshot,inferred_from_current_config}')::boolean
                            as inferred_from_current_config
                from earning_events
                where id = '10000000-0000-0000-0000-000000000010'
                """
            )
            assert order_snapshot is not None
            assert earning_snapshot is not None
            assert order_snapshot["markup_pct"] == Decimal("12.34")
            assert order_snapshot["snapshot_complete"] == "false"
            assert order_snapshot["missing_term"] == "historical_commission_snapshot"
            assert order_snapshot["inferred_from_current_config"] is True
            assert earning_snapshot["commission_pct"] == Decimal("17.5")
            assert earning_snapshot["snapshot_complete"] == "false"
            assert earning_snapshot["missing_term"] == "historical_commission_snapshot"
            assert earning_snapshot["inferred_from_current_config"] is True
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                await conn.execute(
                    """
                    update partner_codes
                    set commission_contract_id = '22222222-2222-2222-2222-222222222222'
                    where id = '10000000-0000-0000-0000-000000000005'
                    """
                )
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('partner_commission_contracts')") is None
            assert (
                await conn.fetchval(
                    """
                    select is_nullable
                    from information_schema.columns
                    where table_name = 'partner_codes'
                      and column_name = 'public_slug'
                    """
                )
                == "YES"
            )
            assert (
                await conn.fetchval(
                    """
                    select commission_contract_id is not null
                    from partner_codes
                    where id = '10000000-0000-0000-0000-000000000005'
                    """
                )
                is True
            )
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            contract_id_after = await conn.fetchval(
                """
                select commission_contract_id
                from partner_codes
                where id = '10000000-0000-0000-0000-000000000005'
                """
            )
            assert contract_id_after == contract_id_before
            assert (
                await conn.fetchval(
                    """
                    select is_nullable
                    from information_schema.columns
                    where table_name = 'partner_codes'
                      and column_name = 'public_slug'
                    """
                )
                == "NO"
            )
            assert (
                await conn.fetchval(
                    """
                    select session_token_hash is null
                       and transfer_token_hash = 'pending-transfer-hash'
                       and consumed_transfer_token_hash is null
                       and transfer_consumed_at is null
                    from partner_attribution_sessions
                    where id = '10000000-0000-0000-0000-000000000011'
                    """
                )
                is True
            )
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_partner_commission_contracts_migration_blocks_downgrade_with_live_contract_history() -> None:
    database_name = f"cvpn_cc_hist_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await _insert_existing_partner_commission_fixture(conn)
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        rotated_contract_id = uuid.uuid4()
        try:
            await conn.execute(
                """
                insert into partner_commission_contracts (
                    id, partner_code_id, owner_type, contract_status, commission_model,
                    commission_pct, markup_pct, payout_hold_days, currency_code,
                    currency_policy, rounding_mode, renewal_policy, refund_policy,
                    terms_snapshot, source, version, effective_from
                )
                values (
                    $1,
                    '10000000-0000-0000-0000-000000000005',
                    'affiliate',
                    'active',
                    'base_plus_markup',
                    19.2500,
                    13.5000,
                    9,
                    'USD',
                    '{"minor_unit": 2}'::jsonb,
                    'ROUND_HALF_UP',
                    '{"eligible": true}'::jsonb,
                    '{"clawback": "manual_review"}'::jsonb,
                    '{"snapshot_complete": true, "source": "live_rotation_test"}'::jsonb,
                    'live_rotation_test',
                    8,
                    now()
                )
                """,
                rotated_contract_id,
            )
            await conn.execute(
                """
                update partner_codes
                set commission_contract_id = $1
                where id = '10000000-0000-0000-0000-000000000005'
                """,
                rotated_contract_id,
            )
        finally:
            await conn.close()

        downgrade = await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION, check=False)
        assert downgrade.returncode != 0
        assert "Cannot downgrade 20260621_partner_comm_contracts" in downgrade.stderr
        assert "multiple commission contracts exist for the same partner code" in downgrade.stderr

        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('partner_commission_contracts')") is not None
            contract_count = await conn.fetchval(
                """
                select count(*)
                from partner_commission_contracts
                where partner_code_id = '10000000-0000-0000-0000-000000000005'
                """
            )
            assert contract_count == 2
            assert (
                await conn.fetchval(
                    """
                    select commission_contract_id
                    from partner_codes
                    where id = '10000000-0000-0000-0000-000000000005'
                    """
                )
                == rotated_contract_id
            )
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_partner_commission_contracts_migration_blocks_downgrade_with_precision_loss() -> None:
    database_name = f"cvpn_cc_prec_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await _insert_existing_partner_commission_fixture(conn)
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await conn.execute(
                """
                update earning_events
                set commission_base_amount = 100.12345678,
                    markup_amount = 12.34567891,
                    commission_amount = 17.55555555,
                    total_amount = 29.90123456,
                    commission_pct = 17.5555
                where id = '10000000-0000-0000-0000-000000000010'
                """
            )
        finally:
            await conn.close()

        downgrade = await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION, check=False)
        assert downgrade.returncode != 0
        assert "Cannot downgrade 20260621_partner_comm_contracts" in downgrade.stderr
        assert "previous numeric precision" in downgrade.stderr

        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('partner_commission_contracts')") is not None
            amount = await conn.fetchval(
                """
                select commission_amount
                from earning_events
                where id = '10000000-0000-0000-0000-000000000010'
                """
            )
            assert amount == Decimal("17.55555555")
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_outbox_deterministic_event_key_is_idempotent_under_concurrent_writers() -> None:
    database_name = f"cvpn_outbox_race_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        event_key = f"settlement-snapshot-incomplete:{uuid.uuid4()}"
        aggregate_id = str(uuid.uuid4())

        async def append_once() -> uuid.UUID:
            async with maker() as session:
                event = await EventOutboxService(session).append_event(
                    event_name="settlement.earning.snapshot_incomplete",
                    aggregate_type="payment",
                    aggregate_id=aggregate_id,
                    partition_key=aggregate_id,
                    event_payload={
                        "payment_id": aggregate_id,
                        "missing_terms": ["commission_contract_snapshot"],
                    },
                    event_key=event_key,
                )
                await session.commit()
                return event.id

        first_id, second_id = await asyncio.gather(append_once(), append_once())

        assert first_id == second_id
        async with maker() as session:
            event_count = await session.scalar(
                select(func.count()).select_from(OutboxEventModel).where(OutboxEventModel.event_key == event_key)
            )
            publication_count = await session.scalar(
                select(func.count())
                .select_from(OutboxPublicationModel)
                .where(OutboxPublicationModel.outbox_event_id == first_id)
            )
        assert event_count == 1
        assert publication_count == 2
        async with maker() as session:
            event = await EventOutboxService(session).append_event(
                event_name="settlement.earning.snapshot_incomplete",
                aggregate_type="payment",
                aggregate_id=aggregate_id,
                partition_key=aggregate_id,
                consumer_keys=(PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,),
                event_payload={
                    "payment_id": aggregate_id,
                    "missing_terms": ["commission_contract_snapshot"],
                },
                event_key=event_key,
            )
            await session.commit()
            ensured_event_id = event.id

        assert ensured_event_id == first_id
        async with maker() as session:
            ensured_publication_count = await session.scalar(
                select(func.count())
                .select_from(OutboxPublicationModel)
                .where(OutboxPublicationModel.outbox_event_id == first_id)
            )
            partner_worker_publication_count = await session.scalar(
                select(func.count())
                .select_from(OutboxPublicationModel)
                .where(
                    OutboxPublicationModel.outbox_event_id == first_id,
                    OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                )
            )
        assert ensured_publication_count == 3
        assert partner_worker_publication_count == 1
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_payment_completed_partner_earning_policy_failure_retries_without_cash_artifacts() -> None:
    database_name = f"cvpn_payearn_retry_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        payment_id = uuid.uuid4()
        async with maker() as session:
            await EventOutboxService(session).append_event(
                event_name="payment.completed",
                aggregate_type="payment",
                aggregate_id=str(payment_id),
                partition_key=str(uuid.uuid4()),
                consumer_keys=(PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,),
                event_key=f"payment.completed:{payment_id}",
                event_payload={"payment_id": str(payment_id), "payment_status": "completed"},
            )
            await session.commit()

        async with maker() as session:
            runner = RunPaymentCompletedEarningOutboxUseCase(session)
            runner._processor.execute = AsyncMock(side_effect=RuntimeError("policy service unavailable"))  # type: ignore[method-assign]
            report = await runner.execute(limit=10, worker_id="retry-worker")

        assert report["claimed"] == 1
        assert report["succeeded"] == 0
        assert report["retrying"] == 1
        assert report["dead_letter"] == 0
        async with maker() as session:
            publication = (
                (
                    await session.execute(
                        select(OutboxPublicationModel).where(
                            OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER
                        )
                    )
                )
                .scalars()
                .one()
            )
            assert publication.publication_status == OutboxPublicationStatus.FAILED.value
            assert publication.attempts == 1
            assert publication.last_error.startswith("RuntimeError:")
            assert "policy service unavailable" not in publication.last_error
            assert publication.next_attempt_at > publication.created_at
            event_count = await session.scalar(select(func.count()).select_from(EarningEventModel))
            legacy_partner_count = await session.scalar(select(func.count()).select_from(PartnerEarningModel))
            reward_count = await session.scalar(select(func.count()).select_from(GrowthRewardAllocationModel))
        assert event_count == 0
        assert legacy_partner_count == 0
        assert reward_count == 0
        assert report["failures"][0]["retry_after_seconds"] == PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS[0]
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_payment_completed_partner_earning_concurrent_workers_claim_publication_once() -> None:
    database_name = f"cvpn_payearn_claim_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        payment_id = uuid.uuid4()
        async with maker() as session:
            await EventOutboxService(session).append_event(
                event_name="payment.completed",
                aggregate_type="payment",
                aggregate_id=str(payment_id),
                partition_key=str(uuid.uuid4()),
                consumer_keys=(PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,),
                event_key=f"payment.completed:{payment_id}",
                event_payload={"payment_id": str(payment_id), "payment_status": "completed"},
            )
            await session.commit()

        async def run_worker(worker_id: str) -> dict:
            async with maker() as session:
                runner = RunPaymentCompletedEarningOutboxUseCase(session)
                runner._processor.execute = AsyncMock(  # type: ignore[method-assign]
                    return_value={
                        "status": "processed",
                        "payment_id": str(payment_id),
                        "cash_payout_created": True,
                        "settlement_earning_event_id": str(uuid.uuid4()),
                    }
                )
                return await runner.execute(limit=10, worker_id=worker_id)

        first_report, second_report = await asyncio.gather(run_worker("claim-worker-1"), run_worker("claim-worker-2"))

        assert first_report["claimed"] + second_report["claimed"] == 1
        assert first_report["succeeded"] + second_report["succeeded"] == 1
        async with maker() as session:
            publication_count = await session.scalar(
                select(func.count())
                .select_from(OutboxPublicationModel)
                .where(OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER)
            )
            published_count = await session.scalar(
                select(func.count())
                .select_from(OutboxPublicationModel)
                .where(
                    OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                    OutboxPublicationModel.publication_status == OutboxPublicationStatus.PUBLISHED.value,
                )
            )
            receipt_count = await session.scalar(
                select(func.count())
                .select_from(OutboxConsumerReceiptModel)
                .where(
                    OutboxConsumerReceiptModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                    OutboxConsumerReceiptModel.event_key == f"payment.completed:{payment_id}",
                )
            )
        assert publication_count == 1
        assert published_count == 1
        assert receipt_count == 1
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_payment_completed_partner_earning_retry_exhaustion_dead_letters_with_reconciliation_event() -> None:
    database_name = f"cvpn_payearn_dlq_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        payment_id = uuid.uuid4()
        raw_provider_marker = "raw-provider-invoice-987654321"
        async with maker() as session:
            await EventOutboxService(session).append_event(
                event_name="payment.completed",
                aggregate_type="payment",
                aggregate_id=str(payment_id),
                partition_key=str(uuid.uuid4()),
                consumer_keys=(PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,),
                event_key=f"payment.completed:{payment_id}",
                event_payload={
                    "payment_id": str(payment_id),
                    "order_id": str(uuid.uuid4()),
                    "payment_status": "completed",
                },
            )
            await session.commit()

        final_report = None
        for attempt_index in range(len(PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS) + 2):
            async with maker() as session:
                runner = RunPaymentCompletedEarningOutboxUseCase(session)
                runner._processor.execute = AsyncMock(  # type: ignore[method-assign]
                    side_effect=RuntimeError(f"policy service unavailable for {raw_provider_marker}")
                )
                final_report = await runner.execute(limit=10, worker_id=f"dlq-worker-{attempt_index}")

            if final_report["dead_letter"]:
                break

            async with maker() as session:
                publication = (
                    (
                        await session.execute(
                            select(OutboxPublicationModel).where(
                                OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER
                            )
                        )
                    )
                    .scalars()
                    .one()
                )
                publication.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
                await session.commit()

        assert final_report is not None
        assert final_report["claimed"] == 1
        assert final_report["succeeded"] == 0
        assert final_report["retrying"] == 0
        assert final_report["dead_letter"] == 1
        assert final_report["reconciliation_required"] == 1
        assert final_report["alerts"] == 1
        async with maker() as session:
            publication = (
                (
                    await session.execute(
                        select(OutboxPublicationModel).where(
                            OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER
                        )
                    )
                )
                .scalars()
                .one()
            )
            assert publication.publication_status == OutboxPublicationStatus.DEAD_LETTER.value
            assert publication.attempts == len(PAYMENT_COMPLETED_RETRY_DELAYS_SECONDS) + 1
            assert raw_provider_marker not in (publication.last_error or "")
            reconciliation_event = (
                (
                    await session.execute(
                        select(OutboxEventModel).where(
                            OutboxEventModel.event_name == "payment.completed.partner_earning.reconciliation_required"
                        )
                    )
                )
                .scalars()
                .one()
            )
            serialized_payload = json.dumps(reconciliation_event.event_payload, sort_keys=True)
            assert reconciliation_event.event_payload["payment_id"] == str(payment_id)
            assert reconciliation_event.event_payload["outbox_publication_id"] == str(publication.id)
            assert reconciliation_event.event_payload["manual_reconciliation_required"] is True
            assert reconciliation_event.event_payload["alert_required"] is True
            assert reconciliation_event.event_payload["error_type"] == "RuntimeError"
            assert "error_fingerprint" in reconciliation_event.event_payload
            assert raw_provider_marker not in serialized_payload
            event_again = await EventOutboxService(session).append_event(
                event_name="payment.completed.partner_earning.reconciliation_required",
                aggregate_type="outbox_publication",
                aggregate_id=str(publication.id),
                partition_key=str(payment_id),
                event_key=f"payment.completed.partner_earning.reconciliation_required:{publication.id}",
                event_payload=dict(reconciliation_event.event_payload),
            )
            await session.commit()
            assert event_again.id == reconciliation_event.id
            reconciliation_count = await session.scalar(
                select(func.count())
                .select_from(OutboxEventModel)
                .where(OutboxEventModel.event_name == "payment.completed.partner_earning.reconciliation_required")
            )
            assert reconciliation_count == 1
            event_count = await session.scalar(select(func.count()).select_from(EarningEventModel))
            legacy_partner_count = await session.scalar(select(func.count()).select_from(PartnerEarningModel))
            reward_count = await session.scalar(select(func.count()).select_from(GrowthRewardAllocationModel))
        assert event_count == 0
        assert legacy_partner_count == 0
        assert reward_count == 0
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


async def _insert_existing_partner_commission_fixture(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        insert into system_config (key, value, description, updated_at)
        values
          ('partner.tiers',
           '{"tiers":[{"min_clients":0,"commission_pct":17.50},{"min_clients":10,"commission_pct":25.00}]}',
           'ac13 migration test',
           now()),
          ('affiliate.payout_hold_days', '{"days":9}', 'ac13 migration test', now())
        on conflict (key) do update set value = excluded.value, updated_at = now();

        insert into auth_realms (
            id, realm_key, realm_type, display_name, audience, cookie_namespace, status, is_default
        )
        values (
            '10000000-0000-0000-0000-000000000001',
            'ac13-customer',
            'customer',
            'AC13 Customer',
            'customer',
            'ac13',
            'active',
            true
        );
        insert into brands (id, brand_key, display_name, status)
        values ('10000000-0000-0000-0000-000000000002', 'ac13-brand', 'AC13 Brand', 'active');
        insert into storefronts (id, storefront_key, brand_id, display_name, host, auth_realm_id, status)
        values (
            '10000000-0000-0000-0000-000000000003',
            'ac13-store',
            '10000000-0000-0000-0000-000000000002',
            'AC13 Store',
            'ac13.example.test',
            '10000000-0000-0000-0000-000000000001',
            'active'
        );
        insert into mobile_users (
            id, email, password_hash, is_active, status, is_partner, totp_enabled, notification_prefs, public_uid
        )
        values (
            '10000000-0000-0000-0000-000000000004',
            'ac13-customer@example.test',
            'hash',
            true,
            'active',
            false,
            false,
            '{}',
            130001
        );
        insert into partner_codes (id, code, code_normalized, markup_pct, is_active, owner_type, version)
        values ('10000000-0000-0000-0000-000000000005', 'AC13POP', 'AC13POP', 12.34, true, 'affiliate', 7);
        insert into quote_sessions (
            id, user_id, auth_realm_id, storefront_id, request_snapshot, quote_snapshot, context_snapshot, expires_at
        )
        values (
            '10000000-0000-0000-0000-000000000006',
            '10000000-0000-0000-0000-000000000004',
            '10000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000003',
            '{}',
            '{}',
            '{}',
            now() + interval '1 day'
        );
        insert into checkout_sessions (
            id, quote_session_id, user_id, auth_realm_id, storefront_id, idempotency_key,
            request_snapshot, checkout_snapshot, context_snapshot, expires_at
        )
        values (
            '10000000-0000-0000-0000-000000000007',
            '10000000-0000-0000-0000-000000000006',
            '10000000-0000-0000-0000-000000000004',
            '10000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000003',
            'ac13-checkout',
            '{}',
            '{}',
            '{}',
            now() + interval '1 day'
        );
        insert into orders (
            id, checkout_session_id, quote_session_id, user_id, auth_realm_id, storefront_id,
            base_price, displayed_price, gateway_amount, commission_base_amount,
            merchant_snapshot, pricing_snapshot, policy_snapshot, entitlements_snapshot
        )
        values (
            '10000000-0000-0000-0000-000000000008',
            '10000000-0000-0000-0000-000000000007',
            '10000000-0000-0000-0000-000000000006',
            '10000000-0000-0000-0000-000000000004',
            '10000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000003',
            100.00,
            112.34,
            112.34,
            100.00,
            '{}',
            '{}',
            '{}',
            '{}'
        );
        insert into order_attribution_results (
            id, order_id, user_id, auth_realm_id, storefront_id, owner_type, partner_code_id,
            rule_path, evidence_snapshot, explainability_snapshot, policy_snapshot, resolved_at, created_at
        )
        values (
            '10000000-0000-0000-0000-000000000009',
            '10000000-0000-0000-0000-000000000008',
            '10000000-0000-0000-0000-000000000004',
            '10000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000003',
            'affiliate',
            '10000000-0000-0000-0000-000000000005',
            '[]',
            '{}',
            '{}',
            '{}',
            now(),
            now()
        );
        insert into earning_events (
            id, client_user_id, order_id, order_attribution_result_id, owner_type, partner_code_id,
            commission_base_amount, markup_amount, commission_pct, commission_amount, total_amount,
            currency_code, source_snapshot, calculation_snapshot, created_at, updated_at
        )
        values (
            '10000000-0000-0000-0000-000000000010',
            '10000000-0000-0000-0000-000000000004',
            '10000000-0000-0000-0000-000000000008',
            '10000000-0000-0000-0000-000000000009',
            'affiliate',
            '10000000-0000-0000-0000-000000000005',
            100.00,
            12.34,
            17.50,
            17.50,
            29.84,
            'USD',
            '{}',
            '{}',
            now(),
            now()
        );
        """
    )


async def _insert_pending_unconsumed_capture_session_fixture(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        insert into partner_attribution_sessions (
            id,
            session_token_hash,
            transfer_token_hash,
            transfer_expires_at,
            transfer_consumed_at,
            partner_code_id,
            partner_account_id,
            auth_realm_id,
            storefront_id,
            status,
            owner_type,
            attribution_model,
            source_host,
            source_path,
            destination_path,
            locale,
            sale_channel,
            sub_ids,
            browser_key_hash,
            capture_idempotency_key_hash,
            destination_url,
            campaign_params,
            evidence_payload,
            policy_snapshot,
            expires_at,
            first_seen_at,
            last_seen_at
        )
        values (
            '10000000-0000-0000-0000-000000000011',
            null,
            'pending-transfer-hash',
            now() + interval '15 minutes',
            null,
            '10000000-0000-0000-0000-000000000005',
            null,
            '10000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000003',
            'pending',
            'affiliate',
            'last_eligible_touch',
            'cyber-vpn.net',
            '/p/ac13',
            '/pricing',
            'ru-RU',
            'content',
            '{}'::json,
            'pending-browser-hash',
            'pending-idempotency-hash',
            'https://cyber-vpn.net/ru-RU/register?pat=pending-transfer-token',
            '{}'::json,
            '{}'::json,
            '{}'::json,
            now() + interval '7 days',
            now(),
            now()
        );
        """
    )


def _database_url(database_name: str) -> str:
    test_url = _test_postgres_url()
    return make_url(test_url).set(database=database_name).render_as_string(hide_password=False)


def _asyncpg_url_for_database(database_name: str) -> str:
    return _database_url(database_name).replace("postgresql+asyncpg://", "postgresql://", 1)


def _asyncpg_admin_url() -> str:
    return _test_postgres_url().replace("postgresql+asyncpg://", "postgresql://", 1)


def _test_postgres_url() -> str:
    url = os.getenv("CYBERVPN_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("CYBERVPN_TEST_POSTGRES_URL is required for PostgreSQL commission migration tests")
    return url


async def _create_database(database_name: str) -> None:
    try:
        conn = await asyncpg.connect(_asyncpg_admin_url())
    except OSError as exc:
        pytest.skip(f"PostgreSQL is unavailable for commission migration tests: {exc}")
    try:
        await conn.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await conn.close()


async def _drop_database(database_name: str) -> None:
    conn = await asyncpg.connect(_asyncpg_admin_url())
    try:
        await conn.execute(
            """
            select pg_terminate_backend(pid)
            from pg_stat_activity
            where datname = $1
              and pid <> pg_backend_pid()
            """,
            database_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        await conn.close()


def _run_alembic(url: str, command: str, revision: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", command, revision],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"alembic {command} {revision} failed with exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result
