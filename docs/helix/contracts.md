# Helix Contracts

## Purpose

This document describes the shared contract package used by the adapter, node daemon, backend, and desktop runtime.

## Contract Inventory

### 1. `manifest`

Used by:

- adapter
- backend
- desktop client

Purpose:

- resolve an entitled desktop user to a signed, versioned runtime manifest tied to a rollout

Key properties:

- `manifest_id`
- `rollout_id`
- `protocol_version`
- `transport_profile`
- `compatibility_window`
- capability requirements
- fallback policy
- signature metadata

### 2. `node-assignment`

Used by:

- adapter
- node daemon

Purpose:

- deliver a versioned node-targeted runtime assignment that can be applied and rolled back safely

Key properties:

- `assignment_id`
- `rollout_id`
- `bundle_version`
- `transport_profile`
- minimum daemon version
- desired state
- last-known-good reference

### 3. `node-heartbeat`

Used by:

- node daemon
- adapter
- monitoring pipeline

Purpose:

- report daemon status, active transport profile, bundle state, local health, and rollback counters

### 4. `client-capabilities`

Used by:

- desktop client
- backend
- adapter

Purpose:

- declare which protocol versions, fallback cores, and transport profile windows the desktop build supports

Key properties:

- supported protocol versions
- supported transport profiles
- profile compatibility window
- fallback core support

### 5. `transport-profile`

Used by:

- adapter
- backend
- desktop client
- node daemon

Purpose:

- define versioned protocol profiles that can be selected, promoted, deprecated, or revoked without rewriting the whole stack

### 6. `benchmark-report`

Used by:

- benchmark harness
- adapter and release evidence set
- release and promotion review

Purpose:

- prove candidate transport competitiveness against `VLESS` and `XHTTP`

### 7. `rollout-state`

Used by:

- adapter
- backend
- dashboards and admin visibility

Purpose:

- summarize active rollout posture, batch progress, node health counts, and desktop outcome metrics

## Contract Rules

- Every contract is versioned.
- Contracts are strict: unknown fields are rejected unless explicitly allowed.
- Rollout-linked contracts must include `rollout_id`.
- Security-sensitive contracts must include signature or integrity metadata where applicable.
- Examples in the shared package must remain valid and executable against the schemas.
- Contracts now expose profile-driven adaptability semantics so future transport changes can often land as policy or profile rotation rather than cross-repo rewrites.

## Agility Semantics Implemented For The Next Runtime Wave

The shared contracts now reserve or expose explicit semantics for:

- `transport_profile_id`
- `transport_profile_version`
- `policy_version`
- compatibility windows
- profile-family negotiation

These fields are required so the adapter can issue only compatible manifests and assignments while keeping multiple transport generations alive during controlled migration windows.

## Validation Rules

- `packages/helix-contract/scripts/validate-contracts.mjs` is the required validation entrypoint.
- Validation must fail fast on any schema or fixture drift.
- Phase 2 code work must not start until validation is green.
