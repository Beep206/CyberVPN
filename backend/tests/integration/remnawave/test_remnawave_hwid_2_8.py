from __future__ import annotations

from src.infrastructure.remnawave.contracts import (
    RemnawaveSubscriptionConfigResponse,
    RemnawaveUserResponse,
)


def _user_payload(**extra: object) -> dict[str, object]:
    return {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "username": "hwid-user",
        "status": "ACTIVE",
        "shortUuid": "HWID123",
        "createdAt": "2026-06-30T00:00:00Z",
        "updatedAt": "2026-06-30T00:01:00Z",
        **extra,
    }


def test_remnawave_2_8_hwid_active_aliases_are_accepted() -> None:
    assert RemnawaveUserResponse.model_validate(_user_payload(hwidActive=2)).hwid_active == 2
    assert RemnawaveUserResponse.model_validate(_user_payload(hwidDevicesActive=3)).hwid_active == 3
    assert RemnawaveUserResponse.model_validate(_user_payload(activeHwidDevices=True)).hwid_active is True


def test_subscription_config_keeps_legacy_hwid_header_compatibility() -> None:
    for key in ("xHwidActive", "x-hwid-active", "x-hwid-limit"):
        config = RemnawaveSubscriptionConfigResponse.model_validate(
            {
                "config": "https://sub.example.com/hwid-user",
                "isFound": True,
                key: 2,
            }
        )

        assert config.x_hwid_active == 2
