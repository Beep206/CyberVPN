# Partner Web

Status: draft
Owner: web
Last updated: 2026-04-24
Scope: `partner/`
Depends on: `../05-environment-and-release-contract.md`, `../08-tags-context-correlation-and-fingerprinting-contract.md`
Related paths: `partner/src/instrumentation-client.ts`, `partner/sentry.server.config.ts`, `partner/sentry.edge.config.ts`, `partner/src/shared/lib/frontend-observability.ts`, `partner/src/app/api/analytics/product-events/route.ts`

## Current state

- `@sentry/nextjs` is integrated.
- Partner-specific runtime observability already exists.
- Product-event and workspace telemetry paths exist.
- Explicit app environment and release inputs are now wired in config.
- Dedicated Sentry contract smoke now exists through `/api/observability/sentry-contract`.

## Target

- Keep partner in its own Sentry project.
- Preserve correlation potential with PostHog through safe IDs only.
- Treat partner workspace mutations and provisioning-related flows as critical.

## Partner-specific considerations

- workspace and product-intelligence routes need clear ownership
- partner runtime sanitization must remain strict
- correlation with analytics must never introduce raw PII into Sentry

## Implementation checklist

- propagate the environment and release contract through real deploy workflows
- preserve partner runtime tags and sanitize them against the shared allowlist
- extend from contract smoke into one workspace or privileged-flow smoke path once the partner Vitest bootstrap defect is removed
- verify source map upload and deploy markers
