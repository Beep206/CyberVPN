# Mini App Staging Rollout Runbook

**Date:** 2026-04-22  
**Status:** Release-readiness runbook  
**Purpose:** execute the canonical staging validation pass for Telegram Mini App runtime, launch control, and customer-facing read paths before canary widening or live promotion.

---

## 1. Document Role

This runbook is the operational companion to:

- [Mini App runtime observability runbook](./MINIAPP_RUNTIME_OBSERVABILITY_RUNBOOK.md)
- [Mini App launch control runbook](./MINIAPP_LAUNCH_CONTROL_RUNBOOK.md)
- [Mini App launch rollout evidence template](../evidence/miniapp/templates/miniapp-launch-rollout-evidence-template.md)
- [growth-platform rollout plan](../growth-platform/10-rollout-plan.md)

Use this runbook when a live staging window must prove:

- admin launch-control surfaces are authoritative and consistent;
- a smoke customer can authenticate and access the Mini App runtime under the current rollout mode;
- `bootstrap` and `offers` are healthy for the target cohort;
- `config` behavior is understood and archived as evidence;
- launch-control and runtime metrics are reachable for the same window.

This runbook does not replace per-environment deploy procedures. It defines the minimum Mini App rollout loop required before canary widening or live promotion.

---

## 2. Required Inputs

Prepare before the window:

- exact staging API base URL
- disposable staging admin operator account
- disposable staging Mini App customer account
- evidence archive path under `docs/evidence/miniapp/<date>/staging/launch/`
- latest green Mini App conformance run
- current rollout ring under validation, normally `R1` or `R2`
- Prometheus base URL when monitoring proof is required from the same shell session

Recommended environment variables:

```bash
export CYBERVPN_API_BASE="https://api.staging.cybervpn.example"
export CYBERVPN_ADMIN_SMOKE_EMAIL="admin-smoke@example.com"
export CYBERVPN_ADMIN_SMOKE_PASSWORD="replace-me"
export CYBERVPN_MINIAPP_CUSTOMER_SMOKE_EMAIL="miniapp-smoke@example.com"
export CYBERVPN_MINIAPP_CUSTOMER_SMOKE_PASSWORD="replace-me"
export CYBERVPN_MINIAPP_LOCALE="en-EN"
export CYBERVPN_MINIAPP_START_PARAM="staging-launch-smoke"
export CYBERVPN_PROMETHEUS_BASE="https://prometheus.staging.cybervpn.example"
export EVIDENCE_DIR="docs/evidence/miniapp/2026-04-22/staging/launch/miniapp-launch-run01"
```

Optional environment flags for deeper checks:

```bash
export CYBERVPN_MINIAPP_EXPECT_CONFIG=true
export CYBERVPN_MINIAPP_ENABLE_TRIAL_SMOKE=false
export CYBERVPN_MINIAPP_TRIAL_EXPECT_SUCCESS=false
export CYBERVPN_MINIAPP_PAYMENT_ID="<known-payment-uuid>"
```

---

## 3. Preconditions

Do not start the live window if any item below is false.

- [ ] staging deploy for `backend`, `frontend`, and `admin` is complete
- [ ] latest Mini App conformance run is green
- [ ] committed OpenAPI and generated client types are in sync
- [ ] admin launch summary has been reviewed
- [ ] smoke customer is valid for the current rollout mode
- [ ] rollback owner and support owner are online
- [ ] evidence directory for this run exists
- [ ] Mini App runtime and launch-control dashboards are reachable
- [ ] no unrelated high-risk rollout is sharing the same window

---

## 4. CI Gate Verification

Start with the standalone conformance gate:

```bash
npm run conformance:miniapp-launch
```

If the evidence pack for this exact run is not initialized yet:

```bash
npm run evidence:miniapp-launch:init -- 2026-04-22 staging miniapp-launch-run01 R2 "miniapp ops"
```

Minimum archived evidence from this checkpoint:

- backend Mini App route and launch-control test result
- frontend Mini App runtime test result
- admin governance test result
- rollout asset validation result

If this checkpoint fails, stop the window. Do not move to staging-host validation.

---

## 5. Staging Runtime Validation

Run the canonical staging smoke:

```bash
npm run staging:miniapp-launch:smoke
```

This smoke captures:

- admin runtime config, readiness, summary, and timeline
- mobile customer login for the Mini App cohort
- Mini App `bootstrap` read model
- Mini App `offers` read model
- Mini App `config` behavior
- optional payment-status or trial evidence when explicitly enabled
- optional Prometheus proof for launch state, blockers, request rate, and config failure ratio

Required evidence artifacts from the smoke:

- admin runtime config snapshot
- admin launch summary snapshot
- admin launch timeline snapshot
- customer login proof
- Mini App bootstrap and offers responses
- Mini App config response or 404 proof
- monitoring proof or explicit monitoring-access exception

---

## 6. Exit Criteria

The staging run is `pass` only if all conditions below are true:

- Mini App conformance gate is green
- admin launch summary matches the intended rollout mode
- smoke customer receives `bootstrap` with `accessGranted=true`
- `offers` loads successfully
- `config` response is either the expected `200` or an explicitly accepted `404` for the disposable smoke account
- no unresolved blocker remains in the divergence register

If any critical step fails:

1. stop widening immediately
2. preserve responses, logs, and screenshots
3. classify the run as `hold` or `rollback`
4. attach the exact failing checkpoint to the evidence pack

---

## 7. Launch Decision Guidance

Use staging evidence together with the admin launch summary:

- if `launch_state=ready_for_live` and the window is staffed, promotion may proceed through the admin launch action `promote_to_live`
- if runtime is healthy but staffing or ownership fields are incomplete, keep `canary`
- if customer impact exists, prefer `start_rollback`
- if rollout must pause without safe canary continuation, use `enter_maintenance`

Do not switch to `live` outside the admin launch-control surface.

---

## 8. Required Evidence Manifest

Attach the following to the run record:

- command transcript for `npm run conformance:miniapp-launch`
- command transcript for `npm run staging:miniapp-launch:smoke`
- admin runtime, readiness, summary, and timeline snapshots
- Mini App bootstrap and offers snapshots
- Mini App config snapshot or accepted absence proof
- monitoring proof or explicit exception record
- divergence register
- final rollout decision block with named owner
