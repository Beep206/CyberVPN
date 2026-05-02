# CyberVPN Platform Foundation P1.6 Platform GitOps Repository And Flux Bootstrap Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live GitHub and Flux bootstrap evidence pending  
**Packet:** `P1.6`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `sre-platform`, `security`

---

## 1. Packet Role

This document is the execution packet for `P1.6` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.6` exists to establish the first canonical GitOps control path for the program:

- separate desired-state repository name `platform-gitops`;
- first bootstrap cluster `nonprod-mgmt`;
- Flux as the canonical reconciler;
- Git as the desired-state source of truth;
- a bootstrap flow that does not leave a GitHub PAT stored in the cluster;
- a repository structure that cleanly separates `clusters`, `infrastructure`, and `apps`.

Implementation note:

- the repository slice for this packet is implemented and locally validated in the current monorepo;
- the remaining closure work is focused on live GitHub repository creation or validation, live Flux bootstrap against `nonprod-mgmt`, and attached reconciliation evidence from the running cluster.

---

## 2. Current Baseline

Before this packet:

- the naming registry froze `platform-gitops` as the desired-state repository, but there was no executable bootstrap helper or scaffold;
- `P1.5` introduced the management-cluster bootstrap path, but did not yet provide a GitOps repository baseline or Flux bootstrap helper;
- the repo had no source-controlled operator artifact for choosing between GitHub PAT auth and SSH deploy-key auth at bootstrap time.

Observed strengths:

- target-state architecture already froze `Flux` as the canonical GitOps engine;
- target-state architecture already froze the promotion model as `GitHub Actions -> PR into GitOps repo`;
- Flux official docs support GitHub bootstrap over SSH deploy keys via `--token-auth=false`;
- Flux `v2.8.x` supports Kubernetes `v1.35.x`, matching the non-prod management-cluster baseline.

Observed implementation risks:

- using `flux bootstrap github --token-auth` would store the GitHub PAT in the cluster, which is not the preferred security posture for this program;
- using a generic Git bootstrap with a permanent write-capable SSH key would give the in-cluster key more rights than needed for the frozen target state;
- putting real Kubernetes manifests into the GitOps repo too early would conflate `P1.6` bootstrap scope with `P2.2` workload delivery scope.

---

## 3. Canonical Decisions For P1.6

`P1.6` fixes the following decisions:

1. The desired-state repository name is `platform-gitops`.
2. The first bootstrap cluster path is `clusters/nonprod-mgmt`.
3. The initial repository structure follows the official Flux guide shape: `clusters/`, `infrastructure/`, `apps/`.
4. The bootstrap path uses `flux bootstrap github --token-auth=false` as the canonical GitHub mode.
5. The bootstrap flow prefers an SSH deploy key stored in-cluster over PAT-in-cluster auth.
6. Since Flux image automation is not in scope for `P1.6`, the deploy key should remain read-only.
7. `P1.6` freezes repository structure and operator bootstrap flow only; it does not yet introduce real `HelmRelease`, `GitRepository`, or `Kustomization` workload delivery objects outside the `flux-system` bootstrap path.
8. Secret values remain outside Git; this packet does not create any exception to that rule.

---

## 4. Scope

In scope for `P1.6`:

- add a canonical helper under [infra/scripts/platform_gitops_bootstrap.py](../../infra/scripts/platform_gitops_bootstrap.py);
- render a standalone `platform-gitops` repository scaffold with:
  - `README.md`
  - `.gitignore`
  - `clusters/nonprod-mgmt`
  - `infrastructure/nonprod-mgmt`
  - `apps/nonprod-mgmt`
  - bootstrap and check scripts
  - version metadata
- add unit coverage and local render smoke for the helper;
- update operator docs to acknowledge the GitOps bootstrap helper and separate desired-state repository surface;
- record the residual for missing live GitHub and Flux bootstrap evidence.

Out of scope for `P1.6`:

- live GitHub repository creation;
- live Flux bootstrap against a running cluster;
- real `HelmRelease`, `GitRepository`, `OCIRepository`, or `Kustomization` delivery objects for platform services;
- image automation controllers;
- production GitOps bootstrap;
- any secret value commits or SOPS adoption.

---

## 5. Official Constraints

The execution of `P1.6` follows current primary-source guidance:

- Flux bootstrap pushes the Flux manifests to a Git repository and configures the cluster to sync from Git;
- `flux bootstrap github --token-auth=false` uses a GitHub PAT at bootstrap time to configure a SSH deploy key, while the cluster authenticates to GitHub over SSH afterwards;
- the generated deploy key is read-only by default unless write access is explicitly requested;
- Flux `v2.8` supports Kubernetes `v1.33`, `v1.34`, and `v1.35`, which covers the current `nonprod-mgmt` Kubernetes version;
- Flux recommends a repository structure with `clusters/`, `infrastructure/`, and `apps/`.

Primary sources:

- Flux bootstrap for GitHub: https://fluxcd.io/flux/installation/bootstrap/github/
- Flux bootstrap command reference: https://fluxcd.io/flux/cmd/flux_bootstrap_github/
- Flux repository structure guide: https://fluxcd.io/flux/guides/repository-structure/
- Flux 2.8 GA announcement and supported Kubernetes versions: https://fluxcd.io/blog/2026/02/flux-v2.8.0/
- Flux latest release metadata (`v2.8.6`): https://github.com/fluxcd/flux2/releases/tag/v2.8.6

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.6`:

