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
