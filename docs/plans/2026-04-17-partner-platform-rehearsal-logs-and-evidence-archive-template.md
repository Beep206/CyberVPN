# CyberVPN Partner Platform Rehearsal Logs And Evidence Archive Template

**Date:** 2026-04-17  
**Status:** Rehearsal and evidence template package  
**Purpose:** define the canonical structure for rehearsal logs, shadow evidence, rollout evidence, reconciliation reports, and sign-off records for the CyberVPN partner platform.

---

## 1. Document Role

This document provides the reusable template layer for:

- cutover rehearsals;
- migration wave rehearsals;
- shadow comparison cycles;
- payout dry-runs;
- pilot evidence packages;
- rollback drills;
- post-launch stabilization reviews.

It should be used together with:

- [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md)
- [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)
- [2026-04-19-partner-platform-environment-command-inventory-sheet.md](2026-04-19-partner-platform-environment-command-inventory-sheet.md)
- [../testing/partner-platform-phase-0-and-phase-1-validation-pack.md](../testing/partner-platform-phase-0-and-phase-1-validation-pack.md)
- [../testing/partner-platform-phase1-exit-evidence.md](../testing/partner-platform-phase1-exit-evidence.md)
- [../testing/partner-platform-phase2-exit-evidence.md](../testing/partner-platform-phase2-exit-evidence.md)
- [../testing/partner-platform-phase3-exit-evidence.md](../testing/partner-platform-phase3-exit-evidence.md)
- [../testing/partner-platform-phase4-exit-evidence.md](../testing/partner-platform-phase4-exit-evidence.md)

---

## 2. Archive Structure

Recommended archive root:

```text
docs/evidence/partner-platform/
```

Recommended hierarchy:

```text
docs/evidence/partner-platform/
  YYYY-MM-DD/
    <environment>/
      <cutover-unit-or-wave>/
        README.md
        logs/
        screenshots/
        diffs/
        metrics/
        approvals/
```

Naming rule:

```text
YYYY-MM-DD_<environment>_<artifact-type>_<scope>_<run-id>
```

Examples:

```text
2026-04-17_staging_shadow_attribution_cu4_run01
2026-04-19_production_cutover_cu3_run02
2026-04-20_production_payout-dryrun_cu7_run01
```

---

## 3. Evidence Classes

| Evidence class | Description | Mandatory for |
|---|---|---|
| `command transcript` | executed commands or deployment actions | every cutover and migration rehearsal |
| `baseline snapshot` | pre-change metrics and state | every shadow, reconciliation, and production cutover |
| `smoke evidence` | screenshots, API responses, test output | every surface-affecting change |
| `shadow report` | new versus reference comparison | every `R1 -> R2` and `R2 -> R3` promotion |
| `reconciliation report` | finance, order, entitlement, or reporting diff | all financial and commercial changes |
| `rollback evidence` | proof rollback worked or was not needed | every rehearsal with rollback path |
| `approval record` | named human approvals and timestamps | every ring promotion and production cutover |
| `pilot decision record` | explicit `approved`, `hold`, or `no_go` decision with owner acknowledgements and rollback scope | every pilot activation, widen, hold, or stop decision |
| `issue register` | unresolved divergences and ownership | every non-clean rehearsal or pilot |

Before any Phase 1 schema or API foundation work starts, the Phase 0 validation pack must already define the minimum evidence shape and required synthetic fixtures.

Before any operational rehearsal assumes `Phase 1` foundations are frozen, the signed `Phase 1` exit evidence pack must already exist in the archive.

Before any operational rehearsal assumes `Phase 2` order-domain foundations are frozen, the signed `Phase 2` exit evidence pack must already exist in the archive.

Before any operational rehearsal assumes `Phase 3` attribution, growth-reward, and renewal foundations are frozen, the signed `Phase 3` exit evidence pack must already exist in the archive.

Before any operational rehearsal assumes `Phase 4` settlement and payout foundations are frozen, the signed `Phase 4` exit evidence pack must already exist in the archive.

Before any operational rehearsal simulates partner payout readiness on top of `Phase 4` settlement foundations, the archive must also include the dry-run settlement evidence spec in [../testing/partner-platform-phase4-dry-run-settlement-evidence.md](../testing/partner-platform-phase4-dry-run-settlement-evidence.md) and the reconciliation pack definition in [../testing/partner-platform-phase4-settlement-reconciliation-pack.md](../testing/partner-platform-phase4-settlement-reconciliation-pack.md).

Before any operational rehearsal assumes `Phase 5` service identity, entitlement, provisioning, and access-delivery foundations are frozen, the signed `Phase 5` exit evidence pack must already exist in the archive.

Before any operational rehearsal treats cross-channel service-access parity as ready for pilot consumption, the archive must also include the replay/parity pack definition in [../testing/partner-platform-phase5-service-access-replay-pack.md](../testing/partner-platform-phase5-service-access-replay-pack.md).

Before any operational rehearsal assumes `Phase 6` official-web, partner-storefront, partner-portal, or admin surfaces are frozen enough for ring promotion, the signed `Phase 6` exit evidence pack must already exist in the archive.

Before any operational rehearsal assumes `Phase 7` event/outbox, analytical marts, partner reporting, or channel parity are frozen enough for `Phase 8` shadow or pilot consumption, the signed `Phase 7` exit evidence pack must already exist in the archive.

Before any operational rehearsal treats `Phase 7` reporting or parity as rollout-grade, the archive must also include the analytical marts pack definition in [../testing/partner-platform-phase7-analytical-marts-and-reconciliation-pack.md](../testing/partner-platform-phase7-analytical-marts-and-reconciliation-pack.md) and the parity evidence pack definition in [../testing/partner-platform-phase7-parity-and-evidence-pack.md](../testing/partner-platform-phase7-parity-and-evidence-pack.md).

