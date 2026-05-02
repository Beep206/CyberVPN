# CyberVPN Platform Foundation P1.2 OpenBao Non-Prod Foundation Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live apply/bootstrap evidence pending  
**Packet:** `P1.2`  
**Primary owners:** `infra-platform` / `security`  
**Supporting owners:** `platform-architecture`, `sre-platform`

---

## 1. Packet Role

This document is the execution packet for `P1.2` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../security/platform-foundation-openbao-and-pki-registry.md](../security/platform-foundation-openbao-and-pki-registry.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.2` exists to establish the first canonical `OpenBao` control plane for the program:

- external to Kubernetes;
- canonical environment id `nonprod`;
- canonical cluster id `openbao-nonprod`;
- AWS KMS auto-unseal;
- integrated `Raft` storage;
- frozen namespace, auth-mount, policy, and PKI naming from `T0.3`.

Implementation note:

- the repository slice for this packet is already implemented and locally validated;
- the remaining closure work is focused on live stack apply evidence, OpenBao init/baseline evidence, and operator-supplied auth inputs.

---

## 2. Current Baseline

Before this packet:

- the repository had no canonical `OpenBao` stack under [infra/terraform/live](../../infra/terraform/live);
- `OpenBao` naming, auth mounts, and PKI paths were frozen only at the documentation layer in [platform-foundation-openbao-and-pki-registry.md](../security/platform-foundation-openbao-and-pki-registry.md);
- legacy secret material still lives in `.env`, Ansible vaults, and inventories under temporary exceptions `EX-002` and `EX-003`;
- no canonical non-prod secrets plane existed for later `VSO`, `JWT auth`, or PKI rollout work.

Observed strengths:

- the registry already fixes canonical ids, mount names, and path conventions;
- `P1.1` already established `OpenTofu` as the canonical IaC engine;
- existing Hetzner and AWS provider patterns already exist in the repo;
- current firewall and cloud-init modules are reusable enough to host an external control-plane VM.

Observed implementation risks:

- a new `OpenBao` stack can accidentally drift back into legacy `staging` naming unless canonical environment ids are repeated everywhere;
- AWS KMS credentials can leak if operators place them in `backend.hcl`, `terraform.tfvars`, or git-tracked files;
- bootstrap can become ad hoc unless namespace/auth/policy creation is scripted;
- one-node `non-prod` is acceptable for the baseline, but it is not an HA claim and cannot be described as such.

---

## 3. Canonical Decisions For P1.2

`P1.2` fixes the following decisions:

1. `OpenBao` remains outside Kubernetes on dedicated VMs.
2. The first implementation path is `infra/terraform/live/staging/openbao`, but the canonical environment id inside the stack is `nonprod`.
3. The canonical cluster id is `openbao-nonprod`.
4. The non-prod baseline is a single-node cluster with integrated `Raft` storage.
5. Auto-unseal uses `AWS KMS`, with the key created in the same stack.
6. The service must not start until `/etc/openbao/openbao.env` exists with out-of-band AWS credentials.
7. Root namespace remains for operator auth and emergency/admin flows; the application namespace baseline is `platform`.
8. `oidc-operators` is rooted in `root`; `cert-fleet` and `approle-bootstrap` are rooted in `platform`.
9. Canonical secrets engines in `platform` are:
   - `kv-apps`
   - `kv-shared`
   - `pki-k8s`
   - `pki-infra`
10. JWT K8s mounts remain spec-driven and cluster-specific; `P1.2` installs examples and bootstrap support, but does not fabricate cluster-specific JWT config without operator inputs.

---

## 4. Scope

In scope for `P1.2`:

- add a dedicated `OpenBao` VM module under [infra/terraform/modules/openbao_node](../../infra/terraform/modules/openbao_node);
- add a non-prod implementation stack under [infra/terraform/live/staging/openbao](../../infra/terraform/live/staging/openbao);
- create the AWS KMS key and alias for auto-unseal in the same stack;
- extend the reusable firewall module so foundational control-plane services can expose non-VPN ports safely;
- add pinned `OpenBao` install/bootstrap cloud-init;
- add baseline policy assets and example OIDC/JWT specs under [infra/openbao](../../infra/openbao);
- add a canonical bootstrap helper under [infra/scripts/openbao_bootstrap.py](../../infra/scripts/openbao_bootstrap.py);
- add unit coverage for the bootstrap helper;
- update operator docs and evidence path for the new non-prod foundation.

Out of scope for `P1.2`:

- production `OpenBao`;
- non-prod HA `OpenBao`;
- Kubernetes/VSO integration;
- application secrets migration;
- PKI issuance for real workloads;
- backup/restore drill automation beyond documenting the residual for `P1.8`;
- final operator OIDC provider details for human auth;
- real `jwt-k8s-*` cluster mounts for clusters that do not exist yet.

---

## 5. Official Constraints

The execution of `P1.2` must follow the current official `OpenBao` guidance:

- `awskms` seal may be activated through a `seal "awskms"` stanza or environment variables; AWS credentials should be supplied through environment variables rather than persisted in config;
- the principal used by OpenBao must have `kms:Encrypt`, `kms:Decrypt`, and `kms:DescribeKey` on the target KMS key;
- integrated storage `raft` requires `cluster_addr` and stores replicated data on each node;
- auth methods and secrets engines must be enabled explicitly at the chosen mount path before configuration;
- the file audit device must be enabled explicitly after init/unseal.

Primary sources:

- AWS KMS seal: https://openbao.org/docs/configuration/seal/awskms/
- Integrated storage (Raft): https://openbao.org/docs/configuration/storage/raft/
- `auth enable`: https://openbao.org/docs/commands/auth/enable/
- `secrets enable`: https://openbao.org/docs/commands/secrets/enable/
- `audit enable`: https://openbao.org/docs/commands/audit/enable/
- JWT/OIDC auth: https://openbao.org/docs/auth/jwt/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.2`:

### 6.1 Infrastructure Modules And Stacks

- [infra/terraform/modules/firewall_policy](../../infra/terraform/modules/firewall_policy)
- [infra/terraform/modules/openbao_node](../../infra/terraform/modules/openbao_node)
- [infra/terraform/live/staging/openbao](../../infra/terraform/live/staging/openbao)

### 6.2 Bootstrap And Policy Assets

- [infra/openbao/policies](../../infra/openbao/policies)
- [infra/openbao/examples](../../infra/openbao/examples)
- [infra/scripts/openbao_bootstrap.py](../../infra/scripts/openbao_bootstrap.py)
- [infra/tests/test_openbao_bootstrap.py](../../infra/tests/test_openbao_bootstrap.py)

### 6.3 Operator Docs

- [infra/terraform/README.md](../../infra/terraform/README.md)
- [infra/README.md](../../infra/README.md)
- [infra/terraform/live/staging/openbao/README.md](../../infra/terraform/live/staging/openbao/README.md)

---

## 7. Workboard

## 7.1 `T1.2.1` Provision The Non-Prod Stack Boundary

**Goal:** create one clean, isolated state object for the `OpenBao` non-prod foundation.

Deliverables:

- dedicated stack under `live/staging/openbao`;
- explicit outputs for node access and KMS ids;
- separate state boundary from `foundation`, `edge`, `dns`, and legacy `control-plane`.

Acceptance criteria:

- the stack validates independently under `tofu`;
- it reads shared SSH key names from `foundation` only;
- it does not merge itself into legacy control-plane state.

## 7.2 `T1.2.2` Bootstrap A Safe External OpenBao Host

**Goal:** make first boot predictable and non-ad hoc.

Deliverables:

- pinned `OpenBao` install path through cloud-init;
- systemd service for `openbao`;
- TLS material and `openbao.hcl`;
- service start gated on `/etc/openbao/openbao.env`.

Acceptance criteria:

- no AWS credentials are written into git-tracked files;
- operator-created seal env is the only supported start gate;
- node firewall exposes only SSH, API/UI, and metrics on approved CIDRs.

## 7.3 `T1.2.3` Freeze The Baseline Mounts, Policies, And Bootstrap Flow

**Goal:** stop mount/policy drift before later packets depend on them.

Deliverables:

- baseline HCL policy assets;
- example OIDC and JWT specs;
- bootstrap helper that can initialize and apply the baseline.

Acceptance criteria:

- the helper can initialize a fresh cluster and apply the frozen baseline idempotently;
- the helper does not require hand-edited ad hoc shell snippets;
- root token revocation remains an explicit operator-controlled option.

## 7.4 `T1.2.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live evidence.

Deliverables:

- `tofu validate` on the new stack;
- unit tests for bootstrap helper;
- packet evidence pack documenting what is done and what still requires operator-provided credentials and inputs.

Acceptance criteria:

- local repo slice is validated;
- residuals are written explicitly;
- later packets may begin without pretending that live OpenBao evidence already exists.

---

## 8. State-Boundary Rules

`P1.2` must keep the following invariants:

1. `staging/openbao` is its own remote state object.
2. `staging/openbao` may read `staging/foundation` through remote state for SSH key names only.
3. `staging/openbao` must not write into legacy `foundation`, `edge`, `dns`, or `control-plane` state.
4. The stack path may remain under legacy `staging/`, but the canonical environment id in resource names and labels remains `nonprod`.
5. No application workload may depend on this packet as if runtime secrets migration were already complete.
6. No Kubernetes auth mounts may be fabricated with placeholder cluster identity and then mistaken for real platform auth.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| AWS credentials leak into repo or plan artifacts | breaks secrets-plane posture before OpenBao is even live | require out-of-band env file generation; never store AWS creds in `backend.hcl` or `terraform.tfvars` |
| legacy `staging` naming bleeds into canonical ids | later packets consume wrong environment vocabulary | keep `environment = nonprod` and `openbao_cluster_id = openbao-nonprod` inside the stack |
| bootstrap becomes shell-history knowledge | repeatability and auditability collapse immediately | use `openbao_bootstrap.py` plus example specs and policy files |
| operators assume one-node non-prod is HA | later readiness claims become misleading | document single-node non-prod as baseline only, not HA evidence |
| metrics or API surface are overexposed | foundational secrets-plane gets unnecessary attack surface | firewall API and metrics separately, with explicit CIDR allowlists |
| JWT or OIDC config is invented without real issuers | auth posture becomes fake and hard to trust | ship examples and helper support only; live config requires operator inputs |

---

## 10. Exit Criteria

`P1.2` is complete only when all of the following are true:

1. The dedicated `OpenBao` stack validates under `OpenTofu`.
2. The non-prod `OpenBao` VM module, firewall extension, policy assets, and bootstrap helper exist in the repository.
3. Operator docs point to the new stack and bootstrap helper.
4. A real non-prod stack apply has been executed against a real backend and cloud credentials.
5. OpenBao has been initialized successfully on the live host.
6. The baseline namespace/auth/secrets/policy layout has been applied successfully.
7. The file audit device is enabled on the live host.
8. Evidence exists for:
   - `status`
   - init output escrow
   - baseline mounts/policies
   - a `kv` smoke check
   - operator bootstrap path for `/etc/openbao/openbao.env`
9. No unexplained infrastructure diff is accepted as “bootstrap noise”.

At the time of writing, criteria `1` through `3` are satisfied in the repository slice; criteria `4` through `9` remain pending live evidence.

---

## 11. Evidence Required For Packet Closure

Minimum evidence bundle:

- `tofu fmt` and `tofu validate` for the new stack;
- unit test evidence for the bootstrap helper;
- stack README and root infra docs updated to point to the canonical operator path;
- archived live `tofu init/plan/apply` evidence for the new stack;
- host bootstrap evidence:
  - rendered `/etc/openbao/openbao.env`
  - `systemctl status openbao`
  - `bao status`
  - `bao audit enable file ...`
  - namespace/auth/secrets/policy evidence
- operator note stating where init/recovery material was escrowed.

Recommended archive location:

```text
docs/evidence/platform-foundation/<YYYY-MM-DD>/p1-2-openbao-nonprod-foundation/
```

---

## 12. Immediate Follow-On Unlocks

Successful `P1.2` unlocks:

- `P1.7` non-prod observability for the new control plane;
- `P1.8` backup and restore work for `OpenBao`;
- `P2.2` platform services that depend on `OpenBao` naming and secret-engine baseline;
- later `JWT auth`, PKI, and `VSO` packets without reopening the path and mount conventions frozen in `T0.3`.
