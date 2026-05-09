# S1-OBS-004 - Alerts Evidence

Date: 2026-05-06
Revalidated: 2026-05-09
Task ID: `S1-OBS-004`
Scope: local/no-cost Prometheus Alertmanager rules, routing and reproducible delivery-test procedure for S1 Controlled Public Beta
Result: completed locally and revalidated as alert configuration/routing evidence; live Telegram/email delivery proof remains required before go-live

## Decision

For S1 Controlled Public Beta, alerting must route launch-critical incidents to both approved channels:

- Telegram private alert channel: `-5173727789`
- backup email: `backup@cyber-vpn.net`

The first accepted live evidence must prove both channels. Local static validation only proves that Prometheus and Alertmanager are configured correctly.

## Implementation Completed

Added:

```text
infra/prometheus/rules/stage1_alerts.yml
scripts/validate-s1-alerting.py
scripts/run-s1-alert-delivery-smoke.sh
backend/tests/contract/test_stage1_alerting_assets_contract.py
docs/runbooks/STAGE1_OBSERVABILITY_ALERT_RUNBOOK.md
```

Updated:

```text
infra/prometheus/prometheus.yml
infra/alertmanager/alertmanager.yml.template
infra/alertmanager/docker-entrypoint.sh
infra/alertmanager/templates/telegram.tmpl
infra/docker-compose.yml
infra/.env.example
scripts/validate-observability-tooling.sh
```

## Alert Coverage

| Area | Alert examples |
|---|---|
| API | `Stage1ApiUnavailable`, `Stage1ApiErrorRatioHigh`, `Stage1ApiLatencyHigh` |
| Worker | `Stage1WorkerUnavailable`, `Stage1WorkerQueueBacklog`, `Stage1WorkerTaskErrorRatioHigh` |
| Telegram Bot | `Stage1TelegramBotUnavailable`, `Stage1TelegramBotErrorRatioHigh` |
| PostgreSQL | `Stage1PostgresUnavailable`, `Stage1PostgresRollbackRatioHigh` |
| Redis/Valkey | `Stage1RedisUnavailable`, `Stage1RedisRejectedConnections` |
| Remnawave/provisioning | `Stage1RemnawaveUnavailable`, `Stage1NoHealthyRemnawaveNodes`, `Stage1ProvisioningDependencyErrors` |
| Paid-but-no-access/orphan payments | `Stage1PaidButNoAccessReviewNeeded`, `Stage1PaidButNoAccessP1Escalation`, `Stage1PaidButNoAccessP0Blocker` |
| Backup/restore evidence | `Stage1PostgresBackupStale`, `Stage1RestoreDrillEvidenceExpired` |

## Routing Contract

| Route | Match | Receiver |
|---|---|---|
| `stage1-p0` | `priority="p0"` | Telegram + backup email |
| `stage1-p1` | `priority="p1"` | Telegram + backup email |
| `stage1-critical` | `severity="critical"` | Telegram + backup email |
| `stage1-warning` | `severity="warning"` | Telegram + backup email |
| `stage1-default` | fallback | Telegram + backup email |

`ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true` must be enabled in staging/production before accepting live evidence. With this flag enabled, Alertmanager refuses to start without real Telegram token, chat id, backup email and SMTP smarthost settings.

## Validation

| Command | Result |
|---|---|
| `python3 scripts/validate-s1-alerting.py` | PASS: S1 alert rules and Alertmanager Telegram/email routing are wired |
| `bash scripts/validate-observability-tooling.sh` | PASS: Prometheus config/rules and rendered Alertmanager config pass `promtool`/`amtool`; optional file_sd warnings remain non-blocking |
| `cd backend && uv run pytest tests/contract/test_stage1_alerting_assets_contract.py -q --no-cov` | PASS: 3 tests |
| `sh -n infra/alertmanager/docker-entrypoint.sh` | PASS |
| `bash -n scripts/run-s1-alert-delivery-smoke.sh` | PASS |
| `bash -n scripts/validate-observability-tooling.sh` | PASS |
| `python3 -m py_compile scripts/validate-s1-alerting.py` | PASS |

## 2026-05-09 Revalidation

This pass revalidated `S1-OBS-004` as a local/no-cost alerting contract. No live delivery command was executed because the workspace has no live Alertmanager endpoint, Telegram receiver secret or SMTP receiver settings.

### Environment Readiness

| Item | 2026-05-09 status | Meaning |
|---|---|---|
| `ALERTMANAGER_URL` | Missing | No live Alertmanager API target available for delivery smoke |
| `ALERTMANAGER_TELEGRAM_BOT_TOKEN` | Missing | Telegram delivery cannot be proven from this workspace |
| `ALERTMANAGER_TELEGRAM_CHAT_ID` | Missing | Target chat cannot be proven from environment |
| `ALERTMANAGER_BACKUP_EMAIL` | Missing | Backup email receiver not configured in this shell |
| `ALERTMANAGER_SMTP_FROM` | Missing | SMTP sender not configured |
| `ALERTMANAGER_SMTP_SMARTHOST` | Missing | SMTP relay not configured |
| `ALERTMANAGER_SMTP_AUTH_USERNAME` | Missing | SMTP auth username not configured |
| `ALERTMANAGER_SMTP_PASSWORD` | Missing | SMTP auth password not configured |
| Running Alertmanager container | Not running | No local/live delivery target available |

