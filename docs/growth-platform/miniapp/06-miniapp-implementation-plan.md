# Mini App Implementation Plan

## Delivery Strategy

Implement Mini App in milestones that harden the runtime first, then commercialize payment and server intelligence.

## Milestone 1 — Routing and Runtime

- [ ] Fix `/miniapp` root redirect to `/miniapp/home`
- [ ] Preserve `/miniapp/*` after auth success
- [ ] Preserve `/miniapp/*` after 2FA return
- [ ] Add canonical Mini App runtime provider
- [ ] Add bootstrap API client
- [ ] Add surface-aware analytics bootstrap event

Acceptance criteria:

- user never leaves Mini App namespace during normal auth flow;
- runtime provider exposes Telegram lifecycle hooks;
- home screen can render from bootstrap data.

## Milestone 2 — Bootstrap and Read Models

- [ ] Create `/api/v1/miniapp/bootstrap`
- [ ] Create `/api/v1/miniapp/offers`
- [ ] Create `/api/v1/miniapp/servers`
- [ ] Create `/api/v1/miniapp/config`
- [ ] Refactor home and plans to use Mini App API instead of broad client fan-out

Acceptance criteria:

- home and plans pages load from Mini App-specific contracts;
- bootstrap payload includes tenant-aware runtime context.

## Milestone 3 — Telegram Payment Flow

- [ ] Add Stars payment provider path
- [ ] Create quote endpoint
- [ ] Create invoice endpoint
- [ ] Integrate pre-checkout validation path
- [ ] Add invoice open and invoice closed handlers in frontend
- [ ] Add payment status refresh endpoint
- [ ] Add reconciliation worker hooks
- [ ] Add refund and duplicate-success handling tests

Acceptance criteria:

- user can complete purchase inside Telegram;
- entitlement activates only after authoritative success;
- duplicate or replayed payment events do not double-fulfill.

## Milestone 4 — Config, Devices, and Support

- [ ] Refine config delivery screen
- [ ] Add device summary and actions
- [ ] Add support and payment-support routes
- [ ] Add degraded and stale runtime states

Acceptance criteria:

- post-payment user can reach config reliably;
- expired or errored states direct user to support cleanly.

## Milestone 5 — Server Picker and Referral

- [ ] Add `/miniapp/servers`
- [ ] Integrate Network Intelligence recommendation data
- [ ] Add signed referral share payloads
- [ ] Add share tracking and abuse thresholds

Acceptance criteria:

- user sees recommended and manual server options;
- referrals preserve attribution safely.

## Backend Tasks

- Mini App namespace
- payment and quote support
- runtime context resolution
- trial eligibility integration
- telemetry and abuse counters

## Frontend Tasks

- runtime hooks
- routing cleanup
- bootstrap-driven pages
- payment state UX
- server picker and support UI

## Bot Tasks

- align entry links and `startapp` payload generation;
- expose payment support command or link path;
- align partner-branded entry metadata.

## QA Tasks

- route persistence tests
- payment and entitlement E2E
- referral integrity tests
- degraded runtime tests

## Dependencies

- shared tenant context contract
- Stars payment policy accepted
- event taxonomy accepted
- public network recommendation contract defined
