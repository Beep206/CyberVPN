# CyberVPN Platform Foundation P1.1 OpenTofu Migration And State-Boundary Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo migration slice complete, live backend evidence pending  
**Packet:** `P1.1`  
**Primary owners:** `infra-platform`  
**Supporting owners:** `platform-architecture`, `sre-platform`

---

## 1. Packet Role

This document is the execution packet for `P1.1` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-monorepo-inventory.md](2026-04-21-platform-foundation-monorepo-inventory.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.1` exists to move the current `infra/terraform` estate onto `OpenTofu` safely, while preserving the current state topology and the current operator-approved apply model.

This packet does **not** provision new target-state control planes by itself. Its job is to make the current infrastructure layer ready for the later `P1.2` through `P1.8` work without keeping `Terraform` as the execution dependency.

Implementation note:

- the repository migration slice for this packet is already in progress;
- the remaining closure work is focused on real remote-backend evidence, state-backup confirmation, and rollback-owner acknowledgement.

---

## 2. Current Baseline

Current repo state relevant to `P1.1`:

- infrastructure stacks already exist under [infra/terraform/live](../../infra/terraform/live);
- stack boundaries are already split into `foundation`, `edge`, `dns`, and legacy `control-plane`;
- current CI still installs and invokes `Terraform` through [iac-ci.yml](../../.github/workflows/iac-ci.yml);
- current operator commands still default to `terraform` through [infra/Makefile](../../infra/Makefile);
- inventory generation still defaults to the `terraform` binary in [infra/ansible/scripts/generate_inventory.py](../../infra/ansible/scripts/generate_inventory.py);
- stack docs still instruct operators to run `terraform -chdir=...` in:
  - [infra/terraform/README.md](../../infra/terraform/README.md)
  - stack-local `README.md` files under `infra/terraform/live/*/*`
- stack `versions.tf` files still pin `required_version = "~> 1.14.0"` and current lockfiles are `Terraform`-generated.

Observed strengths:

- remote backend layout is already explicit and per-stack;
- `terraform_remote_state` usage is limited and understandable;
- `S3` backend with `use_lockfile = true` is already scaffolded;
- state topology is already close to the target model.

Observed migration risks:

- CI and local operator workflows will drift if the binary contract changes in only one place;
- backend credentials can leak if `-backend-config` grows to include secrets instead of environment-driven auth;
- lockfiles and `required_version` constraints will be wrong after engine migration if they are left Terraform-specific;
- `P1.5` and later packets will stall if `P1.1` leaves mixed `terraform` and `tofu` assumptions alive.

---

## 3. Canonical Decisions For P1.1

`P1.1` fixes the following decisions:

1. The canonical IaC engine becomes `OpenTofu`, invoked as `tofu`.
2. The current state split remains intact:
   - one state per stack;
   - separate `staging` and `production` implementation paths;
   - no workspace multiplexing introduced;
   - no state merge across `foundation`, `edge`, `dns`, or legacy `control-plane`.
3. The current backend type remains `s3` during `P1.1`.
4. Manual operator-approved `plan/apply` remains the rule; `P1.1` does not introduce auto-apply CI.
5. `Terraform` stays available only as a rollback tool during the migration window, not as the default path.
6. New `P1+` docs and workflows must stop introducing fresh `terraform` defaults.

Recommended toolchain target:

- `OpenTofu 1.11.x` as the canonical CLI family for this program phase.

Reasoning:

- the current official docs are versioned under `1.11.x`;
- the migration guide explicitly supports side-by-side Terraform/OpenTofu operation during migration;
- `tofu init`, `tofu plan`, and `tofu apply` remain the canonical verification path after migration.

---

## 4. Scope

In scope for `P1.1`:

- migrate command, CI, and script defaults from `terraform` to `tofu`;
- replace Terraform-specific version constraints with OpenTofu-compatible ones;
- regenerate and recommit dependency lockfiles under OpenTofu;
- preserve current backend and state boundaries explicitly;
- update stack and runbook docs so the canonical operator path is `tofu`;
- document rollback-to-Terraform procedure for the migration window.

Out of scope for `P1.1`:

- changing backend type away from `s3`;
- introducing TACOS or a cloud backend;
- applying infrastructure changes unrelated to engine migration;
- provisioning `OpenBao`, `NATS`, `PostHog`, or Talos clusters;
- redesigning the stack topology;
- moving current edge or control-plane provisioning under the future `Node Fleet Controller`.

---

## 5. Official Constraints

The execution of `P1.1` must follow the current official `OpenTofu` guidance:

- back up infrastructure state and code before migration;
- initialize with `tofu init`, validate with `tofu plan`, and run `tofu apply` after verification so the state format is updated if needed;
- commit the dependency lock file written by `tofu init`;
- keep `.terraform/` out of version control;
- prefer environment variables for backend credentials and treat backend-config files carefully because backend settings are stored locally and can end up in plan files;
- re-run `tofu init` whenever backend configuration changes.

Primary sources:

- Migration Guide: https://opentofu.org/docs/intro/migration/migration-guide/
- Initializing Working Directories: https://opentofu.org/docs/cli/init/
- Provider Requirements: https://opentofu.org/docs/language/providers/requirements/
- Backend Configuration: https://opentofu.org/docs/language/settings/backends/configuration/
- GitHub Action for setup in CI: https://github.com/opentofu/setup-opentofu

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.1`:

### 6.1 CI And Automation

- [iac-ci.yml](../../.github/workflows/iac-ci.yml)
- any future IaC bootstrap workflows created during `P1`

### 6.2 Operator Commands And Scripts

- [infra/Makefile](../../infra/Makefile)
- [infra/ansible/scripts/generate_inventory.py](../../infra/ansible/scripts/generate_inventory.py)
- [infra/ansible/tests/test_generate_inventory.py](../../infra/ansible/tests/test_generate_inventory.py)

### 6.3 Infrastructure Stack Definitions

- all `versions.tf` files under [infra/terraform/live](../../infra/terraform/live)
- any module-level provider requirements under [infra/terraform/modules](../../infra/terraform/modules)
- committed `.terraform.lock.hcl` files under each live stack

### 6.4 Operator And Reference Docs

- [infra/terraform/README.md](../../infra/terraform/README.md)
- stack-local `README.md` files under `infra/terraform/live/*/*`
- [infra/README.md](../../infra/README.md)
- [infra/ansible/README.md](../../infra/ansible/README.md)
- [docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md](../runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md)
- any plan or inventory sheet still encoding canonical `terraform` operator commands

---

## 7. Workboard

## 7.1 `T1.1.1` Freeze The Binary And Version Contract

**Goal:** remove ambiguity about which CLI is canonical.

Deliverables:

- one canonical statement that the default IaC CLI is `tofu`;
- one pinned `OpenTofu 1.11.x` toolchain target for CI and operator usage;
- explicit rollback note that `terraform` remains break-glass during migration only.

Acceptance criteria:

- no new `P1+` document or workflow claims `terraform` as the default engine;
- `required_version` constraints in live stacks no longer point at Terraform `1.14.0`.

## 7.2 `T1.1.2` Migrate CI To OpenTofu

**Goal:** make CI validate the IaC estate with the same engine that operators will use.

Deliverables:

- `iac-ci.yml` installs `OpenTofu` instead of `Terraform`;
- all `fmt`, `init -backend=false`, and `validate` calls use `tofu`;
- CI summary text reflects `OpenTofu`, not `Terraform`.

Acceptance criteria:

- CI can validate every current live stack with `tofu`;
- no canonical IaC workflow depends on `hashicorp/setup-terraform`.

## 7.3 `T1.1.3` Migrate Local Operator Commands And Script Defaults

**Goal:** make local commands and script entrypoints converge on the same binary.

Deliverables:

- [infra/Makefile](../../infra/Makefile) defaults to `tofu`;
- inventory generation defaults to `tofu` while preserving an override flag for rollback cases;
- tests and help text stop describing `terraform` as the default.

Acceptance criteria:

- a normal operator path from `infra/Makefile` uses `tofu` without extra flags;
- scripts remain able to accept an explicit alternate binary during rollback if needed.

## 7.4 `T1.1.4` Regenerate Lockfiles Under OpenTofu

**Goal:** align dependency selection and lock metadata with the canonical engine.

Deliverables:

- `.terraform.lock.hcl` regenerated from `tofu init`;
- lockfiles recommitted for all current live stacks;
- provider source and hash metadata reviewed after regeneration.

Acceptance criteria:

- no stack is left with a stale Terraform-generated lockfile after the migration cutover;
- lockfiles are committed for every managed live stack.

## 7.5 `T1.1.5` Preserve And Document State Boundaries

**Goal:** prevent accidental state drift while the engine changes.

Deliverables:

- explicit confirmation that `foundation`, `edge`, `dns`, and legacy `control-plane` remain separate states;
- explicit confirmation that backend keys are unchanged during `P1.1`;
- explicit confirmation that cross-stack reads stay limited to the existing `terraform_remote_state` model.

Acceptance criteria:

- `P1.1` does not merge states, rename backend keys, or introduce workspaces;
- state-boundary rules are written into the packet evidence and updated docs.

## 7.6 `T1.1.6` Rewrite Operator Docs And Runbooks

**Goal:** stop reintroducing Terraform as the normative engine through documentation drift.

Deliverables:

- root and stack-local IaC docs updated to `tofu`;
- runbooks and command inventory sheets updated where the commands are still normative;
- warnings added where a Terraform rollback path remains available temporarily.

Acceptance criteria:

- a new operator following the docs reaches for `tofu`, not `terraform`;
- no canonical operator doc silently mixes both engines without context.

## 7.7 `T1.1.7` Produce Migration Evidence And Rollback Note

**Goal:** make `P1.1` auditable and reversible.

Deliverables:

- migration evidence pack with:
  - before/after CI validation;
  - lockfile regeneration proof;
  - command-surface diff;
  - state-backup confirmation;
- rollback note describing how to temporarily return to `terraform` if `tofu plan` diverges unexpectedly.

Acceptance criteria:

- `P1.1` closure does not depend on memory or commentary-only evidence;
- rollback steps are written before later `P1` packets begin relying on the new engine.

---

## 8. State-Boundary Rules

`P1.1` must keep the following invariants:

1. `staging/foundation`, `staging/edge`, `staging/dns`, and `staging/control-plane` remain separate remote states.
2. `production/foundation`, `production/edge`, `production/dns`, and `production/control-plane` remain separate remote states.
3. No environment may read state from the other environment.
4. No stack may begin writing into another stack's state.
5. No workspace indirection may be introduced to compress multiple stacks into one state object.
6. Any future `OpenBao`, `NATS`, `PostHog`, Talos management-cluster, or workload-cluster states created in later packets must use their own state objects rather than being bolted into legacy control-plane state.

These rules are the “clean state boundaries” part of `P1.1`.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| mixed `terraform` and `tofu` defaults remain alive | operators and CI drift immediately | migrate CI, Makefile, scripts, and docs in the same packet |
| backend credentials leak through backend-config use | `.terraform/` and plan files may contain sensitive backend settings | keep credentials in environment variables; do not expand backend.hcl to include secrets |
| lockfiles drift silently | provider selection differs between machines | regenerate and recommit lockfiles in one controlled change |
| state changes accidentally piggyback on engine migration | rollback becomes unclear | no infra-shape change in `P1.1`; treat any resource diff as a blocker |
| later packets start before rollback posture exists | migration becomes hard to unwind | write rollback note and evidence before calling `P1.1` complete |

---

## 10. Exit Criteria

`P1.1` is complete only when all of the following are true:

1. CI validates current live stacks with `OpenTofu`.
2. The default operator path uses `tofu`.
3. Stack `required_version` constraints are OpenTofu-compatible.
4. All committed live-stack lockfiles are regenerated under OpenTofu.
5. Root and stack-local docs no longer present `terraform` as the canonical path.
6. No backend key, backend type, workspace model, or stack split changed during the packet.
7. State backup and rollback instructions are attached to the packet evidence.
8. No unexpected infrastructure diff is accepted under the label of “migration noise”.

---

## 11. Evidence Required For Packet Closure

Minimum evidence bundle:

- CI run proving `tofu fmt` and `tofu validate` on all live stacks;
- local or CI transcript showing `tofu init -backend=false` succeeds on all validation paths;
- diff of `.terraform.lock.hcl` regeneration for every live stack;
- updated docs showing canonical `tofu` usage;
- state-backup confirmation before the first real non-`backend=false` initialization;
- rollback note and owner assignment.

Recommended archive location:

```text
docs/evidence/platform-foundation/<YYYY-MM-DD>/p1-1-opentofu-migration/
```

---

## 12. Immediate Follow-On Unlocks

Successful `P1.1` unlocks:

- `P1.2` non-prod `OpenBao`;
- `P1.3` non-prod `NATS`;
- `P1.4` non-prod `PostHog`;
- `P1.5` `nonprod-mgmt` bootstrap;
- later GitOps and fleet packets without dragging Terraform-specific defaults forward.
