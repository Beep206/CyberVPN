# S1-PAY-012 — Reconciliation Job Evidence

Date: 2026-05-05
Scope: S1 Controlled Public Beta local/no-cost implementation evidence.

## Decision

`S1-PAY-012` is completed locally as a backend-authoritative reconciliation job plus worker scheduler hook.

The job does not enable any live provider. It scans CyberVPN's canonical payment tables and detects payment/attempt/order mismatches that must become support/finance actions before S1 paid beta can be treated as healthy.

## Implemented contract

| Area | Result |
|---|---|
| Backend reconciliation use case | Added `Stage1PaymentReconciliationUseCase` |
| Internal API | Added `POST /api/v1/payments/internal/reconciliation/run` |
| Internal auth | Protected by `X-Telegram-Bot-Secret`, same internal worker channel used by existing reconciliation hooks |
| Worker task | Added `reconcile_stage1_payments` |
| Schedule | Every 15 minutes via `SCHEDULE_STAGE1_PAYMENT_RECONCILIATION` |
| Output safety | Raw payment ids, order ids, user ids, external references, idempotency keys, provider/request snapshots and payment URLs are redacted |
| Evidence suitability | Output contains `safe_reference`, status fields, age, severity, actions and mismatch counts |

## Mismatches detected

| Code | Meaning | Action |
|---|---|---|
| `stale_active_attempt` | `pending` / `processing` attempt is older than S1 SLA threshold | Reconcile provider dashboard; notify support/finance; do not provision until final success |
| `succeeded_attempt_without_payment` | Provider attempt succeeded but no canonical `payments` row is linked | Create manual review item; preserve paid state; reconcile provider |
| `attempt_payment_status_mismatch` | Attempt and canonical payment status disagree | Reconcile provider; preserve existing access state; block duplicate provisioning |
| `order_settlement_mismatch` | Payment is completed but order settlement is not `paid` | Run/repair post-payment processing; reconcile order settlement |
| `canonical_payment_without_attempt` | Final payment row exists without canonical payment attempt/order link | Manual reconciliation; no silent account creation |
| `unknown_payment_attempt_status` | Attempt has an unknown status | Freeze side effects; manual review |
| `unknown_payment_status` | Payment has an unknown status | Freeze side effects; manual review |
| `user_mismatch` | Payment user and order user disagree | Block automatic access; reconcile identity linkage |

## SLA behavior

| Age | Severity |
|---:|---|
| `<15 minutes` | `manual_review` |
| `>=15 minutes` | `alert_15m` |
| `>=60 minutes` | `p1_escalation` |
| `>=24 hours` | `p0_blocker` |

This matches the S1 orphan-payment rule: no unresolved paid-but-no-access/orphan payment may be older than 24 hours.

## Verification

| Check | Command | Result |
|---|---|---|
| Backend lint | `cd backend && uv run ruff check src/application/use_cases/payments/stage1_reconciliation.py src/presentation/api/v1/payments/routes.py tests/security/test_stage1_payment_reconciliation_job.py` | Passed |
| Backend component/route tests | `cd backend && uv run pytest tests/security/test_stage1_payment_reconciliation_job.py -q --no-cov` | `6 passed` |
| Worker lint | `cd services/task-worker && uv run ruff check src/services/backend_api_client.py src/tasks/payments/reconcile_stage1.py src/tasks/payments/__init__.py src/schedules/definitions.py src/utils/constants.py` | Passed |
| Worker task/schedule tests | `cd services/task-worker && uv run pytest tests/test_payments.py::test_reconcile_stage1_payments_calls_internal_backend_job tests/test_payments.py::test_reconcile_stage1_payments_skips_without_backend_config tests/integration/test_schedules.py::TestScheduleRegistration::test_schedules_module_can_be_imported tests/integration/test_schedules.py::TestScheduleRegistration::test_constants_are_defined -q` | `4 passed` |
| Route boundary spot-check | Local script classified `/api/v1/payments/internal/reconciliation/run` as `header-secret-protected` | Passed for new route |

## Known unrelated test limitation

Running the broader `tests/security/test_stage1_route_boundary.py` suite currently still reports pre-existing unclassified routes outside `S1-PAY-012`:

- `PATCH /api/v1/refunds/{refund_id}`
- `POST /api/v1/payment-disputes/`
- `GET /api/v1/payment-disputes/`
- `GET /api/v1/payment-disputes/{payment_dispute_id}`
- `GET /api/v1/admin/mobile-users/{user_id}/payment-attempts`

The new reconciliation endpoint is not one of the unclassified routes.

## Remaining before paid beta/go-live

| Requirement | Why it remains open |
|---|---|
| Real provider reconciliation evidence | The local job detects internal mismatch states, but provider dashboards/API samples are still required per provider |
| Durable manual review queue evidence | The job output is actionable, but deployed support/admin queue handling still needs evidence |
| Alert delivery evidence | P0/P1 counts are emitted in report output; Telegram/email alert delivery must still be proven in staging/RC |
| Provider placeholder replacement | Local guardrail completed in `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md`; real callback/status/refund/reconciliation samples remain required per provider before enablement |

## Next ID

Next ID to execute: `S1-VPN-009` - define usage display policy before continuing VPN/customer-facing readiness work.
