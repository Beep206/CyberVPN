# Growth Codes Analytics, Observability, And Reporting Spec

**Date:** 2026-04-21  
**Status:** target-state measurement baseline

---

## 1. Goal

Measure growth codes as a separate customer growth system, not as partner program analytics.

This spec covers three layers:

1. business growth metrics
2. admin and operational metrics
3. observability metrics

---

## 1.1 Metric Type Policy

Use metric types deliberately:

- counters for issued, redeemed, rejected, reversed and similar event totals
- gauges for currently active backlog, current balance and current liability
- histograms for resolver, redemption and checkout durations
- ratios from recording rules, not raw source metrics

Examples:

- `cybervpn_invites_issued_total` -> counter
- `cybervpn_referral_codes_active` -> gauge
- `cybervpn_growth_code_resolution_duration_seconds` -> histogram
- `cybervpn_invite:redemption_rate5m` -> recording rule

---

## 2. Invite Metrics

Track:

- invites issued
- invites issued by source
- invites redeemed
- invite redemption rate as derived query or recording rule
- invite-to-signup conversion
- invite-to-paid conversion
- expired invites
- revoked invites
- abuse-blocked invites
- source SKU of invite issuance
- owner rewards created

Suggested metrics:

- `cybervpn_invites_issued_total`
- `cybervpn_invites_issued_by_source_total`
- `cybervpn_invites_redeemed_total`
- `cybervpn_invite_to_signup_total`
- `cybervpn_invite_to_paid_conversion_total`
- `cybervpn_invite_expired_total`
- `cybervpn_invite_revoked_total`
- `cybervpn_invite_abuse_blocks_total`
- `cybervpn_invite_owner_rewards_created_total`

Suggested recording rules:

- `cybervpn_invite:redemption_rate5m`
- `cybervpn_invite:signup_rate5m`
- `cybervpn_invite:paid_conversion_rate5m`

Allowed labels:

- `source_type`
- `plan_family`
- `duration_days`
- `surface`
- `result`
- `reason_code`

---

## 3. Referral Metrics

Track:

- referral link clicks
- referred registrations
- referred first paid conversions
- qualifying orders
- rewards created
- pending rewards
- available rewards
- reversed rewards
- cap usage
- abuse blocks
- partner-upgrade candidates

Suggested metrics:

- `cybervpn_referral_codes_active`
- `cybervpn_referral_link_clicks_total`
- `cybervpn_referral_signups_total`
- `cybervpn_referral_qualifying_orders_total`
- `cybervpn_referral_rewards_created_total`
- `cybervpn_referral_rewards_available_transitions_total`
- `cybervpn_referral_rewards_reversed_total`
- `cybervpn_referral_available_credit_usd`
- `cybervpn_referral_cap_reached_total`
- `cybervpn_referral_abuse_blocks_total`
- `cybervpn_referral_partner_upgrade_candidates_total`

Allowed labels:

- `duration_days`
- `plan_family`
- `reward_status`
- `result`
- `reason_code`

---

## 4. Promo Metrics

Track:

- promo codes created
- promo attempts
- promo accepted
- promo rejected
- discount amount
- orders paid with promo
- refunds after promo
- revenue after discount
- leakage indicators

Suggested metrics:

- `cybervpn_promo_codes_created_total`
- `cybervpn_promo_resolution_attempts_total`
- `cybervpn_promo_codes_applied_total`
- `cybervpn_promo_rejections_total`
- `cybervpn_promo_discount_amount_usd_total`
- `cybervpn_promo_orders_paid_total`
- `cybervpn_promo_refunds_total`
- `cybervpn_promo_revenue_after_discount_usd_total`
- `cybervpn_promo_leakage_suspected_total`

Allowed labels:

- `campaign_type`
- `discount_type`
- `surface`
- `channel`
- `duration_days`
- `result`
- `reject_reason`

---

## 5. Gift Metrics

Track:

- gifts purchased
- gift purchase amount
- gifts issued
- gifts redeemed
- gift redemption failures
- gift expiry
- gift revocation
- gift liability
- gift refunds
- gift chargebacks
- recipient conversion after redemption

Suggested metrics:

- `cybervpn_gift_purchases_total`
- `cybervpn_gift_purchase_amount_usd_total`
- `cybervpn_gift_codes_issued_total`
- `cybervpn_gift_codes_redeemed_total`
- `cybervpn_gift_redemption_failures_total`
- `cybervpn_gift_codes_expired_total`
- `cybervpn_gift_codes_revoked_total`
- `cybervpn_gift_outstanding_liability_usd`
- `cybervpn_gift_breakage_usd_total`
- `cybervpn_gift_refunds_total`
- `cybervpn_gift_refunded_amount_usd_total`
- `cybervpn_gift_chargebacks_total`