### Revalidation Commands

| Command | Result |
|---|---|
| `python3 scripts/validate-s1-alerting.py` | PASS: S1 alert rules and Alertmanager Telegram/email routing are wired |
| `bash scripts/validate-observability-tooling.sh` | PASS: Prometheus config/rules and rendered Alertmanager config pass validation; optional `file_sd` warnings remain non-blocking |
| `cd backend && uv run pytest tests/contract/test_stage1_alerting_assets_contract.py -q --no-cov` | PASS: 3 tests |
| `sh -n infra/alertmanager/docker-entrypoint.sh` | PASS |
| `bash -n scripts/run-s1-alert-delivery-smoke.sh` | PASS |
| `python3 -m py_compile scripts/validate-s1-alerting.py` | PASS |
| `npm audit --audit-level=high` | PASS for high/critical threshold; known moderate `postcss` via Next.js remains tracked and not force-fixed because npm proposes a breaking downgrade |
| `uv export` + `uvx pip-audit --timeout 60` in `backend/` | PASS for runtime and all-groups exports after retrying transient PyPI timeouts |
| `uv export` + `uvx pip-audit --timeout 60` in `services/telegram-bot/` | PASS for runtime and all-groups exports after retrying transient PyPI timeouts |
| `uv export` + `uvx pip-audit --timeout 60` in `services/task-worker/` | PASS for runtime and all-groups exports after retrying transient PyPI timeouts |

### Live Evidence Required Before Go-Live

| Evidence | Required proof |
|---|---|
| Telegram alert delivery | Screenshot or export showing test alert received in private channel `-5173727789` |
| Backup email delivery | Screenshot/header proof showing the same test alert delivered to `backup@cyber-vpn.net` |
| Alertmanager intake | `amtool`/API evidence showing `Stage1AlertDeliveryTest` accepted and visible |
| Receiver fail-closed config | Staging/production `ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true` with redacted receiver env inventory |
| Paid-but-no-access route | Synthetic P1/P0 route proof for `Stage1PaidButNoAccessP1Escalation` and `Stage1PaidButNoAccessP0Blocker` |

## Official Documentation Used

- Alertmanager configuration, routes, receivers and SMTP options: `https://prometheus.io/docs/alerting/latest/configuration/`
- Alertmanager notification templates: `https://prometheus.io/docs/alerting/latest/notification_examples/`

## What This Closes

| Item | Status |
|---|---|
| `S1-OBS-004` local alert rule/routing contract | Closed locally |
| Prometheus loading for S1 alert rules | Closed locally |
| Alertmanager receiver routing to Telegram + backup email | Closed locally |
| Paid-but-no-access 15m/P1/P0 alert rule coverage | Closed locally |
| Reproducible synthetic alert delivery command | Closed locally |

## What Remains Open

| Item | Why still open |
|---|---|
| Real Telegram delivery screenshot | Requires real Alertmanager Telegram bot token and running Alertmanager |
| Real backup email delivery screenshot/header | Requires real SMTP account/config and running Alertmanager |
| Live Alertmanager `/api/v2/alerts` evidence | Requires deployed/staging Alertmanager |
| Deployed Grafana/live target proof | Still required from `S1-OBS-003` go-live evidence |
| Live Sentry project/test-event proof | Still required alongside alert delivery before go-live |

## Acceptance Result

`S1-OBS-004` is **completed locally and revalidated** as alert configuration/routing evidence.

Go-live remains blocked by live Telegram/email delivery proof, deployed dashboard/live target proof and live Sentry proof.

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-OBS-004` as item `25` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| Environment readiness check for Alertmanager URL, Telegram receiver, SMTP receiver and running Alertmanager container | PASS as readiness inventory: all live delivery env values are missing locally and no Alertmanager container is running |
| `python3 scripts/validate-s1-alerting.py` | PASS: S1 alert rules and Alertmanager Telegram/email routing are wired |
| `bash scripts/validate-observability-tooling.sh` | PASS: Prometheus config/rules and rendered Alertmanager config valid; optional `file_sd` warnings remain non-blocking |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/contract/test_stage1_alerting_assets_contract.py -q --no-cov` | PASS: `3` tests |
| `sh -n infra/alertmanager/docker-entrypoint.sh` | PASS |
| `bash -n scripts/run-s1-alert-delivery-smoke.sh` | PASS |
| `bash -n scripts/validate-observability-tooling.sh` | PASS |
| `python3 -m py_compile scripts/validate-s1-alerting.py` | PASS |

Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
