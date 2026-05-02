# Customer Growth Reporting Governance GitHub Protection Handoff

This note defines the exact GitHub workflow and status check that should be configured as required before customer growth reporting governance is treated as protected in the normal PR merge path.

Repository:
- `Beep206/CyberVPN`

Workflow:
- `.github/workflows/customer-growth-reporting-governance-conformance.yml`
- workflow name: `Customer Growth Reporting Governance Conformance`

Required status check:
- `All Customer Growth Reporting Governance Checks Passed`

This is the aggregator job on purpose. It stays stable even if internal job names evolve.

Repo-side payload and helper:
- `.github/rulesets/customer-growth-reporting-governance-main-gate.disabled.json`
- `scripts/sync-customer-growth-reporting-governance-ruleset.sh`

Current repository gate posture:
- repo-managed ruleset payload exists
- GitHub ruleset name: `customer-growth-reporting-governance-main-gate`
- GitHub ruleset id: `15414851`
- GitHub ruleset URL: `https://github.com/Beep206/CyberVPN/rules/15414851`
- current enforcement: `disabled`

## What The Required Check Covers

The required check is green only if all of these jobs pass:

- `Backend Growth Reporting Governance Conformance`
- `Admin Growth Reporting Governance Conformance`
- `Growth Reporting Governance Assets`

This means the branch-protection gate covers:

- backend governance overview and export contracts;
- admin governance coverage, recent decisions, and audit trail surfaces;
- governance alert rules, runbook assets, evidence bootstrap, and ruleset payload integrity.

## CI Artifacts

Each workflow run uploads job logs as artifacts:

- `customer-growth-reporting-governance-backend-<run_id>`
- `customer-growth-reporting-governance-admin-<run_id>`
- `customer-growth-reporting-governance-assets-<run_id>`

Use these artifacts when:

- a required check fails and the PR author needs exact logs;
- governance evidence packs need CI transcript references;
- rollout review wants proof that governance exports, alerts, and handoff assets were green before a live window.
- protected-gate enablement review wants a machine-generated `enable` or `hold` recommendation from staging evidence.

## Manual GitHub Configuration

Configure branch protection or a ruleset for the protected branch and require this exact status check:

- `All Customer Growth Reporting Governance Checks Passed`

Do not require the three internal jobs separately unless governance wants each internal surface exposed. The aggregator check is the safer contract because it survives internal workflow refactors.

## Current Prepared-But-Disabled State

The repository keeps a disabled ruleset payload for this gate:

- ruleset name: `customer-growth-reporting-governance-main-gate`
- enforcement: `disabled`

Inspect current state:

```bash
bash scripts/sync-customer-growth-reporting-governance-ruleset.sh --show-current
```

Create the disabled ruleset if it does not yet exist:

```bash
bash scripts/sync-customer-growth-reporting-governance-ruleset.sh --create-disabled
```

Enable later:

```bash
bash scripts/sync-customer-growth-reporting-governance-ruleset.sh --enable
```

Disable again:

```bash
bash scripts/sync-customer-growth-reporting-governance-ruleset.sh --disable
```

## Handoff Checklist

- [ ] workflow `Customer Growth Reporting Governance Conformance` is present on default branch
- [ ] at least one successful run exists after the latest workflow edit
- [ ] branch protection or ruleset requires `All Customer Growth Reporting Governance Checks Passed`
- [ ] team knows where to find uploaded governance conformance artifacts
- [ ] governance evidence uses the canonical bootstrap template

## Evidence Reference

For governance incident review or rollout preparation, pair this handoff with:

- `docs/runbooks/CUSTOMER_GROWTH_REPORTING_RUNBOOK.md`
- `docs/runbooks/CUSTOMER_GROWTH_REPORTING_GOVERNANCE_STAGING_ROLLOUT_RUNBOOK.md`
- workflow `Customer Growth Reporting Governance Staging Smoke`
- `.github/workflows/customer-growth-reporting-governance-staging-smoke.yml`
- `docs/evidence/customer-growth/templates/customer-growth-reporting-governance-evidence-template.md`
- `scripts/assess-customer-growth-reporting-governance-gate-readiness.sh`
- `approvals/gate-readiness.md` and `approvals/gate-readiness.json` inside the staging evidence pack
