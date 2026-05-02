# Frontend Web

Status: draft
Owner: web
Last updated: 2026-04-24
Scope: `frontend/`
Depends on: `../05-environment-and-release-contract.md`, `../07-privacy-pii-scrubbing-and-replay-policy.md`
Related paths: `frontend/src/instrumentation-client.ts`, `frontend/sentry.server.config.ts`, `frontend/sentry.edge.config.ts`, `frontend/src/proxy.ts`, `frontend/.env.example`

## Current state

- `@sentry/nextjs` is already wired.
- Client, server and edge configs exist.
- Web vitals and global error capture exist.
- Explicit app environment and release inputs are now wired in config.
- Current staging deploy path now exposes Sentry build-upload env scaffolding for sourcemaps and writes release metadata into the job summary.

## Target

- Normalize browser environment through `NEXT_PUBLIC_APP_ENV`.
- Normalize server and edge environment through `APP_ENV`.
- Keep separate public and server DSN variables.
- Add canonical `SENTRY_RELEASE`.
- Decide whether public tunnel is required for this public-facing app.

## Gaps

- Deploy pipelines still need to pass the new environment and release contract consistently.
- `frontend` does not yet have the richer custom runtime layer present in `admin` and `partner`.
- Only the current staging workflow path is aligned; production and other rollout paths still need the same contract.

## Smoke validation baseline

- CI boots a production build with explicit `APP_ENV=staging`, `SENTRY_RELEASE=frontend@<git-sha>`, `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`
- runtime contract is exposed only to trusted callers through `GET /api/observability/sentry-contract`
- CI validates both the public page smoke (`/en-EN`) and the protected runtime contract endpoint

## Implementation checklist

- add explicit environment and release inputs
- propagate the contract to all real deploy workflows
- align server, edge and client config
- decide on tunnel and proxy behavior
- verify source map upload
- add post-deploy browser plus server smoke path
