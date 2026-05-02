# Sentry Rollout Tracker

Status: draft
Owner: platform
Last updated: 2026-04-25
Scope: live execution tracker for all direct Sentry surfaces
Depends on: `../observability/sentry/04-sentry-project-registry.md`
Related paths: `2026-04-24-sentry-implementation-roadmap.md`

## Status vocabulary

- `baseline_complete`: wave-level runtime baseline is implemented and verified
- `contract_aligned`: runtime contract is implemented, but dedicated smoke or operational closure remains open
- `pending`: implementation has not started

## Acceptance vocabulary

- `pending_deploy_strategy`: runtime baseline is complete, but the live deploy-marker owner is not yet assigned
- `pending_live_sentry`: repo-owned acceptance path exists, but live self-hosted Sentry proof is still pending
- `pending_external_deployer`: acceptance depends on an external deployer or store-promotion path outside this repo
- `production_accepted`: live self-hosted Sentry and deploy ownership are fully proven

| Surface | Project | DSN | Env | Release | Artifacts | Smoke | Privacy | Alerting | Tests | Status | Acceptance | PR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `frontend` | `web-frontend` | strong | strong | strong | partial | strong | strong | partial | strong | baseline_complete | pending_deploy_strategy | - |
| `admin` | `web-admin` | strong | strong | strong | partial | strong | strong | partial | strong | baseline_complete | pending_deploy_strategy | - |
| `partner` | `web-partner` | strong | strong | strong | partial | strong | strong | partial | partial | baseline_complete | pending_deploy_strategy | - |
| `backend` | `backend-api` | strong | strong | strong | n/a | strong | strong | partial | strong | baseline_complete | pending_deploy_strategy | - |
| `services/task-worker` | `task-worker` | strong | strong | strong | n/a | strong | strong | partial | strong | baseline_complete | pending_deploy_strategy | - |
| `cybervpn_mobile` | `cybervpn-mobile` | partial | partial | strong | strong | strong | strong | partial | strong | baseline_complete | pending_external_deployer | - |
| `services/telegram-bot` | `telegram-bot` | strong | strong | strong | n/a | strong | strong | partial | strong | baseline_complete | pending_deploy_strategy | - |
| `apps/desktop-client` | `desktop-renderer` / `desktop-native` | strong | strong | strong | strong | strong | strong | partial | strong | baseline_complete | pending_live_sentry | - |
| `apps/android-tv` | `android-tv` | strong | strong | strong | strong | strong | strong | partial | strong | baseline_complete | pending_live_sentry | - |
| `services/node-fleet-controller` | `node-fleet-controller` | strong | strong | strong | n/a | strong | strong | partial | strong | baseline_complete | pending_deploy_strategy | - |
| `services/helix-adapter` | `helix-adapter` | strong | strong | strong | strong | strong | strong | partial | strong | baseline_complete | pending_external_deployer | - |
| `services/helix-node` | `helix-node` | strong | strong | strong | strong | strong | strong | partial | strong | baseline_complete | pending_external_deployer | - |
