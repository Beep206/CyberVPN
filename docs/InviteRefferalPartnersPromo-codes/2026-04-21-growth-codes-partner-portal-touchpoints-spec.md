# Growth Codes Partner Portal Touchpoints Spec

**Date:** 2026-04-21  
**Status:** boundary spec

---

## 1. Purpose

This spec defines the small set of customer growth code touchpoints that may appear in the partner portal.

The goal is to avoid blending customer growth and partner revenue programs.

---

## 2. What Partner Portal May Show

Allowed:

- approved promo campaign assets
- campaign copy guidance
- disclosure requirements
- allowed geographies
- campaign expiry
- approved landing pages
- reseller voucher batches only when capability is explicitly enabled

---

## 3. What Partner Portal Must Not Show

Forbidden:

- consumer invite mechanics
- consumer referral screens
- customer reward wallets
- customer gift purchase flow
- generic promo code creation
- customer reward leaderboards

---

## 4. Approved Promo Asset Model

Partner portal may expose:

- campaign name
- approved promo reference
- disclosure text
- allowed claims
- banned claims
- valid dates
- destination pages

Admin owns the promo itself.
Partner only sees approved campaign packaging.

---

## 5. Reseller Voucher Capability

Only approved reseller or distribution lanes may see:

- voucher batch visibility
- voucher redemption reporting
- voucher request flow

This is not general customer gift management.

---

## 6. Partner Analytics Boundaries

Partner analytics may show:

- campaign performance
- approved offer usage
- partner code performance

Partner analytics must not show:

- customer referral reward balances
- consumer invite conversion leaderboard
- customer gift purchase details

---

## 7. Compliance Touchpoints

Partner portal should show:

- disclosure instructions
- prohibited claims
- promo usage restrictions
- geographic restrictions

---

## 8. Boundary Rule

Customer growth logic remains customer-side and admin-owned.

Partner portal can consume campaign guidance, but it cannot become the control plane for invite, referral or generic promo creation.
