# Growth Codes Admin Operations Spec

**Date:** 2026-04-21  
**Status:** target-state admin operations baseline

---

## 1. Goal

Admin must control the full customer growth code lifecycle without direct database intervention.

This includes:

- issue
- lookup
- attribution inspection
- redemption inspection
- reward control
- risk review
- auditability

---

## 2. Required Admin Areas

1. `Growth Codes Console`
2. `Invite Code Management`
3. `Referral Program Settings`
4. `Promo Campaigns`
5. `Gift Code Batches`
6. `Code Lookup`
7. `Redemption History`
8. `Reward Allocations`
9. `Abuse / Risk Reviews`
10. `Code Analytics`
11. `Bulk Actions`
12. `Manual Issue / Revoke`
13. `Policy Versioning`
14. `Audit Log`

---

## 3. Growth Codes Console

This is the operator home.

Required filters:

- code type
- status
- issuer type
- owner
- campaign
- batch
- storefront
- date range
- redeemed or not redeemed
- risk status
- source order
- issuing admin

Required table columns:

- code
- type
- status
- owner or issuer
- source
- uses
- redemptions
- registrations
- revenue after code
- rewards issued
- risk flags
- expires
- created

---

## 4. Code Detail Page

Every code detail page must expose:

### Summary

- masked code
- type
- status
- owner
- issuer
- source
- policy version
- usage limits
- expiry

### Issuance

- why issued
- by whom
- source order or plan bundle
- admin note

### Touchpoints

- clicks
- manual entries
- sessions
- channels
- UTM
- rejected attempts

### Signups

- who registered through the code
- when
- storefront
- risk subject

### Redemptions

- who redeemed
- what order, entitlement or wallet reward was created
- final status

### Rewards

- who received reward
- pending, available or reversed state
- reason

### Risk

- decisions
- blocks
- self-redemption attempts
- suspicious clusters

### Audit Log

- admin actions
- system actions
- policy changes

---

## 5. Invite Operations

Admin must be able to:

- issue invites
- revoke invites
- extend expiry
- inspect usage
- inspect owner
- inspect redeemer
- issue compensation invites

---

## 6. Manual Invite Grant

Admin grant flow must support:

- target user
- invite policy
- friend days
- expiry days
- count
- reason
- note

Example reasons:

- support compensation
- loyalty
- incident
- manual campaign
- admin test

For high-value grants, maker-checker may be required.

---

## 7. Referral Operations

Admin must be able to:

- change referral reward policy
- inspect referral relationships
- inspect signup attribution
- inspect qualifying orders
- inspect pending and reversed rewards
- block abusive referral flows
- manually reverse bad allocations

---

## 8. Promo Operations

Admin must be able to:

- create campaigns
- pause campaigns
- set eligibility
- set caps
- inspect usage
- revoke leaking promo

---

## 9. Referral Console

Referral console must show:

- referrer
- referred user
- signup source
- qualifying order
- reward value
- reward state
- hold state
- risk result
- cap usage

Actions:

- block reward
- reverse reward
- mark reviewed
- note partner-upgrade candidate

---

## 10. Promo Campaign Console

Promo console must support:

- create single code or batch
- choose eligibility by plan, duration, channel, storefront and checkout mode
- preview quote impact
- pause or revoke campaign
- inspect redemptions, revenue and refunds

---

## 11. Gift Operations

Admin must be able to:

- create single gift codes
- create gift batches
- issue support gifts
- inspect redemption
- revoke unredeemed gift
- handle refund-linked revocation

---

## 12. Gift Code Console

Gift console must support:

- issue single gift
- create gift batch
- set entitlement package
- set recipient hint
- export batch if policy allows
- revoke unused gift
- inspect redeemed gifts
- link gift to support case

---

## 13. Code Lookup

Support must be able to search by:

- full code when allowed
- masked prefix
- owner
- purchaser
- redeemer
- source order
- batch
- campaign

Lookup must show:

- why a code exists
- why a code failed
- who used it
- what effect was created
- what the next safe action is

---

## 14. Required State Mapping

Admin action must map to customer-visible effect:

- revoke promo -> customer sees code inactive or expired-like rejection
- request abuse review -> reward stays pending or blocked
- revoke invite -> customer sees invite unavailable
- issue compensation gift -> customer sees redeemable entitlement code

---

## 15. Audit Requirements

Every privileged mutation must record:

- actor
- timestamp
- object type
- object id
- before
- after
- reason

---

## 16. Admin Metrics Dependency

Admin operations must emit metrics for:

- code grants
- revocations
- reward reversals
- manual adjustments
- code lookups
- bulk issue operations

These are required to monitor operational risk and support load.

---

## 17. Operator Roles

Recommended roles:

- growth_admin
- support_ops
- finance_observer
- fraud_risk
- readonly_auditor

---

## 18. Launch Priority

First admin launch slice:

- promo campaigns
- invite issue and revoke
- code detail and code lookup
- referral inspection
- gift batch issue
- reward reversal
- audit log
