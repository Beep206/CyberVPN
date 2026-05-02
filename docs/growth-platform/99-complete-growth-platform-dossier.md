# CyberVPN Growth Platform — Complete Consolidated Dossier

Этот файл агрегирует полное содержимое всех документов из `docs/growth-platform/` без сокращений. Исходные документы остаются канонической пофайловой структурой, а этот файл служит единым сквозным чтением.

## Included Documents

- `docs/growth-platform/00-index.md`
- `docs/growth-platform/01-executive-summary.md`
- `docs/growth-platform/02-product-strategy.md`
- `docs/growth-platform/03-target-architecture.md`
- `docs/growth-platform/04-shared-platform-foundation.md`
- `docs/growth-platform/05-roadmap-and-milestones.md`
- `docs/growth-platform/06-risk-register.md`
- `docs/growth-platform/07-analytics-and-kpi.md`
- `docs/growth-platform/08-security-and-abuse-prevention.md`
- `docs/growth-platform/09-testing-strategy.md`
- `docs/growth-platform/10-rollout-plan.md`
- `docs/growth-platform/11-open-questions.md`
- `docs/growth-platform/12-admin-control-plane.md`
- `docs/growth-platform/13-data-model-and-migrations.md`
- `docs/growth-platform/14-implementation-start-point.md`
- `docs/growth-platform/15-wave-1-shared-runtime-and-miniapp-foundation.md`
- `docs/growth-platform/16-wave-1-engineering-backlog-by-repo.md`
- `docs/growth-platform/17-wave-1-file-level-change-map.md`
- `docs/growth-platform/adr/ADR-001-telegram-stars-as-primary-telegram-payment-rail.md`
- `docs/growth-platform/adr/ADR-002-shared-multi-tenant-runtime-for-white-label.md`
- `docs/growth-platform/adr/ADR-003-public-network-snapshot-instead-of-direct-prometheus.md`
- `docs/growth-platform/adr/ADR-004-miniapp-as-canonical-conversion-runtime.md`
- `docs/growth-platform/adr/ADR-005-cybervpn-as-platform-of-record.md`
- `docs/growth-platform/miniapp/00-miniapp-overview.md`
- `docs/growth-platform/miniapp/01-miniapp-user-flows.md`
- `docs/growth-platform/miniapp/02-miniapp-technical-spec.md`
- `docs/growth-platform/miniapp/03-miniapp-api-contracts.md`
- `docs/growth-platform/miniapp/04-miniapp-payment-flow.md`
- `docs/growth-platform/miniapp/05-miniapp-security.md`
- `docs/growth-platform/miniapp/06-miniapp-implementation-plan.md`
- `docs/growth-platform/miniapp/07-miniapp-definition-of-done.md`
- `docs/growth-platform/network-intelligence/00-network-intelligence-overview.md`
- `docs/growth-platform/network-intelligence/01-public-speed-map-product-spec.md`
- `docs/growth-platform/network-intelligence/02-public-network-snapshot-spec.md`
- `docs/growth-platform/network-intelligence/03-network-api-contracts.md`
- `docs/growth-platform/network-intelligence/04-prometheus-aggregation-pipeline.md`
- `docs/growth-platform/network-intelligence/05-dpi-resistance-score.md`
- `docs/growth-platform/network-intelligence/06-seo-and-public-pages.md`
- `docs/growth-platform/network-intelligence/07-network-widget-spec.md`
- `docs/growth-platform/network-intelligence/08-network-implementation-plan.md`
- `docs/growth-platform/network-intelligence/09-network-definition-of-done.md`
- `docs/growth-platform/white-label/00-white-label-overview.md`
- `docs/growth-platform/white-label/01-partner-user-flows.md`
- `docs/growth-platform/white-label/02-white-label-domain-model.md`
- `docs/growth-platform/white-label/03-partner-bot-provisioning.md`
- `docs/growth-platform/white-label/04-partner-commercial-policy.md`
- `docs/growth-platform/white-label/05-white-label-api-contracts.md`
- `docs/growth-platform/white-label/06-partner-portal-ux.md`
- `docs/growth-platform/white-label/07-abuse-moderation-kyb.md`
- `docs/growth-platform/white-label/08-white-label-implementation-plan.md`
- `docs/growth-platform/white-label/09-white-label-definition-of-done.md`

---


---

## Source Document: `docs/growth-platform/00-index.md`

# CyberVPN Growth Platform Documentation

## Scope

This dossier defines the full implementation program for three linked growth features:

1. Telegram Mini App
2. White-Label Partner Self-Service Portal
3. Real-Time Network Intelligence / Speed Map

The intent is to treat them as one growth platform, not three disconnected projects.

## Why This Package Exists

CyberVPN already has meaningful building blocks across `frontend/`, `partner/`, `backend/`, `services/telegram-bot/`, and `infra/`. The goal of this documentation is to:

- align product and engineering on one target picture;
- prevent feature drift between Mini App, White-Label, and Network Intelligence;
- define shared platform entities up front;
- record irreversible architectural decisions;
- provide an execution-ready planning set before implementation starts.

## Reading Order

1. [Executive Summary](./01-executive-summary.md)
2. [Product Strategy](./02-product-strategy.md)
3. [Target Architecture](./03-target-architecture.md)
4. [Shared Platform Foundation](./04-shared-platform-foundation.md)
5. [Mini App dossier](./miniapp/00-miniapp-overview.md)
6. [White-Label dossier](./white-label/00-white-label-overview.md)
7. [Network Intelligence dossier](./network-intelligence/00-network-intelligence-overview.md)
8. [Roadmap and Milestones](./05-roadmap-and-milestones.md)
9. [Risk Register](./06-risk-register.md)
10. [Analytics and KPI](./07-analytics-and-kpi.md)
11. [Security and Abuse Prevention](./08-security-and-abuse-prevention.md)
12. [Testing Strategy](./09-testing-strategy.md)
13. [Rollout Plan](./10-rollout-plan.md)
14. [Open Questions](./11-open-questions.md)
15. [Admin Control Plane](./12-admin-control-plane.md)
16. [Data Model and Migrations](./13-data-model-and-migrations.md)
17. [Implementation Start Point](./14-implementation-start-point.md)
18. [Wave 1 Execution Backlog](./15-wave-1-shared-runtime-and-miniapp-foundation.md)
19. [Wave 1 Engineering Backlog by Repo](./16-wave-1-engineering-backlog-by-repo.md)
20. [Wave 1 File-Level Change Map](./17-wave-1-file-level-change-map.md)
21. [ADRs](./adr/ADR-001-telegram-stars-as-primary-telegram-payment-rail.md)

## Consolidated Version

For linear reading, one additional full-file aggregation is available:

- [99-complete-growth-platform-dossier.md](./99-complete-growth-platform-dossier.md)

## Audience Guide

| Audience | Start Here | Why |
|---|---|---|
| Founders / leadership | `01-executive-summary.md` | Business logic, scope, priorities, risk summary |
| Product | `02-product-strategy.md`, `04-shared-platform-foundation.md` | User journeys, value proposition, cross-feature rules |
| Backend | `03-target-architecture.md`, feature API contracts, ADRs | Domain boundaries, APIs, workers, payment rules |
| Frontend | `03-target-architecture.md`, Mini App and Network specs | Surface behavior, routing, runtime context |
| Partner team | White-Label dossier | Onboarding, commercial policy, provisioning lifecycle |
| Platform / SRE | `03-target-architecture.md`, `08-security-and-abuse-prevention.md`, Network docs | Snapshot pipeline, observability, trust boundaries |
| QA | `09-testing-strategy.md`, feature implementation plans | Critical paths, E2E coverage, acceptance criteria |

## Document Status Legend

- `Draft`: ready for review, not yet frozen
- `Review`: in validation with stakeholders
- `Accepted`: approved as implementation baseline
- `Superseded`: kept for history only

## Top-Level Documents

| File | Purpose | Status |
|---|---|---|
| [00-index.md](./00-index.md) | Navigation and reading order | Draft |
| [01-executive-summary.md](./01-executive-summary.md) | Cross-functional summary of the program | Draft |
| [02-product-strategy.md](./02-product-strategy.md) | Users, journeys, value, monetization, growth loop | Draft |
| [03-target-architecture.md](./03-target-architecture.md) | Canonical technical target state | Draft |
| [04-shared-platform-foundation.md](./04-shared-platform-foundation.md) | Shared entities and platform rules | Draft |
| [05-roadmap-and-milestones.md](./05-roadmap-and-milestones.md) | Phased implementation plan | Draft |
| [06-risk-register.md](./06-risk-register.md) | Structured risk list and mitigations | Draft |
| [07-analytics-and-kpi.md](./07-analytics-and-kpi.md) | Metrics, funnels, events, dashboards | Draft |
| [08-security-and-abuse-prevention.md](./08-security-and-abuse-prevention.md) | Security controls and abuse prevention | Draft |
| [09-testing-strategy.md](./09-testing-strategy.md) | Test model, environments, critical E2E coverage | Draft |
| [10-rollout-plan.md](./10-rollout-plan.md) | Alpha to production release plan | Draft |
| [11-open-questions.md](./11-open-questions.md) | Pending decisions and deadlines | Draft |
| [12-admin-control-plane.md](./12-admin-control-plane.md) | Internal operations, risk, finance, and audit control plane | Draft |
| [13-data-model-and-migrations.md](./13-data-model-and-migrations.md) | Migration sequencing and schema evolution plan | Draft |
| [14-implementation-start-point.md](./14-implementation-start-point.md) | First implementation boundary, entry criteria, and non-goals | Draft |
| [15-wave-1-shared-runtime-and-miniapp-foundation.md](./15-wave-1-shared-runtime-and-miniapp-foundation.md) | Execution backlog for Group 1 and Mini App foundation | Draft |
| [16-wave-1-engineering-backlog-by-repo.md](./16-wave-1-engineering-backlog-by-repo.md) | Repo-by-repo execution backlog for Wave 1 | Draft |
| [17-wave-1-file-level-change-map.md](./17-wave-1-file-level-change-map.md) | File-level map of expected Wave 1 touch points | Draft |
| [99-complete-growth-platform-dossier.md](./99-complete-growth-platform-dossier.md) | Full consolidated version of the entire dossier | Draft |

## Feature Dossiers

### Telegram Mini App

- [Overview](./miniapp/00-miniapp-overview.md)
- [User Flows](./miniapp/01-miniapp-user-flows.md)
- [Technical Spec](./miniapp/02-miniapp-technical-spec.md)
- [API Contracts](./miniapp/03-miniapp-api-contracts.md)
- [Payment Flow](./miniapp/04-miniapp-payment-flow.md)
- [Security](./miniapp/05-miniapp-security.md)
- [Implementation Plan](./miniapp/06-miniapp-implementation-plan.md)
- [Definition of Done](./miniapp/07-miniapp-definition-of-done.md)

### White-Label Partner Portal

- [Overview](./white-label/00-white-label-overview.md)
- [Partner User Flows](./white-label/01-partner-user-flows.md)
- [Domain Model](./white-label/02-white-label-domain-model.md)
- [Partner Bot Provisioning](./white-label/03-partner-bot-provisioning.md)
- [Commercial Policy](./white-label/04-partner-commercial-policy.md)
- [API Contracts](./white-label/05-white-label-api-contracts.md)
- [Portal UX](./white-label/06-partner-portal-ux.md)
- [Abuse, Moderation, KYB](./white-label/07-abuse-moderation-kyb.md)
- [Implementation Plan](./white-label/08-white-label-implementation-plan.md)
- [Definition of Done](./white-label/09-white-label-definition-of-done.md)

### Network Intelligence

- [Overview](./network-intelligence/00-network-intelligence-overview.md)
- [Public Speed Map Product Spec](./network-intelligence/01-public-speed-map-product-spec.md)
- [Public Snapshot Spec](./network-intelligence/02-public-network-snapshot-spec.md)
- [API Contracts](./network-intelligence/03-network-api-contracts.md)
- [Prometheus Aggregation Pipeline](./network-intelligence/04-prometheus-aggregation-pipeline.md)
- [DPI Resistance Score](./network-intelligence/05-dpi-resistance-score.md)
- [SEO and Public Pages](./network-intelligence/06-seo-and-public-pages.md)
- [Network Widget Spec](./network-intelligence/07-network-widget-spec.md)
- [Implementation Plan](./network-intelligence/08-network-implementation-plan.md)
- [Definition of Done](./network-intelligence/09-network-definition-of-done.md)

## ADR Set

- [ADR-001: Telegram Stars as Primary Telegram Payment Rail](./adr/ADR-001-telegram-stars-as-primary-telegram-payment-rail.md)
- [ADR-002: Shared Multi-Tenant Runtime for White-Label](./adr/ADR-002-shared-multi-tenant-runtime-for-white-label.md)
- [ADR-003: Public Network Snapshot Instead of Direct Prometheus](./adr/ADR-003-public-network-snapshot-instead-of-direct-prometheus.md)
- [ADR-004: Mini App as Canonical Conversion Runtime](./adr/ADR-004-miniapp-as-canonical-conversion-runtime.md)
- [ADR-005: CyberVPN as Platform of Record](./adr/ADR-005-cybervpn-as-platform-of-record.md)

## Current Baseline Notes

- Telegram Mini App already exists in `frontend/src/app/[locale]/miniapp/`, but routing and auth behavior are not yet canonical.
- Partner Portal already has a meaningful foundation, but not the full bot provisioning and white-label runtime model.
- Public `network` and `status` pages already exist, but part of the current public story still uses mock or simulated data.
- Telegram payment and bot platform constraints require explicit architectural decisions before implementation starts.
- Production rollout also requires an internal control plane for moderation, refunds, payouts, incidents, and audit.

## Relationship to Prior Planning

This dossier supersedes ad hoc planning for the same scope and should be treated as the canonical planning package for implementation sequencing. Older plan documents remain useful as source material, but this folder is the platform-of-record for this initiative.


---

## Source Document: `docs/growth-platform/01-executive-summary.md`

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


---

## Source Document: `docs/growth-platform/02-product-strategy.md`

# Product Strategy

## Strategic Goal

Turn CyberVPN from a product with several strong components into a growth platform with:

- public trust signals;
- Telegram-native conversion;
- partner-led distribution at scale.

## Target Users

### Customer Personas

| Persona | Need | Why These Features Matter |
|---|---|---|
| Telegram-native mobile buyer | Fast purchase and instant VPN access without app-switching | Mini App lowers friction and keeps the flow inside Telegram |
| Trust-seeking evaluator | Proof that the network is real, fast, and stable | Network Intelligence turns performance into visible evidence |
| Returning subscriber | Fast renewal and device/config recovery | Mini App centralizes renew, config, and support |
| Referral-driven user | Easy sharing and invite attribution | Mini App and partner bots make sharing Telegram-native |

### Partner Personas

| Persona | Need | Why White-Label Matters |
|---|---|---|
| Small reseller | Fast branded channel without engineering | Self-service onboarding and managed bot flow |
| Content/community operator | Branded acquisition path inside Telegram | White-Label bot + Mini App + storefront |
| Regional distributor | Pricing control, analytics, payouts | Commercial policy + analytics + settlements |
| Strategic partner | Brand integrity and operational support | Moderation, branded runtime, support hooks |

## Customer Journey

1. Customer sees public proof on network pages or partner distribution material.
2. Customer opens Telegram entry point.
3. Mini App validates identity and builds a personalized bootstrap.
4. Customer starts trial or buys plan with Stars.
5. Customer receives config, device onboarding, and server guidance.
6. Customer shares referral or returns for renewal.

## Partner Journey

1. Partner applies and passes moderation.
2. Partner receives workspace and commercial policy.
3. Partner configures brand and pricing rules.
4. Partner provisions branded bot and Mini App binding.
5. Partner launches campaigns and tracks performance.
6. Partner requests payouts and iterates on conversion.

## Value Proposition by Feature

### Telegram Mini App

- fastest path from intent to purchase;
- native Telegram user experience;
- strong fit for censorship-sensitive markets;
- lower checkout abandonment through in-app payment.

### White-Label

- turns distribution partners into force multipliers;
- reduces manual provisioning and support load;
- creates a branded GTM surface without separate product stacks;
- makes CyberVPN harder to copy as a platform.

### Network Intelligence

- creates trust before purchase;
- improves SEO and public discovery;
- creates product evidence instead of generic claims;
- supplies real data to server picker and partner widgets.

## Growth Loop

1. Public Network pages attract and persuade.
2. Mini App converts.
3. Referral and sharing create new Telegram-native entries.
4. Partners replicate the same flow for new audiences.
5. Network Intelligence feeds back into conversion and retention by improving recommendation quality and trust.

## Competitive Positioning

CyberVPN should not claim unsupported market absolutes. The safer strategic position is:

- Telegram-native acquisition and checkout can become a rare advantage in VPN.
- White-Label bot + branded Mini App can become a hard-to-copy distribution moat.
- Public live network proof can become a differentiated trust asset.

## Monetization Model

### Baseline

- customer purchases plans and add-ons;
- partner earns margin or revenue share under CommercialPolicy;
- CyberVPN remains platform-of-record and merchant-of-record;
- partner storefronts outside Telegram may use additional rails where policy allows.

### Payment Policy

- Telegram surfaces: Telegram Stars / XTR
- Web and external storefronts: crypto, fiat, wallet, and other approved rails
- Internal wallet: optional balance, credits, or settlement utility

## Pricing Assumptions

- keep core plan catalog centralized;
- let partners operate within approved pricing and discount boundaries;
- separate customer-facing price presentation from settlement math;
- keep entitlement logic independent from presentation-layer pricing.

## Core Hypotheses

1. Public proof of network quality increases conversion from landing to trial.
2. Telegram-native flow increases checkout completion versus browser handoff.
3. A canonical Mini App runtime can support both CyberVPN and partner-branded flows without codebase fragmentation.
4. Self-service White-Label can scale partner acquisition materially if moderation and payout controls are strong.
5. Network Intelligence content can produce measurable SEO and sharing lift.

## Success Metrics

### Customer

- landing to Mini App click-through;
- Mini App open to purchase conversion;
- trial to paid conversion;
- time from open to config delivery;
- subscription renewal rate.

### Partner

- application to approval rate;
- approval to active bot rate;
- partner-attributed paid customers;
- partner revenue and payout cycle health;
- provisioning success rate.

### Platform

- payment reconciliation success;
- entitlement activation correctness;
- tenant isolation incident count;
- public snapshot freshness;
- end-to-end conversion funnel visibility.


---

## Source Document: `docs/growth-platform/03-target-architecture.md`

# Target Architecture

## Design Principle

CyberVPN Growth Platform should use one shared core domain with surface-specific read models. No major customer or partner surface should build itself by stitching together large numbers of unrelated generic endpoints at runtime.

