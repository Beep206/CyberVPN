# Node Fleet Controller

Status: implemented
Owner: platform
Last updated: 2026-04-24
Scope: `services/node-fleet-controller/`
Depends on: `../05-environment-and-release-contract.md`, `../08-tags-context-correlation-and-fingerprinting-contract.md`
Related paths: `services/node-fleet-controller/src/main.py`, `services/node-fleet-controller/src/observability.py`, `services/node-fleet-controller/src/api/router.py`, `services/node-fleet-controller/README.md`

## Current state

- Controller remains a pre-production control-plane foundation, but Sentry baseline is now implemented and verified.
- Runtime contract is exposed through a protected probe at `/api/v1/observability/sentry-contract`.
- Workflow planning and reconcile loops now emit explicit Sentry spans.

## Target

- add Sentry as a separate project before production lifecycle ownership expands
- keep request traces and workflow-level spans
- tag by workflow stage, operation type, correlation id and node id

## Pre-production policy

- rollout starts in non-production only
- paging on panic or workflow failure should wait until baseline event quality is proven

## Implementation checklist

- add SDK init with environment and release contract
- instrument workflow engine spans
- add non-prod smoke path
- review before moving into broader production scope

## Implemented baseline

- `sentry-sdk[fastapi]` is initialized in `src/observability.py` with explicit `ENVIRONMENT` and `SENTRY_RELEASE`
- request scrubbing disables default PII, strips sensitive headers and drops health/probe transactions from tracing noise
- protected runtime probe requires `FLEET_CONTROLLER_OBSERVABILITY_INTERNAL_SECRET`
- workflow spans cover `workflow.plan`, `controller.reconcile.preview` and `controller.reconcile.run_once`
- `.env.example` and README now document DSN, release and probe-secret requirements
- CI validates the contract, runs targeted pytest, and boots `uvicorn` for HTTP smoke

## Remaining carryover

- production-grade alert routing is still open
- correlation contract with Loki/Tempo/NATS audit flows is not finalized
- controller is still treated as non-production-first until control-plane ownership hardens
