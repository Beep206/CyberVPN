# Environment And Release Contract

Status: draft
Owner: platform + runtime owners
Last updated: 2026-04-24
Scope: environment and release naming across all Sentry surfaces
Depends on: `04-sentry-project-registry.md`
Related paths: `10-ci-cd-release-artifacts-and-deploy-markers.md`, `11-smoke-tests-and-validation.md`

## Canonical environment values

The canonical Sentry environment vocabulary for this monorepo is:

- `development`
- `staging`
- `production`

## Normalization rules

### Web

- Client: `NEXT_PUBLIC_APP_ENV`
- Server and edge: `APP_ENV`
- Fallback only during transition: `NODE_ENV`
- Release variables: `NEXT_PUBLIC_SENTRY_RELEASE` for browser and `SENTRY_RELEASE` for server/edge

### Backend, worker, bot and controller

- Source of truth: `ENVIRONMENT`
- Allowed values must normalize to the canonical set above
- Release variable: `SENTRY_RELEASE`

### Mobile

- Map `dev` -> `development`
- Map `staging` -> `staging`
- Map `prod` -> `production`
- Keep `internal`, `beta`, `canary` as rollout tags, not as the main Sentry environment
- Runtime source remains `API_ENV` in Flutter, with normalization applied at Sentry init boundaries

### Desktop and Android TV

- Use canonical environment values in build-time config
- Keep distribution tracks as tags, not environment

## Canonical release naming

### Server and web runtime

- `frontend@<git-sha>`
- `admin@<git-sha>`
- `partner@<git-sha>`
- `backend@<git-sha>`
- `task-worker@<git-sha>`
- `telegram-bot@<git-sha>`
- `node-fleet-controller@<git-sha>`
- `helix-adapter@<git-sha>`
- `helix-node@<git-sha>`

### User-facing packaged apps

- `cybervpn-mobile@<version>+<build>`
- `desktop@<version>+<build>`
- `android-tv@<version>+<build>`

## Deploy markers and finalization

- Create release at build time.
- Upload debug artifacts in the same pipeline that builds the artifact.
- Mark deploy only after successful deployment.
- Finalize release only after post-deploy smoke validation succeeds.

## Optional tags

- `deployment_ring` for phased rollout surfaces only
- `runtime_layer` for split projects such as desktop renderer/native

## Wave 1 implemented sources of truth

| Surface group | Implemented env source | Implemented release source |
| --- | --- | --- |
| `frontend` | `APP_ENV` / `NEXT_PUBLIC_APP_ENV` | `SENTRY_RELEASE` / `NEXT_PUBLIC_SENTRY_RELEASE` |
| `admin` | `APP_ENV` / `NEXT_PUBLIC_APP_ENV` | `SENTRY_RELEASE` / `NEXT_PUBLIC_SENTRY_RELEASE` |
| `partner` | `APP_ENV` / `NEXT_PUBLIC_APP_ENV` | `SENTRY_RELEASE` / `NEXT_PUBLIC_SENTRY_RELEASE` |
| `backend` | `ENVIRONMENT` | `SENTRY_RELEASE` |
| `services/task-worker` | `ENVIRONMENT` | `SENTRY_RELEASE` |
| `services/telegram-bot` | `ENVIRONMENT` | `SENTRY_RELEASE` |
| `cybervpn_mobile` | `API_ENV` normalized to canonical Sentry env | `SENTRY_RELEASE` via `--dart-define` |
