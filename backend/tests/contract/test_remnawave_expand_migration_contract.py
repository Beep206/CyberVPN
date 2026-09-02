from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy import CheckConstraint

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260830_remnawave_3_expand.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("remnawave_expand_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_expand_migration_keeps_legacy_references_and_creates_required_stores() -> None:
    migration = _load_migration()
    operations = MagicMock()
    migration.op = operations

    migration.upgrade()

    added_columns = {(call.args[0], call.args[1].name) for call in operations.add_column.call_args_list}
    assert ("mobile_users", "remnawave_user_id") in added_columns
    assert ("mobile_users", "subscription_auto_renew_enabled") in added_columns
    assert ("service_identities", "provider_numeric_subject_id") in added_columns
    assert operations.drop_column.call_count == 0

    created_tables = {call.args[0] for call in operations.create_table.call_args_list}
    assert created_tables == {
        "remnawave_identity_reconciliations",
        "partner_remnawave_resource_grants",
        "remnawave_stream_receipts",
        "remnawave_stream_dead_letters",
        "remnawave_user_usage_hourly",
        "remnawave_subscription_request_events",
        "remnawave_node_user_presence",
        "remnawave_node_connections_hourly",
        "remnawave_stream_gaps",
        "remnawave_stream_checkpoints",
    }
    gap_table_call = next(
        call for call in operations.create_table.call_args_list if call.args[0] == "remnawave_stream_gaps"
    )
    gap_columns = {item.name: item for item in gap_table_call.args[1:] if hasattr(item, "name")}
    assert gap_columns["expires_at"].nullable is True
    gap_constraints = " ".join(
        str(item.sqltext) for item in gap_table_call.args[1:] if isinstance(item, CheckConstraint)
    )
    assert "pending" in gap_constraints
    assert "expires_at IS NULL" in gap_constraints
    assert "expires_at IS NOT NULL" in gap_constraints

    partial_indexes = {
        call.args[0]: str(call.kwargs.get("postgresql_where", ""))
        for call in operations.create_index.call_args_list
        if call.kwargs.get("unique") is True
    }
    assert "remnawave_user_id IS NOT NULL" in partial_indexes["uq_mobile_users_remnawave_user_id_not_null"]
    assert (
        "provider_numeric_subject_id IS NOT NULL"
        in partial_indexes["uq_service_identities_remnawave_numeric_subscription"]
    )
    assert (
        "numeric_user_id IS NOT NULL AND reconciliation_state = 'mapped'"
        in partial_indexes["uq_remnawave_reconciliation_mapped_numeric"]
    )
    assert (
        "legacy_uuid IS NOT NULL AND reconciliation_state = 'mapped'"
        in partial_indexes["uq_remnawave_reconciliation_mapped_legacy"]
    )


def test_expand_migration_downgrade_removes_only_new_surface() -> None:
    migration = _load_migration()
    operations = MagicMock()
    migration.op = operations

    migration.downgrade()

    dropped_columns = {(call.args[0], call.args[1]) for call in operations.drop_column.call_args_list}
    assert dropped_columns == {
        ("mobile_users", "remnawave_user_id"),
        ("mobile_users", "subscription_auto_renew_enabled"),
        ("service_identities", "provider_numeric_subject_id"),
    }
    assert ("mobile_users", "remnawave_uuid") not in dropped_columns
    assert ("service_identities", "provider_subject_ref") not in dropped_columns
    assert operations.drop_table.call_count == 10
