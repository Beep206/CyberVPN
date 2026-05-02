from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.application.services.workflow_engine import WorkflowEngine
from src.config import Settings, get_settings, reset_settings_cache
from src.domain.entities import FleetRequestRecord
from src.domain.enums import RequestStatus, RequestType
from src.main import (
    create_app,
)
from src.observability import before_send, before_send_transaction, is_observability_authorized, setup_sentry


class SentrySetupTests(unittest.TestCase):
    def test_setup_sentry_skips_init_without_dsn(self) -> None:
        settings = Settings(sentry_dsn="", sentry_release="", environment="staging")

        with patch("sentry_sdk.init") as mock_init:
            initialized = setup_sentry(settings)

        self.assertFalse(initialized)
        mock_init.assert_not_called()

    def test_setup_sentry_uses_runtime_contract(self) -> None:
        settings = Settings(
            sentry_dsn="https://fleet@example.com/1",
            sentry_release="node-fleet-controller@abc123",
            environment="staging",
        )

        with (
            patch("sentry_sdk.init") as mock_init,
            patch("sentry_sdk.set_tag") as mock_set_tag,
        ):
            initialized = setup_sentry(settings)

        self.assertTrue(initialized)
        kwargs = mock_init.call_args.kwargs
        self.assertEqual(kwargs["dsn"], "https://fleet@example.com/1")
        self.assertEqual(kwargs["environment"], "staging")
        self.assertEqual(kwargs["release"], "node-fleet-controller@abc123")
        self.assertFalse(kwargs["send_default_pii"])
        self.assertEqual(kwargs["max_request_body_size"], "never")
        self.assertFalse(kwargs["include_local_variables"])
        self.assertEqual(kwargs["in_app_include"], ["src"])
        self.assertEqual(kwargs["traces_sample_rate"], 0.1)
        self.assertEqual(len(kwargs["integrations"]), 2)
        self.assertIs(kwargs["before_send"], before_send)
        self.assertIs(kwargs["before_send_transaction"], before_send_transaction)
        mock_set_tag.assert_any_call("runtime_surface", "node-fleet-controller")
        mock_set_tag.assert_any_call("service.name", settings.service_name)

    def test_before_send_scrubs_sensitive_fields(self) -> None:
        event = {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret",
                    "Cookie": "session=secret",
                    "X-Request-Id": "req-1",
                },
                "data": {"openbao_token": "secret"},
                "cookies": {"session": "secret-cookie"},
            },
            "user": {
                "email": "operator@example.com",
                "username": "operator",
                "ip_address": "127.0.0.1",
                "id": "internal-1",
            },
            "extra": {
                "openbao_response": {"token": "secret"},
                "workflow_stage": "preview",
            },
            "contexts": {
                "fleet": {
                    "opentofu_plan": "sensitive",
                    "operation_type": "reconcile",
                }
            },
        }

        scrubbed = before_send(event, {})

        self.assertIs(scrubbed, event)
        self.assertEqual(event["request"]["headers"]["Authorization"], "[Filtered]")
        self.assertEqual(event["request"]["headers"]["Cookie"], "[Filtered]")
        self.assertEqual(event["request"]["headers"]["X-Request-Id"], "req-1")
        self.assertEqual(event["request"]["data"], "[Filtered]")
        self.assertEqual(event["request"]["cookies"], "[Filtered]")
        self.assertNotIn("email", event["user"])
        self.assertNotIn("username", event["user"])
        self.assertNotIn("ip_address", event["user"])
        self.assertEqual(event["extra"]["openbao_response"], "[Filtered]")
        self.assertEqual(event["extra"]["workflow_stage"], "preview")
        self.assertEqual(event["contexts"]["fleet"]["opentofu_plan"], "[Filtered]")
        self.assertEqual(event["contexts"]["fleet"]["operation_type"], "reconcile")

    def test_before_send_transaction_drops_internal_probe_and_health(self) -> None:
        health_event = {"request": {"url": "http://127.0.0.1:8085/api/v1/health/live"}}
        probe_event = {"request": {"url": "http://127.0.0.1:8085/api/v1/observability/sentry-contract"}}
        normal_event = {"request": {"url": "http://127.0.0.1:8085/api/v1/reconcile/preview"}}

        self.assertIsNone(before_send_transaction(health_event, {}))
        self.assertIsNone(before_send_transaction(probe_event, {}))
        self.assertEqual(before_send_transaction(normal_event, {}), normal_event)

    def test_environment_contract_loads_from_environment(self) -> None:
        os.environ["SENTRY_DSN"] = "https://fleet@example.com/1"
        os.environ["SENTRY_RELEASE"] = "node-fleet-controller@testsha"
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET"] = "fleet-secret"

        reset_settings_cache()
        settings = get_settings()

        self.assertEqual(settings.sentry_dsn, "https://fleet@example.com/1")
        self.assertEqual(settings.sentry_release, "node-fleet-controller@testsha")
        self.assertEqual(settings.environment, "staging")
        self.assertEqual(settings.observability_internal_secret, "fleet-secret")

        reset_settings_cache()
        for key in (
            "SENTRY_DSN",
            "SENTRY_RELEASE",
            "ENVIRONMENT",
            "FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET",
        ):
            os.environ.pop(key, None)

    def test_observability_authorization_requires_matching_secret(self) -> None:
        self.assertTrue(is_observability_authorized("expected-secret", "expected-secret"))
        self.assertFalse(is_observability_authorized("expected-secret", None))
        self.assertFalse(is_observability_authorized("", "expected-secret"))
        self.assertFalse(is_observability_authorized("expected-secret", "wrong-secret"))


class ApiObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-observability.sqlite3")
        settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="staging",
            sentry_dsn="https://fleet@example.com/1",
            sentry_release="node-fleet-controller@abc123",
            observability_internal_secret="fleet-secret",
        )
        self.client = TestClient(create_app(settings))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_observability_probe_rejects_missing_secret(self) -> None:
        response = self.client.get("/api/v1/observability/sentry-contract")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Forbidden"})

    def test_observability_probe_returns_runtime_contract(self) -> None:
        response = self.client.get(
            "/api/v1/observability/sentry-contract",
            headers={"x-observability-secret": "fleet-secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "runtime_surface": "node-fleet-controller",
                "service": "cybervpn-node-fleet-controller",
                "environment": "staging",
                "release": "node-fleet-controller@abc123",
                "dsn_configured": True,
            },
        )


class WorkflowSpanTests(unittest.TestCase):
    def test_workflow_engine_creates_child_span(self) -> None:
        request = FleetRequestRecord(
            request_id="req_test",
            request_type=RequestType.FAILOVER,
            requested_by="system",
            idempotency_key="failover-001",
            status=RequestStatus.ACCEPTED,
            environment="prod",
            country="jp",
        )
        fake_span = MagicMock()

        with patch("sentry_sdk.start_span", return_value=nullcontext(fake_span)) as mock_start_span:
            steps = WorkflowEngine().build_plan(request)

        self.assertEqual(steps[0].step_name, "evaluate_guardrails")
        mock_start_span.assert_called_once_with(
            op="workflow.plan",
            name="node-fleet-controller.workflow.build_plan",
        )
        fake_span.set_data.assert_any_call("node_fleet.request_type", "failover")
        fake_span.set_data.assert_any_call("node_fleet.request_environment", "prod")
