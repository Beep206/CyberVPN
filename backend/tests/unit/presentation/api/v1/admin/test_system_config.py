from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import Request
from prometheus_client import REGISTRY

from src.presentation.api.v1.admin import system_config as system_config_routes
from src.presentation.api.v1.admin.schemas import UpdateAdminMiniAppRuntimeConfigRequest


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "PUT",
            "path": "/api/v1/admin/system-config/miniapp-runtime",
            "headers": [(b"user-agent", b"pytest-agent")],
            "client": ("203.0.113.10", 443),
        }
    )


def _metric_value(name: str, labels: dict[str, str] | None = None) -> float:
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def test_get_admin_miniapp_runtime_config_returns_defaults_when_not_overridden(monkeypatch) -> None:
    state = {
        "model": None,
        "value": None,
    }

    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            assert key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY
            return state["model"]

        async def get_value(self, key: str, default=None):
            assert key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY
            return state["value"] if state["value"] is not None else default

        async def set(self, key: str, value, updated_by=None, description=None):
            state["value"] = value
            state["model"] = SimpleNamespace(
                key=key,
                description=description,
                updated_at=datetime(2026, 4, 22, 11, 0, tzinfo=UTC),
                updated_by=updated_by,
            )
            return state["model"]

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    response = asyncio.run(
        system_config_routes.get_admin_miniapp_runtime_config(
            db=object(),
            _=SimpleNamespace(id=uuid4()),
        )
    )

    assert response.key == "miniapp.runtime"
    assert response.rollout.enabled is True
    assert response.rollout.mode == "live"
    assert response.rollout.checkout_enabled is True
    assert response.rollout.canary_telegram_user_ids == []
    assert response.description == system_config_routes.MINIAPP_RUNTIME_CONFIG_DESCRIPTION
    assert response.updated_at is None
    assert response.updated_by is None


def test_update_admin_miniapp_runtime_config_persists_policy_and_writes_audit(monkeypatch) -> None:
    updated_by = uuid4()
    state = {
        "model": SimpleNamespace(
            key=system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY,
            description="Existing rollout control",
            updated_at=datetime(2026, 4, 22, 10, 45, tzinfo=UTC),
            updated_by=uuid4(),
        ),
        "value": {
            "enabled": True,
            "mode": "live",
            "trial_enabled": True,
            "checkout_enabled": True,
            "config_enabled": True,
            "maintenance_message": None,
            "canary_telegram_user_ids": [],
        },
        "launch_readiness": {
            "observability_acknowledged": True,
            "incident_runbook_acknowledged": True,
            "checkout_canary_passed": True,
            "config_delivery_canary_passed": True,
            "rollback_drill_acknowledged": True,
            "support_window_confirmed": True,
            "customer_comms_ready": True,
            "status_page_template_ready": True,
            "incident_channel": "#miniapp-war-room",
            "rollback_commander": "@ops-lead",
            "primary_oncall_contact": "@backend-oncall",
            "release_window_note": "Friday 18:00 UTC",
        },
    }

    class FakeDbSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.flushed = 0

        def add(self, value: object) -> None:
            self.added.append(value)

        async def flush(self) -> None:
            self.flushed += 1

    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            assert key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY
            return state["model"]

        async def get_value(self, key: str, default=None):
            if key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY:
                return state["value"] if state["value"] is not None else default
            if key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY:
                return state["launch_readiness"]
            raise AssertionError(f"Unexpected key: {key}")

        async def set(self, key: str, value, updated_by=None, description=None):
            state["value"] = value
            state["model"] = SimpleNamespace(
                key=key,
                description=description,
                updated_at=datetime(2026, 4, 22, 11, 30, tzinfo=UTC),
                updated_by=updated_by,
            )
            return state["model"]

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    fake_db = FakeDbSession()
    response = asyncio.run(
        system_config_routes.update_admin_miniapp_runtime_config(
            payload=UpdateAdminMiniAppRuntimeConfigRequest(
                enabled=False,
                mode="rollback",
                trial_enabled=False,
                checkout_enabled=False,
                config_enabled=True,
                maintenance_message="  Maintenance window  ",
                canary_telegram_user_ids=[123456789, 987654321, 123456789],
                change_reason="  canary rollback  ",
            ),
            request=_build_request(),
            db=fake_db,
            current_user=SimpleNamespace(id=updated_by),
        )
    )

    assert response.rollout.enabled is False
    assert response.rollout.mode == "rollback"
    assert response.rollout.trial_enabled is False
    assert response.rollout.checkout_enabled is False
    assert response.rollout.config_enabled is True
    assert response.rollout.maintenance_message == "Maintenance window"
    assert response.rollout.canary_telegram_user_ids == [123456789, 987654321]
    assert response.description == "Existing rollout control"
    assert response.updated_by == updated_by
    assert state["value"]["maintenance_message"] == "Maintenance window"
    assert state["value"]["canary_telegram_user_ids"] == [123456789, 987654321]

    assert len(fake_db.added) == 1
    audit_entry = fake_db.added[0]
    assert audit_entry.action == "system_config.miniapp_runtime.updated"
    assert audit_entry.entity_type == "system_config"
    assert audit_entry.entity_id == "miniapp.runtime"
    assert audit_entry.old_value == {
        "enabled": True,
        "mode": "live",
        "trial_enabled": True,
        "checkout_enabled": True,
        "config_enabled": True,
        "maintenance_message": None,
        "canary_telegram_user_ids": [],
    }
    assert audit_entry.new_value == {
        "enabled": False,
        "mode": "rollback",
        "trial_enabled": False,
        "checkout_enabled": False,
        "config_enabled": True,
        "maintenance_message": "Maintenance window",
        "canary_telegram_user_ids": [123456789, 987654321],
        "change_reason": "canary rollback",
    }
    assert audit_entry.ip_address == "203.0.113.10"
    assert audit_entry.user_agent == "pytest-agent"
    assert fake_db.flushed == 1


