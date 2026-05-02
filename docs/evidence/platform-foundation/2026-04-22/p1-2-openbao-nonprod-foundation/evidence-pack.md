# CyberVPN Platform Foundation P1.2 OpenBao Non-Prod Foundation Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.2`  
**Phase:** `P1`  
**Primary owners:** `infra-platform` / `security`  
**Supporting owners:** `platform-architecture`, `sre-platform`  
**Purpose:** record the concrete repository, validation, and operator-surface changes completed for `P1.2`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-2-openbao-nonprod-foundation-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-2-openbao-nonprod-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-014` as the formal reason `P1.2` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.2` result:

- dedicated non-prod `OpenBao` stack created at `infra/terraform/live/staging/openbao`;
- dedicated Hetzner VM module created at `infra/terraform/modules/openbao_node`;
- reusable firewall module extended for non-VPN foundational services through `extra_inbound_rules`;
- AWS KMS key and alias defined for `awskms` auto-unseal;
- pinned cloud-init/systemd/bootstrap path created for `OpenBao 2.5.2`;
- canonical baseline policy assets and OIDC/JWT example specs created under `infra/openbao`;
- canonical bootstrap helper created at `infra/scripts/openbao_bootstrap.py`;
- unit tests added for the bootstrap helper;
- root infra docs and stack-local docs updated to point to the new stack.

This packet is **not yet claimed complete** because:

- no operator-approved live `tofu apply` against real remote backend and cloud credentials has been executed in this evidence window;
- no live `OpenBao` init, audit-enable, namespace/auth/secrets mount, or `kv` smoke evidence has been attached yet;
- no operator-provided OIDC config or real JWT mount specs exist yet, only canonical examples.

That is intentional. `P1.2` has completed the safe repo and validation slice first, while leaving live control-plane bring-up under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Reusable Infrastructure Layer

- `infra/terraform/modules/firewall_policy`
  - added `extra_inbound_rules` so foundational control-plane services can expose approved ports without forking the firewall module

- `infra/terraform/modules/openbao_node`
  - added dedicated Hetzner VM module for external `OpenBao`
  - provisions:
    - primary IPv4
    - firewall attachment
    - cloud-init bootstrap
    - pinned OpenBao install
    - `openbao.hcl`
    - systemd unit
    - bootstrap TLS material

### 3.2 Non-Prod OpenBao Stack

- `infra/terraform/live/staging/openbao`
  - dedicated stack for the canonical `openbao-nonprod` control plane
  - creates:
    - AWS KMS key and alias
    - OpenBao firewall
    - non-prod OpenBao node set
  - reads only the legacy `staging/foundation` SSH key registry through remote state

### 3.3 OpenBao Baseline Assets

- `infra/openbao/policies`
  - baseline root/operator, bootstrap, fleet, and PKI policies

- `infra/openbao/examples`
  - `oidc-operators-config.json.example`
  - `jwt-mounts.json.example`

### 3.4 Bootstrap Helper And Tests

- `infra/scripts/openbao_bootstrap.py`
  - renders seal env file from current AWS env
  - initializes the cluster
  - applies baseline namespace, auth mounts, secrets engines, and policies
  - optionally applies OIDC config and JWT mount specs
  - optionally issues a bootstrap token
  - optionally runs a `kv` smoke check

- `infra/tests/test_openbao_bootstrap.py`
  - validates seal env rendering
  - validates baseline mount/policy flow through a mocked CLI runner

### 3.5 Operator Docs

- `infra/terraform/README.md`
- `infra/README.md`
- `infra/terraform/live/staging/openbao/README.md`

These now acknowledge the new non-prod `OpenBao` foundation path.

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 OpenTofu Formatting

Command:

```bash
/tmp/opentofu-1.11.6/tofu fmt -recursive \
  infra/terraform/modules/firewall_policy \
  infra/terraform/modules/openbao_node \
  infra/terraform/live/staging/openbao
```

Result:

- formatting completed successfully

### 4.2 OpenTofu Init And Validate

Commands:

```bash
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/openbao init -backend=false -input=false -no-color
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/openbao validate -no-color
```

Result:

- initialization completed successfully with `-backend=false`
- validation completed successfully

### 4.3 Bootstrap Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_openbao_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

Coverage intent:

- current AWS env is rendered correctly into seal env output
- baseline namespace/auth/secrets/policy flow behaves correctly under a mocked `bao` runner

### 4.4 Stack Lockfile

Observed artifact:

- `infra/terraform/live/staging/openbao/.terraform.lock.hcl`

Interpretation:

- the new stack is pinned and reproducible under the current `OpenTofu` toolchain

### 4.5 Workspace Readiness Check For Live OpenBao Evidence

Observed in the current workspace on 2026-04-22:

- no `backend.hcl` is present under `infra/terraform/live/staging/openbao`
- no real `AWS_*` or `TF_VAR_hcloud_token` credentials are present for a live stack apply
- no operator-provided OIDC issuer/client config is present
- no real `jwt-k8s-*` cluster specs are present

Meaning:

- live `tofu init/plan/apply` cannot be executed honestly from this workspace yet
- live `OpenBao` init and baseline apply evidence cannot be attached yet
- the blocker is missing operator-provided backend config, cloud credentials, and issuer details, not missing repo automation

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. `staging/openbao` is a separate stack from:
   - `staging/foundation`
   - `staging/edge`
   - `staging/dns`
   - `staging/control-plane`
2. the new stack reads only `staging/foundation` remote state for SSH key names
3. canonical ids remain:
   - `environment = nonprod`
   - `openbao_cluster_id = openbao-nonprod`
4. no legacy control-plane state was merged or extended
5. no live infrastructure apply was executed as part of this repo/validation slice

Explicitly not changed:

- legacy `staging` implementation path naming on disk
- current `foundation`, `edge`, `dns`, and `control-plane` state boundaries
- application runtime secret delivery
- live OIDC or JWT auth issuer configuration

---

## 6. Residuals Before Packet Closure

Open residuals:

1. `remote-backend apply evidence` for the first real non-prod `OpenBao` stack apply is still pending.
2. `AWS KMS auth evidence` for the OpenBao host is still pending.
3. `OpenBao init evidence` is still pending.
4. `file audit enable evidence` is still pending.
5. `namespace/auth/secrets/policy baseline evidence` is still pending.
6. `kv smoke evidence` is still pending.
7. `operator-auth inputs` for real `oidc-operators` configuration are still pending.
8. `future cluster-auth inputs` for real `jwt-k8s-*` mounts are still pending.

These residuals block a full `P1.2 complete` claim, but they do **not** invalidate the already-completed repository and validation slice above.

---

## 7. Recommended Next Live Commands

When operator-provided `backend.hcl` and credentials exist, the first honest live sequence should be:

```bash
tofu -chdir=infra/terraform/live/staging/openbao init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/openbao plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/openbao apply -var-file=terraform.tfvars
```

Then on the provisioned host:

```bash
python infra/scripts/openbao_bootstrap.py render-seal-env ...
sudo systemctl start openbao
python infra/scripts/openbao_bootstrap.py init-cluster ...
python infra/scripts/openbao_bootstrap.py apply-baseline ...
bao audit enable file file_path=/var/log/openbao/audit.log
```

Evidence for each step should be archived under:

```text
docs/evidence/platform-foundation/2026-04-22/p1-2-openbao-nonprod-foundation/
```
