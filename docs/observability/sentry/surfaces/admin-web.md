# Admin Web

Status: draft
Owner: web
Last updated: 2026-04-24
Scope: `admin/`
Depends on: `../05-environment-and-release-contract.md`, `../08-tags-context-correlation-and-fingerprinting-contract.md`
Related paths: `admin/src/instrumentation-client.ts`, `admin/sentry.server.config.ts`, `admin/sentry.edge.config.ts`, `admin/src/shared/lib/frontend-observability.ts`, `admin/.env.example`

## Current state

- `@sentry/nextjs` is already integrated.
- Admin-specific frontend observability layer already exists.
- Browser tracing, replay and runtime telemetry are already partially present.
- Explicit app environment and release inputs are now wired in config.
- Dedicated Sentry contract smoke now exists through `/api/observability/sentry-contract`.

## Target

- Keep admin in its own Sentry project.
- Preserve the current sanitized runtime layer and align it with the shared tag contract.
- Separate staging and production environments explicitly.
- Route admin issues independently from public web and partner surfaces.

## Admin-specific considerations

- admin mutations are incident-grade
- replay masking must stay stricter than public web
- admin-only internal routes must not leak secrets or bot-internal payloads

## Implementation checklist

- propagate the environment and release contract through real deploy workflows
- keep sanitization layer as the baseline pattern
- verify hidden sourcemaps and server-side DSN in staging
- extend from contract smoke into one privileged-flow smoke path if admin auth fixtures become stable
