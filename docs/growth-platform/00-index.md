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