def test_update_admin_miniapp_runtime_config_blocks_live_mode_when_launch_gates_incomplete(monkeypatch) -> None:
    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            return SimpleNamespace(
                key=key,
                description="Existing rollout control",
                updated_at=datetime(2026, 4, 22, 10, 45, tzinfo=UTC),
                updated_by=uuid4(),
            )

        async def get_value(self, key: str, default=None):
            if key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY:
                return {
                    "enabled": True,
                    "mode": "canary",
                    "trial_enabled": True,
                    "checkout_enabled": True,
                    "config_enabled": True,
                    "maintenance_message": None,
                    "canary_telegram_user_ids": [123456789],
                }
            if key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY:
                return {
                    "observability_acknowledged": True,
                    "incident_runbook_acknowledged": False,
                    "checkout_canary_passed": True,
                    "config_delivery_canary_passed": False,
                    "rollback_drill_acknowledged": False,
                    "support_window_confirmed": False,
                    "customer_comms_ready": False,
                    "status_page_template_ready": False,
                    "incident_channel": None,
                    "rollback_commander": None,
                    "primary_oncall_contact": None,
                    "release_window_note": None,
                }
            return default

        async def set(self, key: str, value, updated_by=None, description=None):
            raise AssertionError("set should not be called when launch readiness is incomplete")

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    try:
        asyncio.run(
            system_config_routes.update_admin_miniapp_runtime_config(
                payload=UpdateAdminMiniAppRuntimeConfigRequest(
                    enabled=True,
                    mode="live",
                    trial_enabled=True,
                    checkout_enabled=True,
                    config_enabled=True,
                    maintenance_message=None,
                    canary_telegram_user_ids=[],
                    change_reason="promote canary to live",
                ),
                request=_build_request(),
                db=SimpleNamespace(add=lambda value: None, flush=lambda: None),
                current_user=SimpleNamespace(id=uuid4()),
            )
        )
    except system_config_routes.HTTPException as exc:
        assert exc.status_code == 409
        assert "launch readiness gates are incomplete" in exc.detail
    else:
        raise AssertionError("Expected HTTPException")


def test_get_admin_miniapp_launch_readiness_returns_defaults(monkeypatch) -> None:
    state = {
        "model": None,
        "value": None,
    }

    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            assert key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY
            return state["model"]

        async def get_value(self, key: str, default=None):
            assert key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY
            return state["value"] if state["value"] is not None else default

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    response = asyncio.run(
        system_config_routes.get_admin_miniapp_launch_readiness_config(
            db=object(),
            _=SimpleNamespace(id=uuid4()),
        )
    )

    assert response.key == "miniapp.launch_readiness"
    assert response.readiness.is_ready is False
    assert response.readiness.observability_acknowledged is False
    assert response.readiness.incident_channel is None
    assert response.description == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_DESCRIPTION


