# ADR-005: CyberVPN as Platform of Record

## Status

Accepted

## Context

White-Label requires a clear baseline for commercial responsibility, settlement logic, refunds, and support. Early ambiguity would complicate legal, payment, and partner operations.

## Decision

CyberVPN remains platform-of-record and merchant-of-record in the baseline White-Label model. Partners act as branded resellers or distribution channels.

## Consequences

- payment and entitlement logic stay centralized;
- partner payouts are derived from shared settlement accounting;
- support and refund flows remain more controllable.

## Alternatives Considered

- Full merchant independence per partner from initial launch
- Mixed unmanaged model with partner-defined payment ownership

These were rejected for initial rollout because they increase risk, legal complexity, and operational fragmentation.
