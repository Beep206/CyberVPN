# Executive Summary

## Purpose

CyberVPN should implement Telegram Mini App, White-Label Partner Self-Service, and Real-Time Network Intelligence as one integrated growth platform. Each feature serves a different stage of the growth loop:

- `Network Intelligence` creates trust and acquisition.
- `Mini App` creates conversion inside Telegram.
- `White-Label` creates distribution scale through partners.

## Why These Three Features Belong Together

Building them separately would force the team to re-solve the same problems multiple times:

- identity linking across Telegram, web, and partner contexts;
- payment authorization and entitlement activation;
- partner attribution and referral logic;
- branded runtime behavior;
- observability and event taxonomy;
- network intelligence reuse across customer and partner surfaces.

The correct target is a shared core with multiple surfaces, not three isolated feature stacks.

## Business Outcome

The combined platform is intended to produce three effects:

1. More qualified top-of-funnel demand through public proof of network quality.
2. Faster in-Telegram activation and purchase with lower checkout friction.
3. Scalable distribution through partner-branded entry points that do not require manual operations per reseller.

## Strategic Thesis

### Network Intelligence

This is the public trust engine. It turns network performance into a visible product asset instead of a hidden operational metric. It should become a source for:

- public landing conversion;
- SEO traffic;
- server recommendation logic;
- partner widgets;
- trust reinforcement during checkout.

### Telegram Mini App

This is the canonical conversion runtime. It should become the fastest path from interest to active access:

- open bot or branded entry point;
- validate Telegram session;
- bootstrap status, trial, and offer context;
- purchase with Telegram Stars;
- deliver config and onboarding inside Telegram.

### White-Label

This is the distribution scaling layer. It converts the core CyberVPN platform into a partner-operated channel without fragmenting the product or operational model.

## Final Target Picture

The target operating model is:

- one shared payment, entitlement, referral, and analytics core;
- one canonical Mini App runtime that can run in platform and partner-branded modes;
- one partner platform that provisions brand, commercial policy, and bot identity without per-partner deployments;
- one public network data layer that powers public pages, partner widgets, and in-app server recommendations;
- one internal operations, risk, finance, and audit control plane that makes the platform production-safe.

## High-Level Roadmap

### Phase 0

- lock product and architecture decisions;
- accept key ADRs;
- define shared platform foundation.

### Phase 1

- fix Mini App routing and auth flow;
- create bootstrap-oriented Mini App API;
- create public network snapshot schema and worker skeleton;
- establish tenant-aware White-Label domain model;
- establish control-plane and migration sequencing baseline.

### Phase 2

- launch integrated Mini App purchase and config flow;
- replace public mock network blocks with sanitized snapshots;
- create partner bot provisioning alpha and branded previews;
- establish immutable settlement ledger and operator workflows.

### Phase 3

- commercialize White-Label onboarding and settlements;
- launch public Speed Map and status pages as truth-based products;
- add partner widgets and DPI probing.

## Key Risks

- Telegram payment compliance inside Telegram surfaces.
- Tenant data leakage across partner contexts.
- Public mock data being mistaken for operational truth.
- Overbuilding one feature without shared platform alignment.
- Managed Bots platform limitations or rollout edge cases.
- Weak operator tooling for refunds, payout disputes, suspensions, and public incidents.

## Main Decisions

- Telegram surfaces use Telegram Stars as the primary payment rail.
- White-Label uses a shared multi-tenant runtime, not one deployment per partner.
- Public Network surfaces read from sanitized snapshots, not directly from Prometheus.
- Mini App is the canonical conversion runtime for platform and partner-branded customer journeys.
- CyberVPN remains platform-of-record and merchant-of-record in the baseline model.
- Partner settlements use append-only ledger history rather than mutable balance-only accounting.

## Success Condition

The initiative succeeds when CyberVPN can:

- acquire users via public network proof;
- convert them via Telegram-native flows;
- distribute the same conversion engine through branded partner entry points;
- keep all payments, entitlements, partner attribution, analytics, refunds, payouts, and audit trails coherent in one platform model.
