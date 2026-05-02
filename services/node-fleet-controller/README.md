# CyberVPN Node Fleet Controller

`Node Fleet Controller` is the future control-plane service for external VPN and edge
fleet lifecycle.

This repository slice currently covers the `P3.1` through `P3.5` foundation packets:

- FastAPI API surface for durable request creation and inspection
- SQLAlchemy-backed durable request, operation-run, and audit store
- workflow planning and reconciliation preview layer
- NATS adapter for canonical `node.command.*` publication
- Sentry-ready FastAPI runtime contract with protected observability smoke endpoint
- external node baseline profile, observed-state ingestion, synthetic verification, and traffic-eligibility evaluation
- typed operator command surface for `node-add`, `node-replace`, `node-drain`, `node-quarantine`, and node-pool capacity adjustments
- durable failover policy bundle with budget, rate-limit, cooldown, confidence, and approval guardrails
- typed `node-failover` operator surface that can accept, block, or park requests in `awaiting_approval`

It is intentionally **not** a live-complete controller yet. Real OpenTofu execution,
OpenBao bootstrap delivery, node enrollment, runtime adapters, and live NATS evidence are
carried forward into later `P3` packets.

## Layout

```text
src/
  api/              FastAPI routes and schemas
  application/      request submission, baseline, operator commands, reconciliation, workflow, audit services
  domain/           frozen domain enums, entities, and exceptions
  infra/            database and NATS adapters
  config.py         service settings
  main.py           FastAPI entry point
tests/
```

## Local Validation

```bash
cd services/node-fleet-controller
python -m unittest discover -s tests -p 'test_*.py'
python -m py_compile $(find src -name '*.py' -print)
```

## Sentry contract

The controller now supports:

- `SENTRY_DSN`
- `SENTRY_RELEASE`
- canonical `ENVIRONMENT`
- protected runtime probe at `/api/v1/observability/sentry-contract` guarded by `FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET`
