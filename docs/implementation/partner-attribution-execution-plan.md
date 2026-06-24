# Partner Attribution Execution Plan

Task: `PARTNER-ATTRIBUTION-HARDENING`

Status: Historical planning artifact. The partial/deferred state in this file
was superseded by the final delivery evidence in
`docs/implementation/partner-attribution-completion-report.md`,
`docs/implementation/partner-attribution-test-matrix.md`,
`docs/implementation/partner-attribution-migration-preflight.md`, and
`.codex/current-task.json`.

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

## Historical Initial Plan Backlog

The items below were deferred when this execution plan was written. They are no
longer the current task status; final implementation and validation evidence is
recorded in the completion report, test matrix, migration preflight, and task
contract.

- Redis-backed public route rate limiting was not yet implemented at that
  checkpoint.
- Persistent partner-code link slugs and compatibility sunset controls were not
  yet introduced at that checkpoint.
- Eligibility policy was not yet centralized across capture, claim, checkout,
  resolver, and admin explainability at that checkpoint.
- Quote/order server-side claim safety net was not yet implemented at that
  checkpoint.
- Immutable commission snapshots, Decimal earning calculation, durable outbox
  worker, DLQ, and no-double-payout constraints were not yet implemented at
  that checkpoint.
- OpenAPI/generated clients had not yet been synchronized with consumer builds
  at that checkpoint.
- PostgreSQL migration upgrade/downgrade/re-upgrade validation had not yet been
  executed at that checkpoint.
- Full backend, frontend, admin, partner, worker, security, and E2E release
  gates had not yet been run at that checkpoint.
