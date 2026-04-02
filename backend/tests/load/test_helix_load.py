"""Load tests for Helix admin control-plane routes.

Targets:

1. GET /api/v1/helix/admin/rollouts/{rollout_id}
2. GET /api/v1/helix/admin/rollouts/{rollout_id}/canary-evidence
3. GET /api/v1/helix/admin/nodes

Run with:
    set HELIX_LOAD_BEARER_TOKEN=<operator-or-admin-token>
    set HELIX_LOAD_ROLLOUT_ID=rollout-helix-canary
    cd backend
    locust -f tests/load/test_helix_load.py --host=http://localhost:8000

Example headless runs:
    locust -f tests/load/test_helix_load.py --host=http://localhost:8000 \
        --tags canary-evidence -u 60 -r 10 -t 5m --headless

    locust -f tests/load/test_helix_load.py --host=http://localhost:8000 \
        --tags helix-admin -u 80 -r 20 -t 5m --headless
"""

from __future__ import annotations

import os

from locust import HttpUser, between, tag, task


def _load_token() -> str:
    return os.getenv("HELIX_LOAD_BEARER_TOKEN", "").strip()


def _load_rollout_id() -> str:
    return os.getenv("HELIX_LOAD_ROLLOUT_ID", "rollout-helix-canary").strip()


def _load_expected_decision() -> str | None:
    value = os.getenv("HELIX_LOAD_EXPECT_DECISION", "").strip().lower()
    return value or None


class HelixAdminLoadUser(HttpUser):
    """Exercises Helix admin routes that operators will poll during canary/hardening."""

    wait_time = between(1, 2)

    def on_start(self) -> None:
        token = _load_token()
        if token:
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        self.rollout_id = _load_rollout_id()
        self.expected_decision = _load_expected_decision()

    @tag("helix-admin", "rollout-status")
    @task(2)
    def test_rollout_status(self) -> None:
        with self.client.get(
            f"/api/v1/helix/admin/rollouts/{self.rollout_id}",
            name="/api/v1/helix/admin/rollouts/[rollout_id]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                body = response.json()
                if body.get("rollout_id") != self.rollout_id:
                    response.failure("rollout_id mismatch in rollout status response")
                    return
                if "current_batch" not in body or "desktop" not in body:
                    response.failure("rollout status response is missing current_batch or desktop")
                    return
                response.success()
                return

            if response.status_code in {401, 403}:
                response.failure("missing or invalid HELIX_LOAD_BEARER_TOKEN")
                return

            response.failure(f"unexpected status for rollout status route: {response.status_code}")

    @tag("helix-admin", "canary-evidence")
    @task(4)
    def test_rollout_canary_evidence(self) -> None:
        with self.client.get(
            f"/api/v1/helix/admin/rollouts/{self.rollout_id}/canary-evidence",
            name="/api/v1/helix/admin/rollouts/[rollout_id]/canary-evidence",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                body = response.json()
                if body.get("rollout_id") != self.rollout_id:
                    response.failure("rollout_id mismatch in canary evidence response")
                    return
                if "decision" not in body or "snapshot" not in body:
                    response.failure("canary evidence response is missing decision or snapshot")
                    return

                expected_decision = self.expected_decision
                if expected_decision is not None and body.get("decision") != expected_decision:
                    response.failure(
                        "canary evidence decision mismatch: "
                        f"expected {expected_decision}, got {body.get('decision')}"
                    )
                    return

                response.success()
                return

            if response.status_code in {401, 403}:
                response.failure("missing or invalid HELIX_LOAD_BEARER_TOKEN")
                return

            response.failure(
                f"unexpected status for canary evidence route: {response.status_code}"
            )

    @tag("helix-admin", "nodes")
    @task(1)
    def test_node_inventory(self) -> None:
        with self.client.get(
            "/api/v1/helix/admin/nodes",
            name="/api/v1/helix/admin/nodes",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                body = response.json()
                if not isinstance(body, list):
                    response.failure("node inventory response is not a list")
                    return
                response.success()
                return

            if response.status_code in {401, 403}:
                response.failure("missing or invalid HELIX_LOAD_BEARER_TOKEN")
                return

            response.failure(f"unexpected status for node inventory route: {response.status_code}")
