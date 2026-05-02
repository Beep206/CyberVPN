# CyberVPN Platform Foundation P2.5 Workload Delivery Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.5`  
**Phase:** `P2`  
**Primary owners:** `infra-platform` / `backend-platform`  
**Supporting owners:** `sre-platform`, `security`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.5`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-5-workload-delivery-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-5-workload-delivery-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` cannot be claimed because `P2.1` through `P2.5` still carry live-closure exceptions.
- this evidence pack carries `EX-025` as the formal reason `P2.5` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.5` result:

- canonical helper added at `infra/scripts/workload_delivery_bootstrap.py`;
- helper renders a two-surface scaffold:
  - source monorepo delivery contract
  - `platform-gitops` app-delivery contract
- first workload pair is frozen as:
  - `backend`
  - `task-worker`
- `helix-adapter` is explicitly excluded from the first pair;
- the workflow contract freezes:
  - image build and push
  - OCI Helm chart package and push
  - GitOps pull-request promotion
- the GitOps scaffold freezes:
  - `OCIRepository`
  - `HelmRelease`
  - cluster-local Flux `Kustomization`
  - namespace for first platform workloads.

This packet is **not yet claimed complete** because:

- no live `GHCR` chart package exists;
- no package access configuration exists yet for:
  - GitHub Actions publication
  - Flux chart pull
  - workload image pull
- no live `platform-gitops` repository mutation or PR evidence exists;
- no live Flux reconciliation or workload rollout exists.

That is intentional. `P2.5` first freezes the delivery contract and carries the runtime closure debt explicitly.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/workload_delivery_bootstrap.py`
  - renders source-repo and GitOps-repo scaffolds
  - renders first charts for:
    - `backend`
    - `task-worker`
  - renders GitHub Actions workflow contract
  - renders Flux `OCIRepository` and `HelmRelease` contracts

- `infra/tests/test_workload_delivery_bootstrap.py`
  - validates scaffold rendering
  - validates `OCIRepository` plus `HelmRelease` contract
  - validates the first workload pair and workflow expectations

### 3.2 Operator Docs

- `infra/README.md`
  - now documents `workload_delivery_bootstrap.py` as the canonical helper for `P2.5`

### 3.3 Packet And Program Records

- `docs/plans/2026-04-22-platform-foundation-p2-5-workload-delivery-execution-packet.md`
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-025`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_workload_delivery_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/workload_delivery_bootstrap.py
```

Result:

- compilation completed successfully

### 4.3 Helper Render Smoke

Command shape:

```bash
python infra/scripts/workload_delivery_bootstrap.py render-scaffold \
  --output-dir <temporary-dir> \
  --source-repository-slug beep/vpnbussiness
```

Result:

- helper completed successfully against the current repository workspace
- rendered scaffold includes:
  - `source-repo/.github/workflows/platform-workload-delivery.yml`
  - `source-repo/charts/cybervpn-backend`
  - `source-repo/charts/cybervpn-task-worker`
  - `platform-gitops/clusters/nonprod-hetzner-hel1-core/platform-workloads.yaml`
  - `platform-gitops/apps/nonprod-hetzner-hel1-core/platform-workloads/backend`
  - `platform-gitops/apps/nonprod-hetzner-hel1-core/platform-workloads/task-worker`
- rendered contract explicitly includes:
  - `helm push`
  - `gh pr create`
  - `OCIRepository`
  - `HelmRelease`
  - chart version pin
  - image digest pin

### 4.4 Workspace Readiness Check For Live Closure

Observed in the current workspace on 2026-04-22:

- no live `GHCR` chart publication evidence exists;
- no live package access or repository-linking evidence exists;
- no live `platform-gitops` repository token or mutation proof exists;
- no live Flux reconciliation exists for the first workloads;
- no non-prod workload deploy or rollback evidence exists.

Meaning:

- the packet cannot honestly claim first-party workload delivery is operational yet;
- `P2.5` must therefore carry a formal residual until real package publish, GitOps PR, and rollout evidence are attached.

---

## 5. Remaining Live Closure Requirements

`P2.5` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. live `GHCR` chart publish exists for the first workload pair;
2. package access is configured and recorded for:
   - GitHub Actions publication with `GITHUB_TOKEN`
   - Flux chart pull
   - workload image pull
3. real promotion evidence exists for:
   - mutation branch in `platform-gitops`
   - pull request creation
   - changed chart version and image digest pins
4. live Flux reconciliation exists for:
   - `platform-workloads`
   - first `OCIRepository`
   - first `HelmRelease`
5. at least one first workload has:
   - deploy evidence
   - rollback or remediation evidence
6. `EX-025` is removed from the exceptions register.