`cybervpn_gift_outstanding_liability_usd` is a gauge. It should represent unpaid service obligation for unredeemed or otherwise still-owed gift entitlement, according to finance policy.

Allowed labels:

- `gift_type`
- `plan_family`
- `duration_days`
- `issuer_type`
- `surface`
- `result`
- `reason_code`

---

## 6. Admin And Operational Metrics

Suggested metrics:

- `cybervpn_growth_admin_code_grants_total`
- `cybervpn_growth_admin_code_revocations_total`
- `cybervpn_growth_admin_reward_reversals_total`
- `cybervpn_growth_admin_manual_adjustments_total`
- `cybervpn_growth_admin_code_lookup_total`
- `cybervpn_growth_admin_bulk_issue_total`

Allowed labels:

- `code_type`
- `admin_action_type`
- `reason_code`
- `result`

---

## 7. Resolver And Observability Metrics

Recommended metrics:

- `cybervpn_growth_code_resolution_total`
- `cybervpn_growth_code_resolution_duration_seconds`
- `cybervpn_growth_code_resolution_failures_total`
- `cybervpn_growth_code_redemptions_total`
- `cybervpn_growth_code_redemption_duration_seconds`
- `cybervpn_growth_code_reservations_reserved`
- `cybervpn_growth_code_reservation_expirations_total`

Allowed labels:

- `code_type`
- `action_context`
- `surface`
- `result`
- `reject_reason`

---

## 7.1 Recording Rules

Prefer derived rules instead of raw ratio metrics.

Recommended examples:

- `cybervpn_invite:redemption_rate5m`
- `cybervpn_referral:signup_to_paid_rate5m`
- `cybervpn_promo:accept_rate5m`
- `cybervpn_gift:redemption_rate5m`
- `cybervpn_growth_code:rejection_rate5m`

---

## 8. Forbidden Metric Labels

Do not use:

- `user_id`
- `code_value`
- `code_id`
- `order_id`
- `email`
- `ip`
- `telegram_id`

---

## 9. Required Dashboards

Recommended dashboards:

- Growth Codes Executive Overview
- Invite Funnel
- Referral Funnel And Reward Health
- Promo Performance
- Gift Issuance And Redemption
- Growth Code Abuse Review
- Growth Admin Operations
- Code Resolver Health

Growth Codes Executive Overview should show:

- issued codes by type
- redemptions by type
- signups by code type
- paid conversion by code type
- reward cost
- revenue impact
- fraud blocks
- gift liability

Invite dashboard should show:

- invites issued by source SKU
- redemption rate
- invite-to-paid conversion
- expired and revoked invites
- abuse blocks
- owner rewards

Referral dashboard should show:

- clicks
- signups
- qualifying purchases
- reward cost
- reversals
- caps reached
- partner-upgrade candidates

Promo dashboard should show:

- usage
- accepted and rejected attempts
- discount cost
- net revenue
- refund rate
- campaign performance
- leakage alerts

Gift dashboard should show:

- purchases
- issued, redeemed and expired counts
- outstanding liability
- refunds and chargebacks
- batch performance

Risk dashboard should show:

- self-referral blocks
- invite farming
- promo brute-force indicators
- gift abuse patterns

---

## 10. Canonical Events

Required events:

- `growth_code.issued`
- `growth_code.assigned`
- `growth_code.resolved`
- `growth_code.rejected`
- `growth_code.reserved`
- `growth_code.reservation_expired`
- `growth_code.redeemed`
- `growth_code.revoked`
- `invite.generated_from_order`
- `invite.redeemed`
- `invite.owner_reward_created`
- `referral.signup_attributed`
- `referral.qualifying_order_detected`
- `referral.reward_pending`
- `referral.reward_available`
- `referral.reward_reversed`
- `promo.applied_to_order`
- `promo.rejected`
- `promo.campaign_paused`
- `gift.purchased`
- `gift.issued`
- `gift.sent`
- `gift.redeemed`
- `gift.revoked`
- `gift.refunded`
- `admin.growth_code_granted`
- `admin.growth_code_revoked`
- `admin.growth_reward_reversed`

---

## 11. Reporting Rule

Growth analytics must stay separate from:

- partner payout reporting
- partner statement reporting
- partner attribution ownership reporting

They also must stay separate from raw low-level Prometheus-style operational metrics in user-facing business reports.
