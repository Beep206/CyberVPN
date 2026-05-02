# Mini App Production Launch And Stabilization Technical Debt

**Date:** 2026-04-22  
**Status:** Open technical debt  
**Purpose:** record the Mini App launch and stabilization work that remains intentionally deferred because it requires live staging or production access, real credentials, and an actual release window.

---

## 1. Role Of This Document

This note records the remaining operational closure work for the CyberVPN Telegram Mini App after the code-side launch package was completed.

It exists so these items are not left in commentary or treated as an implied follow-up. They are explicit runtime residuals after the implementation, hardening, observability, launch-control, and local conformance layers were completed.

This is not a note about missing product code. It is a note about deferred live operational execution.

---

## 2. What Is Already Ready In Code

The following assets are already implemented in the repository:

- Mini App runtime rollout controls and launch-readiness gates in backend and admin;
- Mini App launch summary, launch actions, and audit trail;
- Mini App observability metrics, alerts, dashboards, and runbooks;
- staging smoke automation:
  - `npm run staging:miniapp-launch:smoke`
- local conformance gate:
  - `npm run conformance:miniapp-launch`
- evidence pack bootstrap:
  - `npm run evidence:miniapp-launch:init -- <date> <environment> <run-id> <release-window> "<operator>"`
- operational documents:
  - [MINIAPP_STAGING_ROLLOUT_RUNBOOK.md](../runbooks/MINIAPP_STAGING_ROLLOUT_RUNBOOK.md)
  - [MINIAPP_RUNTIME_OBSERVABILITY_RUNBOOK.md](../runbooks/MINIAPP_RUNTIME_OBSERVABILITY_RUNBOOK.md)
  - [MINIAPP_LAUNCH_CONTROL_RUNBOOK.md](../runbooks/MINIAPP_LAUNCH_CONTROL_RUNBOOK.md)

The code-side launch package is therefore considered ready for handoff into a real release window.

---

## 3. Open Technical Debt Items

| ID | Item | Why Still Open | Closure Evidence |
|---|---|---|---|
| `MINIAPP-LAUNCH-DEBT-01` | run a real staging Mini App launch smoke | requires live staging hosts, real service availability, and working credentials | smoke transcript plus archived evidence directory |
| `MINIAPP-LAUNCH-DEBT-02` | initialize and fill the evidence pack for the exact release window | cannot be completed without a real staging or production window | evidence pack with timestamps, operator name, and scenario outcomes |
| `MINIAPP-LAUNCH-DEBT-03` | verify live Prometheus and Grafana signals during the staging window | dashboards and alerts are coded, but live signal flow cannot be proven locally | Prometheus query captures, dashboard screenshots, alert evidence |
| `MINIAPP-LAUNCH-DEBT-04` | execute real canary cutover through launch actions | requires operator decision, live allowlist, and runtime traffic | audit log evidence plus launch timeline entries |
| `MINIAPP-LAUNCH-DEBT-05` | execute live production cutover or explicitly hold | depends on successful staging evidence and operational approval | `live / hold / rollback` decision record |
| `MINIAPP-LAUNCH-DEBT-06` | run the first stabilization window after activation | requires a real launch and live traffic | stabilization review log and archived launch evidence |

---

## 4. Blocking Nature

These residuals are:

- not blockers for code completion;
- blockers for claiming real production launch;
- blockers for claiming production-proven stabilization.

In short:

- code is ready;
- live operational proof is intentionally deferred.

---

## 5. Preconditions For Closure

Before this technical debt can be retired, the following must exist:

- reachable staging API base;
- reachable staging admin surface;
- staging admin credentials;
- staging customer credentials for Mini App validation;
- optional Prometheus access for live metric verification;
- agreed release window;
- named operator or release owner;
- approved canary or live activation scope.

---

## 6. Recommended Closure Order

Retire these residuals in this order:

1. run `npm run conformance:miniapp-launch` to reconfirm repo state immediately before the live window;
2. create the evidence directory with `npm run evidence:miniapp-launch:init -- ...`;
3. run `npm run staging:miniapp-launch:smoke`;
4. archive staging evidence, metric proof, and any alert proof;
5. execute canary cutover if staging evidence is acceptable;
6. record `live / hold / rollback`;
7. if launched, enter the first stabilization window and archive the review.

---

## 7. Exit Condition

This technical debt note may be marked closed only when:

- the staging smoke is executed against a real environment;
- the evidence pack is archived for the exact release window;
- live metrics and dashboards are proven during the rollout window;
- a canary or live launch decision is recorded explicitly;
- if activation happens, the first stabilization review is archived.

Until then, the correct project posture is:

- implementation complete on the code side;
- launch and stabilization deferred on the operations side.
