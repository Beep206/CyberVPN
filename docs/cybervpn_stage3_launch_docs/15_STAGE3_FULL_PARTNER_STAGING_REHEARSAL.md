# Stage 3 Full Partner Staging Rehearsal

**Stage:** `S3-STAGE-15`
**Status:** Passed for local/non-prod full rehearsal evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-14: Security, Privacy, Legal, And Compliance Gate`

---

## 1. Назначение

S3-STAGE-15 связывает предыдущие S3-гейты в один полный rehearsal перед production disabled-state deploy.

Цель этапа: доказать, что партнёрский контур проходит полный non-production сценарий без включения production partner features:

1. partner application;
2. admin approval/probation;
3. workspace creation;
4. team/member and RBAC checks;
5. partner code/campaign attribution path;
6. customer checkout/order through partner context;
7. attribution result;
8. entitlement/payment/settlement lineage;
9. event backbone publish/consume/replay;
10. partner reporting;
11. settlement/payout dry-run;
12. support/admin operations;
13. observability/alert/dashboard contracts.

Этот этап не включает production partner portal, production storefronts, live payouts or public partner webhooks.

---

## 2. Decision

S3-STAGE-15 decision:

```text
APPROVED_FOR_S3_PRODUCTION_DISABLED_STATE_DEPLOY
```

Разрешён следующий шаг:

```text
S3-STAGE-16: Production Disabled-State Deploy
```

Production defaults remain conservative:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_CODES_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
```

---

## 3. Rehearsal Proof Matrix

| Flow | Evidence |
|---|---|
| Partner application draft/submit/request-info/resubmit | `test_e2e_partner_001_application_review_probation_legal_and_notification_loop` |
| Admin approval/probation | `test_e2e_partner_001_application_review_probation_legal_and_notification_loop` |
| Workspace creation | `test_e2e_perm_010_015_role_permissions_and_admin_partner_sync` |
| Team invite/member role changes | `test_e2e_perm_010_015_role_permissions_and_admin_partner_sync` |
| RBAC and 2FA gate | `test_e2e_perm_010_015_role_permissions_and_admin_partner_sync` |
| Partner code attribution and self-referral abuse block | `test_s3_partner_codes_attribution_and_abuse_controls` |
| Customer checkout/order through partner context | `test_s3_partner_codes_attribution_and_abuse_controls` |
| Attribution explainability | `test_s3_partner_codes_attribution_and_abuse_controls` |
| Storefront preview disabled/readonly contract | `test_s3_reseller_storefront_preview_is_gated_readonly_and_does_not_change_checkout` |
| Reporting, analytics, conversion and settlement surfaces | `test_partner_workspace_reporting_and_cases_are_visible_to_workspace_members` |
| Payment -> earning event -> statement -> payout dry-run | `test_phase4_settlement_foundations_end_to_end` |
| Finance/reconciliation gate | `test_phase4_finance_foundations_surface_and_reconciliation_gate` |
| Statement lifecycle | `test_partner_statement_lifecycle` |
| Runtime observability instrumentation | `test_partner_runtime_observability` |
| OpenAPI contracts | partner application, admin conformance, storefront, statement and observability contract tests |
| Security and tenant isolation | partner scope, auth realm isolation and webhook security tests |
| Event backbone | NATS JetStream smoke proof |
| Outbox dispatcher and consumers | outbox dispatcher proof |
| Partner portal frontend | `PartnerClient`, disabled-boundary and `usePartner` Vitest tests |

---

## 4. Blockers Found And Closed

| Blocker | Fix |
|---|---|
| Settlement dry-run missed held earning events when test payment/event timestamps drifted outside the fixed period window. | `RecordEarningEventUseCase` now writes earning event and hold timestamps from the payment context. Time-dependent tests now set payment/attempt timestamps inside the tested settlement window. |
| Manual reserve in dry-run was created as account-level reserve outside the fixed period window but expected in the statement. | Dry-run tests now attach reserve to the earning event with `reserve_scope=earning_event`. |
| Phase 4 payout dry-run tests were blocked by S3 disabled-state middleware. | Tests now enable `partner_payouts_enabled` only through local `monkeypatch`; production default remains disabled. |
| NATS smoke script failed because compose config interpolated `partner-postgres` variables even for NATS-only proof. | Script now exports and redacts disposable partner-lab PostgreSQL variables for repeatable compose rendering. |