def test_update_admin_miniapp_launch_readiness_persists_policy_and_writes_audit(monkeypatch) -> None:
    updated_by = uuid4()
    state = {
        "model": SimpleNamespace(
            key=system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY,
            description="Existing launch readiness control",
            updated_at=datetime(2026, 4, 22, 10, 45, tzinfo=UTC),
            updated_by=uuid4(),
        ),
        "runtime": {
            "enabled": True,
            "mode": "canary",
            "trial_enabled": True,
            "checkout_enabled": True,
            "config_enabled": True,
            "maintenance_message": None,
            "canary_telegram_user_ids": [123456789],
        },
        "value": {
            "observability_acknowledged": False,
            "incident_runbook_acknowledged": False,
            "checkout_canary_passed": False,
            "config_delivery_canary_passed": False,
            "rollback_drill_acknowledged": False,
            "support_window_confirmed": False,
            "customer_comms_ready": False,
            "status_page_template_ready": False,
            "incident_channel": None,
            "rollback_commander": None,
            "primary_oncall_contact": None,
            "release_window_note": None,
        },
    }

    class FakeDbSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.flushed = 0

        def add(self, value: object) -> None:
            self.added.append(value)

        async def flush(self) -> None:
            self.flushed += 1

    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            assert key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY
            return state["model"]

        async def get_value(self, key: str, default=None):
            if key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY:
                return state["value"] if state["value"] is not None else default
            if key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY:
                return state["runtime"]
            raise AssertionError(f"Unexpected key: {key}")

        async def set(self, key: str, value, updated_by=None, description=None):
            state["value"] = value
            state["model"] = SimpleNamespace(
                key=key,
                description=description,
                updated_at=datetime(2026, 4, 22, 11, 50, tzinfo=UTC),
                updated_by=updated_by,
            )
            return state["model"]

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    fake_db = FakeDbSession()
    response = asyncio.run(
        system_config_routes.update_admin_miniapp_launch_readiness_config(
            payload=system_config_routes.UpdateAdminMiniAppLaunchReadinessConfigRequest(
                observability_acknowledged=True,
                incident_runbook_acknowledged=True,
                checkout_canary_passed=True,
                config_delivery_canary_passed=True,
                rollback_drill_acknowledged=True,
                support_window_confirmed=True,
                customer_comms_ready=True,
                status_page_template_ready=True,
                incident_channel="  #miniapp-war-room  ",
                rollback_commander="  @ops-lead  ",
                primary_oncall_contact="  @backend-oncall  ",
                release_window_note="  Friday 18:00 UTC  ",
                change_reason="  all gates green after canary  ",
            ),
            request=_build_request(),
            db=fake_db,
            current_user=SimpleNamespace(id=updated_by),
        )
    )

    assert response.readiness.is_ready is True
    assert response.readiness.incident_channel == "#miniapp-war-room"
    assert response.readiness.rollback_commander == "@ops-lead"
    assert response.readiness.primary_oncall_contact == "@backend-oncall"
    assert response.readiness.release_window_note == "Friday 18:00 UTC"
    assert response.updated_by == updated_by
    assert len(fake_db.added) == 1
    audit_entry = fake_db.added[0]
    assert audit_entry.action == "system_config.miniapp_launch_readiness.updated"
    assert audit_entry.entity_id == "miniapp.launch_readiness"
    assert audit_entry.new_value["is_ready"] is True
    assert audit_entry.new_value["incident_channel"] == "#miniapp-war-room"
    assert audit_entry.new_value["rollback_commander"] == "@ops-lead"
    assert audit_entry.new_value["change_reason"] == "all gates green after canary"


def test_get_admin_miniapp_launch_summary_derives_server_state(monkeypatch) -> None:
    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_value(self, key: str, default=None):
            if key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY:
                return {
                    "enabled": True,
                    "mode": "canary",
                    "trial_enabled": True,
                    "checkout_enabled": True,
                    "config_enabled": True,
                    "maintenance_message": None,
                    "canary_telegram_user_ids": [123456789],
                }
            if key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY:
                return {
                    "observability_acknowledged": True,
                    "incident_runbook_acknowledged": True,
                    "checkout_canary_passed": True,
                    "config_delivery_canary_passed": True,
                    "rollback_drill_acknowledged": True,
                    "support_window_confirmed": True,
                    "customer_comms_ready": True,
                    "status_page_template_ready": True,
                    "incident_channel": None,
                    "rollback_commander": "@ops-lead",
                    "primary_oncall_contact": "@backend-oncall",
                    "release_window_note": "Friday 18:00 UTC",
                }
            return default

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    response = asyncio.run(
        system_config_routes.get_admin_miniapp_launch_summary(
            db=object(),
            _=SimpleNamespace(id=uuid4()),
        )
    )

    assert response.launch_state == "canary_in_progress"
    assert response.live_switch_allowed is False
    assert response.next_action == "complete_launch_gates"
    assert response.primary_action is None
    assert response.available_actions == ["enter_maintenance", "start_rollback"]
    assert "incident_channel_missing" in response.blockers
    assert _metric_value(
        "miniapp_launch_state_current",
        {"launch_state": "canary_in_progress"},
    ) == 1
    assert _metric_value(
        "miniapp_runtime_rollout_mode_current",
        {"mode": "canary"},
    ) == 1
    assert _metric_value("miniapp_launch_live_switch_allowed") == 0
    assert _metric_value("miniapp_launch_blockers_current") == 1


