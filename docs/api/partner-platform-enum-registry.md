# CyberVPN Partner Platform Enum Registry

**Date:** 2026-04-17  
**Status:** Canonical enum baseline for `T0.1`

This registry freezes the minimum enum vocabulary that later phases must reuse.

## 1. Naming Discipline

- Singular names identify one canonical object or enum family.
- Plural names identify collections, tables, or API collections.
- `payment_dispute` is the canonical dispute object name.
- `payment_disputes` is the canonical collection name.

## 2. Commercial Owner Types

- `none`
- `affiliate`
- `performance`
- `reseller`
- `direct_store`

Semantics:

- `none` = no payout-relevant commercial owner exists.
- `direct_store` = first-party direct ownership for analytics and provenance, without partner payout semantics.

## 3. Attribution Touchpoint Types

- `explicit_code`
- `passive_click`
- `deep_link`
- `qr_scan`
- `storefront_origin`
- `campaign_params`
- `invite_redemption`
- `postback`
- `manual_support_action`

## 4. Commercial Owner Sources

- `explicit_code`
- `passive_click`
- `persistent_reseller_binding`
- `storefront_default`
- `manual_override`
- `contract_assignment`

## 5. Customer Commercial Binding Enums

`binding_type` values:

- `reseller_binding`
- `storefront_default_owner`
- `manual_override`
- `contract_assignment`

`binding_status` values:

- `active`
- `released`
- `superseded`

## 6. Growth Reward Types

- `invite_reward`
- `referral_credit`
- `bonus_days`
- `gift_bonus`

## 7. Policy Lifecycle Enums

`approval_state` values:

- `draft`
- `approved`
- `rejected`

`version_status` values:

- `draft`
- `active`
- `superseded`
- `archived`

## 8. Payment Dispute Normalization

Canonical dispute subtypes:

- `inquiry`
- `warning`
- `chargeback`
- `dispute_reversal`
- `second_chargeback`

Canonical outcome classes:

- `open`
- `won`
- `lost`
- `reversed`

Canonical dispute lifecycle statuses:

- `opened`
- `evidence_required`
- `evidence_submitted`
- `under_review`
- `closed`

## 9. Refund Lifecycle

- `requested`
- `processing`
- `succeeded`
- `failed`
- `cancelled`

## 10. Risk Workflow

`risk_review.status` values:

- `open`
- `resolved`
- `dismissed`

`risk_review.decision` values:

- `pending`
- `allow`
- `block`
- `monitor`
- `hold`

`governance_action.action_type` values:

- `payout_freeze`
- `code_suspension`
- `reserve_extension`
- `traffic_probation`
- `creative_restriction`
- `manual_override`

`governance_action.action_status` values:

- `requested`
- `applied`
- `cancelled`

## 11. Operational Overlays

`partner_traffic_declaration.declaration_kind` values:

- `approved_sources`
- `postback_readiness`

`partner_traffic_declaration.declaration_status` values:

- `submitted`
- `action_required`
- `under_review`
- `complete`
- `blocked`

`creative_approval.approval_kind` values:

- `creative_approval`

`creative_approval.approval_status` values:

- `submitted`
- `action_required`
- `under_review`
- `complete`
- `blocked`

`dispute_case.case_kind` values:

- `payout_dispute`
- `chargeback_review`
- `evidence_collection`
- `reserve_review`

`dispute_case.case_status` values:

- `open`
- `waiting_on_partner`
- `waiting_on_ops`
- `resolved`
- `closed`

Canonical rule:

- `traffic_declaration` is the partner-submitted operational declaration object;
- `creative_approval` is the operator-reviewed approval overlay, not a storefront-only content flag;
- `dispute_case` is an operational case object linked to canonical `payment_dispute`, not a second dispute truth.

## 12. Pilot Control

`pilot_cohort.lane_key` values:

- `invite_gift`
- `consumer_referral`
- `creator_affiliate`
- `performance_media_buyer`
- `reseller_distribution`

`pilot_cohort.surface_key` values:

- `official_web`
- `partner_storefront`
- `partner_portal`
- `miniapp`
- `telegram_bot`
- `desktop_client`

`pilot_cohort.cohort_status` values:

- `scheduled`
- `active`
- `paused`
- `completed`
- `cancelled`

`pilot_rollout_window.window_kind` values:

- `host`
- `partner_workspace`
- `channel`

`pilot_rollout_window.window_status` values:

- `scheduled`
- `active`
- `paused`
- `closed`

`pilot shadow gate` values:

- `green`
- `yellow`
- `red`

`pilot_owner_acknowledgement.owner_team` values:

- `platform`
- `finance_ops`
- `risk_ops`
- `support`
- `partner_ops`
- `qa`

`pilot_owner_acknowledgement.acknowledgement_status` values:

- `acknowledged`

`pilot_rollback_drill.rollback_scope_class` values:

- `config_rollback`
- `traffic_rollback`
- `decision_path_rollback`
- `availability_rollback`
- `containment_mode`

