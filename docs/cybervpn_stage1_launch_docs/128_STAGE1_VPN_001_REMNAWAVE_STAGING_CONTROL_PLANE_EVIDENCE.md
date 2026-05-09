# 128_STAGE1_VPN_001_REMNAWAVE_STAGING_CONTROL_PLANE_EVIDENCE

Backlog ID: `S1-VPN-001`  
Status: local control-plane proof complete; real external staging Remnawave still required  
Date: 2026-05-09  
Scope: Stage 1 Remnawave staging/control-plane readiness for Controlled Public Beta

## Purpose

This document records the no-cost/local evidence collected for `S1-VPN-001`.

The real `S1-VPN-001` acceptance target is an external staging Remnawave control-plane that is reachable by the staging backend only, uses separate staging data/secrets and can support later profile/provisioning smoke. That external staging target is not available in this workspace yet, so this evidence is intentionally limited to local control-plane behavior.

## Decision

For S1, Remnawave staging must be proven in two layers:

| Layer | Status | Meaning |
|---|---|---|
| Local Docker control-plane | Completed in this evidence | We can start and smoke the Remnawave control-plane, PostgreSQL, Valkey and local TLS/proxy path without paying for servers |
| External staging Remnawave | Still open / go-live blocker | A separate staging instance with private API boundary, staging secrets, staging nodes and redacted smoke evidence is still required before first rollout |

This document does not replace `S1-VPN-002` production Remnawave or `S1-VPN-004` trial provisioning evidence.

## Local Runtime Used

Started services:

```text
docker compose -f infra/docker-compose.yml up -d remnawave-db remnawave-redis
docker compose -f infra/docker-compose.yml --profile proxy up -d remnawave caddy
```

Readiness result:

```text
remnawave-db: healthy, bound to 127.0.0.1:6767
remnawave-redis: healthy, bound to 127.0.0.1:6379
remnawave: healthy, app port bound to 127.0.0.1:3005, metrics bound to 127.0.0.1:3001
caddy: healthy, local smoke proxy bound to 80/443
```

Network boundary observed:

```text
remnawave: cybervpn-backend cybervpn-data
remnawave-db: cybervpn-data
remnawave-redis: cybervpn-data
caddy: cybervpn-backend cybervpn-frontend
```

This is acceptable for local smoke. For real staging, the public edge/proxy must expose only approved public routes, while Remnawave API access remains private/internal to the staging backend and authorized ops path.

## Local Smoke Results

Secrets were not printed. The working local Remnawave API token was read from local environment files into a shell variable only.

| Check | Result |
|---|---|
| Remnawave metrics health | PASS: `{"status":"ok","database":null,"redis":null}` |
| Local TLS/proxy panel route | PASS: `https://panel.localhost/` returned HTTP `200` |
| Unauthenticated nodes API | PASS: `https://panel.localhost/api/nodes` returned HTTP `401` |
| Authenticated nodes API | PASS: `/api/nodes` returned a response array |
| Node inventory shape | PASS: `response_type=array` |
| Connected node count | `0` in this run |
| Container cleanup | PASS: `caddy`, `remnawave`, `remnawave-db` and `remnawave-redis` stopped after the batch |

Observed authenticated node summary:

```text
response_count=1
response_type=array
connected_count=0
```

The one node record is a stale local smoke record from earlier local node testing. It references `remnanode-local`, which was not running in this batch. Remnawave logs therefore showed `getaddrinfo ENOTFOUND remnanode-local` warnings. This does not fail the local control-plane smoke, but it explicitly means this document is not connected-node evidence.

## What This Closes

| Item | Status |
|---|---|
| Local Remnawave control-plane startup | Closed locally |
| Local PostgreSQL/Valkey dependencies | Closed locally |
| Local reverse proxy/TLS path | Closed locally |
| API requires authorization | Closed locally |
| `/api/nodes` response shape | Closed locally |

## What Remains Open

| Gap | Required evidence |
|---|---|
| External staging Remnawave | Real staging instance, separate from production and local dev |
| Private/internal API boundary | Network/firewall/ingress proof that only staging backend and approved ops path can reach Remnawave API |
| Staging secrets | Secret-store evidence for staging Remnawave token, node secrets and backend Remnawave settings |
| Connected staging node | At least one staging node connected with node/firewall evidence |
| S1 profiles/inbounds | `vless-reality-raw` and `vless-reality-xhttp` profiles/inbounds configured and evidenced |
| Trial provisioning | `S1-VPN-004` must prove trial -> VPN ready through staging Remnawave |
| Paid provisioning | `S1-VPN-005` must prove payment -> VPN ready through staging Remnawave |
| Backup/export/rebuild | Remnawave backup/export/rebuild strategy and restore/rebuild evidence |
| Monitoring/alerts | Remnawave health, node connectivity and provisioning alerts with live delivery proof |

## Acceptance

`S1-VPN-001` is accepted locally only as control-plane smoke evidence.

Go-live remains blocked until external staging Remnawave evidence is captured with real network boundary, separate staging secrets, connected node and profile/provisioning smoke.

Next ID after this ordered batch: `S1-VPN-004` - trial provisioning.
