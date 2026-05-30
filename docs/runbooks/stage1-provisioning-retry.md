# Stage 1 Provisioning Retry Runbook

## Purpose

`stage1_provisioning_retry_jobs` keeps Remnawave provisioning retry state in PostgreSQL so paid or trial access recovery does not depend on Redis stream retention.

## Enablement Gates

- Backend: `STAGE1_PROVISIONING_RETRY_CLAIMING_ENABLED=false` by default.
- Task worker: `STAGE1_PROVISIONING_RETRY_CLAIMING_ENABLED=false` by default.
- Batch size is bounded by `STAGE1_PROVISIONING_RETRY_BATCH_LIMIT`.

Keep both claiming flags disabled until focused tests and Security review pass.

## Rollback

Set both `STAGE1_PROVISIONING_RETRY_CLAIMING_ENABLED=false` values and restart the backend and task-worker. This stops new claims without deleting queued jobs, preserving paid state and durable retry evidence for manual reconciliation.

Do not delete rows from `stage1_provisioning_retry_jobs` during rollback. Escalate `dead_letter` and `reconciliation_required` rows to support/ops with only safe job metadata: job id, operation, state, attempt count, next attempt timestamp, and correlation id.

## Safe Data Rules

Logs, metrics, Sentry events, issue comments, and worker result payloads must not contain email, Telegram init data, raw provider payment id, secrets, subscription/config URLs, protocol links, or raw Remnawave error text.
