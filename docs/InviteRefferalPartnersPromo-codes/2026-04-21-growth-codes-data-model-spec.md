# Growth Codes Data Model Spec

**Date:** 2026-04-21  
**Status:** target-state backend data model baseline

---

## 1. Design Goal

The data model must support:

- typed code registry
- issuance tracking
- touchpoint tracking
- signup attribution
- type-specific policy tables
- checkout reservations
- redemption audit
- reward allocation
- fraud review
- policy versioning

It must not collapse all business semantics into one untyped discount table.

---

## 2. Base Registry

## 2.1 `growth_codes`

Common registry for invite, referral, promo and gift code identities.

Suggested fields:

- `id`
- `code_hash`
- `code_prefix`
- `code_type`
- `status`
- `issuer_type`
- `issuer_admin_id`
- `owner_user_id`
- `owner_partner_account_id`
- `campaign_id`
- `batch_id`
- `storefront_id`
- `auth_realm_id`
- `policy_version_id`
- `starts_at`
- `expires_at`
- `max_uses`
- `uses_count`
- `created_at`
- `updated_at`
- `revoked_at`
- `revoked_by_admin_id`
- `revoked_reason`

Notes:

- invite and gift codes should be stored hashed
- plaintext should never be used as a reporting key

---

## 3. Issuance And Ownership Tables

## 3.1 `growth_code_issuances`

This table explains why a code exists.

Fields:

- `id`
- `growth_code_id`
- `issuance_type`
- `issued_to_user_id`
- `issued_to_partner_account_id`
- `issued_by_admin_id`
- `source_order_id`
- `source_payment_id`
- `source_plan_sku`
- `source_bundle_snapshot`
- `reason_code`
- `admin_note`
- `created_at`

Examples of `issuance_type`:

- `plan_invite_bundle`
- `admin_manual_grant`
- `support_compensation`
- `gift_purchase`
- `gift_batch`
- `marketing_campaign`
- `conversion_reward`

---

## 4. Touchpoint And Attribution Tables

## 4.1 `growth_code_touchpoints`

This table tracks click, open or manual entry before final redemption.

Fields:

- `id`
- `growth_code_id`
- `code_type`
- `anonymous_session_id`
- `registered_user_id`
- `risk_subject_id`
- `storefront_id`
- `auth_realm_id`
- `surface`
- `channel`
- `utm_source`
- `utm_medium`
- `utm_campaign`
- `click_id`
- `sub_id`
- `ip_hash`
- `user_agent_hash`
- `created_at`
- `converted_to_signup_at`
- `converted_to_order_id`

## 4.2 `growth_signup_attributions`

This table links signup to growth code attribution.

Fields:

- `id`
- `user_id`
- `growth_code_id`
- `code_type`
- `touchpoint_id`
- `attribution_source`
- `storefront_id`
- `auth_realm_id`
- `risk_subject_id`
- `created_at`

Examples of `attribution_source`:

- `invite_link`
- `referral_link`
- `gift_link`
- `promo_landing`
- `manual_code_entry`

---

## 5. Type-Specific Policy Tables

## 5.1 `invite_code_policies`

Fields:

- `growth_code_id`
- `friend_days`
- `entitlement_profile_key`
- `conversion_reward_policy_id`
- `self_redemption_block`
- `risk_ruleset_id`

## 5.2 `referral_program_policies`

Fields:

- `growth_code_id` or reusable program key
- `friend_discount_type`
- `friend_discount_value`
- `eligible_durations`
- `eligible_plan_families`
- `reward_type`
- `reward_value`
- `hold_days`
- `monthly_cap`
- `lifetime_cap`
- `anti_abuse_policy_id`

## 5.3 `promo_code_policies`

Fields:

- `growth_code_id`
- `discount_type`
- `discount_value`
- `max_discount_amount`
- `eligible_plan_families`
- `eligible_durations`
- `eligible_addons`
- `allowed_checkout_modes`
- `allowed_channels`
- `allowed_geos`
- `min_net_paid_amount`
- `usage_cap_per_user`
- `global_usage_cap`

## 5.4 `gift_code_policies`

Fields:

- `growth_code_id`
- `grant_type`
- `plan_family`
- `duration_days`
- `entitlement_snapshot`
- `redemption_mode`
- `transferable`
- `batch_id`

---

## 5.5 Policy Versioning Requirements

Every policy family should support:

- `effective_from`
- `effective_to`
- `status`

Suggested statuses:

- `draft`
- `active`
- `superseded`
- `archived`

Finalized order, redemption and reward records must reference:

- exact `policy_version_id`
- policy snapshot where needed

Quote and reservation records must lock the policy version that was evaluated at quote time. Commit and redemption flows must either reuse that version safely or reject with a structured conflict.

---

