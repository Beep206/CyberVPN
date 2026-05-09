# Stage 1 Support Ticket Path Evidence

> Date: 2026-05-04
> Backlog ID: `S1-SUP-001`
> Scope: Telegram/email/web/bot support-ticket routing contract, public support contact alignment, local test-ticket proof
> Status: local evidence complete; real deployed mailbox, web delivery, Telegram bot and admin queue/alert/SLA evidence remain required before S1 go-live

## Purpose

`S1-SUP-001` proves that Stage 1 has a controlled support-ticket path before paid beta:

- Telegram Bot and Telegram Mini App support intake can map into the same support categories;
- web contact path has an explicit S1 support profile;
- `support@cyber-vpn.net` and `refund@cyber-vpn.net` are the canonical public intake addresses;
- each ticket gets a safe reference, target queue, target contact, priority and SLA;
- user-provided support text is redacted before it can become admin/support evidence;
- no paid helpdesk, LLM or external server is required for this local implementation step.

This task does not claim that public mailboxes or deployed web delivery are live. Those remain go-live blockers until real inbound/outbound tests exist.

## Implemented Contract

| Support intake | S1 behavior |
|---|---|
| Telegram Bot | Existing `/support <question>` and `/paysupport <question>` first-line triage can create backend support staff-note escalation |
| Telegram Mini App | Covered by shared ticket contract as `telegram_mini_app`; live Mini App UX evidence remains open |
| Web ticket/contact | Public support profile now points to `/contact`, `support@cyber-vpn.net`, `refund@cyber-vpn.net` and `<=12h beta first response` |
| Support email | `support_email` intake maps to customer support or finance review depending on category |
| Refund/payment email | `refund_email` intake maps payment/refund issues to `s1_payment_finance_review` |
| Admin manual | `admin_manual` intake can create a safe internal support note/reference |

## Ticket Priority Rules

| Category | Priority | Queue | Contact | SLA |
|---|---|---|---|---|
| `legal_abuse` | `p0` | `s1_owner_legal_abuse` | `support@cyber-vpn.net` | ack <=15m, customer first response <=12h |
| `failed_payment` | `p1` | `s1_payment_finance_review` | `refund@cyber-vpn.net` | ack <=60m, customer first response <=12h |
| `refund_request` | `p1` | `s1_payment_finance_review` | `refund@cyber-vpn.net` | ack <=60m, customer first response <=12h |
| `paid_no_access` | `p1` | `s1_paid_no_access_review` | `support@cyber-vpn.net` | ack <=60m, customer first response <=12h |
| `vpn_not_connecting` | `p2` | `s1_vpn_connectivity_support` | `support@cyber-vpn.net` | customer first response <=12h |
| `expired_subscription` | `p2` | `s1_customer_support` | `support@cyber-vpn.net` | customer first response <=12h |
| `account_access` | `p2` | `s1_customer_support` | `support@cyber-vpn.net` | customer first response <=12h |
| `general` | `p3` | `s1_customer_support` | `support@cyber-vpn.net` | customer first response <=12h |

## Test Ticket Examples

| Scenario | Safe reference | Queue | Safe summary |
|---|---|---|---|
| Web paid-but-no-access | `s1sup-web-p1-43ed16eae411` | `s1_paid_no_access_review` | `I paid but got no access. My config is [vpn-config-url] and dashboard URL is [url]` |
| Refund email | `s1sup-refund-p1-4ccaeff8cbbd` | `s1_payment_finance_review` | `Money was debited but provider is still pending. Contact [email]` |
| Telegram VPN connectivity | `s1sup-tg-p2-ecc3eaff7130` | `s1_vpn_connectivity_support` | `Android cannot connect after renewal.` |

These are deterministic local test-ticket references generated from redacted fixture inputs. They are not live customer tickets.

## Repository Changes

Backend:

- `backend/src/presentation/api/shared/stage1_support_ticket_path.py`
  - added S1 support channels, categories, priorities, SLA constants and routing decisions;
  - added support-safe redaction for VPN config URLs, HTTP URLs, email addresses, Telegram token-like values and long secrets;
  - added deterministic test-ticket reference generation;
  - added staff-note/API serialization helpers that exclude raw customer/provider identifiers.
- `backend/src/presentation/api/shared/__init__.py`
  - exported the S1 support ticket contract for future API/admin/support integrations.

Frontend:

