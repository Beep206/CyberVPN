# Stage 2 Subscription, Renewal, Expiry, And Refund Flows

**Stage:** `S2-STAGE-07`
**Status:** Approved local lifecycle baseline
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 subscription lifecycle contract before VPN provisioning and capacity work.

The goal is that a customer and support operator can understand the account state without guessing from raw Remnawave/payment records. No paid user should silently lose access without a visible state and supportable recovery path.

---

## 2. Canonical Lifecycle Contract

S2 now has a side-effect-free backend contract:

```text
backend/src/presentation/api/shared/stage2_subscription_lifecycle.py
```

It does not change live runtime behavior by itself. It gives backend, UI, support and tests one shared lifecycle model for:

1. trial availability and one-time trial use;
2. active paid/trial access;
3. 72-hour paid grace window;
4. expired/suspended access;
5. payment pending/failed states;
6. provisioning pending/config unavailable states;
7. refund review and refunded-suspended states;
8. manual renewal steps;
9. expiry/grace reminder schedules;
10. autoprolongation evidence gate.

---

## 3. Customer-Facing States

| State | Access state | Payment state | Provisioning state | Support state | Customer meaning |
|---|---|---|---|---|---|
| `trial_available` | `trial_available` | `not_started` | `not_required` | `self_service` | User may activate the one-time trial or choose a paid plan |
| `trial_active` | `trial_active` | current payment state | `ready` | `none` | Trial is active and config may be available |
| `active` | `active` | current payment state | `ready` | `none` | Paid/manual access is active |
| `grace` | `grace` | current payment state | `ready` | `self_service` | Paid access remains available during the 72-hour grace window |
| `expired` | `expired` | current payment state | `suspended` or `expired` | `self_service` | Access is ended; user should renew manually or contact support if already paid |
| `payment_pending` | `payment_pending` | `pending`/`processing` | `not_required` | `self_service` | Payment provider has not reached final success |
| `payment_failed` | `no_access` | `failed`/`cancelled`/`expired` | `not_required` | `self_service` | User can create a new manual renewal invoice |
| `provisioning_pending` | `provisioning_pending` | current payment state | `queued`/`pending`/`provisioning`/`retrying` | `self_service` | Payment may be accepted, but VPN delivery is still running |
| `config_unavailable` | `provisioning_pending` | current payment state | `failed`/`reconciliation_required`/`remnawave_unavailable` | `support_review` | Support must restore config or reconcile provisioning |
| `refund_review` | existing access state | current/refunded payment state | existing provisioning state | `support_review` | Refund request exists; access changes are not automatic |
| `refunded_suspended` | `suspended` | `refunded` | `suspended` | `support_review` | Full refund is recorded for the billing period; current paid access is suspended/reviewed |
| `no_access` | `no_access` | current payment state | `not_required` | `self_service` | No active entitlement; user can buy/redeem access |

---

## 4. Trial Contract

S2 keeps the S1/S2 catalog trial posture:

| Field | Value |
|---|---|
| Duration | `3 days` |
| Traffic | `2 GB` |
| Devices | `1` |
| Repeat trial | Not allowed by default after used/expired |
| Paid conversion | Manual checkout only; no automatic conversion |
| Refund | Trial does not create a cash refund entitlement |

Trial expiration has no paid grace period. At the trial expiry boundary, access is expired and the user must choose a paid plan or receive a support-approved manual grant.

---

## 5. Paid Grace And Disable Behavior

S2 keeps the owner-approved S1 paid grace period:

```text
S2_PAID_GRACE_PERIOD_HOURS=72
```

Behavior:

1. Before paid expiry: state is `active`.
2. From expiry until `expiry + 72h`: state is `grace`; access may remain available.
3. At `expiry + 72h`: state becomes `expired`; provisioning/access should be suspended/disabled through the expiry worker.
4. If Remnawave identity is missing when disable is due, support/reconciliation is required.

This matches the existing S1 expiry worker behavior and tests.

---

## 6. Manual Renewal Flow

S2 manual renewal is the approved default.

Canonical steps:

```text
open_public_catalog_or_mini_app_plans
choose_plan_and_period
create_new_checkout_invoice
wait_for_provider_final_success
run_paid_provisioning_or_extend_existing_access
show_subscription_url_config_and_expiry
record_payment_attempt_and_reconciliation_state
```

