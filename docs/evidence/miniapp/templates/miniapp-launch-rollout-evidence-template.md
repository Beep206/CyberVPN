# Mini App Launch Rollout Evidence Template

**Use for:** staging, production canary, or production launch windows validating Telegram Mini App rollout readiness and cutover discipline.

---

## Metadata

- **Run ID:** `<run-id>`
- **Date:** `<YYYY-MM-DD>`
- **Environment:** `<staging|production-canary|production>`
- **Release Ring:** `<ring>`
- **Owner:** `<owner>`
- **Participants:** `<participants>`
- **CI Workflow URL:** `<workflow-url>`
- **Result:** `pending`

---

## Preconditions

- [ ] miniapp launch conformance gate green
- [ ] committed OpenAPI and generated client types in sync
- [ ] Mini App runtime dashboard reachable
- [ ] launch-control dashboard reachable
- [ ] admin launch summary reviewed
- [ ] smoke customer valid for current rollout mode
- [ ] rollback owner online
- [ ] evidence directory created

---

## API Checkpoints

| Check | Result | Evidence Link | Notes |
|---|---|---|---|
| admin runtime config | pending | `./admin/runtime.json` | |
| admin launch readiness | pending | `./admin/launch-readiness.json` | |
| admin launch summary | pending | `./admin/launch-summary.json` | |
| admin launch timeline | pending | `./admin/launch-timeline.json` | |
| customer mobile login | pending | `./miniapp/customer-login.json` | |
| miniapp bootstrap | pending | `./miniapp/bootstrap.json` | |
| miniapp offers | pending | `./miniapp/offers.json` | |
| miniapp config | pending | `./miniapp/config.json` | |
| miniapp payment status | optional | `./miniapp/payment-status.json` | |
| miniapp trial activation | optional | `./miniapp/trial-activate.json` | |

---

## Monitoring And Alerts

| Signal | Result | Evidence Link | Notes |
|---|---|---|---|
| launch state metric | pending | `./monitoring/launch-state.json` | |
| launch blockers metric | pending | `./monitoring/launch-blockers.json` | |
| runtime request rate | pending | `./monitoring/runtime-request-rate.json` | |
| config failure ratio | pending | `./monitoring/config-failures.json` | |

---

## Divergence Register

| ID | Category | Description | Severity | Owner | Blocking | Disposition |
|---|---|---|---|---|---|---|

---

## Final Decision

- **Decision:** `pending`
- **Decision Owner:** `pending`
- **Timestamp:** `pending`
- **Summary:** `pending`