---

## 5. Evidence Locations

Release evidence:

```text
docs/evidence/releases/s3-stage-15-full-partner-staging-rehearsal-20260525.md
```

Event backbone evidence:

```text
docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z
```

---

## 6. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Full staging flow completed | Passed for local/non-prod rehearsal pack. |
| Evidence attached | Passed. |
| No production partner enablement yet | Passed. |
| Application/approval/workspace/team flow | Passed. |
| Code/attribution/checkout flow | Passed. |
| Reporting/settlement/support flow | Passed. |
| Event backbone proof | Passed. |
| Observability proof | Passed for code/config/assets; live dashboard load remains S3-STAGE-16/17 evidence. |
| Security/privacy gate still valid | Passed through S3-STAGE-14 tests included in pack. |

---

## 7. Validation

Backend full rehearsal pack:

```bash
cd backend
.venv/bin/python -m pytest \
  tests/e2e/test_partner_admin_conformance.py \
  tests/e2e/test_s3_partner_codes_attribution_anti_abuse.py \
  tests/e2e/test_s3_reseller_storefront_contract.py \
  tests/integration/test_partner_portal_reporting_reads.py \
  tests/e2e/test_phase4_settlement_foundations.py \
  tests/e2e/test_phase4_finance_foundations.py \
  tests/integration/test_partner_statement_lifecycle.py \
  tests/integration/test_partner_runtime_observability.py \
  tests/contract/test_partner_admin_e2e_conformance_pack.py \
  tests/contract/test_partner_application_onboarding_openapi_contract.py \
  tests/contract/test_s3_storefront_contract_openapi.py \
  tests/contract/test_partner_statement_openapi_contract.py \
  tests/contract/test_partner_observability_assets_contract.py \
  tests/security/test_partner_scope_enforcement.py \
  tests/security/test_auth_realm_isolation.py \
  tests/security/test_stage3_partner_webhook_receiver_security.py \
  -q --no-cov
```

Observed result:

```text
31 passed in 185.40s
```

Frontend partner portal checks:

```bash
npm run test:run -w frontend -- \
  src/app/[locale]/\(dashboard\)/partner/components/__tests__/PartnerClient.test.tsx \
  src/app/[locale]/\(dashboard\)/partner/components/__tests__/PartnerClient.disabled-boundary.test.tsx \
  src/app/[locale]/\(dashboard\)/partner/hooks/__tests__/usePartner.test.tsx
```

Observed result:

```text
3 files passed
30 tests passed
```

Event backbone proofs:

```bash
STAGE3_NATS_EVIDENCE_DIR=docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z \
  bash scripts/partner/run-stage3-nats-jetstream-smoke.sh

STAGE3_OUTBOX_EVIDENCE_DIR=docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z \
  bash scripts/partner/run-stage3-outbox-dispatcher-proof.sh
```

Observed result:

```text
NATS smoke: status=ok
Outbox dispatcher proof: status=ok
Docker containers after proof: none running
```

---

## 8. Residual Risks

| Risk | Status |
|---|---|
| Real staging/prod host smoke | Deferred to S3-STAGE-16 because this stage is local/non-prod rehearsal. |
| Live Grafana/Loki/Sentry dashboard load | Deferred to S3-STAGE-16/17. Asset and rule contracts passed. |
| Live payouts | Disabled; dry-run only. |
| Public partner webhooks | Disabled; local receiver only. |
| Public storefront rollout | Disabled; preview/contract only. |

---

## 9. Next

```text
S3-STAGE-16: Production Disabled-State Deploy
```
