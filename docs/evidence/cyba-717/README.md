# CYBA-717 Safe Mail Delivery Routing Evidence

Date: 2026-06-18

## Summary

- `services/task-worker` now routes auth/system email through cyber-vpn.net SMTP as the primary provider outside `EMAIL_DEV_MODE`.
- Resend remains available only for explicit resend/fallback tasks when `EMAIL_RESEND_FALLBACK_ENABLED=true` and `RESEND_API_KEY` is present.
- Password reset, growth notification, and growth reporting email jobs use SMTP primary outside dev mode.
- Production settings fail closed when SMTP host, TLS mode, auth username/password, sender domains, or optional Resend fallback prerequisites are missing.
- Billing/support sender identities are represented as runtime env sender strings: `SMTP_BILLING_FROM_EMAIL` and `SMTP_SUPPORT_FROM_EMAIL`; no mailbox passwords or production secrets are committed.

## Routing Policy

- Dev/test route: `EMAIL_DEV_MODE=true` uses Mailpit `SMTP_SERVERS` round-robin.
- Primary production route: `smtp` via `SMTP_HOST`, `SMTP_PORT`, `SMTP_STARTTLS` or `SMTP_USE_SSL`, `SMTP_AUTH_USERNAME`, and `SMTP_AUTH_PASSWORD`.
- Explicit fallback route: `resend` only when the task has `is_resend=true` and `EMAIL_RESEND_FALLBACK_ENABLED=true`.
- Automatic provider fallback after SMTP send failure was not added, to avoid duplicate OTP/magic-link/password-reset sends when provider acceptance state is uncertain.

## Production Hotfix Notes

Date: 2026-06-19

- Production `cybervpn-worker` failed closed when required SMTP auth env was missing after this routing change.
- The rented production app host could not reach `mail.cyber-vpn.net` on standard SMTP submission ports, while the mail server itself was healthy.
- Production now uses `SMTP_PORT=2587`, documented in `docs/runbooks/PRODUCTION_AUTH_EMAIL_DELIVERY_RUNBOOK.md`.
- The mail server exposes `2587` through the committed systemd socket-proxy units in `infra/mail/stalwart-submission-alt.socket` and `infra/mail/stalwart-submission-alt.service`.
- No mailbox passwords, SMTP credentials, OTP codes, or customer mailbox contents are committed.

## Context7 Docs Checked

- Context7 MCP result: monthly quota exceeded.
- Fallback `ctx7` docs checked:
  - `/pydantic/pydantic-settings`: `BaseSettings`, `SettingsConfigDict`, validators, `NoDecode`.
  - `/websites/python-httpx`: `AsyncClient` context manager, `post(..., json=...)`, response status/json access.
  - `/redis/redis-py`: `Redis.from_url`, async close, `set` with `nx`/`ex`, `get`, `delete`.
- Python stdlib SMTP behavior checked against official Python docs for `smtplib`.

## Verification

## Transferable Patch

- Patch artifact: `docs/evidence/cyba-717/cyba-717-smtp-routing.patch`
- Scope: SMTP primary routing, explicit Resend fallback gating, production SMTP validation, auth email payload indirection, privacy-safe recipient logging, and focused tests/evidence.
- Exact requested controller base check could not be performed in this runner: `/home/beep/projects/VPNBussiness` is absent, local clones do not contain commit `3ea3da9c93eb3560073265505cf6cf4c5308870f`, and `git fetch origin --prune` cannot authenticate to `https://gitlab.h.cyber-vpn.net/root/CyberVPN.git` from this environment.
- Best available transfer check: `git apply --check docs/evidence/cyba-717/cyba-717-smtp-routing.patch` in a clean temporary worktree from local `HEAD` `f8e1c6cda7b66e0edca1056b04c5b13d09f64ce0`.
- Best available transfer check result: passed in `/tmp/cyba-717-apply-check.Wi8jgE`.

```bash
PYTHONPATH=services/task-worker REMNAWAVE_API_TOKEN=test-remnawave-token TELEGRAM_BOT_TOKEN=123:test-telegram-token CRYPTOBOT_TOKEN=test-cryptobot-token METRICS_PROTECT=false services/task-worker/.venv/bin/python -m pytest services/task-worker/tests/test_stage1_cryptobot_sandbox_config.py services/task-worker/tests/unit/tasks/test_email_metrics.py services/task-worker/tests/unit/test_email_clients.py services/task-worker/tests/unit/tasks/test_growth_notification_email_deliveries.py services/task-worker/tests/unit/tasks/test_growth_reporting_distribution.py services/task-worker/tests/unit/tasks/test_email_payloads.py -q
```

