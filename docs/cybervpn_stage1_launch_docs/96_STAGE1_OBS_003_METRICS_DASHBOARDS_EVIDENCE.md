# S1-OBS-003 - Metrics and Dashboards Evidence

Date: 2026-05-06  
Revalidated: 2026-05-09  
Task ID: `S1-OBS-003`  
Scope: local/no-cost Prometheus/Grafana metrics and dashboard coverage for S1 Controlled Public Beta  
Result: completed locally and revalidated; deployed Grafana screenshots and live target evidence remain required before go-live

## Decision

For S1 Controlled Public Beta, the primary launch dashboard must show the B2C path and runtime dependencies:

- API health, latency and 5xx ratio;
- auth success and registrations;
- payment success/events;
- paid-but-no-access / orphan reconciliation counts and max age;
- trial activation and config delivery failures;
- worker queue depth and task error ratio;
- PostgreSQL health, active connections and rollback ratio;
- Redis/Valkey health, memory and rejected connections;
- Remnawave scrape health, healthy nodes and API dependency errors;
- Telegram Bot scrape health, update rate and error ratio.

`S1-OBS-003` does not prove alert delivery. Local alert routing is covered by `S1-OBS-004` in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live Telegram/email delivery proof remains required before go-live.

## Implementation Completed

Added:

```text
infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json
infra/prometheus/rules/stage1_dashboard_recording_rules.yml
scripts/validate-s1-observability-dashboards.py
backend/tests/contract/test_stage1_observability_assets_contract.py
docs/runbooks/STAGE1_OBSERVABILITY_DASHBOARD_RUNBOOK.md
```

Updated:

```text
infra/prometheus/prometheus.yml
services/task-worker/src/metrics.py
services/task-worker/src/tasks/payments/reconcile_stage1.py
services/task-worker/tests/test_payments.py
services/task-worker/tests/integration/test_e2e.py
```

## Dashboard Contract

| Surface | Dashboard signal |
|---|---|
| API | `stage1:target_up`, `stage1:api_http_p95_seconds:5m`, `stage1:api_http_error_ratio:5m` |
| Auth | `stage1:auth_success_ratio:5m`, `stage1:registrations:24h` |
| Payments | `stage1:payment_success_ratio:1h`, `payments_total` |
| Paid-but-no-access / orphan policy | `cybervpn_stage1_payment_reconciliation_items_current`, `cybervpn_stage1_payment_reconciliation_max_age_minutes`, `cybervpn_stage1_payment_reconciliation_launch_blocked` |
| Provisioning | `stage1:remnawave_external_error_ratio:5m`, `miniapp_config_delivery_total`, `trials_activated_total` |
| Worker | `cybervpn_queue_depth`, `stage1:worker_task_error_ratio:5m` |
| PostgreSQL | `stage1:target_up{job="postgres"}`, `pg_stat_database_numbackends`, `stage1:postgres_rollback_ratio:5m` |
| Redis/Valkey | `stage1:target_up{job="redis"}`, `stage1:redis_memory_used_bytes`, `redis_rejected_connections_total` |
| Remnawave | `stage1:target_up{job="remnawave"}`, `stage1:remnawave_healthy_nodes:current` |
| Telegram Bot | `stage1:target_up{job="cybervpn-telegram-bot"}`, `bot_updates_total`, `stage1:telegram_bot_error_ratio:5m` |

## Validation

| Command | Result |
|---|---|
| `python3 scripts/validate-s1-observability-dashboards.py` | PASS: S1 dashboard, recording rules and scrape jobs are wired |
| `bash scripts/validate-observability-tooling.sh` | PASS: Prometheus config/rules and rendered Alertmanager config valid; optional file_sd warnings for absent optional target files remain non-blocking |
| `cd backend && uv run pytest tests/contract/test_stage1_observability_assets_contract.py -q --no-cov` | PASS: 3 tests |
| `cd services/task-worker && uv run pytest tests/test_payments.py::test_reconcile_stage1_payments_calls_internal_backend_job tests/test_payments.py::test_reconcile_stage1_payments_skips_without_backend_config -q --no-cov` | PASS: 2 tests |
| `cd services/task-worker && uv run ruff check src/metrics.py src/tasks/payments/reconcile_stage1.py` | PASS |
| `cd backend && uv run ruff check tests/contract/test_stage1_observability_assets_contract.py` | PASS |
| `python3 -m py_compile scripts/validate-s1-observability-dashboards.py` | PASS |
| `python3 -m json.tool infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json >/dev/null` | PASS |

## 2026-05-09 Revalidation

This revalidation was run as the `S1-OBS-003` live metrics/dashboard evidence follow-up. No live Prometheus, Grafana or Alertmanager endpoints/tokens are available in this local/no-cost workspace, so this proves the repository dashboard/rule/metric contract only. It does not prove deployed Grafana screenshots, live Prometheus target health or production-like metric samples.

Environment presence check was performed without printing secret values:

```text
PROMETHEUS_URL=missing
GRAFANA_URL=missing
GRAFANA_SERVICE_ACCOUNT_TOKEN=missing
GRAFANA_API_KEY=missing
ALERTMANAGER_URL=missing
```

Docker resource check:

```text
no running containers
```

Revalidation results:

