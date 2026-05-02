# DPI Resistance Score

## Purpose

DPI Resistance Score should provide a careful public view of how resilient CyberVPN connectivity appears in restrictive conditions. It must not become a decorative number without method.

## Signals

Candidate signals:

- connection success rate
- median handshake latency
- session survival duration
- reconnect success
- protocol fallback success
- packet loss
- probe freshness
- sample confidence

## Confidence

Score confidence should depend on:

- number of recent probes;
- diversity of probe sources;
- consistency of success and failure;
- freshness of observations.

## Country and Protocol Support

Each country may expose:

- overall score
- confidence
- supported protocol summaries

Each protocol summary may expose:

- success rate
- median handshake latency
- last probe time

## Refresh Cadence

Recommended:

- periodic probes throughout the day;
- public score updates only after enough fresh signal exists.

## Public Presentation

Public UI should show:

- score
- confidence
- last updated
- methodology summary
- disclaimer that conditions can change quickly

## What Must Not Be Public

- sensitive anti-blocking internals;
- exact bypass techniques;
- exact probe source identities;
- internal topology.

## Limitations

- country conditions may change quickly;
- limited samples should lower confidence;
- score is directional, not a guarantee.
