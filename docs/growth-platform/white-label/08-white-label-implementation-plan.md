# White-Label Implementation Plan

## Milestone 1 — Domain and Policy Foundation

- [ ] Add `PartnerBot` domain
- [ ] Add `PartnerBotCredential`
- [ ] Add `PartnerBotProvisioningJob`
- [ ] Add `PartnerBrandTheme`
- [ ] Add `PartnerCommercialPolicy`
- [ ] Add `PartnerSettlementAccount`
- [ ] Add `PartnerSettlementLedgerEntry`
- [ ] Add `PartnerRiskProfile`

Acceptance criteria:

- core entities exist with lifecycle states;
- partner runtime no longer depends on static brand defaults alone.

## Milestone 2 — Provisioning Control Plane

- [ ] Create partner bot API namespace
- [ ] Implement provisioning state machine
- [ ] Implement webhook binding health
- [ ] Implement token rotation flow
- [ ] Add managed bot integration spike
- [ ] Add manual token fallback path

Acceptance criteria:

- provisioning job can move draft bot to active or failed state with traceable reasons.

## Milestone 3 — Portal UX and Self-Service Wizard

- [ ] Expand onboarding wizard
- [ ] Add brand editor
- [ ] Add pricing simulator
- [ ] Add provisioning progress UI
- [ ] Add Mini App and storefront previews

Acceptance criteria:

- approved partner can complete the flow without developer intervention.

## Milestone 4 — Analytics and Finance

- [ ] Add partner analytics projections
- [ ] Add payout dashboard
- [ ] Add payout request flow
- [ ] Add hold and settlement status handling
- [ ] Add refund reversal and append-only ledger derivation

Acceptance criteria:

- partner sees conversion and revenue data tied to actual attribution context.

## Milestone 5 — Moderation and Hardening

- [ ] Add KYB levels and risk score integration
- [ ] Add moderation workflow for branding
- [ ] Add emergency suspend tooling
- [ ] Add audit logs for all sensitive mutations
- [ ] Add operator workflows for refund review and payout holds

Acceptance criteria:

- platform can safely stop or restrict a partner without data ambiguity.

## Database Tasks

- new partner bot and commercial tables;
- new settlement and risk tables;
- brand theme and storefront runtime DB alignment.

## Backend Tasks

- partner bot APIs;
- provisioning worker and orchestration services;
- analytics and settlement read models;
- moderation and audit support.

## Frontend Tasks

- wizard extensions;
- preview surfaces;
- provisioning status UI;
- finance and analytics modules.

## Bot Runtime Tasks

- tenant-aware bot runtime context;
- command and menu configuration;
- branding and support resolution;
- partner attribution binding.

## QA Tasks

- provisioning path tests;
- tenant isolation tests;
- payout request tests;
- partner sale attribution E2E.