| Check | Result |
|---|---|
| `python3 scripts/validate-s1-observability-dashboards.py` | PASS: dashboard, recording rules and scrape jobs wired |
| `bash scripts/validate-observability-tooling.sh` | PASS: Prometheus config/rules and rendered Alertmanager config valid; optional file_sd warnings remain non-blocking |
| `cd backend && uv run pytest tests/contract/test_stage1_observability_assets_contract.py -q --no-cov` | PASS: `3` tests |
| `cd services/task-worker && uv run pytest tests/test_payments.py::test_reconcile_stage1_payments_calls_internal_backend_job tests/test_payments.py::test_reconcile_stage1_payments_skips_without_backend_config -q --no-cov` | PASS: `2` tests |
| `cd services/task-worker && uv run ruff check src/metrics.py src/tasks/payments/reconcile_stage1.py` | PASS |
| `cd backend && uv run ruff check tests/contract/test_stage1_observability_assets_contract.py` | PASS |
| `python3 -m py_compile scripts/validate-s1-observability-dashboards.py` | PASS |
| `python3 -m json.tool infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json >/dev/null` | PASS |

## Live Evidence Readiness Matrix

| Live evidence item | Current state | Required go-live evidence |
|---|---|---|
| Prometheus endpoint | Missing in local environment | Redacted `PROMETHEUS_URL` or deployed endpoint proof |
| Grafana endpoint/token | Missing in local environment | Redacted Grafana URL and service-account/API-token proof |
| Live Prometheus targets | Not available locally | `/api/v1/targets` or screenshot/export showing API, worker, bot, PostgreSQL, Redis, Remnawave targets up |
| Stage 1 Grafana dashboard | Local JSON contract only | Deployed dashboard screenshot/export for `stage1-controlled-public-beta` |
| Paid-but-no-access metrics | Local worker metric contract only | Synthetic or staging reconciliation sample showing current count/max age/launch-blocked values |
| Production-like metric data | Not available locally | Dashboard panels populated with real staging/prod samples, not only static JSON |

## Demo

| Component | Feature | Status |
|---|---|---|
| Dashboard JSON | S1 B2C runtime panel contract | PASS |
| Prometheus recording rules | Stage 1 dashboard recording rules wired and valid | PASS |
| Prometheus/Alertmanager tooling | Config/rules/rendered alertmanager validation | PASS |
| Worker metrics | Paid-but-no-access reconciliation metrics contract | PASS |
| Live Grafana/Prometheus | Screenshots, live targets and production-like metric samples | BLOCKED externally: endpoints/tokens are not present in this workspace |

## Official Documentation Used

- Prometheus configuration and rule loading: `https://prometheus.io/docs/prometheus/latest/configuration/configuration/`
- Prometheus file-based service discovery format: `https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config`
- Prometheus Python client counter/gauge guidance: `https://prometheus.github.io/client_python/instrumenting/counter/`
- Grafana dashboard provisioning: `https://grafana.com/docs/grafana/latest/administration/provisioning/`
- Grafana dashboard JSON model: `https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/`

## What This Closes

| Item | Status |
|---|---|
| `S1-OBS-003` local metrics/dashboard assets | Closed locally |
| Prometheus rule file wiring for S1 dashboard recording rules | Closed locally |
| Grafana dashboard JSON contract for S1 B2C runtime | Closed locally |
| Paid-but-no-access reconciliation visibility metric in worker | Closed locally |
| Static validation without paid external infrastructure | Closed locally |

## Security Review

| Check | Result |
|---|---|
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate Next/PostCSS advisory remains tracked because the force fix proposes a breaking downgrade path |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `backend/` | PASS: no known vulnerabilities found |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `services/task-worker/` | PASS: no known vulnerabilities found |
| Secret-pattern scan over updated `S1-OBS-003` source docs | PASS: no matches |
| Dangerous-pattern scan over updated `S1-OBS-003` source docs | PASS: no matches |

## What Remains Open

| Item | Why still open |
|---|---|
| Live Grafana screenshot evidence | Requires deployed/staging Grafana with real Prometheus data |
| Live target-up evidence | Requires actual staging/prod targets and exporters |
| Live paid-but-no-access sample | Requires real provider/staging/prod reconciliation run or explicit synthetic staging sample |
| Alert delivery | Local routing/config is completed in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live Telegram/email proof remains required |
| Live Sentry project/test-event proof | Still required alongside dashboard/alert evidence before go-live |

## Acceptance Result

`S1-OBS-003` is **completed locally and revalidated on 2026-05-09** as metrics/dashboard configuration and static evidence.

Go-live remains blocked by deployed Grafana screenshots/live target proof, live Sentry proof and live Telegram/email alert delivery.

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-OBS-003` as item `24` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| Environment presence check for Prometheus/Grafana/Alertmanager URLs and local tooling | PASS as readiness inventory: live endpoints are missing locally; `promtool`/`amtool` are not installed on host, but validation script runs containerized tooling successfully |
| `python3 scripts/validate-s1-observability-dashboards.py` | PASS: dashboard, recording rules and scrape jobs wired |
| `bash scripts/validate-observability-tooling.sh` | PASS: Prometheus config/rules and rendered Alertmanager config valid; optional `file_sd` warnings remain non-blocking |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/contract/test_stage1_observability_assets_contract.py -q --no-cov` | PASS: `3` tests |
| `cd services/task-worker && PYENV_VERSION=3.13.11 uv run pytest tests/test_payments.py::test_reconcile_stage1_payments_calls_internal_backend_job tests/test_payments.py::test_reconcile_stage1_payments_skips_without_backend_config -q --no-cov` | PASS: `2` tests |
| `cd services/task-worker && PYENV_VERSION=3.13.11 uv run ruff check src/metrics.py src/tasks/payments/reconcile_stage1.py` | PASS |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check tests/contract/test_stage1_observability_assets_contract.py` | PASS |
| `python3 -m py_compile scripts/validate-s1-observability-dashboards.py` | PASS |
| `python3 -m json.tool infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json >/dev/null` | PASS |

Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
