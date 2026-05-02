# Public Network Snapshot Spec

## Objective

Define the canonical sanitized data model for all public network surfaces.

## Snapshot Contract

```ts
type PublicNetworkSnapshot = {
  schemaVersion: string
  methodologyVersion: string
  version: string
  measurementWindow: {
    from: string
    to: string
  }
  generatedAt: string
  expiresAt: string
  freshnessStatus: 'fresh' | 'stale' | 'degraded'
  confidence: 'low' | 'medium' | 'high'
  global: {
    status: 'online' | 'degraded' | 'partial_outage' | 'major_outage'
    uptimePct30d: number
    uptimePct90d: number
    onlineRegions: number
    degradedRegions: number
    offlineRegions: number
    medianLatencyMs: number | null
    medianSpeedMbps: number | null
  }
  regions: Array<{
    id: string
    publicName: string
    countryCode: string
    city?: string
    status: 'online' | 'degraded' | 'offline'
    medianLatencyMs: number | null
    p95LatencyMs: number | null
    speedMbps: number | null
    uptimePct30d: number | null
    lastProbeAt: string | null
    confidence: 'low' | 'medium' | 'high'
  }>
  incidents: Array<{
    id: string
    severity: 'minor' | 'major' | 'critical'
    status: 'investigating' | 'identified' | 'monitoring' | 'resolved'
    publicTitle: string
    publicSummary: string
    affectedRegions: string[]
    startedAt: string
    resolvedAt?: string
  }>
  dpi?: {
    enabled: boolean
    lastUpdatedAt: string
  }
}
```

## Freshness Rules

- `generatedAt` is the snapshot creation time;
- `expiresAt` is the maximum freshness deadline for public rendering;
- `freshnessStatus` is required on every snapshot.

## Cache Policy

- public API can cache snapshot responses;
- cache must never hide stale state from the user;
- stale-but-valid responses may still be served if clearly marked.

## Atomic Publish Rules

Publishing a new public snapshot should follow this rule set:

1. build next snapshot in isolation;
2. validate completeness;
3. validate sanitization and absence of private labels;
4. publish atomically;
5. keep previous valid snapshot if the new one fails validation or publish;
6. expose stale or degraded state honestly if fallback snapshot is used.

## Sanitization Rules

- no raw infrastructure identifiers;
- no internal hostnames;
- no sensitive topology;
- no raw probe metadata that exposes exact anti-blocking behavior.

## Incident Representation

Incidents should be:

- human-readable;
- operationally truthful;
- region-oriented;
- security-safe.

## Confidence Model

Confidence should reflect:

- probe recency;
- sample count;
- source diversity;
- consistency of observations.

## Stale Behavior

If snapshot is stale:

- public API still returns snapshot if policy allows;
- UI shows stale or degraded state;
- live language is suppressed.
