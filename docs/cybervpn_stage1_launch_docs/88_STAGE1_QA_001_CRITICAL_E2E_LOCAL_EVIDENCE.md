> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-05
> Backlog ID: `S1-QA-001`
> Статус: PASS for local/no-cost critical E2E gate. This is not staging/prod go-live evidence.

# S1-QA-001 Critical E2E Local Evidence

## Purpose

`S1-QA-001` checks that the S1 Controlled Public Beta critical path is locally coherent across backend, customer UI, Telegram Bot, worker/scheduler and admin/support surfaces.

The target journey is:

```text
register/login
-> trial or mock paid status
-> Remnawave provisioning contract
-> config/subscription/usage availability contract
-> admin/support visibility and recovery actions
-> worker/notification/reconciliation support path
```

This local gate intentionally avoids paid external infrastructure and live payment-provider calls.

## Scope Covered

| Area | Local proof |
|---|---|
| Registration/login boundary | Auth/admin route protections and S1 customer surface tests cover protected route behavior, admin host boundary and support/admin role gates |
| Trial | Trial policy and trial provisioning request/result contract passed |
| Payment | Provider final-status mapping, webhook idempotency, orphan payment, payment -> provisioning failure, reconciliation and wallet/payment-history local contracts passed |
| Provisioning | Trial, paid, retry, expiry/grace-disable and credential-regeneration provisioning contracts passed through fake/in-memory Remnawave gateways |
| Connect/config | Local proof covers config/subscription URL safe delivery contracts, usage availability/unavailability contract and previous local connected Remnawave node evidence in `25_STAGE1_VPN_012_LOCAL_REMNAWAVE_NODE_EVIDENCE.md` |
| Admin/support | Admin host protection, RBAC, 2FA, audit, manual grant, payment attempts, credential regeneration and support escalation/template/ticket paths passed |
| Telegram | Stage 1 command surface, support triage and first-line support handlers passed |
| Worker/scheduler | Payment tasks, stage1 Telegram notifications, resilience and schedules passed |

## Local QA Fixes Made During This Gate

| Finding | Resolution |
|---|---|
| Backend manual subscription route test used fixed `2026-05-04` expiry and became time-sensitive on `2026-05-05` | Updated the test to calculate a future current expiry from `datetime.now(UTC)` so the route-level extend path remains deterministic |
| Admin Vitest failed before executing tests on Node `v24.14.1` because `jsdom/cssstyle` required an ESM graph with top-level await | Aligned admin Vitest config with frontend: `pool: 'threads'`, `environment: 'happy-dom'` |
| Admin test environment attempted real runtime analytics fetches to `localhost:3000` | Added the same browser API mocks used by frontend tests: `navigator.sendBeacon` and `window.open` |
| Admin action buttons with `magnetic={false}` were still wrapped by `InceptionButton` | Changed admin `Button` so `magnetic={false}` returns the plain button, which is the expected low-motion/action-dialog behavior |
| Customer detail credential-regeneration component test was blocked by portal event limitations in the local DOM runner | The component test now uses an inline `AdminActionDialog` mock that preserves the reason-gate/confirm contract and keeps this test focused on the customer-detail action |

Vitest configuration was checked against official Vitest docs for `environment` and `pool` settings:

- <https://vitest.dev/config/environment>
- <https://main.vitest.dev/config/pool>

## Commands Executed

### Backend Critical Slice

```bash
cd backend
SKIP_TEST_DB_BOOTSTRAP=1 uv run pytest --no-cov \
  tests/security/test_stage1_trial_provisioning.py \
  tests/security/test_stage1_paid_provisioning.py \
  tests/security/test_stage1_payment_provisioning_failure.py \
  tests/security/test_stage1_provisioning_retry.py \
  tests/security/test_stage1_webhook_idempotency.py \
  tests/security/test_stage1_provider_payment_status_mapping.py \
  tests/security/test_stage1_orphan_payment_policy.py \
  tests/security/test_stage1_expiry_grace_disable.py \
  tests/security/test_stage1_credential_regeneration.py \
  tests/security/test_stage1_admin_access_protection.py \
  tests/security/test_stage1_admin_2fa_enforcement.py \
  tests/security/test_stage1_admin_rbac_matrix.py \
  tests/security/test_stage1_admin_manual_subscription_ops.py \
  tests/security/test_stage1_admin_payment_attempts_view.py \
  tests/security/test_stage1_admin_audit_log.py \
  tests/security/test_stage1_support_ticket_path.py \
  tests/security/test_stage1_support_escalation.py \
  tests/security/test_stage1_support_templates.py \
  tests/security/test_stage1_status_error_contract.py \
  tests/security/test_stage1_rate_limit_policy.py \
  -q
```

