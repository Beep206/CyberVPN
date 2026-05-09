# 60. Stage 1 Evidence - S1-TG-008 AI Support First Line and Escalation

Date: 2026-05-04

Backlog ID: `S1-TG-008`

Status: completed locally for Telegram Bot first-line support triage and backend support-escalation intake. Real deployed Telegram bot, live support/admin queue workflow, alert delivery and human support SLA evidence remain required before S1 go-live.

## Objective

Prove that the Telegram Bot can handle the first support message during S1 Controlled Public Beta without relying on a paid AI provider:

- user can send `/support <question>` or `/paysupport <question>`;
- bot performs deterministic first-line triage for payment, provisioning, connectivity, account, legal/abuse and general questions;
- payment/provisioning/connectivity/account/legal/abuse cases are escalated;
- general low-risk questions receive first-line guidance without creating queue noise;
- VPN config links, URLs, Telegram bot tokens and long secret-like values are redacted before support payload creation;
- backend accepts bot-created escalations through an internal Telegram bot endpoint and stores an admin-visible support staff note.

Important S1 scope note: this is not an external LLM/AI integration. It is a deterministic first-line automation layer that satisfies the no-cost S1 requirement and keeps the later AI/provider choice out of the critical path.

## Official Docs Checked

| Surface | Source |
|---|---|
| aiogram dependency injection for handler contextual data | https://docs.aiogram.dev/en/latest/dispatcher/dependency_injection.html |
| aiogram `CommandObject.args` support for command arguments | https://docs.aiogram.dev/en/latest/dispatcher/filters/command.html |
| aiogram router/async handler registration | https://docs.aiogram.dev/en/latest/dispatcher/router.html |

## Implemented Contract

| Rule | Local implementation |
|---|---|
| No paid AI dependency for S1 | `Stage1SupportTriageService` uses deterministic keyword classification |
| User support entrypoint | `/support` and `/paysupport` still show contact when no question is provided |
| First-line triage entrypoint | `/support <text>` and `/paysupport <text>` classify and answer with a safe reference |
| Escalation categories | payment, provisioning, connectivity, account, legal/abuse |
| Non-escalating first line | general beta questions return guidance plus support contact/reference |
| Sensitive data handling | config URLs, HTTP URLs, Telegram token-like values and long secrets are redacted |
| Backend escalation intake | `POST /telegram/bot/user/{telegram_id}/support/escalations` with `X-Telegram-Bot-Secret` |
| Admin visibility | backend stores a `customer_staff_notes` support note for the matched mobile user |
| Safe failure behavior | if backend escalation fails, user receives fallback reference and support contact |

## Repository Changes

Telegram bot:

- `services/telegram-bot/src/services/support_triage.py`
  - added deterministic S1 first-line triage;
  - added support-safe redaction helper;
  - added stable support reference generation.
- `services/telegram-bot/src/handlers/support.py`
  - preserved `/support` and `/paysupport` contact behavior;
  - added command-argument triage;
  - added best-effort backend escalation with fallback user response;
  - avoids logging user-provided support text.
- `services/telegram-bot/src/services/api_client.py`
  - added `create_support_escalation`.
- `services/telegram-bot/src/locales/en/messages.ftl`
  - added first-line support and escalation messages.
- `services/telegram-bot/src/locales/ru/messages.ftl`
  - added first-line support and escalation messages.

Backend:

- `backend/src/presentation/api/v1/telegram/schemas.py`
  - added bot support escalation request/response schemas.
- `backend/src/presentation/api/v1/telegram/routes.py`
  - added internal bot support-escalation endpoint;
  - stores escalation as a support staff note;
  - defensively redacts sensitive text again before note creation.

Tests:

- `services/telegram-bot/tests/unit/test_support_triage.py`
  - covers escalation classification, non-escalating general triage and redaction.
- `services/telegram-bot/tests/unit/test_handlers/test_support.py`
  - covers support contact, escalation creation, fallback and non-escalation flow.
- `services/telegram-bot/tests/unit/test_api_client.py`
  - covers bot API client support-escalation endpoint call.
- `backend/tests/integration/api/v1/telegram/test_telegram_channel_parity.py`
  - covers backend support-escalation endpoint and staff-note redaction.

## Local Evidence Commands

Telegram Bot full unit suite:

```bash
cd services/telegram-bot
.venv/bin/python -m pytest tests/unit -q
```

Result:

```text
307 passed in 28.34s
```

Backend Telegram channel parity:

```bash
cd backend
.venv/bin/python -m pytest tests/integration/api/v1/telegram/test_telegram_channel_parity.py --no-cov -q
```

Result:

```text
4 passed in 0.33s
```

Focused lint for changed Telegram Bot files:

```bash
cd services/telegram-bot
.venv/bin/python -m ruff check \
  src/handlers/support.py \
  src/services/support_triage.py \
  src/services/api_client.py \
  tests/unit/test_support_triage.py \
  tests/unit/test_handlers/test_support.py \
  tests/unit/test_api_client.py
```

Result:

```text
All checks passed!
```

Focused lint for changed backend files:

```bash
cd backend
.venv/bin/python -m ruff check \
  src/presentation/api/v1/telegram/routes.py \
  src/presentation/api/v1/telegram/schemas.py \
  tests/integration/api/v1/telegram/test_telegram_channel_parity.py
```

Result:

```text
All checks passed!
```

## What This Closes

| Item | Status |
|---|---|
| `S1-TG-008` local first-line support triage | Closed locally |
| `/support <question>` and `/paysupport <question>` triage behavior | Closed locally |
| Bot-created backend support escalation contract | Closed locally |
| Safe redaction before support note creation | Closed locally |
| Fallback support reference when backend escalation fails | Closed locally |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| Real staging Telegram bot command flow with screenshots/redacted transcript | Open |
| Deployed backend support-escalation endpoint over approved internal path | Open |
| Admin UI/support timeline proof that staff note is visible and actionable | Open |
| Alert delivery for P0/P1 support escalation | Open |
| Human support SLA acknowledgement evidence for P0/P1/beta first response | Open |
| Full `S1-SUP-001` Telegram/email/web support ticket path | Closed locally in `69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`; deployed mailbox/web/bot/admin queue/alert proof remains open |
| `S1-SUP-002` final support templates | Closed locally in `70_STAGE1_SUP_002_SUPPORT_TEMPLATES_EVIDENCE.md`; owner/legal text approval closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; provider/live workflow evidence remains open |
| `S1-SUP-003` full support -> finance/ops/owner escalation runbook evidence | Closed locally in `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`; deployed queue, alert and human SLA proof remain open |

## Security Review Notes

| Check | Result |
|---|---|
| Secret handling | No real Telegram token, provider credential, VPN config or webhook secret was added |
| User data minimization | Support notes receive redacted summaries, not raw message text |
| Logging | Handler logs only safe reference/category-level failures, not user text |
| Backend auth | Support-escalation intake requires `X-Telegram-Bot-Secret` like other bot-facing endpoints |
| Production side effects | Tests use mocks/local ASGI only; no live Telegram/provider/Remnawave calls |
| Launch scope | No external paid AI provider is required for S1 |
| Dependency audit | The two targeted Python findings discovered after this task are remediated in `61_STAGE1_DEPENDENCY_CVE_FIX_EVIDENCE.md`: bot `pip` upgraded to `26.1`, unused backend `pillow 12.1.1` removed, and bot/backend `pip-audit` now returns `No known vulnerabilities found` |

## Next ID

Next ID to execute: `S1-ADM-001` - admin domain/access protection.
