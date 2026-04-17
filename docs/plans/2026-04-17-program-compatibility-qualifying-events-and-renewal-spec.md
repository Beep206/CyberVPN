# CyberVPN Program Compatibility, Qualifying Events, And Renewal Spec

**Date:** 2026-04-17  
**Status:** Domain specification  
**Purpose:** define the compatibility matrix, qualifying-event rules, renewal ownership model, and recurring-economics rules for the five-lane CyberVPN partner platform.

---

## 1. Document Role

This document turns compatibility, qualification, and renewal rules into a dedicated spec so backend, frontend, finance, and support do not make local interpretations.

---

## 2. Stacking Model

Commercial discount instruments:

- promo
- creator code discount
- reseller price override
- consumer referral discount

Settlement instruments:

- wallet spend
- non-withdrawable wallet credit

Growth reward outputs:

- invite reward
- referral credit
- bonus days
- gift bonus

Default rule:

- one commercial discount instrument at a time unless policy explicitly allows more.

---

## 3. Surface Compatibility

Each surface must declare:

- accepted code types;
- whether external override is allowed;
- whether wallet spend is allowed;
- whether invite redemption is allowed;
- whether consumer referral discount is allowed;
- whether same-owner-only restrictions apply.

This matrix must exist as typed policy, not only as prose or frontend conditionals.

---

## 4. Qualifying First Payment

A qualifying first payment requires:

- eligible offer and SKU;
- eligible program policy version;
- positive commissionable economic amount;
- not voided or fully refunded;
- not rejected by risk policy.

Orders funded entirely through excluded non-withdrawable value are not commissionable first payments.

---

## 5. Renewal Model

Renewals must be represented as `renewal_orders`.

Canonical rules:

- renewals are new orders;
- renewal provenance remains linked to original acquisition;
- payout eligibility for renewals is policy-driven;
- renewal ownership does not automatically imply renewal payout;
- partner inactivity or suspension can block payout while preserving provenance.

---

## 6. Upgrade And Downgrade Effects

The spec must support policy decisions for:

- plan upgrades mid-cycle;
- plan downgrades on future renewal;
- addon changes between cycles;
- policy changes between quote and renewal.

The platform must preserve provenance while allowing renewal economics to follow current eligible policy.

---

## 7. Acceptance Conditions

This spec is acceptable only when:

- stacking rules are machine-evaluable;
- qualifying-event rules are explicit;
- renewal provenance and payout semantics are distinct;
- support and finance can explain why a renewal did or did not generate partner earnings.