Result:

```text
218 passed in 4.71s
```

Note: the first backend run found the time-sensitive manual subscription route test described above. After the fix, the same backend critical slice passed.

### Frontend Customer and Mini App Slice

```bash
cd frontend
npm run test:run -- \
  'src/app/[locale]/miniapp/home/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/wallet/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/referral/__tests__/page.test.tsx' \
  'src/lib/api/__tests__/payments.test.ts' \
  'src/lib/api/__tests__/vpn.test.ts' \
  'src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx' \
  'src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts' \
  'src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx'
```

Result:

```text
Test Files  10 passed (10)
Tests       69 passed (69)
```

### Admin Slice

```bash
cd admin
npm run test:run -- \
  'src/features/customers/components/__tests__/customer-detail-credential-regeneration.test.tsx' \
  'src/lib/api/__tests__/customers-admin.test.ts'
```

Result:

```text
Test Files  2 passed (2)
Tests       16 passed (16)
```

### Telegram Bot Slice

```bash
cd services/telegram-bot
uv run pytest \
  tests/unit/test_stage1_surface.py \
  tests/unit/test_stage1_command_entrypoints.py \
  tests/unit/test_support_triage.py \
  tests/unit/test_handlers/test_support.py \
  -q
```

Result:

```text
21 passed in 0.31s
```

### Worker/Scheduler Slice

```bash
cd services/task-worker
uv run pytest \
  tests/test_payments.py \
  tests/test_stage1_telegram_notifications.py \
  tests/test_resilience.py \
  tests/integration/test_schedules.py \
  -q
```

Result:

```text
49 passed in 1.42s
```

### Static Checks For Files Touched During This Gate

```bash
cd backend
uv run ruff check tests/security/test_stage1_admin_manual_subscription_ops.py

cd admin
npx eslint \
  vitest.config.ts \
  src/test/setup.ts \
  src/components/ui/button.tsx \
  src/features/customers/components/__tests__/customer-detail-credential-regeneration.test.tsx
```

Result:

```text
ruff: All checks passed
eslint: passed with no output
```

### Docker Resource Check

```bash
cd infra
docker compose ps --services --filter status=running
```

Result:

```text
No running services returned
```

No containers were left running after `S1-QA-001`.

## What This Proves

| S1 path | Result |
|---|---|
| Trial -> VPN provisioning contract | PASS |
| Paid final status -> VPN provisioning contract | PASS |
| Paid webhook failure -> retry/support/orphan policy | PASS |
| Duplicate webhook side effects | PASS |
| Expiry/grace disable | PASS |
| Credential regeneration safe response | PASS |
| Customer Mini App/customer cabinet critical surfaces | PASS |
| Payment/VPN frontend API client behavior | PASS |
| Admin support visibility and recovery actions | PASS |
| Telegram command/support path | PASS |
| Worker payment/notification/schedule support path | PASS |

## What This Does Not Prove Yet

| Gap | Required later |
|---|---|
| Real registration/login against deployed staging/prod | Staging browser/API proof with real HTTPS domain and cookies |
| Real payment provider callback | Provider sandbox/prod webhook transcript, signature proof and idempotency persistence proof |
| Real Remnawave staging/prod provisioning | Staging/prod Remnawave profiles, nodes, user create/update and subscription URL evidence |
| Real VPN client connection | Disposable smoke user connects with generated config/subscription URL on a real staging/prod node |
| Real admin/support persona | Deployed admin browser proof with 2FA, RBAC, audit and support queue |
| Real alert delivery | Telegram alert channel and backup email delivery evidence |
| Real backup/restore/rollback | Local backup/restore is covered by `S1-QA-003`/`S1-QA-004`; local rollback dry-run is covered by `S1-REL-006`; managed staging/prod backup/restore and staging/prod rollback remain covered by later go-live gates |

## Acceptance Result

`S1-QA-001` is **completed locally** as a no-cost critical E2E gate.

It is acceptable for continuing local/no-cost S1 work. It is not sufficient for go-live without staging/prod provider, Remnawave, DNS/TLS, observability, backup/restore and rollback evidence.

`S1-OBS-001`, `S1-OBS-002`, `S1-OBS-003` and `S1-OBS-004` were completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`, `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` and `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ID: `S1-FE-002` - dashboard states for active/trial/grace/expired/payment/provisioning.
