from datetime import UTC, datetime

import pytest

from src.infrastructure.remnawave.mappers.user_mapper import map_remnawave_user


@pytest.mark.unit
def test_maps_remnawave_3_numeric_user_without_synthetic_uuid() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC).isoformat()

    user = map_remnawave_user(
        {
            "id": 42,
            "username": "alice",
            "status": "active",
            "shortUuid": "nanoid-value",
            "createdAt": now,
            "updatedAt": now,
            "userTraffic": {
                "usedTrafficBytes": 123,
                "lifetimeUsedTrafficBytes": 456,
                "onlineAt": now,
            },
        }
    )

    assert user.remnawave_id == 42
    assert user.uuid is None
    assert user.ref.require_numeric_id() == 42
    assert user.used_traffic_bytes == 123
    assert user.lifetime_used_traffic_bytes == 456


@pytest.mark.unit
def test_rejects_user_payload_without_numeric_or_legacy_identity() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC).isoformat()

    with pytest.raises(ValueError, match="neither numeric id nor legacy UUID"):
        map_remnawave_user(
            {
                "username": "alice",
                "status": "active",
                "shortUuid": "nanoid-value",
                "createdAt": now,
                "updatedAt": now,
            }
        )


@pytest.mark.parametrize("invalid_numeric_id", [0, -1, True, "42"])
def test_rejects_inexact_numeric_identity(invalid_numeric_id) -> None:
    with pytest.raises(ValueError, match="exact positive integer"):
        map_remnawave_user(
            {
                "id": invalid_numeric_id,
                "username": "numeric-invalid",
                "status": "ACTIVE",
                "shortUuid": "numeric-invalid",
                "createdAt": "2026-01-01T00:00:00+00:00",
                "updatedAt": "2026-01-01T00:00:00+00:00",
            }
        )
