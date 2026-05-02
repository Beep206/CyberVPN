# Growth Codes E2E Conformance Test Plan

**Date:** 2026-04-21  
**Status:** target-state QA baseline

---

## 1. Goal

Define end-to-end scenarios proving that customer growth codes work correctly across:

- checkout
- entitlement grant
- wallet reward
- admin operations
- risk
- audit

---

## 2. Core Scenarios

1. `Max 365` purchase generates `3 invites`
2. invite redeemed by new user
3. invite redemption creates entitlement grant
4. self-invite blocked
5. referral link -> signup -> `365d` paid order -> pending reward
6. referral reward becomes available after hold
7. referral reward reversed after refund
8. promo accepted for eligible SKU
9. promo rejected for ineligible duration
10. promo conflicts with partner binding
11. gift purchased by user
12. gift redeemed by recipient
13. gift refund after unredeemed gift revokes gift
14. gift chargeback after redeemed gift creates risk or admin case
15. wallet plus referral discount does not create recursive payout
16. admin manual invite grant creates audit event
17. admin code lookup shows issuance, touchpoint, redemption and reward chain

---

## 3. Required Assertions

Every scenario should assert:

- lifecycle events emitted
- correct policy version referenced
- correct reservation behavior where applicable
- correct reward state
- correct entitlement effect
- correct audit trail
- correct risk result

---

## 4. Negative Scenarios

- promo validate accepted but commit rejected after policy change
- invite entered in wrong checkout context
- gift entered in checkout discount box
- referral applied on addon-only order
- referral applied on partner-bound customer
- repeated redeem request is idempotent

---

## 5. Evidence Requirement

QA evidence should include:

- request and response traces
- created lifecycle records
- emitted events
- resulting order or entitlement ids
- reward ids
- audit ids

---

## 6. Success Criteria

Package is conformance-ready when QA can execute these scenarios without asking backend or frontend teams how the system is expected to behave.
