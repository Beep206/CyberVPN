# CyberVPN Commerce, Attribution, And Settlement Data Model Spec

**Date:** 2026-04-17  
**Status:** Data model specification  
**Purpose:** define the canonical entity set, relationships, snapshots, version references, and domain boundaries for commerce, attribution, growth rewards, disputes, and settlement data.

---

## 1. Document Role

This document defines the data-model layer for:

- commerce and orders;
- attribution and commercial ownership;
- growth rewards;
- merchant, billing, and dispute links;
- partner finance and settlement.

It focuses on data contracts and relationships, not UI or phased implementation.

## 1.1 Naming Convention

Naming convention for this package:

- singular form = canonical resource or object name in domain language
- plural form = collection, entity-set, endpoint-group, or table-family semantics

Examples:

- `payment_dispute` = one canonical dispute object
- `payment_disputes` = dispute entity set or API collection
- `growth_reward_allocation` = one reward allocation object
- `growth_reward_allocations` = reward allocation entity set
- `renewal_order` = one renewal order object
- `renewal_orders` = renewal-order entity set

---

## 2. Core Entity Groups

## 2.1 Commercial Sessions And Orders

Required entities:

- `quote_sessions`
- `checkout_sessions`
- `orders`
- `order_items`
- `payment_attempts`
- `refunds`
- `commissionability_evaluations`
- `renewal_orders`

## 2.2 Attribution And Rewards

Required entities:

- `attribution_touchpoints`
- `customer_commercial_bindings`
- `order_attribution_results`
- `growth_reward_allocations`

## 2.3 Merchant, Billing, And Disputes

Required entities:

- `merchant_profiles`
- `invoice_profiles`
- `billing_descriptors`
- `tax_calculation_snapshots`
- `payment_disputes`

## 2.4 Settlement

Required entities:

- `earning_events`
- `earning_holds`
- `earning_adjustments`
- `partner_statements`
- `partner_payout_accounts`
- `settlement_periods`
- `payout_instructions`
- `payout_executions`
- `reserves`
- `fx_rate_snapshots`

## 2.4.1 Canonical Payout Account Rule

`partner_payout_account` is a first-class canonical settlement entity.

It must not be treated only as embedded payout-destination data inside `payout_instruction` or `payout_execution`.

Canonical implications:

- `partner_payout_account` owns payout-destination identity and lifecycle;
- `payout_instruction` references a `partner_payout_account_id`;
- `payout_execution` references the instruction used and the resolved payout-account reference;
- verification, suspension, archival, and default-selection belong to the payout-account object itself.

Minimum domain fields expected on `partner_payout_account`:

- `partner_account_id`
- `settlement_profile_id` where relevant
- `payout_rail`
- masked destination details
- verification status
- approval state where required
- default indicator where allowed
- created_at
- updated_at
- disabled_at or archived_at where relevant

## 2.5 Operational Overlays Linked To Commerce And Settlement

Required linked operational entities:

- `partner_traffic_declarations`
- `creative_approvals`
- `dispute_cases`

---

## 3. Canonical Relationship Rules

1. One `quote_session` may lead to zero or one `checkout_session`.
2. One `checkout_session` may lead to zero or one `order`.
3. One `order` may contain many `order_items`.
4. One `order` may have many `payment_attempts`.
5. One `order` may have many `refunds`.
6. One finalized `order` has at most one `order_attribution_result`.
7. One `order` may produce many `growth_reward_allocations`.
8. One `order` may produce many `earning_events`.
9. Many `earning_events` may roll into one `partner_statement`.
10. One `partner_payout_account` may be referenced by many `payout_instructions` and `payout_executions`.
11. One `payment_dispute` references one underlying commercial order, even if provider settlement references differ.
12. One `dispute_case` may aggregate one or more `payment_dispute` records plus operational evidence and decisions.
13. One `payout_instruction` references exactly one resolved `partner_payout_account`, even if the account was suggested by workspace defaults or operator choice.

---

## 4. Snapshot Strategy

The platform must snapshot on `order`:

- storefront
- auth realm
- merchant profile
- support profile
- communication profile where relevant
- pricebook version
- offer version
- eligibility version
- applied code version
- legal document set version where relevant
- tax snapshot
- billing descriptor snapshot
- attribution result reference
- growth reward allocation references
- entitlement result reference

Finalized commercial objects must not rely on mutable current-state configuration to remain explainable.

---

## 5. Version-Linked Objects

The data model must support linking finalized events to:

- `partner_code_versions`
- `commission_policy_versions`
- `discount_policy_versions`
- `markup_policy_versions`
- `attribution_policy_versions`
- `eligibility_policy_versions`
- `pricebook_versions`
- `offer_versions`
- `program_eligibility_versions`
- `surface_policy_matrix_versions`
- `storefront_legal_doc_set_versions`

---

## 6. Domain Boundaries In Data Terms

Commerce and Orders owns:

- sessions
- orders
- line items
- payment attempts
- refund linkage to orders

Attribution owns:

- touchpoints
- bindings
- attribution results
- commercial owner provenance

Growth Rewards owns:

- invite and referral reward allocations
- non-cash outputs

Merchant/Billing/Tax/Disputes owns:

- merchant snapshots
- invoices and tax snapshots
- billing descriptors
- dispute objects and evidence references

Settlement owns:

- earning consequences
- holds
- reserves
- `partner_payout_accounts` as first-class settlement entities
- payout account references from instructions and executions
- statement membership
- payout execution state

Operational overlays own:

- traffic declarations
- creative approval state
- dispute case handling

---

## 7. Required Audit Fields

Every financially or commercially significant entity should carry:

- immutable primary id
- created_at
- updated_at
- created_by actor where relevant
- approval actor where relevant
- source channel
- storefront_id
- auth_realm_id where relevant
- correlation_id or request_id where relevant
- status
- version reference where relevant

---

## 8. Acceptance Conditions

The data model is acceptable only when:

- orders are the canonical commercial record;
- attribution and growth rewards are separated;
- merchant and settlement consequences are explicit;
- finalized objects can be reconstructed from snapshots and version references;
- disputes and chargeback outcomes are normalized through canonical dispute records.
