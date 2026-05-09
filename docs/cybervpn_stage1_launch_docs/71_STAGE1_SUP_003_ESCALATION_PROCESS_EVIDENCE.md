# Stage 1 Support Escalation Process Evidence

> Date: 2026-05-05
> Backlog ID: `S1-SUP-003`
> Scope: support/AI -> finance/ops/owner escalation process for Controlled Public Beta
> Status: local runbook contract and tests complete; deployed admin queue, alert delivery and human SLA acknowledgement evidence remain required before S1 go-live

## Purpose

`S1-SUP-003` closes the local runbook gate for Stage 1 support escalation.

The goal is to make escalation operationally deterministic:

- AI/bot and first-line support can classify a user issue without inventing a new path;
- payment/refund cases route to finance;
- paid-but-no-access, provisioning failures and VPN/node incidents route to ops;
- legal/abuse/account-conflict/emergency cases route to owner;
- P0 and P1 cases carry explicit acknowledgement SLA;
- every escalation creates a ticket/staff note or audit trail;
- support never requests passwords, 2FA/TOTP codes, full card numbers, CVV/CVC, raw QR codes, raw subscription URLs or raw config files.

## S1 Owners and Alert Destinations

| Item | Value |
|---|---|
| Primary on-call/support owner | `@Sasha_Beep` |
| Backup on-call/support owner | `@Sasha_Beep` |
| Private Telegram alert channel | `-5173727789` |
| Backup alert email | `backup@cyber-vpn.net` |
| Support email | `support@cyber-vpn.net` |
| Refund/support email | `refund@cyber-vpn.net` |

Single-person coverage remains an accepted S1 risk only if owner records that acceptance in the go-live decision.

## Escalation Rule Catalog

| Trigger | Category | Path | Target | Priority | Queue | Ack SLA |
|---|---|---|---|---|---|---:|
| `general_support` | `general` | AI -> Support | Support | P3 | `s1_customer_support` | n/a |
| `failed_payment` | `failed_payment` | AI -> Support -> Finance | Finance | P1 | `s1_payment_finance_review` | 60m |
| `refund_request` | `refund_request` | AI -> Support -> Finance | Finance | P1 | `s1_payment_finance_review` | 60m |
| `paid_no_access` | `paid_no_access` | AI -> Support -> Ops | Ops | P1 | `s1_paid_no_access_review` | 60m |
| `paid_no_access_over_24h` | `paid_no_access` | Support -> Ops -> Owner | Owner | P0 | `s1_paid_no_access_review` | 15m |
| `provisioning_failure` | `paid_no_access` | Support -> Ops | Ops | P1 | `s1_paid_no_access_review` | 60m |
| `remnawave_or_node_outage` | `vpn_not_connecting` | Support -> Ops -> Owner | Ops | P0 | `s1_ops_incident` | 15m |
| `vpn_connectivity_incident` | `vpn_not_connecting` | AI -> Support -> Ops | Ops | P2 | `s1_vpn_connectivity_support` | n/a |
| `expired_subscription_stuck` | `expired_subscription` | AI -> Support | Support | P2 | `s1_customer_support` | n/a |
| `account_access_conflict` | `account_access` | AI -> Support -> Owner | Owner | P1 | `s1_owner_account_access` | 60m |
| `legal_abuse_request` | `legal_abuse` | Support -> Owner | Owner | P0 | `s1_owner_legal_abuse` | 15m |
| `emergency_kill_switch` | `legal_abuse` | Ops -> Owner | Owner | P0 | `s1_owner_emergency` | 15m |

All categories share the S1 customer first-response target: 12 hours.

## Critical Rules

| Rule | S1 behavior |
|---|---|
| Paid but no access | P1 to ops; check final payment state, provisioning state and Remnawave user/subscription; retry or manually recover only after safe verification |
| Paid but no access older than 24h | P0 owner escalation; must resolve access, refund/manual grant decision or pause affected flow if systemic |
| Failed payment | P1 to finance; do not mark paid from screenshot only; verify provider final status |
| Refund request | P1 to finance; do not promise guaranteed or automatic refund; decision depends on final Refund Policy and provider capability |
| Remnawave/node outage | P0 ops incident with owner path; pause trial/payment/provisioning if needed |
| Account access conflict | P1 owner review; no silent account merge |
| Legal/abuse | P0 owner review; preserve audit trail; no private data disclosure without owner/legal approval |
| Emergency kill switch | P0 owner path; owner can pause registration, payments, trial, provisioning or initiate rollback |

