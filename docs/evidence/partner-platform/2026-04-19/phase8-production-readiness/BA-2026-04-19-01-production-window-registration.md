# CyberVPN Partner Platform Production Window Registration

**Window ID:** `BA-2026-04-19-01`  
**Date:** 2026-04-19  
**Status:** production window registration baseline for broad activation readiness  
**Purpose:** record the exact production activation window baseline for the current `R3 -> R4` broad-activation review, using the canonical command inventory and linking the operational evidence already assembled by `Phase 8`.

---

## 1. Record Role

This record is the named production window registration required by:

- [partner-platform-phase8-production-readiness-bundle.md](../../../../testing/partner-platform-phase8-production-readiness-bundle.md)
- [partner-platform-phase8-exit-evidence.md](../../../../testing/partner-platform-phase8-exit-evidence.md)
- [partner-platform-broad-activation-sign-off-tracker.md](../../../../testing/partner-platform-broad-activation-sign-off-tracker.md)
- [2026-04-19-partner-platform-environment-command-inventory-sheet.md](../../../../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md)
- [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](../../../../plans/2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)
- [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](../../../../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)

This record is intentionally concrete about document scope and intentionally incomplete where live production data is not stored in the repository.

It is valid for execution planning only. It is not valid for live production command execution until every `pending` field in sections 2 through 5 is replaced with a real approved value.

---

## 2. Scope Freeze

| Field | Value |
|---|---|
| Approval request id | `BA-2026-04-19-01` |
| Requested on | `2026-04-19` |
| Requested by | `pending named requester` |
| Target rollout ring change | `R3 -> R4` |
| Exact lane set | `pending human scope freeze` |
| Exact surface set | `pending human scope freeze` |
| Exact pilot cohort ids | `pending human scope freeze` |
| Exact cutover units | `pending human scope freeze` |
| Exact rollout window name | `BA-2026-04-19-01 broad-activation window` |
| Exact environments | `production` |
| Approved start | `pending approved timestamp` |
| Approved end | `pending approved timestamp` |
| Incident commander | `pending named owner` |
| Command owner | `pending named owner` |
| Rollback owner | `pending named owner` |
| Finance approver | `pending named owner or n/a for non-payout scope` |
| Risk approver | `pending named owner or n/a for non-risk-sensitive scope` |
| Support lead | `pending named owner` |

Operational rule:

- no live execution is allowed while any field above still says `pending`;
- if the scope changes after sign-off, this record must be superseded rather than edited silently.

---

## 3. Runtime Parameters

The base command families are already frozen in the environment command inventory sheet. Only the live window values below remain to be filled.

| Parameter | Value |
|---|---|
| `BACKEND_IMAGE` | `pending immutable digest or n/a` |
| `WORKER_IMAGE` | `pending immutable digest or n/a` |
| `HELIX_ADAPTER_IMAGE` | `pending immutable digest or n/a` |
| `SECRETS_SOURCE` | `pending secure path or n/a` |
| `VAULT_PASSWORD_FILE` | `pending secure path or n/a` |
| `VAULT_ID` | `pending secure id or n/a` |
| `PROD_REMNAWAVE_CANARY_HOST` | `pending inventory hostname or n/a` |
| `PROD_HELIX_CANARY_HOST` | `pending inventory hostname or n/a` |
| Incident channel | `pending live channel ref` |
| Finance channel | `pending live channel ref or n/a` |
| Support channel | `pending live channel ref` |
| Risk channel | `pending live channel ref or n/a` |

These values must match the actual approved live window. Chat-only substitutions are not allowed.

---

## 4. Approved Command Set