Before any `Phase 8` pilot posture is promoted into broad production activation, the archive must also include the signed readiness bundle in [../testing/partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md) together with the signed gate record in [../testing/partner-platform-phase8-exit-evidence.md](../testing/partner-platform-phase8-exit-evidence.md).

---

## 4. Core Rehearsal Log Template

Use this header for every rehearsal record.

```md
# Rehearsal Log

**Run ID:** <run-id>
**Date:** <YYYY-MM-DD>
**Environment:** <local|staging|production>
**Window ID:** <window-id or n/a>
**Release Ring:** <R0|R1|R2|R3|R4>
**Cutover Unit / Migration Wave:** <CUx / MWx>
**Lane:** <invite|referral|creator|performance|reseller|mixed>
**Surface:** <official-web|partner-storefront|partner-portal|admin|telegram|mobile|desktop|api>
**Owner:** <name/role>
**Participants:** <list>
**Rollback Class:** <config|traffic|decision-path|availability|containment>
**Result:** <pass|pass-with-issues|hold|rollback|fail>
```

---

## 5. Preconditions Template

```md
## Preconditions

- [ ] freeze checkpoint complete
- [ ] approving owners named
- [ ] rollback owner online
- [ ] baseline metrics captured
- [ ] evidence archive path created
- [ ] command inventory sheet linked
- [ ] window registration record linked if environment = production
- [ ] target commands reviewed
- [ ] support/finance/risk notified if required
- [ ] synthetic or pilot data prepared
```

Add environment-specific preconditions as needed.

---

## 6. Execution Log Template

```md
## Execution Log

| Time | Step | Action | Actor | Result | Evidence Link |
|---|---|---|---|---|---|
| 10:00 | 1 | start window and capture baseline | platform | pass | ./metrics/baseline.json |
| 10:05 | 2 | apply config promotion | platform | pass | ./logs/config-promotion.txt |
| 10:12 | 3 | run smoke checks | QA | pass | ./screenshots/smoke/ |
| 10:20 | 4 | run shadow comparison | data/BI | hold | ./diffs/shadow-diff.md |
```

Rules:

- each execution step must have an actor;
- every failing or partial step must link to evidence;
- no “done” row without a result value.

---

## 7. Metrics Snapshot Template

```md
## Metrics Snapshot

| Metric | Baseline | Current | Threshold | Status | Notes |
|---|---|---|---|---|---|
| auth success rate | 99.8% | 99.7% | >= 99.5% | pass | |
| attribution divergence | 0.0% | 0.7% | <= 1.0% | pass | |
| payout liability delta | $0 | $18 | <= $50 | pass | within tolerance |
| entitlement drift | 0 | 3 | = 0 | fail | investigate missing revokes |
```

---

## 8. Divergence Register Template

```md
## Divergence Register

| ID | Category | Description | Severity | Owner | Disposition | Blocking |
|---|---|---|---|---|---|---|
| D-01 | shadow | referral allocation duplicated on one account | high | growth | fix before re-run | yes |
| D-02 | reporting | portal export rounding differs from finance report | low | data/BI | accepted for later patch | no |
```

Use category values such as:

- `shadow`
- `reconciliation`
- `auth`
- `pricing`
- `settlement`
- `entitlement`
- `support`
- `legal`
- `ops`

---

## 9. Rollback Drill Template

```md
## Rollback Drill

**Rollback Triggered:** <yes|no>
**Rollback Reason:** <reason or not-applicable>
**Rollback Start:** <time>
**Rollback End:** <time>
**Rollback Owner:** <owner>

| Step | Action | Result | Evidence Link |
|---|---|---|---|
| 1 | disable authority path | pass | ./logs/rollback-step1.txt |
| 2 | restore prior config | pass | ./logs/rollback-step2.txt |
| 3 | re-run smoke checks | pass | ./screenshots/rollback-smoke/ |
```

If rollback was not triggered, record why it was not needed.

---

## 10. Approval And Sign-Off Template

```md
## Approvals

| Function | Name | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform engineering | <name> | approve | <time> | |
| finance | <name> | approve | <time> | |
| risk | <name> | hold | <time> | pending issue D-01 |
| support | <name> | approve | <time> | |
```

No production readiness evidence package is complete without a sign-off block.

---

## 11. Archive Manifest Template

```md
## Archive Manifest

- runbook used: <doc path>
- command inventory sheet: <doc path>
- window registration record: <path or n/a>
- screenshots: <path>
- logs: <path>
- shadow reports: <path>
- reconciliation diffs: <path>
- approvals: <path>
- incident or command channel transcript: <path>
- linked tickets or issues: <path>
```

---

## 12. Retention And Integrity Rules

Evidence handling rules:

1. do not overwrite historical evidence files;
2. append new run IDs instead of replacing old runs;
3. keep financial, attribution, and legal evidence immutable;
4. record redactions explicitly if sensitive values must be removed;
5. keep approval timestamps and approver identities;
6. maintain one README per archive folder summarizing outcome and blockers.

---

## 13. Minimal README Template For Archive Folders

```md
# Evidence Archive Summary

**Run ID:** <run-id>
**Environment:** <environment>
**Scope:** <cutover unit / wave / pilot>
**Result:** <pass|hold|rollback|fail>
**Blocking issues:** <list or none>
**Next action:** <re-run|promote|contain|rollback complete>
```

---

## 14. Exit Criteria For This Template Package

This template package is complete when:

- every rehearsal type can use one consistent structure;
- evidence is easy to locate by date, environment, and scope;
- approvals, divergences, and rollback behavior are always recorded;
- the archive can support audits, finance reviews, and post-launch investigations.
