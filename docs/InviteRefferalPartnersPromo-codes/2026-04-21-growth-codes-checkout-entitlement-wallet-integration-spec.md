# Growth Codes Checkout, Entitlement, Wallet Integration Spec

**Date:** 2026-04-21  
**Status:** target-state integration baseline

---

## 1. Purpose

This spec defines how customer growth codes integrate with:

- checkout quote
- checkout commit
- wallet
- entitlement creation
- partner conflict logic

---

## 2. Code Resolution Engine

Every user-entered or implied code must go through one backend resolver:

```text
code input
  -> detect code type
  -> validate context
  -> apply typed policy
  -> return accepted effect or conflict
```

Resolver context includes:

- user identity or anonymous shell
- realm
- storefront
- sale channel
- checkout mode
- selected plan family
- selected period
- selected add-ons
- current subscription state
- wallet usage
- partner binding
- risk subject

---

## 3. Quote Integration

### Quote flow

```text
frontend quote request
  -> pricing inputs
  -> optional code_input
  -> backend resolve
  -> backend pricing
  -> final quote payload
```

Frontend must never:

- compute discount
- decide stacking
- infer entitlement

Legacy validate note:

- legacy promo validate endpoints are not source of truth for final checkout application
- final truth is `quote -> reservation -> commit -> consume`

---

## 4. Discount Order

Default order:

1. base plan price
2. add-ons
3. partner markup if partner flow is active
4. promo or referral friend discount
5. wallet usage
6. gateway amount

Conflict rule:

- referral discount and partner code must not coexist
- promo and partner code must not coexist
- partner binding counts as partner flow even if no explicit partner code is entered in the current checkout

That means backend must reject forbidden combinations not only on `partner_code`, but also on persistent `partner_binding`.

---

## 5. Invite Redemption

Invite must not use normal discount flow.

Target-state flow:

```text
invite redeem
  -> validate invite
  -> create redemption
  -> create entitlement grant with limited invite profile
  -> mark code consumed
```

Target-state invite entitlement profile:

- `1 device`
- `standard mode`
- `shared pool`
- `no dedicated IP`
- `no add-ons`
- duration = `friend_days`

Compatibility mode during migration:

- invite redemption may temporarily create `bonus_days` allocation until `entitlement_grants` are fully implemented

Target-state wins after migration.

Expected result:

- `gateway_amount = 0`
- no payout
- no commissionability

---

## 6. Gift Redemption

Gift must not use normal discount flow.

Flow:

```text
gift redeem
  -> validate code
  -> create gift redemption record
  -> create entitlement grant or future entitlement
  -> mark gift consumed
```

Expected result:

- `gateway_amount = 0`
- auditable entitlement grant
- no referral reward
- no partner payout

Gift policy with active subscription:

| Situation | Default rule |
| --- | --- |
| gift same plan family | extend current subscription or create future entitlement |
| gift higher plan | create temporary upgraded entitlement for gift duration |
| gift lower plan | create future entitlement or convert to extension by policy |
| gift while current dedicated IP active | do not include dedicated IP unless gift explicitly supports it |
| gift includes dedicated IP | require explicit gift design and location rules, otherwise not supported |

First implementation recommendation:

- gift supports `plan family + duration` only
- dedicated IP gift packages are out of scope unless explicitly designed

---

## 7. Wallet Integration

Wallet is allowed with:

- promo discount
- referral friend discount
- partner flow, if no forbidden conflict exists

Wallet is not the normal path for:

- invite redemption
- gift redemption

Referral rewards should land in:

- non-withdrawable wallet or equivalent reward balance

Recommended wallet buckets:

- `cash_balance_withdrawable`
- `customer_credit_nonwithdrawable`
- `reward_credit_nonwithdrawable`
- `promo_credit_nonwithdrawable`

Default rule:

- referral reward -> `customer_credit_nonwithdrawable`
- gift redemption -> no generic wallet balance by default
- invite redemption -> no wallet balance
- promo -> discount, not wallet credit

---

## 8. Reservations

Single-use or limited-use codes must use quote reservations.

Required behavior:

- quote reserves code usage
- commit consumes reservation
- failed or expired quote releases reservation

This is especially important for:

- single-use promo
- gift code
- low-cap invite issue

---

## 9. Idempotency

Critical mutations must be idempotent:

- quote commit
- gift redeem
- invite redeem
- reward allocation

Repeated client retry must not create:

- double reward
- double entitlement
- double usage

---

## 10. Expected Quote Response

Quote response should return:

- base amount
- addons amount
- discounts
- wallet applied
- gateway amount
- code resolution result
- conflicts
- effective entitlements snapshot

---

## 11. Forbidden Recursive Effects

The system must prevent:

- gift redemption creating referral payout
- gift redemption creating partner payout
- referral credit itself becoming qualifying commercial revenue
- invite redemption becoming cash commission source

---

## 12. Policy Version Lock

The final order, redemption or reward must reference:

- exact `policy_version_id`
- effective policy snapshot at resolution time

If policy changes between quote and commit:

- either reservation preserves prior valid policy outcome within reservation TTL
- or commit must fail with a structured policy-changed conflict

This must be explicit per code type.

---

## 13. Current Platform Alignment

This spec fits the current pricing baseline:

- 4 public paid families
- 4 term variants per family
- 2 add-ons
- term-level invite bundles
- backend quote as pricing truth
