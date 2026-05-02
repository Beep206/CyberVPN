# Target Architecture And Scope

Status: draft
Owner: platform (proposed)
Last updated: 2026-04-24
Scope: all direct and indirect Sentry coverage in the monorepo
Depends on: `00-current-state-and-discovery.md`
Related paths: `surfaces/`, `04-sentry-project-registry.md`, `05-environment-and-release-contract.md`

## Architectural principles

1. Sentry is used for application errors, crashes, release health, replay and app-level tracing.
2. Prometheus, Grafana, Loki, Tempo and PostHog remain the system of record for metrics, logs, infrastructure traces and product analytics.
3. Every deployable runtime surface gets its own project unless there is a strong operational reason not to split it.
4. Surface ownership follows runtime and operational boundaries, not repository folder convenience.
5. Privacy defaults are restrictive by default, with allowlist-based context and aggressive server-side scrubbing.

## Direct scope

The following surfaces are direct Sentry integration targets:

- `frontend`
- `admin`
- `partner`
- `backend`
- `services/task-worker`
- `services/telegram-bot`
- `services/node-fleet-controller`
- `services/helix-adapter`
- `services/helix-node`
- `cybervpn_mobile`
- `apps/desktop-client`
- `apps/android-tv`

## Indirect scope

The following repository areas do not get standalone Sentry projects and are covered through the runtime that imports them:

- `packages/*`
- `SDK/`
- shared frontend/domain libraries inside app folders

## Out of scope for now

- `infra/`
- `platform-gitops/`
- `docs/`
- `apps/browser-extension` until it becomes an executable runtime

## Project model

Target model:

- Separate Sentry projects for `frontend`, `admin`, `partner`, `backend`, `task-worker`, `telegram-bot`, `node-fleet-controller`, `helix-adapter`, `helix-node`, `cybervpn-mobile`, `android-tv`.
- Split `apps/desktop-client` into two Sentry projects: renderer and native.
- Use one organization-level policy package for privacy, tags, release handling and alerting.

## Rollout waves

### Wave 1

- `frontend`
- `admin`
- `partner`
- `backend`
- `services/task-worker`
- `cybervpn_mobile`

### Wave 2

- `services/telegram-bot`
- `apps/desktop-client`
- `apps/android-tv`
- `services/node-fleet-controller`

### Wave 3

- `apps/desktop-client`
- `services/helix-adapter`
- `services/helix-node`

## Target end-state

At the end of rollout:

- each direct surface has a project, DSN, environment contract and release contract;
- all production surfaces have artifact upload and smoke validation;
- privacy and replay rules are consistent across runtimes;
- incidents can be correlated from Sentry into logs and traces using shared identifiers.