Result: `49 passed in 1.10s`

```bash
PYTHONPATH=services/task-worker REMNAWAVE_API_TOKEN=test-remnawave-token TELEGRAM_BOT_TOKEN=123:test-telegram-token CRYPTOBOT_TOKEN=test-cryptobot-token METRICS_PROTECT=false /srv/paperclip/data/instances/default/projects/b412bbf0-42d3-4803-913b-15951083d2fb/55092778-1c70-4f8a-aa61-869c6d0f33ae/_default/VPNBussiness-main/services/task-worker/.venv/bin/python -m pytest services/task-worker/tests/test_stage1_cryptobot_sandbox_config.py services/task-worker/tests/unit/tasks/test_email_metrics.py services/task-worker/tests/unit/test_email_clients.py services/task-worker/tests/unit/tasks/test_growth_notification_email_deliveries.py services/task-worker/tests/unit/tasks/test_growth_reporting_distribution.py services/task-worker/tests/unit/tasks/test_email_payloads.py -q
```

Result from patch-applied clean worktree: `49 passed in 1.29s`

```bash
/home/beep/.local/bin/ruff check backend/src/infrastructure/tasks/email_task_dispatcher.py backend/tests/unit/infrastructure/tasks/test_email_task_dispatcher.py services/task-worker/src/config.py services/task-worker/src/services/email/privacy.py services/task-worker/src/services/email/routing.py services/task-worker/src/services/email/smtp_client.py services/task-worker/src/services/email/resend_client.py services/task-worker/src/services/email/brevo_client.py services/task-worker/src/services/email/templates.py services/task-worker/src/tasks/email/payloads.py services/task-worker/src/tasks/email/send_otp.py services/task-worker/src/tasks/email/send_magic_link.py services/task-worker/src/tasks/email/send_password_reset.py services/task-worker/src/tasks/email/process_growth_notification_deliveries.py services/task-worker/src/tasks/email/process_growth_reporting_deliveries.py services/task-worker/tests/conftest.py services/task-worker/tests/test_stage1_cryptobot_sandbox_config.py services/task-worker/tests/unit/tasks/test_email_metrics.py services/task-worker/tests/unit/tasks/test_email_payloads.py services/task-worker/tests/unit/test_email_clients.py
```

Result: `All checks passed!`

```bash
REMNAWAVE_API_TOKEN=test-remnawave-token TELEGRAM_BOT_TOKEN=123:test-telegram-token CRYPTOBOT_TOKEN=test-cryptobot-token METRICS_PROTECT=false /srv/paperclip/data/instances/default/projects/b412bbf0-42d3-4803-913b-15951083d2fb/55092778-1c70-4f8a-aa61-869c6d0f33ae/_default/VPNBussiness-main/backend/.venv/bin/python -m pytest backend/tests/unit/infrastructure/tasks/test_email_task_dispatcher.py -q
```

Result: test assertions passed, but isolated run failed on global coverage threshold: `Coverage failure: total of 47 is less than fail-under=70`.

```bash
REMNAWAVE_API_TOKEN=test-remnawave-token TELEGRAM_BOT_TOKEN=123:test-telegram-token CRYPTOBOT_TOKEN=test-cryptobot-token METRICS_PROTECT=false /srv/paperclip/data/instances/default/projects/b412bbf0-42d3-4803-913b-15951083d2fb/55092778-1c70-4f8a-aa61-869c6d0f33ae/_default/VPNBussiness-main/backend/.venv/bin/python -m pytest backend/tests/unit/infrastructure/tasks/test_email_task_dispatcher.py -q --no-cov
```

Result from patch-applied clean worktree: `2 passed`

## Rollback Path

- Revert `services/task-worker/src/services/email/routing.py` and the task selectors to restore the previous API-provider routing.
- Keep `CYBA-739` payload/log/token hardening intact unless SecurityEngineer explicitly approves a rollback.
- Do not restore query-string OTP/token URLs or secret-bearing SMTP headers.

## Not Done

- No production SMTP credentials were requested, read, changed, tested, printed, or committed.
- No production deployment was performed.
- No real customer, payment, or mailbox data was used.
