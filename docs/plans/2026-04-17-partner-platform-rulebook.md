# CyberVPN Partner Platform Rulebook

**Date:** 2026-04-17  
**Status:** Canonical business rulebook  
**Purpose:** define the canonical business rules, program families, precedence rules, payout ownership, and non-negotiable platform constraints for the five-lane CyberVPN partner platform.

---

## 1. Document Role

This rulebook is the business-policy anchor for the partner platform.

It defines:

- the five canonical lanes;
- consumer growth versus partner revenue separation;
- ownership and reward rules;
- stacking and precedence principles;
- qualifying-event principles;
- non-negotiable brand and payout restrictions.

This document describes **what must be true**. The implementation architecture, data model, and APIs are specified in companion documents.

---

## 2. Canonical Lane Model

## 2.1 Consumer Growth Programs

| Lane | Goal | Reward type | Withdrawable | Cash owner |
|---|---|---|---|---|
| Invite / Gift | activation and social spread | bonus days, extra invites, non-cash perks | no | never |
| Consumer Referral Credits | customer-led recommendation | fixed non-withdrawable credit | no | never |

## 2.2 Partner Revenue Programs

| Lane | Goal | Reward type | Withdrawable | Cash owner |
|---|---|---|---|---|
| Creator / Affiliate | content and creator acquisition | revshare earnings | yes, after hold | yes |
| Performance / Media Buyer | paid traffic at scale | custom CPA or hybrid | yes, after longer hold | yes |
| Reseller / API / Distribution | price ownership and distribution | markup and/or hybrid earnings | yes | yes |

## 2.3 Family Separation Rule

Consumer growth programs must not be modelled as partner-finance programs.

They may reuse:

- code mechanics;
- offer mechanics;
- ledger primitives;
- reporting pipelines.

But they must remain separate across:

- actor classes;
- eligibility rules;
- ledgers;
- payout semantics;
- portals and permissions;
- disputes and compliance.

---

## 3. Non-Negotiable Invariants

1. One `order` has at most one cash payout owner.
2. Invite and consumer referral rewards never become cash payout owners.
3. `explicit_code > passive_click > default_referral_state`.
4. Persistent reseller or storefront commercial bindings outrank incidental affiliate touches.
5. Official CyberVPN-branded surfaces never expose self-serve markup.
6. Partner-branded storefronts render native storefront pricing, not “CyberVPN base price plus visible markup”.
7. Consumer referral credits are non-withdrawable.
8. Wallet spend never recursively creates new payout entitlements.
9. Partner tiering is driven by net paid economics and quality metrics, not only client counts.
10. Critical economics must be defined through typed, versioned policy objects.
11. Classical MLM is prohibited.
12. Optional one-level sub-affiliate is a derived earnings overlay, not an acquisition owner.

---

## 4. Invite / Gift Rules

Invite is a growth mechanic, not a cash-affiliate mechanic.

Canonical rules:

- invite may grant bonus days, extra invites, or non-cash value;
- invite may coexist with commercial attribution;
- invite never owns the commercial payout of an order;
- invite-generated wallet value, if used, must not recursively generate new payouts;
- invite redemption and invite reward policies must be versioned and auditable.

Invite is intended to support:

- activation;
- warm introduction to product;
- light retention loops.

Invite is not intended to act as reseller or affiliate monetization.

---

## 5. Consumer Referral Credit Rules

Canonical rules:

- referral reward type is fixed non-withdrawable credit;
- referral duration mode is first qualifying payment only;
- baseline eligible durations are `90`, `180`, `365`;
- `30-day` plans are excluded by default;
- monthly and lifetime caps apply before any upgrade into affiliate status;
- friend discount and referrer reward are separate outputs;
- self-referral and abuse rules are enforced through risk policy, not only account-level checks.

Referral credits are designed for:

- normal customers;
- understandable economics;
- forecastable unit economics;
- reduced abuse compared with indefinite percentage revshare.

---

## 6. Creator / Affiliate Rules

Creator / Affiliate is the public revenue engine for:

- creators;
- content publishers;
- SEO sites;
- communities;
- reviews and media surfaces.

Canonical rules:

- public economics favor `90`, `180`, and `365` durations;
- `30-day` plans are discouraged or custom-only;
- earnings are withdrawable only after hold release;
- partners may hold multiple codes with different economics;
- margin-mode and conversion-mode are valid code strategies;
- creator surfaces on official CyberVPN properties must not behave like reseller price-ownership surfaces.

---

## 7. Performance / Media Buyer Rules

Performance is a closed lane.

Canonical rules:

- approval required;
- no public rates;
- server-side postback and source identifiers are mandatory;
- trial traffic is not automatically commissionable;
- longer payout hold than creator programs;
- quality gates enforce refund, chargeback, retention, and abnormal-velocity thresholds;
- probation mode applies to new performance partners.