### 6.1 Bootstrap Helper And Tests

- [infra/scripts/platform_gitops_bootstrap.py](../../infra/scripts/platform_gitops_bootstrap.py)
- [infra/tests/test_platform_gitops_bootstrap.py](../../infra/tests/test_platform_gitops_bootstrap.py)

### 6.2 Operator Docs

- [infra/README.md](../../infra/README.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p1-6-platform-gitops-and-flux-bootstrap/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p1-6-platform-gitops-and-flux-bootstrap/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T1.6.1` Freeze The Separate Desired-State Repository Surface

**Goal:** render a canonical standalone `platform-gitops` repository scaffold without pretending that real workload manifests already exist.

Deliverables:

- scaffolded repository structure:
  - `clusters/nonprod-mgmt`
  - `infrastructure/nonprod-mgmt`
  - `apps/nonprod-mgmt`
- repository root rules and source-of-truth boundaries documented in `README.md`
- baseline `.gitignore` for credentials and transient artifacts

Acceptance criteria:

- scaffold renders reproducibly from the helper;
- source-of-truth boundaries match the naming registry;
- repository structure is explicit before `P2.2` adds real delivery resources.

### 7.2 `T1.6.2` Freeze The Flux Bootstrap Posture

**Goal:** make the operator bootstrap path explicit and safe.

Deliverables:

- a bootstrap script using `flux bootstrap github --token-auth=false`
- pinned Flux version metadata
- a check script for post-bootstrap verification

Acceptance criteria:

- the bootstrap flow does not rely on PAT-in-cluster auth;
- the helper makes the bootstrap path and cluster path explicit;
- the generated repo does not silently enable image automation or write-capable deploy-key assumptions.

### 7.3 `T1.6.3` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking a real GitHub repo or live Flux bootstrap.

Deliverables:

- helper unit tests;
- local render smoke;
- packet evidence pack;
- formal carry-forward residual for missing live GitHub and Flux evidence.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are written explicitly;
- later packets may begin without pretending that Flux is already live on `nonprod-mgmt`.

---

## 8. State-Boundary Rules

`P1.6` must keep the following invariants:

1. `platform-gitops` is a separate repository surface from `platform-monorepo`.
2. Flux is the reconciler, not the desired-state source of truth.
3. Secret values are not committed to the GitOps repository.
4. `P1.6` may bootstrap only the Flux control path, not real workload delivery resources.
5. `clusters/nonprod-mgmt` is the bootstrap path; future cluster and environment growth must not rewrite that canonical starting point.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| PAT auth is used inside the cluster | long-lived GitHub credentials end up stored in Kubernetes | use `flux bootstrap github --token-auth=false` in the helper baseline |
| the bootstrap deploy key gets unnecessary write privileges | in-cluster Git credential has more rights than frozen target state requires | keep image automation out of `P1.6`; use default read-only deploy-key posture |
| real workload manifests land during bootstrap packet | scope expands into `P2.2` and mixes repository freeze with service delivery | scaffold only structure and bootstrap scripts in `P1.6` |
| desired-state repo and monorepo boundaries drift | manual deploy logic or application repos regain deployment truth | repeat `platform-gitops` boundary in scaffold `README.md` and packet docs |
| packet is treated as closed without live Flux evidence | later packets assume GitOps already exists in-cluster | carry forward a formal residual until live GitHub and Flux bootstrap evidence is attached |
