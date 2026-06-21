# Partner Attribution Execution Plan

Task: `PARTNER-ATTRIBUTION-HARDENING`

Status: Partial. The following plan reflects the staged implementation path derived from the audit and acceptance criteria.

## Phase 1: Public Capture Boundary

- Harden the customer `/p/[publicToken]` route without changing visual design.
- Strip client-supplied realm and forwarding headers.
- Send server-controlled forwarding metadata and deterministic idempotency metadata.
- Restrict public capture destinations to server-resolved keys.
- Validate unknown production hosts with an explicit failure response.

## Phase 2: Backend Capture Idempotency

- Resolve public capture through a dedicated customer realm dependency.
- Persist only hashed browser and idempotency identifiers.
- Reuse an active pending session for reloads instead of creating duplicate sessions and touchpoints.
- Preserve replay detection after transfer-token consumption.

## Phase 3: Database Guardrails

- Add migration columns for capture idempotency and consumed transfer-token state.
- Add partial uniqueness constraints for touchpoint idempotency/source event and active binding ownership.
- Include preflight checks for PostgreSQL duplicate data that would prevent safe constraint creation.

## Phase 4: Regression Tests

- Add backend route/dependency/use-case tests for trusted host resolution, idempotent capture, transfer replay behavior, resolver precedence, and partner CORS.
- Add frontend route tests for cookie creation, forwarding-header stripping, destination sanitization, redirect fallback, and unknown production hosts.

## Deferred Required Phases

- Implement Redis-backed public route rate limiting.
- Introduce persistent partner-code link slugs and compatibility sunset controls.
- Centralize eligibility policy across capture, claim, checkout, resolver, and admin explainability.
- Implement quote/order server-side claim safety net.
- Implement immutable commission snapshots, Decimal earning calculation, durable outbox worker, DLQ, and no-double-payout constraints.
- Synchronize OpenAPI/generated clients and run consumer builds.
- Execute PostgreSQL migration upgrade/downgrade/re-upgrade validation.
- Run full backend, frontend, admin, partner, worker, security, and E2E release gates.
