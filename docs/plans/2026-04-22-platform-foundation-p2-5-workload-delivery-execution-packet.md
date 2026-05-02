# CyberVPN Platform Foundation P2.5 Workload Delivery Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live registry and GitOps evidence pending  
**Packet:** `P2.5`  
**Primary owners:** `infra-platform` / `backend-platform`  
**Supporting owners:** `sre-platform`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.5` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-monorepo-inventory.md](2026-04-21-platform-foundation-monorepo-inventory.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.5` exists to freeze the first source-repo and GitOps-repo delivery contract for Kubernetes-managed first-party workloads:

- first-party workloads are packaged as OCI Helm charts;
- charts are stored in `GHCR`;
- Flux consumes charts through `OCIRepository` plus `HelmRelease`;
- promotion happens by GitOps pull request, not by mutating Ansible inventory release manifests;
- the promoted state pins:
  - chart version
  - workload image digest.

Implementation note:

- this packet is being executed as a pre-launch `repo/validation` slice because no live `GHCR` package permissions, no live `platform-gitops` repository mutation, and no live workload cluster are available in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live package publish, GitOps PR creation, Flux reconciliation, and first workload rollout evidence.

---

## 2. Current Baseline

Before this packet:

- `.github/workflows/control-plane-images.yml` already built digest-pinned images for:
  - `backend`
  - `task-worker`
  - `helix-adapter`
- `.github/workflows/control-plane-promote.yml` still mutated Ansible inventory release manifests instead of GitOps workload state;
- `.github/workflows/deploy-staging.yml` remained a placeholder summary workflow rather than a canonical deployment action;
- the repo still had no first-party Helm chart directories.

Observed strengths:

- image-build discipline already exists and can be reused;
- `platform-gitops` and Flux baseline were already frozen in `P1.6`;
- workload-cluster app-delivery surfaces were expected by the roadmap but not yet scaffolded.

Observed implementation risks:

- without an explicit source-repo plus GitOps-repo contract, later workload migration could drift into ad hoc Helm or `kubectl` delivery;
- if chart packaging and GitOps mutation are not frozen together, the program could accidentally replace one legacy delivery path with another;
- the first workload set needs to be deliberately narrow so `P2.5` does not pretend the external fleet adapter path is already ready for Kubernetes delivery.

---

## 3. Canonical Decisions For P2.5

`P2.5` fixes the following decisions:

1. The first Kubernetes-managed first-party workload pair is:
   - `backend`
   - `task-worker`
2. `helix-adapter` is intentionally not part of the first `P2.5` pair because it remains entangled with external fleet transition work.
3. The source monorepo owns:
   - chart source
   - image builds
   - chart packaging
   - GitOps promotion workflow logic
4. The `platform-gitops` repository owns:
   - pinned chart version
   - pinned image digest
   - `OCIRepository`
   - `HelmRelease`
5. Flux must consume first-party charts through `OCIRepository` and `HelmRelease.chartRef`, not through Git-sourced chart packaging.
6. `HelmRelease` stays environment-specific and carries image digest pins inline.
7. Registry access for Flux and runtime image pulls is explicit and remains out of git.
8. Runtime application configuration still enters workloads through `ExternalSecret`, not through chart-embedded secret values.

---

## 4. Scope

In scope for `P2.5`:

- add a canonical helper under [infra/scripts/workload_delivery_bootstrap.py](../../infra/scripts/workload_delivery_bootstrap.py);
- add unit coverage for the helper;
- render source-repo scaffold for:
  - first charts
  - GitHub Actions workflow contract
- render `platform-gitops` scaffold for:
  - `OCIRepository`
  - `HelmRelease`
  - app namespace
  - cluster-local Flux `Kustomization`
- update operator docs so the helper is discoverable from `infra/README.md`;
- record packet evidence and formal carry-forward residual.

Out of scope for the current repository slice executed in this workspace:

- live `GHCR` chart publishing;
- live package permissions and package-repository linking;
- live `platform-gitops` repository mutation;
- live pull request creation;
- live Flux reconciliation;
- live workload deployment, rollback, or Flagger analysis.

---

## 5. Official Constraints

The execution of `P2.5` follows current primary-source guidance:

- Flux recommends `OCIRepository` as the preferred source for OCI Helm charts and supports direct `HelmRelease.chartRef` to `OCIRepository`;
- Flux OCI Helm examples require `layerSelector` to select the Helm content layer;
- Helm OCI push requires:
  - `oci://` prefix
  - no basename or tag in the push target reference;