## Repository Changes

Backend:

- `backend/src/presentation/api/shared/stage1_support_escalation.py`
  - added stable escalation owners: `ai_first_line`, `support`, `finance`, `ops`, `owner`;
  - added stable triggers for payment, refund, paid-no-access, provisioning, Remnawave/node outage, VPN connectivity, account access, legal/abuse and emergency kill switch;
  - added machine-readable runbook rules with queue, contact, target owner, priority, SLA, required actions, forbidden actions, audit and alert flags;
  - added safe decision serialization tied to support ticket reference, without user-provided text or provider payloads.
- `backend/src/presentation/api/shared/__init__.py`
  - exports escalation constants, rules and helpers for future admin/support/API integration.

Tests:

- `backend/tests/security/test_stage1_support_escalation.py`
  - proves rule coverage and category mapping;
  - proves finance/ops/owner routing;
  - proves paid-no-access becomes P0 after 24h;
  - proves Remnawave/node outage is a P0 ops incident with owner path and kill-switch permission;
  - proves account/legal cases require owner review and audit;
  - proves support templates match default escalation rules;
  - proves escalation decisions serialize only ticket reference and rule metadata, not user text.

Docs:

- `09_STAGE1_LEGAL_SUPPORT_OPERATIONS.md`
  - expanded support escalation process with owners, queues, SLA and critical escalation rules.
- `11_STAGE1_REVIEW_CHECKLIST.md`
  - marks local support escalation process as tested.
- `19_STAGE1_TECH_DEBT_REGISTER.md`
  - records remaining deployed support escalation/alert evidence debt.

## Local Evidence Commands

Backend lint:

```bash
cd backend
uv run ruff check src/presentation/api/shared/__init__.py src/presentation/api/shared/stage1_support_escalation.py tests/security/test_stage1_support_escalation.py
```

Result:

```text
All checks passed!
```

Backend escalation tests:

```bash
cd backend
uv run pytest tests/security/test_stage1_support_escalation.py -q --no-cov
```

Result:

```text
9 passed
```

Combined support contract tests:

```bash
cd backend
uv run pytest tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_templates.py tests/security/test_stage1_support_escalation.py -q --no-cov
```

Result:

```text
29 passed
```

Dependency checks:

```bash
cd backend && uv run pip check
cd backend && uvx pip-audit --progress-spinner off
```

Result:

```text
pip check: No broken requirements found.
pip-audit: No known vulnerabilities found.
```

## What This Closes

| Item | Status |
|---|---|
| `S1-SUP-003` local escalation runbook contract | Closed locally |
| AI/support -> finance payment/refund path | Closed locally |
| AI/support -> ops paid-no-access/provisioning/VPN path | Closed locally |
| Support/ops -> owner legal/abuse/account/emergency path | Closed locally |
| P0/P1 SLA mapping for escalation rules | Closed locally |
| Sensitive-data guardrails for escalation rules | Closed locally |
| Template -> escalation queue/contact consistency | Closed locally |

## Remaining Evidence Before Go-Live

| Evidence | Status |
|---|---|
| Deployed support/admin queue showing escalation ownership and staff-note visibility | Open |
| P0/P1 Telegram alert delivery to `-5173727789` | Open |
| Backup alert email delivery to `backup@cyber-vpn.net` | Open |
| Human acknowledgement evidence: P0 <=15m, P1 <=1h, beta first response <=12h | Open |
| Live paid-but-no-access case through admin/support queue, audit log and ops resolution path | Open before paid beta |
| Live support/refund mailbox evidence using `support@cyber-vpn.net` and `refund@cyber-vpn.net` | Open |
| Owner go-live acceptance of single-person on-call/support coverage or assignment of separate backup | Open |

## Security Notes

- No production alert token, mailbox credential, provider credential, bot token, VPN config or user secret was added.
- Escalation decisions serialize ticket reference and static runbook metadata only; they do not include user-provided message text.
- Every escalation rule forbids requesting passwords, 2FA/TOTP codes, full card numbers, CVV/CVC, raw QR codes, raw subscription URLs or raw config files.
- Legal/abuse and account-access cases require owner review and audit trail.
- Docker was not started for this task.

## Next ID

Next ID to execute: `S1-FE-010` - Frontend bundle/env scan. Legal/text work is closed by `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
