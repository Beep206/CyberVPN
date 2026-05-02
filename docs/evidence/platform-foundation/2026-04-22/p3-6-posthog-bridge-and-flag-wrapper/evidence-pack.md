# CyberVPN Platform Foundation P3.6 PostHog Bridge And Flag Wrapper Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P3.6`  
**Phase:** `P3`  
**Primary owners:** `growth-platform`  
**Supporting owners:** `backend-platform`, `partner-platform`, `transport-backend`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [platform-foundation-posthog-bridge-and-flag-wrapper-spec.md](../../../../api/platform-foundation-posthog-bridge-and-flag-wrapper-spec.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.6` carries `EX-035` as the formal reason later work may continue while live
  `PostHog` authoritative capture and identified flag-evaluation proof are still absent.

---

## 2. Result Snapshot

Current `P3.6` result:

- the backend now contains an authoritative `PostHog` bridge mapper for:
  - `order.finalized -> checkout_payment_captured`
  - `invite.redeemed -> partner_user_activated`
- the partner app now contains a governed internal product-intelligence surface:
  - typed product-event contracts and allowlisted properties;
  - same-origin `/api/analytics/product-events` ingestion;
  - server-side `posthog-node` helper;
  - typed product feature-flag wrapper and bootstrap provider;
  - dashboard reporter for the first governed UX event path;
- the first governed product-flag contracts are now frozen behind deterministic default-off
  fallback.

This packet is **not yet claimed complete** because:

- there is no live `PostHog` host or token smoke in the current workspace;
- there is no live authoritative outbox or NATS consumer writing into `PostHog`;
- there is no live identified server-side flag evaluation proof for dashboard requests;
- there is no live governed frontend capture evidence from a deployed partner runtime.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 3.1 Partner Route, Contract, Server, And Provider Tests

```bash
cd partner
npx vitest run \
  src/app/api/analytics/product-events/route.test.ts \
  src/lib/product-intelligence/__tests__/contracts.test.ts \
  src/lib/product-intelligence/__tests__/server.test.ts \
  src/app/providers/__tests__/product-intelligence-provider.test.tsx
```

Result:

- `Test Files  4 passed (4)`
- `Tests  11 passed (11)`

### 3.2 Partner Targeted Lint

```bash
cd partner
npx eslint \
  src/lib/product-intelligence/contracts.ts \
  src/lib/product-intelligence/server.ts \
  src/lib/product-intelligence/client.ts \
  src/app/providers/product-intelligence-provider.tsx \
  src/shared/ui/atoms/product-analytics-reporter.tsx \
  src/app/api/analytics/product-events/route.ts \
  src/app/api/analytics/product-events/route.test.ts \
  src/lib/product-intelligence/__tests__/contracts.test.ts \
  src/lib/product-intelligence/__tests__/server.test.ts \
  src/app/providers/__tests__/product-intelligence-provider.test.tsx \
  'src/app/[locale]/(dashboard)/layout.tsx'
```

Result:

- targeted eslint completed successfully with no remaining diagnostics

### 3.3 Backend Bridge Unit Tests

```bash
cd backend
.venv/bin/python -m pytest --no-cov tests/unit/application/services/test_posthog_bridge.py
```

Result:

- `4 passed in 0.11s`

### 3.4 Backend Syntax Check

```bash
cd backend
.venv/bin/python -m py_compile src/application/services/posthog_bridge.py
```

Result:

- compilation completed successfully

### 3.5 Typecheck Advisory

Advisory command executed:

```bash
cd partner
npx tsc --noEmit
```

Observed result:

- full `partner` typecheck is currently blocked by a pre-existing repo-wide TypeScript
  backlog outside the `P3.6` files;
- this advisory does not invalidate the targeted `P3.6` repository slice because the new
  packet-specific tests and targeted lint completed successfully.

### 3.6 Local Foundation Coverage

Observed validated baseline:

- unsupported authoritative source events are ignored rather than loosely mapped;
- the internal product-event route rejects foreign origin traffic and invalid payloads;
- only governed event names and allowlisted properties survive sanitation;
- the product-intelligence provider exposes deterministic bootstrap state for
  `server_evaluated`, `fallback`, and `disabled` modes;
- the dashboard runtime now integrates the product-intelligence provider and first governed
  event reporter without claiming live identified evaluation.

---

## 4. Remaining Live Closure Requirements

`P3.6` can only move from "repo slice complete" to "packet complete" when:

1. a deployed partner runtime proves same-origin governed product-event capture into a live
   `PostHog` project;
2. at least one authoritative server-side commercial event is delivered into live
   `PostHog` through the approved bridge path;
3. identified server-side product-flag evaluation is proven for at least one real partner
   dashboard request;
4. at least one governed frontend UX event and one authoritative commercial event are
   visible in live `PostHog` with the expected allowlisted properties only;
5. `EX-035` is removed from the exceptions register.