`pilot_rollback_drill.drill_status` values:

- `passed`
- `failed`

`pilot_go_no_go_decision.decision_status` values:

- `approved`
- `hold`
- `no_go`

Canonical rule:

- `pilot_cohort` is the backend-owned pilot activation object for limited real traffic;
- `pilot_rollout_window` is the explicit host, workspace, or channel exposure window attached to one cohort;
- `pilot_owner_acknowledgement` is the signed owner-by-owner runbook acknowledgement object, not a checklist hidden in chat or spreadsheets;
- `pilot_rollback_drill` is the canonical record that a bounded rollback path was actually exercised before activation;
- `pilot_go_no_go_decision` is the explicit approve, hold, or no-go record tied to live metrics, rollback scope, and evidence links;
- pilot pause and activation state must never be inferred from frontend-only flags.

## 13. Commissionability Lifecycle

- `pending`
- `eligible`
- `ineligible`

## 14. Settlement Event Lifecycle

`earning_event.event_status` values:

- `on_hold`
- `available`
- `blocked`
- `reversed`

`earning_hold.hold_reason_type` values:

- `payout_hold`
- `risk_review`
- `manual`
- `reserve`
- `dispute`

`earning_hold.hold_status` values:

- `active`
- `released`
- `superseded`
- `expired`

`reserve.reserve_scope` values:

- `partner_account`
- `earning_event`

`reserve.reserve_reason_type` values:

- `risk_buffer`
- `dispute_buffer`
- `manual`

`reserve.reserve_status` values:

- `active`
- `released`

`settlement_period.period_status` values:

- `open`
- `closed`

`partner_statement.statement_status` values:

- `open`
- `closed`

`partner_payout_account.account_status` values:

- `active`
- `suspended`
- `archived`

`partner_payout_account.verification_status` values:

- `pending`
- `verified`

`partner_payout_account.approval_status` values:

- `pending`
- `approved`

`payout_instruction.instruction_status` values:

- `pending_approval`
- `approved`
- `rejected`
- `completed`

`payout_execution.execution_mode` values:

- `dry_run`
- `live`

`payout_execution.execution_status` values:

- `requested`
- `submitted`
- `succeeded`
- `failed`
- `reconciled`
- `cancelled`

`statement_adjustment.adjustment_type` values:

- `manual`
- `refund_clawback`
- `dispute_clawback`
- `reserve_application`
- `reserve_release`

`statement_adjustment.adjustment_direction` values:

- `credit`
- `debit`

## 14. Partner Integration Credentials

`partner_integration_credential.credential_kind` values:

- `reporting_api_token`
- `postback_secret`

`partner_integration_credential.credential_status` values:

- `ready`
- `pending_rotation`
- `blocked`

`partner_integration_delivery.channel` values:

- `reporting_export`
- `postback`

`partner_integration_delivery.status` values:

- `delivered`
- `failed`
- `paused`

## 15. Renewal Modes

- `manual`
- `auto`

## 16. Service Access Foundation

`service_identity.identity_status` values:

- `active`
- `suspended`
- `revoked`

`provisioning_profile.profile_status` values:

- `draft`
- `active`
- `archived`

`entitlement_grant.grant_status` values:

- `pending`
- `active`
- `suspended`
- `revoked`
- `expired`

`entitlement_grant.source_type` values:

- `order`
- `growth_reward`
- `renewal`
- `manual`

`device_credential.credential_type` values:

- `mobile_device`
- `desktop_client`
- `telegram_bot`
- `subscription_token`

`device_credential.credential_status` values:

- `active`
- `revoked`
- `expired`

`access_delivery_channel.channel_type` values:

- `subscription_url`
- `shared_client`
- `telegram_bot`
- `desktop_manifest`

`access_delivery_channel.channel_status` values:

- `active`
- `suspended`
- `archived`

## 15. Surface Policy Capabilities

- `external_code_override`
- `same_owner_only_codes`
- `promo_stacking`
- `wallet_spend`
- `invite_redemption`
- `referral_discount`
- `customer_facing`
- `operator_facing`

## 16. Reporting Outbox Lifecycle

`outbox_event.event_status` values:

- `pending_publication`
- `partially_published`
- `published`
- `failed`

`outbox_publication.publication_status` values:

- `pending`
- `claimed`
- `submitted`
- `published`
- `failed`

## 17. Reserved Terms

These terms are reserved and must not be redefined with conflicting semantics in later phases:

- `partner_payout_accounts`
- `entitlements`
- `accepted_legal_documents`
- `surface_policy_matrix_versions`
- `growth_reward_allocations`
- `earning_events`
- `earning_holds`
- `partner_statements`
- `settlement_periods`
- `statement_adjustments`
- `reserves`
- `service_identities`
- `provisioning_profiles`
- `device_credentials`
- `access_delivery_channels`
- `outbox_events`
- `outbox_publications`
