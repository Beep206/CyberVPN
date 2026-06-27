from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.growth_benefit_model import InviteBatchModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.presentation.api.v1.invites import routes
from src.presentation.api.v1.invites.schemas import AdminExtendInviteBatchRequest, AdminInviteBatchActionRequest
from tests.helpers.realm_auth import cleanup_sqlite_file, create_realm_test_sessionmaker, initialize_realm_test_database


class AsyncSessionAdapter:
    def __init__(self, session) -> None:
        self._session = session

    def add(self, model) -> None:
        self._session.add(model)

    def add_all(self, models) -> None:
        self._session.add_all(models)

    async def flush(self) -> None:
        self._session.flush()

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.55"),
        state=SimpleNamespace(),
        headers={"user-agent": "pytest-invite-batches"},
    )


def _mobile_user(*, email: str) -> MobileUserModel:
    return MobileUserModel(
        id=uuid.uuid4(),
        public_uid=int(uuid.uuid4().int % 9_000_000_000) + 1_000_000,
        email=email,
        password_hash="hashed",
        is_active=True,
        status="active",
    )


def _admin_user() -> AdminUserModel:
    return AdminUserModel(
        id=uuid.uuid4(),
        login=f"invite-admin-{uuid.uuid4().hex[:8]}",
        email=f"invite-admin-{uuid.uuid4().hex[:8]}@example.test",
        password_hash="hashed",
        role="admin",
        is_active=True,
        is_email_verified=True,
    )


def _batch(owner: MobileUserModel, *, expires_at: datetime | None = None) -> InviteBatchModel:
    return InviteBatchModel(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        source_type="growth_benefit",
        requested_count=2,
        issued_count=2,
        friend_days=7,
        expiry_mode="relative" if expires_at else "none",
        expiry_days=30 if expires_at else None,
        expires_at=expires_at,
        entitlement_mode="profile_key",
        entitlement_profile_key="invite_limited_access_v1",
        entitlement_snapshot={},
        status="issued",
        idempotency_key=f"test-batch:{uuid.uuid4()}",
    )


def _invite(owner: MobileUserModel, batch: InviteBatchModel | None, *, code: str) -> InviteCodeModel:
    return InviteCodeModel(
        id=uuid.uuid4(),
        code=code,
        owner_user_id=owner.id,
        free_days=7,
        batch_id=batch.id if batch else None,
        status="issued",
        code_hash=f"hash-{code}",
        code_prefix=code[:8],
        entitlement_mode="profile_key" if batch else None,
        entitlement_profile_key="invite_limited_access_v1" if batch else None,
        entitlement_snapshot={},
        source="growth_benefit" if batch else "admin_grant",
        source_payment_id=None,
        expires_at=batch.expires_at if batch else None,
    )


@pytest.mark.asyncio
async def test_list_my_invites_groups_growth_batches_without_breaking_unbatched() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    owner = _mobile_user(email=f"owner-{uuid.uuid4().hex[:8]}@example.test")
    expires_at = datetime.now(UTC) + timedelta(days=30)
    batch = _batch(owner, expires_at=expires_at)
    try:
        with sessionmaker() as sync_db:
            db = AsyncSessionAdapter(sync_db)
            db.add_all(
                [
                    owner,
                    batch,
                    _invite(owner, batch, code=f"GI{uuid.uuid4().hex[:10].upper()}"),
                    _invite(owner, batch, code=f"GI{uuid.uuid4().hex[:10].upper()}"),
                    _invite(owner, None, code=f"AD{uuid.uuid4().hex[:10].upper()}"),
                ]
            )
            await db.flush()

            grouped = await routes.list_my_invites(
                offset=0,
                limit=50,
                group_by="batch",
                db=db,
                user_id=owner.id,
            )

            assert grouped.total_batches == 1
            assert grouped.total_invites == 3
            assert grouped.batches[0].batch.id == batch.id
            assert grouped.batches[0].batch.requested_count == 2
            assert [invite.batch_id for invite in grouped.batches[0].invites] == [batch.id, batch.id]
            assert len(grouped.unbatched) == 1
            assert grouped.unbatched[0].batch_id is None
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_invite_batch_extend_export_and_revoke_are_audited_without_raw_code_leakage() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    owner = _mobile_user(email=f"owner-{uuid.uuid4().hex[:8]}@example.test")
    admin = _admin_user()
    expires_at = datetime.now(UTC) + timedelta(days=5)
    batch = _batch(owner, expires_at=expires_at)
    first_code = f"GI{uuid.uuid4().hex[:10].upper()}"
    second_code = f"GI{uuid.uuid4().hex[:10].upper()}"
    first_invite = _invite(owner, batch, code=first_code)
    second_invite = _invite(owner, batch, code=second_code)
    second_invite.is_used = True
    second_invite.used_by_user_id = uuid.uuid4()
    second_invite.used_at = datetime.now(UTC)
    try:
        with sessionmaker() as sync_db:
            db = AsyncSessionAdapter(sync_db)
            db.add_all([owner, admin, batch, first_invite, second_invite])
            await db.flush()

            extended = await routes.admin_extend_invite_batch(
                batch_id=batch.id,
                body=AdminExtendInviteBatchRequest(reason="Marketing extension", expiry_days=7),
                request=_request(),
                db=db,
                current_user=admin,
            )
            assert extended.id == batch.id
            assert extended.expires_at is not None
            assert extended.expires_at > expires_at

            exported = await routes.admin_export_invite_batch(
                batch_id=batch.id,
                request=_request(),
                db=db,
                current_user=admin,
            )
            assert exported.exported_count == 2
            assert {row.code for row in exported.codes} == {first_code, second_code}

            revoked = await routes.admin_revoke_invite_batch(
                batch_id=batch.id,
                body=AdminInviteBatchActionRequest(reason="Campaign ended"),
                request=_request(),
                db=db,
                current_user=admin,
            )
            assert revoked.status == "revoked"

            persisted_batch = await db.get(InviteBatchModel, batch.id)
            assert persisted_batch is not None
            assert persisted_batch.status == "revoked"
            assert persisted_batch.revoked_by_admin_id == admin.id
            persisted_first = await db.get(InviteCodeModel, first_invite.id)
            persisted_second = await db.get(InviteCodeModel, second_invite.id)
            assert persisted_first is not None
            assert persisted_first.status == "revoked"
            assert persisted_first.revoked_at is not None
            assert persisted_second is not None
            assert persisted_second.status == "issued"
            assert persisted_second.revoked_at is None

            audit_rows = (await db.execute(select(AuditLog).where(AuditLog.entity_id == str(batch.id)))).scalars().all()
            assert {row.action for row in audit_rows} >= {
                "invite_batch.extended",
                "invite_batch.exported",
                "invite_batch.revoked",
            }
            serialized_audit = str([(row.old_value, row.new_value) for row in audit_rows])
            assert first_code not in serialized_audit
            assert second_code not in serialized_audit

            outbox_rows = (
                (await db.execute(select(OutboxEventModel).where(OutboxEventModel.aggregate_id == str(batch.id))))
                .scalars()
                .all()
            )
            assert {row.event_name for row in outbox_rows} >= {"invite.batch.extended", "invite.batch.revoked"}
            serialized_outbox = str([row.event_payload for row in outbox_rows])
            assert first_code not in serialized_outbox
            assert second_code not in serialized_outbox
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
