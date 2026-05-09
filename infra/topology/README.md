# Stage 1 Topology Contracts

This directory contains local topology/environment contracts for Stage 1.

The topology is a no-secret implementation artifact for the owner-approved `Simple Controlled Hybrid Container Topology`. It selects placement and boundaries for S1, but it does not claim that staging or production infrastructure is already deployed.

## Files

| File | Purpose |
|---|---|
| `stage1-production-topology.json` | Machine-readable S1 topology contract |
| `stage1-staging-environment.json` | Machine-readable S1 staging environment contract |
| `stage1-production-environment.json` | Machine-readable S1 production environment deployability contract |
| `../ingress/stage1-protected-ingress-contract.json` | Machine-readable S1 protected ingress contract |
| `../../scripts/validate_s1_production_topology.py` | Static topology validator |
| `../../scripts/validate_s1_staging_environment.py` | Static staging environment validator |
| `../../scripts/validate_s1_production_environment.py` | Static production environment validator |
| `../../scripts/validate_s1_protected_ingress.py` | Static protected ingress validator |
| `../tests/test_stage1_production_topology.py` | Pytest coverage for required topology invariants |
| `../tests/test_stage1_staging_environment.py` | Pytest coverage for required staging invariants |
| `../tests/test_stage1_production_environment.py` | Pytest coverage for required production environment invariants |
| `../tests/test_stage1_protected_ingress.py` | Pytest coverage for protected ingress invariants |

## S1 Topology Summary

Production-critical services stay outside the home lab:

- public site/customer cabinet;
- backend API;
- Telegram production webhook receiver;
- payment webhook receiver;
- managed PostgreSQL 17.x;
- private Valkey/Redis;
- dedicated production Remnawave control-plane;
- admin production;
- DNS/TLS/edge;
- VPN exit nodes;
- primary observability/alerting;
- only copy of backups.

Containers are acceptable for the application layer: frontend, admin, backend API, Telegram Bot and worker/scheduler. Data/state authority is not container-local: PostgreSQL, Valkey/Redis and backup storage must be external/private and evidenced before go-live.

## Not Yet Known From The Repository

The repository does not currently prove:

- which cloud/hosting account will host production;
- exact regions;
- exact managed PostgreSQL/Valkey providers;
- origin IPs;
- private network CIDRs;
- Cloudflare/equivalent zone IDs;
- production image digests;
- production deploy user/SSH policy.

Those items are intentionally carried into `S1-INFRA-002`...`S1-INFRA-005`.

`S1-INFRA-003` adds the production deployability contract. It does not create or claim live production. It defines the required production services, environment separation, public ingress, preflight checks, kill switches and external evidence needed before controlled public beta traffic can be sent to production.

`S1-INFRA-005` adds the protected ingress contract. It does not deploy edge/proxy/firewall rules. It defines the required public entrypoints, admin access gate, private-service boundary, blocked public paths and live evidence required before go-live.