Customer copy may say:

```text
Manual renewal is available.
Payment status can take time to update.
If payment succeeded but access is not ready, support will review it.
```

Customer copy must not say:

```text
Renews automatically.
Saved recurring payment method.
Guaranteed instant refund.
```

---

## 7. Expiry Reminder Schedule

S2 reminder schedules are deterministic and safe for email/Telegram/in-app notifications.

| Access kind | Reminder offsets |
|---|---|
| Paid before expiry | `72h`, `24h`, `3h` before `access_expires_at` |
| Trial before expiry | `24h`, `3h` before `access_expires_at` |
| Paid grace before disable | `24h`, `3h` before `grace_ends_at` |

The schedule builder returns timestamps only. It does not expose subscription URLs, tokens, configs or provider payloads.

---

## 8. Refund Impact Contract

| Refund impact | Access behavior | Support behavior |
|---|---|---|
| `none` | Normal lifecycle evaluation | No refund support state |
| `pending_review` | Existing access state is preserved | Support/finance review; no automatic access change |
| `partial_refund_review` | Existing access state is preserved until approved correction | Support/finance review; may later reduce time/quota/wallet state |
| `full_refund_succeeded` | Current paid access becomes `suspended`; config unavailable | Support review; customer should not expect access for refunded period |

This follows the existing Refund Policy wording: a pending refund request does not automatically pause, extend or disable VPN access unless support/ops applies a correction.

---

## 9. UI Message Coverage

The S2 contract maps lifecycle states to stable message keys such as:

```text
subscription.trial_available
subscription.trial_active
subscription.active
subscription.grace
subscription.expired
subscription.payment_pending
subscription.payment_failed
subscription.provisioning_pending
subscription.config_unavailable
subscription.refund_review
subscription.refunded_suspended
subscription.no_access
```

Existing frontend copy already contains the critical customer states in customer dashboard / Mini App / generated locale bundles:

1. active subscription;
2. no active subscription;
3. trial available/activated;
4. grace period;
5. expired access;
6. payment pending/failed/expired/refunded;
7. provisioning pending/failed/config unavailable;
8. refund review language in refund/legal/support copy.

S2 UI work should consume the lifecycle state instead of inventing new state names.

---

## 10. Autoprolongation Gate

Autoprolongation remains disabled until every evidence item exists:

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

Runtime flag remains:

```text
PAYMENT_AUTORENEWAL_ENABLED=false
```

Even if the code path exists later, public copy must stay manual-renewal only until the evidence gate passes.

---

## 11. Support Contract

Support may use:

```text
user id
Telegram id / username
email
payment attempt id
order id
subscription lifecycle state
safe payment reference
request id / trace id
support ticket reference
```

Support must not request or expose:

```text
password
OTP code
refresh token
Telegram initData
provider secret
webhook signature
raw provider payload
raw subscription URL unless the user already sees it in the customer UI
raw VPN config file
```

---

## 12. No-Go Conditions

Do not proceed to wider S2 sale if any condition is true:

1. paid access can expire without visible `grace` or `expired` state;
2. a trial can be repeatedly activated without an explicit owner-approved policy;
3. refund success does not suspend/review the refunded access period;
4. payment pending and provisioning pending are collapsed into the same generic error;
5. config unavailable does not escalate to support/reconciliation;
6. renewal copy promises automatic renewal while `PAYMENT_AUTORENEWAL_ENABLED=false`;
7. expiry reminders include secret URLs/tokens/configs;
8. support cannot diagnose lifecycle state without direct database access.

---

## 13. Acceptance Evidence

Completed checks for this stage:

| Check | Result |
|---|---|
| S2 lifecycle helper | Added |
| Trial one-time/duration/quota/device contract | Tested |
| Paid 72h grace and disable boundary | Tested against S1 constant |
| Payment pending/failed state visibility | Tested |
| Provisioning pending vs config unavailable split | Tested |
| Refund review/full-refund suspended behavior | Tested |
| Manual renewal steps and reminder schedules | Tested |
| Autoprolongation evidence gate | Tested |
| Existing refund/renewal integration flows | Passed |

Commands and outputs are recorded in:

```text
docs/evidence/releases/s2-stage-07-subscription-lifecycle-20260522.md
```