## 6. Resolution, Reservation And Redemption Tables

## 6.1 `growth_code_resolution_events`

Stores all resolution attempts, including failures.

Fields:

- `id`
- `growth_code_id` nullable when raw code is unknown
- `raw_code_hash`
- `code_type` nullable until resolved
- `user_id` nullable
- `anonymous_session_id`
- `checkout_session_id` nullable
- `order_id` nullable
- `surface`
- `action_context`
- `result`
- `reject_reason`
- `conflict_code`
- `policy_version_id`
- `risk_decision_id` nullable
- `created_at`

Examples of `reject_reason`:

- `code_not_found`
- `code_expired`
- `code_exhausted`
- `not_eligible_for_sku`
- `not_eligible_for_surface`
- `conflicts_with_partner_code`
- `conflicts_with_promo`
- `blocked_by_risk`
- `self_redemption_blocked`
- `already_redeemed`

## 6.2 `growth_code_reservations`

Needed for safe checkout and single-use flows.

Fields:

- `id`
- `growth_code_id`
- `checkout_session_id`
- `user_id`
- `reserved_at`
- `expires_at`
- `status`
- `consumed_order_id`
- `released_at`
- `release_reason`
- `created_at`

Statuses:

- `reserved`
- `consumed`
- `expired`
- `released`
- `cancelled`

## 6.3 `growth_code_redemptions`

Stores final successful code usage.

Fields:

- `id`
- `growth_code_id`
- `code_type`
- `redeemer_user_id`
- `beneficiary_user_id`
- `order_id` nullable
- `entitlement_grant_id` nullable
- `wallet_transaction_id` nullable
- `reward_allocation_id` nullable
- `storefront_id`
- `auth_realm_id`
- `risk_decision_id`
- `status`
- `redeemed_at`
- `reversed_at`
- `reversal_reason`
- `created_at`

---

## 7. Reward Tables

## 7.1 `growth_reward_allocations`

Fields:

- `id`
- `reward_type`
- `source_code_id`
- `source_redemption_id`
- `source_order_id`
- `receiver_user_id`
- `amount_usd` nullable
- `bonus_days` nullable
- `extra_invites_count` nullable
- `status`
- `hold_until`
- `available_at`
- `reversed_at`
- `reversal_reason`
- `wallet_transaction_id` nullable
- `created_at`

---

## 8. Gift-Specific Tables

## 8.1 `gift_code_batches`

Batch metadata for admin or approved reseller issue.

Suggested fields:

- `id`
- `issuer_type`
- `created_by_admin_id`
- `reseller_partner_account_id` nullable
- `count`
- `plan_family`
- `duration_days`
- `expires_at`
- `export_allowed`
- `status`
- `created_at`

## 8.2 `gift_code_items`

Individual issued gift identities and batch membership.

Suggested fields:

- `id`
- `gift_batch_id`
- `growth_code_id`
- `status`
- `assigned_recipient_email_hash` nullable
- `redeemed_at` nullable
- `created_at`

## 8.3 `gift_purchases`

Audit of purchased gift transactions.

Suggested fields:

- `id`
- `purchaser_user_id`
- `purchase_order_id`
- `gift_code_id`
- `plan_family`
- `duration_days`
- `recipient_email_hash`
- `recipient_message_snapshot`
- `status`
- `created_at`
- `refunded_at`

## 8.4 `gift_redemptions`

Explicit gift redemption history and entitlement linkage.

Suggested fields:

- `id`
- `gift_code_id`
- `redeemer_user_id`
- `entitlement_grant_id`
- `redeemed_at`
- `status`
- `risk_decision_id`

---

## 9. Referral-Specific Tables

## 9.1 `referral_codes`

Persistent user-owned referral identity.

## 9.2 `referral_relationships`

Links referrer and referred user.

## 9.3 `referral_reward_allocations`

Optional projection or subtype of `growth_reward_allocations`.

---

## 10. Audit Requirements

All mutable code operations must record:

- actor
- timestamp
- before and after status
- reason
- linked order or redemption
- policy version

Recommended audit-linked actions:

- manual invite grant
- expiry extension
- promo pause or revoke
- gift batch issue
- referral reward reversal

---

## 11. Tracking Rule

No code implementation is complete unless the data model can connect:

- issuance
- touchpoint
- signup attribution
- resolution event
- reservation
- redemption
- reward allocation
- admin audit

---

## 12. Hashing And Secrecy

- store hashed invite and gift values
- do not expose raw code values in logs
- allow prefix lookup only for operator support UX
- use HMAC-style protected hashing for raw code lookups and resolution events
- brute-force attempts must be rate-limited and recorded

---

## 13. Modeling Rule

Shared registry is allowed.

Shared business semantics are not.

Registry is for identity, status and policy linkage. Typed tables define meaning.