- GitHub documents that:
  - workflows may publish packages associated with the workflow repository using `GITHUB_TOKEN`
  - package access for GitHub Actions on granular-permission packages must be explicitly granted where needed.

Primary sources:

- Flux manage Helm releases: https://v2-6.docs.fluxcd.io/flux/guides/helmreleases/
- Flux 2.3 OCI and `chartRef` guidance: https://fluxcd.io/blog/2024/05/flux-v2.3.0/
- Helm OCI registries: https://helm.sh/docs/v3/topics/registries/
- GitHub Packages permissions: https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages
- GitHub Container registry: https://docs.github.com/en/enterprise-cloud@latest/packages/working-with-a-github-packages-registry/working-with-the-container-registry

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.5`:

### 6.1 Helper And Tests

- [infra/scripts/workload_delivery_bootstrap.py](../../infra/scripts/workload_delivery_bootstrap.py)
- [infra/tests/test_workload_delivery_bootstrap.py](../../infra/tests/test_workload_delivery_bootstrap.py)

### 6.2 Existing Surfaces Updated During P2.5

- [infra/README.md](../../infra/README.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-5-workload-delivery/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-5-workload-delivery/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.5.1` Freeze The Source-Repo Delivery Contract

**Goal:** define how first-party workloads leave the monorepo.

Deliverables:

- first OCI Helm charts
- GitHub Actions workflow scaffold
- source-repo delivery `README`

Acceptance criteria:

- the workflow contract builds and pushes images;
- the workflow contract packages and pushes charts;
- the workflow contract describes GitOps pull-request promotion rather than inventory-manifest mutation.

### 7.2 `T2.5.2` Freeze The GitOps-Repo Delivery Contract

**Goal:** define how the workload cluster consumes first-party releases.

Deliverables:

- cluster-local Flux `Kustomization`
- `OCIRepository`
- `HelmRelease`
- namespace scaffold

Acceptance criteria:

- workloads are consumed through `OCIRepository` and `HelmRelease`;
- chart version and image digest are pinned separately;
- app namespace and runtime auth expectations are explicit.

### 7.3 `T2.5.3` Freeze The First Workload Pair

**Goal:** keep the initial application-delivery contract narrow and realistic.

Deliverables:

- chart scaffold for `backend`
- chart scaffold for `task-worker`
- explicit non-selection of `helix-adapter`

Acceptance criteria:

- the selected pair matches the roadmap’s first internal workload candidates;
- `helix-adapter` is explicitly excluded from the first pair rather than silently forgotten.

### 7.4 `T2.5.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any real chart publication or rollout exists.

Deliverables:

- helper unit tests
- local render smoke
- local syntax validation
- packet evidence pack
- formal carry-forward residual for missing live package publish and GitOps rollout proof

Acceptance criteria:

- repository slice is locally validated;
- live closure requirements are explicit;
- later `P2` packets may proceed without pretending first workload delivery is already operational.

---

## 8. State-Boundary Rules

`P2.5` must keep the following invariants:

1. The source monorepo is not the desired-state source for cluster rollout; `platform-gitops` remains that source.
2. `HelmRelease` values must not embed secret values.
3. Registry auth for Flux and runtime image pulls remains out of git.
4. The first pair is deliberately narrow and does not imply all existing images are now valid Kubernetes workloads.
5. `P2.5` must not claim any live chart publish or rollout success from repository-only work.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| source repo keeps mutating Ansible release manifests | target-state delivery model never actually changes | freeze GitOps PR as the only target promotion model |
| Flux chart consumption is underspecified | later rollout uses ad hoc Git-based chart delivery | freeze `OCIRepository + HelmRelease.chartRef` explicitly |
| private `GHCR` access is left implicit | live cluster fails to pull charts or images | render explicit registry secret contract and carry it as live closure debt |
| initial workload set grows too wide | packet scope becomes fiction | keep `backend + task-worker` as the first pair and explicitly exclude `helix-adapter` |

---

## 10. Packet Exit For The Repository Slice

The repository slice for `P2.5` is considered complete only when:

1. the helper and tests exist in git;
2. source-repo and GitOps-repo scaffolds render successfully;
3. operator docs point to the helper;
4. local validation passes;
5. the evidence pack records the honest residual that still blocks live packet closure.

This does **not** equal packet completion in the live program. Full `P2.5` closure additionally requires:

- live `GHCR` chart publish evidence;
- package access evidence for:
  - workflow publication
  - Flux chart pull
  - workload image pull
- real `platform-gitops` mutation on a promotion branch;
- real promotion pull request evidence;
- Flux reconciliation evidence for the first delivered workloads;
- non-prod deploy/rollback proof for at least one real workload.
