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
