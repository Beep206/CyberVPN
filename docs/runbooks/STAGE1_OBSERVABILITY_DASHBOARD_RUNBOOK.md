# Stage 1 Observability Dashboard Runbook

This runbook covers the local/no-cost S1 metrics dashboard slice for Controlled Public Beta.

## Primary Dashboard

Use Grafana dashboard `stage1-controlled-public-beta`.

Primary signals:

- API, worker, Telegram Bot, PostgreSQL, Redis/Valkey and Remnawave scrape health.
- API latency and API 5xx ratio.
- Auth success ratio and registrations.
- Payment success ratio, payment events and paid-but-no-access reconciliation counts.
- Trial activation and Mini App config delivery failures.
- Worker queue depth and worker task error ratio.
- PostgreSQL active connections and rollback ratio.
- Redis memory and rejected connections.
- Remnawave healthy node count and Remnawave API dependency errors.
- Telegram Bot update rate and error ratio.

## Triage Order

1. Paid-but-no-access reconciliation.
Check `cybervpn_stage1_payment_reconciliation_items_current`, `cybervpn_stage1_payment_reconciliation_max_age_minutes` and `cybervpn_stage1_payment_reconciliation_launch_blocked`. If any item approaches 24 hours, pause paid beta until support/finance resolves or owner explicitly accepts the risk.

2. Remnawave health.
Check `stage1:target_up{job="remnawave"}`, `stage1:remnawave_healthy_nodes:current` and `stage1:remnawave_external_error_ratio:5m`. If Remnawave is down or has no healthy nodes, pause trial/payment provisioning.

3. API/auth health.
Check `stage1:api_http_p95_seconds:5m`, `stage1:api_http_error_ratio:5m` and `stage1:auth_success_ratio:5m`. Correlate with backend logs, Sentry and recent deploys.

4. Worker and queue health.
Check `cybervpn_queue_depth`, `stage1:worker_task_error_ratio:5m` and the worker dashboard. If queues grow while provisioning/payments are active, pause new paid flow before orphan payments accumulate.

5. PostgreSQL and Redis/Valkey.
Check PostgreSQL connections, rollback ratio, Redis memory and rejected connections. Redis/Valkey is not S1 durable source of truth; PostgreSQL remains authoritative.

## Local Validation

Run:

```bash
python3 scripts/validate-s1-observability-dashboards.py
bash scripts/validate-observability-tooling.sh
cd backend && uv run pytest tests/contract/test_stage1_observability_assets_contract.py -q --no-cov
```

## Go-Live Evidence To Capture

- Grafana screenshot of `stage1-controlled-public-beta` with all panels visible and no secret values.
- Prometheus targets page or API output showing required S1 jobs up or intentionally documented as unavailable.
- Prometheus rule evaluation proof for `stage1_dashboard_recording_rules.yml`.
- One sample paid-but-no-access reconciliation run output with safe/redacted references only.
- Correlated Sentry/log sample for a non-sensitive synthetic incident.

## Boundary

This runbook does not prove alert delivery. Telegram/email alert tests are handled by `S1-OBS-004`.
