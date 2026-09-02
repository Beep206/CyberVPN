from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260901_partner_mutation_exclusive_grants.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("partner_mutation_exclusive_grants_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operations(*, duplicate=None):
    operations = MagicMock()
    operations.get_bind.return_value.execute.return_value.first.return_value = duplicate
    return operations


def test_upgrade_fails_before_ddl_when_mutable_resource_is_shared() -> None:
    migration = _load_migration()
    migration.op = operations = _operations(duplicate=("profile", "resource-uuid"))

    with pytest.raises(RuntimeError, match="profile/integration grants"):
        migration.upgrade()

    operations.drop_index.assert_not_called()
    operations.create_index.assert_not_called()


def test_upgrade_replaces_index_with_mutation_safe_exclusivity() -> None:
    migration = _load_migration()
    migration.op = operations = _operations()

    migration.upgrade()

    operations.drop_index.assert_called_once_with(
        "uq_partner_remnawave_exclusive_active_resource",
        table_name="partner_remnawave_resource_grants",
    )
    created = operations.create_index.call_args
    assert created.kwargs["unique"] is True
    predicate = str(created.kwargs["postgresql_where"])
    assert "profile" in predicate
    assert "integration" in predicate


def test_downgrade_restores_prior_node_and_service_identity_invariant() -> None:
    migration = _load_migration()
    migration.op = operations = _operations()

    migration.downgrade()

    predicate = str(operations.create_index.call_args.kwargs["postgresql_where"])
    assert "node" in predicate
    assert "service_identity" in predicate
    assert "profile" not in predicate
    assert "integration" not in predicate