## Surface Map

```text
Frontend
├── Web Marketing
├── Public Network Pages
├── Telegram Mini App
├── Partner Portal
├── Partner Storefront
├── Partner-Branded Mini App
└── Admin / Operations Control Plane

Backend
├── Mini App API
├── Partner API
├── Partner Bots API
├── Public Network API
├── Admin Operations API
├── Payments API
└── Entitlements API

Workers
├── Network Snapshot Worker
├── Partner Bot Provisioning Worker
├── Telegram Payment Reconciliation Worker
├── Partner Settlement Worker
├── DPI Probe Worker
└── Analytics Worker
```

## Frontend Surfaces

### Web Marketing

- main brand narrative;
- acquisition CTAs into Telegram and web checkout;
- bridge to public proof pages.

### Public Network Pages

- `/[locale]/network`
- `/[locale]/status`
- supporting public region and DPI pages
- SSR and cache-friendly sanitized data only

### Telegram Mini App

- canonical customer conversion runtime;
- platform mode and partner-branded mode;
- trial, quote, Stars checkout, config, devices, referral.

### Partner Portal

- application and moderation UX;
- brand setup;
- bot provisioning;
- analytics and payouts;
- risk and compliance visibility.

### Partner Storefront

- branded external acquisition surface;
- optional web checkout outside Telegram;
- shared commercial and branding context.

### Admin / Operations Control Plane

- partner approvals and moderation;
- bot suspend, rotate, and revoke flows;
- refund and payout review;
- public incident management;
- audit and risk investigation.

## Backend Namespaces

### `/api/v1/miniapp/*`

- Telegram-optimized read models;
- surface-aware trial, offer, device, config, referral, and payment actions.

### `/api/v1/public/network/*`

- sanitized public snapshots;
- no internal-only labels or operational topology;
- explicit freshness and confidence.

### `/api/v1/partner/*`

- workspace, brand, pricing, analytics, payout, and onboarding operations.

### `/api/v1/partner-bots/*`

- provisioning lifecycle;
- status and credential rotation;
- release and suspension actions.

### Existing Platform APIs

- payments, entitlements, subscriptions, referral, and Telegram-specific bot APIs remain shared core dependencies.
- admin and operations APIs coordinate moderation, incidents, refunds, payouts, and emergency actions.

## Domain Model

Core entities should include:

- `User`
- `TelegramIdentity`
- `IdentityLink`
- `PartnerWorkspace`
- `PartnerBot`
- `PartnerCommercialPolicy`
- `PartnerBrandTheme`
- `Storefront`
- `PartnerSettlementLedgerEntry`
- `Payment`
- `Order`
- `Entitlement`
- `Trial`
- `Referral`
- `Device`
- `Server`
- `PublicNetworkSnapshot`
- `Incident`

## Worker Responsibilities

### Network Snapshot Worker

- reads Prometheus and internal network data;
- generates sanitized public snapshots;
- sets freshness and expiry fields;
- writes materialized data for public APIs.

### Partner Bot Provisioning Worker

- validates workspace readiness;
- reserves or binds bot identity;
- applies branding and menu setup;
- binds Mini App and webhook;
- emits provisioning status transitions.

### Telegram Payment Reconciliation Worker

- reconciles Telegram Stars invoices and payment events;
- supports explicit pre-checkout validation integration through bot runtime behavior;
- activates entitlements only after authoritative success;
- handles retries and refund-aware follow-up.

### Partner Settlement Worker

- creates immutable ledger entries for sale, refund, payout, hold, and release events;
- derives payout-ready balances from append-only history;
- supports payout reconciliation and reversal handling.

### DPI Probe Worker

- runs country and protocol probes;
- records signal quality;
- contributes to public DPI score with confidence values.

### Analytics Worker

- validates and enriches event streams;
- materializes reporting datasets;
- supports partner and funnel dashboards.

## Payment Flows

### Telegram Surfaces

- quote creation uses surface and tenant context;
- invoice creation uses Telegram Stars with currency `XTR`;
- pre-checkout validation must be explicit;
- entitlement activation happens after authoritative `successful_payment` confirmation;
- disputes and refunds follow Telegram-compatible support handling.

### Web and External Partner Storefront

- may support non-Telegram rails under policy;
- still create shared `Payment`, `Order`, and `Entitlement` records.

## Tenant Model

Every request must resolve a tenant-aware runtime context:

- `platform`
- `partner`

Runtime context should include:

- surface;
- brand theme;
- commercial policy;
- attribution metadata;
- support contacts;
- legal identity view.

## Observability

Surface labels should include:

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

Each surface should support:

- runtime errors;
- funnel events;
- payment events;
- latency and freshness metrics where relevant.

## Caching Strategy

### Public Network

- CDN and HTTP caching allowed;
- `Cache-Control`, `ETag`, and `Last-Modified` are required;
- stale mode must be explicit;
- snapshot publishing must be atomic.

### Mini App

- bootstrap payloads should be short-lived and server-authoritative;
- avoid excessive client fan-out;
- prefer consolidated read models with selective refresh.

## Public vs Private Data Boundaries

Public surfaces must never expose:

- internal node hostnames;
- raw Prometheus labels;
- exact infrastructure topology;
- secret operational thresholds;
- partner-private financial data.

Public surfaces may expose:

- sanitized region and node labels;
- public incident summaries;
- aggregated latency, speed, and uptime;
- freshness state and confidence;
- methodology version and measurement window where appropriate.

## Architecture Rule Set

1. One shared core domain.
2. Surface-specific read models.
3. Tenant context resolved on every branded surface.
4. Telegram payment compliance enforced by design.
5. Public network data always served from sanitized snapshots.
6. Partner settlement history is append-only.
7. Public snapshot publication is atomic and truth-preserving.


---

## Source Document: `docs/growth-platform/04-shared-platform-foundation.md`

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


---

## Source Document: `docs/growth-platform/05-roadmap-and-milestones.md`

# Roadmap and Milestones

## Delivery Model

The program should run as phased platform delivery rather than sequential isolated feature work.

## Phase 0 — Product and Architecture Decisions

### Goal

Freeze the irreversible decisions that would otherwise force major rewrites later.

### Deliverables

- shared platform foundation accepted;
- ADR-001 through ADR-005 accepted;
- target architecture baseline accepted;
- product scope split into platform and feature workstreams.

### Go / No-Go

- no implementation starts without payment policy, tenant model, and snapshot policy approval.

## Phase 1 — Shared Foundation

### Goal

Create the shared contracts needed by all three features.

### Milestones

- identity and runtime context schema aligned;
- attribution model defined;
- event taxonomy defined;
- surface taxonomy extended;
- tenant-aware payment and entitlement metadata model defined;
- immutable settlement ledger schema defined;
- admin control plane baseline defined;
- migration sequencing accepted.

### Dependencies

- Phase 0 decisions complete.

## Phase 2 — Mini App Conversion Runtime

### Goal

Turn the current Mini App baseline into a canonical Telegram-native conversion surface.

### Milestones

- `/miniapp` routing fixed;
- auth and 2FA stay inside Mini App namespace;
- bootstrap API available;
- Telegram Stars quote and invoice flow defined and implemented;
- config delivery and support path stabilized;
- refund and duplicate-payment handling verified.

### Critical Path

- Telegram payment reconciliation and entitlement correctness.

## Phase 3 — Public Network Intelligence

### Goal

Replace placeholder or mock public network sections with truthful, snapshot-driven public data.

### Milestones

- snapshot schema approved;
- public aggregation worker operational;
- overview, uptime, incidents, and leaderboard APIs live;
- public pages render sanitized snapshots;
- stale mode and freshness alerting live;
- atomic publish and previous-valid-snapshot retention live.

## Phase 4 — White-Label Self-Service Runtime

### Goal

Transform the partner foundation into self-service distribution infrastructure.

### Milestones

- PartnerBot domain model live;
- provisioning state machine live;
- brand and storefront runtime DB-driven;
- branded Mini App preview available;
- partner wizard covers application through launch preparation;
- admin and operator moderation/suspend controls available.

## Phase 5 — DPI, Widgets, and Partner Scaling

### Goal

Move from functional platform to differentiated market asset.

### Milestones

- DPI probe pipeline in place;
- public DPI score available with confidence model;
- partner widgets available;
- partner analytics and payout workflows stabilized;
- managed bots primary path tested with fallback path available;
- settlement ledger reversal and hold/release workflows stabilized.

## Phase 6 — Hardening, Observability, and Scale

### Goal

Prepare the platform for larger partner counts and sustained traffic growth.

### Milestones

- canary and stable release rings for partner bots;
- stronger abuse scoring;
- public snapshot freshness SLO;
- reconciliation and settlement dashboards;
- incident playbooks and rollback rehearsals complete.

## Parallel Workstreams

| Workstream | Core Area | Primary Owners |
|---|---|---|
| Customer Runtime | Mini App, routing, checkout, config | Frontend + Backend |
| Platform Core | identity, payment, entitlement, attribution | Backend |
| White-Label Runtime | partner domain, portal UX, provisioning | Backend + Partner Frontend |
| Network Intelligence | snapshot worker, public API, public pages | Platform + Frontend |
| Control Plane | analytics, security, testing, rollout | Platform + QA |

## Dependencies Summary

| Depends On | Needed By | Why |
|---|---|---|
| Shared tenant context | Mini App, White-Label | Partner-branded runtime cannot be bolted on later |
| Telegram payment policy | Mini App, partner bots | In-Telegram flows must be compliant by design |
| Public snapshot schema | Network pages, server picker, widgets | One public truth source |
| Attribution model | referral, partner revenue, analytics | Shared commercial math |
| Immutable settlement ledger | White-Label payouts and refunds | Prevents payout and reversal ambiguity |
| Admin control plane | White-Label and public trust rollout | Required for moderation, incidents, refunds, and suspensions |

## Release Order

1. Shared contracts and ADRs
2. Mini App runtime hardening
3. Public network snapshot layer
4. White-Label domain and provisioning alpha
5. Public Speed Map launch
6. Partner commercialization and DPI expansion

## Feature Gates

- `miniapp_stars_checkout_enabled`
- `public_network_snapshot_enabled`
- `partner_bots_alpha_enabled`
- `partner_branded_miniapp_enabled`
- `public_dpi_score_enabled`
- `partner_widget_enabled`

## Estimated Complexity

| Area | Complexity | Notes |
|---|---|---|
| Shared foundation | High | Cross-cutting and rewrite-prevention work |
| Mini App | High | Telegram runtime, payment correctness, UX latency |
| White-Label | Very High | Multi-tenant domain, moderation, provisioning |
| Network Intelligence | Medium to High | Data pipeline plus public truth constraints |

## Owner Model

- Product owns scope, positioning, and unresolved business policy.
- Backend owns shared domain, APIs, payments, tenant isolation, and workers.
- Frontend owns customer surfaces and partner UX.
- Platform owns public snapshot pipeline, alerting, security controls, and rollout discipline.
- QA owns critical path verification and rollback validation.


---

## Source Document: `docs/growth-platform/06-risk-register.md`

# Risk Register

## Risk Model

Severity scale:

- `Critical`
- `High`
- `Medium`
- `Low`

Probability scale:

- `High`
- `Medium`
- `Low`

## Active Risk Register

| Risk | Area | Severity | Probability | Mitigation | Owner | Fallback |
|---|---|---:|---:|---|---|---|
| Tenant data leakage across partners | White-Label | Critical | Medium | Strict tenant context, repository filters, audit logs, tests | Backend | Immediate partner surface suspend |
| Payment entitlement activated before authoritative success | Mini App | Critical | Medium | Server-authoritative payment confirmation, reconciliation worker, idempotency | Backend | Manual entitlement rollback |
| Public mock or simulated metrics shown as truth | Network | High | Medium | Snapshot-only public API, freshness, confidence, truthfulness policy | Platform | Remove affected block from public pages |
| Telegram payment compliance drift | Mini App / Bot | Critical | Medium | ADR-backed payment policy, explicit surface payment matrix | Product + Backend | Disable Telegram purchase and keep read-only flow |
| Managed Bots limitations or rollout blockers | White-Label | High | Medium | Managed bot spike, manual token fallback | Platform | Manual bot onboarding path |
| White-Label abuse or impersonation brands | White-Label | High | High | KYB, moderation, blocked brand rules, payout holds | Product + Risk | Emergency suspend and credential revoke |
| Public snapshot becomes stale but still appears live | Network | High | Medium | `generatedAt`, `expiresAt`, stale mode, alerting | Platform | Switch UI to degraded status |
| Mutable settlement state causes payout or refund disputes | White-Label | High | Medium | Append-only partner settlement ledger and reversal entries | Finance + Backend | Freeze payouts until reconciliation |
| Missing operator tooling delays abuse, refunds, or incident response | Operations | High | Medium | Admin control plane and emergency actions before public scale | Platform + Ops | Restrict rollout to manual cohort |
| Overengineering before signal | Program | Medium | Medium | Staged release gates and phased launch | Product | Freeze advanced work until metrics arrive |
| Referral abuse via Telegram loops | Mini App / White-Label | High | Medium | Signed payloads, rate limits, abuse scoring | Backend | Disable reward issuance for flagged flows |
| Incomplete partner settlement model | White-Label | High | Medium | Platform-of-record baseline, explicit commercial policy | Product + Finance | Delay payout automation |
| Support burden spikes after launch | Mini App / White-Label | Medium | Medium | `/paysupport`, help surfaces, incident scripts, dashboards | Product + Support | Scope-limited rollout |
| SEO pages overpromise DPI or uptime claims | Network | High | Medium | Confidence markers, methodology page, legal copy review | Product + Legal | Remove affected SEO pages |

## Product Risks

- Mini App may be functionally complete but still fail on perceived simplicity if the bootstrap and checkout flow feel slow or fragmented.
- White-Label may attract low-quality partners if moderation and commercial boundaries are weak.
- Network Intelligence may underperform as an acquisition lever if public storytelling is strong visually but weak on data freshness and methodology.

## Technical Risks

- current Mini App route and auth inconsistencies can create partial flows and hard-to-debug drop-off;
- partner runtime can drift into static or env-driven behavior if DB-driven branding is not enforced early;
- snapshot generation can become expensive if schema is not designed for efficient periodic updates;
- refund, reversal, and payout state can drift if ledger and reconciliation are modeled as mutable balances only.

## Legal and Compliance Risks

- public claims about service availability in sensitive regions require careful wording and proof confidence;
- partner branding can create impersonation and trademark exposure;
- payment support and refund expectations must align with chosen payment rails and merchant-of-record policy.

## Risk Review Cadence

- weekly during planning;
- twice weekly during payment and provisioning implementation;
- per rollout stage before expansion of audience.


---

## Source Document: `docs/growth-platform/07-analytics-and-kpi.md`

# Analytics and KPI

## Analytics Purpose

Analytics must support four outcomes:

- measure acquisition quality;
- measure Mini App conversion;
- measure partner-driven distribution performance;
- prove operational health of public trust surfaces.

## North Star Metrics

### Platform

- paid active customers attributable to the Growth Platform
- partner-attributed recurring revenue
- Mini App paid conversion rate
- public network page to conversion assist rate

## Funnel Families

### Mini App Funnel

Core events:

- `miniapp_opened`
- `miniapp_bootstrap_loaded`
- `miniapp_auth_success`
- `trial_started`
- `checkout_started`
- `miniapp_invoice_opened`
- `payment_success`
- `config_delivered`

Key KPIs:

- open to bootstrap success rate
- bootstrap to trial start rate
- bootstrap to checkout start rate
- checkout start to payment success rate
- payment success to config delivered rate
- median time from open to config delivered

### White-Label Funnel

Core events:

- `partner_application_submitted`
- `partner_application_approved`
- `partner_workspace_created`
- `partner_bot_provisioning_started`
- `partner_bot_active`
- `partner_sale_attributed`
- `partner_payout_requested`

Key KPIs:

- application to approval rate
- approval to active bot rate
- provisioning success rate
- time from approval to first sale
- partner revenue by commercial policy tier

### Network Intelligence Funnel

Core events:

- `network_page_view`
- `public_network_region_clicked`
- `public_network_cta_click`
- `cta_to_miniapp_clicked`
- `widget_loaded`

Key KPIs:

- public page CTR into Mini App
- region detail engagement rate
- widget load volume and source distribution
- conversion assist rate by page and region

## Payment Events

Shared commercial events:

- `checkout_quote_created`
- `invoice_created`
- `invoice_opened`
- `invoice_closed`
- `payment_success`
- `payment_cancelled`
- `payment_failed`
- `refund_requested`
- `refund_completed`

## Retention Metrics

- renewal rate
- subscription expiry recovery rate
- returning Mini App sessions
- device reconfiguration rate
- retention by entry source and partner

## Referral Metrics

- referral shares
- referral opens
- referral-attributed trial starts
- referral-attributed payments
- suspicious referral loop count

## Partner Revenue Metrics

- gross sales by partner
- net payout-ready revenue by partner
- refunds and holds
- active customers per partner
- partner funnel by geography

## Event Payload Requirements

Every event should include:

- `eventName`
- `eventId`
- `occurredAt`
- `surface`
- `locale`
- `userId` or anonymous ID
- `partnerId` if applicable
- `workspaceId` if applicable
- `storefrontId` if applicable
- `botId` if applicable
- `referralCode` if applicable
- `campaign` if applicable
- `requestId` if applicable

## Dashboard Requirements

### Product Dashboard

- Mini App funnel
- network assist funnel
- trial to paid conversion
- revenue by source

### Partner Operations Dashboard

- application queue
- provisioning state distribution
- active bots
- payout queue
- abuse and review flags

### Platform Dashboard

- payment reconciliation health
- snapshot freshness
- tenant isolation alerts
- Stars checkout success rate

## Data Quality Rules

- event names must be stable and versioned if changed;
- payment events must be deduplicated;
- public network metrics must expose freshness;
- partner attribution must not rely on a single client-side signal.


---

## Source Document: `docs/growth-platform/08-security-and-abuse-prevention.md`

# Security and Abuse Prevention

## Objective

Protect customer flows, partner isolation, payment integrity, and public trust surfaces before production rollout.

## Core Security Principles

1. Server-authoritative trust decisions only.
2. Tenant isolation by design.
3. Signed attribution and referral payloads.
4. Payment activation only after authoritative confirmation.
5. Public surfaces expose sanitized data only.

## Telegram Security

### initData Validation

- raw Telegram init data must be validated on the backend;
- `initDataUnsafe` must never be trusted for security-sensitive decisions;
- session creation must bind to validated Telegram identity;
- telemetry emitted by the client must never be used as security proof.

