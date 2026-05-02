# ADR-003: Public Network Snapshot Instead of Direct Prometheus

## Status

Accepted

## Context

CyberVPN wants to expose public network intelligence. Prometheus is an internal operational system and is not appropriate as a direct public request path.

## Decision

Public Network APIs and pages read only from sanitized, materialized network snapshots.

## Consequences

- an aggregation worker becomes mandatory;
- freshness and stale handling become explicit product concerns;
- public data can be cached safely and served consistently.

## Alternatives Considered

- Direct public querying of Prometheus
- Frontend direct polling of internal monitoring endpoints

These were rejected because they create security, performance, and truthfulness risks.
