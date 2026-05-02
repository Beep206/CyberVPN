# Growth Code Taxonomy And Compatibility Matrix

**Date:** 2026-04-21  
**Status:** target-state compatibility baseline

---

## 1. Taxonomy

| Code type | Main effect | Typical surface | Creates cash owner | Creates checkout discount | Creates entitlement |
| --- | --- | --- | --- | --- | --- |
| Invite | friend access for N days | client frontend | no | no | yes |
| Referral | friend discount + referrer reward | client frontend | no | yes | no |
| Promo | admin marketing discount | checkout + admin | no | yes | no |
| Gift | prepaid access or bonus entitlement | client + admin | no | sometimes indirect | yes |
| Partner | partner attribution / markup / earnings | partner platform | yes | sometimes | no |

---

## 2. Compatibility Matrix

| Combination | Default rule |
| --- | --- |
| promo + partner code | forbidden |
| referral discount + partner code | forbidden |
| referral discount + promo | forbidden |
| invite redemption + promo | not applicable |
| gift redemption + promo | forbidden by default |
| wallet + promo | allowed |
| wallet + referral discount | allowed |
| wallet + partner code | allowed |
| gift redemption + referral reward | forbidden |
| gift redemption + partner payout | forbidden |
| addon-only + referral reward | forbidden by default |
| addon-only + promo | allowed only if promo policy allows add-ons |
| upgrade + promo | allowed only if promo policy allows upgrades |
| renewal + promo | allowed only if promo policy allows renewals |

Partner binding rule:

- persistent partner binding counts as partner flow even when no explicit partner code is entered in the current checkout
- therefore `promo + partner_binding` and `referral_discount + partner_binding` are forbidden unless policy explicitly allows them

---

## 3. Checkout Mode Compatibility

| Code type | New purchase | Upgrade | Renewal | Add-on only | Redemption-only flow |
| --- | --- | --- | --- | --- | --- |
| Invite | no | no | no | no | yes |
| Referral | yes | no by default | no by default | no | no |
| Promo | yes | policy-driven | policy-driven | policy-driven | no |
| Gift | no | no | no | no | yes |
| Partner | yes | policy-driven | policy-driven | limited | no |

---

## 4. Surface Compatibility

| Code type | Client frontend | Admin | Partner portal |
| --- | --- | --- | --- |
| Invite | yes | yes | no |
| Referral | yes | yes | no |
| Promo | yes | yes | only approved assets |
| Gift | yes | yes | reseller-only capability |
| Partner | no direct management | yes | yes |

---

## 5. Wallet Compatibility

| Mechanism | Wallet allowed | Notes |
| --- | --- | --- |
| Promo discount | yes | wallet applies after discount |
| Referral friend discount | yes | wallet applies after discount |
| Invite redemption | no normal wallet path | handled as entitlement grant |
| Gift redemption | no normal wallet path | handled as entitlement grant |
| Partner code purchase | yes | payout rules depend on commissionable base |

Wallet bucket rule:

- growth rewards should use non-withdrawable wallet buckets
- promo is not a wallet credit by default
- gift and invite are not generic wallet top-ups

---

## 6. Channel Compatibility

Default allowed channels for customer growth codes:

- `web`
- `miniapp`
- `telegram_bot`
- future `mobile_app`, if added

Channel must always be policy-checked per code.

---

## 7. Tariff Compatibility

Default assumptions:

- referral friend discount applies only to qualifying `90 / 180 / 365` first paid orders
- invite bundle availability depends on specific term-level SKU
- promo must declare eligible plan families and durations
- gift should resolve into concrete plan family plus duration, not open-ended money balance

---

## 8. Conflict Priorities

If multiple codes are entered or implied, conflict order should be:

1. reject impossible code types together
2. reject policy-ineligible code for route or checkout mode
3. reject partner-growth conflicts
4. reject exhausted, expired or revoked code
5. return accepted typed effect

---

## 9. Canonical User Messages

Examples:

- `This promo code cannot be combined with a partner code.`
- `Referral benefits are available only on the first qualifying paid order.`
- `This gift code must be redeemed from the redeem flow, not the checkout discount box.`
- `This invite code has expired.`

---

## 10. Wrong-Context Handling

Examples:

- invite or gift entered in checkout discount box -> backend returns `wrong_context`
- promo entered in redeem flow -> backend returns `wrong_context`

Frontend must route user to the correct flow based on backend result.

---

## 11. Frozen Compatibility Outcome

The platform must never silently stack:

- partner revenue incentive with referral discount
- partner revenue incentive with promo discount
- gift redemption with payoutable reward logic

These are explicit conflicts, not frontend choices.
