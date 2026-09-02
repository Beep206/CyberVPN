from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import asyncpg
import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptService,
    remnawave_create_request_hash,
    remnawave_customer_create_key,
)
from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    _acquire_runtime_mapping_locks,
    persist_runtime_mapped_mobile_identity,
    persist_runtime_mapped_service_identity,
)
from src.application.services.remnawave_identity_retirement import (
    apply_remnawave_owner_identity_retirement,
    assert_remnawave_service_identity_grantable,
    prepare_remnawave_owner_identity_retirement,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel, PartnerAccountModel
from src.infrastructure.database.models.remnawave_upgrade_model import (
    PartnerRemnawaveResourceGrantModel,
    RemnawaveIdentityReconciliationModel,
)
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.presentation.api.v1.remnawave_status.routes import _numeric_identity_cutover_ready
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

PREVIOUS_REVISION = "20260711_plan_code_len"


async def _insert_mapping(
    connection: asyncpg.Connection,
    *,
    subject_id: uuid.UUID,
    numeric_id: int,
    legacy_uuid: uuid.UUID,
) -> None:
    async with connection.transaction():
        await connection.execute(
            """
            insert into remnawave_identity_reconciliations (
                id, subject_type, subject_id, legacy_uuid, numeric_user_id,
                reconciliation_state, evidence, reconciled_at, created_at, updated_at
            ) values ($1, 'mobile_user', $2, $3, $4, 'mapped', '{}'::jsonb, now(), now(), now())
            """,
            uuid.uuid4(),
            subject_id,
            str(legacy_uuid),
            numeric_id,
        )


@pytest.mark.asyncio
async def test_remnawave_mapping_migration_enforces_concurrent_numeric_and_legacy_uniqueness() -> None:
    database_name = f"cvpn_rw_identity_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        first = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        second = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            indexes = {
                row["indexname"]
                for row in await first.fetch(
                    """
                    select indexname from pg_indexes
                    where tablename = 'remnawave_identity_reconciliations'
                    """
                )
            }
            assert "uq_remnawave_reconciliation_mapped_numeric" in indexes
            assert "uq_remnawave_reconciliation_mapped_legacy" in indexes

            shared_legacy = uuid.uuid4()
            legacy_results = await asyncio.gather(
                _insert_mapping(first, subject_id=uuid.uuid4(), numeric_id=101, legacy_uuid=shared_legacy),
                _insert_mapping(second, subject_id=uuid.uuid4(), numeric_id=102, legacy_uuid=shared_legacy),
                return_exceptions=True,
            )
            assert sum(isinstance(result, asyncpg.UniqueViolationError) for result in legacy_results) == 1

            shared_numeric = 201
            numeric_results = await asyncio.gather(
                _insert_mapping(first, subject_id=uuid.uuid4(), numeric_id=shared_numeric, legacy_uuid=uuid.uuid4()),
                _insert_mapping(second, subject_id=uuid.uuid4(), numeric_id=shared_numeric, legacy_uuid=uuid.uuid4()),
                return_exceptions=True,
            )
            assert sum(isinstance(result, asyncpg.UniqueViolationError) for result in numeric_results) == 1
        finally:
            await first.close()
            await second.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        connection = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await connection.fetchval("select to_regclass('remnawave_identity_reconciliations')") is None
        finally:
            await connection.close()
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    finally:
        await _drop_database(database_name)


