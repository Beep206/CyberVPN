# Customer Growth Notification GitHub Protection Handoff

This note defines the exact GitHub workflow and status check that should be configured as required before the repaired customer growth notification lifecycle is treated as protected in the normal PR merge path.

Repository:
- `Beep206/CyberVPN`

Workflow:
- `.github/workflows/customer-growth-notification-conformance.yml`
- workflow name: `Customer Growth Notification Conformance`

Required status check:
- `All Customer Growth Notification Checks Passed`

This is the aggregator job on purpose. It stays stable even if internal job names evolve.

Current repository ruleset state:
- GitHub ruleset name: `customer-growth-notification-main-gate`
- GitHub ruleset id: `15405034`
- GitHub ruleset URL: `https://github.com/Beep206/CyberVPN/rules/15405034`
- current enforcement: `disabled`

Repo-side payload and helper:
- `.github/rulesets/customer-growth-notification-main-gate.disabled.json`
- `scripts/sync-customer-growth-notification-ruleset.sh`

## What The Required Check Covers

The required check is green only if all of these jobs pass:

- `Backend Growth Notification Conformance`
- `Frontend Growth Notification Conformance`
- `Admin Growth Notification Conformance`
- `Growth Notification Rollout Assets`

This means the branch-protection gate covers:

- backend delivery, repair, escalation, and conformance packs;
- customer rewards-hub and miniapp growth-notification surfaces;
- admin growth delivery consoles and delivery forensics;
- rollout asset validation, dashboard validation, and evidence bootstrap presence.

## CI Artifacts

Each workflow run uploads job logs as artifacts:

- `customer-growth-notification-backend-<run_id>`
- `customer-growth-notification-frontend-<run_id>`
- `customer-growth-notification-admin-<run_id>`
- `customer-growth-notification-assets-<run_id>`

Use these artifacts when:

- a required check fails and the PR author needs exact logs;
- a staging evidence pack needs a CI transcript reference;
- rollout review wants proof that conformance and rollout assets were green before a live window.

## Manual GitHub Configuration

Configure branch protection or a ruleset for the protected branch and require this exact status check:

- `All Customer Growth Notification Checks Passed`

Do not require the four internal jobs separately unless governance wants each internal surface exposed. The aggregator check is the safer contract because it survives internal workflow refactors.

## Current Prepared-But-Disabled State

The repository keeps a disabled ruleset payload for this gate:

- ruleset name: `customer-growth-notification-main-gate`
- enforcement: `disabled`

Inspect current state:

```bash
bash scripts/sync-customer-growth-notification-ruleset.sh --show-current
```

Create the disabled ruleset if it does not yet exist:

```bash
bash scripts/sync-customer-growth-notification-ruleset.sh --create-disabled
```

Enable later:

```bash
bash scripts/sync-customer-growth-notification-ruleset.sh --enable
```

Disable again:

```bash
bash scripts/sync-customer-growth-notification-ruleset.sh --disable
```

## Handoff Checklist

- [ ] workflow `Customer Growth Notification Conformance` is present on default branch
- [ ] at least one successful run exists after the latest workflow edit
- [ ] branch protection/ruleset requires `All Customer Growth Notification Checks Passed`
- [ ] team knows where to find uploaded growth-notification artifacts
- [ ] staging rollout uses the canonical smoke and evidence pack

## Evidence Reference

For live staging or rollout windows, pair this handoff with:

- `docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_DELIVERY_RUNBOOK.md`
- `docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_STAGING_ROLLOUT_RUNBOOK.md`
- `docs/evidence/customer-growth/templates/customer-growth-notification-rollout-evidence-template.md`
