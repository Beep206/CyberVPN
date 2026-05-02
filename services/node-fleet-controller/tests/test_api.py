from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from src.config import Settings
from src.main import create_app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-api.sqlite3")
        settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        self.client = TestClient(create_app(settings))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_create_request_and_preview_reconcile(self) -> None:
        create_response = self.client.post(
            "/api/v1/requests",
            json={
                "request_type": "provisioning",
                "requested_by": "operator@example.com",
                "idempotency_key": "node-add-fr-001",
                "environment": "nonprod",
                "country": "fr",
                "provider_selector": "auto",
                "node_class": "standard",
                "requested_capacity_delta": 1,
            },
        )
        self.assertEqual(create_response.status_code, 202)
        body = create_response.json()
        self.assertEqual(body["request"]["request_type"], "provisioning")

        request_id = body["request"]["request_id"]
        audit_response = self.client.get(f"/api/v1/requests/{request_id}/audit")
        preview_response = self.client.get("/api/v1/reconcile/preview")

        self.assertEqual(audit_response.status_code, 200)
        self.assertEqual(len(audit_response.json()), 2)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.json()["items"][0]["planned_steps"][0], "select_placement")

    def test_reconcile_run_once_executes_internal_steps_and_stops_before_external_dependencies(self) -> None:
        create_response = self.client.post(
            "/api/v1/requests",
            json={
                "request_type": "provisioning",
                "requested_by": "operator@example.com",
                "idempotency_key": "node-add-de-001",
                "environment": "nonprod",
                "country": "de",
                "provider_selector": "auto",
                "node_class": "standard",
                "requested_capacity_delta": 1,
            },
        )
        self.assertEqual(create_response.status_code, 202)

        reconcile_response = self.client.post("/api/v1/reconcile/run-once")
        self.assertEqual(reconcile_response.status_code, 200)

        item = reconcile_response.json()["items"][0]
        self.assertEqual(item["executed_steps"], ["select_placement"])
        self.assertTrue(item["blocked_on_external_dependency"])
        self.assertEqual(item["request"]["status"], "running")
        self.assertEqual(item["operation_run"]["current_step"], "create_plan")
