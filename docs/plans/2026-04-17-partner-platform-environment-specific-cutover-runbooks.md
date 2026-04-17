# CyberVPN Partner Platform Environment-Specific Cutover Runbooks

**Date:** 2026-04-17  
**Status:** Environment-specific cutover runbook package  
**Purpose:** define the operational cutover procedures for local integration, staging validation, and production rollout environments for the CyberVPN partner platform.

---

## 1. Document Role

This document converts the platform-level cutover model into environment-specific execution guidance.

It must be used together with:

- [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md)
- [2026-04-17-partner-platform-detailed-phased-implementation-plan.md](2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [2026-04-17-partner-platform-delivery-program.md](2026-04-17-partner-platform-delivery-program.md)

This document does not replace per-service deployment docs. It defines how the partner-platform cutover is executed across environments.

---

## 2. Environment Taxonomy

| Environment | Purpose | Main release rings | Operational posture |
|---|---|---|---|
| `local` | developer and QA integration | `R0`, `R1` | synthetic data, local services, no external partner traffic |
| `staging` | shadow validation, rehearsals, limited pilot simulation | `R1`, `R2`, selected `R3` dry-runs | production-like routing, controlled datasets, disposable accounts |
| `production` | partner and customer traffic | `R3`, `R4` | strict freeze windows, explicit approvals, immutable evidence capture |

Current repository evidence:

- local development uses repo-root `npm` commands and `infra/docker compose`;
- staging infrastructure exists under `infra/terraform/live/staging/*`;
- some staging operational checklists already exist in [STAGING_REMNAWAVE_SMOKE_CHECKLIST.md](/home/beep/projects/VPNBussiness/docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md) and [CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md);
- production-specific command sources are not fully stored in this repository and must be filled by environment owners before live cutover.

---

## 3. Common Cutover Algorithm

Every environment-specific runbook follows the same sequence:

1. Confirm cutover unit, environment, owners, and window.
2. Confirm freeze checkpoint and ring-promotion approval.
3. Confirm rollback class and rollback owner.
4. Validate pre-cutover metrics and evidence baselines.
5. Execute the environment-specific command checklist.
6. Run immediate smoke checks and targeted conformance checks.
7. Run shadow or reconciliation checks if the environment requires them.
8. Decide promote, hold, contain, or rollback.
9. Record evidence in the rehearsal and archive template.
10. Handover to the next environment or rollout ring.

No environment may skip steps `2`, `3`, `6`, or `9`.

---

## 4. Cutover Unit Applicability By Environment

| Cutover unit | Local | Staging | Production | Notes |
|---|---|---|---|---|
| `CU1` Auth realm activation | yes | yes | yes | mandatory before partner storefront pilots |
| `CU2` Storefront routing activation | partial | yes | yes | local may use host overrides or mock host resolution |
| `CU3` Order-domain cutover | yes | yes | yes | highest-risk commercial cutover |
| `CU4` Attribution engine activation | yes | yes | yes | requires shadow mode before broad prod |
| `CU5` Growth reward activation | yes | yes | yes | must verify no cash-owner conflicts |
| `CU6` Settlement and statement activation | partial | yes | yes | local can simulate, staging and production are authoritative |
| `CU7` Partner payout activation | no | dry-run only | yes | live payout execution is production-only |
| `CU8` Entitlement activation | yes | yes | yes | channel-neutral access checks required |
| `CU9` Official frontend activation | yes | yes | yes | surface-policy enforcement required |
| `CU10` Partner storefront activation | limited | yes | yes | requires realm, merchant, support routing proof |
| `CU11` Partner portal activation | yes | yes | yes | finance views must be API-backed |
| `CU12` Admin and support activation | yes | yes | yes | operator audit evidence required |
| `CU13` Reporting and export activation | yes | yes | yes | staging used for reconciliation before prod |
| `CU14` Channel parity activation | partial | yes | yes | promote separately per channel |

---

## 5. Local Integration Runbook

## 5.1 Scope

The local environment exists to validate:

- schema and API compatibility;
- realm-aware auth behavior;
- quote, order, attribution, and entitlement flows;
- surface-policy enforcement in dev mode;
- operator-facing UI integration against local or mocked services.

It does not validate:

- real partner payouts;
- production-grade traffic routing;
- live chargeback/provider lifecycles;
- external partner cohort behavior.

## 5.2 Local Preflight

Minimum local preflight:

1. Install repo dependencies with `npm install`.
2. Start core local services with `cd infra && docker compose up -d`.
3. Start frontend with `NEXT_TELEMETRY_DISABLED=1 npm run dev`.
4. Confirm local Postgres, Redis/Valkey, and backend dependencies are healthy.
5. Prepare synthetic test data for realms, storefronts, partner accounts, orders, and reward cases.
6. Confirm feature flags or config toggles for the target cutover unit.

## 5.3 Local Cutover Procedure

| Step | Action | Evidence required |
|---|---|---|
| `L1` | apply additive schema changes and verify boot | migration output, service boot logs |
| `L2` | enable feature flag or local authority switch for target cutover unit | config diff |
| `L3` | run targeted smoke path for the unit | test or smoke output |
| `L4` | run negative and abuse scenarios for the same unit | failure-case evidence |
| `L5` | verify explainability and audit outputs | screenshots or API responses |
| `L6` | verify rollback path locally | rollback output and restored behavior |

## 5.4 Local Success Criteria

Local cutover is successful when:

- targeted API and UI flows pass;
- rollback path is proven at least once;
- synthetic replay for the cutover unit produces deterministic output;
- no environment-specific workaround is needed to keep the feature alive.

---

## 6. Staging Validation Runbook

## 6.1 Scope

Staging exists to validate:

- production-like routing and host resolution;
- shadow-mode comparisons;
- controlled pilot rehearsals;
- operational runbooks;
- support, finance, and risk workflows against realistic data.

Staging is the default environment for:

- `R1 -> R2` and most `R2 -> R3` promotion evidence;
- order-domain backfill rehearsals;
- shadow attribution and statement comparisons;
- partner storefront host and realm validation;
- entitlement parity checks across non-web channels.

## 6.2 Staging Preconditions

Before a staging cutover:

1. Confirm staging infrastructure state under `infra/terraform/live/staging/*` is current.
2. Confirm DNS, control-plane, and edge prerequisites are healthy.
3. Confirm disposable staging accounts exist for customer, partner, support, and admin scenarios.
4. Confirm evidence path and rehearsal template instance have been created.
5. Confirm rollback steps are rehearsed and the rollback owner is online.
6. Confirm no unrelated staging changes are being rolled out in the same window.

## 6.3 Staging Command Sources

The following command sources are canonical and must be referenced instead of reinvented in each cutover:

- [staging/control-plane README](</home/beep/projects/VPNBussiness/infra/terraform/live/staging/control-plane/README.md>)
- [staging/foundation README](</home/beep/projects/VPNBussiness/infra/terraform/live/staging/foundation/README.md>)
- [staging/dns README](</home/beep/projects/VPNBussiness/infra/terraform/live/staging/dns/README.md>)
- [STAGING_REMNAWAVE_SMOKE_CHECKLIST.md](/home/beep/projects/VPNBussiness/docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md)
- [CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md)

## 6.4 Staging Cutover Procedure

| Step | Action | Evidence required |
|---|---|---|
| `S1` | freeze unrelated staging changes and confirm owners | change-freeze acknowledgement |
| `S2` | apply environment-specific schema or config promotion for the target unit | deployment log |
| `S3` | run targeted staging smoke checklist for the affected surfaces | smoke checklist result |
| `S4` | run shadow comparison or reconciliation cycle for affected objects | shadow report or reconciliation diff |
| `S5` | run operator workflows for support, finance, and risk if the unit affects them | screenshots or API traces |
| `S6` | classify result as ready, hold, contain, or rollback | decision record |
| `S7` | archive evidence and link it to the readiness log | archive manifest |

## 6.5 Staging Rollback Procedure

If staging cutover fails:

1. stop rollout widening immediately;
2. revert config or traffic exposure first;
3. preserve logs, diffs, and screenshots before cleanup;
4. restore previous authoritative path;
5. rerun smoke checks to prove restored behavior;
6. record the failed rehearsal and unresolved deltas.

---

## 7. Production Runbook

## 7.1 Scope

Production runbooks apply only after:

- `R3` pilot evidence exists;
- go/no-go governance approval is complete;
- rollback owners are assigned;
- reconciliation thresholds are green;
- support, risk, and finance staffing are scheduled for the window.

## 7.2 Production Preconditions

Before any production cutover window:

1. confirm the exact cutover unit or units;
2. confirm pilot evidence archive links;
3. confirm production-only secrets and environment manifests;
4. confirm communication channels for finance, risk, support, and engineering;
5. confirm freeze window start and end;
6. confirm rollback decision threshold and incident commander.

## 7.3 Production Command Discipline

Production command lists must not live only in chat messages. Before first live use, each production environment must have:

- a named command owner;
- an exact environment inventory;
- explicit deploy, verify, and rollback commands;
- secret locations and access approvers;
- DNS or host routing actions if relevant;
- smoke and reconciliation command references.

Where the repository does not already store production commands, the runbook must keep placeholders in this format and replace them before the window:

```text
<production-schema-apply-command>
<production-config-promotion-command>
<production-traffic-shift-command>
<production-shadow-compare-command>
<production-rollback-command>
```

No production cutover may begin while these placeholders remain unresolved.

## 7.4 Production Cutover Procedure

| Step | Action | Evidence required |
|---|---|---|
| `P1` | start cutover command review and confirm go/no-go approval | signed approval snapshot |
| `P2` | open incident or command channel and assign incident commander | channel link |
| `P3` | capture baseline metrics, liability views, and error budgets | baseline snapshot |
| `P4` | execute cutover commands in approved order | command transcript |
| `P5` | run immediate smoke checks and ring-specific validation | smoke evidence |
| `P6` | run mandatory shadow or reconciliation check for affected objects | reconciliation output |
| `P7` | decide widen, hold, contain, or rollback | decision record |
| `P8` | archive all evidence, including rollback if triggered | archive manifest |

## 7.5 Production Mandatory Freeze Rules

During a production cutover window:

- no unrelated schema work;
- no unrelated pricebook or merchant changes;
- no unrelated auth or routing changes;
- no payout execution while liability reconciliation is unresolved;
- no widening from one lane cohort to another without approval refresh.

---

## 8. Environment-Specific Checklists By High-Risk Unit

## 8.1 `CU1` Auth Realm Activation

Must prove in every environment:

- same email may exist in separate realms;
- same password does not grant cross-realm access;
- session audience and scopes are correct;
- legal acceptance and support routing remain surface-aware.

## 8.2 `CU3` Order-Domain Cutover

Must prove in staging and production:

- order snapshots are created exactly once;
- retries attach to one order correctly;
- refund and dispute references remain linked;
- finance can reconcile pre- and post-cutover totals.

## 8.3 `CU4` Attribution Engine Activation

Must prove in staging and production:

- explicit code precedence works;
- reseller persistence is not lost;
- explainability payload is readable by support and partner ops;
- winner divergence is below threshold.

## 8.4 `CU6` Settlement And Statement Activation

Must prove in staging and production:

- statement close and reopen works;
- holds and reserves are visible;
- payout availability is blocked when risk or finance requires it;
- no wallet-based shortcut controls partner finance.

## 8.5 `CU8` Entitlement Activation

Must prove in every environment:

- purchase and service-consumption contexts stay linked but distinct;
- entitlement issue and revoke flows are deterministic;
- channel-specific access stays consistent;
- support can inspect the active entitlement state.

---

## 9. Exit Criteria For This Runbook Package

This package is ready when:

- every cutover unit can be mapped to at least one environment-specific procedure;
- staging and production windows have explicit preconditions;
- production placeholders are visible and must be resolved before live use;
- local, staging, and production evidence requirements are clear enough to support the rehearsal template and readiness archive.
