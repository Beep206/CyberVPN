# Partner Observability GitHub Protection Handoff

This note defines the exact GitHub workflow and status check that should be configured as required before partner observability is treated as protected in the normal PR merge path.

Repository:
- `Beep206/CyberVPN`

Workflow:
- `.github/workflows/partner-observability-conformance.yml`
- workflow name: `Partner Observability Conformance`

Required status check:
- `All Partner Observability Checks Passed`

This is the aggregator job on purpose. It stays stable even if internal job names evolve.

Current repository ruleset state:
- GitHub ruleset name: `partner-observability-main-gate`
- GitHub ruleset id: `15310525`
- GitHub ruleset URL: `https://github.com/Beep206/CyberVPN/rules/15310525`
- current enforcement: `disabled`

Repo-side payload and helper:
- `.github/rulesets/partner-observability-main-gate.disabled.json`
- `scripts/sync-partner-observability-ruleset.sh`

## What The Required Check Covers

The required check is green only if all of these jobs pass:

- `Backend Observability Pack`
- `Partner Frontend Observability`
- `Admin Frontend Observability`
- `Observability Assets`

This means the branch-protection gate covers:

- backend runtime observability packs;
- partner/admin frontend observability surface checks;
- Prometheus and Alertmanager tooling validation with `promtool` and `amtool`;
- observability asset contract tests;
- Grafana dashboard validation;
- observability evidence bootstrap presence.

## CI Artifacts

Each workflow run uploads job logs as artifacts:

- `partner-observability-backend-<run_id>`
- `partner-observability-partner-<run_id>`
- `partner-observability-admin-<run_id>`
- `partner-observability-assets-<run_id>`

Use these artifacts when:

- a required check fails and the PR author needs exact logs;
- staging evidence needs a CI transcript reference;
- rollout review wants proof that local/CI observability conformance was green before a live window.

## Manual GitHub Configuration

Configure branch protection or a ruleset for the protected branch and require this exact status check:

- `All Partner Observability Checks Passed`

Do not require the four internal jobs separately unless there is a governance reason to expose each one individually. The aggregator check is the safer contract because it hides internal workflow refactors from branch protection.

## Current Prepared-But-Disabled State

The repository already has a disabled ruleset prepared for this gate:

- ruleset name: `partner-observability-main-gate`
- ruleset id: `15310525`
- enforcement: `disabled`

This means the branch protection contract is already created in GitHub but has no effect on merges until someone explicitly enables it.

To inspect current state:

```bash
bash scripts/sync-partner-observability-ruleset.sh --show-current
```

To enable later:

```bash
bash scripts/sync-partner-observability-ruleset.sh --enable
```

To disable again:

```bash
bash scripts/sync-partner-observability-ruleset.sh --disable
```

## Recommended Companion Required Checks

This document only covers the observability gate. Pair it with the existing partner/admin product conformance gate:

- `All Partner/Admin Checks Passed`

Current paired partner-admin ruleset:
- name: `partner-admin-main-gate`
- id: `15310657`
- URL: `https://github.com/Beep206/CyberVPN/rules/15310657`
- enforcement: `disabled`

If both are required, the protected merge path ensures:

- product/runtime conformance is green;
- observability/runtime evidence gates are green.

The observability ruleset itself should only require:

- `All Partner Observability Checks Passed`

Do not duplicate `All Partner/Admin Checks Passed` inside the observability ruleset payload if a separate partner-admin ruleset is used.

## Handoff Checklist

- [ ] workflow `Partner Observability Conformance` is present on default branch
- [ ] at least one successful run exists after the latest workflow edit
- [ ] branch protection/ruleset requires `All Partner Observability Checks Passed`
- [ ] partner-admin gate remains required if already adopted
- [ ] team knows where to find uploaded observability artifacts

## Evidence Reference

For live staging or rollout windows, pair this handoff with:

- `docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md`
- `docs/evidence/partner-platform/templates/partner-observability-evidence-template.md`