- `frontend/src/shared/lib/official-support-routing.ts`
  - updated canonical support email to `support@cyber-vpn.net`;
  - added `refund@cyber-vpn.net`;
  - updated beta response window to `<=12h beta first response`;
  - made `/contact`, `/help` and `https://t.me/cybervpn_bot` explicit entrypoints.
- `frontend/src/widgets/official-support-routing-panel.tsx`
  - renders support email, refund/payment email, web ticket, help center, Telegram bot and legal links from the same official support profile.

Tests:

- `backend/tests/security/test_stage1_support_ticket_path.py`
  - covers web, support email, refund email, Telegram Bot, Telegram Mini App and admin manual ticket paths;
  - covers P0/P1/P2 priority mapping and SLA;
  - covers redaction and stable reference generation.
- `frontend/src/shared/lib/__tests__/official-support-routing.test.ts`
  - covers S1-approved public support contacts and entrypoints.

## Local Evidence Commands

Backend lint:

```bash
cd backend
uv run ruff check src/presentation/api/shared/__init__.py src/presentation/api/shared/stage1_support_ticket_path.py tests/security/test_stage1_support_ticket_path.py
```

Result:

```text
All checks passed!
```

Backend support-ticket tests:

```bash
cd backend
uv run pytest tests/security/test_stage1_support_ticket_path.py -q --no-cov
```

Result:

```text
9 passed
```

Frontend support profile test:

```bash
cd frontend
npm run test:run -- src/shared/lib/__tests__/official-support-routing.test.ts
```

Result:

```text
Test Files  1 passed (1)
Tests  2 passed (2)
```

Frontend support profile lint:

```bash
cd frontend
npm run lint -- src/shared/lib/official-support-routing.ts src/shared/lib/__tests__/official-support-routing.test.ts src/widgets/official-support-routing-panel.tsx
```

Result:

```text
Passed
```

Security/dependency checks:

```bash
cd backend && uv run pip check
cd backend && uvx pip-audit --progress-spinner off
cd frontend && npm audit --omit=dev
```

Result:

```text
backend pip check: No broken requirements found.
backend pip-audit: No known vulnerabilities found.
frontend npm audit: existing moderate PostCSS advisory via Next.js; `npm audit fix --force` would install next@9.3.3, so it was not applied.
```

## What This Closes

| Item | Status |
|---|---|
| `S1-SUP-001` local Telegram/email/web/bot support-ticket path | Closed locally |
| S1 support contacts aligned to `cyber-vpn.net` | Closed locally |
| Deterministic support reference and queue/SLA mapping | Closed locally |
| Support redaction for configs, URLs, emails, bot tokens and long secrets | Closed locally |
| No-cost/no-server implementation requirement | Closed locally |

## Remaining Evidence Before Go-Live

| Evidence | Status |
|---|---|
| Real inbound and outbound `support@cyber-vpn.net` mailbox test | Open |
| Real inbound and outbound `refund@cyber-vpn.net` mailbox test | Open |
| Deployed web contact/ticket path delivery proof | Open |
| Live Telegram bot support transcript with backend/admin visibility | Open |
| Admin support queue/timeline proof for created ticket/staff note | Open |
| P0/P1 alert delivery to Telegram alert channel and backup email | Open |
| Human acknowledgement proof for P0 <=15m, P1 <=1h and beta first response <=12h | Open |
| Full escalation process evidence from support to finance/ops/owner | Open under `S1-SUP-003` |

## Security Notes

- No production mailbox credential, bot token, provider credential, VPN config or user secret was added.
- Support summaries redact VPN config URLs, HTTP URLs, email addresses, Telegram token-like values and long secret-like values.
- Ticket references are hashes of sanitized routing inputs and do not expose raw provider payment IDs.
- Docker was not started for this task.
- Owner/legal text approval for public support copy is closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; deployed mailbox/web/bot/admin queue proof remains tracked separately.

## Source Notes

| Source | Use |
|---|---|
| Vitest `describe` API: <https://vitest.dev/api/describe> | Confirmed current test-suite API pattern |
| Vitest `expect` API: <https://vitest.dev/api/expect> | Confirmed assertion API used in frontend support profile tests |
| next-intl navigation docs: <https://next-intl.dev/docs/routing/navigation> | Confirmed localized `Link` navigation pattern for support/help/legal links |

## Next ID

Next ID to execute: `S1-SUP-002` - support templates.