### startapp and Referral Payloads

- sign payloads with expiry;
- include partner and campaign metadata only where necessary;
- reject malformed or expired payloads;
- audit suspicious reuse.

## Partner Tenant Isolation

Controls:

- explicit tenant resolution per request;
- no implicit default tenant on partner-aware surfaces;
- repository and service layer tenant checks;
- audit logging for cross-tenant access attempts;
- test coverage for negative isolation cases.

## Payment Verification

- invoice creation is server-side;
- pre-checkout validation must be explicit and auditable;
- invoice status is reconciled from authoritative payment events;
- entitlement activation occurs only after confirmed success;
- refunds and disputes update platform state explicitly.

## Token and Credential Security

- encrypt bot tokens and payment secrets at rest;
- rotate credentials with auditable workflows;
- restrict plaintext token exposure in UI and logs;
- revoke and rebind credentials on emergency suspend.

## Webhook Security

- verify Telegram or internal webhook authenticity;
- isolate webhook handling by bot identity and tenant context;
- prevent replay where supported;
- alert on repeated invalid signatures or malformed payloads.

## Public API Controls

- rate limit public network endpoints;
- cache responses aggressively but safely;
- strip internal identifiers and topology;
- enforce public schema validation before serving.

## Trial Abuse Prevention

Signals may include:

- Telegram identity history;
- device or browser fingerprint signals;
- IP and ASN patterns;
- referral loop patterns;
- partner risk score;
- prior payment and trial history.

## White-Label Abuse Prevention

- KYB and moderation tiers;
- brand review and impersonation detection;
- bot creation limits;
- payout holds for suspicious accounts;
- emergency suspend with token revoke;
- blocked category enforcement.

## Audit Logs

Required for:

- partner provisioning actions;
- brand and commercial policy changes;
- token rotations;
- payout requests and approvals;
- cross-tenant security events;
- payment state transitions;
- admin and operator actions against partners, incidents, payouts, or refunds.

## Emergency Controls

- suspend partner workspace;
- suspend partner bot;
- disable branded Mini App binding;
- stop payouts;
- force public widget disable for a tenant;
- disable purchase while leaving read-only support access.

## Data Exposure Rules

Never expose publicly:

- internal node names;
- raw Prometheus labels;
- credential references;
- secret partner commercial terms;
- sensitive abuse or risk scoring internals.

Expose publicly only if sanitized:

- aggregated metrics;
- public incident summaries;
- public region labels;
- freshness and confidence state.


---

## Source Document: `docs/growth-platform/09-testing-strategy.md`

# Testing Strategy

## Objective

Testing must prove that the Growth Platform is correct across surface, tenant, payment, and public-data boundaries.

## Test Layers

### Unit Tests

- pricing and attribution helpers;
- tenant context resolution;
- referral signing and verification;
- payment state transitions;
- snapshot freshness logic.

### Integration Tests

- Mini App bootstrap composition;
- payment to entitlement activation;
- partner provisioning state transitions;
- public snapshot publication flow;
- webhook handling and reconciliation.

### Contract Tests

- Mini App API contracts;
- Partner API contracts;
- Public Network API contracts;
- Telegram payment and webhook adapters.

### End-to-End Tests

- Telegram Mini App critical purchase path;
- partner application to active branded bot;
- public snapshot generation to SSR page rendering;
- stale snapshot degraded rendering behavior.

## Critical E2E Scenarios

1. User opens Mini App, pays, and gets config.
2. Partner creates bot, user buys through partner context, partner receives attributed sale.
3. Network snapshot worker publishes fresh data and public page renders it.
4. Snapshot becomes stale and UI clearly shows stale or degraded state instead of fake live status.
5. Refund occurs after entitlement activation and produces correct reversal behavior.
6. Partner suspension occurs after active bot and customer-facing behavior degrades safely.

## Security Test Areas

- invalid Telegram init data rejection;
- cross-tenant access rejection;
- unsigned or expired referral payload rejection;
- premature entitlement activation prevention;
- public data sanitization verification.

## Payment Test Areas

- quote idempotency;
- invoice creation idempotency;
- duplicate `successful_payment` event handling;
- `pre_checkout_query` validation handling;
- successful payment reconciliation;
- canceled invoice handling;
- refund-aware entitlement behavior;
- duplicate webhook resilience;
- partner ledger reversal correctness.

## Performance and Load

- Mini App bootstrap latency under realistic mobile conditions;
- public network API response under cached and uncached paths;
- provisioning queue throughput;
- analytics ingestion durability.

## Smoke Tests

Must exist for:

- Mini App bootstrap
- Stars payment status check
- public network overview
- partner workspace load
- provisioning job health

## Rollback Tests

- disable purchase while keeping Mini App readable;
- revert public network page to safe degraded mode;
- suspend a partner bot and verify customer-facing behavior;
- roll back provisioning state after partial failure;
- release and re-apply payout hold entries cleanly.

## Additional Production-Critical Scenarios

- failed provisioning rollback after partial webhook or menu binding;
- stale snapshot with last valid snapshot retained;
- public incident publication and update workflow;
- negative tenant leakage tests for partner data, payments, and configs;
- admin/operator audit trail tests.

## Environment Strategy

- local dev for contract and unit coverage;
- staging for Telegram-integrated flows where possible;
- pre-production for snapshot freshness, provisioning, and settlement rehearsals;
- production canary for partner and public rollout.


---

## Source Document: `docs/growth-platform/10-rollout-plan.md`

# Rollout Plan

## Rollout Principle

Release the platform in controlled stages. Keep the architecture complete, but gate exposure aggressively.

## Stage 1 — Internal Alpha

### Scope

- CyberVPN Mini App only
- no partner bots in public use
- public network pages behind feature flags or internal access

### Exit Criteria

- payment flow passes end-to-end
- config delivery works
- no critical security defects
- bootstrap latency is acceptable
- operator refund and suspend actions are available for internal testing

## Stage 2 — Controlled Beta

### Scope

- public network overview and status visible
- Mini App available to controlled user cohorts
- White-Label provisioning allowed only for a small trusted set
- manual fallback allowed for partner bot onboarding

### Exit Criteria

- provisioning success rate above target threshold
- payment reconciliation stable
- no tenant leakage
- public snapshot freshness alerts stable
- payout hold and release controls available

## Stage 3 — Closed Partner Beta

### Scope

- 3 to 5 trusted partners
- branded Mini App previews
- partner analytics and payout requests visible
- public Speed Map available

### Exit Criteria

- partner launch path works without code or ENV changes
- moderation workflow operational
- no critical partner abuse incidents
- immutable settlement ledger and reversal path validated

## Stage 4 — Public Launch

### Scope

- CyberVPN Mini App fully public
- public network pages and status pages indexed
- White-Label application flow public
- partner widget pilot enabled

### Exit Criteria

- on-call playbooks ready
- support routing in place
- dashboards and alerts cover payment, provisioning, and snapshot freshness

## Feature Flags

- `miniapp_enabled`
- `miniapp_stars_checkout_enabled`
- `public_network_enabled`
- `public_network_dpi_enabled`
- `partner_portal_self_service_enabled`
- `partner_branded_miniapp_enabled`
- `partner_widget_enabled`

## Rollback Plan

### Mini App

- disable purchase actions;
- keep read-only account state if needed;
- fall back to support and renewal messaging.

### White-Label

- stop new applications or provisioning;
- suspend affected partner runtime;
- preserve existing customer access while blocking new checkout if required.

### Network Intelligence

- switch affected pages to stale or degraded state;
- hide unsupported modules such as DPI score or widgets;
- maintain truthful status banner.

## Monitoring Checklist

- payment success and failure rates
- entitlement creation correctness
- provisioning queue state
- snapshot freshness
- public API cache and error rate
- partner tenant isolation alerts
- refund and settlement ledger anomalies
- operator action audit completeness

## Incident Response

- define severity levels by surface;
- identify owner rotation per stage;
- route payment incidents differently from public-data incidents;
- include emergency suspend for partner runtime.

## Launch Checklist

- ADRs accepted
- feature flags configured
- support copy available
- dashboards visible
- rollback rehearsed
- legal and product copy reviewed


---

## Source Document: `docs/growth-platform/11-open-questions.md`

# Open Questions

## Purpose

This file captures unresolved product, technical, legal, and commercial questions that must be answered before later implementation phases.

## Open Questions Table

| Question | Area | Owner | Decision Deadline | Current Recommendation |
|---|---|---|---|---|
| Are partners allowed to customize final customer pricing freely or only within policy bands? | White-Label | Product | Phase 1 | Allow controlled bands within `PartnerCommercialPolicy` |
| Should platform customers and partner customers share one catalog with visibility rules or have separate derived catalogs? | Platform | Product + Backend | Phase 1 | Shared canonical catalog with policy-based visibility |
| Which locales are required for first public launch of network pages? | Network | Product | Phase 1 | Launch priority locales, then expand to full set |
| Should DPI score be public in first release? | Network | Product + Infra | Phase 2 | No, launch after real probes and confidence model |
| Can Managed Bots satisfy required behavior for permissions, token rotation, webhook binding, menu button binding, and scale? | White-Label | Platform | Phase 2 | Run managed-bot spike and keep manual token fallback |
| What is the minimum review tier for a partner to provision a branded bot? | White-Label | Risk + Product | Phase 2 | Approval required before active provisioning |
| Are Telegram-only users required to pass additional recovery steps before payout-affecting actions? | Security | Product + Backend | Phase 2 | Keep support-mediated recovery for sensitive actions |
| How much branding freedom can partners have for support and legal copy? | White-Label | Product + Legal | Phase 2 | Controlled override with moderation |
| Do we support recurring subscription behavior inside Telegram at initial launch? | Payments | Product | Phase 3 | Launch with reliable one-time purchase and renewal flows first |
| How should Stars revenue map into partner settlement accounting? | White-Label | Finance + Product | Phase 3 | Convert to internal settlement ledger under platform-of-record model |
| What public promise language is acceptable for sensitive geographies in SEO pages? | Network | Legal + Product | Phase 3 | Use confidence-based wording, no absolute claims |

## Decision Rules

- no payment implementation without payment-policy closure;
- no public DPI claims without methodology and confidence closure;
- no White-Label public launch without partner risk and moderation policy closure.

## Update Cadence

- review during weekly platform planning;
- convert resolved items into ADRs, accepted policy docs, or implementation plan updates.


---

## Source Document: `docs/growth-platform/12-admin-control-plane.md`

# Admin Control Plane

## Purpose

The Growth Platform cannot be production-safe without an internal operations layer. Mini App, White-Label, and Network Intelligence all require internal controls for moderation, risk, finance, incident handling, and audit.

## Scope

The admin control plane should support:

- approve or reject partner applications;
- approve or reject branding;
- suspend partner workspace;
- suspend partner bot;
- rotate or revoke bot credentials;
- review refunds;
- hold or release payouts;
- inspect immutable settlement ledger history;
- manage public incidents;
- inspect and export audit trail.

## Primary Operator Roles

- `Growth Admin`
- `Partner Operations`
- `Risk and Compliance`
- `Finance Operations`
- `Support and Refund Operations`
- `Platform Incident Operator`

Each role should have scoped permissions rather than broad implicit super-admin access.

## Core Surfaces

### Partner Review Queue

- application review;
- KYB state;
- risk score;
- reviewer notes;
- next required action.

### Branding Moderation

- brand assets and copy review;
- impersonation and policy checks;
- moderation decision history.

### Bot Lifecycle Console

- provisioning state;
- credential status;
- rotation and revoke actions;
- suspend and restore actions;
- managed-bot or manual-token path visibility.

### Refund and Payment Console

- payment lookup;
- entitlement state lookup;
- refund review or execution;
- duplicate-payment investigation.

### Settlement and Payout Console

- payout-ready balance derived from ledger;
- hold and release actions;
- payout request review;
- reversal chain inspection.

### Incident and Public Status Console

- create incident;
- update incident;
- resolve incident;
- publish safe public text by region impact.

### Audit and Investigation Console

- search by partner, bot, workspace, payment, payout, incident, or user;
- export operator history;
- inspect emergency actions.

## Required Data Objects

- `PartnerWorkspace`
- `PartnerRiskProfile`
- `PartnerBot`
- `PartnerBotProvisioningJob`
- `PartnerBotCredential`
- `Payment`
- `Order`
- `Entitlement`
- `PartnerSettlementLedgerEntry`
- `PublicIncident`
- `AuditLogEntry`

## Control Plane Invariants

1. Every sensitive action emits an audit record.
2. Refund and payout actions preserve ledger history.
3. Suspension actions are explicit and attributable.
4. Public incident edits are attributable to operator identity.
5. Broad White-Label rollout should not happen before this control plane exists in a usable form.


---

## Source Document: `docs/growth-platform/13-data-model-and-migrations.md`

# Data Model and Migrations

## Purpose

This document defines migration sequencing so implementation does not drift into feature-specific schema shortcuts.

## Migration Principles

1. Shared runtime entities come before feature-specific convenience tables.
2. Payment, entitlement, and attribution migrations preserve backward compatibility where possible.
3. Partner finance uses append-only ledger semantics from the start.
4. Public snapshot publishing supports atomic replacement and last-valid retention.

## Group 1 — Shared Runtime Context

Goal:

- establish tenant-aware and attribution-aware foundation.

Expected schema areas:

- identity links;
- Telegram identity linkage;
- runtime tenant context support;
- surface and attribution metadata expansion.

## Group 2 — Mini App Payments and Entitlements

Goal:

- support Telegram Stars purchase flow safely.

Expected schema areas:

- payment provider and surface metadata expansion;
- quote and invoice references;
- payment authoritative status fields;
- refund and reconciliation support;
- entitlement linkage hardening.

## Group 3 — Public Network Intelligence

Goal:

- support public snapshot generation and truthful serving.

Expected schema areas:

- public snapshot store;
- snapshot history;
- public incidents;
- methodology versioning;
- measurement window metadata.

## Group 4 — White-Label Foundation

Goal:

- create durable partner tenant objects before advanced UX.

Expected schema areas:

- partner bots;
- partner brand theme;
- partner commercial policy;
- partner settlement accounts;
- partner risk profile;
- provisioning jobs.

## Group 5 — Settlement and Operations

Goal:

- make finance and operations production-grade.

Expected schema areas:

- immutable partner settlement ledger;
- payout hold and release records;
- operator actions and audit records;
- incident publication records.

## Migration Sequencing Rules

- no partner payout automation before ledger tables exist;
- no public incident editing without audit support;
- no partner-branded rollout without tenant-aware runtime tables;
- no recurring subscription work inside Telegram until baseline Stars flow is stable.

## Backfill Strategy

- derive tenant context where safely inferable;
- backfill partner attribution conservatively;
- create explicit unknown states instead of silent assumptions;
- flag ambiguous history for manual review.

## Release Strategy

- ship migrations before dependent code paths;
- use temporary compatibility adapters where needed;
- remove transition logic only after live verification.

## Anti-Patterns to Avoid

- durable business state only in JSON blobs or env defaults;
- mutable partner balances without ledger history;
- public snapshot rows overwritten without last-valid fallback;
- feature rollout before lower migration groups are complete.


---

## Source Document: `docs/growth-platform/14-implementation-start-point.md`

# Implementation Start Point

## Purpose

This document fixes the exact starting boundary for implementation so the team does not begin with visually attractive but structurally premature work.

## Start Point Decision

The implementation starts with two tightly linked work packages:

1. `Group 1 — Shared Runtime Context`
2. `Mini App Routing and Payment Foundation`

These two packages are the correct first wave because:

- partner-branded runtime cannot be bolted on later without rework;
- payment, entitlement, and attribution correctness must be solved before White-Label scale;
- Mini App already exists in the repo and is the canonical conversion runtime;
- public Network Intelligence and White-Label will both depend on the same runtime and payment foundation.

## Why Not Start Elsewhere

### Why Not Start with White-Label UX First

Because that would encourage:

- static branding shortcuts;
- manual bot workflows;
- partner-specific payment or attribution hacks;
- tenant leakage risk.

### Why Not Start with Speed Map First

Because Speed Map is strategically important, but it does not unblock the core conversion contract. If we launched it first without the shared runtime and Mini App foundation, it would create traffic before the platform is ready to convert that traffic correctly.

## Wave 1 Objective

Wave 1 should leave the project in this state:

- runtime context exists as a first-class platform concept;
- Mini App routing is canonical and stable;
- Mini App auth and return paths never break out of `/miniapp/*`;
- Telegram Stars purchase flow has a correct baseline contract;
- payment fulfillment is authoritative and replay-safe;
- enough observability exists to validate the first integrated user path.

## Mandatory Preconditions Already Fixed by the Dossier

These are treated as accepted inputs to implementation:

- Mini App is the canonical conversion runtime.
- Telegram digital-goods flows use Stars / `XTR`.
- White-Label uses a shared multi-tenant runtime.
- Public network pages must use sanitized snapshots.
- CyberVPN remains platform-of-record in the baseline commercial model.
- Partner settlement history must be append-only.

## What Is In Scope for Wave 1

### Shared Runtime Context

- runtime tenant model
- attribution model
- identity link expansion
- surface taxonomy alignment
- bootstrap-ready runtime commercial context

### Mini App Foundation

- route and auth continuity
- bootstrap API foundation
- quote and invoice foundation
- pre-checkout-aware payment contract
- successful-payment-authoritative fulfillment
- config-delivery-safe post-payment flow

## What Is Explicitly Out of Scope for Wave 1

- full White-Label self-service wizard
- public partner onboarding launch
- recurring Telegram Stars subscriptions
- public DPI score launch
- partner widget rollout
- payout automation
- complete admin control plane implementation beyond what Wave 1 directly depends on

## Required Repositories and Areas to Touch First

### `backend/`

- runtime context and attribution expansion
- Mini App namespace
- payment contract extensions
- entitlement-safe fulfillment path

### `frontend/`

- Mini App routing corrections
- bootstrap-based data loading
- checkout state handling
- runtime hooks

### `services/telegram-bot/`

- payment event compatibility
- pre-checkout validation path
- successful payment handoff

### `partner/`

- no major UX implementation in Wave 1, except only if runtime context integration requires shared contract alignment

## Exit Criteria for Wave 1

Wave 1 is complete when:

1. runtime context and attribution contracts are implemented and documented in code;
2. Mini App root and auth flows are stable inside `/miniapp/*`;
3. a user can move from Mini App open to quote creation without route or tenant ambiguity;
4. invoice creation and payment reconciliation have a correct baseline Telegram Stars contract;
5. entitlement activation is driven only by authoritative payment success;
6. duplicate payment success events do not double-fulfill;
7. observability exists for bootstrap, checkout start, payment success, and config delivery;
8. the team can safely start White-Label bot provisioning and Public Network snapshot implementation on top of the shared base.

