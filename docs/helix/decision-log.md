# Helix Decision Log

## Purpose

This log freezes blocking architecture decisions for the first implementation wave. If one of these decisions changes, related architecture and execution docs must be updated in the same change set.

## Decision 1: Adapter Persistence Model

- Decision: use the existing PostgreSQL deployment with a dedicated `helix` schema
- Reason: fastest operational path while preserving service-owned state boundaries
- Alternatives considered: separate database in phase one
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 2: Desktop Runtime Packaging

- Decision: ship the private runtime as a bundled, signed sidecar
- Reason: deterministic versioning, controlled compatibility, and explicit signature verification path
- Alternatives considered: embedded Rust module, provisioned runtime only
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 3: Manifest Delivery Model

- Decision: hybrid delivery using version checks or long-poll style refresh plus rapid invalidate or revoke
- Reason: balances control-plane simplicity with fast emergency response
- Alternatives considered: polling only, push only
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 4: Rollout Channel Topology

- Decision: `lab`, `canary`, and `stable` channels exist from the start
- Reason: rollout quality and blast-radius control require explicit promotion states
- Alternatives considered: single internal channel
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 5: Node Grouping

- Decision: manage `lab`, `prod-like`, and `regional` node groups explicitly
- Reason: allows benchmark discipline and safer promotion sequencing
- Alternatives considered: flat node inventory without rollout grouping
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `ops`, `sre`

## Decision 6: Client Scope

- Decision: desktop only in phase one
- Reason: the desktop client is the safest proving ground for runtime supervision, fallback, telemetry, and fast iteration
- Alternatives considered: simultaneous mobile rollout
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 7: Remnawave Authority Model

- Decision: `Remnawave` remains the source of truth for users, subscriptions, plans, billing entitlements, and node inventory
- Reason: preserves current platform integrity and avoids a deep fork
- Alternatives considered: transport-specific mutation inside Remnawave
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 8: Protocol Adaptation Model

- Decision: Helix evolution must be profile-driven and policy-driven before it becomes binary-driven
- Reason: fast response to blocking pressure requires controlled profile rotation, compatibility filtering, and revoke paths without a long multi-client rewrite cycle
- Alternatives considered: hard-coded single-behavior transport with binary-only updates
- Status: approved for phase one
- Decision date: `2026-03-31`
- Required approvers: `admin`, `sre`

## Decision 9: Remnawave Node Plugins Boundary

- Decision: do not embed Helix control-plane or runtime ownership into Remnawave `Node Plugins`
- Reason: keeps Helix loosely coupled, preserves Remnawave upgradeability, and limits plugins to optional node-local helpers
- Alternatives considered: packaging Helix as a Remnawave addon or plugin module
- Status: approved for phase one
- Decision date: `2026-04-12`
- Required approvers: `admin`, `sre`

## Open Operational Mapping

The implementation wave still requires mapping the role-based approvals above to named human owners before formal phase closure.
