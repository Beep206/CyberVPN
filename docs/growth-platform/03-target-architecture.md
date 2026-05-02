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