## Recommended Delivery Shape

Wave 1 should be implemented as a small number of coherent vertical slices, not dozens of unrelated commits:

1. Runtime context and attribution slice
2. Mini App route and auth continuity slice
3. Mini App bootstrap slice
4. Telegram Stars payment foundation slice
5. Payment-to-entitlement correctness and observability slice

## Go / No-Go Rule

Do not start broad White-Label feature work or public Speed Map launch work until Wave 1 exit criteria are met.


---

## Source Document: `docs/growth-platform/15-wave-1-shared-runtime-and-miniapp-foundation.md`

# Wave 1 Execution Backlog — Shared Runtime Context and Mini App Foundation

## Purpose

This document decomposes the first implementation wave into concrete execution streams, task groups, dependencies, and acceptance criteria.

## Wave 1 Scope

Wave 1 includes:

- `Group 1 — Shared Runtime Context`
- `Mini App routing and auth continuity`
- `Mini App bootstrap foundation`
- `Mini App Telegram Stars payment foundation`
- `payment-to-entitlement correctness`
- `minimum observability and QA coverage`

## Delivery Streams

| Stream | Focus | Primary Owners |
|---|---|---|
| W1-A | Shared runtime and attribution core | Backend |
| W1-B | Mini App routing and auth continuity | Frontend |
| W1-C | Mini App bootstrap and read model | Backend + Frontend |
| W1-D | Telegram Stars payment foundation | Backend + Bot Service + Frontend |
| W1-E | Observability, QA, and release readiness | Platform + QA |

## Stream W1-A — Shared Runtime Context

### W1-A1: Define Runtime Commercial Context Contract

Objective:

- introduce a canonical runtime context that can serve both platform and partner-branded surfaces.

Tasks:

- define runtime context type and backend serialization contract;
- include tenant, brand, commercial policy, and attribution sections;
- align surface taxonomy with dossier.

Primary areas:

- `backend/src/domain/*`
- `backend/src/application/use_cases/*`
- `frontend/src/*` shared types where required

Acceptance criteria:

- one canonical runtime contract exists;
- both `platform` and `partner` tenant modes are represented;
- Mini App bootstrap can depend on it without ad hoc extensions.

### W1-A2: Identity and Attribution Linkage Expansion

Objective:

- make attribution and Telegram identity reliable enough for Mini App and later partner flows.

Tasks:

- expand identity link model where needed;
- normalize `source`, `surface`, `partner`, `bot`, `storefront`, `campaign`, and `start_param`;
- ensure attribution survives into payment intent creation.

Acceptance criteria:

- backend can resolve attribution for Mini App quote creation;
- unresolved or malformed attribution fails safely.

### W1-A3: Migration Group 1 Implementation

Objective:

- implement the first migration group from the dossier.

Tasks:

- add shared runtime context support fields/tables;
- add surface and attribution metadata support;
- add any transitional backfill logic needed for existing users or sessions.

Acceptance criteria:

- schema supports runtime context without JSON-only shortcuts;
- migration order is documented in code comments or migration metadata.

## Stream W1-B — Mini App Routing and Auth Continuity

### W1-B1: Fix Canonical Root Routing

Objective:

- make Mini App entry deterministic.

Tasks:

- change Mini App root redirect to `/[locale]/miniapp/home`;
- review any route guards or navigation assumptions that still point to `/home` or `/dashboard`.

Acceptance criteria:

- direct Mini App root entry always lands in Mini App namespace;
- no auth success path escapes to regular dashboard routes.

### W1-B2: Preserve Mini App Namespace Through Auth and 2FA

Objective:

- keep all return paths Mini App-safe.

Tasks:

- update Mini App auth provider redirects;
- update 2FA return handling;
- review any global auth fallback that assumes web dashboard as destination.

Acceptance criteria:

- authenticated Mini App users stay in `/miniapp/*`;
- 2FA completion returns into Mini App flow.

### W1-B3: Add Route Regression Tests

Objective:

- prevent future route drift.

Tasks:

- add route and auth continuity coverage;
- cover root entry, auth success, and 2FA return.

Acceptance criteria:

- regressions fail in automated tests.

## Stream W1-C — Mini App Bootstrap and Read Model

### W1-C1: Create `/api/v1/miniapp/bootstrap`

Objective:

- replace broad client fan-out with one consolidated bootstrap.

Tasks:

- create Mini App namespace if absent;
- assemble runtime, user, subscription, trial, wallet, devices, referral, support, and primary CTA;
- include freshness metadata.

Acceptance criteria:

- home state can render from bootstrap;
- runtime tenant context is included;
- bootstrap response is small and stable enough for Telegram webview usage.

### W1-C2: Refactor Home and Plans to Use Mini App Contracts

Objective:

- reduce generic API fan-out and align UI with new read model.

Tasks:

- introduce Mini App API client layer;
- move critical home/plans rendering to bootstrap or Mini App-specific contracts;
- keep fallback handling explicit.

Acceptance criteria:

- home and plans screens do not depend on large uncontrolled request fans;
- failures degrade predictably.

### W1-C3: Prepare Server-Picker Input Contract

Objective:

- make sure later server picker work is unblocked.

Tasks:

- define recommended server shape in bootstrap or servers endpoint;
- ensure contract is compatible with future Network Intelligence snapshot data.

Acceptance criteria:

- server recommendation is represented in the Mini App contract even if full server picker UI is not complete yet.

## Stream W1-D — Telegram Stars Payment Foundation

### W1-D1: Create Quote Foundation

Objective:

- establish a server-side commercial intent before invoice creation.

Tasks:

- create quote endpoint;
- validate plan, add-ons, tenant context, attribution, and pricing;
- make quote idempotent where appropriate.

Acceptance criteria:

- quote is stable enough to be the basis for invoice creation;
- malformed attribution or invalid tenant context is rejected.

### W1-D2: Create Telegram Invoice Foundation

Objective:

- create server-side invoice generation for Stars purchases.

Tasks:

- create invoice endpoint returning payment ID and invoice URL;
- enforce `XTR` flow assumptions;
- persist payment intent before returning invoice data.

Acceptance criteria:

- Mini App can open Telegram invoice from backend-created data;
- no client-side price tampering path exists.

### W1-D3: Pre-Checkout Validation Integration

Objective:

- ensure Telegram payment flow is checked before checkout proceeds.

Tasks:

- define how bot runtime validates quote, tenant state, suspension state, and policy state on `pre_checkout_query`;
- reject inconsistent or unsafe purchase attempts;
- log failures for investigation.

Acceptance criteria:

- pre-checkout rejects invalid or stale payment attempts;
- validation path is explicit and testable.

### W1-D4: Authoritative Successful Payment Fulfillment

Objective:

- tie service delivery to authoritative payment success only.

Tasks:

- implement `successful_payment` authoritative transition;
- map payment success to order finalization and entitlement activation;
- add replay-safe handling for duplicate success events.

Acceptance criteria:

- entitlement is not activated on invoice close alone;
- duplicate success events do not double-fulfill.

### W1-D5: Refund and Reversal Baseline

Objective:

- make refund handling non-destructive from the beginning.

Tasks:

- define refund-aware payment state transitions;
- create settlement reversal design hooks for later White-Label finance;
- ensure refund does not require mutating historical sale facts.

Acceptance criteria:

- refund path is represented in the model and tests;
- later ledger implementation can consume it without redesign.

## Stream W1-E — Observability, QA, and Release Readiness

### W1-E1: Event Instrumentation for the First Critical Path

Objective:

- instrument the exact path being built.

Required events:

- `miniapp_opened`
- `miniapp_bootstrap_loaded`
- `miniapp_auth_success`
- `checkout_started`
- `miniapp_invoice_opened`
- `payment_success`
- `config_delivered`

Acceptance criteria:

- events are visible in development and test environments;
- event payload includes surface and runtime context.

### W1-E2: Core Test Matrix

Objective:

- validate Wave 1 before broader feature work begins.

Required tests:

- route continuity tests;
- bootstrap contract tests;
- quote and invoice idempotency tests;
- duplicate `successful_payment` handling tests;
- pre-checkout rejection tests;
- payment-to-entitlement integration tests.

Acceptance criteria:

- Wave 1 critical path has automated coverage across unit, integration, and E2E layers where appropriate.

### W1-E3: Release Gate for Wave 1 Completion

Objective:

- define the point where the team can start Wave 2 work safely.

Wave 1 release gate:

- routing fixed;
- runtime context implemented;
- bootstrap live;
- quote and invoice flows live in development or staging;
- successful payment path authoritative;
- regression tests passing;
- required telemetry live.

## Dependencies

| Dependency | Required By |
|---|---|
| Runtime context contract | Bootstrap, quote creation, later partner branding |
| Telegram Stars payment policy | Quote and invoice foundation |
| Surface taxonomy | Observability and analytics |
| Migration Group 1 | Runtime context persistence |
| Existing entitlement model | Payment fulfillment |

## Explicit Non-Goals for Wave 1

- full White-Label onboarding UX
- public partner launch
- public Speed Map rollout
- recurring Telegram Stars subscriptions
- payout automation
- full admin control plane implementation

## Recommended PR / Slice Order

1. Runtime context contract + migration group 1
2. Mini App route and auth corrections
3. Mini App bootstrap API + frontend adoption
4. Quote and invoice backend foundation
5. Pre-checkout + successful-payment authoritative path
6. Observability + regression tests

## Wave 1 Done State

The team may consider Wave 1 complete only when the first end-to-end Mini App conversion path is technically correct and reusable by later platform layers, not merely visually functional.


---

## Source Document: `docs/growth-platform/16-wave-1-engineering-backlog-by-repo.md`

# Wave 1 Engineering Backlog by Repo

## Purpose

This document converts the Wave 1 execution backlog into repo-by-repo engineering work. It is intended to be close enough to implementation that engineering leads can assign slices without reinterpreting the platform dossier.

## Wave 1 Scope Reminder

Wave 1 covers:

- `Group 1 — Shared Runtime Context`
- Mini App routing and auth continuity
- Mini App bootstrap foundation
- Telegram Stars payment foundation
- payment-to-entitlement correctness
- minimum observability and QA coverage

## Repo Overview

| Repo Area | Wave 1 Role |
|---|---|
| `backend/` | source of truth for runtime context, quote/invoice/payment state, entitlement correctness |
| `frontend/` | canonical Mini App routing, bootstrap-driven UI, invoice lifecycle UX |
| `services/telegram-bot/` | Telegram payment event handling, pre-checkout validation, successful payment handoff |
| `partner/` | mostly untouched in Wave 1 except for contract awareness |
| `infra/` | no major public rollout work in Wave 1, limited observability support only |

## Backend Backlog

## B1. Runtime Context Foundation

### Objective

Introduce a canonical runtime commercial context and attribution contract that Mini App and later partner-branded flows can consume.

### Likely existing anchors

- `backend/src/presentation/dependencies/auth_realms.py`
- `backend/src/presentation/dependencies/partner_workspace.py`
- `backend/src/presentation/api/v1/auth/realm_context.py`
- `backend/src/domain/entities/auth_realm.py`
- `backend/src/domain/entities/storefront.py`
- `backend/src/domain/entities/customer_commercial_binding.py`
- `backend/src/domain/entities/attribution_touchpoint.py`
- `backend/src/domain/entities/order_attribution_result.py`
- `backend/src/application/use_cases/auth_realms/resolve_realm.py`
- `backend/src/application/use_cases/commerce_sessions/context_resolution.py`
- `backend/src/application/use_cases/attribution/*`

### Tasks

- define a reusable runtime commercial context DTO or domain contract;
- include tenant, brand, commercial policy, attribution, and surface data;
- align auth realm resolution with runtime context resolution;
- ensure attribution resolution can survive into quote and payment creation.

### Acceptance criteria

- backend exposes one canonical runtime context shape for Mini App bootstrap;
- runtime context can represent both `platform` and future `partner` tenant modes;
- attribution fields are explicit and not inferred ad hoc by every endpoint.

## B2. Migration Group 1

### Objective

Implement the first migration wave that supports shared runtime context and attribution.

### Likely existing anchors

- `backend/alembic/versions/20260417_phase1_auth_realms.py`
- `backend/alembic/versions/20260417_phase1_storefront_core.py`
- `backend/alembic/versions/20260417_phase1_partner_workspace.py`
- `backend/alembic/versions/20260421_phase14_mobile_telegram_oidc_subject.py`

### Tasks

- create new Alembic revision for runtime context and attribution support;
- extend existing realm/session/attribution tables as needed;
- document backfill behavior for existing Mini App and Telegram-linked users.

### Acceptance criteria

- no Wave 1 logic depends on undocumented schema shortcuts;
- migration order is explicit and compatible with current Alembic structure.

## B3. Mini App Namespace

### Objective

Add a Mini App-specific backend namespace that aggregates existing use cases into Telegram-optimized contracts.

### Likely existing anchors

- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`
- `backend/src/presentation/api/v1/trial/routes.py`
- `backend/src/presentation/api/v1/payments/routes.py`
- `backend/src/presentation/api/v1/quotes/routes.py`
- `backend/src/presentation/api/v1/payment_attempts/routes.py`
- `backend/src/application/use_cases/auth/telegram_miniapp.py`
- `backend/src/application/use_cases/trial/activate_trial.py`
- `backend/src/application/use_cases/payments/checkout.py`
- `backend/src/application/use_cases/payments/commit_checkout.py`
- `backend/src/application/use_cases/subscriptions/get_current_entitlements.py`

### Tasks

- create `backend/src/presentation/api/v1/miniapp/`;
- implement `bootstrap`, `offers`, `quote`, `invoice`, and `payment status` paths for Wave 1;
- reuse existing domain logic instead of cloning it;
- include freshness and runtime context in bootstrap.

### Acceptance criteria

- home and plans flows can depend on Mini App-specific contracts instead of uncontrolled generic fan-out;
- bootstrap endpoint is fast, stable, and Telegram-oriented.

## B4. Payment and Entitlement Correctness

### Objective

Establish the correct baseline Telegram Stars purchase contract.

### Likely existing anchors

- `backend/src/domain/entities/payment.py`
- `backend/src/domain/entities/payment_attempt.py`
- `backend/src/domain/entities/quote_session.py`
- `backend/src/domain/entities/checkout_session.py`
- `backend/src/application/use_cases/payments/checkout.py`
- `backend/src/application/use_cases/payments/commit_checkout.py`
- `backend/src/application/use_cases/payments/post_payment.py`
- `backend/src/application/use_cases/payments/payment_webhook.py`
- `backend/src/application/use_cases/orders/create_order_from_checkout.py`
- `backend/src/application/services/entitlements_service.py`
- `backend/src/presentation/api/v1/payment_attempts/*`
- `backend/src/presentation/api/v1/checkout_sessions/*`
- `backend/src/presentation/api/v1/payments/*`

### Tasks

- make quote creation runtime-context-aware;
- create invoice generation path for `XTR` purchase flows;
- define authoritative state transitions for payment success and replay handling;
- ensure entitlement activation occurs only after authoritative success.

### Acceptance criteria

- invoice UI close alone never fulfills service;
- duplicate success events do not double-activate entitlement;
- payment state can be observed through backend contracts.

## B5. Minimum Refund and Reversal Hooks

### Objective

Prepare the system for refund-safe behavior without implementing the full settlement layer yet.

### Likely existing anchors

- `backend/src/presentation/api/v1/refunds/*`
- `backend/src/presentation/api/v1/payment_disputes/*`
- `backend/src/application/use_cases/payment_disputes/*`
- `backend/alembic/versions/20260418_phase2_refunds_and_disputes.py`

### Tasks

- define refund-aware payment state mapping;
- add explicit reversal hooks for later ledger integration;
- ensure refund does not imply destructive history mutation.

### Acceptance criteria

- refund path is represented in code contracts and tests;
- later White-Label finance can attach ledger entries without redesigning payment history.

## Frontend Backlog

## F1. Route and Auth Continuity

### Likely existing anchors

- `frontend/src/app/[locale]/miniapp/page.tsx`
- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
- `frontend/src/stores/auth-store.ts`
- `frontend/src/features/auth/lib/pending-twofa-client.ts`
- `frontend/src/i18n/navigation.ts`

### Tasks

- fix Mini App root redirect;
- keep auth success inside Mini App namespace;
- keep 2FA completion inside Mini App namespace;
- add or update route regression tests.

### Acceptance criteria

- no normal Mini App auth path exits to `/dashboard`;
- root entry always lands in `/miniapp/home`.

## F2. Runtime and Bootstrap Adoption

### Likely existing anchors

- `frontend/src/app/[locale]/miniapp/layout.tsx`
- `frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts`
- `frontend/src/app/[locale]/miniapp/home/page.tsx`
- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/lib/api/auth.ts`
- `frontend/src/lib/api/payments.ts`
- `frontend/src/lib/api/vpn.ts`
- `frontend/src/lib/api/referral.ts`
- `frontend/src/lib/api/servers.ts`

### Tasks

- introduce Mini App API client layer for bootstrap-oriented reads;
- reduce page-level request fan-out in home and plans;
- add runtime hooks needed for invoice lifecycle and Telegram UX.

### Acceptance criteria

- home and plans render from Mini App-specific contracts;
- runtime hook layer supports later server picker and payment work.

## F3. Payment UX Foundation

### Likely existing anchors

- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/payments/page.tsx`
- `frontend/src/lib/api/payments.ts`
- `frontend/src/lib/api/client.ts`
- `frontend/src/stores/__tests__/auth-store-miniapp.test.ts`

### Tasks

- integrate quote and invoice flow with backend Mini App API;
- handle invoice open, close, pending, paid, canceled, and failed states;
- refresh payment status server-authoritatively after invoice UI close.

### Acceptance criteria

- client UI never treats invoice close as delivery success;
- payment states are explicit and testable.

## Telegram Bot Service Backlog

## T1. Pre-Checkout Validation

### Current repo signal

The current `services/telegram-bot/src/handlers/payment.py` responds to pre-checkout with:

- `ok=False`
- `"Telegram Stars are not enabled in this flow"`

This is a direct Wave 1 gap.

### Likely existing anchors

- `services/telegram-bot/src/handlers/payment.py`
- `services/telegram-bot/src/services/payment_stars.py`
- `services/telegram-bot/src/services/api_client.py`
- `services/telegram-bot/src/services/payment_service.py`

### Tasks

- replace placeholder rejection with real pre-checkout validation;
- validate quote, user, tenant context, and suspension state;
- return user-safe error when checkout must be rejected.

### Acceptance criteria

- valid orders can pass pre-checkout;
- invalid or stale orders are rejected predictably and logged.

## T2. Successful Payment Handling

### Current repo signal

`successful_payment_handler` currently logs `unexpected_successful_payment_received`, which means the baseline flow is not production-ready yet.

### Tasks

- map successful payment payloads to backend payment finalization;
- ensure duplicate event safety;
- trigger config-ready or entitlement-ready state through the backend rather than local assumptions.

### Acceptance criteria

- successful payment no longer lands in an "unexpected" path;
- backend becomes the source of truth for fulfillment.

## T3. Deep Links and Support

### Likely existing anchors

- `services/telegram-bot/src/utils/deep_links.py`
- `services/telegram-bot/src/handlers/support.py`
- `services/telegram-bot/src/handlers/subscription.py`
- `services/telegram-bot/src/keyboards/payment.py`

### Tasks

- align `startapp` payload generation with signed attribution expectations;
- ensure payment-support path is available for Telegram payment issues;
- keep bot-generated links aligned with Mini App route policy.

### Acceptance criteria

- bot entry links are compatible with Mini App runtime expectations;
- payment-support path exists for operational use.

## Partner Repo Backlog

Wave 1 should avoid major `partner/` implementation, but should reserve compatibility work if shared runtime contracts need aligned TypeScript types or preview scaffolding.

Likely areas to watch:

- `partner/src/features/storefront-shell/lib/runtime.ts`
- `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts`

## Recommended Implementation Order

1. Backend runtime context and migration group 1
2. Frontend Mini App route/auth continuity
3. Backend Mini App bootstrap
4. Frontend bootstrap adoption
5. Backend quote/invoice foundation
6. Telegram bot pre-checkout and successful payment handling
7. Payment-to-entitlement tests and observability

## Wave 1 Completion Signal

This backlog is complete only when the first Mini App conversion path is both technically correct and reusable by later White-Label and Network Intelligence work.


---

## Source Document: `docs/growth-platform/17-wave-1-file-level-change-map.md`

# Wave 1 File-Level Change Map

## Purpose

This file maps Wave 1 work to concrete repo files and clarifies whether each file is expected to be:

- `Modify`
- `Create`
- `Verify`

It is not a promise that every listed file must change, but it is the expected implementation surface.

## Backend — Shared Runtime Context

| File | Action | Why |
|---|---|---|
| `backend/src/presentation/dependencies/auth_realms.py` | Modify | Align runtime context with auth realm resolution |
| `backend/src/presentation/dependencies/partner_workspace.py` | Modify | Tenant-aware partner workspace resolution hooks |
| `backend/src/presentation/api/v1/auth/realm_context.py` | Modify | Shared runtime context handoff |
| `backend/src/domain/entities/auth_realm.py` | Verify | Ensure realm model can support Wave 1 assumptions |
| `backend/src/domain/entities/storefront.py` | Verify | Check compatibility with future partner-branded runtime |
| `backend/src/domain/entities/customer_commercial_binding.py` | Modify | Runtime commercial policy linkage |
| `backend/src/domain/entities/attribution_touchpoint.py` | Modify | Attribution fields for `start_param`, partner, surface |
| `backend/src/domain/entities/order_attribution_result.py` | Modify | Preserve attribution into order/payment flow |
| `backend/src/application/use_cases/auth_realms/resolve_realm.py` | Modify | Resolve realm into runtime context |
| `backend/src/application/use_cases/commerce_sessions/context_resolution.py` | Modify | Shared context resolution logic |
| `backend/src/application/use_cases/attribution/*` | Modify | Attribution resolution and recording alignment |

## Backend — Alembic / Migration Group 1

| File / Area | Action | Why |
|---|---|---|
| `backend/alembic/versions/` new revision | Create | Runtime context and attribution schema support |
| `backend/alembic/versions/20260417_phase1_auth_realms.py` | Verify | Existing realm foundation baseline |
| `backend/alembic/versions/20260417_phase1_storefront_core.py` | Verify | Existing storefront baseline |
| `backend/alembic/versions/20260417_phase1_partner_workspace.py` | Verify | Existing partner workspace baseline |
| `backend/alembic/versions/20260421_phase14_mobile_telegram_oidc_subject.py` | Verify | Existing Telegram identity-related migration context |

## Backend — Mini App Namespace

| File | Action | Why |
|---|---|---|
| `backend/src/presentation/api/v1/miniapp/` | Create | New Mini App API namespace |
| `backend/src/presentation/api/v1/auth/routes.py` | Modify | Reuse or adapt Mini App auth handoff |
| `backend/src/presentation/api/v1/telegram/routes.py` | Modify | Align Telegram bot and Mini App commercial contracts |
| `backend/src/presentation/api/v1/trial/routes.py` | Verify / Modify | Reuse for Mini App trial actions |
| `backend/src/presentation/api/v1/payments/routes.py` | Verify / Modify | Payment status and shared payment views |
| `backend/src/presentation/api/v1/quotes/routes.py` | Verify / Modify | Quote reuse or adaptation |
| `backend/src/presentation/api/v1/payment_attempts/routes.py` | Verify / Modify | Payment state visibility |
| `backend/src/application/use_cases/auth/telegram_miniapp.py` | Modify | Bootstrap/session integration |
| `backend/src/application/use_cases/trial/activate_trial.py` | Verify | Trial eligibility reuse |
| `backend/src/application/use_cases/payments/checkout.py` | Modify | Quote and checkout semantics for Mini App |
| `backend/src/application/use_cases/payments/commit_checkout.py` | Modify | Align with Stars and authoritative flow |
| `backend/src/application/use_cases/subscriptions/get_current_entitlements.py` | Verify | Bootstrap and post-payment access state |

## Backend — Payment and Fulfillment Correctness

| File | Action | Why |
|---|---|---|
| `backend/src/domain/entities/payment.py` | Modify | Explicit payment state support |
| `backend/src/domain/entities/payment_attempt.py` | Modify | Attempt tracking for invoice and reconciliation |
| `backend/src/domain/entities/quote_session.py` | Modify | Quote persistence and integrity |
| `backend/src/domain/entities/checkout_session.py` | Modify | Checkout session semantics |
| `backend/src/application/use_cases/payments/post_payment.py` | Modify | Authoritative success handling |
| `backend/src/application/use_cases/payments/payment_webhook.py` | Modify | Payment event reconciliation path |
| `backend/src/application/use_cases/orders/create_order_from_checkout.py` | Modify | Fulfillment bridge to order creation |
| `backend/src/application/services/entitlements_service.py` | Verify / Modify | Authoritative entitlement activation |
| `backend/src/presentation/api/v1/refunds/*` | Verify | Refund extension path |
| `backend/src/presentation/api/v1/payment_disputes/*` | Verify | Dispute and refund readiness |

## Frontend — Mini App Route and Auth Continuity

| File | Action | Why |
|---|---|---|
| `frontend/src/app/[locale]/miniapp/page.tsx` | Modify | Fix root redirect into Mini App namespace |
| `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx` | Modify | Keep auth success inside Mini App |
| `frontend/src/stores/auth-store.ts` | Modify | Align Mini App auth state and follow-up behavior |
| `frontend/src/features/auth/lib/pending-twofa-client.ts` | Modify | Preserve Mini App-safe return path |
| `frontend/src/i18n/navigation.ts` | Verify | Ensure router helpers remain compatible |
| `frontend/src/stores/__tests__/auth-store-miniapp.test.ts` | Modify | Route/auth continuity regression coverage |

## Frontend — Bootstrap and Runtime

| File | Action | Why |
|---|---|---|
| `frontend/src/app/[locale]/miniapp/layout.tsx` | Modify | Runtime providers and bootstrap boundary |
| `frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts` | Modify | Runtime lifecycle, invoice integration hooks |
| `frontend/src/app/[locale]/miniapp/home/page.tsx` | Modify | Bootstrap-driven home rendering |
| `frontend/src/app/[locale]/miniapp/plans/page.tsx` | Modify | Quote and invoice UX |
| `frontend/src/lib/api/miniapp.ts` | Create | Mini App-specific API client |
| `frontend/src/lib/api/auth.ts` | Verify / Modify | Mini App session interactions |
| `frontend/src/lib/api/payments.ts` | Verify / Modify | Payment status helpers |
| `frontend/src/lib/api/vpn.ts` | Verify | Config and entitlement reads |
| `frontend/src/lib/api/referral.ts` | Verify | Referral integration path |
| `frontend/src/lib/api/servers.ts` | Verify | Future server recommendation compatibility |

## Frontend — Tests

| File | Action | Why |
|---|---|---|
| `frontend/src/app/[locale]/miniapp/home/__tests__/page.test.tsx` | Modify | Bootstrap/home contract changes |
| `frontend/src/app/[locale]/miniapp/plans/__tests__/page.test.tsx` | Modify | Quote/invoice behavior |
| `frontend/src/lib/api/__tests__/payments.test.ts` | Modify | Payment contract changes |
| `frontend/src/stores/__tests__/auth-store.test.ts` | Verify / Modify | Auth state side-effects |

## Telegram Bot Service — Payment Path

| File | Action | Why |
|---|---|---|
| `services/telegram-bot/src/handlers/payment.py` | Modify | Replace placeholder pre-checkout rejection and unexpected success handling |
| `services/telegram-bot/src/services/payment_stars.py` | Modify | Align Stars invoice and status semantics |
| `services/telegram-bot/src/services/api_client.py` | Modify | Backend calls for quote, invoice, payment status, and fulfillment |
| `services/telegram-bot/src/services/payment_service.py` | Verify / Modify | Shared payment orchestration |
| `services/telegram-bot/src/handlers/subscription.py` | Verify / Modify | Subscription flow integration with Stars path |
| `services/telegram-bot/src/keyboards/payment.py` | Verify / Modify | Payment CTA and retry behavior |
| `services/telegram-bot/src/utils/deep_links.py` | Modify | Signed `startapp` and Mini App link generation |
| `services/telegram-bot/src/handlers/support.py` | Modify | Payment-support path |

## Partner Repo — Watch List

| File | Action | Why |
|---|---|---|
| `partner/src/features/storefront-shell/lib/runtime.ts` | Verify | Future compatibility with runtime context contract |
| `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts` | Verify | No Wave 1 implementation expected, but contract alignment matters |

## File-Level Notes from Current Baseline

### Verified Mini App Routing Gap

- `frontend/src/app/[locale]/miniapp/page.tsx` currently redirects outside the Mini App namespace.

### Verified Mini App Auth Gap

- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx` currently sends success paths outside the canonical Mini App route space.

### Verified Telegram Bot Payment Gap

- `services/telegram-bot/src/handlers/payment.py` currently rejects pre-checkout in the Stars flow and treats `successful_payment` as unexpected.

This makes the bot payment handler a mandatory Wave 1 file, not an optional follow-up.

## Suggested First PR Sequence

### PR 1

- runtime context contract
- migration group 1

### PR 2

- Mini App root routing
- Mini App auth and 2FA return continuity

### PR 3

- Mini App bootstrap API
- frontend bootstrap adoption

### PR 4

- quote and invoice foundation
- bot pre-checkout and successful payment handling

### PR 5

- tests, observability, and payment-to-entitlement hardening


---

## Source Document: `docs/growth-platform/adr/ADR-001-telegram-stars-as-primary-telegram-payment-rail.md`

# ADR-001: Telegram Stars as Primary Telegram Payment Rail

## Status

Accepted

## Context

CyberVPN plans to sell digital VPN access inside Telegram Mini Apps and Telegram bots. Telegram platform rules require digital goods and services inside Telegram app surfaces to use Telegram-native payment rails.

## Decision

All Telegram-native purchase flows use Telegram Stars / XTR as the primary payment rail.

## Consequences

- Mini App and Telegram bot checkout flows must use Telegram invoice behavior.
- entitlement activation must be tied to Telegram-authoritative payment success;
- non-Telegram payment rails remain available only on approved external surfaces.

## Alternatives Considered

- Continue using CryptoBot as default in-Telegram rail
- Redirect all Telegram checkout to external web

Both were rejected because they either conflict with platform expectations or increase checkout friction materially.


---

## Source Document: `docs/growth-platform/adr/ADR-002-shared-multi-tenant-runtime-for-white-label.md`

# ADR-002: Shared Multi-Tenant Runtime for White-Label

## Status

Accepted

## Context

White-Label needs to scale to many partners while preserving one shared payment, entitlement, analytics, and runtime core. One deployment per partner would increase operational complexity and security risk.

## Decision

White-Label uses a shared multi-tenant runtime with per-partner configuration, branding, and commercial policy.

## Consequences

- tenant context becomes a first-class architectural requirement;
- branding and storefront behavior must be DB-driven;
- provisioning focuses on identity and configuration, not code deployment.

## Alternatives Considered

- One deployment per partner
- Separate product branch for major partners

These were rejected because they reduce maintainability, slow rollout, and complicate payment and entitlement coherence.


---

## Source Document: `docs/growth-platform/adr/ADR-003-public-network-snapshot-instead-of-direct-prometheus.md`

# ADR-003: Public Network Snapshot Instead of Direct Prometheus

## Status

Accepted

## Context

CyberVPN wants to expose public network intelligence. Prometheus is an internal operational system and is not appropriate as a direct public request path.

## Decision

Public Network APIs and pages read only from sanitized, materialized network snapshots.

## Consequences

- an aggregation worker becomes mandatory;
- freshness and stale handling become explicit product concerns;
- public data can be cached safely and served consistently.

## Alternatives Considered

- Direct public querying of Prometheus
- Frontend direct polling of internal monitoring endpoints

These were rejected because they create security, performance, and truthfulness risks.


---

## Source Document: `docs/growth-platform/adr/ADR-004-miniapp-as-canonical-conversion-runtime.md`

# ADR-004: Mini App as Canonical Conversion Runtime

## Status

Accepted

## Context

CyberVPN already has a Mini App baseline and wants both platform and partner-branded customer journeys to converge on one low-friction conversion surface.

## Decision

The Telegram Mini App becomes the canonical conversion runtime for CyberVPN and partner-branded Telegram entry points.

## Consequences

- Mini App must be tenant-aware from the start;
- partner-branded Mini App flows reuse the same core runtime;
- routing, payments, config delivery, and analytics must be designed for reuse.

## Alternatives Considered

- Separate CyberVPN and partner Mini App codebases
- Web-first checkout with Mini App as a thin wrapper

These were rejected because they increase fragmentation and weaken Telegram-native conversion.


---

## Source Document: `docs/growth-platform/adr/ADR-005-cybervpn-as-platform-of-record.md`

# ADR-005: CyberVPN as Platform of Record

## Status

Accepted

## Context

White-Label requires a clear baseline for commercial responsibility, settlement logic, refunds, and support. Early ambiguity would complicate legal, payment, and partner operations.

## Decision

CyberVPN remains platform-of-record and merchant-of-record in the baseline White-Label model. Partners act as branded resellers or distribution channels.

## Consequences

- payment and entitlement logic stay centralized;
- partner payouts are derived from shared settlement accounting;
- support and refund flows remain more controllable.

## Alternatives Considered

- Full merchant independence per partner from initial launch
- Mixed unmanaged model with partner-defined payment ownership

These were rejected for initial rollout because they increase risk, legal complexity, and operational fragmentation.


---

## Source Document: `docs/growth-platform/miniapp/00-miniapp-overview.md`

# Telegram Mini App Overview

## Purpose

The Telegram Mini App is the canonical customer conversion runtime for CyberVPN. It should compress the path from first open to active service access into one Telegram-native flow:

`open -> bootstrap -> trial or payment -> config -> connect -> share`

## Role in the Growth Loop

- receives users from public Network Intelligence pages;
- converts Telegram-native demand faster than web handoff flows;
- acts as the customer runtime reused later in partner-branded mode;
- feeds referral sharing and partner attribution back into the shared platform core.

## User Personas

### First-Time Telegram Buyer

- wants fast access;
- does not want to leave Telegram;
- responds well to simple plans and strong default recommendations.

### Returning Customer

- needs renewal, device recovery, and support;
- wants a quick status view and low-friction config access.

### Referral Customer

- comes via friend or partner link;
- should keep attribution context from `startapp` payload to purchase.

### Partner-Branded Customer

- enters through a branded bot or Mini App;
- still uses the same underlying entitlement and payment core.

## Screen Set

Required screens:

- home
- plans
- checkout
- servers
- devices
- wallet
- referral
- profile
- support
- payments history

## Current Baseline

CyberVPN already has a Mini App baseline in `frontend/src/app/[locale]/miniapp/` with multiple screens and Telegram auth hooks. The current baseline is strong enough to build on, but not yet canonical because:

- root routing is inconsistent;
- auth success can leave the Mini App route space;
- checkout is not yet fully aligned with Telegram Stars-first policy;
- Telegram lifecycle handling is partial;
- there is no full server picker experience yet.

## Backend Dependencies

The Mini App depends on:

- Telegram identity validation
- subscriptions and entitlements
- plans and add-ons
- wallet and payment state
- devices and config delivery
- referral and attribution
- support and incident-aware messaging
- Network Intelligence for recommended server data

## Runtime Modes

### Platform Mode

- tenant kind is `platform`
- CyberVPN brand and support profile apply
- platform commercial policy applies

### Partner-Branded Mode

- tenant kind is `partner`
- brand theme and support profile come from partner workspace
- commercial policy, attribution, and bot binding are partner-scoped

## Full Version Scope

- validated Telegram bootstrap
- Telegram Stars checkout
- server recommendation and manual selection
- device and config lifecycle
- partner-branded runtime support
- analytics and abuse controls
- support and payment issue paths

## Explicitly Out of Scope for First Integrated Release

- separate codebase for partner-branded Mini App
- direct public network queries from the Mini App
- unsupported payment rails inside Telegram
- unrestricted partner-level UI overrides


---

## Source Document: `docs/growth-platform/miniapp/01-miniapp-user-flows.md`

# Mini App User Flows

## Flow: First Open

### Entry Point

`https://t.me/<bot>?startapp=<payload>`

### Steps

1. User opens Telegram Mini App.
2. Frontend reads Telegram runtime and raw init data.
3. Frontend sends raw init data to backend.
4. Backend validates Telegram identity.
5. Backend resolves runtime commercial context.
6. Backend returns bootstrap payload.
7. User sees primary CTA based on subscription or trial status.

### Failure Cases

- invalid or expired init data;
- partner bot suspended;
- stale or failed bootstrap;
- unsupported locale or missing runtime context.

## Flow: Auth and Bootstrap

1. Mini App loads runtime provider.
2. Backend validates identity and session linkage.
3. Backend returns authenticated bootstrap payload.
4. Frontend renders home state without leaving `/miniapp/*`.

Failure cases:

- validation failure;
- session mismatch;
- 2FA-required edge case that must still preserve Mini App return path.

## Flow: Trial Activation

1. User sees `start_trial` CTA.
2. Frontend calls `POST /api/v1/miniapp/trial/activate`.
3. Backend checks trial eligibility and abuse signals.
4. Backend creates trial entitlement or rejects with reason.
5. Frontend refreshes bootstrap and navigates to config or server selection.

Failure cases:

- trial not eligible;
- suspicious user state;
- missing tenant policy;
- concurrency or duplicate request.

## Flow: Plan Selection

1. User opens plans screen.
2. Frontend loads offers and plan presentation for current tenant.
3. User selects plan and optional add-ons.
4. Frontend creates quote request.

Failure cases:

- plan hidden by commercial policy;
- offer expired;
- unsupported combination of plan and add-on.

## Flow: Stars Checkout

1. Frontend calls quote endpoint.
2. Backend validates catalog, pricing, partner attribution, and eligibility.
3. Frontend requests invoice creation.
4. Backend creates Telegram Stars invoice.
5. Frontend calls `Telegram.WebApp.openInvoice`.
6. Telegram closes invoice UI.
7. Frontend refreshes payment status from backend.
8. Backend grants entitlement only after authoritative successful payment.

Failure cases:

- invoice creation failure;
- user cancels invoice;
- payment pending or delayed;
- duplicate webhook or late confirmation.

## Flow: Payment Success

1. Payment success reaches backend.
2. Backend creates or updates order and entitlement.
3. Backend updates payment record and attribution state.
4. Frontend refreshes bootstrap or payment status.
5. User sees config delivery CTA.

## Flow: Payment Cancelled

1. Invoice closes without success.
2. Frontend refreshes payment state.
3. UI shows canceled or pending state.
4. User can retry or choose different plan.

## Flow: Config Delivery

1. User opens config or devices screen.
2. Backend returns tenant-aware service access state.
3. User sees QR, deep links, copy URLs, or device actions.
4. Action is logged as `config_delivered`.

Failure cases:

- no entitlement;
- config generation failure;
- service state degraded;
- device limit reached.

## Flow: Server Selection

1. User opens servers screen.
2. Frontend loads recommended and manual server list from Mini App API.
3. User selects server.
4. Selection updates recommendation state or config context.

Failure cases:

- no available regions;
- stale network intelligence data;
- selected server offline by time of action.

## Flow: Device Management

1. User opens devices screen.
2. Frontend loads active devices and limits.
3. User can inspect, revoke, or create device-specific access.
4. Backend enforces entitlement device rules.

## Flow: Referral Sharing

1. User opens referral screen.
2. Frontend loads signed share payload and share text.
3. User shares via Telegram-native path.
4. Attribution is preserved in `startapp` payload.

Failure cases:

- expired signed payload;
- abuse threshold reached;
- partner campaign disabled.

## Flow: Support

1. User opens support.
2. Frontend shows support routes from runtime context.
3. User can access general support or payment support.

## Flow: Expired Subscription Renewal

1. Bootstrap shows `renew` CTA.
2. User enters plans or checkout.
3. Renewal follows the same quote and invoice flow with current attribution rules.

## Flow: Partner-Branded Entry

1. User opens partner-managed Telegram entry point.
2. Backend resolves partner tenant context.
3. Brand theme, support, and commercial policy are applied.
4. Purchase still flows through shared payment and entitlement core.


---

## Source Document: `docs/growth-platform/miniapp/02-miniapp-technical-spec.md`

# Mini App Technical Spec

## Routing Policy

Canonical route map:

- `/[locale]/miniapp`
- `/[locale]/miniapp/home`
- `/[locale]/miniapp/servers`
- `/[locale]/miniapp/plans`
- `/[locale]/miniapp/checkout`
- `/[locale]/miniapp/wallet`
- `/[locale]/miniapp/devices`
- `/[locale]/miniapp/referral`
- `/[locale]/miniapp/profile`
- `/[locale]/miniapp/support`
- `/[locale]/miniapp/payments`

Required rule:

- any user already inside `/miniapp/*` must stay inside `/miniapp/*` after auth, 2FA return, purchase refresh, and error recovery.

## Frontend Structure

Recommended feature structure:

- `features/miniapp-runtime`
- `features/miniapp-auth`
- `features/miniapp-checkout`
- `features/miniapp-servers`
- `features/miniapp-support`
- `features/miniapp-referral`

## Telegram Lifecycle Layer

Required hooks:

- `useTelegramWebAppRuntime`
- `useMiniAppViewport`
- `useMiniAppBackButton`
- `useMiniAppMainButton`
- `useMiniAppInvoice`
- `useMiniAppStartParam`
- `useMiniAppTheme`
- `useMiniAppHaptics`
- `useMiniAppAnalytics`

## Backend Namespace

New namespace:

- `backend/src/presentation/api/v1/miniapp/`

This namespace should aggregate existing use cases into Telegram-optimized read models instead of duplicating business logic.

The payment side of this namespace must integrate cleanly with Telegram bot payment events, including explicit pre-checkout validation and authoritative successful payment handling.

## Bootstrap Model

`GET /api/v1/miniapp/bootstrap` should return:

- session state
- runtime commercial context
- user profile hints
- subscription and trial state
- wallet state
- device summary
- recommended server
- primary CTA
- referral share context
- unresolved payment state
- support routes
- feature flags
- freshness timestamp

## Session Model

- Telegram raw init data validated by backend;
- platform session issued or resumed server-side;
- runtime tenant context resolved during bootstrap;
- no trust decisions based on `initDataUnsafe`.

## Tenant Context

Mini App must support:

- `platform` mode;
- `partner` mode.

Tenant context affects:

- branding;
- support links;
- plan visibility;
- pricing and discounts;
- attribution;
- analytics surface metadata.

## Error States

Required user-visible states:

- invalid Telegram session;
- bootstrap unavailable;
- stale runtime data;
- payment pending;
- no eligible offers;
- service degraded;
- support required.

## Caching

- bootstrap payload should be short-lived;
- payment state must refresh server-authoritatively;
- server list should prefer platform snapshot data over direct client recomputation;
- locale and brand assets may use stronger caching if versioned safely.

## i18n and RTL

- use existing locale infrastructure;
- preserve RTL layout integrity;
- support tenant-aware copy overlays only where explicitly allowed;
- support partner branding without fragmenting the translation model.

## Accessibility and Mobile UX Constraints

- large tap targets;
- reduced reliance on hover or precision gestures;
- safe area awareness;
- explicit loading, stale, and degraded states;
- avoid deep, modal-heavy nesting that conflicts with Telegram navigation.

## Baseline Corrections Required Before Feature Expansion

- fix root redirect into `/miniapp/home`;
- keep auth return path inside Mini App;
- replace generic page fan-out with bootstrap-oriented model;
- add full server picker surface;
- complete Stars-based invoice lifecycle.


---

## Source Document: `docs/growth-platform/miniapp/03-miniapp-api-contracts.md`

# Mini App API Contracts

## Contract Rules

- all endpoints are authenticated via validated Telegram session or active platform session bound to Mini App context;
- all writes must be idempotent where repeated client actions are likely;
- all responses must include machine-readable error codes;
- Telegram digital goods payment flows assume currency `XTR`.

## Endpoint List

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/miniapp/bootstrap` | Consolidated runtime bootstrap |
| GET | `/api/v1/miniapp/dashboard` | Optional dashboard-specific payload |
| GET | `/api/v1/miniapp/servers` | Recommended and manual server options |
| GET | `/api/v1/miniapp/offers` | Plans and add-ons filtered by runtime context |
| POST | `/api/v1/miniapp/trial/activate` | Trial activation |
| POST | `/api/v1/miniapp/checkout/quote` | Quote generation |
| POST | `/api/v1/miniapp/checkout/invoice` | Telegram Stars invoice creation |
| GET | `/api/v1/miniapp/payments/:id/status` | Payment status refresh |
| GET | `/api/v1/miniapp/devices` | Device summary and actions view |
| GET | `/api/v1/miniapp/config` | Config and access delivery read model |
| GET | `/api/v1/miniapp/referral` | Referral share payload and stats |
| POST | `/api/v1/miniapp/referral/share` | Share event capture |
| POST | `/api/v1/miniapp/events` | Telemetry/event ingest |

## `GET /api/v1/miniapp/bootstrap`

### Response

```ts
type MiniAppBootstrapResponse = {
  session: {
    authenticated: boolean
    userId: string | null
    telegramUserId: string | null
    authRealm: 'customer' | 'partner_customer'
  }
  runtime: {
    surface: 'telegram_miniapp' | 'partner_miniapp'
    tenant: {
      kind: 'platform' | 'partner'
      partnerId?: string
      workspaceId?: string
      storefrontId?: string
      botId?: string
    }
    brand: {
      name: string
      logoUrl?: string
      primaryColor?: string
      supportUrl?: string
    }
    attribution: {
      referralCode?: string
      campaign?: string
      startParam?: string
      source?: string
    }
  }
  freshness: {
    generatedAt: string
  }
}
```

### Error Codes

- `miniapp_invalid_session`
- `miniapp_tenant_unavailable`
- `miniapp_bootstrap_unavailable`

## `POST /api/v1/miniapp/trial/activate`

### Request

```json
{
  "idempotencyKey": "uuid"
}
```

### Response

```json
{
  "status": "activated",
  "entitlementId": "uuid",
  "expiresAt": "2026-05-01T00:00:00Z"
}
```

### Error Codes

- `trial_not_eligible`
- `trial_risk_blocked`
- `trial_already_used`

## `POST /api/v1/miniapp/checkout/quote`

### Request

```json
{
  "planId": "uuid",
  "addons": [
    {
      "addonId": "uuid",
      "qty": 1
    }
  ],
  "idempotencyKey": "uuid"
}
```

### Response

```json
{
  "quoteId": "uuid",
  "currency": "XTR",
  "displayedAmount": 499,
  "partnerAttribution": {
    "partnerId": "uuid",
    "botId": "uuid"
  }
}
```

### Error Codes

- `offer_not_available`
- `pricing_policy_rejected`
- `quote_invalid_state`

## `POST /api/v1/miniapp/checkout/invoice`

### Request

```json
{
  "quoteId": "uuid",
  "idempotencyKey": "uuid"
}
```

### Response

```json
{
  "paymentId": "uuid",
  "invoiceUrl": "https://t.me/$invoice/...",
  "currency": "XTR",
  "expiresAt": "2026-04-21T12:00:00Z"
}
```

### Error Codes

- `invoice_creation_failed`
- `quote_expired`
- `payment_method_not_available`

## `GET /api/v1/miniapp/payments/:id/status`

### Response

```json
{
  "paymentId": "uuid",
  "status": "pending",
  "entitlementActivated": false
}
```

### Status Values

- `pending`
- `paid`
- `cancelled`
- `failed`
- `refunded`

## Telegram Payment Contract Notes

- invoice creation is server-side only;
- client-side `invoiceClosed` is not authoritative for fulfillment;
- `pre_checkout_query` validation must occur in the Telegram bot runtime path;
- `successful_payment` is the authoritative event for delivery;
- recurring Stars subscriptions remain a future feature gate until baseline one-time purchase and renewal flows are stable.

## `GET /api/v1/miniapp/servers`

### Response Shape

```ts
type ServerOption = {
  id: string
  countryCode: string
  city: string
  publicName: string
  status: 'online' | 'degraded' | 'offline'
  latencyMs: number | null
  speedMbps: number | null
  uptimePct30d: number | null
  dpiScore?: number | null
  recommendedReason:
    | 'lowest_latency'
    | 'highest_stability'
    | 'best_dpi_resistance'
    | 'partner_default'
    | 'manual'
}
```

## Auth Requirements

- valid Telegram bootstrap session;
- resolved tenant context;
- anti-replay validation for payment and referral actions.

## Rate Limits

- bootstrap: moderate, per session and IP
- trial activation: strict, per user and abuse window
- quote and invoice creation: strict, per user and idempotency key
- event ingest: batched or limited by session

## Idempotency Rules

- trial activation requires idempotency key
- quote creation should support idempotency where same payload repeats
- invoice creation must be idempotent
- share events should deduplicate obvious retries


---

## Source Document: `docs/growth-platform/miniapp/04-miniapp-payment-flow.md`

# Mini App Payment Flow

## Policy

Telegram Mini App purchase flows use Telegram Stars / XTR as the primary and default payment rail.

For digital goods and services inside Telegram apps, Telegram requires Stars with currency `XTR`. Delivery must happen only after authoritative payment success, not after invoice UI close.

## Flow Overview

1. User selects a plan.
2. Frontend requests quote.
3. Backend validates pricing, attribution, and eligibility.
4. Frontend requests invoice creation.
5. Backend creates Telegram Stars invoice server-side.
6. Frontend opens invoice with Telegram WebApp API.
7. Telegram closes invoice UI.
8. Bot runtime handles `pre_checkout_query` and explicit validation.
9. Backend reconciles payment state.
10. Entitlement activates only after authoritative `successful_payment`.
11. User receives config or device onboarding.

## Quote Creation

Quote creation must include:

- plan and add-ons;
- runtime tenant context;
- referral and campaign metadata;
- active discounts and trial interactions;
- commercial policy restrictions.

Quote output should be immutable enough for invoice creation and reconciliation.

## Invoice Creation

Invoice creation must:

- reference a valid quote;
- bind payment to user, tenant, and attribution context;
- generate a Telegram-compatible invoice with currency `XTR`;
- persist payment ID before invoice URL is returned.

For Telegram Stars digital flows:

- third-party provider semantics do not define fulfillment;
- quote, tenant, and attribution must be locked before invoice open.

## Invoice Open

Frontend uses Telegram runtime to open invoice. The Mini App should:

- lock double-submit behavior;
- record `invoice_opened`;
- show pending state until backend refresh completes.

## Invoice Closed

When invoice UI closes:

- frontend refreshes payment status;
- backend may still report `pending` until authoritative payment update lands;
- UI must distinguish between `cancelled`, `pending`, and `paid`.
- UI close alone does not authorize delivery.

## Pre-Checkout Validation

The Telegram payment path must explicitly validate:

- quote still valid;
- tenant context still valid;
- pricing unchanged;
- commercial policy still allows the purchase;
- user and partner state not suspended.

The bot runtime must answer pre-checkout queries within Telegram time limits and reject unsafe or inconsistent orders.

## Successful Payment Handling

Required sequence:

1. payment success event reaches backend;
2. payment record becomes authoritative success;
3. order is finalized;
4. entitlement is activated;
5. config delivery becomes available;
6. partner attribution and analytics are finalized.

Authoritative success comes from Telegram payment events, not from the client UI.

## Refund Handling

The platform must define:

- when refunds are allowed;
- which support path is used;
- how partner revenue and internal settlement react to refunds;
- how entitlement state changes after refund.

Refund handling must create reversal effects in partner settlement accounting rather than mutating historical sale entries.

## Reconciliation

Use a dedicated reconciliation worker to:

- retry delayed status fetches;
- deduplicate webhook or event processing;
- repair transient mismatches;
- expose a clear operational dashboard.

This worker must also tolerate duplicate `successful_payment` events and refund follow-up events safely.

## Partner Attribution

Partner attribution must be attached at quote time and preserved through:

- invoice creation;
- payment success;
- entitlement creation;
- settlement accounting.

## Failure Cases

- quote expired before invoice creation;
- invoice creation failure;
- user closes invoice without payment;
- delayed payment success;
- duplicate success event;
- entitlement creation failure after payment success;
- refund after entitlement activation.

## Idempotency Rules

- one payment intent per quote and idempotency key;
- invoice creation returns existing live invoice where safe;
- payment success processing is idempotent;
- entitlement activation must not duplicate on replay;
- partner settlement reversal must not duplicate on refund replay.


---

## Source Document: `docs/growth-platform/miniapp/05-miniapp-security.md`

# Mini App Security

## Core Rules

1. Validate raw Telegram init data on the backend.
2. Never trust `initDataUnsafe` for protected actions.
3. Sign and expire all share and attribution payloads.
4. Activate service only after authoritative payment success.
5. Keep tenant context explicit in partner-branded flows.

## Telegram Session Validation

- raw init data enters backend on bootstrap;
- backend verifies origin and validity;
- session is bound to canonical user and Telegram identity;
- suspicious mismatches are logged and rate-limited;
- client telemetry around runtime events is informative only and not trusted as proof.

## `initDataUnsafe` Restrictions

Allowed uses:

- display-only hints in non-sensitive UI before bootstrap completes

Forbidden uses:

- price calculation
- partner attribution trust
- entitlement access
- trial eligibility
- payment authorization

## Signed `startapp` Payloads

Signed payloads should include:

- referral code if present;
- partner and campaign metadata if present;
- issuance time and expiry;
- signature or MAC.

## Referral and Attribution Signing

- never expose plain, unbounded referral tokens as the only signal;
- include expiry and integrity protection;
- validate surface and tenant where relevant.

## Payment Payload Security

- quote and invoice actions require server-issued references;
- client must not be able to change price or attribution silently;
- payment records must capture tenant and commercial context before invoice open;
- pre-checkout validation must reject quote tampering or stale tenant context.

## Trial Abuse Protection

Trial checks should incorporate:

- Telegram identity history;
- user linkage history;
- device and IP risk signals;
- referral loop patterns;
- partner risk policies.

## Config Delivery Protection

- require active entitlement;
- enforce device limits and access rules;
- audit config delivery;
- protect sensitive config URLs from uncontrolled reuse where possible.

## Rate Limits

Recommended strict controls for:

- trial activation
- quote creation
- invoice creation
- referral share events
- device mutation actions

## Suspicious Behavior Detection

Examples:

- many quote attempts with low follow-through;
- repeated invalid payloads;
- referral self-attribution loops;
- partner-branded flows hitting unexpected geographies or abuse patterns.

## Security Readiness Criteria

- bootstrap validation audited;
- payment activation server-authoritative;
- signed payloads implemented;
- abuse thresholds observable;
- partner-aware isolation tested.


---

## Source Document: `docs/growth-platform/miniapp/06-miniapp-implementation-plan.md`

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


---

## Source Document: `docs/growth-platform/miniapp/07-miniapp-definition-of-done.md`

# Mini App Definition of Done

## Product DoD

- user can open Mini App, authenticate, purchase or start trial, and obtain config without leaving Telegram;
- primary user journeys are available in both platform and partner-branded mode;
- server picker and referral flows are available.

## Technical DoD

- `/miniapp` routing is canonical and stable;
- Mini App uses dedicated API contracts for bootstrap, offers, servers, config, and payment status;
- runtime hooks cover Telegram lifecycle needs.

## Security DoD

- backend validates raw Telegram init data;
- `initDataUnsafe` is not used for trust decisions;
- referral and start payloads are signed;
- payment and config access rules are audited.

## Payment DoD

- in-Telegram payment uses Telegram Stars;
- invoice lifecycle is supported in frontend and backend;
- entitlement activates only after authoritative success;
- refund and support handling is defined.

## Analytics DoD

- Mini App funnel events are emitted and visible in dashboards;
- partner and referral attribution survive purchase;
- payment and config delivery events reconcile.

## Testing DoD

- unit, contract, integration, and E2E coverage exist for critical paths;
- route persistence and payment replay behaviors are tested;
- partner-branded runtime path is covered.

## Rollout DoD

- feature flags exist for major Mini App modules;
- rollback path exists for checkout;
- support and incident routing are documented.


---

## Source Document: `docs/growth-platform/network-intelligence/00-network-intelligence-overview.md`

# Network Intelligence Overview

## Purpose

Real-Time Network Intelligence turns CyberVPN network quality into a public product asset. It should create trust before purchase and also feed operationally useful signals into customer and partner experiences.

## Strategic Roles

### Trust and Acquisition

- prove network quality with public evidence;
- reduce generic marketing claims;
- create a stronger reason to click into Mini App or trial.

### SEO

- support search demand around speed, uptime, latency, and availability;
- create durable pages tied to real public metrics.

### Partner Widgets

- give partners a branded proof layer they can embed;
- strengthen downstream conversion from partner channels.

### Mini App Server Picker

- provide recommended server and stability signals;
- reduce guesswork in server selection.

## What Counts as Public Proof

Public proof may include:

- sanitized regional performance snapshots;
- uptime windows;
- public incident summaries;
- freshness markers;
- confidence markers for sensitive claims such as DPI score.

## What Must Not Be Public

- internal hostnames;
- raw Prometheus labels;
- capacity ceilings;
- precise network topology;
- sensitive anti-blocking implementation details.


---

## Source Document: `docs/growth-platform/network-intelligence/01-public-speed-map-product-spec.md`

# Public Speed Map Product Spec

## Product Goal

Create a public, trustworthy, and conversion-aware network proof surface.

## Core Pages

- `/[locale]/network`
- `/[locale]/status`
- `/[locale]/network/regions`
- `/[locale]/network/regions/:country`
- `/[locale]/network/dpi-resistance`
- `/[locale]/network/uptime`

## Core Blocks

- global health summary
- freshness display
- region leaderboard
- region cards
- public incident block
- uptime history
- methodology note
- CTA into Mini App

## UX Requirements

- SSR-friendly initial render;
- last updated and freshness state always visible;
- live-looking visuals must still be honest about data freshness;
- degraded and stale state must be explicit.

## Conversion Path

Primary CTA path:

- public page -> Mini App -> trial or purchase

Secondary path:

- public page -> web/storefront for users outside Telegram

## Region Cards

Each region card should show:

- public region name;
- latency;
- speed;
- uptime;
- current status;
- confidence where applicable.

## Incident Block

Must show:

- current incident severity;
- public summary;
- affected regions;
- current state;
- timestamps.

## Methodology Block

Should explain:

- what metrics are shown;
- how fresh they are;
- what is aggregated;
- what is intentionally not public.

## SEO Blocks

Include:

- static context around network quality;
- localized explanatory copy;
- internal links to region and uptime pages.


---

## Source Document: `docs/growth-platform/network-intelligence/02-public-network-snapshot-spec.md`

# Public Network Snapshot Spec

## Objective

Define the canonical sanitized data model for all public network surfaces.

## Snapshot Contract

```ts
type PublicNetworkSnapshot = {
  schemaVersion: string
  methodologyVersion: string
  version: string
  measurementWindow: {
    from: string
    to: string
  }
  generatedAt: string
  expiresAt: string
  freshnessStatus: 'fresh' | 'stale' | 'degraded'
  confidence: 'low' | 'medium' | 'high'
  global: {
    status: 'online' | 'degraded' | 'partial_outage' | 'major_outage'
    uptimePct30d: number
    uptimePct90d: number
    onlineRegions: number
    degradedRegions: number
    offlineRegions: number
    medianLatencyMs: number | null
    medianSpeedMbps: number | null
  }
  regions: Array<{
    id: string
    publicName: string
    countryCode: string
    city?: string
    status: 'online' | 'degraded' | 'offline'
    medianLatencyMs: number | null
    p95LatencyMs: number | null
    speedMbps: number | null
    uptimePct30d: number | null
    lastProbeAt: string | null
    confidence: 'low' | 'medium' | 'high'
  }>
  incidents: Array<{
    id: string
    severity: 'minor' | 'major' | 'critical'
    status: 'investigating' | 'identified' | 'monitoring' | 'resolved'
    publicTitle: string
    publicSummary: string
    affectedRegions: string[]
    startedAt: string
    resolvedAt?: string
  }>
  dpi?: {
    enabled: boolean
    lastUpdatedAt: string
  }
}
```

## Freshness Rules

- `generatedAt` is the snapshot creation time;
- `expiresAt` is the maximum freshness deadline for public rendering;
- `freshnessStatus` is required on every snapshot.

## Cache Policy

- public API can cache snapshot responses;
- cache must never hide stale state from the user;
- stale-but-valid responses may still be served if clearly marked.

## Atomic Publish Rules

Publishing a new public snapshot should follow this rule set:

1. build next snapshot in isolation;
2. validate completeness;
3. validate sanitization and absence of private labels;
4. publish atomically;
5. keep previous valid snapshot if the new one fails validation or publish;
6. expose stale or degraded state honestly if fallback snapshot is used.

## Sanitization Rules

- no raw infrastructure identifiers;
- no internal hostnames;
- no sensitive topology;
- no raw probe metadata that exposes exact anti-blocking behavior.

## Incident Representation

Incidents should be:

- human-readable;
- operationally truthful;
- region-oriented;
- security-safe.

## Confidence Model

Confidence should reflect:

- probe recency;
- sample count;
- source diversity;
- consistency of observations.

## Stale Behavior

If snapshot is stale:

- public API still returns snapshot if policy allows;
- UI shows stale or degraded state;
- live language is suppressed.


---

## Source Document: `docs/growth-platform/network-intelligence/03-network-api-contracts.md`

# Network API Contracts

## Endpoint List

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/public/network/overview` | Global public summary |
| GET | `/api/v1/public/network/regions` | Region list |
| GET | `/api/v1/public/network/regions/:id` | Region detail |
| GET | `/api/v1/public/network/leaderboard` | Ranked public regions |
| GET | `/api/v1/public/network/uptime` | Public uptime windows |
| GET | `/api/v1/public/network/incidents` | Public incident list |
| GET | `/api/v1/public/network/widget` | Widget payload or embed contract |
| GET | `/api/v1/public/network/dpi-score` | DPI score summary |
| GET | `/api/v1/public/network/seo-summary` | SEO-oriented summarized content payload |

## Common Response Requirements

- `version`
- `schemaVersion`
- `methodologyVersion`
- `measurementWindow`
- `generatedAt`
- `expiresAt`
- `freshnessStatus`
- `confidence`

## Cache Headers

Recommended default:

```text
Cache-Control: public, max-age=60, stale-while-revalidate=300
ETag: "<value>"
Last-Modified: "<http-date>"
```

## `GET /api/v1/public/network/overview`

Returns:

- global status
- regional counts
- median performance aggregates
- freshness and last generated time

## `GET /api/v1/public/network/regions`

Returns a paginated or bounded list of public regions with:

- region name
- status
- latency
- speed
- uptime
- confidence

## `GET /api/v1/public/network/incidents`

Returns current and recent public incidents with safe summaries and affected regions.

## `GET /api/v1/public/network/widget`

Returns widget configuration or payload depending on widget type. Must support rate limiting and partner-aware branding only where allowed.

## `GET /api/v1/public/network/dpi-score`

Returns only if DPI score is enabled and sufficiently trustworthy:

- enabled flag
- last updated time
- country-level public scores
- confidence
- supported protocol summaries

## Error Handling

Common error codes:

- `public_snapshot_unavailable`
- `public_snapshot_stale`
- `public_region_not_found`
- `public_dpi_not_enabled`

## Security Rules

- all responses must be sanitized before publish;
- no direct Prometheus proxy behavior;
- widget endpoints must not leak partner-private data.


---

## Source Document: `docs/growth-platform/network-intelligence/04-prometheus-aggregation-pipeline.md`

# Prometheus Aggregation Pipeline

## Goal

Convert internal monitoring signals into sanitized public snapshots without exposing Prometheus directly to public traffic.

## Data Sources

- Prometheus metrics
- internal monitoring endpoints
- node metadata
- incident records
- DPI probe results

## Pipeline

```text
Prometheus / internal monitoring / probes / DB
-> aggregation worker
-> sanitized snapshot
-> Redis/Postgres materialized store
-> public API
-> SSR/ISR/frontend
-> CDN/cache
```

## Worker Responsibilities

- query data sources on schedule;
- normalize regional and global aggregates;
- determine freshness state;
- generate public snapshot;
- publish or replace previous snapshot safely and atomically.

## Storage

Recommended:

- Redis for latest fast-read snapshot
- Postgres for snapshot history and incident traceability

## Failure Modes

- Prometheus unavailable
- partial source outage
- malformed upstream metric
- storage publish failure

## Stale Mode

If source data fails:

- retain last valid snapshot;
- mark snapshot stale or degraded;
- alert platform team;
- public UI shows stale state explicitly.

## Atomic Publish Rule

The worker must not partially overwrite the currently served public snapshot. If publish validation fails, the last known valid snapshot remains active until a newer valid snapshot is ready.

## Alerting

Alert on:

- snapshot generation failure
- snapshot publish failure
- snapshot staleness beyond threshold
- suspicious metric gaps

## Rule

No direct public Prometheus access is allowed in the final architecture.


---

## Source Document: `docs/growth-platform/network-intelligence/05-dpi-resistance-score.md`

# DPI Resistance Score

## Purpose

DPI Resistance Score should provide a careful public view of how resilient CyberVPN connectivity appears in restrictive conditions. It must not become a decorative number without method.

## Signals

Candidate signals:

- connection success rate
- median handshake latency
- session survival duration
- reconnect success
- protocol fallback success
- packet loss
- probe freshness
- sample confidence

## Confidence

Score confidence should depend on:

- number of recent probes;
- diversity of probe sources;
- consistency of success and failure;
- freshness of observations.

## Country and Protocol Support

Each country may expose:

- overall score
- confidence
- supported protocol summaries

Each protocol summary may expose:

- success rate
- median handshake latency
- last probe time

## Refresh Cadence

Recommended:

- periodic probes throughout the day;
- public score updates only after enough fresh signal exists.

## Public Presentation

Public UI should show:

- score
- confidence
- last updated
- methodology summary
- disclaimer that conditions can change quickly

## What Must Not Be Public

- sensitive anti-blocking internals;
- exact bypass techniques;
- exact probe source identities;
- internal topology.

## Limitations

- country conditions may change quickly;
- limited samples should lower confidence;
- score is directional, not a guarantee.


---

## Source Document: `docs/growth-platform/network-intelligence/06-seo-and-public-pages.md`

# SEO and Public Pages

## SEO Goal

Use truthful public network data to support discovery, trust, and conversion without making unsupported claims.

## Page Map

- `/[locale]/network`
- `/[locale]/status`
- `/[locale]/network/regions`
- `/[locale]/network/regions/:country`
- `/[locale]/network/uptime`
- `/[locale]/network/dpi-resistance`

## URL Strategy

- stable, readable, locale-aware URLs;
- country pages only for regions with acceptable public data quality;
- canonical URLs per locale.

## Metadata

Each page should include:

- descriptive title
- summary aligned to current public data
- OG image strategy
- locale tags where applicable

## Structured Data

Potential structured data:

- FAQ or explanatory content where appropriate
- breadcrumb schema
- organization/site metadata

## Internal Linking

Link between:

- network overview and status
- regions and uptime
- regions and DPI
- public pages and Mini App CTA

## Localized Pages

Roll out by translation readiness and policy confidence. Sensitive claims should be handled carefully in every locale.

## Canonical Policy

- one canonical per localized page
- avoid duplicate near-empty region pages
- noindex pages that do not yet have enough signal or content quality

## Content Clusters

- VPN speed map
- VPN uptime
- VPN latency by region
- public VPN status
- DPI-resistant VPN

## Editorial Rule

Do not publish absolute claims that outrun measurement quality.


---

## Source Document: `docs/growth-platform/network-intelligence/07-network-widget-spec.md`

# Network Widget Spec

## Purpose

Allow CyberVPN and approved partners to embed public network proof in external pages without exposing raw internal data.

## Widget Types

- iframe widget
- badge widget
- uptime badge
- speed badge
- branded network card

## Widget Requirements

- sanitized data only;
- cache-friendly responses;
- low-latency embeds;
- optional partner branding within approved limits.

## Embed Example

```html
<iframe
  src="https://cybervpn.com/widgets/network?partner=partner_slug"
  loading="lazy"
></iframe>
```

## Configuration Options

- locale
- theme variant
- region focus
- widget size
- partner identifier where allowed

## Cache and Rate Limits

- widget payload should be backed by public snapshot cache;
- partner widget traffic should be rate limited and observable;
- embed abuse should be detectable.

## Security

- no partner-private data;
- no raw infrastructure identifiers;
- signed or validated branding parameters where needed.

## Customization

Allowed:

- theme variant
- locale
- selected approved widgets

Not allowed:

- arbitrary metric injection
- unsupported branding assets
- unsafe or misleading copy overrides


---

## Source Document: `docs/growth-platform/network-intelligence/08-network-implementation-plan.md`

# Network Implementation Plan

## Milestone 1 — Snapshot Foundation

- [ ] Define `PublicNetworkSnapshot` schema
- [ ] Create snapshot repository
- [ ] Create aggregation worker skeleton
- [ ] Add freshness and expiry logic
- [ ] Add atomic publish validation and previous-valid fallback

Acceptance criteria:

- one canonical snapshot model exists and can be stored and served.

## Milestone 2 — Public API

- [ ] Create public network API namespace
- [ ] Add overview, regions, leaderboard, uptime, and incidents endpoints
- [ ] Add cache headers and ETag support
- [ ] Add sanitization validation before publish

Acceptance criteria:

- public API serves snapshot-derived data only.

## Milestone 3 — Public Pages

- [ ] Replace mock or simulated network/status blocks
- [ ] Add freshness and degraded UI states
- [ ] Add Mini App CTA bridge
- [ ] Add methodology block
- [ ] Add public incident publication workflow

Acceptance criteria:

- public pages render truthful snapshot data and show freshness state.

## Milestone 4 — Widgets and SEO

- [ ] Add widget contract
- [ ] Add region page support
- [ ] Add metadata and OG strategy
- [ ] Add internal linking plan

Acceptance criteria:

- widget and core SEO paths are usable and safe.

## Milestone 5 — DPI Expansion

- [ ] Create probe worker
- [ ] Add DPI score aggregation
- [ ] Add confidence model
- [ ] Add public DPI page and API

Acceptance criteria:

- DPI score is supported by real probes and clear confidence markers.

## Monitoring Tasks

- snapshot freshness dashboard
- publish failure alerts
- public API error rate
- widget load and rate-limit metrics

## QA Tasks

- snapshot generation tests
- sanitization tests
- stale mode UI tests
- public page rendering tests
- widget security and cache tests


---

## Source Document: `docs/growth-platform/network-intelligence/09-network-definition-of-done.md`

# Network Definition of Done

## Product DoD

- public network pages show real, sanitized network intelligence rather than decorative live-like placeholders;
- users can move from proof pages into conversion surfaces cleanly.

## Technical DoD

- public API reads from sanitized snapshots;
- direct public Prometheus access is eliminated;
- freshness and stale handling are explicit;
- snapshot publication is atomic and preserves last valid snapshot.

## Public Truth DoD

- no mock live data is shown as truth;
- incidents and uptime windows are operationally grounded;
- confidence and methodology are visible where needed.

## SEO DoD

- public pages support structured metadata, canonical rules, and meaningful content;
- region pages launch only where signal quality supports them.

## Widget DoD

- partner widgets use snapshot-derived data;
- rate limits and customization rules are enforced.

## Observability DoD

- snapshot freshness alerts exist;
- public API error and cache metrics exist;
- degraded mode is testable and visible.


---

## Source Document: `docs/growth-platform/white-label/00-white-label-overview.md`

# White-Label Overview

## Purpose

White-Label turns CyberVPN into a distribution platform. Partners should be able to launch branded customer entry points without requiring per-partner deployments or manual code changes.

## Target Partners

- Telegram-native resellers
- regional distributors
- community operators and creators
- affiliate operators graduating into branded distribution
- strategic distribution partners with stronger brand needs

## Business Model

Baseline model:

- CyberVPN remains platform-of-record and merchant-of-record;
- partner operates as branded reseller or distribution channel;
- revenue share, margin rules, and payout behavior are controlled by `PartnerCommercialPolicy`.

## Partner Journey

1. Apply
2. Pass KYB and moderation
3. Receive workspace
4. Configure brand and pricing
5. Provision branded bot and Mini App
6. Launch storefront and campaigns
7. Monitor sales and request payouts

## Self-Service Scope

Required self-service capabilities:

- application and review status
- brand setup
- pricing and margin setup within approved policy
- bot creation or binding
- Mini App preview
- storefront preview
- analytics visibility
- payout request flow

## Managed Bot Strategy

Primary path:

- Telegram Managed Bots
- shared multi-tenant runtime
- credential lifecycle controlled by the platform

Fallback path:

- partner-created bot token onboarding with encryption and validation

## Storefront Strategy

- partner storefront remains part of shared CyberVPN platform;
- branding and legal/support context become DB-driven;
- external web checkout is allowed only under approved payment policy.

## Branded Mini App Strategy

The branded Mini App is not a second product. It is the canonical Mini App runtime with:

- partner theme
- partner support links
- partner attribution
- partner commercial policy

## Non-Goals

- one codebase per partner
- one deployment per partner
- unrestricted partner copy, pricing, or legal override
- isolated entitlement or payment systems per partner


---

## Source Document: `docs/growth-platform/white-label/01-partner-user-flows.md`

# Partner User Flows

## Flow: Partner Application

1. Partner opens portal.
2. Partner creates or resumes application.
3. Partner submits business, audience, and basic compliance data.
4. Portal shows application status and next actions.

Failure cases:

- incomplete application;
- blocked business category;
- duplicate or suspicious application.

## Flow: KYB and Moderation

1. System scores application risk.
2. Manual or automated review determines required next steps.
3. Partner uploads additional materials if needed.
4. Application transitions to approved or rejected.

## Flow: Workspace Creation

1. Approved application creates `PartnerWorkspace`.
2. Commercial and branding defaults are attached.
3. Partner enters onboarding wizard.

## Flow: Brand Setup

1. Partner submits brand name, logo, colors, descriptions, and support contacts.
2. Platform validates formatting and moderation rules.
3. Moderation-approved branding becomes active or staged.

## Flow: Pricing Setup

1. Partner configures pricing within commercial policy.
2. System validates markup, discount, and campaign limits.
3. Partner sees simulator output.

## Flow: Bot Creation

Primary path:

1. Partner requests managed bot provisioning.
2. System creates provisioning job.
3. Bot identity is reserved and bound to workspace.

Fallback path:

1. Partner creates bot manually.
2. Partner submits token.
3. System validates ownership and capabilities.

## Flow: Bot Provisioning

1. Provisioning job validates workspace, brand, and policy.
2. System applies branding, commands, menu button, webhook, and Mini App binding.
3. Launch assets are generated.
4. Bot moves to active or degraded state.

## Flow: Mini App Preview

1. Partner opens preview.
2. Runtime renders branded Mini App with partner context.
3. Partner verifies theme, copy, pricing, and support surfaces.

## Flow: Storefront Preview

1. Partner previews external storefront shell.
2. Brand and legal/support surfaces are validated.
3. Launch checklist highlights missing items.

## Flow: Launch

1. Partner confirms readiness.
2. Platform checks provisioning and moderation status.
3. Bot and storefront enter public-ready state.

## Flow: Analytics

1. Partner views dashboard.
2. Portal shows visits, opens, trials, payments, conversion, revenue, and top geographies.

## Flow: Payout Request

1. Partner opens finance section.
2. Partner sees available balance and hold state.
3. Partner requests payout.
4. Platform validates policy, risk, and account completeness.

## Flow: Bot Suspension

1. Platform or partner requests suspend.
2. Bot status moves to suspended.
3. Customer-facing runtime shows appropriate messaging.

## Flow: Token Rotation

1. Rotation is requested.
2. New credential is validated and bound.
3. Old credential is revoked or retired.
4. Audit log is written.


---

## Source Document: `docs/growth-platform/white-label/02-white-label-domain-model.md`

# White-Label Domain Model

## Objective

Define the core entities required for self-service branded distribution without fragmenting the shared CyberVPN core.

## Entity Overview

| Entity | Purpose |
|---|---|
| `PartnerWorkspace` | Top-level tenant and lifecycle owner |
| `PartnerProfile` | Business identity and operating metadata |
| `PartnerBot` | Branded Telegram runtime object |
| `PartnerBotCredential` | Token and credential lifecycle object |
| `PartnerBotProvisioningJob` | Provisioning orchestration state |
| `PartnerBrandTheme` | Brand assets and display policy |
| `PartnerCommercialPolicy` | Pricing, revenue, settlement, trial rules |
| `PartnerStorefront` | Branded external acquisition shell |
| `PartnerSettlementAccount` | Payout destination and state |
| `PartnerSettlementLedgerEntry` | Append-only settlement history |
| `PartnerRiskProfile` | Risk score, KYB, abuse state |
| `PartnerCustomer` | Partner-attributed customer projection |
| `PartnerAttributedSale` | Commercial attribution record |

## `PartnerWorkspace`

Key fields:

- `id`
- `applicationId`
- `status`
- `workspaceSlug`
- `ownerUserId`
- `riskProfileId`
- `brandThemeId`
- `commercialPolicyId`
- `storefrontId`

Lifecycle:

- `draft`
- `pending_review`
- `approved`
- `active`
- `restricted`
- `suspended`
- `terminated`

## `PartnerProfile`

Key fields:

- business name
- legal entity
- contact data
- primary geographies
- audience type
- support capability notes

Mutable by:

- partner for draft and pending state
- platform for reviewed and verified state

## `PartnerBot`

Key fields:

- `id`
- `workspaceId`
- `status`
- `releaseChannel`
- `telegram.botId`
- `telegram.username`
- `telegram.managedByBotId`
- `binding.storefrontId`
- `binding.miniAppBindingId`
- `binding.commercialPolicyId`

Status values:

- `draft`
- `pending_review`
- `approved`
- `provisioning`
- `active`
- `degraded`
- `suspended`
- `revoked`
- `failed`

## `PartnerBotCredential`

Key fields:

- `id`
- `partnerBotId`
- `credentialType`
- `tokenRef`
- `status`
- `lastValidatedAt`
- `rotatedAt`

Status values:

- `missing`
- `active`
- `rotating`
- `revoked`
- `invalid`

## `PartnerBotProvisioningJob`

Key fields:

- `id`
- `partnerBotId`
- `requestedBy`
- `state`
- `attemptCount`
- `lastErrorCode`
- `lastErrorMessage`

States are defined fully in the provisioning spec.

## `PartnerBrandTheme`

Key fields:

- display name
- logo asset reference
- primary and secondary color tokens
- support links
- localized welcome copy
- legal display copy
- moderation status

## `PartnerCommercialPolicy`

Key fields:

- allowed plan IDs
- markup mode and limits
- discount rules
- trial policy reference
- payment policy by surface
- revenue share model
- payout currency and thresholds

## `PartnerStorefront`

Key fields:

- `id`
- `workspaceId`
- `host`
- `brandThemeId`
- `commercialPolicyId`
- `status`

## `PartnerSettlementAccount`

Key fields:

- payout method type
- payout address or account ref
- verification status
- hold status
- payout eligibility

## `PartnerSettlementLedgerEntry`

Key fields:

- `id`
- `workspaceId`
- `partnerId`
- `paymentId`
- `saleId`
- `entryType`
- `amount`
- `currency`
- `effectiveAt`
- `reasonCode`
- `createdAt`

Entry types:

- `sale_credit`
- `refund_reversal`
- `payout_debit`
- `hold_applied`
- `hold_released`
- `adjustment`

Rule:

- entries are append-only;
- current payout-ready balance is derived, not overwritten.

## `PartnerRiskProfile`

Key fields:

- KYB level
- risk score
- moderation flags
- blocked categories
- payout hold state
- manual review requirements

## `PartnerCustomer`

Projection entity for partner dashboards:

- user ID
- first attribution source
- first purchase date
- current subscription status
- active revenue contribution

## `PartnerAttributedSale`

Key fields:

- sale ID
- user ID
- partner ID
- bot ID
- storefront ID
- payment ID
- order ID
- gross amount
- platform amount
- partner amount
- settlement status

## Audit Requirements

Audit logs are required for:

- provisioning requests
- token rotations
- brand changes
- commercial policy changes
- payout requests and approvals
- ledger hold and release actions
- suspension and restoration actions


---

## Source Document: `docs/growth-platform/white-label/03-partner-bot-provisioning.md`

# Partner Bot Provisioning

## Goal

Provision a branded Telegram bot into the shared CyberVPN runtime without per-partner deployments.

## Strategy

Primary path:

- Managed Bots
- shared multi-tenant runtime
- platform-controlled credential lifecycle

Fallback path:

- manual bot token onboarding
- encrypted token storage
- capability validation before activation

## Managed Bots Spike Criteria

Before relying on Managed Bots as the default production path, the platform should validate:

- manager bot permissions and capabilities;
- managed token retrieval behavior;
- managed token rotation behavior;
- webhook binding behavior;
- menu button and Mini App binding behavior;
- profile, commands, descriptions, and branding update behavior;
- revocation and owner update signals;
- scale limits and rate-limit behavior.

## Provisioning State Machine

### Partner Bot Lifecycle

```text
draft
-> pending_review
-> approved
-> provisioning_requested
-> provisioning_running
-> active
-> degraded
-> suspended
-> revoked
-> failed
```

### Provisioning Job Lifecycle

```text
queued
-> validating_partner
-> reserving_bot_identity
-> applying_branding
-> configuring_commands
-> configuring_menu_button
-> binding_webhook
-> binding_miniapp
-> generating_launch_assets
-> publishing
-> completed
```

### Failure States

- `failed_validation`
- `failed_bot_creation`
- `failed_token_fetch`
- `failed_webhook_binding`
- `failed_branding`
- `rollback_required`
- `manual_intervention_required`

## Provisioning Steps

1. Validate workspace and approval state.
2. Validate brand and commercial policy completeness.
3. Reserve or bind bot identity.
4. Apply branding and descriptive fields.
5. Configure commands and menu button.
6. Bind webhook and runtime routing.
7. Bind branded Mini App entry.
8. Generate launch assets.
9. Mark bot active or degraded.

## Webhook Binding

Webhook binding must:

- identify the bot and tenant safely;
- prevent cross-tenant routing mistakes;
- expose validation and retry status.

## Menu Button and Commands

Provisioning should set:

- Mini App launch binding
- support and payment-support routes if applicable
- partner-specific or platform-approved command set

## Branding Setup

Branding is applied only from moderated or approved brand data. Unsafe or rejected branding must block provisioning completion.

## Retry and Rollback

- retry transient failures automatically;
- require manual intervention for trust or policy failures;
- rollback partial binding where a bot would otherwise appear active but broken.

## Token Rotation

Rotation must:

- validate new token or managed credential;
- switch runtime binding safely;
- retire old credential;
- preserve audit trail.

## Bot Suspension

Suspension must support:

- platform-initiated suspend;
- partner-requested suspend;
- emergency suspend with credential revoke if needed.


---

## Source Document: `docs/growth-platform/white-label/04-partner-commercial-policy.md`

# Partner Commercial Policy

## Purpose

`PartnerCommercialPolicy` defines what a partner is allowed to sell, how prices are derived, how revenue is split, and how settlement behaves.

## Pricing Model

Required controls:

- allowed base plans
- markup mode
- markup ceilings
- discount rules
- optional campaign constraints

Markup modes:

- fixed
- percentage
- custom within approval range

## Revenue Share

Supported models:

- commission
- reseller margin
- hybrid

Required outputs:

- gross sale
- platform share
- partner share
- payout-ready share
- held share

## Trial Policy

Commercial policy must define:

- whether trials are enabled;
- which trial policy is attached;
- any partner-specific restrictions or incentives;
- whether certain acquisition sources disable trial.

## Refunds

Policy must define:

- whether partner balance is adjusted on refund;
- which sale states become payout-ineligible;
- who handles support and dispute communication.

## Payouts

Required fields:

- payout currency
- minimum payout
- payout cadence
- hold rules
- required account verification
- ledger-based payout-ready balance derivation

## Settlement Periods

Recommended controls:

- configurable settlement windows;
- pending, hold, ready, paid states;
- manual and automated payout support.

## Fraud Holds

Fraud hold logic may depend on:

- risk score;
- refund spike;
- unusual conversion behavior;
- chargeback or dispute signals where relevant.

Hold and release actions must be represented in the settlement ledger, not as hidden balance mutations.

## Merchant / Platform of Record

Baseline decision:

- CyberVPN remains platform-of-record and merchant-of-record.
- Partner acts as reseller or distribution channel.

## Supported Payment Rails

By default:

- Telegram surfaces: Stars / XTR
- external web or storefront: approved non-Telegram rails according to platform policy
- internal wallet: optional for credits, bonuses, or settlement support

## Policy Boundaries

Partners may configure within policy. They do not create independent payment, entitlement, or legal systems.


---

## Source Document: `docs/growth-platform/white-label/05-white-label-api-contracts.md`

# White-Label API Contracts

## Endpoint List

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/partner/workspace` | Current workspace view |
| PATCH | `/api/v1/partner/workspace` | Workspace updates |
| GET | `/api/v1/partner/brand` | Brand theme state |
| PATCH | `/api/v1/partner/brand` | Brand updates |
| GET | `/api/v1/partner/bots` | Bot list |
| POST | `/api/v1/partner/bots` | Create draft bot |
| GET | `/api/v1/partner/bots/:id` | Bot details |
| POST | `/api/v1/partner/bots/:id/provision` | Start provisioning |
| POST | `/api/v1/partner/bots/:id/suspend` | Suspend bot |
| POST | `/api/v1/partner/bots/:id/rotate-token` | Rotate credential |
| GET | `/api/v1/partner/analytics` | Partner analytics |
| GET | `/api/v1/partner/payouts` | Payout state |
| POST | `/api/v1/partner/payouts/request` | Request payout |

## Contract Requirements

- all endpoints are tenant-authenticated;
- all bot mutations require explicit workspace ownership or admin override;
- state-mutating endpoints should use idempotency where retries are expected.

## `GET /api/v1/partner/workspace`

Returns:

- workspace status
- review status
- linked brand theme
- linked commercial policy
- linked storefront
- next required actions

## `PATCH /api/v1/partner/brand`

Allows moderated updates to:

- display name
- logo asset
- color tokens
- support profile
- selected branded copy fields

Returns moderation state and validation issues.

## `POST /api/v1/partner/bots`

Creates draft bot record.

Request example:

```json
{
  "displayName": "Example VPN",
  "defaultLocale": "en-EN"
}
```

## `POST /api/v1/partner/bots/:id/provision`

Starts provisioning job.

Response example:

```json
{
  "jobId": "uuid",
  "state": "queued"
}
```

Error codes:

- `partner_workspace_not_ready`
- `partner_brand_not_approved`
- `partner_bot_invalid_state`

## `POST /api/v1/partner/bots/:id/rotate-token`

Supports:

- managed credential rotation;
- manual token replacement in fallback mode;
- validation result in response.

## `GET /api/v1/partner/analytics`

Returns:

- visits
- Mini App opens
- trials
- payments
- revenue
- conversion
- top geographies
- top offers

## `POST /api/v1/partner/payouts/request`

Request must validate:

- verified settlement account;
- available balance;
- hold state;
- risk restrictions.


---

## Source Document: `docs/growth-platform/white-label/06-partner-portal-ux.md`

# Partner Portal UX

## UX Goal

The portal should feel like an operator console for launching and running a branded CyberVPN distribution business, not a generic settings panel.

## Core Screens

- partner dashboard
- onboarding wizard
- brand editor
- pricing and margin simulator
- bot provisioning center
- branded Mini App preview
- storefront preview
- launch checklist
- analytics dashboard
- payout dashboard

## Onboarding Wizard

Suggested steps:

1. Business profile
2. Compliance and KYB
3. Traffic and geo focus
4. Brand identity
5. Pricing and margin
6. Bot setup
7. Mini App preview
8. Storefront preview
9. Launch assets
10. Analytics and finance

Each step should support:

- draft save
- validation
- review banner
- audit visibility
- next required action

## Brand Editor

Must expose:

- name and logo
- color system
- descriptions
- support and legal display fields
- moderation feedback

## Bot Provisioning UI

Must show:

- current bot status
- provisioning job state
- failure reason if present
- retry or manual action path
- webhook and Mini App binding health

## Pricing Simulator

Must show:

- customer-facing price
- platform share
- partner share
- payout-ready estimate
- discount and margin constraints

## Mini App Preview

Preview must render tenant-aware:

- theme
- support links
- plan presentation
- checkout CTA labels

## Launch Checklist

Must clearly indicate whether the partner is blocked by:

- incomplete KYB;
- unapproved branding;
- missing payout account;
- invalid bot state;
- missing storefront requirements.

## Moderation and Error States

The portal should not hide enforcement. It should show:

- review pending banners
- brand rejected reasons
- bot degraded state
- payout hold reasons
- support escalation path


---

## Source Document: `docs/growth-platform/white-label/07-abuse-moderation-kyb.md`

# Abuse, Moderation, and KYB

## Purpose

White-Label introduces significant abuse risk. This document defines the minimum control system needed before broad public rollout.

## KYB Levels

- `Level 0`: application submitted
- `Level 1`: identity and business basics verified
- `Level 2`: operating business evidence verified
- `Level 3`: strategic or higher-risk partner with deeper review

## Partner Risk Score

Risk score can consider:

- business category
- geography
- brand similarity or impersonation signals
- traffic claims
- payout behavior
- refund behavior
- support burden

## Brand Moderation

Review for:

- trademark or impersonation risk
- misleading claims
- prohibited categories
- unsupported network promises
- unsafe or policy-violating imagery or text

## Bot Creation Limits

Controls:

- limit active bots per workspace;
- limit re-provision attempts;
- require manual review for escalated cases.

## Payout Holds

Payouts may be held for:

- incomplete verification;
- elevated risk;
- refund or fraud anomalies;
- unresolved support or compliance cases.

## Emergency Suspend

The platform must be able to:

- suspend workspace
- suspend bot
- revoke credential
- disable Mini App binding
- stop payouts

## Manual Review

Manual review is required when:

- brand impersonation is suspected;
- managed provisioning repeatedly fails for unclear reasons;
- risk score exceeds threshold;
- payout anomalies appear.

## Blocked Categories

Examples may include:

- impersonation of official institutions;
- disallowed scam or abuse-heavy verticals;
- unsupported or unsafe marketing promises;
- categories blocked by platform policy or legal review.

## Audit Trail

Must log:

- reviewer decisions;
- brand moderation outcomes;
- provisioning actions;
- token rotations;
- suspension events;
- payout holds and releases.

## Admin Tooling Requirements

- searchable review queue
- partner health view
- risk and payout hold indicators
- bot provisioning intervention tools
- emergency suspend actions


---

## Source Document: `docs/growth-platform/white-label/08-white-label-implementation-plan.md`

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


---

## Source Document: `docs/growth-platform/white-label/09-white-label-definition-of-done.md`

# White-Label Definition of Done

## Product DoD

- partner can self-service from approved application to active branded bot and branded Mini App path;
- partner has storefront preview, launch checklist, analytics, and payout visibility.

## Technical DoD

- partner branding is DB-driven;
- storefront runtime is DB-driven;
- branded Mini App uses shared canonical runtime;
- provisioning follows a state machine with retries and failure visibility.

## Security and Compliance DoD

- tenant isolation is enforced and tested;
- moderation and KYB controls are active;
- emergency suspend exists;
- audit logs exist for sensitive actions.

## Commercial DoD

- `PartnerCommercialPolicy` governs pricing and settlement;
- partner revenue attribution is preserved end-to-end;
- payout lifecycle is defined and observable;
- immutable settlement ledger and reversal behavior are in place.

## Provisioning DoD

- Managed Bots primary path is available or validated for the target release;
- manual token fallback exists;
- token rotation and suspension exist;
- admin/operator suspend and recovery paths exist.

## Analytics DoD

- partner applications, provisioning, sales, and payout events are captured;
- partner dashboards reflect actual attributed performance.

## Testing DoD

- E2E path exists for application -> bot -> payment -> entitlement -> partner attribution;
- negative tests exist for tenant leakage and provisioning failures.