def test_execute_admin_miniapp_launch_action_promotes_live_and_writes_audit(monkeypatch) -> None:
    updated_by = uuid4()
    state = {
        "model": SimpleNamespace(
            key=system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY,
            description="Existing rollout control",
            updated_at=datetime(2026, 4, 22, 10, 45, tzinfo=UTC),
            updated_by=uuid4(),
        ),
        "value": {
            "enabled": True,
            "mode": "canary",
            "trial_enabled": True,
            "checkout_enabled": True,
            "config_enabled": True,
            "maintenance_message": "Canary in progress",
            "canary_telegram_user_ids": [123456789],
        },
        "launch_readiness": {
            "observability_acknowledged": True,
            "incident_runbook_acknowledged": True,
            "checkout_canary_passed": True,
            "config_delivery_canary_passed": True,
            "rollback_drill_acknowledged": True,
            "support_window_confirmed": True,
            "customer_comms_ready": True,
            "status_page_template_ready": True,
            "incident_channel": "#miniapp-war-room",
            "rollback_commander": "@ops-lead",
            "primary_oncall_contact": "@backend-oncall",
            "release_window_note": "Friday 18:00 UTC",
        },
    }

    class FakeDbSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.flushed = 0

        def add(self, value: object) -> None:
            self.added.append(value)

        async def flush(self) -> None:
            self.flushed += 1

    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            assert key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY
            return state["model"]

        async def get_value(self, key: str, default=None):
            if key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY:
                return state["value"]
            if key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY:
                return state["launch_readiness"]
            return default

        async def set(self, key: str, value, updated_by=None, description=None):
            state["value"] = value
            state["model"] = SimpleNamespace(
                key=key,
                description=description,
                updated_at=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
                updated_by=updated_by,
            )
            return state["model"]

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    fake_db = FakeDbSession()
    before_actions = _metric_value(
        "miniapp_launch_actions_total",
        {"action": "promote_to_live", "status": "executed"},
    )

    response = asyncio.run(
        system_config_routes.execute_admin_miniapp_launch_action(
            payload=system_config_routes.ExecuteAdminMiniAppLaunchActionRequest(
                action="promote_to_live",
                change_reason="  canary stable across payment and config flows  ",
            ),
            request=_build_request(),
            db=fake_db,
            current_user=SimpleNamespace(id=updated_by),
        )
    )

    assert response.launch_state == "live"
    assert response.runtime.mode == "live"
    assert response.runtime.maintenance_message is None
    assert response.available_actions == [
        "start_rollback",
        "enter_maintenance",
        "return_to_canary",
    ]
    assert state["value"]["mode"] == "live"
    assert state["value"]["enabled"] is True
    assert state["value"]["maintenance_message"] is None
    assert len(fake_db.added) == 1
    audit_entry = fake_db.added[0]
    assert audit_entry.action == "system_config.miniapp_launch_action.executed"
    assert audit_entry.new_value["action"] == "promote_to_live"
    assert audit_entry.new_value["change_reason"] == "canary stable across payment and config flows"
    assert audit_entry.new_value["summary"]["launch_state"] == "live"
    assert audit_entry.old_value["summary"]["launch_state"] == "ready_for_live"
    assert _metric_value(
        "miniapp_launch_actions_total",
        {"action": "promote_to_live", "status": "executed"},
    ) == before_actions + 1
    assert _metric_value(
        "miniapp_launch_state_current",
        {"launch_state": "live"},
    ) == 1
    assert _metric_value(
        "miniapp_runtime_rollout_mode_current",
        {"mode": "live"},
    ) == 1
    assert _metric_value("miniapp_launch_live_switch_allowed") == 1
    assert _metric_value("miniapp_launch_blockers_current") == 0


