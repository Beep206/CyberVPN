# Backend API

Status: draft
Owner: core
Last updated: 2026-04-24
Scope: `backend/`
Depends on: `../05-environment-and-release-contract.md`, `../07-privacy-pii-scrubbing-and-replay-policy.md`
Related paths: `backend/src/main.py`, `backend/src/presentation/middleware/request_id.py`, `backend/src/presentation/exception_handlers.py`, `backend/.env.example`

## Current state

- Sentry SDK is already integrated in startup.
- `request_id` is already present and propagated.
- Observability-related tests already exist.
- `SENTRY_DSN` is now documented in `.env.example`.
- `SENTRY_RELEASE` is now wired through settings and Sentry init.

## Target

- add canonical release input
- keep `request_id` and `trace_id` in Sentry context
- classify expected domain exceptions vs incident-grade failures

## Backend-specific considerations

- auth, payment, admin and webhook endpoints require strict scrub rules
- correlation into Loki and Tempo must be preserved
- startup smoke and one synthetic request must validate each deploy

## Smoke validation baseline

- CI validates `ENVIRONMENT`, `SENTRY_DSN` and `SENTRY_RELEASE` before targeted smoke execution
- targeted pytest smoke verifies `/health` stays reachable while backend settings expose the expected Sentry contract from CI env vars

## Implementation checklist

- add env documentation gaps
- standardize tags and severity mapping
- add smoke event path and release marker flow
- verify critical span coverage for DB, Redis and external HTTP
