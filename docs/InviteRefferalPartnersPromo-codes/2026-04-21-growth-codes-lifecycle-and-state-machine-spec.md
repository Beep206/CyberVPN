# Growth Codes Lifecycle And State Machine Spec

**Date:** 2026-04-21  
**Status:** target-state state-machine baseline

---

## 1. Purpose

This spec defines lifecycle state machines for:

- invite code
- referral relationship
- promo campaign and promo code
- gift code
- code reservation
- code redemption
- reward allocation

For each lifecycle the system must define:

- states
- allowed transitions
- initiating actor
- side effects
- terminal states
- idempotent transitions
- replay-safe behavior

---

## 2. General Rules

- every lifecycle must have explicit terminal states
- replayed requests must not create double redemptions, double rewards or double entitlements
- scheduler-driven transitions must be idempotent
- admin reversal must be explicit, auditable and policy-bound
- state transitions must emit lifecycle events

---

## 3. Invite Code Lifecycle

States:

- `issued`
- `active`
- `used`
- `expired`
- `revoked`

Terminal states:

- `used`
- `expired`
- `revoked`

| Transition | Actor | Side effect | Idempotent |
| --- | --- | --- | --- |
| `issued -> active` | system or admin | code becomes redeemable | yes |
| `active -> used` | redeem endpoint | create redemption + entitlement grant | must be |
| `active -> expired` | scheduler | code unavailable | yes |
| `active -> revoked` | admin or risk | code unavailable + audit event | yes |
| `used -> revoked` | admin or risk, policy-bound | controlled reversal or block flow | controlled only |

Invite redemption target-state:

- creates `entitlement_grant` with invite-limited profile

Compatibility mode during migration:

- invite redemption may temporarily create `bonus_days` allocation until entitlement grants are fully implemented

Target-state wins after migration.

---

## 4. Referral Relationship Lifecycle

States:

- `created`
- `registered`
- `qualified_pending_reward`
- `reward_available`
- `reward_reversed`
- `blocked_by_risk`

Terminal states:

- `reward_available`
- `reward_reversed`
- `blocked_by_risk`

| Transition | Actor | Side effect | Idempotent |
| --- | --- | --- | --- |
| `created -> registered` | signup attribution | relationship linked to referred user | yes |
| `registered -> qualified_pending_reward` | qualifying order evaluator | create pending reward allocation | must be |
| `qualified_pending_reward -> reward_available` | hold-release job | reward becomes usable | yes |
| `qualified_pending_reward -> blocked_by_risk` | risk engine or reviewer | reward blocked | yes |
| `reward_available -> reward_reversed` | refund, chargeback or admin reversal | reverse allocation | controlled |
| `blocked_by_risk -> reward_available` | manual review | release reward | controlled |

Migration note:

- legacy referral commission behavior is historical only
- target-state referral rewards use non-withdrawable growth reward semantics

---

## 5. Promo Campaign Lifecycle

States:

- `draft`
- `active`
- `paused`
- `expired`
- `exhausted`
- `revoked`

Terminal states:

- `expired`
- `exhausted`
- `revoked`

| Transition | Actor | Side effect | Idempotent |
| --- | --- | --- | --- |
| `draft -> active` | admin | campaign usable in resolver | yes |
| `active -> paused` | admin | new applications denied | yes |
| `paused -> active` | admin | campaign usable again | yes |
| `active -> expired` | scheduler | expired rejection path enabled | yes |
| `active -> exhausted` | usage cap evaluator | usage denied due to cap | yes |
| `active/paused -> revoked` | admin | campaign permanently unavailable | yes |

---

## 6. Promo Code Application Lifecycle

Resolution outcomes:

- `accepted`
- `rejected`
- `conflicted`
- `blocked_by_risk`

Reservations are a separate lifecycle.

Promo validate note:

- legacy validate endpoints are not final truth
- final truth is quote -> reservation -> commit -> consume

---

## 7. Gift Code Lifecycle

States:

- `issued`
- `active`
- `redeemed`
- `expired`
- `revoked`
- `refunded_blocked`

Terminal states:

- `redeemed`
- `expired`
- `revoked`
- `refunded_blocked`

| Transition | Actor | Side effect | Idempotent |
| --- | --- | --- | --- |
| `issued -> active` | system or admin | code redeemable | yes |
| `active -> redeemed` | redeem endpoint | gift redemption + entitlement grant | must be |
| `active -> expired` | scheduler | code unavailable | yes |
| `active -> revoked` | admin | code unavailable + audit event | yes |
| `active -> refunded_blocked` | refund or chargeback workflow | prevent future redeem | yes |
| `redeemed -> refunded_blocked` | refund or chargeback workflow | create support or risk case | controlled |

Gift policy with active subscription:

- same plan family -> extend current subscription or create future entitlement
- higher plan -> create temporary upgraded entitlement for gift duration
- lower plan -> create future entitlement or extension by policy
- dedicated IP gift package is out of scope unless explicitly designed

---

## 8. Code Reservation Lifecycle

States:

- `reserved`
- `consumed`
- `expired`
- `released`
- `cancelled`

Terminal states:

- `consumed`
- `expired`
- `released`
- `cancelled`

| Transition | Actor | Side effect | Idempotent |
| --- | --- | --- | --- |
| `none -> reserved` | quote flow | usage locked to checkout context | must be |
| `reserved -> consumed` | commit flow | reservation attached to order | must be |
| `reserved -> expired` | scheduler | reservation no longer valid | yes |
| `reserved -> released` | quote cancelled or failed | usage released | yes |
| `reserved -> cancelled` | admin or system exception | explicit cancellation | yes |

Reservations exist to protect:

- single-use promo
- gift redemption
- limited-use codes

---

## 9. Code Redemption Lifecycle

States:

- `accepted`
- `rejected`
- `conflicted`
- `blocked_by_risk`
- `reversed`

Terminal states:

- `accepted`
- `rejected`
- `conflicted`
- `blocked_by_risk`
- `reversed`

Redemption record must reference:

- code
- beneficiary
- resulting order or entitlement
- reward allocation if any
- policy version

---

## 10. Reward Allocation Lifecycle

States:

- `pending`
- `available`
- `blocked_by_risk`
- `reversed`
- `expired`

Terminal states:

- `available`
- `reversed`
- `expired`
- `blocked_by_risk` unless reopened by manual review

| Transition | Actor | Side effect | Idempotent |
| --- | --- | --- | --- |
| `none -> pending` | qualifying event processor | reward created on hold | must be |
| `pending -> available` | hold-release job | reward usable in allowed wallet bucket | yes |
| `pending -> blocked_by_risk` | risk engine | reward blocked | yes |
| `available -> reversed` | refund, chargeback or admin | reverse reward and wallet effect if needed | controlled |
| `pending -> expired` | expiry policy | pending reward dies | yes |

---

## 11. Emitted Events

Minimum lifecycle events:

- `growth_code.issued`
- `growth_code.resolved`
- `growth_code.redeemed`
- `growth_code.revoked`
- `growth_code.reserved`
- `growth_code.reservation_expired`
- `invite.redeemed`
- `referral.signup_attributed`
- `referral.reward_pending`
- `referral.reward_available`
- `referral.reward_reversed`
- `promo.applied_to_order`
- `gift.purchased`
- `gift.redeemed`
- `gift.revoked`
- `admin.growth_code_granted`
- `admin.growth_reward_reversed`

---

## 12. Design Rule

Lifecycle state must be explicit per typed object.

Do not overload one generic `status` field to represent:

- code issuance state
- redemption result
- reward state
- campaign state
- reservation state

These are different lifecycles and must remain separate.
