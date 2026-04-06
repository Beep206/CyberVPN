# Helix SLO and SLA Map

## Purpose

This file maps the execution-document thresholds to owners and escalation paths.

## Owners

- `admin`: product quality bar and promotion approval
- `ops`: rollout hygiene, node readiness, and day-to-day operational visibility
- `sre`: reliability, incident response, secret custody, and rollback authority

## Phase Targets

| Phase | Key SLO | SLA / Escalation | Owner |
|---|---|---|---|
| `0` | 100% mandatory artifacts exist | blocking decision older than 24h escalates to `admin + sre` | `admin`, `sre` |
| `1` | 100% schemas versioned and examples valid | validation failure fixed same business day | `admin`, `sre` |
| `2` | health endpoints available, ready <= 15s | crash-loop fixed within 4h | `sre` |
| `3` | manifest resolve `p95 <= 200ms`, revoke <= 60s, profile rotation remains config-first | signing, revoke, or profile compatibility defect is `P0` | `sre` |
| `4` | rollback recovery `p95 <= 90s` | any failed rollback blocks next wave | `sre` |
| `5` | unauthorized admin access rate = 0 | auth boundary defect is `P0` | `sre` |
| `6` | critical alerts delivered <= 120s | missing rollback or heartbeat alert blocks canary | `ops`, `sre` |
| `7` | desktop fallback restore `p95 <= 20s` | broken fallback blocks canary | `sre` |
| `8` | audit job success >= 99% | degraded audit pipeline fixed within 4h | `ops`, `sre` |
| `9` | canary rollback to safe state <= 5m | severe breach rollback decision <= 30m | `admin`, `sre` |
| `10` | rollback drill pass = 100% | unresolved critical threat gap blocks stable | `admin`, `sre` |

## Metric Ownership

| Metric Family | Primary Owner | Secondary Owner |
|---|---|---|
| Benchmark pass/fail | `admin` | `sre` |
| Manifest latency and revoke | `sre` | `ops` |
| Profile compatibility and adaptation speed | `sre` | `admin` |
| Node heartbeat freshness | `ops` | `sre` |
| Rollback success | `sre` | `ops` |
| Desktop fallback rate | `sre` | `admin` |
| Channel promotion decisions | `admin` | `sre` |

## Escalation Rules

- Any `P0` security, signing, revoke, or rollback defect escalates immediately to `sre`.
- Any promotion dispute escalates to `admin + sre`.
- Any benchmark failure that contradicts release intent blocks rollout until `admin` signs off on a revised plan.
