# Partner Admin GitHub Protection Handoff

This note defines the exact GitHub workflow and status check that should be configured as required before the integrated `partner + admin + backend` product conformance gate is treated as protected in the normal PR merge path.

Repository:
- `Beep206/CyberVPN`

Workflow:
- `.github/workflows/partner-admin-conformance.yml`
- workflow name: `Partner Admin Conformance`

Required status check:
- `All Partner/Admin Checks Passed`

This is the aggregator job on purpose. It stays stable even if internal job names evolve.

## What The Required Check Covers

The required check is green only if all of these jobs pass:

- `Backend Conformance Pack`
- `Admin Surface Readiness`
- `Partner Surface Readiness`

This means the branch-protection gate covers:

- backend partner/admin runtime and contract packs;
- admin surface readiness;
- partner surface readiness.

## Current Repository Ruleset State

GitHub ruleset:
- name: `partner-admin-main-gate`
- id: `15310657`
- URL: `https://github.com/Beep206/CyberVPN/rules/15310657`
- enforcement: `disabled`

Repo-side payload and helper:
- `.github/rulesets/partner-admin-main-gate.disabled.json`
- `scripts/sync-partner-admin-ruleset.sh`

## Manual GitHub Configuration

Configure branch protection or a ruleset for the protected branch and require this exact status check:

- `All Partner/Admin Checks Passed`

Do not duplicate this check inside the observability ruleset. Keep product conformance and observability as separate required gates.

## Current Prepared-But-Disabled State

The repository has a disabled ruleset prepared for this gate. It may be created or updated via:

```bash
bash scripts/sync-partner-admin-ruleset.sh --show-current
```

To create the disabled ruleset if it does not yet exist:

```bash
bash scripts/sync-partner-admin-ruleset.sh --create-disabled
```

To enable later:

```bash
bash scripts/sync-partner-admin-ruleset.sh --enable
```

To disable again:

```bash
bash scripts/sync-partner-admin-ruleset.sh --disable
```

## Recommended Companion Required Check

Pair this gate with observability:

- `All Partner Observability Checks Passed`

If both are required, the protected merge path ensures:

- product/runtime conformance is green;
- observability/runtime evidence gates are green.

## Handoff Checklist

- [ ] workflow `Partner Admin Conformance` is present on default branch
- [ ] at least one successful run exists after the latest workflow edit
- [ ] branch protection/ruleset requires `All Partner/Admin Checks Passed`
- [ ] observability gate remains separate
- [ ] team knows where to find partner/admin CI logs and artifacts