| Command family | Canonical source for this window |
|---|---|
| terraform and inventory | [environment command inventory sheet, section 6.1](../../../../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md#61-terraform-and-inventory) |
| control-plane promotion | [environment command inventory sheet, section 6.2](../../../../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md#62-production-control-plane-promotion) |
| production edge rollout family | [environment command inventory sheet, section 6.3](../../../../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md#63-production-edge-rollouts) |
| production canary rollout family | [environment command inventory sheet, section 6.4](../../../../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md#64-production-canary-rollouts) |
| smoke and cutover discipline | [environment-specific cutover runbooks](../../../../plans/2026-04-17-partner-platform-environment-specific-cutover-runbooks.md) |
| rehearsal structure and archive rules | [rehearsal logs and evidence archive template](../../../../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md) |
| attribution shadow comparison | [partner-platform-phase8-attribution-shadow-pack.md](../../../../testing/partner-platform-phase8-attribution-shadow-pack.md) |
| settlement shadow comparison | [partner-platform-phase8-settlement-shadow-pack.md](../../../../testing/partner-platform-phase8-settlement-shadow-pack.md) |
| production readiness gate | [partner-platform-phase8-production-readiness-bundle.md](../../../../testing/partner-platform-phase8-production-readiness-bundle.md) |
| phase gate proof | [partner-platform-phase8-exit-evidence.md](../../../../testing/partner-platform-phase8-exit-evidence.md) |

No command outside these linked sources is approved for this registration record.

---

## 5. Evidence Links

| Evidence item | Link |
|---|---|
| sign-off tracker | [partner-platform-broad-activation-sign-off-tracker.md](../../../../testing/partner-platform-broad-activation-sign-off-tracker.md) |
| production-readiness bundle | [partner-platform-phase8-production-readiness-bundle.md](../../../../testing/partner-platform-phase8-production-readiness-bundle.md) |
| phase 8 exit evidence | [partner-platform-phase8-exit-evidence.md](../../../../testing/partner-platform-phase8-exit-evidence.md) |
| environment command inventory sheet | [2026-04-19-partner-platform-environment-command-inventory-sheet.md](../../../../plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md) |
| environment-specific runbooks | [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](../../../../plans/2026-04-17-partner-platform-environment-specific-cutover-runbooks.md) |
| rehearsal template | [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](../../../../plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md) |
| pilot roster and rollout calendar | [2026-04-17-partner-platform-pilot-cohort-roster-and-rollout-calendar.md](../../../../plans/2026-04-17-partner-platform-pilot-cohort-roster-and-rollout-calendar.md) |
| rehearsal log for this exact window | `pending evidence path` |
| archive manifest for this exact window | `pending evidence path` |
| pilot readiness snapshot archive ref | `pending archive ref` |
| owner acknowledgement archive ref | `pending archive ref` |
| rollback drill archive ref | `pending archive ref` |
| go / no-go decision archive ref | `pending archive ref` |

---

## 6. Current Blocking Status

| Check | Status | Notes |
|---|---|---|
| named registration record exists | complete | this document |
| base command inventory is explicit | complete | command inventory sheet linked |
| environment is frozen to production | complete | this record |
| exact lane set is named | pending | must be copied from approved scope |
| exact surface set is named | pending | must be copied from approved scope |
| exact pilot cohort ids are named | pending | must be copied from approved scope |
| exact cutover units are named | pending | must be copied from approved scope |
| approved start and end timestamps are recorded | pending | live window not yet named |
| named human owners are recorded | pending | live staffing not yet inserted |
| live runtime parameters are recorded | pending | digests, secrets, canary hosts absent from repo |
| rehearsal log is linked | pending | live rehearsal archive not yet attached |
| archive manifest is linked | pending | live archive not yet attached |
| human approvals are linked | pending | `RB-011` still open |

This record is therefore `execution-ready for coordination`, but not `live-ready for production cutover`.

---

## 7. Completion Rule

This production window registration record becomes valid for live use only when:

1. every `pending` field above is replaced with a real approved value;
2. the exact scope matches the approval scope in the sign-off tracker;
3. the rehearsal log and archive manifest for this exact window are linked;
4. the required named approvers have signed the readiness bundle and exit evidence for the same scope.

Until then, this document serves as the authoritative named placeholder for the activation window, but it does not authorize command execution.
