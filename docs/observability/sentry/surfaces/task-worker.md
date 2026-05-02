# Task Worker

Status: draft
Owner: core
Last updated: 2026-04-24
Scope: `services/task-worker/`
Depends on: `../05-environment-and-release-contract.md`, `../09-sampling-tracing-replay-and-volume-policy.md`
Related paths: `services/task-worker/src/broker.py`, `services/task-worker/src/config.py`, `services/task-worker/.env.example`

## Current state

- Worker already initializes Sentry when DSN is present.
- Redis broker and scheduled task categories are confirmed.
- `SENTRY_DSN` is now documented in `.env.example`.
- `SENTRY_RELEASE` is now wired through worker settings and startup init.

## Target

- adopt release naming and deploy markers
- standardize worker tags around task, queue, retries and trigger source
- keep lower sampling for noisy housekeeping tasks

## Worker-specific considerations

- retryable failures must not become incident noise
- canary task and startup heartbeat should prove rollout
- backend request/job correlation should be preserved when tasks are spawned from API flows

## Smoke validation baseline

- CI validates `ENVIRONMENT`, `SENTRY_DSN` and `SENTRY_RELEASE` before worker smoke tests
- startup smoke asserts `sentry_sdk.init(...)` receives the resolved DSN, environment and release
- config smoke asserts the loaded settings expose the same contract that CI injected

## Implementation checklist

- add config documentation
- add tag contract
- add canary task validation
- apply differential sampling by task group
