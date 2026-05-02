# CyberVPN Platform Foundation P1.1 OpenTofu Migration Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.1`  
**Phase:** `P1`  
**Primary owners:** `infra-platform`  
**Supporting owners:** `platform-architecture`, `sre-platform`  
**Purpose:** record the concrete repository, CI-surface, lockfile, and operator-surface changes performed for `P1.1`, plus the verification that already exists before any operator-approved live `plan/apply`.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-1-opentofu-migration-and-state-boundary-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-1-opentofu-migration-and-state-boundary-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- The sign-off pack explicitly allows `P1` planning and implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-013` as the formal reason `P1.1` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.1` result:

- canonical IaC CLI pinned to `OpenTofu 1.11.6`;
- IaC CI migrated from `hashicorp/setup-terraform` to `opentofu/setup-opentofu`;
- live-stack validation commands now run through `tofu`;
- local operator surface now defaults to `tofu`;
- inventory generation now prefers `--stack-dir`, `--tofu-bin`, and `--stack-output-file`;
- rollback compatibility remains available through legacy `--terraform-*` aliases and `TOFU=terraform` overrides;
- live-stack lockfiles were regenerated under `tofu init`;
- stack and runbook docs now present `tofu` as the canonical path;
- state boundaries, backend type, backend keys, and stack split were not changed.

This packet is **not yet claimed complete** because:

- no operator-approved live `tofu init` against real backends was executed in this evidence window;
- no state-backup record for the first real non-`backend=false` cutover has been attached yet.

That is intentional. `P1.1` has completed the safe repo and validation slice first, while leaving live backend cutover under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Canonical Version Contract

- added `.opentofu-version` pinned to `1.11.6`

### 3.2 CI Surface

- `.github/workflows/iac-ci.yml`
  - installs `OpenTofu`
  - runs `tofu fmt`
  - runs `tofu init -backend=false`
  - runs `tofu validate`
  - keeps manual approval posture for real apply work

### 3.3 Local Operator Surface

- `infra/Makefile`
  - canonical engine variable is now `TOFU`
  - existing `terraform-*` targets remain as compatibility aliases, but execute with `$(TOFU)`
  - canonical inventory commands now pass `--tofu-bin` and `--stack-dir`
  - live cutover evidence can now be captured through `tofu-capture-cutover-evidence`

- `infra/ansible/scripts/generate_inventory.py`
  - canonical CLI now speaks in OpenTofu terms
  - legacy `--terraform-*` flag aliases remain available for rollback workflows

- `infra/ansible/tests/test_generate_inventory.py`
  - updated to test canonical OpenTofu flags
  - added explicit rollback-alias coverage

- `infra/scripts/capture_opentofu_cutover_evidence.sh`
  - archives `init`, `state pull`, `plan`, and human-readable plan output into one evidence bundle
  - intentionally avoids `apply`
  - writes plan JSON only on explicit opt-in because it may contain sensitive values in plain text

### 3.4 Stack Constraints And Lockfiles

- live-stack `required_version` constraints moved to `~> 1.11.0`
- module-level `versions.tf` files now also require `~> 1.11.0`
- every committed live-stack `.terraform.lock.hcl` was regenerated under `tofu init`
- provider registry namespace now resolves through `registry.opentofu.org/...`

### 3.5 Canonical Operator Docs

- `infra/terraform/README.md`
- stack-local README files under `infra/terraform/live/*/*`
- `infra/ansible/README.md`
- `infra/README.md`
- `docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md`
- `docs/plans/2026-04-19-partner-platform-environment-command-inventory-sheet.md`
- production-window evidence link updated to the new OpenTofu command section

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Inventory Generator Tests

Command:

```bash
python -m unittest discover -s infra/ansible/tests -p 'test_*.py'
```

Result:

- `Ran 10 tests`
- `OK`

Coverage intent:

- canonical OpenTofu flags work;
- fixture-backed inventory generation works;
- rollback aliases `--terraform-bin` and `--terraform-dir` still work.

### 4.2 Operator Make Surface

Commands:

```bash
make -C infra inventory-fixture-staging TOFU=/tmp/opentofu-1.11.6/tofu
make -C infra tofu-fmt TOFU=/tmp/opentofu-1.11.6/tofu
make -C infra inventory-test
```

Result:

- fixture-backed inventory snapshot written successfully;
- fixture-backed `alloy-edge` target snapshot written successfully;
- `tofu-fmt` completed across all current live stacks;
- make-driven inventory tests passed.

