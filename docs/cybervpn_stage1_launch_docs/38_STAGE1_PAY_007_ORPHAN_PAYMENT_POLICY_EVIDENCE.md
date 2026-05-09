> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-08
> Backlog ID: `S1-PAY-007`
> Статус: local orphan payment / paid-but-no-access policy, SLA thresholds and dashboard proof completed and revalidated; real admin/support queue and alert delivery evidence remain required before paid beta.

# S1-PAY-007 Orphan Payment Policy Evidence

## Purpose

Этот документ фиксирует `S1-PAY-007`: paid-but-no-access and orphan payments must become explicit support/reconciliation items, and no unresolved orphan/paid-but-no-access case may be older than 24 hours during S1 Controlled Public Beta.

S1 rule:

```text
No unresolved paid-but-no-access or orphan payment may be older than 24 hours.
15 minutes -> alert.
1 hour -> P1 support/ops escalation.
24 hours -> P0 launch blocker until resolved or explicitly accepted by owner.
```

This is a no-cost local implementation gate. It does not create the final production admin queue, and it does not prove real Telegram/email alert delivery.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-006`. No runtime code changes were required; the existing policy, support/admin serialization and integration contracts still match the S1 owner rule.

## Implementation

Added:

```text
backend/src/presentation/api/shared/stage1_orphan_payment_policy.py
backend/tests/security/test_stage1_orphan_payment_policy.py
```

Updated:

```text
backend/src/presentation/api/shared/__init__.py
```

The policy exposes:

- `Stage1PaymentAccessSnapshot`;
- `Stage1OrphanPaymentReason`;
- `Stage1OrphanPaymentSlaState`;
- `Stage1OrphanPaymentAction`;
- `Stage1OrphanPaymentDecision`;
- `Stage1OrphanPaymentQueueSummary`;
- `evaluate_stage1_orphan_payment`;
- `summarize_stage1_orphan_payment_queue`;
- `STAGE1_ORPHAN_ALERT_AFTER_MINUTES = 15`;
- `STAGE1_ORPHAN_P1_AFTER_MINUTES = 60`;
- `STAGE1_ORPHAN_P0_AFTER_MINUTES = 1440`.

## Covered Scenarios

| Scenario | S1 decision |
|---|---|
| Payment paid and VPN access ready | No manual review |
| Payment paid, user not found | `orphan_review_required`; create manual review item; alert support/finance; do not silently create account |
| Payment paid, order not found | `orphan_review_required`; create manual review item; alert support/finance; do not silently create account |
| Payment paid, provisioning failed | Preserve `paid`; set provisioning to `retrying`; queue provisioning retry |
| Payment paid, Remnawave unavailable | Preserve `paid`; set provisioning to `remnawave_unavailable`; escalate by SLA |
| Payment paid, amount/currency mismatch | `reconciliation_required`; block automatic access; reconcile provider dashboard |
| Provider final success after CyberVPN timeout | Preserve `paid`; reopen reconciliation; queue provisioning retry |
| User reports debit but provider state is non-final | Create support ticket; reconcile via provider dashboard/API |

## SLA Behavior

| Age of unresolved item | S1 state | Required action |
|---:|---|---|
| `<15m` | `manual_review` | Create manual review item |
| `>=15m` | `alert_15m` | Send paid-without-access alert |
| `>=1h` | `p1_escalation` | Escalate support/ops |
| `>=24h` | `p0_blocker` | Block launch/paid beta continuation until resolved or accepted by owner |

## Safety Rules

- Raw provider payment ids and internal payment ids are not serialized in policy output.
- API/admin/support output uses a hashed `safe_reference`.
- Paid state is preserved when VPN provisioning fails.
- Orphan user/order cases never silently create accounts.
- Amount/currency mismatch never grants automatic access by default.
- Queue summary exposes aggregate counts for dashboards/alerts.

## Local Evidence Summary

| Check | Result |
|---|---|
| Paid + VPN ready does not require manual review | Passed |
| Paid + user missing becomes orphan review | Passed |
| Paid + order missing becomes orphan review | Passed |
| Paid + provisioning failed preserves paid and queues retry | Passed |
| Paid + Remnawave unavailable escalates by SLA | Passed |
| Amount/currency mismatch blocks automatic access | Passed |
| Provider final success after timeout reopens reconciliation | Passed |
| User-reported debit with non-final provider state creates support ticket | Passed |
| 15m / 1h / 24h thresholds are explicit | Passed |
| Serialization redacts raw payment ids | Passed |
| ASGI dashboard summary marks 24h unresolved item as launch-blocking | Passed |

## Targeted Test Result

```text
backend/tests/security/test_stage1_orphan_payment_policy.py ............... [100%]
15 passed in 0.05s
```

## Broader Regression Result

```text
66 passed in 0.44s
```

The 2026-05-08 broader regression covered:

- orphan payment policy;
- payment reconciliation job;
- payment webhook -> provisioning failure handling;
- webhook idempotency;
- support ticket path;
- support escalation;
- admin payment-attempt safe view.

## What This Closes

| Item | Status |
|---|---|
| `S1-PAY-007` local orphan payment policy | Closed locally |
| 15m / 1h / 24h SLA thresholds | Closed locally |
| Manual review state mapping | Closed locally |
| Paid-but-no-access dashboard summary contract | Closed locally |
| Raw payment id redaction for support/admin output | Closed locally |

## What Remains Open

| Item | Why still open |
|---|---|
| Real admin/support queue | Local ticket reference/queue/SLA contract exists in `69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`; production admin/support workflow evidence remains open |
| Real alert delivery | Needs Telegram alert channel and backup email delivery evidence |
| Audit log samples | Needs role-gated admin/support resolution flow |
| Provider dashboard/API reconciliation | Requires real provider accounts/credentials |
| Provisioning retry integration | Local retry contract completed in `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md`; local payment webhook -> retry orchestration completed in `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`; durable/live provider/staging evidence remains open |

## 2026-05-08 Verification

| Check | Result |
|---|---|
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_orphan_payment_policy.py -q --no-cov` | PASS: 15 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_orphan_payment_policy.py tests/security/test_stage1_payment_reconciliation_job.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_admin_payment_attempts_view.py -q --no-cov` | PASS: 66 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_orphan_payment_policy.py tests/security/test_stage1_orphan_payment_policy.py` | PASS |
| Policy output redaction | PASS: tests prove raw provider/internal payment ids do not serialize |
| Dashboard/feature proof | PASS: ASGI orphan dashboard marks 24h unresolved item as launch-blocking |
| Integration proof | PASS: reconciliation and payment-provisioning failure tests use the S1 orphan policy |
| Stale next-step scan for `S1-PAY-007` as current next ID | PASS: no matches |
| `git diff --check -- <S1-PAY-007 touched files>` | PASS |
| Trailing whitespace scan over touched files | PASS |
| Secret scan over touched files | PASS after excluding explicit redacted placeholders and documentation terms |
| Static dangerous-pattern scan over touched files | PASS |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain tracked outside this task |
| Backend `pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| Running containers after task | PASS: no task containers started |

## Security Review Notes

- S1 output uses `safe_reference` hashes instead of raw provider payment ids or internal payment ids.
- Orphan user/order cases do not silently create accounts.
- Amount/currency mismatch blocks automatic access until reconciliation.
- Paid state is preserved when provisioning fails; retry/support escalation is used instead of losing payment state.
- This task did not start Docker containers or require external provider credentials.

## Next ID

Next ID superseded by `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## Regeneration Command

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL='postgresql+asyncpg://<redacted>' \
REDIS_URL='redis://localhost:6379/15' \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder-32-plus-chars>' \
JWT_REFRESH_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_orphan_payment_policy.py \
  -q --no-cov
```
