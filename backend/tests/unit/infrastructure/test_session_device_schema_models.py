"""Schema foundation checks for user devices and refresh rotation history."""

from sqlalchemy.orm import configure_mappers

from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.database.models.user_device_model import UserDeviceModel


def test_user_devices_have_active_principal_device_uniqueness() -> None:
    configure_mappers()

    table = UserDeviceModel.__table__

    assert {
        "auth_realm_id",
        "principal_subject",
        "principal_class",
        "audience",
        "device_key_hash",
        "revoked_at",
        "revoked_reason",
    }.issubset(table.columns.keys())

    unique_index = next(index for index in table.indexes if index.name == "uq_user_devices_active_principal_device_key")
    assert unique_index.unique is True
    assert [column.name for column in unique_index.columns] == [
        "auth_realm_id",
        "principal_class",
        "principal_subject",
        "device_key_hash",
    ]
    assert str(unique_index.dialect_options["postgresql"]["where"]) == "revoked_at IS NULL"


def test_principal_sessions_are_ready_for_device_and_current_refresh_token_linkage() -> None:
    configure_mappers()

    table = PrincipalSessionModel.__table__

    assert "user_device_id" in table.columns
    assert "current_refresh_token_id" in table.columns
    assert table.columns["user_device_id"].nullable is True
    assert table.columns["current_refresh_token_id"].nullable is True

    assert "ix_principal_sessions_user_device_status" in {index.name for index in table.indexes}
    assert "ix_principal_sessions_current_refresh_token_id" in {index.name for index in table.indexes}


def test_refresh_tokens_are_append_only_rotation_ready() -> None:
    configure_mappers()

    table = RefreshToken.__table__

    assert {
        "jti",
        "family_id",
        "parent_token_id",
        "principal_session_id",
        "consumed_at",
        "replaced_by_token_id",
        "revoked_reason",
    }.issubset(table.columns.keys())

    index_names = {index.name for index in table.indexes}
    assert {
        "uq_refresh_tokens_jti",
        "ix_refresh_tokens_principal_session_id",
        "ix_refresh_tokens_family_id",
        "ix_refresh_tokens_parent_token_id",
        "ix_refresh_tokens_replaced_by_token_id",
        "ix_refresh_tokens_consumed_at",
        "ix_refresh_tokens_session_family",
    }.issubset(index_names)

    unique_index = next(index for index in table.indexes if index.name == "uq_refresh_tokens_jti")
    assert unique_index.unique is True
    assert str(unique_index.dialect_options["postgresql"]["where"]) == "jti IS NOT NULL"
