# Customer Growth Codes Rulebook

**Date:** 2026-04-21  
**Status:** target-state rulebook

---

## 1. Purpose

This rulebook defines the business meaning of customer growth codes in CyberVPN.

It covers:

- invite codes
- referral codes
- promo codes
- gift codes
- customer growth rewards

It does not cover:

- partner revenue codes
- partner payout logic
- partner statement logic
- partner attribution ownership contracts

---

## 2. Core Principle

CyberVPN must treat growth codes as a separate customer growth platform, not as a simplified partner program.

Growth codes exist to support:

- acquisition
- activation
- term expansion
- retention
- support gestures
- controlled campaigns
- gifting

They do not exist to create long-term partner cash ownership.

---

## 3. Code Types

## 3.1 Invite code

Purpose:

- give another user short controlled access

Core semantics:

- creates entitlement-like access
- does not create cash owner
- does not create partner payout
- does not act as checkout discount
- usually comes from paid SKU invite bundle or admin issue

## 3.2 Referral code

Purpose:

- let one customer refer another customer

Core semantics:

- friend gets first-order discount or equivalent benefit
- referrer gets non-withdrawable reward after qualifying event
- not a partner commission
- not a payoutable earning

## 3.3 Promo code

Purpose:

- apply admin-owned marketing discount or controlled offer

Core semantics:

- affects checkout quote
- does not create cash owner
- does not create referral relationship
- does not create partner payout by itself

## 3.4 Gift code

Purpose:

- grant prepaid subscription value or bonus entitlement

Core semantics:

- redeemable entitlement or subscription value
- not a partner payout event
- not a referral qualifying event by default
- should be modeled as entitlement grant, not generic stored wallet value

## 3.5 Partner code

Purpose:

- partner-owned commercial attribution and revenue

Core semantics:

- belongs to partner platform
- may create revenue ownership or markup semantics
- must not be treated as customer growth code

---

## 4. Surface Ownership

### Client frontend

Owns:

- invites
- referral
- redeem code UX
- gift purchase and gift redemption
- checkout code entry
- rewards overview

### Admin panel

Owns:

- promo management
- invite issue and revoke
- referral policy configuration
- gift batch issue
- code lookup
- abuse review
- manual reversal
- audit log

### Partner portal

Owns only:

- approved promo campaign assets
- campaign guidance
- disclosure and compliance instructions
- reseller voucher visibility only when special capability exists

Must not own:

- consumer invites
- consumer referrals
- customer gift purchase flow
- generic promo creation

---

## 5. Shared Backend Principle

All customer growth codes must flow through a single backend resolution layer:

- resolve code type
- validate context
- apply typed policy
- return effect or conflict

This does not mean all codes share the same business meaning.

---

## 6. Checkout Principles

- frontend never computes final discount logic
- frontend never decides stacking
- frontend never creates entitlements
- frontend never allocates rewards
- backend quote and redeem flows are the only source of truth
- persistent partner binding counts as partner flow even when no partner code is entered in the current checkout

---

## 7. Reward Principles

- invite rewards are growth rewards, not partner rewards
- referral rewards are non-withdrawable
- gift redemption is not a payout event
- promo discounts do not create ownership
- partner economics must remain separate
- promo is discount, not wallet credit
- invite does not create generic wallet balance
- gift does not create generic wallet balance by default

---

## 8. Default Product Policy

### Invite

- issued from term-level invite bundles or admin issue
- gives friend limited access for a fixed number of days
- may optionally reward inviter after later paid conversion
- target-state redemption creates limited `entitlement_grant`
- compatibility mode may temporarily map invite redemption to `bonus_days` allocation until entitlement-grant migration is complete

### Referral

- friend gets first qualifying paid-order discount
- referrer gets non-withdrawable reward after hold
- only for defined qualifying orders

### Promo

- admin-owned
- policy-bound by SKU, channel, checkout mode, geography and caps
- cannot be treated as partner-owned incentive

### Gift

- entitlement-oriented
- preferably fixed plan family plus duration
- redeem creates auditable entitlement grant
- dedicated IP gift packages are out of scope unless explicitly designed

---

## 9. Legacy Referral Migration Rule

Legacy referral commission behavior must not silently leak into target-state growth rewards.

Default migration rule:

- legacy referral relationships stay visible for history and audit
- new accruals after cutover use non-withdrawable growth reward model
- any grandfathered exception must be explicit through legacy policy versioning

---

## 10. Prohibited Confusions

The system must not:

- treat referral as affiliate program
- treat gift as wallet top-up by default
- treat invite as checkout discount
- allow partner portal to manage consumer referral program
- allow promo to silently stack with partner attribution

---

## 11. Baseline Pricing Context

This package assumes the current public pricing line:

- 4 public paid families: `Basic`, `Plus`, `Pro`, `Max`
- 4 terms: `30`, `90`, `180`, `365`
- 2 canonical add-ons: `extra_device`, `dedicated_ip`
- invite bundle is term-level, not a separate tariff

---

## 12. Rule Freeze Outcome

This rulebook freezes these meanings:

- `invite = access`
- `referral = discount + non-withdrawable reward`
- `promo = admin discount policy`
- `gift = prepaid entitlement`
- `partner = separate revenue layer`
