# Prometheus Aggregation Pipeline

## Goal

Convert internal monitoring signals into sanitized public snapshots without exposing Prometheus directly to public traffic.

## Data Sources

- Prometheus metrics
- internal monitoring endpoints
- node metadata
- incident records
- DPI probe results

## Pipeline

```text
Prometheus / internal monitoring / probes / DB
-> aggregation worker
-> sanitized snapshot
-> Redis/Postgres materialized store
-> public API
-> SSR/ISR/frontend
-> CDN/cache
```

## Worker Responsibilities

- query data sources on schedule;
- normalize regional and global aggregates;
- determine freshness state;
- generate public snapshot;
- publish or replace previous snapshot safely and atomically.

## Storage

Recommended:

- Redis for latest fast-read snapshot
- Postgres for snapshot history and incident traceability

## Failure Modes

- Prometheus unavailable
- partial source outage
- malformed upstream metric
- storage publish failure

## Stale Mode

If source data fails:

- retain last valid snapshot;
- mark snapshot stale or degraded;
- alert platform team;
- public UI shows stale state explicitly.

## Atomic Publish Rule

The worker must not partially overwrite the currently served public snapshot. If publish validation fails, the last known valid snapshot remains active until a newer valid snapshot is ready.

## Alerting

Alert on:

- snapshot generation failure
- snapshot publish failure
- snapshot staleness beyond threshold
- suspicious metric gaps

## Rule

No direct public Prometheus access is allowed in the final architecture.
