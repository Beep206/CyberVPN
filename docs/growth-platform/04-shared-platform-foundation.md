# Shared Platform Foundation

## Purpose

This document defines the common platform model required by Mini App, White-Label, and Network Intelligence. It is the most important planning document in the dossier because it prevents each feature from inventing its own identity, payment, attribution, and analytics rules.

## Shared Platform Entities

### User

Canonical customer identity across all customer-facing surfaces.

### TelegramIdentity

Telegram-specific identity material used for validated Telegram sessions, bot attribution, and Mini App binding.

### IdentityLink

Links one user to one provider identity in one tenant-aware context.

### PartnerWorkspace

Owns partner onboarding state, brand, commercial policy, and operational status.

### Entitlement

The source of truth for service access. Never create a separate entitlement system for partner customers.

### Payment

Represents money movement or platform-recognized payment state across surfaces.

### PartnerSettlementLedgerEntry

Immutable settlement record for partner finance and payout readiness.

### AttributionContext

Represents source, campaign, referral, partner, bot, storefront, and start parameter metadata for every acquisition and sale event.

## Identity Model

Identity should be layered:

1. Canonical user
2. External identity provider links
3. Surface session
4. Tenant-aware runtime context

Recommended provider types:

- `telegram`
- `email`
- `wallet`
- `partner_customer`

Recommended `IdentityLink` fields:

- `id`
- `userId`
- `provider`
- `providerUserId`
- `tenantId`
- `verifiedAt`
- `createdAt`

## TelegramIdentity

Telegram identity should track:

- Telegram user ID
- username and display hints
- last validated init data timestamp
- linked bot or managed bot context when applicable
- partner tenant association where applicable
- risk flags and abuse counters

Backend validation of raw Telegram init data is mandatory for trust decisions.

## PartnerWorkspace

Partner workspace is the top-level tenant object for White-Label:

- application and moderation status;
- brand theme;
- commercial policy;
- storefront binding;
- bot inventory;
- settlement accounts;
- risk profile.

## Tenant Context

Every partner-aware runtime must resolve:

- `tenant.kind`: `platform` or `partner`
- `partnerId`
- `workspaceId`
- `storefrontId`
- `botId`
- brand and support profile
- commercial policy reference
- attribution metadata

No partner surface should rely on an implicit default tenant.

## Subscription and Entitlement Model

The core rule is:

`Payment -> Order -> Entitlement -> Device/Config Access`

Partner context should be metadata on top of the same commercial and entitlement chain. It must not create a second service-access model.

Required entitlement dimensions:

- plan and duration;
- traffic policy;
- device limit;
- add-ons;
- service identity or provisioning profile;
- suspension or grace state.

## Payment Model

Required shared payment properties:

- payment method and provider;
- surface;
- tenant context;
- attribution context;
- order reference;
- platform settlement state;
- support and refund state.

Policy by surface:

- Telegram Mini App and bots use Telegram Stars as the primary rail.
- External web or storefront surfaces may use approved non-Telegram rails.

## Immutable Settlement Ledger

Partner balance must be derived from append-only ledger entries instead of mutable balance-only state.

Recommended entry types:

- `sale_credit`
- `refund_reversal`
- `payout_debit`
- `hold_applied`
- `hold_released`
- `adjustment`

Recommended fields:

- `id`
- `workspaceId`
- `partnerId`
- `paymentId`
- `saleId`
- `entryType`
- `amount`
- `currency`
- `effectiveAt`
- `createdAt`
- `reasonCode`

Rules:

- never mutate historical financial entries;
- derive payout-ready balance from ledger state;
- record refunds and reversals as new entries.

## Attribution Model

Every acquisition and payment flow should record:

- source
- surface
- partner ID
- workspace ID
- storefront ID
- bot ID
- referral code
- campaign
- UTM map
- Telegram `start_param` where available

This is required so that partner revenue, referral reward, and funnel analytics all reconcile from one model.

## Referral Model

Referral is a platform entity, not a front-end trick. It should support:

- platform-wide referrals;
- partner-scoped referrals;
- signed Telegram payloads;
- share message generation;
- abuse detection;
- reward status and lifecycle.

## Analytics Event Taxonomy

All events should have:

- event name;
- timestamp;
- user or anonymous ID;
- surface;
- locale;
- tenant context;
- attribution context;
- request correlation ID when relevant.

Examples of shared events:

- `user_registered`
- `trial_started`
- `checkout_started`
- `payment_success`
- `payment_cancelled`
- `entitlement_created`
- `config_delivered`
- `server_selected`
- `referral_shared`
- `partner_attributed_sale`
- `partner_ledger_entry_created`
- `partner_payout_hold_applied`
- `partner_payout_hold_released`

## Surface Taxonomy

Canonical surface labels:

- `customer_web`
- `customer_miniapp`
- `customer_bot`
- `customer_marketing_network`
- `customer_status_public`
- `partner_portal`
- `partner_storefront`
- `partner_bot_runtime`
- `partner_miniapp`
- `admin_portal`

These labels should be reused in:

- analytics;
- runtime metrics;
- payment events;
- abuse rules;
- dashboards.

## Feature Flags

Feature flags should be supported at:

- global platform level;
- surface level;
- tenant level;
- partner workspace level;
- release ring level.

Examples:

- `miniapp_checkout_stars_enabled`
- `partner_managed_bots_enabled`
- `public_network_dpi_enabled`
- `partner_widget_public_enabled`

## i18n Policy

The platform already supports a large locale set. Shared rules:

- platform copy remains centrally managed;
- partner branding can override selected text only where explicitly allowed;
- Mini App and public pages must support RTL-safe layouts;
- public pages should phase locale rollout based on translation and compliance readiness.

## Foundation Invariants

1. One customer identity model.
2. One entitlement model.
3. One attribution model.
4. One tenant context contract.
5. One analytics taxonomy.
6. One surface taxonomy.
7. No feature-specific shortcuts that bypass these shared entities.
8. Partner financial history is append-only and auditable.
