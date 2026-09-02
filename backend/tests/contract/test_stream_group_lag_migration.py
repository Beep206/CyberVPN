from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260901_stream_group_lag.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("stream_group_lag_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_nullable_lag_with_nonnegative_database_guard() -> None:
    migration = _load_migration()
    operations = MagicMock()
    migration.op = operations

    migration.upgrade()

    operations.add_column.assert_called_once()
    table_name, column = operations.add_column.call_args.args
    assert table_name == "remnawave_stream_checkpoints"
    assert column.name == "observed_group_lag"
    assert column.nullable is True
    operations.create_check_constraint.assert_called_once_with(
        "ck_remnawave_stream_checkpoint_group_lag_nonnegative",
        "remnawave_stream_checkpoints",
        "observed_group_lag IS NULL OR observed_group_lag >= 0",
    )


def test_downgrade_removes_guard_before_column() -> None:
    migration = _load_migration()
    operations = MagicMock()
    migration.op = operations

    migration.downgrade()

    operations.drop_constraint.assert_called_once_with(
        "ck_remnawave_stream_checkpoint_group_lag_nonnegative",
        "remnawave_stream_checkpoints",
        type_="check",
    )
    operations.drop_column.assert_called_once_with(
        "remnawave_stream_checkpoints",
        "observed_group_lag",
    )
    operation_names = [record[0] for record in operations.method_calls]
    assert operation_names.index("drop_constraint") < operation_names.index("drop_column")
