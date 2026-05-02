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