This lane exists for:

- paid traffic desks;
- Telegram ads;
- native;
- paid social;
- push/display;
- other high-volume acquisition channels.

---

## 8. Reseller / API / Distribution Rules

Canonical rules:

- official CyberVPN-branded surfaces do not self-serve markup;
- markup is allowed only on partner-owned, approved, or API-driven surfaces;
- reseller ownership may be persistent;
- reseller economics can be markup-only or hybrid;
- storefront default ownership may be reseller-based on partner-owned storefronts;
- reseller does not collapse into creator-affiliate semantics.

This lane exists for:

- partner-owned storefronts;
- API-driven resale;
- controlled distribution;
- approved multi-surface partner commerce.

---

## 9. Commercial Ownership Rules

## 9.1 Commercial Owner Types

Canonical commercial owner types:

- `none`
- `affiliate`
- `performance`
- `reseller`
- `direct_store`

Semantics:

- `none` = no commercial owner resolved or no payout-relevant owner exists
- `direct_store` = first-party direct commercial ownership for analytics and provenance, without partner payout semantics

## 9.2 Owner Sources

Canonical owner sources:

- `explicit_code`
- `passive_click`
- `persistent_reseller_binding`
- `storefront_default`
- `manual_override`

## 9.3 Growth Reward Types

Canonical growth reward types:

- `invite_reward`
- `referral_credit`
- `bonus_days`
- `gift_bonus`

---

## 10. Stacking And Compatibility Rules

Canonical principles:

1. Only one commercial discount instrument reduces merchandise price unless policy explicitly allows otherwise.
2. Wallet spend is a settlement instrument, not a discount instrument.
3. Growth rewards can coexist with a commercial owner.
4. Growth rewards do not create cash payout ownership.
5. Surface policy can restrict external code override.

Baseline compatibility defaults:

| Combination | Default |
|---|---|
| promo + creator code | blocked |
| consumer referral discount + creator code | blocked |
| consumer referral discount + reseller code | blocked |
| wallet spend + one discount instrument | allowed |
| invite reward + commercial owner | allowed |
| partner-storefront default owner + external creator code | blocked unless surface policy allows override |

---

## 11. Qualifying Event Rules

Canonical qualifying first payment rules:

- eligible offer and SKU;
- eligible program policy at order time;
- positive commissionable net paid amount after excluded credits;
- not voided, fully refunded, or fraud-rejected;
- not self-purchase under risk policy.

An economically free order funded entirely by excluded non-withdrawable value does not qualify as a commissionable first payment.

---

## 12. Renewal Rules

Renewal is handled at the `renewal_orders` layer.

Canonical rules:

- renewals are new orders, not mutations of the originating order;
- renewal ownership inherits from the originating commissionable chain unless a stronger persistent commercial binding exists;
- consumer referral credits do not create renewal ownership;
- renewal payout eligibility uses renewal policy effective at renewal creation;
- historical provenance remains even when payout eligibility changes.

---

## 13. Brand And Storefront Rules

Canonical rules:

- official CyberVPN and partner-branded storefronts are separate public commercial surfaces;
- brand, storefront, auth realm, merchant profile, support profile, and communication profile are distinct concepts;
- customer accounts are realm-scoped, not globally shared;
- partner-branded credentials do not automatically log in to CyberVPN official surfaces;
- the same person may hold separate accounts under different realms if policy allows;
- risk analysis may correlate abuse across realms without breaking customer-visible isolation.

---

## 14. Finance Rules

Canonical rules:

- consumer finance and partner finance are distinct domains;
- wallet is not the accounting system for partner settlement;
- partner payouts are driven through holds, statements, reserves, adjustments, and payout executions;
- disputes and chargebacks must flow through typed financial adjustment rules;
- no hard-delete of financial objects.

---

## 15. Risk And Governance Rules

Canonical rules:

- risk foundation applies early to eligibility and anti-abuse decisions;
- cross-realm abuse detection is allowed for internal risk operations;
- traffic declarations and policy acceptance must be versioned;
- creative and claims controls are enforceable through governance tooling;
- payout freeze, reserve extension, and code suspension are explicit governance actions;
- every sensitive decision needs actor attribution and audit trail.

Banned behaviors include:

- unauthorized brand PPC;
- trademark bidding or misspellings;
- spam;
- bots and fake traffic;
- cookie stuffing;
- fake reviews;
- adware, popunders, forced redirects;
- misleading privacy or anonymity claims.

---

## 16. Acceptance Conditions

The rulebook is satisfied only when:

- every domain spec and implementation plan preserves these invariants;
- no delivery shortcut overrides the canonical business rules;
- finance, support, risk, and growth teams use the same rule interpretations.
