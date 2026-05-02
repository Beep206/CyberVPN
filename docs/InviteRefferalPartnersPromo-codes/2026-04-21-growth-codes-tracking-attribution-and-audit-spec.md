# Growth Codes Tracking, Attribution, And Audit Spec

**Date:** 2026-04-21  
**Status:** target-state tracking baseline

---

## 1. Purpose

Growth codes must be modeled as a lifecycle, not as isolated code rows.

The platform must be able to answer for every invite, referral, promo and gift code:

- who issued it
- who owns it
- who distributed it
- who clicked or entered it
- who registered after the touchpoint
- who redeemed or applied it
- what entitlement, discount, order or reward was created
- whether risk blocked it
- which admin manually changed it and why

---

## 2. Lifecycle Model

Canonical lifecycle:

```text
code issued
  -> code assigned or owned
  -> code distributed or touched
  -> code resolved
  -> user registered
  -> code reserved or redeemed
  -> order, entitlement or reward created
  -> reward held, available or reversed
  -> audit, metrics and risk reviews updated
```

This lifecycle must be traceable end-to-end.

---

## 3. Roles Around A Code

| Role | Meaning |
| --- | --- |
| `issuer` | who created the code: system, admin, purchase, campaign or batch |
| `owner` | who owns the code economically or operationally |
| `distributor` | who shared the code if different from owner |
| `recipient_hint` | who the code was intended for, such as masked email |
| `touchpoint_user` | who clicked or entered the code before registration or checkout |
| `registered_user` | who registered after the touchpoint |
| `redeemer` | who actually redeemed the code |
| `beneficiary` | who received discount, entitlement or credit |
| `reward_receiver` | who received reward after a qualifying downstream event |
| `admin_actor` | which admin manually created, changed or revoked the code |

These roles are not interchangeable.

---

## 4. Invite Tracking

Required trace:

```text
invite issuance
  -> invite touchpoint
  -> signup attribution
  -> invite redemption
  -> entitlement grant
  -> optional owner reward
```

For invite, admin and support must be able to see:

- owner user
- issuance source
- source order and source plan SKU when bundle-generated
- click or enter touchpoints
- resulting signup
- redeemer
- entitlement granted
- optional reward to owner
- risk decision

---

## 5. Referral Tracking

Required trace:

```text
referral link copy
  -> touchpoint
  -> signup attribution
  -> referral relationship
  -> qualifying order
  -> reward allocation
  -> reward hold and release or reversal
```

Support and analytics must be able to answer:

- which user referred which user
- which signup was attributed
- which first paid order qualified
- which reward was created
- whether that reward is pending, available or reversed

---

## 6. Promo Tracking

Required trace:

```text
promo issued
  -> promo distributed or published
  -> promo entered in checkout
  -> resolution event
  -> reservation
  -> committed order
  -> discount snapshot
  -> refund or chargeback follow-up
```

For promo, admin must be able to inspect:

- campaign or issuer
- channel and storefront
- user who entered it
- SKU and checkout mode
- accepted or rejected result
- reject reason or conflict
- order receiving discount
- refund state

---

## 7. Gift Tracking

Required trace:

```text
gift purchase or admin issue
  -> gift code issuance
  -> recipient hint or delivery
  -> gift redemption touchpoint
  -> gift redemption
  -> entitlement grant
  -> refund, revoke or chargeback follow-up
```

For gift, the system must know:

- purchaser or admin issuer
- recipient hint
- redeemer
- purchased SKU or entitlement snapshot
- entitlement created
- purchase order
- redemption date
- refund or revocation state

---

## 8. Core Tracking Records

The backend must record at least:

- issuance
- touchpoint
- signup attribution
- resolution event
- reservation
- redemption
- reward allocation
- admin audit event

---

## 9. Admin Audit Requirements

Every manual admin action must record:

- actor
- object type
- object id
- action type
- reason
- optional note
- before and after state
- related order, case or batch if applicable

Examples:

- manual invite grant
- revoke promo
- reverse referral reward
- issue support gift
- extend expiry

---

## 10. Support Lookup Requirements

Operators must be able to search by:

- full code if permitted
- masked prefix
- owner
- purchaser
- redeemer
- source order
- gift batch
- campaign

The lookup view must show:

- summary
- issuance
- touchpoints
- signups
- redemptions
- rewards
- risk results
- audit trail

---

## 11. Metrics Dependency

Tracking records are not optional analytics extras.

They are prerequisites for:

- growth funnel reporting
- abuse review
- support diagnosis
- reward correctness
- finance correctness
- auditability

---

## 12. Frozen Design Outcome

No growth code implementation is considered complete unless it can be traced through:

- issuance
- touchpoint
- attribution
- redemption or application
- resulting economic or entitlement effect
- admin and risk audit
