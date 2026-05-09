# Stage 1 Evidence Pack

This directory is the navigational evidence pack for `S1 Controlled Public Beta`.

It does not duplicate every transcript. Instead, each category README links back to the canonical evidence documents under `docs/cybervpn_stage1_launch_docs/`.

## Categories

| Directory | Purpose |
|---|---|
| `payments/` | Provider readiness, webhook, idempotency, refund, reconciliation and paid-access evidence |
| `infra/` | Production topology, staging/prod placement, ingress, DNS/TLS, managed services and home-lab boundary evidence |
| `vpn/` | Remnawave, protocols, provisioning, retry, expiry, usage, regions and node policy evidence |
| `db/` | Clean migrations, first-admin bootstrap, backup and restore evidence |
| `security/` | Secrets, endpoint boundary, Swagger, CORS/cookies/CSRF, backend/edge rate limits, auth flows, bundle/env and dependency evidence |
| `frontend/` | Customer web dashboard, config delivery, critical UI, i18n, screenshots and frontend build evidence |
| `observability/` | Sentry, PII scrubbing, metrics, dashboards, alerts and incident trace evidence |
| `release/` | Branch/tag policy, release notes, rollback, go/no-go and final RC evidence |
| `legal-support/` | Legal/text approval, support ticket paths, templates, escalation and refund/orphan workflows |
| `scope-map/` | Dirty worktree inventory and launch-critical/excluded scope map |

## Rules

- No secret values, raw tokens, private keys, provider dashboard credentials or unredacted payment payloads belong in this pack.
- Local evidence must be labelled local/dev/no-cost when it does not prove staging/prod readiness.
- External provider evidence must be redacted before committing.
- Go-live requires a final evidence review against `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`.

Current root index: `../../91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`.
