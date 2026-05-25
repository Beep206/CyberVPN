# S3-STAGE-15 Evidence: Full Partner Staging Rehearsal

**Date:** 2026-05-25
**Stage:** `S3-STAGE-15`
**Status:** Passed for local/non-prod full rehearsal evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/15_STAGE3_FULL_PARTNER_STAGING_REHEARSAL.md`

---

## 1. Summary

S3-STAGE-15 proves the complete partner/reseller platform rehearsal path locally/non-prod:

```text
partner application -> admin review -> probation approval -> legal acceptance
workspace creation -> team/RBAC/2FA controls
partner code/attribution -> customer checkout/order -> explainability
reporting/analytics/conversion views -> support/admin ops
payment/earning event -> statement -> payout dry-run -> reconciliation
transactional outbox -> NATS JetStream -> durable consumers/replay/dead-letter
partner portal frontend enabled/disabled boundary tests
security/privacy/legal checks from S3-STAGE-14 remain passing
```

This evidence does not enable production partner portal, public storefronts, public webhooks or live payouts.

---

## 2. Changed Files For This Stage

```text
backend/src/application/use_cases/settlement/earning_events.py
backend/tests/e2e/test_phase4_settlement_foundations.py
backend/tests/e2e/test_phase4_finance_foundations.py
backend/tests/integration/test_partner_statement_lifecycle.py
scripts/partner/run-stage3-nats-jetstream-smoke.sh
docs/cybervpn_stage3_launch_docs/15_STAGE3_FULL_PARTNER_STAGING_REHEARSAL.md
docs/evidence/releases/s3-stage-15-full-partner-staging-rehearsal-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z/
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z/
```

---

## 3. Blockers Found During Rehearsal

| Finding | Result |
|---|---|
| Earning events used current timestamp instead of payment timestamp for settlement period matching. | Fixed in `RecordEarningEventUseCase`. |
| Phase4 dry-run tests had fixed April 2026 periods but implicit current payment timestamps. | Fixed by setting payment/attempt timestamps inside the tested settlement window. |
| Reserve dry-run used account-level reserve outside the statement window. | Fixed by tying reserve to the earning event. |
| S3 disabled-state middleware blocked local payout dry-run tests. | Fixed by test-only `partner_payouts_enabled` monkeypatch; production default remains disabled. |
| NATS smoke script missed partner-lab PostgreSQL env vars during compose rendering. | Fixed and redacted. |

---

## 4. Proof Matrix

| Proof | Result |
|---|---|
| Partner application + admin review + legal acceptance | Passed |
| Workspace creation + members + RBAC + 2FA | Passed |
| Partner code attribution + abuse block | Passed |
| Customer checkout/order through partner context | Passed |
| Storefront preview disabled/readonly contract | Passed |
| Reporting/conversion/analytics/settlement surfaces | Passed |
| Support/admin operations and payout review queue | Passed |
| Payment -> earning event -> statement -> payout dry-run | Passed |
| Partner statement lifecycle | Passed |
| Runtime observability instrumentation | Passed |
| OpenAPI route/schema contracts | Passed |
| Security/tenant/webhook gate | Passed |
| NATS publish/consume/replay | Passed |
| Outbox dispatcher/consumer/dead-letter/idempotency | Passed |
| Partner frontend shell and disabled boundary | Passed |
| Docker cleanup after lab proofs | Passed |

---

## 5. Commands And Results

### Backend Full Rehearsal Pack

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

### Frontend Partner Portal Pack

```bash
npm run test:run -w frontend -- \
  src/app/[locale]/\(dashboard\)/partner/components/__tests__/PartnerClient.test.tsx \
  src/app/[locale]/\(dashboard\)/partner/components/__tests__/PartnerClient.disabled-boundary.test.tsx \
  src/app/[locale]/\(dashboard\)/partner/hooks/__tests__/usePartner.test.tsx
```

Observed result:

```text
Test Files  3 passed (3)
Tests       30 passed (30)
```

### NATS JetStream Smoke

```bash
STAGE3_NATS_EVIDENCE_DIR=docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z \
  bash scripts/partner/run-stage3-nats-jetstream-smoke.sh
```

Observed result:

```text
status=ok
publish_proof=.../publish.txt
consume_proof=.../consumer-next.txt
replay_proof=.../consumer-replay-next.txt
alert_input_proof=.../jsz-after.json
```

### Outbox Dispatcher Proof

```bash
STAGE3_OUTBOX_EVIDENCE_DIR=docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z \
  bash scripts/partner/run-stage3-outbox-dispatcher-proof.sh
```

Observed result:

```text
status=ok
published_publications=2
consumer_receipts=3
duplicate_delivery_idempotent=true
successful_event_status=published
```

### Container Cleanup

```bash
docker ps --format '{{.Names}}\t{{.Status}}'
```

Observed result:

```text
no running containers
```

### Final Hygiene

```bash
cd backend
.venv/bin/python -m py_compile \
  src/application/use_cases/settlement/earning_events.py \
  tests/e2e/test_phase4_settlement_foundations.py \
  tests/e2e/test_phase4_finance_foundations.py \
  tests/integration/test_partner_statement_lifecycle.py

.venv/bin/python -m ruff check \
  src/application/use_cases/settlement/earning_events.py \
  tests/e2e/test_phase4_settlement_foundations.py \
  tests/e2e/test_phase4_finance_foundations.py \
  tests/integration/test_partner_statement_lifecycle.py

bash -n scripts/partner/run-stage3-nats-jetstream-smoke.sh scripts/partner/run-stage3-outbox-dispatcher-proof.sh
git diff --check
npm audit --audit-level=high
```

Observed result:

```text
py_compile: passed
ruff: passed
bash syntax: passed
git diff --check: passed
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this gate
secret scan: no real secret material found; script matches are generated disposable lab passwords
dangerous pattern scan: no new dangerous pattern in changed S3-STAGE-15 code/scripts
```

---

## 6. Evidence Artifacts

```text
docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z/summary.txt
docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z/jsz-after.json
docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z/consumer-next.txt
docs/evidence/partner-platform/stage3-nats-s3-stage15-20260525T072500Z/consumer-replay-next.txt
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z/summary.json
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z/db-after-dispatch.json
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z/consumer-receipts.json
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z/dead-letter-proof.json
docs/evidence/partner-platform/stage3-outbox-s3-stage15-20260525T072500Z/checksums.sha256
```

---

## 7. Decision

```text
APPROVED_FOR_S3_PRODUCTION_DISABLED_STATE_DEPLOY
```

Next:

```text
S3-STAGE-16: Production Disabled-State Deploy
```
