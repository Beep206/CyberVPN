# S2 Stage 07 Evidence: Subscription, Renewal, Expiry, And Refund Flows

**Stage:** `S2-STAGE-07`
**Date:** 2026-05-22
**Status:** Passed local lifecycle baseline
**Scope:** CyberVPN Public Release 1.0 subscription lifecycle contract

---

## 1. Purpose

This evidence closes the local portion of `S2-STAGE-07`.

The goal was to make the customer lifecycle explicit before moving to S2 VPN provisioning/capacity work:

1. trial availability and one-time trial rules;
2. active trial/paid/manual access;
3. paid grace period and disable boundary;
4. expired/suspended behavior;
5. payment pending/failed behavior;
6. provisioning pending/config unavailable behavior;
7. refund review and full-refund access impact;
8. manual renewal steps;
9. expiry/grace reminder schedule;
10. autoprolongation evidence gate.

---

## 2. Files Changed

| File | Purpose |
|---|---|
| `backend/src/presentation/api/shared/stage2_subscription_lifecycle.py` | New side-effect-free lifecycle decision helper for S2 |
| `backend/src/presentation/api/shared/__init__.py` | Exports S2 lifecycle contract symbols |
| `backend/tests/security/test_stage2_subscription_lifecycle.py` | Security/product-policy checks for S2 lifecycle states |
| `docs/cybervpn_stage2_launch_docs/06_STAGE2_SUBSCRIPTION_LIFECYCLE.md` | Stage 2 lifecycle specification |
| `docs/plans/2026-05-22-cybervpn-stage2-public-release-master-plan.md` | Marks `S2-STAGE-07` local baseline as completed |
| `docs/evidence/releases/s2-stage-07-subscription-lifecycle-20260522.md` | This evidence file |

---

## 3. Lifecycle Contract Added

The backend now has a redacted S2 lifecycle helper:

```text
backend/src/presentation/api/shared/stage2_subscription_lifecycle.py
```

It produces customer/support-facing decisions without provisioning, payment side effects or secret exposure.

Covered states:

| State | Meaning |
|---|---|
| `trial_available` | User may activate one-time trial or choose paid plan |
| `trial_active` | Trial is active |
| `active` | Paid/manual access is active |
| `grace` | Paid access is inside the 72-hour grace window |
| `expired` | Access ended; manual renewal/support path is visible |
| `payment_pending` | Provider has not reached final success |
| `payment_failed` | User can create a new manual renewal invoice |
| `provisioning_pending` | VPN delivery is still running/retrying |
| `config_unavailable` | Support/reconciliation must restore VPN configuration |
| `refund_review` | Refund is under support/finance review; access changes are not automatic |
| `refunded_suspended` | Full refund succeeded; current paid access is suspended/reviewed |
| `no_access` | No current entitlement |

---

## 4. Owner Policy Reflected

| Policy | S2 result |
|---|---|
| Trial | `3 days`, `2 GB`, `1 device`, one-time by default |
| Trial expiry | No paid grace; user must buy/redeem/manual grant |
| Paid grace | `72 hours`, matching S1 owner-approved policy |
| Manual renewal | Default S2 flow |
| Autoprolongation | Remains gated by evidence and runtime flag |
| Refund pending | No automatic access loss |
| Full refund succeeded | Current paid period is suspended/reviewed |
| Config unavailable | Support/reconciliation escalation |

---

## 5. Autoprolongation Gate

True recurring billing remains disabled until all evidence exists:

```text
provider_recurring_support
explicit_user_consent
cancel_flow
failed_renewal_handling
renewal_reminders
refund_policy_alignment
webhook_idempotency
staging_smoke
production_smoke
```

Required runtime posture:

```text
PAYMENT_AUTORENEWAL_ENABLED=false
```

No public copy may promise automatic renewal, saved recurring payment methods or automatic recurring charges before this gate is closed.

---

## 6. Test Evidence

### 6.1 S2 Lifecycle Unit/Security Checks

Command:

```bash
cd backend
uv run ruff check src/presentation/api/shared/stage2_subscription_lifecycle.py tests/security/test_stage2_subscription_lifecycle.py
uv run pytest tests/security/test_stage2_subscription_lifecycle.py -q --no-cov
```

Result:

```text
All checks passed!
9 passed in 0.25s
```

### 6.2 Broader S1/S2 Policy Regression Set

Command:

```bash
cd backend
uv run ruff check src/presentation/api/shared/__init__.py src/presentation/api/shared/stage2_subscription_lifecycle.py tests/security/test_stage2_subscription_lifecycle.py
uv run pytest tests/security/test_stage2_subscription_lifecycle.py tests/security/test_stage1_expiry_grace_disable.py tests/security/test_stage1_grace_period_product_policy.py tests/security/test_stage1_refund_dispute_process.py tests/security/test_stage1_provider_payment_status_mapping.py -q --no-cov
```

Result:

```text
All checks passed!
76 passed in 0.39s
```

### 6.3 Existing Refund/Renewal Integration Flows

Temporary local services were started only for this integration check:

```bash
cd infra
docker compose up -d remnawave-db remnawave-redis
```

Command:

```bash
cd backend
SWAGGER_ENABLED=false RATE_LIMIT_PAYMENT_WRITE_REQUESTS=1000 uv run pytest tests/integration/test_refund_and_dispute_lifecycle.py tests/integration/test_renewal_ownership.py -q --no-cov
```

Result:

```text
4 passed in 48.42s
```

Cleanup:

```bash
cd infra
docker compose stop remnawave-db remnawave-redis
docker ps --format '{{.Names}}\t{{.Status}}'
```

Result:

```text
No local containers left running.
```

---

## 7. Security Review

Checked risks:

1. no raw provider payloads are emitted by the lifecycle helper;
2. no subscription URLs, VPN configs, tokens, passwords or webhook secrets are included in reminder schedules;
3. refund pending state does not silently remove access;
4. full refund state does not leave refunded paid access silently active;
5. payment pending and provisioning pending are distinct customer-visible states;
6. config unavailable escalates to support/reconciliation;
7. recurring billing cannot be enabled unless all required evidence is present.

---

## 8. Remaining Risks

| Risk | Status | Handling |
|---|---|---|
| True autoprolongation | Not enabled | Keep gated until provider recurring support, consent, cancel, failed-renewal, reminders, refund policy, idempotency and staging/prod smoke evidence exist |
| Live provider recurring behavior | Not proven | Must be proven in later S2 payment/runtime work before enabling recurring charges |
| UI consumption of lifecycle helper | Contract is ready, full UI wiring remains follow-up work if needed | S2 UI must consume these state names/message keys and must not invent conflicting lifecycle states |
| Live production lifecycle proof | Not part of local baseline | Production/staging checks remain in later S2 stages |

---

## 9. Exit Decision

`S2-STAGE-07` local lifecycle baseline is closed.

It is acceptable to proceed to:

```text
S2-STAGE-08: VPN Provisioning, Protocols, And Capacity
```
