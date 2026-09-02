from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260831_connection_drop_receipts.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("remnawave_connection_drop_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operations(*, preflight_result=None):
    operations = MagicMock()
    operations.get_bind.return_value.execute.return_value.first.return_value = preflight_result
    return operations


def test_connection_drop_migration_is_expand_safe_and_adds_exclusive_grants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    operations = _operations()
    migration.op = operations
    monkeypatch.setattr(migration, "_receipt_table_exists", lambda _bind: False)

    migration.upgrade()

    operations.drop_constraint.assert_called_once_with(
        "ck_partner_remnawave_resource_type",
        "partner_remnawave_resource_grants",
        type_="check",
    )
    check_sql = operations.create_check_constraint.call_args.args[2]
    assert "service_identity" in check_sql
    exclusive_index = next(
        call
        for call in operations.create_index.call_args_list
        if call.args[0] == "uq_partner_remnawave_exclusive_active_resource"
    )
    assert exclusive_index.kwargs["unique"] is True
    assert "revoked_at IS NULL" in str(exclusive_index.kwargs["postgresql_where"])
    assert "service_identity" in str(exclusive_index.kwargs["postgresql_where"])

    table_call = next(
        call for call in operations.create_table.call_args_list if call.args[0] == "remnawave_connection_drop_receipts"
    )
    column_names = {item.name for item in table_call.args[1:] if getattr(item, "name", None)}
    assert {
        "id",
        "key_hmac",
        "hmac_key_id",
        "receipt_id",
        "audience",
        "actor_id",
        "workspace_id",
        "scope_hmac",
        "payload_hmac",
        "state",
        "created_at",
        "updated_at",
        "expires_at",
        "reconciled_at",
        "reconciled_by_admin_id",
        "reconciliation_reason",
        "reconciliation_reference",
    } <= column_names
    assert "idempotency_key" not in column_names
    assert "payload" not in column_names
    assert "ip_address" not in column_names
    expires_at = next(item for item in table_call.args[1:] if getattr(item, "name", None) == "expires_at")
    assert expires_at.nullable is True
    lifecycle_constraints = [
        str(item.sqltext)
        for item in table_call.args[1:]
        if getattr(item, "name", None) == "ck_remnawave_connection_drop_receipt_lifecycle"
    ]
    assert len(lifecycle_constraints) == 1
    assert "state = 'outcome_unknown' AND expires_at IS NULL" in lifecycle_constraints[0]
    assert "reconciled_at IS NULL" in lifecycle_constraints[0]
    assert "expires_at > reconciled_at" in lifecycle_constraints[0]
    pending_actor_index = next(
        call
        for call in operations.create_index.call_args_list
        if call.args[0] == "ix_remnawave_connection_drop_receipts_pending_actor"
    )
    assert "outcome_unknown" in str(pending_actor_index.kwargs["postgresql_where"])
    key_lifecycle_index = next(
        call
        for call in operations.create_index.call_args_list
        if call.args[0] == "ix_remnawave_connection_drop_receipts_key_lifecycle"
    )
    assert key_lifecycle_index.args[2] == ["hmac_key_id", "state", "expires_at"]
    unresolved_index = next(
        call
        for call in operations.create_index.call_args_list
        if call.args[0] == "ix_remnawave_connection_drop_receipts_unresolved_public_id"
    )
    assert unresolved_index.args[2] == ["receipt_id"]
    assert "outcome_unknown" in str(unresolved_index.kwargs["postgresql_where"])


def test_connection_drop_migration_aborts_on_existing_cross_workspace_grants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    operations = _operations(preflight_result=("node", "323fe749-9d77-464f-8fe2-51a7b0b0209a"))
    migration.op = operations
    monkeypatch.setattr(migration, "_receipt_table_exists", lambda _bind: False)

    with pytest.raises(RuntimeError, match="Conflicting active partner Remnawave"):
        migration.upgrade()

    operations.create_table.assert_not_called()
    operations.create_index.assert_not_called()
    operations.drop_constraint.assert_not_called()


def test_connection_drop_migration_downgrade_restores_prior_contract() -> None:
    migration = _load_migration()
    operations = _operations()
    migration.op = operations

    migration.downgrade()

    operations.drop_table.assert_not_called()
    operations.drop_index.assert_called_once_with(
        "uq_partner_remnawave_exclusive_active_resource",
        table_name="partner_remnawave_resource_grants",
    )
    restored_check = operations.create_check_constraint.call_args.args[2]
    assert "service_identity" not in restored_check


def test_connection_drop_reupgrade_strictly_validates_and_reuses_retained_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    operations = _operations()
    migration.op = operations
    validate = MagicMock()
    monkeypatch.setattr(migration, "_receipt_table_exists", lambda _bind: True)
    monkeypatch.setattr(migration, "_validate_retained_receipt_table", validate)

    migration.upgrade()

    validate.assert_called_once_with(operations.get_bind.return_value)
    operations.create_table.assert_not_called()
    assert not any(
        call.args[0].startswith("ix_remnawave_connection_drop_receipts")
        for call in operations.create_index.call_args_list
    )


def test_connection_drop_reupgrade_fails_before_grant_ddl_for_incompatible_retained_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    operations = _operations()
    migration.op = operations
    monkeypatch.setattr(migration, "_receipt_table_exists", lambda _bind: True)
    monkeypatch.setattr(
        migration,
        "_validate_retained_receipt_table",
        MagicMock(side_effect=RuntimeError("incompatible exact schema: constraints")),
    )

    with pytest.raises(RuntimeError, match="incompatible exact schema"):
        migration.upgrade()

    operations.drop_constraint.assert_not_called()
    operations.create_constraint.assert_not_called()
    operations.create_index.assert_not_called()


def test_connection_drop_downgrade_fails_before_destructive_changes_when_grants_exist() -> None:
    migration = _load_migration()
    operations = _operations(preflight_result=(1,))
    migration.op = operations

    with pytest.raises(RuntimeError, match="Remove service_identity grants"):
        migration.downgrade()

    operations.drop_table.assert_not_called()
    operations.drop_index.assert_not_called()