### 4.3 Live-Stack Validation With OpenTofu

Validation family executed for all eight live stacks:

```bash
tofu -chdir=<stack> init -backend=false -input=false -no-color
tofu -chdir=<stack> validate -no-color
```

Validated stacks:

- `staging/foundation`
- `staging/edge`
- `staging/dns`
- `staging/control-plane`
- `production/foundation`
- `production/edge`
- `production/dns`
- `production/control-plane`

Result:

- every stack initialized successfully with `-backend=false`
- every stack validated successfully

### 4.4 Lockfile Regeneration Evidence

Observed lockfile changes:

- header changed from `terraform init` to `tofu init`
- provider source changed from `registry.terraform.io/...` to `registry.opentofu.org/...`

This was verified on both Hetzner and Cloudflare-backed stacks.

### 4.5 Workspace Readiness Check For Live Backend Evidence

Observed in the current workspace on 2026-04-22:

- no `backend.hcl` files are present under `infra/terraform/live/*/*`
- no relevant `AWS_*`, `TF_VAR_*`, `HCLOUD_*`, or `CLOUDFLARE_*` environment variables are present

Meaning:

- live remote-backend `tofu init` and `tofu plan` cannot be executed honestly from this workspace yet
- the blocker is missing operator-provided backend config and credentials, not missing repo automation

### 4.6 Cutover Evidence Automation Smoke

Validation commands executed:

```bash
bash -n infra/scripts/capture_opentofu_cutover_evidence.sh
make -C infra tofu-capture-cutover-evidence ...<fake tofu smoke inputs>...
```

Result:

- shell syntax check passed
- direct script execution produced:
  - `init.log`
  - `remote-state-backup.tfstate`
  - `remote-state-backup.tfstate.sha256`
  - `plan.log`
  - `plan.txt`
  - `plan.status`
  - `tfplan`
- the same flow also succeeded through the `make tofu-capture-cutover-evidence` wrapper

Interpretation:

- the remaining blocker for live evidence is external operator input, not missing capture tooling

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. backend type remains `s3`
2. backend keys remain unchanged
3. stack split remains:
   - `staging/foundation`
   - `staging/edge`
   - `staging/dns`
   - `staging/control-plane`
   - `production/foundation`
   - `production/edge`
   - `production/dns`
   - `production/control-plane`
4. no workspace indirection introduced
5. no state merge introduced
6. no live infrastructure apply was executed as part of this repo/validation slice

Explicitly not changed:

- `cybervpn-terraform-state` bucket naming
- `terraform.tfstate` object key naming
- `terraform_remote_state` boundaries already in use
- existing stack directory names under `infra/terraform/live/*`

These remain intentionally stable until a later, separately controlled phase changes them.

---

## 6. Residuals Before Packet Closure

Open residuals:

1. `state-backup confirmation` for the first real non-`backend=false` OpenTofu cutover is still pending.
2. `live tofu plan evidence` against real remote backends is still pending.
3. `owner-assigned rollback acknowledgement` remains to be recorded alongside the rollback note.

These residuals block a full `P1.1 complete` claim, but they do **not** invalidate the already-completed migration slice above.

Formal tracking:

- these residuals are now recorded as `EX-013` in the temporary exceptions register

---

## 7. Next Required Action

Before `P1.1` can be called complete:

1. record the state-backup procedure and exact backup artifact location for each live stack;
2. run operator-approved real `tofu init` and `tofu plan` against the live remote backends;
3. attach resulting plan evidence and confirm no unexpected infrastructure diff is accepted as “migration noise”;
4. attach the rollback owner acknowledgement referenced in the rollback note.

Canonical command family for step 2:

```bash
cd infra
make tofu-capture-cutover-evidence \
  TOFU=tofu \
  STACK_DIR=terraform/live/staging/foundation \
  BACKEND_CONFIG=terraform/live/staging/foundation/backend.hcl \
  EVIDENCE_DIR=artifacts/opentofu-cutover/staging-foundation-manual
```

If the stack requires root-module variables:

```bash
cd infra
make tofu-capture-cutover-evidence \
  TOFU=tofu \
  STACK_DIR=terraform/live/production/edge \
  BACKEND_CONFIG=terraform/live/production/edge/backend.hcl \
  VAR_FILE=terraform/live/production/edge/terraform.tfvars \
  EVIDENCE_DIR=artifacts/opentofu-cutover/production-edge-manual
```

---

## 8. Linked Rollback Note

Rollback procedure:

- [rollback-note.md](rollback-note.md)