def test_execute_admin_miniapp_launch_action_blocks_invalid_transition(monkeypatch) -> None:
    class FakeSystemConfigRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_key(self, key: str):
            return SimpleNamespace(
                key=key,
                description="Existing rollout control",
                updated_at=datetime(2026, 4, 22, 10, 45, tzinfo=UTC),
                updated_by=uuid4(),
            )

        async def get_value(self, key: str, default=None):
            if key == system_config_routes.MINIAPP_RUNTIME_CONFIG_KEY:
                return {
                    "enabled": True,
                    "mode": "canary",
                    "trial_enabled": True,
                    "checkout_enabled": True,
                    "config_enabled": True,
                    "maintenance_message": None,
                    "canary_telegram_user_ids": [123456789],
                }
            if key == system_config_routes.MINIAPP_LAUNCH_READINESS_CONFIG_KEY:
                return {
                    "observability_acknowledged": True,
                    "incident_runbook_acknowledged": False,
                    "checkout_canary_passed": True,
                    "config_delivery_canary_passed": False,
                    "rollback_drill_acknowledged": False,
                    "support_window_confirmed": False,
                    "customer_comms_ready": False,
                    "status_page_template_ready": False,
                    "incident_channel": None,
                    "rollback_commander": "@ops-lead",
                    "primary_oncall_contact": None,
                    "release_window_note": None,
                }
            return default

        async def set(self, key: str, value, updated_by=None, description=None):
            raise AssertionError("set should not be called for invalid launch actions")

    monkeypatch.setattr(system_config_routes, "SystemConfigRepository", FakeSystemConfigRepository)

    before_blocked = _metric_value(
        "miniapp_launch_actions_total",
        {"action": "promote_to_live", "status": "blocked"},
    )

    try:
        asyncio.run(
            system_config_routes.execute_admin_miniapp_launch_action(
                payload=system_config_routes.ExecuteAdminMiniAppLaunchActionRequest(
                    action="promote_to_live",
                    change_reason="attempt invalid promotion",
                ),
                request=_build_request(),
                db=object(),
                current_user=SimpleNamespace(id=uuid4()),
            )
        )
    except system_config_routes.HTTPException as exc:
        assert exc.status_code == 409
        assert "not allowed" in str(exc.detail)
        assert _metric_value(
            "miniapp_launch_actions_total",
            {"action": "promote_to_live", "status": "blocked"},
        ) == before_blocked + 1
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException for invalid launch action")


def test_get_admin_miniapp_launch_timeline_returns_recent_launch_events(monkeypatch) -> None:
    entries = [
        SimpleNamespace(
            id=uuid4(),
            created_at=datetime(2026, 4, 22, 12, 5, tzinfo=UTC),
            admin_id=uuid4(),
            action="system_config.miniapp_launch_action.executed",
            entity_id="miniapp.runtime",
            new_value={
                "action": "start_rollback",
                "runtime": {
                    "mode": "rollback",
                },
                "summary": {
                    "launch_state": "rollback_in_progress",
                },
                "change_reason": "rollback after canary regression",
            },
        ),
        SimpleNamespace(
            id=uuid4(),
            created_at=datetime(2026, 4, 22, 11, 55, tzinfo=UTC),
            admin_id=uuid4(),
            action="system_config.miniapp_launch_readiness.updated",
            entity_id="miniapp.launch_readiness",
            new_value={
                "is_ready": True,
                "change_reason": "all gates green",
            },
        ),
    ]

    class FakeAuditLogRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_recent_by_actions(self, actions, *, limit: int = 20):
            assert tuple(actions) == system_config_routes.MINIAPP_LAUNCH_TIMELINE_ACTIONS
            assert limit == 5
            return entries

    monkeypatch.setattr(system_config_routes, "AuditLogRepository", FakeAuditLogRepository)

    response = asyncio.run(
        system_config_routes.get_admin_miniapp_launch_timeline(
            limit=5,
            db=object(),
            _=SimpleNamespace(id=uuid4()),
        )
    )

    assert len(response) == 2
    assert response[0].event_type == "launch_action"
    assert response[0].action_name == "start_rollback"
    assert response[0].resulting_runtime_mode == "rollback"
    assert response[0].resulting_launch_state == "rollback_in_progress"
    assert response[0].change_reason == "rollback after canary regression"
    assert response[1].event_type == "launch_readiness_update"
    assert response[1].readiness_ready is True