async def _seed_runtime_pair(
    sessions: async_sessionmaker[AsyncSession],
    *,
    same_owner: bool,
    suffix: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    realm_id = uuid.uuid4()
    mobile_owner_id = uuid.uuid4()
    service_owner_id = mobile_owner_id if same_owner else uuid.uuid4()
    service_identity_id = uuid.uuid4()
    async with sessions() as db:
        db.add(
            AuthRealmModel(
                id=realm_id,
                realm_key=f"identity-{suffix}",
                realm_type="customer",
                display_name=f"Identity {suffix}",
                audience=f"identity-{suffix}",
                cookie_namespace=f"id-{suffix}",
            )
        )
        db.add_all(
            [
                MobileUserModel(
                    id=mobile_owner_id,
                    public_uid=int(uuid.uuid4().int % 8_000_000_000_000_000_000),
                    auth_realm_id=realm_id,
                    email=f"mobile-{suffix}@example.test",
                    password_hash="not-a-real-password-hash",
                ),
                ServiceIdentityModel(
                    id=service_identity_id,
                    service_key=f"remnawave-{suffix}",
                    customer_account_id=service_owner_id,
                    auth_realm_id=realm_id,
                    provider_name="remnawave",
                    identity_scope="account",
                    identity_status="active",
                ),
            ]
        )
        if not same_owner:
            db.add(
                MobileUserModel(
                    id=service_owner_id,
                    public_uid=int(uuid.uuid4().int % 8_000_000_000_000_000_000),
                    auth_realm_id=realm_id,
                    email=f"service-owner-{suffix}@example.test",
                    password_hash="not-a-real-password-hash",
                )
            )
        await db.commit()
    return mobile_owner_id, service_identity_id


async def _concurrent_runtime_pair(
    sessions: async_sessionmaker[AsyncSession],
    *,
    mobile_owner_id: uuid.UUID,
    service_identity_id: uuid.UUID,
    numeric_ids: tuple[int, int],
    legacy_uuids: tuple[uuid.UUID, uuid.UUID],
) -> list[object]:
    barrier = asyncio.Barrier(2)

    async def persist_mobile() -> object:
        async with sessions() as db:
            customer = await db.get(MobileUserModel, mobile_owner_id)
            assert customer is not None
            await barrier.wait()
            result = await persist_runtime_mapped_mobile_identity(
                db,
                customer=customer,
                remnawave_user_id=numeric_ids[0],
                remnawave_uuid=legacy_uuids[0],
                source="postgres_concurrency_mobile",
            )
            await db.commit()
            return result

    async def persist_service() -> object:
        async with sessions() as db:
            identity = await db.get(ServiceIdentityModel, service_identity_id)
            assert identity is not None
            await barrier.wait()
            result = await persist_runtime_mapped_service_identity(
                db,
                service_identity=identity,
                remnawave_user_id=numeric_ids[1],
                remnawave_uuid=legacy_uuids[1],
                source="postgres_concurrency_service",
            )
            await db.commit()
            return result

    return list(await asyncio.gather(persist_mobile(), persist_service(), return_exceptions=True))


def _mapping_row(
    *,
    subject_type: str,
    subject_id: uuid.UUID,
    numeric_id: int,
    legacy_uuid: str | None,
) -> RemnawaveIdentityReconciliationModel:
    now = datetime.now(UTC)
    return RemnawaveIdentityReconciliationModel(
        id=uuid.uuid4(),
        subject_type=subject_type,
        subject_id=subject_id,
        legacy_uuid=legacy_uuid,
        numeric_user_id=numeric_id,
        reconciliation_state="mapped",
        evidence={"source": "postgres_readiness_test"},
        reconciled_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_runtime_cross_type_owner_guard_is_serialized_on_postgres() -> None:
    database_name = f"cvpn_rw_owner_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    engine = create_async_engine(url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        first_session = sessions()
        second_session = sessions()
        try:
            await first_session.begin()
            await second_session.begin()
            await _acquire_runtime_mapping_locks(
                first_session,
                subject_type="mobile_user",
                subject_id=uuid.uuid4(),
                numeric_user_id=201,
                legacy_uuid=uuid.uuid4(),
            )
            await asyncio.wait_for(
                _acquire_runtime_mapping_locks(
                    second_session,
                    subject_type="service_identity",
                    subject_id=uuid.uuid4(),
                    numeric_user_id=202,
                    legacy_uuid=uuid.uuid4(),
                ),
                timeout=2,
            )
        finally:
            await second_session.rollback()
            await first_session.rollback()
            await second_session.close()
            await first_session.close()

        same_mobile_id, same_service_id = await _seed_runtime_pair(
            sessions,
            same_owner=True,
            suffix=f"same-{uuid.uuid4().hex[:8]}",
        )
        shared_legacy = uuid.uuid4()
        same_owner_results = await _concurrent_runtime_pair(
            sessions,
            mobile_owner_id=same_mobile_id,
            service_identity_id=same_service_id,
            numeric_ids=(301, 301),
            legacy_uuids=(shared_legacy, shared_legacy),
        )
        assert not any(isinstance(result, BaseException) for result in same_owner_results)
        async with sessions() as db:
            same_owner_ledger_count = await db.scalar(
                select(func.count())
                .select_from(RemnawaveIdentityReconciliationModel)
                .where(RemnawaveIdentityReconciliationModel.subject_id.in_({same_mobile_id, same_service_id}))
            )
        assert same_owner_ledger_count == 2
        async with sessions() as db:
            assert await _numeric_identity_cutover_ready(db) is True

        numeric_mobile_id, numeric_service_id = await _seed_runtime_pair(
            sessions,
            same_owner=False,
            suffix=f"numeric-{uuid.uuid4().hex[:8]}",
        )
        numeric_results = await _concurrent_runtime_pair(
            sessions,
            mobile_owner_id=numeric_mobile_id,
            service_identity_id=numeric_service_id,
            numeric_ids=(401, 401),
            legacy_uuids=(uuid.uuid4(), uuid.uuid4()),
        )
        assert sum(isinstance(result, RemnawaveIdentityAccessConflict) for result in numeric_results) == 1

        legacy_mobile_id, legacy_service_id = await _seed_runtime_pair(
            sessions,
            same_owner=False,
            suffix=f"legacy-{uuid.uuid4().hex[:8]}",
        )
        colliding_legacy = uuid.uuid4()
        legacy_results = await _concurrent_runtime_pair(
            sessions,
            mobile_owner_id=legacy_mobile_id,
            service_identity_id=legacy_service_id,
            numeric_ids=(501, 502),
            legacy_uuids=(colliding_legacy, colliding_legacy),
        )
        assert sum(isinstance(result, RemnawaveIdentityAccessConflict) for result in legacy_results) == 1

        async with sessions() as db:
            different_owner_ledger_count = await db.scalar(
                select(func.count())
                .select_from(RemnawaveIdentityReconciliationModel)
                .where(
                    RemnawaveIdentityReconciliationModel.subject_id.in_(
                        {
                            numeric_mobile_id,
                            numeric_service_id,
                            legacy_mobile_id,
                            legacy_service_id,
                        }
                    )
                )
            )
        assert different_owner_ledger_count == 2
    finally:
        await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_numeric_cutover_readiness_fails_closed_on_postgres() -> None:
    database_name = f"cvpn_rw_ready_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    engine = create_async_engine(url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        mobile_id, service_id = await _seed_runtime_pair(
            sessions,
            same_owner=True,
            suffix=f"ready-{uuid.uuid4().hex[:8]}",
        )
        async with sessions() as db:
            mobile = await db.get(MobileUserModel, mobile_id)
            service = await db.get(ServiceIdentityModel, service_id)
            assert mobile is not None
            assert service is not None

            mobile.remnawave_user_id = 601
            mobile.remnawave_uuid = None
            db.add(
                _mapping_row(
                    subject_type="mobile_user",
                    subject_id=mobile.id,
                    numeric_id=601,
                    legacy_uuid=None,
                )
            )
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is False

            await db.execute(delete(RemnawaveIdentityReconciliationModel))
            mobile.remnawave_uuid = "invalid-rollback-id"
            db.add(
                _mapping_row(
                    subject_type="mobile_user",
                    subject_id=mobile.id,
                    numeric_id=601,
                    legacy_uuid="invalid-rollback-id",
                )
            )
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is False

            await db.execute(delete(RemnawaveIdentityReconciliationModel))
            inactive_legacy = uuid.uuid4()
            mobile.remnawave_uuid = str(inactive_legacy)
            mobile.is_active = False
            mobile.status = "disabled"
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is False

            mobile.remnawave_user_id = None
            mobile.remnawave_uuid = None
            orphan_legacy = uuid.uuid4()
            db.add(
                _mapping_row(
                    subject_type="mobile_user",
                    subject_id=uuid.uuid4(),
                    numeric_id=602,
                    legacy_uuid=str(orphan_legacy),
                )
            )
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is False

            await db.execute(delete(RemnawaveIdentityReconciliationModel))
            exact_legacy = uuid.uuid4()
            mobile.remnawave_user_id = 603
            mobile.remnawave_uuid = str(exact_legacy).upper()
            db.add(
                _mapping_row(
                    subject_type="mobile_user",
                    subject_id=mobile.id,
                    numeric_id=603,
                    legacy_uuid=str(exact_legacy),
                )
            )
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is True

            await db.execute(delete(RemnawaveIdentityReconciliationModel))
            first_legacy = uuid.uuid4()
            second_legacy = uuid.uuid4()
            mobile.remnawave_user_id = 604
            mobile.remnawave_uuid = str(first_legacy)
            service.provider_numeric_subject_id = 604
            service.provider_subject_ref = str(second_legacy)
            db.add_all(
                [
                    _mapping_row(
                        subject_type="mobile_user",
                        subject_id=mobile.id,
                        numeric_id=604,
                        legacy_uuid=str(first_legacy),
                    ),
                    _mapping_row(
                        subject_type="service_identity",
                        subject_id=service.id,
                        numeric_id=604,
                        legacy_uuid=str(second_legacy),
                    ),
                ]
            )
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is False

            await db.execute(delete(RemnawaveIdentityReconciliationModel))
            shared_legacy = uuid.uuid4()
            mobile.remnawave_user_id = 605
            mobile.remnawave_uuid = str(shared_legacy)
            service.provider_numeric_subject_id = 606
            service.provider_subject_ref = str(shared_legacy)
            db.add_all(
                [
                    _mapping_row(
                        subject_type="mobile_user",
                        subject_id=mobile.id,
                        numeric_id=605,
                        legacy_uuid=str(shared_legacy),
                    ),
                    _mapping_row(
                        subject_type="service_identity",
                        subject_id=service.id,
                        numeric_id=606,
                        legacy_uuid=str(shared_legacy),
                    ),
                ]
            )
            await db.flush()
            assert await _numeric_identity_cutover_ready(db) is False
            await db.rollback()
    finally:
        await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_owner_retirement_removes_every_pair_and_preserves_cutover_readiness_on_postgres() -> None:
    database_name = f"cvpn_rw_retire_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    engine = create_async_engine(url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        mobile_id, alias_service_id = await _seed_runtime_pair(
            sessions,
            same_owner=True,
            suffix=f"retire-{uuid.uuid4().hex[:8]}",
        )
        alias_legacy = uuid.uuid4()
        distinct_legacy = uuid.uuid4()
        distinct_service_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        alias_grant_id = uuid.uuid4()
        node_grant_id = uuid.uuid4()
        async with sessions() as db:
            mobile = await db.get(MobileUserModel, mobile_id)
            alias_service = await db.get(ServiceIdentityModel, alias_service_id)
            assert mobile is not None
            assert alias_service is not None
            mobile.remnawave_user_id = 701
            mobile.remnawave_uuid = str(alias_legacy)
            alias_service.provider_numeric_subject_id = 701
            alias_service.provider_subject_ref = str(alias_legacy)
            distinct_service = ServiceIdentityModel(
                id=distinct_service_id,
                service_key=f"retirement-distinct-{distinct_service_id}",
                customer_account_id=mobile_id,
                auth_realm_id=alias_service.auth_realm_id,
                provider_name="remnawave",
                identity_scope="subscription",
                subscription_key=f"subscription:{distinct_service_id}",
                provider_numeric_subject_id=702,
                provider_subject_ref=str(distinct_legacy),
                identity_status="active",
            )
            admin = AdminUserModel(
                id=admin_id,
                login=f"retire-{admin_id.hex[:12]}",
                email=f"retire-{admin_id.hex[:12]}@example.test",
                auth_realm_id=alias_service.auth_realm_id,
                password_hash="not-a-real-password-hash",
                role="admin",
                is_active=True,
            )
            workspace = PartnerAccountModel(
                id=workspace_id,
                account_key=f"retire-{workspace_id.hex[:12]}",
                display_name="Retirement workspace",
                legacy_owner_user_id=mobile_id,
            )
            db.add_all(
                [
                    distinct_service,
                    admin,
                    workspace,
                    _mapping_row(
                        subject_type="mobile_user",
                        subject_id=mobile_id,
                        numeric_id=701,
                        legacy_uuid=str(alias_legacy),
                    ),
                    _mapping_row(
                        subject_type="service_identity",
                        subject_id=alias_service_id,
                        numeric_id=701,
                        legacy_uuid=str(alias_legacy),
                    ),
                    _mapping_row(
                        subject_type="service_identity",
                        subject_id=distinct_service_id,
                        numeric_id=702,
                        legacy_uuid=str(distinct_legacy),
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    PartnerRemnawaveResourceGrantModel(
                        id=alias_grant_id,
                        workspace_id=workspace_id,
                        resource_type="service_identity",
                        resource_uuid=alias_service_id,
                        permission_keys=["remnawave_read"],
                        granted_by_admin_user_id=admin_id,
                        audit_reason="Lifecycle test grant",
                    ),
                    PartnerRemnawaveResourceGrantModel(
                        id=node_grant_id,
                        workspace_id=workspace_id,
                        resource_type="node",
                        resource_uuid=uuid.uuid4(),
                        permission_keys=["remnawave_read"],
                        granted_by_admin_user_id=admin_id,
                        audit_reason="Unrelated node grant",
                    ),
                ]
            )
            await db.commit()

        async with sessions() as db:
            assert await _numeric_identity_cutover_ready(db) is True
            mobile = await db.get(MobileUserModel, mobile_id)
            assert mobile is not None
            plan = await prepare_remnawave_owner_identity_retirement(db, customer=mobile)
            assert {ref.require_numeric_id() for ref in plan.provider_refs} == {701, 702}
            retired_at = datetime.now(UTC)
            await apply_remnawave_owner_identity_retirement(db, plan=plan, retired_at=retired_at)
            plan.customer.remnawave_user_id = None
            plan.customer.remnawave_uuid = None
            plan.customer.is_active = False
            plan.customer.status = "deleted"
            await db.commit()

        async with sessions() as db:
            identities = list(
                (
                    await db.execute(
                        select(ServiceIdentityModel).where(
                            ServiceIdentityModel.id.in_({alias_service_id, distinct_service_id})
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(identities) == 2
            assert all(identity.identity_status == "revoked" for identity in identities)
            assert all(identity.provider_numeric_subject_id is None for identity in identities)
            assert all(identity.provider_subject_ref is None for identity in identities)
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RemnawaveIdentityReconciliationModel)
                    .where(
                        RemnawaveIdentityReconciliationModel.subject_id.in_(
                            {mobile_id, alias_service_id, distinct_service_id}
                        )
                    )
                )
                == 0
            )
            alias_grant = await db.get(PartnerRemnawaveResourceGrantModel, alias_grant_id)
            node_grant = await db.get(PartnerRemnawaveResourceGrantModel, node_grant_id)
            assert alias_grant is not None and alias_grant.revoked_at is not None
            assert node_grant is not None and node_grant.revoked_at is None
            audit = (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "partner_remnawave_resource_grant.revoked_by_account_deletion",
                        AuditLog.entity_id == str(alias_grant_id),
                    )
                )
            ).scalar_one()
            assert audit.admin_id is None
            assert audit.old_value["issuance_reason"] == "Lifecycle test grant"
            with pytest.raises(RemnawaveIdentityAccessConflict, match="not grantable"):
                await assert_remnawave_service_identity_grantable(
                    db,
                    service_identity_id=alias_service_id,
                )
            assert await _numeric_identity_cutover_ready(db) is True
    finally:
        await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_deletion_registry_serializes_create_marker_and_rejects_stale_remap_on_postgres() -> None:
    database_name = f"cvpn_rw_delete_race_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    engine = create_async_engine(url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        mobile_id, _ = await _seed_runtime_pair(
            sessions,
            same_owner=True,
            suffix=f"delete-race-{uuid.uuid4().hex[:8]}",
        )
        foreign_mobile_id, foreign_service_id = await _seed_runtime_pair(
            sessions,
            same_owner=False,
            suffix=f"foreign-delete-{uuid.uuid4().hex[:8]}",
        )
        collided_legacy = uuid.uuid4()
        async with sessions() as db:
            foreign_mobile = await db.get(MobileUserModel, foreign_mobile_id)
            foreign_service = await db.get(ServiceIdentityModel, foreign_service_id)
            assert foreign_mobile is not None
            assert foreign_service is not None
            foreign_mobile.remnawave_user_id = 850
            foreign_mobile.remnawave_uuid = str(collided_legacy)
            foreign_service.provider_numeric_subject_id = 850
            foreign_service.provider_subject_ref = str(collided_legacy)
            db.add_all(
                [
                    _mapping_row(
                        subject_type="mobile_user",
                        subject_id=foreign_mobile.id,
                        numeric_id=850,
                        legacy_uuid=str(collided_legacy),
                    ),
                    _mapping_row(
                        subject_type="service_identity",
                        subject_id=foreign_service.id,
                        numeric_id=850,
                        legacy_uuid=str(collided_legacy),
                    ),
                ]
            )
            await db.commit()
        async with sessions() as db:
            foreign_mobile = await db.get(MobileUserModel, foreign_mobile_id)
            assert foreign_mobile is not None
            with pytest.raises(RemnawaveIdentityAccessConflict, match="another reconciliation owner"):
                await prepare_remnawave_owner_identity_retirement(db, customer=foreign_mobile)
            await db.rollback()
        async with sessions() as db:
            await db.execute(
                delete(RemnawaveIdentityReconciliationModel).where(
                    RemnawaveIdentityReconciliationModel.subject_id.in_({foreign_mobile_id, foreign_service_id})
                )
            )
            foreign_mobile = await db.get(MobileUserModel, foreign_mobile_id)
            foreign_service = await db.get(ServiceIdentityModel, foreign_service_id)
            assert foreign_mobile is not None
            assert foreign_service is not None
            foreign_mobile.remnawave_user_id = None
            foreign_mobile.remnawave_uuid = None
            foreign_service.provider_numeric_subject_id = None
            foreign_service.provider_subject_ref = None
            await db.commit()

        stale_session = sessions()
        delete_session = sessions()
        marker_session = sessions()
        try:
            stale_customer = await stale_session.get(MobileUserModel, mobile_id)
            deleting_customer = await delete_session.get(MobileUserModel, mobile_id)
            assert stale_customer is not None
            assert deleting_customer is not None
            plan = await prepare_remnawave_owner_identity_retirement(
                delete_session,
                customer=deleting_customer,
            )

            marker_pid = int(await marker_session.scalar(select(func.pg_backend_pid())))
            marker_started = asyncio.Event()

            async def begin_create_marker() -> object:
                marker_started.set()
                try:
                    return await RemnawaveCreateAttemptService(marker_session).begin(
                        scope="remnawave-customer:create",
                        idempotency_key=remnawave_customer_create_key(mobile_id),
                        request_hash=remnawave_create_request_hash({"race": str(mobile_id)}),
                        customer_account_id=mobile_id,
                    )
                except BaseException as exc:  # asserted below; keeps the task observable
                    return exc

            marker_task = asyncio.create_task(begin_create_marker())
            await marker_started.wait()
            async with sessions() as observer:
                for _ in range(100):
                    wait_event = (
                        await observer.execute(
                            text("select wait_event from pg_stat_activity where pid = :pid"),
                            {"pid": marker_pid},
                        )
                    ).scalar_one_or_none()
                    if wait_event == "advisory":
                        break
                    await asyncio.sleep(0.01)
                else:
                    pytest.fail("Create marker did not block on the deletion registry lock")

            await apply_remnawave_owner_identity_retirement(
                delete_session,
                plan=plan,
                retired_at=datetime.now(UTC),
            )
            plan.customer.status = "deleted"
            plan.customer.is_active = False
            await delete_session.commit()

            marker_result = await asyncio.wait_for(marker_task, timeout=5)
            assert isinstance(marker_result, RemnawaveCreateAttemptConflict)
            assert "no longer accepts" in str(marker_result)
            await marker_session.rollback()

            with pytest.raises(RemnawaveIdentityAccessConflict, match="owner is terminal"):
                await persist_runtime_mapped_mobile_identity(
                    stale_session,
                    customer=stale_customer,
                    remnawave_user_id=801,
                    remnawave_uuid=uuid.uuid4(),
                    source="postgres_delete_race",
                )
            await stale_session.rollback()
        finally:
            await marker_session.rollback()
            await marker_session.close()
            await delete_session.rollback()
            await delete_session.close()
            await stale_session.rollback()
            await stale_session.close()

        async with sessions() as db:
            marker_count = await db.scalar(
                select(func.count())
                .select_from(ApiIdempotencyRecordModel)
                .where(ApiIdempotencyRecordModel.resource_id == mobile_id)
            )
            assert marker_count == 0

        pending_mobile_id, _ = await _seed_runtime_pair(
            sessions,
            same_owner=True,
            suffix=f"pending-delete-{uuid.uuid4().hex[:8]}",
        )
        pending_legacy = uuid.uuid4()
        async with sessions() as db:
            pending_mobile = await db.get(MobileUserModel, pending_mobile_id)
            assert pending_mobile is not None
            pending_mobile.remnawave_user_id = 901
            pending_mobile.remnawave_uuid = str(pending_legacy)
            db.add(
                _mapping_row(
                    subject_type="mobile_user",
                    subject_id=pending_mobile_id,
                    numeric_id=901,
                    legacy_uuid=str(pending_legacy),
                )
            )
            await db.commit()

        async with sessions() as marker_db:
            attempts = RemnawaveCreateAttemptService(marker_db)
            decision = await attempts.begin(
                scope="remnawave-customer:update",
                idempotency_key=remnawave_create_request_hash({"pending_delete_customer": str(pending_mobile_id)}),
                request_hash=remnawave_create_request_hash({"operation": "pending_update"}),
                customer_account_id=pending_mobile_id,
            )
            assert decision.should_mutate is True

        async with sessions() as delete_db:
            pending_mobile = await delete_db.get(MobileUserModel, pending_mobile_id)
            assert pending_mobile is not None
            with pytest.raises(RemnawaveIdentityAccessConflict, match="unresolved Remnawave provider mutation"):
                await prepare_remnawave_owner_identity_retirement(
                    delete_db,
                    customer=pending_mobile,
                )
            assert pending_mobile.remnawave_user_id == 901
            ledger_count = await delete_db.scalar(
                select(func.count())
                .select_from(RemnawaveIdentityReconciliationModel)
                .where(RemnawaveIdentityReconciliationModel.subject_id == pending_mobile_id)
            )
            assert ledger_count == 1
            await delete_db.rollback()

        async with sessions() as marker_db:
            attempts = RemnawaveCreateAttemptService(marker_db)
            replay = await attempts.begin(
                scope="remnawave-customer:update",
                idempotency_key=remnawave_create_request_hash({"pending_delete_customer": str(pending_mobile_id)}),
                request_hash=remnawave_create_request_hash({"operation": "pending_update"}),
                customer_account_id=pending_mobile_id,
            )
            await attempts.mark_completed(
                replay.record,
                user_ref=RemnawaveUserRef(id=901, legacy_uuid=pending_legacy),
            )
            await marker_db.commit()

        async with sessions() as delete_db:
            pending_mobile = await delete_db.get(MobileUserModel, pending_mobile_id)
            assert pending_mobile is not None
            plan = await prepare_remnawave_owner_identity_retirement(
                delete_db,
                customer=pending_mobile,
            )
            assert plan.provider_refs == (RemnawaveUserRef(id=901, legacy_uuid=pending_legacy),)
            await delete_db.rollback()
    finally:
        await engine.dispose()
        await _drop_database(database_name)
