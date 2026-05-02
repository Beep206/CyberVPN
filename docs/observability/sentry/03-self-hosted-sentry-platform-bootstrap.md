# Self-Hosted Sentry Platform Bootstrap

Status: draft
Owner: platform
Last updated: 2026-04-24
Scope: self-hosted Sentry platform foundation and org-level bootstrap
Depends on: `02-open-questions-and-decision-log.md`
Related paths: `04-sentry-project-registry.md`, `07-privacy-pii-scrubbing-and-replay-policy.md`, `runbooks/self-hosted-sentry-operations.md`

## Goal

Bootstrap a self-hosted Sentry platform that is ready to host all CyberVPN runtime projects with stable access control, safe defaults and predictable retention.

## Bootstrap checklist

### Organization and access

- Create the CyberVPN organization.
- Create teams: `web`, `core`, `client-apps`, `platform`.
- Create at least 2 human org admins.
- Create 1 service account for CI artifact upload and release automation.
- Define least-privilege access for non-admin users.

### Project scaffolding

- Pre-create all Sentry projects listed in `04-sentry-project-registry.md`.
- Apply shared naming, slug and ownership conventions.
- Attach org-level rules for scrubbing and event size limits before DSNs are distributed.

### Storage and retention

- Set separate retention policy for `staging` and `production`.
- Set storage budget and replay/tracing caps before enabling replay broadly.
- Define backup and restore ownership and cadence.

### Security and privacy

- Turn on server-side scrubbing defaults before first production rollout.
- Denylist auth, cookie, token, payment and Telegram-config data centrally.
- Restrict raw attachments and oversized contexts unless explicitly allowed.

### Release operations

- Create CI auth token management path.
- Standardize release creation, artifact upload, deploy markers and verification.
- Define upgrade policy for the self-hosted Sentry platform itself.

## Boundary

If the self-hosted deployment is operated from another infrastructure repository, this document still remains the product-facing contract. The lower-level IaC/run commands may live elsewhere, but ownership, access model and defaults must stay aligned with this package.
