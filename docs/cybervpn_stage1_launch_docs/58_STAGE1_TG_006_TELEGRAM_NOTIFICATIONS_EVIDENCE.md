# 58. Stage 1 Evidence - S1-TG-006 Telegram Notifications

Date: 2026-05-04

Backlog ID: `S1-TG-006`

Status: completed locally for the Stage 1 notification contract and queue delivery path. Real BotFather token, webhook/polling, deployed HTTPS and live Telegram client evidence remain required before S1 go-live.

## Objective

Prove that customer-critical Telegram notifications for Controlled Public Beta can be queued and delivered where Telegram is enabled:

- subscription expiry warning and expired access;
- payment received and payment failed;
- VPN provisioning ready and provisioning delayed/failed;
- disabled or unlinked Telegram channel does not create a queue row;
- dynamic values in HTML-mode Telegram messages are escaped;
- existing `notification_queue` processor can deliver S1 notification rows through `TelegramClient`.

## Official Docs Checked

| Surface | Source |
|---|---|
| Telegram Bot API message delivery and HTML parse mode surface | https://core.telegram.org/bots/api |

## Implemented Policy

| Rule | Local implementation |
|---|---|
| S1 notification set is explicit | `STAGE1_TELEGRAM_NOTIFICATION_TYPES` contains only expiry, payment and provisioning events |
| "Where enabled" is fail-closed | Builder returns `None` when Telegram notifications are disabled or user has no linked `telegram_id` |
| Invalid Telegram destination is rejected | Non-positive `telegram_id` raises `ValueError` before queue row creation |
| Queue is source of delivery | `Stage1TelegramNotification.to_queue_model()` writes `pending` `NotificationQueueModel` rows |
| Provisioning messages do not expose raw config links | `provisioning_ready` points user to CyberVPN cabinet; QR/subscription URL/config is retrieved inside the app |
| User-controlled fields are HTML escaped | Username, plan, reason, support ref, URLs and expiry display fields are escaped before Telegram HTML delivery |
| Delivery processor remains central | Existing `process_notification_queue` sends S1 rows through `TelegramClient.send_message` and marks rows `sent`/retryable |

## Repository Changes

Task-worker runtime:

- `services/task-worker/src/tasks/notifications/stage1_contract.py`
  - added queue-ready S1 notification contract and builder;
  - added enabled/unlinked-user fail-closed behavior;
  - added required-field validation for expiry and payment events.
- `services/task-worker/src/utils/constants.py`
  - added `provisioning_ready` and `provisioning_failed` notification type constants.
- `services/task-worker/src/utils/formatting.py`
  - added provisioning-ready and provisioning-failed Telegram templates;
  - added HTML escaping for customer-critical subscription/payment/provisioning templates.
- `services/task-worker/src/tasks/notifications/__init__.py`
  - exported the S1 notification contract helpers.

Tests:

- `services/task-worker/tests/test_stage1_telegram_notifications.py`
  - covers notification type allowlist, disabled/unlinked gating, queue model conversion, HTML escaping, required-field validation and queue processor delivery.

No real Telegram token, BotFather call, webhook call, Remnawave call or payment provider call was used.

## Evidence Matrix

| Flow | Proof |
|---|---|
| Expiry warning | Builder creates `subscription_expiring` queue row with scheduled delivery |
| Expired subscription | Builder creates `subscription_expired` queue row |
| Payment success | Builder creates `payment_received` queue row and validates `amount` + plan duration |
| Payment failure | Builder creates `payment_failed` queue row with escaped reason |
| Provisioning ready | Builder creates `provisioning_ready` queue row without raw VPN config in Telegram |
| Provisioning delayed/failed | Builder creates `provisioning_failed` queue row with support reference/retry hint |
| Disabled notifications | Builder returns `None` when `enabled=false` |
| No linked Telegram | Builder returns `None` when `telegram_id=None` |
| Invalid Telegram ID | Builder raises `ValueError` for non-positive IDs |
| Queue processor | Existing processor sends S1 queue row and marks it `sent` |

## Local Evidence Commands

Task-worker component and queue delivery suite:

```bash
cd services/task-worker
uv run pytest tests/test_stage1_telegram_notifications.py tests/test_notifications.py -q
```

Result:

```text
21 passed in 0.60s
```

Static check for changed task-worker files:

```bash
cd services/task-worker
uv run ruff check \
  src/tasks/notifications/stage1_contract.py \
  src/tasks/notifications/__init__.py \
  src/utils/constants.py \
  src/utils/formatting.py \
  tests/test_stage1_telegram_notifications.py \
  tests/test_notifications.py
```

Result:

```text
All checks passed!
```

Diff whitespace check:

```bash
git diff --check
```

Result:

```text
passed with no output
```

Frontend dependency audit:

```bash
cd frontend
npm audit --audit-level=high
```

Result:

```text
0 high/critical vulnerabilities. npm audit still reports 2 moderate advisories in Next's transitive PostCSS path; the suggested force fix would downgrade Next and is not applied.
```

Task-worker Python dependency audit:

```bash
cd services/task-worker
uvx pip-audit --progress-spinner off
```

Result:

```text
No known vulnerabilities found
```

Focused secret-name/value scan:

```bash
rg -n "(BOT_TOKEN|WEBHOOK_SECRET|OAUTH_CLIENT_SECRET|BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9_]{20,})" \
  services/task-worker/src/tasks/notifications \
  services/task-worker/src/utils \
  services/task-worker/tests/test_stage1_telegram_notifications.py
```

Result:

```text
Only expected dummy test env placeholders were found in `tests/test_stage1_telegram_notifications.py`; no real secret values were added.
```

Focused dangerous-pattern scan:

```bash
rg -n "\\b(eval|exec)\\s*\\(|subprocess\\.|os\\.system\\(|text\\(f\\\"|text\\(f'|\\.raw\\(|innerHTML|dangerouslySetInnerHTML" \
  services/task-worker/src/tasks/notifications/stage1_contract.py \
  services/task-worker/src/tasks/notifications/__init__.py \
  services/task-worker/src/utils/constants.py \
  services/task-worker/src/utils/formatting.py \
  services/task-worker/tests/test_stage1_telegram_notifications.py
```

Result:

```text
no matches
```

## Security Review Notes

| Check | Result |
|---|---|
| Secret handling | No real bot token, webhook secret, provider secret or Telegram initData was added |
| HTML injection | Customer-critical Telegram templates now escape dynamic values before HTML-mode delivery |
| Config leakage | Provisioning-ready notification does not place QR/subscription URL/config into Telegram text |
| Channel gating | Disabled or unlinked Telegram notifications do not create queue rows |
| Retry semantics | Existing queue processor keeps Telegram API failures retryable until max retries |
| Production side effects | Tests use local mocks only; no live Telegram/API/provider calls |
| Dependency audit | Python audit clean; frontend audit has no high/critical findings and tracks the existing moderate Next/PostCSS advisory |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| Real staging bot token stored through approved secret process | Open |
| Redacted `getMe` and webhook/polling evidence for staging bot | Open |
| Real Telegram client proof that expiry/payment/provisioning messages render correctly | Open |
| Deployed HTTPS staging proof for queue worker -> Telegram delivery | Open |
| Real alert/support escalation proof when notification delivery permanently fails | Open |
| Provider/payment webhook -> S1 payment notification integration evidence | Open |
| Remnawave provisioning success/failure -> S1 provisioning notification integration evidence | Open |
| Production smoke after RC tag | Open |

## Next ID

Next ID to execute: `S1-ADM-001` - admin domain/access protection.
